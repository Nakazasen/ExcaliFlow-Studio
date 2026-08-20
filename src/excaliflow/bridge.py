"""Discover local, user-owned IDE AI bridges without starting or configuring them."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
AIOS_MARKERS = (
    "src/aios_habit/antigravity_bridge.py",
    "scripts/antigravity_sidecar_daemon.py",
)


def _local_http_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in LOCAL_HOSTS or parsed.username or parsed.password:
        return None
    return value.rstrip("/")


def _manifest_bridge(project_dir: Path) -> dict | None:
    manifest = project_dir / ".excaliflow" / "ide-bridge.json"
    if not manifest.is_file():
        return None
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"detected": False, "reason": "IDE Bridge manifest is invalid JSON."}
    health_url = _local_http_url(raw.get("health_url"))
    completion_url = _local_http_url(raw.get("completion_url"))
    if not health_url or not completion_url:
        return {
            "detected": False,
            "reason": "IDE Bridge manifest must use localhost HTTP health_url and completion_url values.",
        }
    return {
        "detected": True,
        "name": str(raw.get("name") or "Local IDE Bridge"),
        "health_url": health_url,
        "completion_url": completion_url,
        "model": str(raw.get("model") or "local-ide-bridge"),
        "detected_by": ".excaliflow/ide-bridge.json",
    }


def discover_ide_bridge(project_dir: str | Path) -> dict:
    """Return a safe browser bridge config, without making a network request.

    Atlas only accepts loopback HTTP URLs. The browser performs a health check and
    sends requests only after the user asks a question.
    """
    root = Path(project_dir)
    manifest = _manifest_bridge(root)
    if manifest is not None:
        return manifest
    if all((root / marker).is_file() for marker in AIOS_MARKERS):
        return {
            "detected": True,
            "name": "Antigravity IDE Bridge",
            "health_url": "http://127.0.0.1:8585/health",
            "completion_url": "http://127.0.0.1:8585/v1/chat/completions",
            "model": "antigravity-brain-pro",
            "detected_by": "AIOS WorkLens bridge markers",
        }
    return {"detected": False, "reason": "No supported local IDE Bridge was detected in this codebase."}
