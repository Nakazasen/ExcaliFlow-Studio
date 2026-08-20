"""Portable entry point for evidence-first ExcaliFlow codebase explanations."""

from __future__ import annotations

import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "src"))

from excaliflow.cli import main  # noqa: E402


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] != "ask":
        sys.argv.insert(1, "explain")
    main()
