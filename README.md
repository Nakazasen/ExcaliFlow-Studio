# ExcaliFlow Studio

<p align="center">
  <strong>Local-First Code Intelligence & Presentation-Ready Visual Architecture Engine</strong>
</p>

<p align="center">
  <a href="https://github.com/Nakazasen/ExcaliFlow-Studio/releases"><img src="https://img.shields.io/badge/version-v0.1.2-blue.svg" alt="Version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-brightgreen.svg" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-purple.svg" alt="License"></a>
  <a href="tests/"><img src="https://img.shields.io/badge/tests-47%2F47%20passing-success.svg" alt="Tests"></a>
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
- **🗺️ Interactive Codebase Atlas**: Explains what applications do, generates 1→2→3 reading paths, and visualizes native SVG dependency graphs.
- **🎨 Multi-Format Visual Artifacts**:
  - Offline HTML viewers with pan/zoom.
  - Native `.excalidraw` editable files.
  - High-res vector SVGs with Georgia/Arial typography for executive slides (16:9), whitepapers, and documents.
- **🧠 Smart Multi-Line Typography Engine**: Automatic word-boundary wrapping, dynamic vertical spacing, native SVG `<title>` tooltips, and right-edge clipping auto-anchoring.
- **🔍 Evidence-First Q&A**: Answers architectural questions with verified `file:line` citations directly from source code AST.
- **🔗 Evidence Graph for RAG**: Visualizes RAG retrieval traces (`rag-trace.json`) to audit and verify model claims against ground truth passages.
- **🤖 Universal AI Host Integration**: One-click skill installer for Codex, Claude Code, GitHub Copilot, Gemini CLI, Antigravity, OpenCode, and Cursor.

---

## 📦 Installation

### Option 1: Via `uv` (Recommended)

```powershell
# Install directly as a global tool from the local directory
uv tool install --editable "D:\Sandbox\ExcaliFlow Studio"

# Verify offline runtime
excaliflow --offline-check
```

### Option 2: Via `pip`

```powershell
git clone https://github.com/Nakazasen/ExcaliFlow-Studio.git
cd ExcaliFlow-Studio
pip install -e .
```

### Option 3: Windows One-Click Setup (Zero-Python)

Download `ExcaliFlow-Setup-windows.zip` from the [Latest GitHub Release](https://github.com/Nakazasen/ExcaliFlow-Studio/releases/latest), extract it, and double-click `ExcaliFlow-Setup.cmd`.

---

## ⚡ Fastest Way to Use: The `/excaliflow` AI Skill Dashboard

The **ExcaliFlow Agent Skill (`SKILL.md`) is bundled directly** in all installations. Once installed in your AI IDE (Antigravity, Claude Code, Cursor, GitHub Copilot, Gemini CLI, etc.):

1. Just type `/excaliflow` in the chat window.
2. The agent automatically presents the **Interactive Feature Dashboard Menu (v3.1)**:
   - `1` 🏢 **Architecture & Excalidraw**
   - `2` 🗺️ **Codebase Atlas (Explore & Learn Code)**
   - `3` 📊 **Editorial Diagrams (Wardley, Sankey, Journey, Slide)**
   - `4` 🔍 **Source-Backed Codebase Q&A**
   - `5` 🔗 **Evidence Graph for RAG**
   - `6` 🩺 **Atlas AI Bridge Doctor**
   - `7` 🔄 **Check for Updates**
3. Reply with a number (e.g. `1` or `2`) or a short description—**no need to memorize complex CLI flags!**

---

## 🔗 The Golden Workflow: Synergy with `/graphify`

> [!TIP]
> **Does ExcaliFlow work best with `/graphify`?**
> **YES!** While ExcaliFlow can scan raw source code AST on its own, pairing `/graphify` with `/excaliflow` forms the ultimate architectural visualization pipeline:
>
> 1. **Step 1 (`/graphify`)**: Analyzes the codebase to construct high-dimensional knowledge graphs with God-node detection, community clustering, and hyperedges (`graphify-out/graph.json`).
> 2. **Step 2 (`/excaliflow`)**: Automatically detects `graphify-out/graph.json`, parses semantic communities, and renders them into an interactive **Panzoom HTML Viewer** and an editable **Excalidraw canvas**!

```text
┌─────────────────┐       ┌───────────────────────┐       ┌──────────────────────────────┐
│  Your Codebase  │ ────> │ /graphify (Knowledge) │ ────> │ /excaliflow (Visual Studio)  │
│  (Source Files) │       │ graphify-out/graph.json│       │ Interactive HTML + Excalidraw│
└─────────────────┘       └───────────────────────┘       └──────────────────────────────┘
```

---

## 🛠️ Feature Modules & CLI Guide

| Feature Group | Description & Output | CLI Command |
| :--- | :--- | :--- |
| **1. Architecture & Excalidraw** | Scans codebase $\to$ Offline Panzoom HTML viewer + editable `.excalidraw` scene | `excaliflow --dir . --with-excalidraw --open` |
| **2. Codebase Atlas** | Interactive web guide with plain-language summary, reading path & module roles | `excaliflow open --dir .` |
| **3. Editorial & Presentation SVGs** | Presentation-grade SVGs (Wardley, Sankey, Journey, Architecture, KPI, Funnel, Risk) | `excaliflow --editorial-out out.svg --visual-type wardley --visual-data brief.json --canvas slide` |
| **4. Source-Backed Q&A** | Answers questions about classes/functions/imports with `file:line` citations | `excaliflow ask --dir . --audience engineer --question "..."` |
| **5. Evidence Graph for RAG** | Converts RAG retrieval logs into an interactive verification map | `excaliflow knowledge import` & `atlas` |
| **6. Atlas AI Bridge & Doctor** | Manages local sidecar bridges (`:8788`) and checks connection to Gemini Web2API (`:8081`) | `excaliflow bridge doctor --dir .` |
| **7. Update Checker** | Non-intrusive check against GitHub Releases for new updates | `excaliflow update check` |

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
├── docs/                   # Setup playbooks & architectural guides
├── examples/               # Sample briefs & RAG trace payloads
├── tests/                  # Deterministic test suite (47 tests)
├── SKILL.md                # AI Agent skill protocol definition (v3.1)
├── pyproject.toml          # Package configuration
└── VERSION                 # Semantic version file
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
Third-party bundled libraries are documented in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

