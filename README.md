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

## Bắt đầu cho người không viết code

Không cần biết `--out`, Mermaid, Excalidraw hay AI Bridge. Sau khi cài skill, double-click `scripts\Open-ExcaliFlow.cmd`, chọn thư mục project, và Atlas sẽ mở trong trình duyệt ở chế độ **Học codebase**. Bản đồ, câu hỏi mẫu và giải thích từ mã nguồn đã hoạt động ngay cả khi chưa cấu hình AI.

Người dùng thích dùng terminal hoặc AI agent chỉ cần một lệnh:

```powershell
excaliflow open --dir "D:\MyProject"
```

File tạo ra là `.excaliflow\atlas.html` trong project. Phần AI Bridge, port và Gemini chỉ dành cho lúc người dùng chủ động cần câu trả lời AI; xem `excaliflow bridge doctor` khi gặp vấn đề.

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

`atlas` now opens in **Học codebase** mode: a plain-language answer to “Ứng dụng này làm gì?”, 1→2→3 reading path, 3–4 evidence-based responsibility blocks, translated terms, and sample questions. It does not infer business behavior: responsibility blocks use only source path/name hints and say so in the UI. **Full codebase** remains one click away and shows every scanned source file plus its proven internal import relationships. `Engineer mode` is opt-in. The Atlas uses a native SVG graph and does not depend on Mermaid or any network runtime.

If the inspected repository already exposes a supported local IDE Bridge, Atlas uses it first for questions and shows that source in the UI. AIOS WorkLens is recognised through its existing Antigravity sidecar contract (`127.0.0.1:8585`); Atlas checks `/health`, then calls its OpenAI-compatible completion endpoint only when a user asks. It never starts a sidecar, sends to a remote URL, or labels a fallback answer as AI. Other projects can opt in with `.excaliflow/ide-bridge.json` containing loopback-only `health_url`, `completion_url`, optional `name`, and optional `model`.

Atlas also probes a locally running [Gemini Web2API](https://github.com/Sophomoresty/gemini-web2api) server after the project bridge: `http://127.0.0.1:8081/v1/models` then `/v1/chat/completions` with `gemini-3.6-flash`. This is an optional external-processing source, not an offline model: its UI label explicitly says the question and structural scan context go through the local proxy to Gemini. Atlas does not install, start, store credentials for, or bypass authentication on this server. For safer local exposure, configure that server to bind `127.0.0.1`, keep `api_keys` empty for browser use, and use only with source context you permit to leave the machine.

## Create a Bridge for any repository

When a repository does not already expose an IDE Bridge, create a project-local **ExcaliFlow Atlas Bridge**. It binds only to `127.0.0.1:8788`, exposes the same health and OpenAI-compatible chat endpoints Atlas expects, and forwards only to a local Gemini Web2API server at `127.0.0.1:8081`. It never starts Gemini Web2API itself.

```powershell
# Creates .excaliflow/ide-bridge.json without overwriting an existing bridge.
excaliflow bridge init --dir "D:\MyProject"

# Starts the bridge; `start` creates the manifest first if it is missing.
excaliflow bridge start --dir "D:\MyProject"

# Or create the manifest alongside an Atlas output.
excaliflow atlas --dir "D:\MyProject" --create-bridge --out "D:\MyProject\codebase-atlas.html"
```

```powershell
excaliflow atlas --dir "D:\MyProject" --audience learner --out "D:\MyProject\codebase-atlas.html"
```

Run `excaliflow bridge doctor --dir "D:\MyProject" --port 8789` whenever setup is uncertain: it reports the project manifest, Gemini Web2API upstream, and Atlas Bridge separately, then prints the next safe action. The complete reusable setup, privacy boundary, verification, and troubleshooting procedure is in [the Atlas AI Runtime Playbook](docs/atlas-gemini-web2api.md); it is included when the skill is installed into another AI host.

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

For a computer without Python, download `ExcaliFlow-Setup-windows.zip` from the [latest GitHub Release](https://github.com/Nakazasen/ExcaliFlow-Studio/releases/latest), extract it, then double-click `ExcaliFlow-Setup.cmd`. The small Windows dialog asks for the AI tool, shows the exact destination before copying anything, verifies the generator after installation, and needs neither Administrator permission nor a network download.

Maintainers create that release asset with:

```powershell
.\installers\build-windows-release.ps1
```

The generated `dist\ExcaliFlow-Setup-windows.zip` contains only the portable skill and the installer; it does not bundle Python or install a background service.

Every pushed version tag matching `v*` now runs the Windows release workflow: it tests the tagged commit, builds the ZIP, creates or updates its GitHub Release, and replaces the release asset. To publish the first version, tag the intended commit (for example `v0.1.0`) and push that tag.

The same workflow publishes `ExcaliFlow-Setup-windows.exe` only when signing is configured. Add `WINDOWS_SIGNING_PFX_BASE64` and `WINDOWS_SIGNING_PFX_PASSWORD` as GitHub Actions secrets, and `WINDOWS_TIMESTAMP_URL` as a repository variable. The pipeline then signs with SHA-256, RFC 3161 timestamps the EXE, verifies its Authenticode signature, and uploads it. Without all three values it deliberately publishes no EXE, rather than presenting an unsigned binary as trusted.

## Migration boundary

The package CLI deliberately calls the verified generator while the renderer and viewer are split into testable modules. This preserves existing installed-skill behavior; it is not yet a claim that the monolith has been fully removed.
