"""Stable package entry point during the compatibility migration."""

from __future__ import annotations

import runpy
import sys
import argparse
from pathlib import Path

from excaliflow.atlas import write_atlas
from excaliflow.bridge_server import DEFAULT_PORT, DEFAULT_UPSTREAM, bridge_status, initialize_bridge, serve_bridge
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
    if len(sys.argv) > 1 and sys.argv[1] == "bridge":
        parser = argparse.ArgumentParser(prog="excaliflow", description="Create or run a loopback-only Atlas Bridge for a codebase.")
        parser.add_argument("command", choices=("init", "serve", "start", "doctor"))
        parser.add_argument("--dir", type=Path, default=Path.cwd(), help="Codebase directory that owns the bridge manifest.")
        parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Loopback port for the Atlas Bridge.")
        parser.add_argument("--upstream", default=DEFAULT_UPSTREAM, help="Loopback OpenAI-compatible upstream, usually Gemini Web2API.")
        args = parser.parse_args(sys.argv[2:])
        if args.command == "init":
            print(f"Created Atlas Bridge manifest: {initialize_bridge(args.dir, port=args.port)}")
            return
        if args.command == "doctor":
            status = bridge_status(args.dir, upstream_url=args.upstream, port=args.port)
            print("Atlas Bridge doctor")
            print(f"- Project manifest: {'ready' if status['manifest_ready'] else 'missing or invalid'} ({status['manifest']})")
            print(f"- Gemini Web2API: {'ready' if status['upstream_ready'] else 'not responding'} ({status['upstream_url']})")
            print(f"- Atlas Bridge: {'ready' if status['bridge_ready'] else 'not responding'} ({status['bridge_url']})")
            print(f"Next: {status['next_action']}")
            return
        if args.command == "start":
            manifest = args.dir / ".excaliflow" / "ide-bridge.json"
            if not manifest.exists():
                print(f"Created Atlas Bridge manifest: {initialize_bridge(args.dir, port=args.port)}")
        serve_bridge(args.upstream, port=args.port)
        return
    if len(sys.argv) > 1 and sys.argv[1] == "atlas":
        parser = argparse.ArgumentParser(prog="excaliflow", description="Create an offline Codebase Atlas with graph, explanation, and local Q&A.")
        parser.add_argument("command", choices=("atlas",))
        parser.add_argument("--dir", type=Path, default=Path.cwd(), help="Codebase directory to inspect.")
        parser.add_argument("--audience", choices=("engineer", "learner"), default="learner", help="Default vocabulary when opening Full codebase; Atlas opens in learner mode.")
        parser.add_argument("--create-bridge", action="store_true", help="Create the project Atlas Bridge manifest before writing the Atlas; does not start a server.")
        parser.add_argument("--out", type=Path, default=Path("codebase-atlas.html"), help="Offline HTML output path.")
        args = parser.parse_args()
        if args.create_bridge:
            print(f"Created Atlas Bridge manifest: {initialize_bridge(args.dir)}")
        output = write_atlas(args.dir, args.out, args.audience)
        print(f"Wrote offline Codebase Atlas to: {output}")
        return
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
