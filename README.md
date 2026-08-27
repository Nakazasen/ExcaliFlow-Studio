# ExcaliFlow Studio

<p align="center">
  <strong>Local-First Code Intelligence & Presentation-Ready Visual Architecture Engine</strong>
</p>

<p align="center">
  <a href="https://github.com/Nakazasen/ExcaliFlow-Studio/releases"><img src="https://img.shields.io/badge/version-v0.1.3-blue.svg" alt="Version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-brightgreen.svg" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-purple.svg" alt="License"></a>
  <a href="tests/"><img src="https://img.shields.io/badge/tests-64%2F64%20passing-success.svg" alt="Tests"></a>
  <a href="#key-highlights"><img src="https://img.shields.io/badge/offline-100%25%20zero%20cloud%20deps-orange.svg" alt="Offline Ready"></a>
</p>

<p align="center">
  <a href="README.md"><strong>English</strong></a> • <a href="README_VI.md"><strong>Tiếng Việt</strong></a>
</p>

---

## 🌟 Overview

**ExcaliFlow Studio** is a local-first toolkit designed for software engineers, architects, and learners to explore, understand, and visualize complex software codebases. It operates **100% locally and offline**, turning source code trees and knowledge graphs into interactive web atlases, editable `.excalidraw` scenes, presentation-grade SVG diagrams, and deterministic source-backed explanations.

---

## 🚀 Key Highlights

- **🔒 100% Local-First & Privacy-Preserving**: No telemetry, no cloud dependencies. Works completely in air-gapped environments.
- **⚡ Interactive Reach Tracing**: Click any node to instantly trace its callers (Upstream - Cyan) and dependencies (Downstream - Emerald) while dimming out-of-scope elements.
- **✨ Animated Signal Flow**: Toggle animated directional signal pulses along edges to visualize live data flows.
- **🔍 Architecture Change Comparison (Diff Engine)**: Compare two codebase snapshots or git commits to inspect added, removed, and modified architecture components before merging PRs (`--diff`).
- **🎴 1200×630 Social & README Share Card**: Generate standard 1200×630 vector presentation cards ready for project README headers and social embeds (`--share-card`).
- **🗺️ Interactive Codebase Atlas**: Explains what applications do, generates 1→2→3 reading paths, and visualizes native SVG dependency graphs.
- **🎨 Multi-Format Visual Artifacts**: Offline HTML viewers with pan/zoom, native `.excalidraw` editable files, and high-res vector SVGs.
- **🧠 Smart Multi-Line Typography Engine**: Automatic word-boundary wrapping, dynamic vertical spacing, native SVG `<title>` tooltips, and right-edge clipping auto-anchoring.
- **🔍 Evidence-First Q&A**: Answers architectural questions with verified `file:line` citations directly from source code AST.
- **🔗 Evidence Graph for RAG**: Visualizes RAG retrieval traces (`rag-trace.json`) to audit and verify model claims against ground truth passages.
- **🤖 Universal AI Host Integration**: One-click skill installer for Codex, Claude Code, GitHub Copilot, Gemini CLI, Antigravity, OpenCode, and Cursor.

---

## ⚡ 5-Second Quickstart (For Newcomers — Zero Setup!)

You **do not need any external tools or complex configuration** to visualize your codebase. ExcaliFlow works 100% standalone right out of the box:

### 1. Install ExcaliFlow
```bash
pip install -e .
# or via uv:
uv tool install --editable .
```

### 2. Run in any project directory
```bash
# Navigate to your project folder
cd /path/to/your/project

# Generate and instantly open your architecture diagram
excaliflow --open --with-excalidraw
```
🎉 **Boom!** Your browser opens immediately with an interactive Panzoom HTML architecture viewer and an editable `.excalidraw` canvas right beside your code!

---

## 💡 Standalone vs. Supercharged: Do I Need `/graphify`?

| Mode | How it Works | When to Use |
| :--- | :--- | :--- |
| 🚀 **Standalone Mode** *(Default — Zero Setup)* | ExcaliFlow automatically scans your code AST, directory structure, and import relations on its own. | You want an instant, beautiful architecture diagram of any project in 5 seconds without installing anything else. |
| ⚡ **Supercharged with `/graphify`** *(Optional Power-Up)* | **What is Graphify?** An open-source tool that extracts semantic knowledge graphs, detects central God-nodes, and clusters community hyperedges. If `graphify` is installed on your system, ExcaliFlow **automatically detects it** and renders deep multidimensional knowledge graphs without any extra configuration! | You have large, complex codebases and want AI-powered community detection and God-node structural analysis. |

ExcaliFlow accepts Graphify `>=0.9.48,<0.10`: patch updates remain available, while an unvalidated breaking minor release cannot silently enter the workflow. `uv.lock` intentionally records one exact version for reproducible development and CI. At runtime an incompatible CLI falls back to the internal AST scanner; `--strict` fails closed with an actionable install command.

```text
┌─────────────────────────┐       ┌──────────────────────────────────────┐       ┌──────────────────────────────┐
│  Your Codebase          │ ────> │  ExcaliFlow Standalone (AST / Code)  │ ────> │  Interactive HTML Viewer     │
│  (Python, JS, TS, etc.) │   │   └──────────────────────────────────────┘   │   │  (Reach Tracing + Flow Pulse)│
│                         │   │   ┌──────────────────────────────────────┐   │   │  + Editable .excalidraw Scene│
│                         │   └──>│  Optional: /graphify Knowledge Graph │───┘   │  + 1200x630 Share Card SVG   │
└─────────────────────────┘       └──────────────────────────────────────┘       └──────────────────────────────┘
```

---

## 🤖 Fastest Way for AI Agents: The `/excaliflow` Skill Dashboard

If you use AI IDEs / Coding Agents (**Antigravity, Codex, Cursor, Claude Code, GitHub Copilot, Gemini CLI**):

1. Type `/excaliflow` in your AI chat window.
2. The agent automatically presents the **1-Click Feature Dashboard Menu (v3.6)**:
   - `1` 🏢 **Architecture & Excalidraw (Reach Tracing + Flow Motion)**
   - `2` 🔍 **Architecture Diff Comparison (`--diff`)**
   - `3` 🎴 **1200×630 README Share Card (`--share-card`)**
   - `4` 🗺️ **Codebase Atlas (Explore & Learn Code)**
   - `5` 📊 **Editorial Diagrams (Wardley, Sankey, Journey, Slide)**
   - `6` 🔍 **Source-Backed Codebase Q&A**
   - `7` 🔗 **Evidence Graph for RAG**
   - `8` 🩺 **Atlas AI Bridge Lifecycle**
   - `9` 📖 **Atlas, Explain, Watch & Offline Check**
   - `10` 🧩 **Install/Doctor for AI Hosts**
   - `11` 🔄 **Check for Updates**
3. Reply with a number (e.g. `1` or `2`) or a short description—**no need to memorize complex CLI flags!**

---

## 🛠️ Feature Modules & CLI Guide

| Feature Group | Description & Output | CLI Command |
| :--- | :--- | :--- |
| **1. Architecture & Excalidraw** | Scans codebase $\to$ Offline Panzoom HTML viewer (Reach Tracing + Animated Flow) + `.excalidraw` | `excaliflow --dir . --with-excalidraw --open` |
| **2. Architecture Diff Engine** | Compares current architecture with previous snapshot or git commit | `excaliflow --diff HEAD~1 --open` |
| **3. 1200×630 Share Card** | Generates 1200×630 vector card for README and social sharing | `excaliflow --share-card "README_CARD.svg" --open` |
| **4. Codebase Atlas** | Interactive web guide with plain-language summary, reading path & module roles | `excaliflow open --dir .` |
| **5. Editorial & Presentation SVGs** | Presentation-grade SVGs (Wardley, Sankey, Journey, Architecture, KPI, Funnel, Risk) | `excaliflow --editorial-out out.svg --visual-type wardley --visual-data brief.json --canvas slide` |
| **6. Source-Backed Q&A** | Answers questions about classes/functions/imports with `file:line` citations | `excaliflow ask --dir . --audience engineer --question "..."` |
| **7. Evidence Graph for RAG** | Converts RAG retrieval logs into an interactive verification map | `excaliflow knowledge import` & `atlas` |
| **8. Atlas AI Bridge Lifecycle** | Manages Atlas Bridge (`:8788`), optional AIOS IDE bridge (`:8585`), and Gemini Web2API (`:8081`) | `excaliflow bridge init/start/doctor --dir .` |
| **9. Atlas, Explain & Monitoring** | Generates Atlas/guides, watches source changes, and verifies offline assets | `excaliflow atlas`, `explain`, `--watch`, `--offline-check` |
| **10. AI Host Installation** | Lists targets, installs, and diagnoses portable skills for supported AI hosts | `excaliflow targets/install/doctor` |
| **11. Update Checker** | Non-intrusive check against GitHub Releases for new updates | `excaliflow update check` |

---

### 1. Codebase Architecture & Excalidraw

Scans directory AST or Graphify knowledge graphs (`graphify-out/graph.json`) and generates a standalone interactive viewer:

```powershell
# Generate HTML viewer and editable .excalidraw scene
excaliflow --dir "D:\MyProject" --with-excalidraw --out "D:\MyProject\architecture.html" --open

# Listen to file changes and auto-regenerate
excaliflow --dir "D:\MyProject" --watch
```

---

### 2. Codebase Atlas (Interactive Onboarding)

Built for onboarding and understanding unfamiliar codebases without reading hundreds of files:

```powershell
# Open Codebase Atlas in browser
excaliflow open --dir "D:\MyProject"

# Generate static Atlas HTML file
excaliflow atlas --dir "D:\MyProject" --audience learner --out "D:\MyProject\codebase-atlas.html"
```

