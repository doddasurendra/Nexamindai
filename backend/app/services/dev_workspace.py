"""Software Development Workspace: inspect public GitHub repositories (read-only)."""
from __future__ import annotations

import asyncio
import base64
import time
from typing import Any

import httpx

from ..config import get_settings

settings = get_settings()

GH_API = "https://api.github.com"


async def _gh_get(path: str, timeout: float = 15) -> Any:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(
            f"{GH_API}{path}",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "NexaMindAI/1.0"},
        )
    if response.status_code == 404:
        raise ValueError("Repository not found")
    if response.status_code == 403:
        raise ValueError("GitHub API rate limit reached (60/hour unauthenticated)")
    if response.status_code >= 400:
        raise ValueError(f"GitHub API error: HTTP {response.status_code}")
    return response.json()


async def inspect_repo(repo: str) -> dict[str, Any]:
    """Inspect a public GitHub repository: metadata, tree, languages, README."""
    started = time.perf_counter()
    parts = repo.strip().strip("/").split("/")
    if len(parts) < 2:
        raise ValueError("Use the form owner/repository, e.g. fastapi/fastapi")
    owner, name = parts[0], parts[1]

    repo_data = await _gh_get(f"/repos/{owner}/{name}")
    languages_task = _gh_get(f"/repos/{owner}/{name}/languages")
    tree_task = _gh_get(f"/repos/{owner}/{name}/git/trees/{repo_data.get('default_branch', 'main')}?recursive=1")
    readme_task = _gh_get(f"/repos/{owner}/{name}/readme")

    try:
        languages = await languages_task
    except Exception:
        languages = {}
    try:
        tree = await tree_task
    except Exception:
        tree = {"tree": []}
    try:
        readme = await readme_task
    except Exception:
        readme = None

    readme_text = ""
    if readme and readme.get("content"):
        try:
            readme_text = base64.b64decode(readme["content"]).decode("utf-8", errors="replace")[:6000]
        except Exception:
            readme_text = ""

    files = []
    for item in tree.get("tree", []):
        if item.get("type") == "blob":
            files.append(item.get("path", ""))

    return {
        "repo": f"{owner}/{name}",
        "name": repo_data.get("full_name"),
        "description": repo_data.get("description") or "",
        "stars": repo_data.get("stargazers_count", 0),
        "forks": repo_data.get("forks_count", 0),
        "open_issues": repo_data.get("open_issues_count", 0),
        "default_branch": repo_data.get("default_branch"),
        "license": (repo_data.get("license") or {}).get("spdx_id") if repo_data.get("license") else None,
        "homepage": repo_data.get("homepage") or "",
        "language": repo_data.get("language") or "",
        "languages": languages,
        "file_count": len(files),
        "sample_files": files[:80],
        "readme": readme_text,
        "url": repo_data.get("html_url"),
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }
