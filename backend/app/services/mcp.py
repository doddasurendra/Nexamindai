"""MCP over HTTP JSON-RPC: connection checks, tool discovery and permissioned execution."""
from __future__ import annotations

import base64
import hashlib
import json
import time
from typing import Any

import httpx

from ..config import get_settings
from ..errors import ProviderError
from .fetch import validate_url

settings = get_settings()

try:
    from cryptography.fernet import Fernet

    def _fernet() -> "Fernet":
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
        return Fernet(key)

    def encrypt_headers(headers: dict[str, str]) -> str:
        return _fernet().encrypt(json.dumps(headers).encode()).decode()

    def decrypt_headers(token: str) -> dict[str, str]:
        if not token:
            return {}
        return json.loads(_fernet().decrypt(token.encode()).decode())

except Exception:  # pragma: no cover - cryptography missing

    def encrypt_headers(headers: dict[str, str]) -> str:
        return base64.b64encode(json.dumps(headers).encode()).decode()

    def decrypt_headers(token: str) -> dict[str, str]:
        if not token:
            return {}
        return json.loads(base64.b64decode(token).decode())


async def _rpc(
    url: str,
    method: str,
    params: dict[str, Any] | None,
    headers: dict[str, str],
    *,
    session_id: str | None = None,
    allow_private: bool = False,
    request_id: int = 1,
) -> tuple[dict[str, Any], str | None]:
    await validate_url(url, allow_private=allow_private)
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
    merged = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", **headers}
    if session_id:
        merged["Mcp-Session-Id"] = session_id
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload, headers=merged)
    if response.status_code >= 400:
        raise ProviderError("MCP", f"{method} failed: HTTP {response.status_code} {response.text[:300]}")
    new_session = response.headers.get("mcp-session-id")
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type:
        data = None
        for line in response.text.splitlines():
            if line.startswith("data:"):
                data = json.loads(line[5:].strip())
                break
        if data is None:
            raise ProviderError("MCP", "Empty SSE response")
    else:
        data = response.json()
    if "error" in data:
        raise ProviderError("MCP", str(data["error"]))
    return data.get("result", {}), new_session


async def connect(url: str, headers: dict[str, str], *, allow_private: bool = False) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    init, session = await _rpc(
        url,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "NexaMind AI", "version": "1.0.0"},
        },
        headers,
        allow_private=allow_private,
    )
    tools_payload, _ = await _rpc(url, "tools/list", {}, headers, session_id=session, allow_private=allow_private)
    tools = [
        {
            "name": tool.get("name"),
            "description": tool.get("description", ""),
            "inputSchema": tool.get("inputSchema", {}),
        }
        for tool in tools_payload.get("tools", [])
    ]
    return init, tools


async def call_tool(
    url: str,
    headers: dict[str, str],
    tool: str,
    arguments: dict[str, Any],
    *,
    allow_private: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    result, _ = await _rpc(
        url,
        "tools/call",
        {"name": tool, "arguments": arguments},
        headers,
        allow_private=allow_private,
        request_id=2,
    )
    return {"result": result, "latency_ms": int((time.perf_counter() - started) * 1000)}
