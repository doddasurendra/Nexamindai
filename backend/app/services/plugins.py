"""Plugin Center: 5 free AI plugins from the '5 Free AI Plugins for Claude' catalogue,
with real environment detection — install status, how to connect, and what NexaMind can use."""
from __future__ import annotations

import importlib
import os
import shutil
from typing import Any

from ..config import get_settings

settings = get_settings()

PLUGINS: list[dict[str, Any]] = [
    {
        "id": "freellmapi",
        "name": "FreeLLMAPI",
        "fixes": "Usage limits",
        "problem": "Pools free tiers of many AI providers behind one OpenAI-compatible endpoint with automatic failover between models. Works with Claude Code.",
        "repo": "https://github.com/tashfeenahmed/freellmapi",
        "docs": "https://github.com/tashfeenahmed/freellmapi#readme",
        "type": "llm-proxy",
        "install_steps": [
            "git clone https://github.com/tashfeenahmed/freellmapi.git",
            "cd freellmapi && copy .env.example .env  (fill in free provider keys)",
            "npm install && npm run dev",
        ],
        "env_vars": ["FREELMAPI_BASE_URL", "FREELMAPI_API_KEY", "FREELMAPI_MODEL"],
        "aI_note": "NexaMind can use it as a model provider once FREELMAPI_BASE_URL is set (e.g. http://localhost:3001/v1).",
    },
    {
        "id": "lemo-opuscar",
        "name": "Lemo-Opuscar",
        "fixes": "Video creation",
        "problem": "Claude Code skill that makes short animated films in dozens of styles, entirely in code.",
        "repo": "https://github.com/lemomo-ai/lemo-opuscar",
        "docs": "https://github.com/lemomo-ai/lemo-opuscar#readme",
        "type": "claude-code-skill",
        "install_steps": [
            "claude plugin marketplace add lemomo-ai/lemo-opuscar",
            "claude plugin install lemo-opuscar@lemolab",
        ],
        "env_vars": [],
        "aI_note": "Runs inside Claude Code (animated films via code). NexaMind lists it as an available video-creation skill; it cannot be executed by the NexaMind backend.",
    },
    {
        "id": "ponytail",
        "name": "Ponytail",
        "fixes": "Over-engineering",
        "problem": "Stops coding agents from over-engineering, so Claude writes less code and uses fewer tokens.",
        "repo": "https://github.com/DietrichGebert/ponytail",
        "docs": "https://github.com/DietrichGebert/ponytail#readme",
        "type": "claude-code-skill",
        "install_steps": [
            "/plugin marketplace add DietrichGebert/ponytail",
            "/plugin install ponytail@ponytail",
        ],
        "env_vars": [],
        "aI_note": "Runs inside Claude Code as a skill. NexaMind lists it as an available token-saving coding skill; it cannot be executed by the NexaMind backend.",
    },
    {
        "id": "agent-reach",
        "name": "Agent Reach",
        "fixes": "Web access",
        "problem": "Gives an AI agent read and search access to the web: Twitter/X, Reddit, YouTube, GitHub and more — without paid APIs.",
        "repo": "https://github.com/Panniantong/Agent-Reach",
        "docs": "https://github.com/Panniantong/Agent-Reach#readme",
        "type": "cli-tool",
        "install_steps": [
            "git clone https://github.com/Panniantong/Agent-Reach.git",
            "cd Agent-Reach && npm install && npm link   (or follow its README)",
            "agent-reach doctor --text",
        ],
        "env_vars": [],
        "aI_note": "NexaMind can call `agent-reach read <url>` if the CLI is installed (see /api/plugins/agent-reach/read).",
    },
    {
        "id": "skillspector",
        "name": "NVIDIA SkillSpector",
        "fixes": "Security",
        "problem": "Open-source scanner that checks an AI agent skill for risky instructions, hidden code or malware before you install it.",
        "repo": "https://github.com/NVIDIA/skillspector",
        "docs": "https://docs.nvidia.com/skills/scanning-agent-skills",
        "type": "security-scanner",
        "install_steps": [
            "pip install skillspector",
            "skillspector scan --help    (scan an agent skill before installing)",
        ],
        "env_vars": [],
        "aI_note": "Runs before installing any of the above plugins. NexaMind detects it and lists it as the security gate for the plugin flow.",
    },
]


def _claude_plugin_dirs() -> list[str]:
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".claude", "plugins"),
        os.path.join(home, ".config", "claude", "plugins"),
        os.path.join(home, ".agents", "plugins"),
    ]
    return [path for path in candidates if os.path.isdir(path)]


def _skillspector_installed() -> bool:
    try:
        importlib.import_module("skillspector")
        return True
    except Exception:
        return bool(shutil.which("skillspector"))


def _claude_skill_installed(skill: str) -> bool:
    for base in _claude_plugin_dirs():
        for root, dirs, files in os.walk(base):
            if skill in (item.lower() for item in dirs) or any(skill in f.lower() for f in files):
                return True
    return False


def _freellmapi_status() -> str:
    if not settings.freellmapi_base_url:
        return "not-configured"
    # Best-effort health check; keep it cheap and non-fatal.
    try:
        import urllib.request
        req = urllib.request.Request(settings.freellmapi_base_url.rstrip("/") + "/models", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return "ready" if resp.status < 400 else "unreachable"
    except Exception:
        return "configured-but-unreachable"


def detect(plugin_id: str) -> dict[str, Any]:
    plugin = next((p for p in PLUGINS if p["id"] == plugin_id), None)
    if plugin is None:
        raise KeyError(plugin_id)

    if plugin_id == "freellmapi":
        status = _freellmapi_status()
    elif plugin_id == "agent-reach":
        status = "ready" if shutil.which("agent-reach") else "not-installed"
    elif plugin_id == "skillspector":
        status = "ready" if _skillspector_installed() else "not-installed"
    elif plugin_id in {"lemo-opuscar", "ponytail"}:
        status = "installed" if _claude_skill_installed(plugin_id) else "available (claude code skill)"
    else:
        status = "unknown"
    return {**plugin, "status": status}


def catalog() -> list[dict[str, Any]]:
    return [detect(p["id"]) for p in PLUGINS]
