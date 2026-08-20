"""Safe host adapters for installing the portable ExcaliFlow skill."""

from __future__ import annotations

import shutil
from pathlib import Path


SKILL_CONTENT = ("SKILL.md", "THIRD_PARTY_LICENSES.md", "agents", "assets", "scripts", "tests")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_target(host: str, *, home: Path | None = None, workspace: Path | None = None) -> Path:
    base = home or Path.home()
    if host == "codex":
        return base / ".codex" / "skills" / "excaliflow"
    if host == "antigravity":
        return base / ".gemini" / "config" / "skills" / "excaliflow"
    if host == "agy":
        if workspace is None:
            raise ValueError("AGY installation requires --workspace PATH.")
        return workspace.resolve() / ".agents" / "skills" / "excaliflow"
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
