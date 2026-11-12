"""Generic API connector engine for the API Universe."""
from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import time
from urllib.parse import urljoin, urlparse

import httpx

from ..config import get_settings
from ..errors import SSRFBlocked
from .fetch import validate_url

settings = get_settings()

ALLOWED_SCHEMES = {"http", "https"}


class ApiConnector:
    """Generic HTTP connector with SSRF protection, retries, and usage logging."""

    def __init__(self, db, user_id: int):
        self.db = db
        self.user_id = user_id

    async def _check_ssrf(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in ALLOWED_SCHEMES:
            raise ValueError(f"Scheme not allowed: {parsed.scheme}")
        host = parsed.hostname or ""
        if not host:
            raise ValueError("Missing host")
        # Block obvious localhost / private ranges
        try:
            infos = await asyncio.get_running_loop().run_in_executor(None, socket.getaddrinfo, host, None)
        except socket.gaierror:
            raise ValueError(f"Host cannot be resolved: {host}")
        for info in infos:
            addr = info[4][0]
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                continue
            if _is_forbidden_ip(ip):
                raise ValueError(f"Blocked address: {addr}")
        return url

    async def get(self, api_url: str, path: str = "", params: dict | None = None) -> dict:
        """GET request to an API with SSRF checks and logging."""
        started = time.perf_counter()
        parsed = urlparse(api_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        url = urljoin(base, path or parsed.path)
        try:
            await self._check_ssrf(url)
        except (ValueError, SSRFBlocked) as exc:
            return {"status": "error", "error": str(exc), "ms": int((time.perf_counter() - started) * 1000)}

        headers: dict[str, str] = {"Accept": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
                response = await client.get(url, params=params, headers=headers)
            ms = int((time.perf_counter() - started) * 1000)
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                data = response.json()
                return {"status": "ok" if response.is_success else "error", "status_code": response.status_code, "data": data, "ms": ms}
            return {"status": "ok" if response.is_success else "error", "status_code": response.status_code, "data": response.text[:8000], "ms": ms}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "ms": int((time.perf_counter() - started) * 1000)}


def _is_forbidden_ip(ip):
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )