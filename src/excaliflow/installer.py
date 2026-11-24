"""Safe host adapters for installing the portable ExcaliFlow skill."""

from __future__ import annotations

import shutil
import json
import sys
import ast
import re
from importlib import metadata
from pathlib import Path
from urllib.parse import unquote, urlparse


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
    """Resolve a complete source/portable root across editable and wheel installs."""
    candidates = [Path(__file__).resolve().parents[2], Path(sys.prefix)]
    try:
        direct_url = metadata.distribution("excaliflow-studio").read_text("direct_url.json")
        if direct_url:
            parsed = urlparse(str(json.loads(direct_url).get("url", "")))
            if parsed.scheme == "file":
                path = unquote(parsed.path)
                if parsed.netloc:
                    path = f"//{parsed.netloc}{path}"
                elif sys.platform.startswith("win") and path.startswith("/"):
                    path = path[1:]
                candidates.insert(0, Path(path))
    except (metadata.PackageNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):
        pass
    for candidate in candidates:
        root = candidate.resolve()
        if (root / "scripts" / "generate_diagram.py").is_file() and (root / "assets" / "vendor").is_dir():
            return root
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
    return target, not doctor_issues(target)


def doctor_issues(target: Path) -> list[str]:
    """Return actionable integrity failures for one portable skill install."""
    required = (
        "VERSION",
        "SKILL.md",
        "scripts/generate_diagram.py",
        "src/excaliflow/__init__.py",
        "src/excaliflow/cli.py",
        "assets/vendor/mermaid.min.js",
        "assets/vendor/panzoom.min.js",
    )
    issues = [f"missing {name}" for name in required if not (target / name).is_file()]
    if issues:
        return issues
    try:
        version = (target / "VERSION").read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            issues.append(f"invalid VERSION: {version!r}")
        init_text = (target / "src" / "excaliflow" / "__init__.py").read_text(encoding="utf-8")
        ver_match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init_text, re.MULTILINE)
        if not ver_match or ver_match.group(1) != version:
            issues.append(f"version mismatch between VERSION ({version!r}) and __init__.py ({ver_match.group(1) if ver_match else None!r})")
        skill_text = (target / "SKILL.md").read_text(encoding="utf-8")
        if not skill_text.startswith("---\n") or "name: excaliflow" not in skill_text[:200]:
            issues.append("invalid SKILL.md frontmatter")
        py_files = [target / "scripts" / "generate_diagram.py", *sorted((target / "src" / "excaliflow").glob("*.py"))]
        for py_path in py_files:
            rel_py = py_path.relative_to(target).as_posix()
            ast.parse(py_path.read_text(encoding="utf-8"), filename=rel_py)
        for relative, marker in (("assets/vendor/mermaid.min.js", "mermaid"), ("assets/vendor/panzoom.min.js", "Panzoom")):
            content = (target / relative).read_text(encoding="utf-8")
            if len(content) < 1000 or marker not in content:
                issues.append(f"invalid offline asset: {relative}")
    except (OSError, UnicodeError, SyntaxError) as error:
        issues.append(str(error))
    return issues
