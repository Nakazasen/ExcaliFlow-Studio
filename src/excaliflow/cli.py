"""Stable package entry point during the compatibility migration."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    """Dispatch to the verified legacy generator without duplicating its behavior."""
    repository_root = Path(__file__).resolve().parents[2]
    legacy_script = repository_root / "scripts" / "generate_diagram.py"
    if not legacy_script.is_file():
        raise SystemExit(f"ExcaliFlow generator is missing: {legacy_script}")
    sys.argv = [str(legacy_script), *sys.argv[1:]]
    runpy.run_path(str(legacy_script), run_name="__main__")


if __name__ == "__main__":
    main()
