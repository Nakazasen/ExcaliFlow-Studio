# ExcaliFlow Studio

Local-first code intelligence and presentation-ready diagrams.

## Current capabilities

- Graphify/Understand-aware codebase diagrams.
- Offline Mermaid + Panzoom viewer and editable `.excalidraw` export.
- Editorial SVG/HTML plus architecture, Sankey, Wardley, journey, KPI, funnel, timeline, quadrant, process, matrix, and risk visuals.
- Evidence-first codebase guide and Q&A for both engineers and people learning to code.

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

## Explore and learn a codebase

Use the existing diagram command to see relationships, then use the same local source scan to explain the project or answer a focused question. `engineer` uses implementation vocabulary; `learner` explains the same evidence in beginner-friendly language.

```powershell
# A high-level learning guide, with file and line evidence
excaliflow explain --dir "D:\MyProject" --audience learner --out "D:\MyProject\CODEBASE_GUIDE.md"

# Ask about a class, function, file, imports, dependencies, or the architecture
excaliflow ask --dir "D:\MyProject" --audience engineer --question "What is UserService?"
excaliflow ask --dir "D:\MyProject" --audience learner --question "How do the imports connect?"
```

The answers are deterministic and source-backed: they identify matching declarations and import statements with file/line evidence. They intentionally do not claim to understand unsupported languages or infer behavior that is not visible in the scanned source.

## Codebase Atlas

`atlas` brings graph, explanation, and focused Q&A into one offline HTML file. Select a module to see its declarations; switch between engineer and learner vocabulary; then ask about a symbol or how imports connect. The Atlas has a native SVG graph and does not depend on Mermaid or any network runtime.

```powershell
excaliflow atlas --dir "D:\MyProject" --audience learner --out "D:\MyProject\codebase-atlas.html"
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

## Windows one-click setup

For a computer without Python, download `ExcaliFlow-Setup-windows.zip` from a release, extract it, then double-click `ExcaliFlow-Setup.cmd`. The small Windows dialog asks for the AI tool, shows the exact destination before copying anything, verifies the generator after installation, and needs neither Administrator permission nor a network download.

Maintainers create that release asset with:

```powershell
.\installers\build-windows-release.ps1
```

The generated `dist\ExcaliFlow-Setup-windows.zip` contains only the portable skill and the installer; it does not bundle Python or install a background service.

## Migration boundary

The package CLI deliberately calls the verified generator while the renderer and viewer are split into testable modules. This preserves existing installed-skill behavior; it is not yet a claim that the monolith has been fully removed.
