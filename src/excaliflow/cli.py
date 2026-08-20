"""Stable package entry point during the compatibility migration."""

from __future__ import annotations

import runpy
import sys
import argparse
from pathlib import Path

from excaliflow.installer import doctor, install_skill, resolve_target


def main() -> None:
    """Dispatch to the verified legacy generator without duplicating its behavior."""
    if len(sys.argv) > 1 and sys.argv[1] in {"install", "doctor"}:
        parser = argparse.ArgumentParser(prog="excaliflow", description="Install or verify the portable ExcaliFlow skill.")
        parser.add_argument("command", choices=("install", "doctor"))
        parser.add_argument("--host", choices=("codex", "antigravity", "agy"), required=True)
        parser.add_argument("--workspace", type=Path, help="Workspace used by the AGY project-skill adapter.")
        parser.add_argument("--target", type=Path, help="Explicit target for any IDE or desktop app.")
        args = parser.parse_args()
        target = args.target or resolve_target(args.host, workspace=args.workspace)
        if args.command == "install":
            print(f"Installed ExcaliFlow skill to: {install_skill(target)}")
        else:
            path, ready = doctor(args.host, workspace=args.workspace) if args.target is None else (target, (target / "scripts" / "generate_diagram.py").is_file())
            print(f"{args.host}: {'ready' if ready else 'not installed'} ({path})")
            if not ready:
                raise SystemExit(1)
        return
    repository_root = Path(__file__).resolve().parents[2]
    legacy_script = repository_root / "scripts" / "generate_diagram.py"
    if not legacy_script.is_file():
        raise SystemExit(f"ExcaliFlow generator is missing: {legacy_script}")
    sys.argv = [str(legacy_script), *sys.argv[1:]]
    runpy.run_path(str(legacy_script), run_name="__main__")


if __name__ == "__main__":
    main()
