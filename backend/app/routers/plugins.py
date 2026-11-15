"""Plugin Center routes: catalogue, status detection, Agent Reach read, SkillSpector scan."""
from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_user
from ..errors import IntegrationNotConfigured, ProviderError
from ..models import User
from ..services import plugins as plugin_service

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


class ScanRequest(BaseModel):
    path: str = Field(min_length=1, max_length=500)


def _run_cli(args: list[str], timeout: float) -> tuple[int, str, str]:
    """Run a CLI synchronously in a thread (Windows asyncio subprocess is NotImplementedError)."""
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, errors="replace")
    return proc.returncode, proc.stdout, proc.stderr


@router.get("")
async def list_plugins(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    return plugin_service.catalog()


@router.get("/{plugin_id}")
async def plugin_detail(plugin_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    try:
        return plugin_service.detect(plugin_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Plugin not found")


@router.get("/agent-reach/read")
async def agent_reach_read(url: str = Query(min_length=4), user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Read a public page through the Agent Reach CLI (read-only)."""
    if not shutil.which("agent-reach"):
        raise IntegrationNotConfigured(
            "Agent Reach",
            "AGENT_REACH_CLI",
            "Install the Agent Reach CLI (https://github.com/Panniantong/Agent-Reach) and run `agent-reach doctor` first.",
        )
    try:
        code, stdout, stderr = await asyncio.to_thread(_run_cli, ["agent-reach", "read", url], 60)
    except subprocess.TimeoutExpired:
        raise ProviderError("Agent Reach", "agent-reach read timed out after 60s")
    except OSError as exc:
        raise ProviderError("Agent Reach", f"Could not start agent-reach: {exc}")
    if code != 0:
        raise ProviderError("Agent Reach", f"agent-reach read failed: {(stderr or stdout)[:300] or f'exit code {code}'}")
    return {"url": url, "ok": True, "text": stdout[:8000]}


@router.post("/skillspector/scan")
async def skillspector_scan(payload: ScanRequest, user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Scan a skill/plugin path with NVIDIA SkillSpector before installing."""
    path = Path(payload.path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Path not found: {payload.path}")
    if not plugin_service._skillspector_installed():
        raise IntegrationNotConfigured(
            "NVIDIA SkillSpector",
            "SKILLSPECTOR_PY",
            "Install first: pip install skillspector (https://github.com/NVIDIA/skillspector)",
        )
    exe = shutil.which("skillspector") or "skillspector"
    try:
        code, stdout, stderr = await asyncio.to_thread(_run_cli, [exe, "scan", str(path)], 60)
    except subprocess.TimeoutExpired:
        raise ProviderError(
            "SkillSpector",
            "Scanner did not respond within 60s. It is an agent-based tool and may need an LLM API key or interactive config; run `skillspector --help` in a terminal first.",
        )
    except OSError as exc:
        raise ProviderError("SkillSpector", f"Could not start skillspector: {exc}")
    if code != 0:
        raise ProviderError("SkillSpector", f"Scan failed: {(stderr or stdout)[:300] or f'exit code {code}'}")
    return {"path": str(path), "ok": True, "report": stdout[:8000]}
