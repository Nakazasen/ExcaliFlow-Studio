"""Safe host adapters for installing the portable ExcaliFlow skill."""

from __future__ import annotations

import shutil
from pathlib import Path


SKILL_CONTENT = ("VERSION", "SKILL.md", "THIRD_PARTY_LICENSES.md", "agents", "assets", "docs", "scripts", "src", "tests")

# Each entry is a documented, native Agent Skills destination.  Keep this map
# intentionally small: an unknown IDE must use the explicit --target option.
USER_TARGETS = {
    "codex": (".codex", "skills"),
    "claude": (".claude", "skills"),
    "copilot": (".copilot", "skills"),
    "gemini": (".gemini", "skills"),
    "opencode": (".config", "opencode", "skills"),
    "kiro": (".kiro", "skills"),
}

WORKSPACE_TARGETS = {
    "agy": (".agents", "skills"),
    "claude": (".claude", "skills"),
    "copilot": (".github", "skills"),
    "gemini": (".gemini", "skills"),
    "opencode": (".opencode", "skills"),
    "kiro": (".kiro", "skills"),
}

HOSTS = tuple(sorted({*USER_TARGETS, *WORKSPACE_TARGETS, "antigravity", "agy", "custom"}))


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_target(host: str, *, home: Path | None = None, workspace: Path | None = None) -> Path:
    base = home or Path.home()
    if host == "custom":
        raise ValueError("Custom IDE installation requires --target PATH.")
    if host == "antigravity":
        # Antigravity Desktop has no published, stable skill location.  Only
        # reuse its verified local profile path; otherwise demand --target.
        configured = base / ".gemini" / "config" / "skills"
        if configured.is_dir():
            return configured / "excaliflow"
        raise ValueError("Antigravity Desktop needs --target PATH on this machine.")
    if workspace is not None:
        destination = WORKSPACE_TARGETS.get(host)
        if destination is None:
            raise ValueError(f"{host} has no documented workspace skill destination; use --target PATH.")
        return workspace.resolve().joinpath(*destination, "excaliflow")
    destination = USER_TARGETS.get(host)
    if destination is not None:
        return base.joinpath(*destination, "excaliflow")
    if host == "agy":
        raise ValueError("AGY installation requires --workspace PATH.")
    raise ValueError(f"Unsupported host: {host}.")


def install_skill(target: Path, *, source: Path | None = None) -> Path:
    root = source or repository_root()
    missing = [name for name in SKILL_CONTENT if not (root / name).exists()]
    if missing:
        raise FileNotFoundError(f"Portable skill is incomplete: {', '.join(missing)}")
    target.mkdir(parents=True, exist_ok=True)
    for name in SKILL_CONTENT:
        origin, destination = root / name, target / name
        if origin.is_dir():
            shutil.copytree(origin, destination, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(origin, destination)
    return target


def doctor(host: str, *, home: Path | None = None, workspace: Path | None = None) -> tuple[Path, bool]:
    target = resolve_target(host, home=home, workspace=workspace)
    return target, (target / "scripts" / "generate_diagram.py").is_file()
