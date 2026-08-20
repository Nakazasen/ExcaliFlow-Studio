# ExcaliFlow Studio

Local-first code intelligence and presentation-ready diagrams.

## Current capabilities

- Graphify/Understand-aware codebase diagrams.
- Offline Mermaid + Panzoom viewer and editable `.excalidraw` export.
- Editorial SVG/HTML plus architecture, Sankey, Wardley, journey, KPI, funnel, timeline, quadrant, process, matrix, and risk visuals.

## Development layout

```text
src/excaliflow/       # stable package/CLI boundary
scripts/              # compatibility generator during migration
assets/vendor/         # pinned offline browser runtimes
tests/                 # deterministic generator and CLI tests
agents/                # skill metadata
```

## Run

```powershell
$env:PYTHONPATH = "$PWD/src"
py -3 -m excaliflow.cli --help
py -3 -m unittest discover -s tests -v
```

## Install for an AI host

After cloning and running `pip install -e .`, use a host name. The command prints the exact destination before you open the IDE:

```powershell
excaliflow install --host codex
excaliflow install --host antigravity
excaliflow install --host agy --workspace "D:\MyProject"
```

Use `excaliflow targets` to see every built-in destination on the current computer. The supported destinations are intentionally limited to published skill locations:

| Host | User destination | Workspace destination |
| --- | --- | --- |
| Codex | `~/.codex/skills/excaliflow` | use `--target` |
| Claude Code | `~/.claude/skills/excaliflow` | `.claude/skills/excaliflow` |
| GitHub Copilot / VS Code | `~/.copilot/skills/excaliflow` | `.github/skills/excaliflow` |
| Gemini CLI | `~/.gemini/skills/excaliflow` | `.gemini/skills/excaliflow` |
| OpenCode | `~/.config/opencode/skills/excaliflow` | `.opencode/skills/excaliflow` |
| Kiro IDE / CLI | `~/.kiro/skills/excaliflow` | `.kiro/skills/excaliflow` |
| AGY-compatible workspace | — | `.agents/skills/excaliflow` |

Antigravity Desktop remains supported through the verified local profile already present on this machine (`~/.gemini/config/skills/excaliflow`). It has no public, stable skill-path contract, so on a new computer the installer fails closed and asks for `--target` instead of inventing a directory.

For Cursor or any other IDE without a documented Agent Skills destination, make the destination explicit:

```powershell
excaliflow install --host custom --target "D:\MyIDE\skills\excaliflow"
```

Verify a host after installation:

```powershell
excaliflow doctor --host codex
excaliflow doctor --host antigravity
excaliflow doctor --host custom --target "D:\MyIDE\skills\excaliflow"
```

## Migration boundary

The package CLI deliberately calls the verified generator while the renderer and viewer are split into testable modules. This preserves existing installed-skill behavior; it is not yet a claim that the monolith has been fully removed.
