"""Explicit, unsigned release-notification checks for portable ExcaliFlow installs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_MANIFEST_URL = "https://github.com/Nakazasen/ExcaliFlow-Studio/releases/latest/download/update.json"
MANIFEST_SCHEMA = "excaliflow-update/v1"
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class UpdateCheckError(ValueError):
    """Raised for invalid local version or release-manifest data."""


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = _SEMVER.fullmatch(value.strip())
    if not match:
        raise UpdateCheckError(f"Version must be stable SemVer X.Y.Z, got: {value!r}.")
    return tuple(int(part) for part in match.groups())


def current_version(root: str | Path) -> str:
    """Read the version receipt copied alongside a portable installed skill."""

    receipt = Path(root) / "VERSION"
    try:
        version = receipt.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise UpdateCheckError(f"Installed VERSION receipt is unavailable: {receipt}.") from error
    _version_tuple(version)
    return version


def _is_loopback_http(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def _validate_manifest_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.netloc:
        return
    if _is_loopback_http(url):
        return
    raise UpdateCheckError("Update manifest URL must use HTTPS (HTTP is allowed only for localhost testing).")


def _validate_https_url(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise UpdateCheckError(f"Update manifest {field} must be a non-empty HTTPS URL.")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise UpdateCheckError(f"Update manifest {field} must be an HTTPS URL.")
    return value


def _validate_manifest(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise UpdateCheckError("Update manifest must be a JSON object.")
    if value.get("schema_version") != MANIFEST_SCHEMA:
        raise UpdateCheckError(f"Update manifest schema_version must be {MANIFEST_SCHEMA}.")
    version = value.get("version")
    if not isinstance(version, str):
        raise UpdateCheckError("Update manifest version must be text.")
    _version_tuple(version)
    return {
        "version": version,
        "release_notes_url": _validate_https_url(value.get("release_notes_url"), "release_notes_url"),
        "asset_url": _validate_https_url(value.get("asset_url"), "asset_url"),
    }


def _fetch_manifest(url: str, timeout: float) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "ExcaliFlow-Update-Check"})
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise UpdateCheckError(f"Update server returned HTTP {response.status}.")
            return json.loads(response.read().decode("utf-8"))
    except (URLError, OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise UpdateCheckError(f"Could not check for updates: {error}.") from error


def check_for_update(
    root: str | Path,
    *,
    manifest_url: str = DEFAULT_MANIFEST_URL,
    timeout: float = 5.0,
    fetch: Callable[[str, float], dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Check one manifest on demand and never change local installed files."""

    try:
        current = current_version(root)
        _validate_manifest_url(manifest_url)
        manifest = _validate_manifest((fetch or _fetch_manifest)(manifest_url, timeout))
        latest = manifest["version"]
    except (UpdateCheckError, OSError, ValueError) as error:
        return {"status": "unavailable", "message": str(error)}
    status = "update_available" if _version_tuple(latest) > _version_tuple(current) else "up_to_date"
    return {
        "status": status,
        "current_version": current,
        "latest_version": latest,
        "release_notes_url": manifest["release_notes_url"],
        "asset_url": manifest["asset_url"],
    }