- **What does this app do?**: Clear, factual summary derived from entry points and manifest files.
- **1-2-3 Reading Path**: Sequenced recommendations for where a developer should begin reading.
- **Module Responsibilities**: Grouped core components with evidence links.

---

### 3. Editorial & Business Diagrams

Generates clean, publication-ready vector SVGs (and standalone HTML wrappers) designed for 16:9 presentation slides, whitepapers, and documents:

```powershell
# Wardley Map (Value chain & technology evolution)
excaliflow --editorial-out "wardley.svg" --visual-type wardley --visual-data "brief.json" --canvas slide

# Sankey Flow Diagram
excaliflow --editorial-out "sankey.svg" --visual-type sankey --visual-data "brief.json" --canvas document

# User Journey Map
excaliflow --editorial-out "journey.svg" --visual-type journey --visual-data "brief.json" --canvas slide

# Business Reports (kpi, funnel, timeline, process, quadrant, matrix, risk)
excaliflow --editorial-out "kpi.svg" --visual-type kpi --visual-data "kpi-data.json" --canvas slide
```

Supported visual types (`--visual-type`):
`architecture` • `wardley` • `sankey` • `journey` • `kpi` • `funnel` • `timeline` • `process` • `quadrant` • `matrix` • `risk`

---

### 4. Source-Backed Codebase Q&A

Ask specific questions and receive deterministic answers citing exact code locations:

```powershell
# For engineers (technical implementation details):
excaliflow ask --dir "D:\MyProject" --audience engineer --question "What does UserService do?"

# For beginners / learners (high-level architectural explanation):
excaliflow ask --dir "D:\MyProject" --audience learner --question "How do the components communicate?"

# Generate comprehensive markdown learning guide:
excaliflow explain --dir "D:\MyProject" --audience learner --out "D:\MyProject\CODEBASE_GUIDE.md"
```

---

### 5. Evidence Graph for RAG

Audit RAG answers and verify factual claims against retrieved chunks:

```powershell
# 1. Convert RAG retrieval output into canonical evidence graph
excaliflow knowledge import --trace ".\examples\rag-trace.json" --out ".\evidence-graph.json"

# 2. Render self-contained Evidence Atlas HTML
excaliflow knowledge atlas --graph ".\evidence-graph.json" --out ".\evidence-atlas.html"
```

---

### 6. Atlas AI Bridge & Diagnostics

Connects local AI backends (e.g. Antigravity Sidecar `:8585` or local [Gemini Web2API](https://github.com/Sophomoresty/gemini-web2api) `:8081`):

```powershell
# Initialize bridge manifest (.excaliflow/ide-bridge.json)
excaliflow bridge init --dir "D:\MyProject"

# Start loopback bridge server (bound strictly to 127.0.0.1:8788)
excaliflow bridge start --dir "D:\MyProject"

# Diagnose connection health
excaliflow bridge doctor --dir "D:\MyProject"
```

---

### 7. Universal AI Host Skill Installer

Install ExcaliFlow as a native skill into your preferred AI agent environment:

```powershell
# Check supported skill targets
excaliflow targets

# Install for specific AI host
excaliflow install --host claude       # Claude Code
excaliflow install --host antigravity   # Google Antigravity
excaliflow install --host copilot       # GitHub Copilot
excaliflow install --host codex         # OpenAI Codex
excaliflow install --host gemini        # Gemini CLI
excaliflow install --host custom --target "D:\Path\To\Skills\excaliflow"
```

---

## 🧪 Testing & Verification

ExcaliFlow Studio enforces rigorous unit testing covering offline rendering, CLI arguments, SVG parsing, and typography limits:

```powershell
# Run the complete test suite
uv run python -m unittest discover -s tests -v

# Check offline runtime assets (Mermaid & Panzoom)
uv run excaliflow --offline-check
```

---

## 📁 Repository Structure

```text
ExcaliFlow-Studio/
├── src/excaliflow/         # Core package, CLI dispatchers, and Atlas engine
│   ├── cli.py              # CLI entry point
│   ├── atlas.py            # Interactive Codebase Atlas renderer
│   ├── bridge_server.py    # Local loopback AI bridge
│   ├── explorer.py         # Source scan AST & evidence Q&A engine
│   ├── knowledge.py        # RAG evidence graph processor
│   └── installer.py        # Universal AI agent skill installer
├── scripts/
│   └── generate_diagram.py # Universal architecture & editorial diagram generator
├── assets/vendor/          # Pinned offline JavaScript runtimes (Mermaid, Panzoom)
├── docs/                   # Setup playbooks & Maintenance manuals (maintenance-and-architecture.md)
├── examples/               # Sample briefs & RAG trace payloads
├── tests/                  # Deterministic test suite (65 tests)
├── SKILL.md                # AI Agent skill protocol definition (v3.6)
├── pyproject.toml          # Package configuration
└── VERSION                 # Semantic version file (0.1.3)
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
Third-party bundled libraries are documented in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
