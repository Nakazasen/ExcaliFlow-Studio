"""Stable package entry point during the compatibility migration."""

from __future__ import annotations

import runpy
import sys
import argparse
from pathlib import Path

from excaliflow.explorer import inspect_codebase, serialise_answer
from excaliflow.installer import HOSTS, USER_TARGETS, WORKSPACE_TARGETS, doctor, install_skill, resolve_target


def write_console(content: str) -> None:
    """Write UTF-8 safely when a legacy Windows console cannot encode Vietnamese."""
    try:
        print(content, end="")
    except UnicodeEncodeError:
        sys.stdout.buffer.write(content.encode("utf-8"))


def main() -> None:
    """Dispatch to the verified legacy generator without duplicating its behavior."""
    if len(sys.argv) > 1 and sys.argv[1] in {"explain", "ask"}:
        parser = argparse.ArgumentParser(prog="excaliflow", description="Explain a local codebase with source-backed evidence.")
        parser.add_argument("command", choices=("explain", "ask"))
        parser.add_argument("--dir", type=Path, default=Path.cwd(), help="Codebase directory to inspect.")
        parser.add_argument("--audience", choices=("engineer", "learner"), default="engineer", help="Explanation depth and vocabulary.")
        parser.add_argument("--question", help="Required for ask; use a symbol, file, import, dependency, or overview question.")
        parser.add_argument("--format", choices=("markdown", "json"), default="markdown", help="Output for people or another AI tool.")
        parser.add_argument("--out", type=Path, help="Optional file for the generated explanation or answer.")
        args = parser.parse_args()
        if args.command == "ask" and not args.question:
            parser.error("ask requires --question.")
        content = serialise_answer(inspect_codebase(args.dir), args.question, args.audience, args.format)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(content, encoding="utf-8")
            print(f"Wrote source-backed {args.command} output to: {args.out}")
        else:
            write_console(content)
        return
    if len(sys.argv) > 1 and sys.argv[1] in {"install", "doctor", "targets"}:
        parser = argparse.ArgumentParser(prog="excaliflow", description="Install or verify the portable ExcaliFlow skill.")
        parser.add_argument("command", choices=("install", "doctor", "targets"))
        parser.add_argument("--host", choices=HOSTS, help="AI host whose documented skill destination should be used.")
        parser.add_argument("--workspace", type=Path, help="Use the host's documented project skill destination in this workspace.")
        parser.add_argument("--target", type=Path, help="Exact destination for an unsupported or custom IDE.")
        args = parser.parse_args()
        if args.command == "targets":
            print("Documented user-scope destinations:")
            for host in USER_TARGETS:
                print(f"  {host}: {resolve_target(host)}")
            print("Documented workspace hosts: " + ", ".join(WORKSPACE_TARGETS))
            print("  antigravity: uses its verified local profile, otherwise pass --target PATH")
            print("  custom: always pass --target PATH")
            return
        if args.host is None:
            parser.error("--host is required for install and doctor.")
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
