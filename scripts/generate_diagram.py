#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
Excali-Flow v2: Universal Architecture & Diagram Generator (Mermaid -> Excalidraw)
Tự động quét cấu trúc bất kỳ dự án nào (Python, Node.js, Go, Rust, v.v.),
tích hợp phân tích Đồ thị tri thức (Graphify / Knowledge Graph),
tạo sơ đồ kiến trúc Mermaid phong cách vẽ tay Excalidraw và xuất ra giao diện
Web tương tác độc lập (Standalone Single-File HTML) với Pan/Zoom (Panzoom v4.5.1),
Collapsible Sidebar (Ctrl+B), Live Editor, Export PNG 2x / SVG Vector.
=============================================================================
"""

import os
import sys
import re
import time
import ast
import json
import webbrowser
import argparse
import hashlib
import uuid
import math
import subprocess
import shutil
import tempfile
from html import escape as xml_escape
from pathlib import Path, PurePosixPath

SKILL_ROOT = Path(__file__).resolve().parents[1]
VENDOR_DIR = SKILL_ROOT / "assets" / "vendor"
RUNTIME_ASSETS = {
    "mermaid": (VENDOR_DIR / "mermaid.min.js", "mermaid"),
    "panzoom": (VENDOR_DIR / "panzoom.min.js", "Panzoom"),
}

EDITORIAL_CANVASES = {
    "document": (1400, 900),
    "slide": (1600, 900),
    "social": (1200, 1200),
}
EDITORIAL_TYPES = {"architecture", "sankey", "wardley", "journey"}
REPORT_TYPES = {"kpi", "funnel", "timeline", "quadrant", "process", "matrix", "risk"}

# Graphify is pre-1.0, so a minor release may contain breaking changes. Allow
# compatible patch upgrades while requiring an ExcaliFlow validation before
# crossing into the next minor series.
GRAPHIFY_MIN_VERSION = (0, 9, 48)
GRAPHIFY_MAX_VERSION = (0, 10, 0)
GRAPHIFY_VERSION_SPEC = ">=0.9.48,<0.10"
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs"}
WATCH_CONFIG_NAMES = {"pyproject.toml", "package.json", "go.mod", "Cargo.toml"}
WATCH_EXCLUDED_DIRS = {
    ".git", ".excaliflow", ".venv", "venv", "__pycache__", "build", "dist",
    "graphify-out", "node_modules", "target",
}


class EditorialValidationError(ValueError):
    """Raised when a visual brief cannot truthfully produce an editorial artifact."""

# Đảm bảo in UTF-8 trên Windows console
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


MERMAID_RESERVED_KEYWORDS = {
    "end", "subgraph", "graph", "flowchart", "class", "click", "style",
    "call", "direction", "linkstyle", "classdef", "interpolate", "acctitle", "accdescr"
}

def sanitize_mermaid_id(raw_id: str) -> str:
    """Chuẩn hóa ID để hợp lệ trong cú pháp Mermaid (không chứa dấu cách, gạch ngang, ký tự đặc biệt và từ khóa dành riêng)."""
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', str(raw_id))
    if clean and clean[0].isdigit():
        clean = "N_" + clean
    if not clean:
        clean = "NODE"
    elif clean.lower() in MERMAID_RESERVED_KEYWORDS:
        clean = f"ID_{clean}"
    return clean


def escape_mermaid_label(label: str) -> str:
    """Thoát các ký tự gây lỗi cú pháp hiển thị Mermaid (newline, ngoặc, nháy, thẻ góc, v.v.)."""
    if label is None:
        return ""
    lbl = str(label)
    # 1. Thoát dấu ngoặc và dấu nháy có thể phá vỡ cú pháp định nghĩa node
    lbl = lbl.replace('"', "'").replace('[', '(').replace(']', ')')
    lbl = lbl.replace('{', '(').replace('}', ')')
    # 2. Thoát dấu so sánh / thẻ góc TRƯỚC KHI chuyển đổi ngắt dòng sang <br/>
    lbl = lbl.replace('<', '&lt;').replace('>', '&gt;')
    # 3. Chuyển đổi ngắt dòng thành <br/> để Mermaid hiển thị nhiều dòng hợp lệ
    lbl = lbl.replace('\r\n', '<br/>').replace('\n', '<br/>').replace('\r', '<br/>')
    # 4. Thoát dấu pipe (|) tránh làm hỏng edge text trong cú pháp -->|label|
    lbl = lbl.replace('|', '/')
    return lbl.strip()


def load_offline_runtime() -> dict:
    """Load pinned browser runtimes or fail before writing an offline viewer."""
    assets = {}
    for name, (path, marker) in RUNTIME_ASSETS.items():
        if not path.is_file():
            raise RuntimeError(f"Offline runtime missing: {path}")
        text = path.read_text(encoding="utf-8")
        if len(text) < 1000 or marker not in text:
            raise RuntimeError(f"Offline runtime is invalid: {path}")
        assets[name] = text.replace("</script>", "<\\/script>")
    return assets


def scan_language_sources(project_root: Path) -> dict:
    """Extract declarations and simple relationships without claiming a full AST."""
    patterns = {
        ".py": ("Python", r"(?:^|\n)\s*(?:async\s+)?(?:class|def)\s+([A-Za-z_]\w*)", r"(?:^|\n)\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))"),
        ".js": ("JavaScript", r"(?:class|function)\s+([A-Za-z_$][\w$]*)", r"(?:import.+?from\s+|require\s*\()['\"]([^'\"]+)"),
        ".jsx": ("JavaScript", r"(?:class|function)\s+([A-Za-z_$][\w$]*)", r"(?:import.+?from\s+|require\s*\()['\"]([^'\"]+)"),
        ".ts": ("TypeScript", r"(?:class|function|interface|type)\s+([A-Za-z_$][\w$]*)", r"(?:import.+?from\s+|require\s*\()['\"]([^'\"]+)"),
        ".tsx": ("TypeScript", r"(?:class|function|interface|type)\s+([A-Za-z_$][\w$]*)", r"(?:import.+?from\s+|require\s*\()['\"]([^'\"]+)"),
        ".go": ("Go", r"(?:type\s+([A-Za-z_]\w*)\s+(?:struct|interface)|func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*))", r"import\s+(?:\([^)]*\)|\"([^\"]+)\")"),
        ".rs": ("Rust", r"(?:struct|enum|trait|impl|fn)\s+([A-Za-z_]\w*)", r"use\s+([^;]+)"),
    }
    symbols, relations, languages, warnings = [], [], set(), []
    ignored = {"node_modules", "target", "dist", "build", ".git", ".venv", "venv", "__pycache__"}
    for current_root, directories, filenames in os.walk(project_root, topdown=True):
        directories[:] = sorted(name for name in directories if name not in ignored and not name.startswith("."))
        for filename in sorted(filenames):
            if filename.startswith("."):
                continue
            path = Path(current_root) / filename
            spec = patterns.get(path.suffix.lower())
            if not spec:
                continue
            language, declaration, import_pattern = spec
            languages.add(language)
            rel = path.relative_to(project_root).as_posix()
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                warnings.append(f"Skipped {rel}: {exc}")
                continue
            for match in re.finditer(declaration, text):
                name = next((value for value in match.groups() if value), None)
                if name:
                    symbols.append({"id": f"SRC_{sanitize_mermaid_id(rel)}_{sanitize_mermaid_id(name)}", "name": name, "file": rel, "language": language})
            for match in re.finditer(import_pattern, text, re.MULTILINE | re.DOTALL):
                target = next((value for value in match.groups() if value), None)
                if target:
                    relations.append({"source": rel, "target": target, "kind": "imports"})
    return {"provenance": "language_aware" if symbols else "structural", "languages": sorted(languages), "symbols": symbols[:40], "relations": relations[:40], "warnings": warnings[:10]}


def generate_mermaid_from_language_analysis(project_info: dict, analysis: dict) -> dict:
    lines = ["flowchart LR"]
    node_ids = {}
    for index, symbol in enumerate(analysis["symbols"]):
        node_id = f"S{index}"
        node_ids[symbol["name"]] = node_id
        lines.append(f'    {node_id}["{escape_mermaid_label(symbol["name"])}\\n{escape_mermaid_label(symbol["file"])}"]')
    for relation in analysis["relations"]:
        source = next((node for node in analysis["symbols"] if node["file"] == relation["source"]), None)
        if source and source["name"] in node_ids:
            external_id = hashlib.sha256(relation["target"].encode("utf-8")).hexdigest()[:10].upper()
            lines.append(f'    {node_ids[source["name"]]} -->|imports| EXT_{external_id}["{escape_mermaid_label(relation["target"])}"]')
    if not analysis["symbols"]:
        lines.append('    STRUCT["Structural scan only: no supported source declarations found"]')
    desc = f"Provenance: {analysis['provenance']}; languages: {', '.join(analysis['languages']) or 'none'}"
    if analysis["warnings"]:
        desc += "; warnings: " + " | ".join(analysis["warnings"])
    return {"source_analysis": {"title": "Source Analysis", "desc": desc, "code": "\n".join(lines)}}


def compute_architecture_diff(old_analysis: dict, new_analysis: dict) -> dict:
    """
    So sánh sự khác biệt kiến trúc giữa 2 bản snapshot (Before vs After).
    Hỗ trợ cả định dạng Source Analysis (symbols/relations) và Graph JSON (nodes/edges).
    Phân loại:
    - Added: Node/Edge mới (+)
    - Removed: Node/Edge bị xóa (-)
    - Modified: Node có quan hệ thay đổi hoặc sửa đổi (Δ)
    - Unchanged: Node giữ nguyên (=)
    """
    def extract_elements(data: dict):
        nodes = {}
        edges = set()
        if "symbols" in data:
            for s in data.get("symbols", []):
                nid = s.get("id") or s.get("name")
                nodes[nid] = {"id": nid, "name": s.get("name", nid), "file": s.get("file", ""), "type": "symbol"}
            for r in data.get("relations", []):
                edges.add((r.get("source", ""), r.get("target", ""), r.get("kind", "imports")))
        elif "nodes" in data:
            for n in data.get("nodes", []):
                nid = n.get("id") or n.get("name")
                nodes[nid] = {"id": nid, "name": n.get("name") or n.get("label") or nid, "file": n.get("file") or n.get("path") or "", "type": "node"}
            for e in data.get("edges", []):
                src = e.get("source") or e.get("from") or ""
                tgt = e.get("target") or e.get("to") or ""
                kind = e.get("kind") or e.get("label") or "rel"
                edges.add((src, tgt, kind))
        return nodes, edges

    old_nodes, old_edges = extract_elements(old_analysis)
    new_nodes, new_edges = extract_elements(new_analysis)

    added_nodes = [n for nid, n in new_nodes.items() if nid not in old_nodes]
    removed_nodes = [n for nid, n in old_nodes.items() if nid not in new_nodes]
    common_ids = set(old_nodes.keys()) & set(new_nodes.keys())

    modified_nodes = []
    unchanged_nodes = []
    for nid in common_ids:
        o_n = old_nodes[nid]
        n_n = new_nodes[nid]
        o_conns = {e for e in old_edges if e[0] == nid or e[1] == nid or e[0] == o_n.get("file") or e[1] == o_n.get("name")}
        n_conns = {e for e in new_edges if e[0] == nid or e[1] == nid or e[0] == n_n.get("file") or e[1] == n_n.get("name")}
        if o_conns != n_conns or o_n.get("file") != n_n.get("file"):
            modified_nodes.append(n_n)
        else:
            unchanged_nodes.append(n_n)

    added_edges = new_edges - old_edges
    removed_edges = old_edges - new_edges
    common_edges = new_edges & old_edges

    lines = ["flowchart LR"]
    lines.append("    %% Architecture Diff Styles")
    lines.append("    classDef added fill:#dcfce7,stroke:#16a34a,stroke-width:2.5px,color:#14532d;")
    lines.append("    classDef removed fill:#fee2e2,stroke:#dc2626,stroke-width:2px,stroke-dasharray: 4 4,color:#7f1d1d;")
    lines.append("    classDef modified fill:#fef3c7,stroke:#d97706,stroke-width:2.5px,color:#78350f;")
    lines.append("    classDef unchanged fill:#f1f5f9,stroke:#94a3b8,stroke-width:1px,color:#334155;")

    node_id_map = {}
    counter = 0

    for n in added_nodes:
        nid = f"ADD_{counter}"
        counter += 1
        node_id_map[n["id"]] = nid
        node_id_map[n["name"]] = nid
        if n["file"]:
            node_id_map[n["file"]] = nid
        f_info = f"\\n{escape_mermaid_label(n['file'])}" if n.get("file") else ""
        lines.append(f'    {nid}["[+] {escape_mermaid_label(n["name"])}{f_info}"]:::added')

    for n in removed_nodes:
        nid = f"REM_{counter}"
        counter += 1
        node_id_map[n["id"]] = nid
        node_id_map[n["name"]] = nid
        if n["file"]:
            node_id_map[n["file"]] = nid
        f_info = f"\\n{escape_mermaid_label(n['file'])}" if n.get("file") else ""
        lines.append(f'    {nid}["[-] {escape_mermaid_label(n["name"])}{f_info}"]:::removed')

    for n in modified_nodes:
        nid = f"MOD_{counter}"
        counter += 1
        node_id_map[n["id"]] = nid
        node_id_map[n["name"]] = nid
        if n["file"]:
            node_id_map[n["file"]] = nid
        f_info = f"\\n{escape_mermaid_label(n['file'])}" if n.get("file") else ""
        lines.append(f'    {nid}["[Δ] {escape_mermaid_label(n["name"])}{f_info}"]:::modified')

    for n in unchanged_nodes[:25]:
        nid = f"UNC_{counter}"
        counter += 1
        node_id_map[n["id"]] = nid
        node_id_map[n["name"]] = nid
        if n["file"]:
            node_id_map[n["file"]] = nid
        lines.append(f'    {nid}["{escape_mermaid_label(n["name"])}"]:::unchanged')

    for src, tgt, kind in added_edges:
        s = node_id_map.get(src)
        t = node_id_map.get(tgt)
        if s and t:
            lines.append(f'    {s} ==>|added {kind}| {t}')

    for src, tgt, kind in removed_edges:
        s = node_id_map.get(src)
        t = node_id_map.get(tgt)
        if s and t:
            lines.append(f'    {s} -.->|removed {kind}| {t}')

    for src, tgt, kind in list(common_edges)[:35]:
        s = node_id_map.get(src)
        t = node_id_map.get(tgt)
        if s and t:
            lines.append(f'    {s} --> {t}')

    if not added_nodes and not removed_nodes and not modified_nodes and not added_edges and not removed_edges:
        lines.append('    DIFF_EMPTY["No architectural drift detected between snapshots (=)"]')

    desc = f"Architecture Diff: +{len(added_nodes)} added, -{len(removed_nodes)} removed, ~{len(modified_nodes)} modified; +{len(added_edges)} new relations"
    return {
        "architecture_diff": {
            "title": "Architecture Diff (Before vs After)",
            "desc": desc,
            "code": "\n".join(lines),
            "stats": {
                "added_nodes": len(added_nodes),
                "removed_nodes": len(removed_nodes),
                "modified_nodes": len(modified_nodes),
                "added_relations": len(added_edges),
                "removed_relations": len(removed_edges)
            }
        }
    }


def load_diff_baseline(diff_target: str, project_root: Path) -> dict:
    """Load a snapshot, directory, or Git commit; never silently skip a requested diff."""
    supplied = Path(diff_target)
    candidate = supplied if supplied.is_absolute() else project_root / supplied
    if candidate.is_file():
        try:
            value = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Diff baseline file is invalid: {candidate} ({error})") from error
        if not isinstance(value, dict):
            raise RuntimeError(f"Diff baseline must be a JSON object: {candidate}")
        return value
    if candidate.is_dir():
        return scan_language_sources(candidate)

    verified = subprocess.run(
        ["git", "rev-parse", "--verify", f"{diff_target}^{{commit}}"],
        cwd=str(project_root), capture_output=True, text=True, check=False,
    )
    if verified.returncode != 0:
        raise RuntimeError(f"Diff baseline does not exist as a file, directory, or Git commit: {diff_target}")
    listing = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "-z", diff_target],
        cwd=str(project_root), capture_output=True, check=False,
    )
    if listing.returncode != 0:
        raise RuntimeError(f"Could not list source files at Git commit: {diff_target}")

    names = [name.decode("utf-8", errors="strict") for name in listing.stdout.split(b"\0") if name]
    with tempfile.TemporaryDirectory(prefix="excaliflow-diff-") as temp:
        snapshot_root = Path(temp)
        extracted = 0
        for name in names:
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts or pure.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            content = subprocess.run(
                ["git", "show", f"{diff_target}:{name}"],
                cwd=str(project_root), capture_output=True, check=False,
            )
            if content.returncode != 0:
                raise RuntimeError(f"Could not read {name} at Git commit {diff_target}")
            destination = snapshot_root.joinpath(*pure.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content.stdout)
            extracted += 1
        if not extracted:
            raise RuntimeError(f"Git commit contains no supported source files: {diff_target}")
        return scan_language_sources(snapshot_root)


def generate_share_card_svg(project_title: str, stats: dict) -> str:
    """Tạo thẻ ảnh chia sẻ chuẩn 1200x630 (README & Social Share Card) dạng SVG vector."""
    nodes_count = stats.get("nodes_count", 0)
    edges_count = stats.get("edges_count", 0)
    provenance = stats.get("provenance", "AST Language Aware")
    
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630">
  <defs>
    <linearGradient id="bg-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="50%" stop-color="#1e1b4b" />
      <stop offset="100%" stop-color="#090d16" />
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="30%" r="60%">
      <stop offset="0%" stop-color="#6366f1" stop-opacity="0.35" />
      <stop offset="100%" stop-color="#0f172a" stop-opacity="0" />
    </radialGradient>
    <filter id="card-shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#000000" flood-opacity="0.5" />
    </filter>
  </defs>
  
  <!-- Background -->
  <rect width="1200" height="630" fill="url(#bg-grad)" />
  <rect width="1200" height="630" fill="url(#glow)" />
  
  <!-- Subtle Grid Pattern -->
  <g opacity="0.08" stroke="#ffffff" stroke-width="1">
    <line x1="0" y1="105" x2="1200" y2="105" />
    <line x1="0" y1="210" x2="1200" y2="210" />
    <line x1="0" y1="315" x2="1200" y2="315" />
    <line x1="0" y1="420" x2="1200" y2="420" />
    <line x1="0" y1="525" x2="1200" y2="525" />
    <line x1="200" y1="0" x2="200" y2="630" />
    <line x1="400" y1="0" x2="400" y2="630" />
    <line x1="600" y1="0" x2="600" y2="630" />
    <line x1="800" y1="0" x2="800" y2="630" />
    <line x1="1000" y1="0" x2="1000" y2="630" />
  </g>
  
  <!-- Header Section -->
  <g transform="translate(60, 50)">
    <rect width="140" height="32" rx="16" fill="#4f46e5" fill-opacity="0.3" stroke="#818cf8" stroke-width="1.5" />
    <text x="70" y="21" font-family="sans-serif" font-size="13" font-weight="700" fill="#c7d2fe" text-anchor="middle" letter-spacing="1">EXCALIFLOW</text>
    
    <text x="0" y="90" font-family="Georgia, sans-serif" font-size="42" font-weight="700" fill="#ffffff">{escape_mermaid_label(project_title)}</text>
    <text x="0" y="125" font-family="sans-serif" font-size="18" fill="#94a3b8">Interactive Architecture Map &amp; Verified Codebase Atlas</text>
  </g>
  
  <!-- Metric Badges -->
  <g transform="translate(60, 210)">
    <rect width="240" height="74" rx="12" fill="#1e293b" stroke="#334155" stroke-width="1.5" filter="url(#card-shadow)" />
    <text x="24" y="32" font-family="sans-serif" font-size="13" font-weight="600" fill="#94a3b8">CODE SYMBOLS &amp; NODES</text>
    <text x="24" y="60" font-family="sans-serif" font-size="24" font-weight="800" fill="#38bdf8">{nodes_count} Nodes</text>
    
    <rect x="260" width="240" height="74" rx="12" fill="#1e293b" stroke="#334155" stroke-width="1.5" filter="url(#card-shadow)" />
    <text x="284" y="32" font-family="sans-serif" font-size="13" font-weight="600" fill="#94a3b8">RELATIONS &amp; EDGES</text>
    <text x="284" y="60" font-family="sans-serif" font-size="24" font-weight="800" fill="#4ade80">{edges_count} Edges</text>
    
    <rect x="520" width="280" height="74" rx="12" fill="#1e293b" stroke="#334155" stroke-width="1.5" filter="url(#card-shadow)" />
    <text x="544" y="32" font-family="sans-serif" font-size="13" font-weight="600" fill="#94a3b8">ANALYSIS PROVENANCE</text>
    <text x="544" y="60" font-family="sans-serif" font-size="20" font-weight="700" fill="#fbbf24">{provenance}</text>
  </g>
  
  <!-- Visual Window Mockup -->
  <g transform="translate(60, 310)">
    <rect width="1080" height="250" rx="16" fill="#0b1120" stroke="#3b82f6" stroke-width="2" stroke-opacity="0.6" filter="url(#card-shadow)" />
    
    <circle cx="30" cy="24" r="6" fill="#ef4444" />
    <circle cx="50" cy="24" r="6" fill="#f59e0b" />
    <circle cx="70" cy="24" r="6" fill="#10b981" />
    <text x="100" y="28" font-family="monospace" font-size="12" fill="#64748b">architecture_viewer.html • Panzoom 100% • Reach Tracing Active</text>
    
    <g transform="translate(40, 50)">
      <rect x="20" y="30" width="180" height="60" rx="8" fill="#1e293b" stroke="#38bdf8" stroke-width="2" />
      <text x="110" y="66" font-family="sans-serif" font-size="14" font-weight="700" fill="#f8fafc" text-anchor="middle">Entrypoint / API</text>
      
      <line x1="200" y1="60" x2="310" y2="60" stroke="#60a5fa" stroke-width="2" stroke-dasharray="6 3" />
      <polygon points="310,60 300,55 300,65" fill="#60a5fa" />
      
      <rect x="320" y="20" width="220" height="80" rx="10" fill="#1e293b" stroke="#f59e0b" stroke-width="3" />
      <text x="430" y="55" font-family="sans-serif" font-size="16" font-weight="800" fill="#fef08a" text-anchor="middle">Core Service Engine</text>
      <text x="430" y="78" font-family="sans-serif" font-size="11" fill="#fef9c3" text-anchor="middle">⚡ Reach Focused Node</text>
      
      <line x1="540" y1="60" x2="650" y2="60" stroke="#4ade80" stroke-width="2" stroke-dasharray="6 3" />
      <polygon points="650,60 640,55 640,65" fill="#4ade80" />
      
      <rect x="660" y="30" width="200" height="60" rx="8" fill="#1e293b" stroke="#4ade80" stroke-width="2" />
      <text x="760" y="66" font-family="sans-serif" font-size="14" font-weight="700" fill="#f8fafc" text-anchor="middle">Database &amp; Storage</text>
      
      <line x1="430" y1="100" x2="430" y2="135" stroke="#4ade80" stroke-width="2" stroke-dasharray="6 3" />
      <polygon points="430,135 425,125 435,125" fill="#4ade80" />
      <rect x="330" y="140" width="200" height="45" rx="8" fill="#1e293b" stroke="#4ade80" stroke-width="2" />
      <text x="430" y="168" font-family="sans-serif" font-size="13" font-weight="600" fill="#f8fafc" text-anchor="middle">Graphify Knowledge Graph</text>
    </g>
  </g>
  
  <!-- Footer Tagline -->
  <g transform="translate(60, 595)">
    <text x="0" y="0" font-family="sans-serif" font-size="12" fill="#64748b">Generated by ExcaliFlow Studio • 100% Local-First &amp; Air-Gapped • github.com/Nakazasen/ExcaliFlow-Studio</text>
  </g>
</svg>"""


def generate_share_card_file(project_dir: str, out_path: str = "share-card.svg") -> Path:
    """Tạo và ghi tệp Share Card 1200x630 SVG."""
    proj_path = Path(project_dir).resolve()
    out_file = Path(out_path)
    if not out_file.is_absolute():
        out_file = proj_path / out_file
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    lang_info = scan_language_sources(proj_path)
    stats = {
        "languages": lang_info.get("languages", ["Python"]),
        "nodes_count": len(lang_info.get("symbols", [])),
        "edges_count": len(lang_info.get("relations", [])),
        "provenance": lang_info.get("provenance", "AST Language Aware")
    }
    svg_content = generate_share_card_svg(proj_path.name, stats)
    out_file.write_text(svg_content, encoding="utf-8")
    print(f"[*] Da tao thanh cong 1200x630 Share Card tai: {out_file.resolve()}")
    return out_file.resolve()




def get_latest_source_mtime(project_root: Path) -> float:
    """Tra cuu thoi diem sua doi moi nhat cua cac tap tin ma nguon trong du an."""
    latest_mtime = 0.0
    excluded_dirs = {
        ".git", "node_modules", "graphify-out", ".understand-anything", ".understand",
        "dist", "build", "__pycache__", ".venv", "venv", ".pytest_cache", ".ruff_cache",
        ".mypy_cache", ".excaliflow"
    }
    excluded_exts = {".html", ".excalidraw", ".svg", ".png", ".jpg", ".jpeg", ".zip", ".tar", ".gz", ".log"}
    try:
        for p in project_root.rglob("*"):
            if any(part in excluded_dirs or part.startswith(".") for part in p.parts):
                continue
            if p.is_file() and p.suffix.lower() not in excluded_exts:
                try:
                    mtime = p.stat().st_mtime
                    if mtime > latest_mtime:
                        latest_mtime = mtime
                except OSError:
                    pass
    except Exception:
        pass
    return latest_mtime


def graphify_version_status(graphify_bin: str) -> tuple[bool, str]:
    """Return whether the Graphify CLI is inside ExcaliFlow's tested window."""
    try:
        proc = subprocess.run(
            [graphify_bin, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"khong doc duoc phien ban ({exc})"

    output = (proc.stdout or proc.stderr or "").strip()
    match = re.search(r"(?:^|\s)(\d+)\.(\d+)\.(\d+)(?:\s|$)", output)
    if proc.returncode != 0 or not match:
        detail = output or f"exit code {proc.returncode}"
        return False, f"khong nhan dien duoc phien ban ({detail})"

    version = tuple(int(part) for part in match.groups())
    version_text = ".".join(str(part) for part in version)
    compatible = GRAPHIFY_MIN_VERSION <= version < GRAPHIFY_MAX_VERSION
    return compatible, version_text


def compatible_graphify_binary(graphify_bin: str | None, strict: bool = False) -> str | None:
    """Validate the executable before allowing automatic Graphify extraction."""
    if not graphify_bin:
        return None
    compatible, detail = graphify_version_status(graphify_bin)
    if compatible:
        return graphify_bin

    message = (
        f"Graphify {detail} nam ngoai cua so tuong thich {GRAPHIFY_VERSION_SPEC}. "
        f'Hãy cai/cap nhat bang: uv tool install --force "graphifyy{GRAPHIFY_VERSION_SPEC}"'
    )
    if strict:
        raise RuntimeError(f"Fail-Closed: {message}")
    print(f"[!] Canh bao: {message} Khong tu dong chay Graphify; dung do thi hien co hoac AST.")
    return None


def run_graphify_extract(project_root: Path, graphify_bin: str) -> bool:
    """Kich hoat Graphify headless extraction va bao cao ket qua ro rang, khong giau loi."""
    try:
        print(f"[*] Dang chay Graphify de trich xuat/cap nhat do thi tri thuc tai: {project_root}...")
        proc = subprocess.run(
            [graphify_bin, "extract", str(project_root), "--code-only", "--out", str(project_root)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False
        )
        if proc.returncode == 0:
            print("[*] Graphify da hoan tat trich xuat/cap nhat do thi thanh cong.")
            return True
        else:
            err_msg = proc.stderr.strip() or proc.stdout.strip() or f"Exit code {proc.returncode}"
            print(f"[!] Canh bao: Graphify that bai voi ma loi {proc.returncode}:\n{err_msg}")
            return False
    except Exception as e:
        print(f"[!] Khong the thuc thi Graphify ({e}). Chuyen sang bo quet AST noi bo.")
        return False


def find_knowledge_graph(project_root: Path, auto_trigger: bool = True, strict: bool = False):
    """
    Tự động tìm kiếm file đồ thị tri thức (Graphify hoặc Understand-Anything).
    Ưu tiên:
    1. Graphify graphs (canonical graphify-out/graph.json, lồng trong graphify-out/, hoặc graph.json ở root)
    2. Nếu chưa có và auto_trigger=True: tự động kích hoạt graphify extract --code-only để tạo graphify-out/graph.json.
    3. Understand graphs (.understand-anything/knowledge-graph.json, .understand/knowledge-graph.json, knowledge-graph.json ở root)
    Áp dụng kiểm tra tính mới (staleness check) và cơ chế Fail-Closed nghiêm ngặt trên TOÀN BỘ các loại đồ thị tìm thấy.
    """
    project_root = project_root.resolve()
    g_out = project_root / "graphify-out" / "graph.json"
    graphify_bin = shutil.which("graphify") if auto_trigger else None
    latest_src_mtime = get_latest_source_mtime(project_root)

    # Helper gom tất cả ứng viên Graphify độc lập (tránh lỗi elif khi thư mục rỗng)
    def collect_graphify_candidates():
        candidates = []
        if g_out.is_file():
            candidates.append(g_out)
        if (project_root / "graphify-out").is_dir():
            for p in (project_root / "graphify-out").glob("**/graph.json"):
                if p.is_file() and p not in candidates:
                    candidates.append(p)
        if (project_root / "graph.json").is_file() and (project_root / "graph.json") not in candidates:
            candidates.append(project_root / "graph.json")
        return candidates

    graphify_candidates = collect_graphify_candidates()

    # Nếu tìm thấy đồ thị Graphify: Kiểm tra tính mới so với mã nguồn
    if graphify_candidates:
        selected_graph = max(graphify_candidates, key=lambda p: p.stat().st_mtime)
        graph_mtime = selected_graph.stat().st_mtime
        if latest_src_mtime > graph_mtime:
            if auto_trigger and graphify_bin:
                graphify_bin = compatible_graphify_binary(graphify_bin, strict=strict)
            if auto_trigger and graphify_bin:
                print(f"[*] Phat hien ma nguon co thay doi sau lan tao do thi ({latest_src_mtime:.1f} > {graph_mtime:.1f}). Tien hanh cap nhat Graphify...")
                success = run_graphify_extract(project_root, graphify_bin)
                if not success:
                    if strict:
                        raise RuntimeError(f"Fail-Closed: Graphify update failed in strict mode for {project_root}")
                    print(f"[!] Graphify cap nhat that bai; su dung do thi hien co.")
                else:
                    # Quét lại sau khi Graphify hoàn tất để xác nhận tệp đồ thị thực sự mới hơn mã nguồn
                    new_candidates = collect_graphify_candidates()
                    if new_candidates:
                        new_selected = max(new_candidates, key=lambda p: p.stat().st_mtime)
                        if new_selected.stat().st_mtime >= latest_src_mtime:
                            selected_graph = new_selected
                        elif strict:
                            raise RuntimeError(f"Fail-Closed: Graphify reported success but output graph is still stale ({latest_src_mtime:.1f} > {new_selected.stat().st_mtime:.1f}) in strict mode for {project_root}")
                    elif strict:
                        raise RuntimeError(f"Fail-Closed: Graphify reported success but no output graph was found in strict mode for {project_root}")
            elif strict:
                if not graphify_bin:
                    raise RuntimeError(f"Fail-Closed: Stale graph detected ({latest_src_mtime:.1f} > {graph_mtime:.1f}) but graphify executable is not available in strict mode for {project_root}")
                else:
                    raise RuntimeError(f"Fail-Closed: Stale graph detected ({latest_src_mtime:.1f} > {graph_mtime:.1f}) but auto_trigger is disabled in strict mode for {project_root}")
            else:
                print(f"[!] Canh bao: Ma nguon moi hon do thi ({latest_src_mtime:.1f} > {graph_mtime:.1f}) nhung khong the cap nhat tu dong.")
        return ("graphify", selected_graph)

    # 2. Nếu chưa có đồ thị Graphify và auto_trigger=True: Kích hoạt Graphify để tạo mới lần đầu
    if auto_trigger and graphify_bin:
        graphify_bin = compatible_graphify_binary(graphify_bin, strict=strict)
    if auto_trigger and graphify_bin:
        print(f"[*] Chua tim thay do thi tri thuc. Tu dong kich hoat Graphify cho: {project_root}...")
        if run_graphify_extract(project_root, graphify_bin):
            new_candidates = collect_graphify_candidates()
            if new_candidates:
                new_selected = max(new_candidates, key=lambda p: p.stat().st_mtime)
                if new_selected.stat().st_mtime >= latest_src_mtime:
                    print(f"[*] Da tao moi thanh cong do thi tri thuc Graphify: {new_selected}")
                    return ("graphify", new_selected)
                elif strict:
                    raise RuntimeError(f"Fail-Closed: Initial Graphify extraction created stale graph ({latest_src_mtime:.1f} > {new_selected.stat().st_mtime:.1f}) in strict mode for {project_root}")
            elif strict:
                raise RuntimeError(f"Fail-Closed: Initial Graphify extraction reported success but no output graph was found in strict mode for {project_root}")
        elif strict:
            raise RuntimeError(f"Fail-Closed: Initial Graphify extraction failed in strict mode for {project_root}")

    # 3. Gom tất cả ứng viên Understand-Anything độc lập
    understand_candidates = []
    for u_path in [
        project_root / ".understand-anything" / "knowledge-graph.json",
        project_root / ".understand" / "knowledge-graph.json",
        project_root / "knowledge-graph.json"
    ]:
        if u_path.is_file() and u_path not in understand_candidates:
            understand_candidates.append(u_path)

    if understand_candidates:
        selected_u = max(understand_candidates, key=lambda p: p.stat().st_mtime)
        u_mtime = selected_u.stat().st_mtime
        if latest_src_mtime > u_mtime:
            if strict:
                raise RuntimeError(f"Fail-Closed: Stale Understand knowledge graph detected ({latest_src_mtime:.1f} > {u_mtime:.1f}) and cannot be automatically updated in strict mode for {project_root}")
            else:
                print(f"[!] Canh bao: Ma nguon moi hon do thi Understand ({latest_src_mtime:.1f} > {u_mtime:.1f}).")
        return ("understand", selected_u)

    if strict:
        raise RuntimeError(f"Fail-Closed: No knowledge graph found or generated for {project_root}")

    return (None, None)


def parse_graphify_graph(graph_json_path: Path) -> dict:
    """
    Phân tích file graphify-out/graph.json để trích xuất các cộng đồng (communities/hyperedges),
    các node trung tâm (god nodes / high-degree nodes), và các liên kết quan trọng.
    Đảm bảo an toàn tuyệt đối khi gặp JSON rỗng, JSON mảng [] hoặc node/edge không đúng định dạng.
    """
    try:
        raw_text = graph_json_path.read_text(encoding="utf-8", errors="ignore")
        if not raw_text.strip():
            print(f"[!] File {graph_json_path} rỗng.")
            return None
        data = json.loads(raw_text)
    except Exception as e:
        print(f"[!] Lỗi đọc/parse JSON {graph_json_path}: {e}")
        return None

    if not isinstance(data, dict):
        print(f"[!] Cảnh báo: Dữ liệu {graph_json_path} không phải là JSON object (dict). Bỏ qua để fallback.")
        return None

    try:
        raw_nodes = data.get("nodes", [])
        if isinstance(raw_nodes, dict):
            raw_nodes = list(raw_nodes.values())
        elif not isinstance(raw_nodes, list):
            raw_nodes = []

        raw_edges = data.get("edges", []) or data.get("links", [])
        if isinstance(raw_edges, dict):
            raw_edges = list(raw_edges.values())
        elif not isinstance(raw_edges, list):
            raw_edges = []
        raw_edges = [e for e in raw_edges if isinstance(e, dict)]

        raw_hyperedges = data.get("hyperedges", [])
        if isinstance(raw_hyperedges, dict):
            raw_hyperedges = list(raw_hyperedges.values())
        elif not isinstance(raw_hyperedges, list):
            raw_hyperedges = []

        if not raw_nodes and not raw_hyperedges:
            return None

        node_map = {}
        degree_map = {}
        for n in raw_nodes:
            if not isinstance(n, dict):
                continue
            nid = n.get("id")
            if not nid:
                continue
            str_nid = str(nid)
            node_map[str_nid] = {
                "id": str_nid,
                "label": str(n.get("label") or nid),
                "file_type": str(n.get("file_type", "code")),
                "source_file": str(n.get("source_file", "")),
                "community": str(n.get("community", ""))
            }
            degree_map[str_nid] = 0

        for e in raw_edges:
            if not isinstance(e, dict):
                continue
            src = str(e.get("source", ""))
            tgt = str(e.get("target", ""))
            if src in degree_map:
                degree_map[src] += 1
            if tgt in degree_map:
                degree_map[tgt] += 1

        communities = []
        for h in raw_hyperedges:
            if not isinstance(h, dict):
                continue
            hid = str(h.get("id", ""))
            hlabel = str(h.get("label") or hid)
            hnodes = h.get("nodes", [])
            if isinstance(hnodes, list):
                hnodes = [str(x) for x in hnodes if x]
            else:
                hnodes = []
            relation = str(h.get("relation", ""))
            source_file = str(h.get("source_file", ""))
            if hnodes:
                communities.append({
                    "id": hid,
                    "label": hlabel,
                    "nodes": hnodes,
                    "relation": relation,
                    "source_file": source_file,
                    "size": len(hnodes)
                })

        communities.sort(key=lambda x: x["size"], reverse=True)

        if not node_map and not communities:
            return None

        return {
            "node_map": node_map,
            "raw_nodes": raw_nodes,
            "raw_edges": raw_edges,
            "communities": communities,
            "degree_map": degree_map,
            "directed": bool(data.get("directed", True))
        }
    except Exception as e:
        print(f"[!] Lỗi trích xuất đồ thị Graphify từ {graph_json_path}: {e}")
        return None


def parse_understand_graph(graph_json_path: Path) -> dict:
    """Phân tích file knowledge-graph.json từ Understand-Anything an toàn tuyệt đối."""
    try:
        raw_text = graph_json_path.read_text(encoding="utf-8", errors="ignore")
        if not raw_text.strip():
            print(f"[!] File {graph_json_path} rỗng.")
            return None
        data = json.loads(raw_text)
    except Exception as e:
        print(f"[!] Lỗi đọc/parse JSON {graph_json_path}: {e}")
        return None

    if not isinstance(data, dict):
        print(f"[!] Cảnh báo: Dữ liệu {graph_json_path} không phải là JSON object (dict). Bỏ qua để fallback.")
        return None

    try:
        raw_nodes = data.get("nodes", [])
        if isinstance(raw_nodes, dict):
            raw_nodes = list(raw_nodes.values())
        elif not isinstance(raw_nodes, list):
            raw_nodes = []

        raw_edges = data.get("edges", []) or data.get("links", [])
        if isinstance(raw_edges, dict):
            raw_edges = list(raw_edges.values())
        elif not isinstance(raw_edges, list):
            raw_edges = []
        raw_edges = [e for e in raw_edges if isinstance(e, dict)]

        project = data.get("project", {})
        if not isinstance(project, dict):
            project = {"name": str(project), "description": ""}

        node_map = {}
        for n in raw_nodes:
            if not isinstance(n, dict):
                continue
            nid = n.get("id")
            if not nid:
                continue
            str_nid = str(nid)
            node_map[str_nid] = {
                "id": str_nid,
                "name": str(n.get("name") or nid),
                "filePath": str(n.get("filePath", "")),
                "summary": str(n.get("summary", "")),
                "tags": n.get("tags", []) if isinstance(n.get("tags"), list) else [],
                "type": str(n.get("type", "file"))
            }

        if not node_map:
            return None

        return {
            "project": project,
            "node_map": node_map,
            "raw_nodes": raw_nodes,
            "raw_edges": raw_edges
        }
    except Exception as e:
        print(f"[!] Lỗi trích xuất đồ thị Understand từ {graph_json_path}: {e}")
        return None


def generate_mermaid_from_graphify(graph_data: dict, root_name: str) -> dict:
    """Tạo sơ đồ Mermaid độ nét cao từ dữ liệu đồ thị Graphify."""
    diagrams = {}
    node_map = graph_data["node_map"]
    raw_edges = graph_data["raw_edges"]
    communities = graph_data["communities"]
    degree_map = graph_data["degree_map"]

    # 1. SƠ ĐỒ CỘNG ĐỒNG KIẾN TRÚC (Graphify Communities Architecture)
    comm_lines = [
        "%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e0f2fe', 'primaryBorderColor': '#0284c7', 'primaryTextColor': '#0f172a', 'secondaryColor': '#fef3c7', 'secondaryBorderColor': '#d97706', 'secondaryTextColor': '#0f172a', 'tertiaryColor': '#f3e8ff', 'tertiaryBorderColor': '#9333ea', 'tertiaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%",
        "flowchart TD"
    ]

    used_node_ids = set()
    node_to_comm = {}

    if communities:
        for idx, comm in enumerate(communities[:8]):
            comm_id = f"COMM_{idx}"
            comm_label = escape_mermaid_label(comm['label'])
            comm_lines.append(f'    subgraph {comm_id}["📦 {comm_label}"]')
            
            for nid in comm["nodes"][:6]:
                clean_id = sanitize_mermaid_id(nid)
                used_node_ids.add(nid)
                node_to_comm[nid] = comm_id
                
                ninfo = node_map.get(nid, {})
                label = escape_mermaid_label(ninfo.get("label", nid))
                icon = "📄" if ninfo.get("file_type") == "code" else "📑"
                comm_lines.append(f'        {clean_id}["{icon} {label}"]')
            comm_lines.append('    end')
    else:
        # Fallback grouping by source_file directory
        dir_groups = {}
        for nid, ninfo in node_map.items():
            sfile = ninfo.get("source_file", "")
            dname = sfile.split("/")[0] if "/" in sfile else "Core"
            dir_groups.setdefault(dname, []).append(nid)
            
        for idx, (dname, nids) in enumerate(list(dir_groups.items())[:6]):
            comm_id = f"DIR_{idx}"
            comm_lines.append(f'    subgraph {comm_id}["📁 {dname}"]')
            for nid in nids[:5]:
                clean_id = sanitize_mermaid_id(nid)
                used_node_ids.add(nid)
                label = escape_mermaid_label(node_map[nid].get("label", nid))
                comm_lines.append(f'        {clean_id}["📄 {label}"]')
            comm_lines.append('    end')

    # Draw inter-community edges
    added_edges = set()
    for e in raw_edges:
        src = e.get("source")
        tgt = e.get("target")
        if src in used_node_ids and tgt in used_node_ids and src != tgt:
            rel = escape_mermaid_label(e.get("relation", "relates_to"))
            pair = (src, tgt, rel)
            if pair not in added_edges and len(added_edges) < 25:
                added_edges.add(pair)
                s_id = sanitize_mermaid_id(src)
                t_id = sanitize_mermaid_id(tgt)
                comm_lines.append(f'    {s_id} -->|{rel}| {t_id}')

    diagrams["graphify_arch"] = {
        "title": "🧠 Kiến Trúc Tri Thức & Cộng Đồng (Graphify Knowledge Architecture)",
        "desc": f"Đồ thị cộng đồng kiến trúc và các mô-đun chức năng được trích xuất từ Graphify cho {root_name}",
        "code": "\n".join(comm_lines)
    }

    # 2. SƠ ĐỒ MẠNG LƯỚI PHỤ THUỘC & GỌI HÀM (Dependency & Call Graph)
    dep_lines = [
        "%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#ede9fe', 'primaryBorderColor': '#7c3aed', 'primaryTextColor': '#0f172a', 'secondaryColor': '#dcfce7', 'secondaryBorderColor': '#16a34a', 'secondaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%",
        "flowchart LR"
    ]

    sorted_nodes = sorted(degree_map.items(), key=lambda x: x[1], reverse=True)
    top_nids = {nid for nid, deg in sorted_nodes[:25] if nid in node_map}
    
    for nid in top_nids:
        clean_id = sanitize_mermaid_id(nid)
        label = escape_mermaid_label(node_map[nid]["label"])
        dep_lines.append(f'    {clean_id}["⚙️ <b>{label}</b>"]')

    added_dep_edges = set()
    for e in raw_edges:
        src = e.get("source")
        tgt = e.get("target")
        if src in top_nids and tgt in top_nids and src != tgt:
            rel = escape_mermaid_label(e.get("relation", "calls"))
            pair = (src, tgt)
            if pair not in added_dep_edges and len(added_dep_edges) < 30:
                added_dep_edges.add(pair)
                dep_lines.append(f'    {sanitize_mermaid_id(src)} -->|{rel}| {sanitize_mermaid_id(tgt)}')

    diagrams["graphify_deps"] = {
        "title": "🔗 Mạng Lưới Phụ Thuộc & Quan Hệ Mô-Đun (Dependency Graph)",
        "desc": "Các nút trung tâm (God nodes) và liên kết phụ thuộc, luồng gọi hàm giữa các thành phần cốt lõi",
        "code": "\n".join(dep_lines)
    }

    # 3. SƠ ĐỒ LUỒNG DỮ LIỆU & VẬN HÀNH (Data Flow & Pipeline)
    diagrams["pipeline"] = {
        "title": "🔄 Luồng Dữ Liệu & Xử Lý (Data Pipeline)",
        "desc": "Mô tả chu trình tiếp nhận dữ liệu đầu vào, xử lý qua các tầng và xuất kết quả",
        "code": """%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#dcfce7', 'primaryBorderColor': '#16a34a', 'primaryTextColor': '#0f172a', 'secondaryColor': '#fef9c3', 'secondaryBorderColor': '#ca8a04', 'secondaryTextColor': '#0f172a', 'tertiaryColor': '#fee2e2', 'tertiaryBorderColor': '#dc2626', 'tertiaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '15px' }, 'look': 'handDrawn'}}%%
flowchart LR
    INPUT["📥 Dữ liệu đầu vào<br/>(Sources / Evidence)"] --> AUTH{"🔐 Kiểm tra & Xác thực"}
    
    AUTH -->|Hợp lệ| PROCESS["⚙️ Xử lý Logic & Trích xuất<br/>(Extraction Engine)"]
    AUTH -->|Không hợp lệ| ERR["❌ Báo lỗi & Ghi log"]

    PROCESS --> VAULT[("💾 Lưu trữ Bằng chứng & Bộ nhớ<br/>(Evidence Vault / Knowledge Graph)")]
    VAULT --> SYNTH["✨ Tổng hợp & Điều phối Agent"]
    SYNTH --> OUTPUT["📤 Xuất kết quả & Phản hồi<br/>(Workspace Output / Insights)"]
"""
    }

    # 4. SƠ ĐỒ TUẦN TỰ (Sequence / Call Flow)
    diagrams["sequence"] = {
        "title": "⏱️ Sơ Đồ Tuần Tự (Sequence Diagram)",
        "desc": "Luồng tương tác tuần tự giữa Người dùng, Giao diện, Bộ định tuyến và Tầng lưu trữ",
        "code": """%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#fee2e2', 'primaryBorderColor': '#dc2626', 'primaryTextColor': '#0f172a', 'secondaryColor': '#e0f2fe', 'secondaryBorderColor': '#0284c7', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%
sequenceDiagram
    autonumber
    actor User as 👤 Người Dùng (User)
    participant UI as 🖥️ Giao Diện (Workspace UI)
    participant Router as 🧭 Bộ Định Tuyến (Router / Gateway)
    participant Agent as 🤖 Tác Vụ Agent (Orchestrator)
    participant Vault as 💾 Lưu Trữ (Memory Vault / DB)

    User->>UI: 1. Gửi yêu cầu / Thao tác tương tác
    UI->>Router: 2. Chuyển tiếp Request và Context
    Router->>Vault: 3. Truy vấn Bằng chứng & Tri thức
    Vault-->>Router: 4. Trả về đồ thị ngữ cảnh liên quan
    Router->>Agent: 5. Kích hoạt Agent xử lý chuyên sâu
    Agent->>Agent: 6. Thực thi thuật toán & biến đổi
    Agent->>Vault: 7. Ghi nhận Checkpoint & Bằng chứng mới
    Agent-->>UI: 8. Cập nhật kết quả hoàn thành
    UI-->>User: 9. Hiển thị thông báo và đồ họa trực quan
"""
    }

    return diagrams


def generate_mermaid_from_understand(understand_data: dict, root_name: str) -> dict:
    """Tạo sơ đồ Mermaid từ dữ liệu Understand-Anything knowledge-graph.json."""
    diagrams = {}
    node_map = understand_data["node_map"]
    raw_edges = understand_data["raw_edges"]
    project = understand_data.get("project", {})

    proj_name = project.get("name", root_name)
    proj_desc = project.get("description", "Dự án phần mềm")

    dir_groups = {}
    for nid, ninfo in node_map.items():
        fpath = ninfo.get("filePath", "")
        if "/" in fpath:
            top_dir = fpath.split("/")[0]
            if top_dir.startswith(".") and "/" in fpath:
                parts = fpath.split("/")
                top_dir = f"{parts[0]}/{parts[1]}" if len(parts) > 1 else parts[0]
        else:
            top_dir = "Root"
        dir_groups.setdefault(top_dir, []).append(nid)

    arch_lines = [
        "%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e0f2fe', 'primaryBorderColor': '#0284c7', 'primaryTextColor': '#0f172a', 'secondaryColor': '#fef3c7', 'secondaryBorderColor': '#d97706', 'secondaryTextColor': '#0f172a', 'tertiaryColor': '#f3e8ff', 'tertiaryBorderColor': '#9333ea', 'tertiaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%",
        "flowchart TD"
    ]

    used_nodes = set()
    for idx, (group_name, nids) in enumerate(list(dir_groups.items())[:8]):
        gid = f"GRP_{idx}"
        clean_gname = escape_mermaid_label(group_name)
        arch_lines.append(f'    subgraph {gid}["📁 {clean_gname}"]')
        for nid in nids[:5]:
            clean_id = sanitize_mermaid_id(nid)
            used_nodes.add(nid)
            name = escape_mermaid_label(node_map[nid].get("name", nid))
            arch_lines.append(f'        {clean_id}["📄 {name}"]')
        arch_lines.append('    end')

    added_edges = set()
    for e in raw_edges:
        src = e.get("source")
        tgt = e.get("target")
        if src in used_nodes and tgt in used_nodes and src != tgt:
            etype = escape_mermaid_label(e.get("type", "uses"))
            pair = (src, tgt)
            if pair not in added_edges and len(added_edges) < 25:
                added_edges.add(pair)
                arch_lines.append(f'    {sanitize_mermaid_id(src)} -->|{etype}| {sanitize_mermaid_id(tgt)}')

    diagrams["understand_arch"] = {
        "title": "🏛️ Kiến Trúc Hệ Thống (Knowledge Graph Architecture)",
        "desc": f"Sơ đồ phân cấp cấu trúc thành phần từ đồ thị tri thức của {proj_name}: {proj_desc}",
        "code": "\n".join(arch_lines)
    }

    # Dependency Flow
    dep_lines = [
        "%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#ede9fe', 'primaryBorderColor': '#7c3aed', 'primaryTextColor': '#0f172a', 'secondaryColor': '#dcfce7', 'secondaryBorderColor': '#16a34a', 'secondaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%",
        "flowchart LR"
    ]
    
    code_nodes = [nid for nid, n in node_map.items() if "src" in n.get("filePath", "") or n.get("type") == "file"][:20]
    for nid in code_nodes:
        clean_id = sanitize_mermaid_id(nid)
        name = escape_mermaid_label(node_map[nid]["name"])
        dep_lines.append(f'    {clean_id}["⚙️ {name}"]')

    dep_set = set()
    for e in raw_edges:
        src = e.get("source")
        tgt = e.get("target")
        if src in code_nodes and tgt in code_nodes and src != tgt:
            pair = (src, tgt)
            if pair not in dep_set and len(dep_set) < 25:
                dep_set.add(pair)
                rel = escape_mermaid_label(e.get("type", "imports"))
                dep_lines.append(f'    {sanitize_mermaid_id(src)} -->|{rel}| {sanitize_mermaid_id(tgt)}')

    diagrams["understand_deps"] = {
        "title": "🔗 Liên Kết Phụ Thuộc Mô-Đun (Module Dependency)",
        "desc": "Mối quan hệ import và sử dụng giữa các module mã nguồn trong dự án",
        "code": "\n".join(dep_lines)
    }

    # Pipeline
    diagrams["pipeline"] = {
        "title": "🔄 Luồng Dữ Liệu & Vận Hành (Data Pipeline)",
        "desc": "Quy trình xử lý dữ liệu từ đầu vào đến lưu trữ và hiển thị kết quả",
        "code": """%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#dcfce7', 'primaryBorderColor': '#16a34a', 'primaryTextColor': '#0f172a', 'secondaryColor': '#fef9c3', 'secondaryBorderColor': '#ca8a04', 'secondaryTextColor': '#0f172a', 'tertiaryColor': '#fee2e2', 'tertiaryBorderColor': '#dc2626', 'tertiaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '15px' }, 'look': 'handDrawn'}}%%
flowchart LR
    INPUT["📥 Dữ liệu & Sự kiện"] --> ROUTER{"🧭 Điều phối & Xác thực"}
    ROUTER -->|Hợp lệ| EXEC["⚙️ Bộ Xử Lý Cốt Lõi"]
    ROUTER -->|Không hợp lệ| ERR["❌ Xử lý lỗi"]
    EXEC --> DB[("💾 Cơ sở dữ liệu & Bộ nhớ")]
    DB --> UI["🖥️ Giao diện người dùng"]
"""
    }

    # Sequence
    diagrams["sequence"] = {
        "title": "⏱️ Sơ Đồ Tuần Tự (Sequence Diagram)",
        "desc": "Luồng trao đổi thông điệp tuần tự giữa Client, Controller và Database",
        "code": """%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#fee2e2', 'primaryBorderColor': '#dc2626', 'primaryTextColor': '#0f172a', 'secondaryColor': '#e0f2fe', 'secondaryBorderColor': '#0284c7', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%
sequenceDiagram
    autonumber
    actor User as 👤 Người Dùng
    participant UI as 🖥️ Giao Diện
    participant Core as ⚙️ Bộ Xử Lý
    participant Storage as 💾 Lưu Trữ

    User->>UI: 1. Thao tác / Gửi yêu cầu
    UI->>Core: 2. Kích hoạt xử lý với tham số
    Core->>Storage: 3. Đọc / Ghi dữ liệu
    Storage-->>Core: 4. Trả về kết quả
    Core-->>UI: 5. Cập nhật trạng thái
    UI-->>User: 6. Hiển thị hoàn tất
"""
    }

    return diagrams


def scan_project_structure(project_root: Path) -> dict:
    """Tự động phân tích ngôn ngữ và cấu trúc dự án bất kỳ (Fallback khi không có Knowledge Graph)."""
    project_root = project_root.resolve()
    
    is_python = any(project_root.glob("*.py")) or (project_root / "src").exists() or (project_root / "requirements.txt").exists() or (project_root / "pyproject.toml").exists()
    is_node = (project_root / "package.json").exists() or (project_root / "node_modules").exists()
    is_go = (project_root / "go.mod").exists() or any(project_root.glob("*.go"))
    is_rust = (project_root / "Cargo.toml").exists()

    file_tree = {}
    total_files = 0

    ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build', '.next', '.cache', 'graphify-out'}

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        rel_root = Path(root).relative_to(project_root).as_posix()
        
        valid_files = [f for f in files if not f.startswith('.') and not f.endswith(('.pyc', '.exe', '.dll', '.so', '.dylib'))]
        if valid_files:
            file_tree[rel_root] = valid_files[:15]
            total_files += len(valid_files)

    return {
        "root_name": project_root.name,
        "is_python": is_python,
        "is_node": is_node,
        "is_go": is_go,
        "is_rust": is_rust,
        "file_tree": file_tree,
        "total_files": total_files
    }


def scan_python_ast(project_root: Path) -> dict:
    """Quét AST mã nguồn Python nếu là dự án Python."""
    classes = {}
    functions = {}
    calls = []

    files_to_scan = list(project_root.glob("src/**/*.py")) + list(project_root.glob("*.py"))
    
    for file_path in files_to_scan[:40]:
        if "__pycache__" in str(file_path):
            continue
        rel_path = file_path.relative_to(project_root).as_posix()
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8", errors="ignore"), filename=str(file_path))
        except Exception:
            continue

        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                child.parent = parent

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes[node.name] = {
                    "file": rel_path,
                    "methods": methods[:6],
                    "bases": [b.id for b in node.bases if isinstance(b, ast.Name)]
                }
            elif isinstance(node, ast.FunctionDef) and not isinstance(getattr(node, 'parent', None), ast.ClassDef):
                functions[node.name] = {
                    "file": rel_path,
                    "args": [a.arg for a in node.args.args][:4]
                }
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append({"caller_file": rel_path, "target": node.func.id})
                elif isinstance(node.func, ast.Attribute):
                    calls.append({"caller_file": rel_path, "target": node.func.attr})

    return {"classes": classes, "functions": functions, "calls": calls}


def generate_mermaid_from_project(project_info: dict, ast_data: dict = None) -> dict:
    """Tự động sinh các mẫu sơ đồ Mermaid phong cách Excalidraw cho dự án thông thường."""
    root_name = project_info["root_name"]
    diagrams = {}

    # --- SƠ ĐỒ 1: KIẾN TRÚC MÔ-ĐUN TỔNG THỂ ---
    flow_lines = [
        "%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e0f2fe', 'primaryBorderColor': '#0284c7', 'primaryTextColor': '#0f172a', 'secondaryColor': '#fef3c7', 'secondaryBorderColor': '#d97706', 'secondaryTextColor': '#0f172a', 'tertiaryColor': '#f3e8ff', 'tertiaryBorderColor': '#9333ea', 'tertiaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '15px' }, 'look': 'handDrawn'}}%%",
        "flowchart TD"
    ]

    sub_idx = 0
    dir_nodes = {}
    for rel_dir, files in list(project_info["file_tree"].items())[:8]:
        sub_id = f"DIR_{sub_idx}"
        sub_idx += 1
        disp_name = rel_dir if rel_dir != "." else f"📦 {root_name} (Root)"
        flow_lines.append(f'    subgraph {sub_id}["📁 {disp_name}"]')
        
        for f in files[:5]:
            file_node_id = f"F_{sub_idx}_{abs(hash(f)) % 10000}"
            dir_nodes[f] = file_node_id
            flow_lines.append(f'        {file_node_id}["📄 {f}"]')
        flow_lines.append('    end')

    root_files = project_info["file_tree"].get(".", [])
    for rf in root_files[:3]:
        rf_id = dir_nodes.get(rf)
        if rf_id:
            for other_f, of_id in dir_nodes.items():
                if of_id != rf_id and not any(other_f == r for r in root_files):
                    flow_lines.append(f'    {rf_id} -->|Imports / Coordinates| {of_id}')
                    break

    diagrams["overview"] = {
        "title": "🏛️ Kiến Trúc Thư Mục & Mô-Đun (Module Overview)",
        "desc": f"Sơ đồ phân cấp cấu trúc mô-đun chính của dự án {root_name}",
        "code": "\n".join(flow_lines)
    }

    # --- SƠ ĐỒ 2: NẾU LÀ PYTHON VÀ CÓ AST ---
    if ast_data and (ast_data["classes"] or ast_data["functions"]):
        ast_lines = [
            "%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#ede9fe', 'primaryBorderColor': '#7c3aed', 'primaryTextColor': '#0f172a', 'secondaryColor': '#dcfce7', 'secondaryBorderColor': '#16a34a', 'secondaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%",
            "flowchart TD"
        ]

        class_node_map = {}
        for cname, cinfo in list(ast_data["classes"].items())[:15]:
            cid = f"CLS_{abs(hash(cname)) % 10000}"
            class_node_map[cname] = cid
            methods_txt = "<br/>• ".join(cinfo["methods"][:4])
            if methods_txt:
                methods_txt = "<br/>• " + methods_txt
            ast_lines.append(f'    {cid}["🏛️ class <b>{cname}</b><br/><i>({cinfo["file"]})</i>{methods_txt}"]')

        for fname, finfo in list(ast_data["functions"].items())[:10]:
            fid = f"FN_{abs(hash(fname)) % 10000}"
            class_node_map[fname] = fid
            ast_lines.append(f'    {fid}["⚙️ def <b>{fname}()</b><br/><i>({finfo["file"]})</i>"]')

        added = set()
        for call in ast_data["calls"]:
            tgt = call["target"]
            if tgt in class_node_map:
                for src_name, src_info in ast_data["classes"].items():
                    if src_info["file"] == call["caller_file"] and src_name != tgt:
                        pair = (src_name, tgt)
                        if pair not in added:
                            added.add(pair)
                            ast_lines.append(f'    {class_node_map[src_name]} -->|Calls/Uses| {class_node_map[tgt]}')

        diagrams["ast_live"] = {
            "title": "🔍 Sơ Đồ Code & Quan Hệ Hàm (Live AST)",
            "desc": "Trích xuất tự động các Class, Function và mối quan hệ thực tế trong mã nguồn",
            "code": "\n".join(ast_lines)
        }

    # --- SƠ ĐỒ 3: LUỒNG DỮ LIỆU MẪU (DATA PIPELINE) ---
    diagrams["pipeline"] = {
        "title": "🔄 Luồng Dữ Liệu & Xử Lý (Data Flow / Pipeline)",
        "desc": "Mô tả chu trình tiếp nhận dữ liệu đầu vào, xử lý qua các tầng và xuất kết quả",
        "code": """%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#dcfce7', 'primaryBorderColor': '#16a34a', 'primaryTextColor': '#0f172a', 'secondaryColor': '#fef9c3', 'secondaryBorderColor': '#ca8a04', 'secondaryTextColor': '#0f172a', 'tertiaryColor': '#fee2e2', 'tertiaryBorderColor': '#dc2626', 'tertiaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '15px' }, 'look': 'handDrawn'}}%%
flowchart LR
    INPUT["📥 Dữ liệu đầu vào<br/>(Input Data / Request)"] --> AUTH{"🔐 Kiểm tra & Xác thực"}
    
    AUTH -->|Hợp lệ| PROCESS["⚙️ Xử lý Logic cốt lõi<br/>(Core Processing Engine)"]
    AUTH -->|Không hợp lệ| ERR["❌ Báo lỗi & Ghi log"]

    PROCESS --> ENHANCE["✨ Tối ưu & Tinh chỉnh dữ liệu"]
    ENHANCE --> STORE[("💾 Lưu trữ kết quả<br/>(Database / File Storage)")]
    STORE --> OUTPUT["📤 Xuất kết quả<br/>(Response / Export File)"]
"""
    }

    # --- SƠ ĐỒ 4: SƠ ĐỒ TUẦN TỰ (SEQUENCE / CALL FLOW) ---
    diagrams["sequence"] = {
        "title": "⏱️ Sơ Đồ Tuần Tự (Sequence Diagram)",
        "desc": "Luồng trao đổi thông điệp tuần tự giữa Client, Presenter/Controller và Service/Database",
        "code": """%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#fee2e2', 'primaryBorderColor': '#dc2626', 'primaryTextColor': '#0f172a', 'secondaryColor': '#e0f2fe', 'secondaryBorderColor': '#0284c7', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%
sequenceDiagram
    autonumber
    actor User as 👤 Người Dùng
    participant UI as 🖥️ Giao Diện (UI / View)
    participant Core as ⚙️ Bộ Xử Lý (Core Engine)
    participant Storage as 💾 Lưu Trữ (Disk / DB)

    User->>UI: 1. Thao tác / Gửi yêu cầu
    UI->>Core: 2. Kích hoạt xử lý với tham số
    Core->>Storage: 3. Đọc dữ liệu gốc
    Storage-->>Core: 4. Trả về luồng dữ liệu
    Core->>Core: 5. Thực hiện tính toán & biến đổi
    Core->>Storage: 6. Ghi dữ liệu đã xử lý
    Core-->>UI: 7. Cập nhật tiến độ & hoàn tất
    UI-->>User: 8. Hiển thị thông báo thành công
"""
    }

    return diagrams


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Excali-Flow Architecture Visualizer</title>
  
  <script>__MERMAID_RUNTIME__</script>
  <script>__PANZOOM_RUNTIME__</script>

  <style>
    :root {
      --bg-canvas: #f8f9fa;
      --bg-panel: #ffffff;
      --border-color: #e2e8f0;
      --text-main: #1e293b;
      --text-muted: #64748b;
      --primary: #4f46e5;
      --primary-hover: #4338ca;
      --accent: #f59e0b;
      --font-hand: 'Shantell Sans', 'Caveat', 'Virgil', cursive, sans-serif;
      --font-ui: 'Inter', system-ui, -apple-system, sans-serif;
      --font-code: 'Fira Code', monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: var(--font-ui);
      background-color: var(--bg-canvas);
      color: var(--text-main);
      display: flex;
      height: 100vh;
      width: 100vw;
      overflow: hidden;
    }

    #sidebar {
      width: 460px;
      min-width: 460px;
      max-width: 460px;
      background: var(--bg-panel);
      border-right: 2px solid var(--border-color);
      display: flex;
      flex-direction: column;
      box-shadow: 4px 0 15px rgba(0,0,0,0.03);
      z-index: 10;
      margin-left: 0;
      opacity: 1;
      pointer-events: auto;
      transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease;
    }

    #sidebar.collapsed {
      margin-left: -460px;
      opacity: 0;
      pointer-events: none;
    }

    .header-bar {
      padding: 16px 20px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #fafafa;
    }

    .header-title {
      font-family: var(--font-hand);
      font-size: 1.4rem;
      font-weight: 700;
      color: #0f172a;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .badge {
      font-family: var(--font-ui);
      font-size: 0.7rem;
      font-weight: 600;
      background: #e0e7ff;
      color: #3730a3;
      padding: 2px 8px;
      border-radius: 12px;
      text-transform: uppercase;
    }

    .icon-btn {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.9rem;
      color: var(--text-muted);
      transition: all 0.15s ease;
    }

    .icon-btn:hover {
      background: #e2e8f0;
      color: var(--text-main);
    }

    .tabs-nav {
      display: flex;
      padding: 8px 12px 0 12px;
      gap: 6px;
      border-bottom: 1px solid var(--border-color);
      background: #f8fafc;
      overflow-x: auto;
    }

    .tab-btn {
      padding: 8px 14px;
      font-size: 0.85rem;
      font-weight: 600;
      background: transparent;
      border: 1px solid transparent;
      border-bottom: none;
      border-radius: 8px 8px 0 0;
      color: var(--text-muted);
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }

    .tab-btn:hover {
      color: var(--text-main);
      background: #e2e8f0;
    }

    .tab-btn.active {
      background: var(--bg-panel);
      color: var(--primary);
      border-color: var(--border-color);
      border-bottom: 1px solid var(--bg-panel);
      margin-bottom: -1px;
    }

    .editor-section {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 16px;
      gap: 10px;
      min-height: 0;
    }

    .editor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .editor-desc {
      font-size: 0.82rem;
      color: var(--text-muted);
      line-height: 1.4;
    }

    #mermaid-code {
      flex: 1;
      width: 100%;
      font-family: var(--font-code);
      font-size: 0.82rem;
      line-height: 1.45;
      padding: 12px;
      border-radius: 8px;
      border: 1px solid var(--border-color);
      background: #0f172a;
      color: #f8fafc;
      resize: none;
      outline: none;
    }

    #mermaid-code:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
    }

    .btn-row {
      display: flex;
      gap: 8px;
    }

    .btn {
      padding: 9px 14px;
      font-size: 0.85rem;
      font-weight: 600;
      border-radius: 6px;
      cursor: pointer;
      border: 1px solid var(--border-color);
      background: #ffffff;
      color: var(--text-main);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.15s ease;
    }

    .btn:hover {
      background: #f1f5f9;
      border-color: #cbd5e1;
    }

    .btn-primary {
      background: var(--primary);
      color: #ffffff;
      border-color: var(--primary);
    }

    .btn-primary:hover {
      background: var(--primary-hover);
    }

    #viewport {
      flex: 1;
      position: relative;
      background: 
        radial-gradient(circle, #cbd5e1 1px, transparent 1px);
      background-size: 24px 24px;
      background-color: #fdfbf7; /* Warm Excalidraw paper */
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.3s ease;
      min-width: 0;
    }

    #panzoom-container {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: grab;
      overflow: hidden;
    }

    #panzoom-container:active {
      cursor: grabbing;
    }

    #diagram-output {
      padding: 40px;
      display: inline-block;
      user-select: none;
      transform-origin: center center;
    }

    #diagram-output > svg {
      display: block;
      width: auto;
      height: auto;
      max-width: none;
      max-height: none;
      overflow: visible;
    }

    .floating-toolbar {
      position: absolute;
      bottom: 24px;
      right: 24px;
      display: flex;
      align-items: center;
      gap: 6px;
      background: #ffffff;
      padding: 6px 12px;
      border-radius: 12px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
      border: 1px solid var(--border-color);
      z-index: 20;
    }

    .tool-btn {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 1.05rem;
      color: var(--text-main);
      transition: background 0.15s;
    }

    .tool-btn:hover {
      background: #f1f5f9;
    }

    .zoom-badge {
      font-family: var(--font-ui);
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--text-muted);
      background: #f1f5f9;
      padding: 4px 8px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      min-width: 48px;
      user-select: none;
    }

    /* Toggle Button CSS - Chỉ hiển thị khi Sidebar bị thu gọn */
    .toggle-sidebar-btn {
      position: absolute;
      top: 16px;
      left: 16px;
      z-index: 30;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 8px -1px rgba(0,0,0,0.08);
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      color: var(--text-main);
    }

    .toggle-sidebar-btn:hover {
      background: #f8fafc;
      box-shadow: 0 6px 12px -2px rgba(0,0,0,0.12);
    }

    /* Ẩn nút toggle khi Sidebar đang mở để tránh đè lên tiêu đề header */
    #sidebar:not(.collapsed) + #toggle-sidebar {
      opacity: 0;
      pointer-events: none;
      transform: translateX(-20px);
    }

    #sidebar.collapsed + #toggle-sidebar {
      opacity: 1;
      pointer-events: auto;
      transform: translateX(0);
    }

    .mermaid text {
      font-family: var(--font-hand) !important;
      font-size: 15px !important;
      letter-spacing: 0.2px;
    }

    .error-box {
      background: #fee2e2;
      border: 1px solid #ef4444;
      color: #991b1b;
      padding: 12px;
      border-radius: 8px;
      font-size: 0.85rem;
      display: none;
    }

    /* Reach Tracing & Isolation */
    .node {
      cursor: pointer !important;
      transition: opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1), filter 0.25s cubic-bezier(0.4, 0, 0.2, 1), transform 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .node:hover {
      filter: drop-shadow(0 0 10px rgba(99, 102, 241, 0.7)) !important;
    }
    .node.reach-focused {
      filter: drop-shadow(0 0 18px #f59e0b) drop-shadow(0 0 6px #f59e0b) !important;
      opacity: 1 !important;
      transform-origin: center;
      transform: scale(1.05);
    }
    .node.reach-focused rect, .node.reach-focused path, .node.reach-focused polygon, .node.reach-focused circle {
      stroke: #f59e0b !important;
      stroke-width: 3.5px !important;
      fill: #fef3c7 !important;
    }
    .node.reach-focused foreignObject div, .node.reach-focused .nodeLabel, .node.reach-focused text {
      color: #78350f !important;
      fill: #78350f !important;
      font-weight: 800 !important;
    }
    .node.reach-upstream {
      filter: drop-shadow(0 0 14px #0284c7) drop-shadow(0 0 5px #38bdf8) !important;
      opacity: 1 !important;
      transform-origin: center;
      transform: scale(1.02);
    }
    .node.reach-upstream rect, .node.reach-upstream path, .node.reach-upstream polygon, .node.reach-upstream circle {
      stroke: #0284c7 !important;
      stroke-width: 3px !important;
      fill: #e0f2fe !important;
    }
    .node.reach-upstream foreignObject div, .node.reach-upstream .nodeLabel, .node.reach-upstream text {
      color: #0369a1 !important;
      fill: #0369a1 !important;
      font-weight: 800 !important;
    }
    .node.reach-downstream {
      filter: drop-shadow(0 0 14px #16a34a) drop-shadow(0 0 5px #4ade80) !important;
      opacity: 1 !important;
      transform-origin: center;
      transform: scale(1.02);
    }
    .node.reach-downstream rect, .node.reach-downstream path, .node.reach-downstream polygon, .node.reach-downstream circle {
      stroke: #16a34a !important;
      stroke-width: 3px !important;
      fill: #dcfce7 !important;
    }
    .node.reach-downstream foreignObject div, .node.reach-downstream .nodeLabel, .node.reach-downstream text {
      color: #14532d !important;
      fill: #14532d !important;
      font-weight: 800 !important;
    }
    .node.reach-dimmed {
      opacity: 0.34 !important;
      filter: none !important;
    }
    .edgePath, .edgePaths > g, path.flowchart-link {
      transition: opacity 0.25s ease, stroke-width 0.25s ease, stroke 0.25s ease !important;
    }
    .edgePath.reach-highlight-up path,
    .edgePaths > g.reach-highlight-up path,
    path.flowchart-link.reach-highlight-up {
      stroke: #0284c7 !important;
      stroke-width: 3.5px !important;
      opacity: 1 !important;
      filter: drop-shadow(0 0 6px rgba(2, 132, 199, 0.9)) !important;
    }
    .edgePath.reach-highlight-down path,
    .edgePaths > g.reach-highlight-down path,
    path.flowchart-link.reach-highlight-down {
      stroke: #16a34a !important;
      stroke-width: 3.5px !important;
      opacity: 1 !important;
      filter: drop-shadow(0 0 6px rgba(22, 163, 74, 0.9)) !important;
    }
    .edgePath.reach-dimmed, .edgePaths > g.reach-dimmed, path.flowchart-link.reach-dimmed,
    .edgeLabel.reach-dimmed {
      opacity: 0.16 !important;
    }

    /* Animated Signal Flow (Stream of Glowing Photons) */
    @keyframes signalFlowMotion {
      from { stroke-dashoffset: 36; }
      to { stroke-dashoffset: 0; }
    }
    .flow-animated .edgePath path,
    .flow-animated .edgePaths path,
    .flow-animated path.flowchart-link,
    .flow-animated path.path,
    .flow-animated .edge-thickness-normal,
    .flow-animated svg path[id*="L-"],
    .flow-animated svg path[id*="L_"] {
      stroke-dasharray: 8 6 !important;
      stroke: #6366f1 !important;
      stroke-width: 3px !important;
      animation: signalFlowMotion 0.85s linear infinite !important;
      filter: drop-shadow(0 0 5px rgba(99, 102, 241, 0.9)) !important;
      opacity: 1 !important;
    }
    .flow-animated marker path,
    .flow-animated marker polygon {
      fill: #6366f1 !important;
      stroke: #6366f1 !important;
      filter: drop-shadow(0 0 4px rgba(99, 102, 241, 0.9)) !important;
    }

    /* Reach Info Floating Bar */
    .reach-info-bar {
      position: absolute;
      top: 16px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 25;
      background: rgba(15, 23, 42, 0.92);
      color: #ffffff;
      padding: 8px 18px;
      border-radius: 30px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.25);
      font-size: 0.85rem;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 12px;
      backdrop-filter: blur(8px);
      border: 1px solid rgba(255,255,255,0.15);
      animation: fadeInDown 0.25s ease;
    }
    .reach-pill {
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 0.75rem;
      font-weight: 700;
    }
    .reach-pill-up { background: #0284c7; color: #ffffff; }
    .reach-pill-down { background: #16a34a; color: #ffffff; }
    .reach-clear-btn {
      background: rgba(255,255,255,0.2);
      border: none;
      color: #ffffff;
      padding: 3px 10px;
      border-radius: 12px;
      cursor: pointer;
      font-size: 0.78rem;
      transition: background 0.15s;
    }
    .reach-clear-btn:hover { background: rgba(255,255,255,0.35); }
    @keyframes fadeInDown {
      from { opacity: 0; transform: translate(-50%, -10px); }
      to { opacity: 1; transform: translate(-50%, 0); }
    }
  </style>
</head>
<body>

  <aside id="sidebar">
    <div class="header-bar">
      <div class="header-title">
        <span>🎨 Excali-Flow</span>
        <span class="badge">Ultra v3.5</span>
      </div>
      <button id="btn-collapse-sidebar" class="icon-btn" title="Thu gọn Sidebar (Ctrl+B)">◀</button>
    </div>

    <nav class="tabs-nav" id="tabs-container"></nav>

    <div class="editor-section">
      <div class="editor-header">
        <div class="editor-desc" id="tab-desc">Mô tả sơ đồ</div>
      </div>

      <textarea id="mermaid-code" spellcheck="false" placeholder="Nhập mã Mermaid tại đây..."></textarea>
      
      <div id="error-msg" class="error-box"></div>

      <div class="btn-row">
        <button id="btn-render" class="btn btn-primary" style="flex: 2;">
          <span>⚡ Cập Nhật Sơ Đồ</span>
        </button>
        <button id="btn-copy" class="btn" style="flex: 1;">
          <span>📋 Sao Chép</span>
        </button>
      </div>
    </div>
  </aside>

  <button id="toggle-sidebar" class="toggle-sidebar-btn" title="Mở bảng điều khiển (Ctrl+B)">
    <span>✏️</span> <span>Mở Bảng Điều Khiển</span>
  </button>

  <main id="viewport">
    <div id="reach-bar" class="reach-info-bar" style="display: none;">
      <span id="reach-title">🔍 Reach Tracing</span>
      <span class="reach-pill reach-pill-up" id="reach-up-count">0 Upstream</span>
      <span class="reach-pill reach-pill-down" id="reach-down-count">0 Downstream</span>
      <button id="reach-clear-btn" class="reach-clear-btn">✕ Bỏ chọn</button>
    </div>

    <div id="panzoom-container">
      <div id="diagram-output" class="mermaid"></div>
    </div>

    <div class="floating-toolbar">
      <button id="toggle-flow" class="tool-btn" title="Bật/Tắt Luồng chuyển động (Animated Signal Flow)" style="font-size: 0.85rem; width: auto; padding: 0 10px; font-weight: 600;">✨ Luồng</button>
      <div style="width: 1px; height: 24px; background: var(--border-color); margin: 0 4px;"></div>
      <button id="zoom-in" class="tool-btn" title="Phóng to (Zoom In)">➕</button>
      <button id="zoom-out" class="tool-btn" title="Thu nhỏ (Zoom Out)">➖</button>
      <button id="zoom-reset" class="tool-btn" title="Về mặc định (Reset)">🎯</button>
      <button id="zoom-fit" class="tool-btn" title="Vừa khung hình (Fit to Screen)">📐</button>
      <span id="zoom-badge" class="zoom-badge">100%</span>
      <div style="width: 1px; height: 24px; background: var(--border-color); margin: 0 4px;"></div>
      <button id="export-svg" class="tool-btn" title="Tải file Vector SVG">🖼️ SVG</button>
      <button id="export-png" class="tool-btn" title="Tải ảnh PNG">📷 PNG</button>
      <button id="export-card" class="tool-btn" title="Xuất Thẻ Ảnh Bìa 1200×630 (README / Social Share Card)" style="font-size: 0.85rem; width: auto; padding: 0 10px; font-weight: 600;">🎴 Card</button>
    </div>
  </main>

  <script>
    const diagrams = __DIAGRAMS_DATA__;

    let currentTab = Object.keys(diagrams)[0];
    let panzoomInstance = null;
    let renderGeneration = 0;

    mermaid.initialize({
      startOnLoad: false,
      look: 'handDrawn',
      theme: 'base',
      fontFamily: '"Shantell Sans", "Caveat", "Virgil", cursive, sans-serif',
      themeVariables: {
        fontFamily: '"Shantell Sans", "Caveat", "Virgil", cursive, sans-serif',
        fontSize: '15px',
        primaryColor: '#e0f2fe',
        primaryBorderColor: '#0284c7',
        primaryTextColor: '#0f172a',
        secondaryColor: '#fef3c7',
        secondaryBorderColor: '#d97706',
        secondaryTextColor: '#0f172a',
        tertiaryColor: '#f3e8ff',
        tertiaryBorderColor: '#9333ea',
        tertiaryTextColor: '#0f172a',
        lineColor: '#334155',
        edgeLabelBackground: '#ffffff'
      }
    });

    const codeArea = document.getElementById('mermaid-code');
    const descArea = document.getElementById('tab-desc');
    const tabsContainer = document.getElementById('tabs-container');
    const diagramOutput = document.getElementById('diagram-output');
    const panzoomContainer = document.getElementById('panzoom-container');
    const zoomBadge = document.getElementById('zoom-badge');
    const errorBox = document.getElementById('error-msg');

    function setupTabs() {
      tabsContainer.innerHTML = '';
      Object.keys(diagrams).forEach(key => {
        const btn = document.createElement('button');
        btn.className = `tab-btn ${key === currentTab ? 'active' : ''}`;
        btn.textContent = diagrams[key].title.split('(')[0].trim();
        btn.onclick = () => selectTab(key);
        tabsContainer.appendChild(btn);
      });
    }

    function selectTab(key) {
      currentTab = key;
      setupTabs();
      descArea.textContent = diagrams[key].desc;
      codeArea.value = diagrams[key].code.trim();
      renderDiagram();
    }

    function updateZoomBadge(scale) {
      if (zoomBadge) {
        zoomBadge.textContent = `${Math.round((scale || 1) * 100)}%`;
      }
    }

    function fitToScreen() {
      if (!panzoomInstance) return;
      const svg = diagramOutput.querySelector('svg');
      if (!svg) {
        panzoomInstance.reset();
        updateZoomBadge(panzoomInstance.getScale());
        return;
      }

      const containerRect = panzoomContainer.getBoundingClientRect();
      const svgRect = svg.getBoundingClientRect();
      let bounds = null;
      try { bounds = svg.querySelector('g')?.getBBox(); } catch (e) {}
      const svgWidth = bounds?.width || svg.viewBox?.baseVal?.width || svgRect.width || 800;
      const svgHeight = bounds?.height || svg.viewBox?.baseVal?.height || svgRect.height || 600;

      const padding = 80;
      const availableWidth = Math.max(containerRect.width - padding * 2, 200);
      const availableHeight = Math.max(containerRect.height - padding * 2, 200);

      const scaleX = availableWidth / svgWidth;
      const scaleY = availableHeight / svgHeight;
      let targetScale = Math.min(scaleX, scaleY, 2.5);
      if (targetScale < 0.1) targetScale = 0.1;

      panzoomInstance.reset({ animate: false });
      panzoomInstance.zoom(targetScale, { animate: false });
      const centeredX = (containerRect.width - svgWidth * targetScale) / 2;
      const centeredY = (containerRect.height - svgHeight * targetScale) / 2;
      panzoomInstance.pan(centeredX, centeredY, { animate: false });
      updateZoomBadge(targetScale);
    }

    // Attach wheel event on container once to avoid memory leaks
    panzoomContainer.addEventListener('wheel', (event) => {
      if (!panzoomInstance) return;
      panzoomInstance.zoomWithWheel(event);
    }, { passive: false });

    // Gắn panzoomchange trên diagramOutput một lần duy nhất tránh tích lũy listener
    diagramOutput.addEventListener('panzoomchange', (event) => {
      updateZoomBadge(event.detail.scale);
    });

    async function renderDiagram() {
      const generation = ++renderGeneration;
      const code = codeArea.value.trim();
      errorBox.style.display = 'none';
      if (panzoomInstance) {
        try { panzoomInstance.destroy(); } catch (e) {}
        panzoomInstance = null;
      }
      diagramOutput.innerHTML = '<div style="font-family: var(--font-hand); font-size: 1.2rem; color: #64748b;">⏳ Đang vẽ sơ đồ phác thảo...</div>';

      try {
        const id = `render-${generation}-${Date.now()}`;
        const { svg } = await mermaid.render(id, code);
        if (generation !== renderGeneration) return;
        diagramOutput.innerHTML = svg;
        const renderedSvg = diagramOutput.querySelector('svg');
        const viewBox = renderedSvg?.viewBox?.baseVal;
        if (!renderedSvg || !viewBox || !viewBox.width || !viewBox.height) {
          throw new Error('Mermaid returned an SVG without a usable viewBox.');
        }
        renderedSvg.setAttribute('width', `${viewBox.width}px`);
        renderedSvg.setAttribute('height', `${viewBox.height}px`);
        renderedSvg.style.width = `${viewBox.width}px`;
        renderedSvg.style.height = `${viewBox.height}px`;
        diagramOutput.style.width = `${viewBox.width}px`;
        diagramOutput.style.height = `${viewBox.height}px`;

        panzoomInstance = Panzoom(diagramOutput, {
          maxScale: 6,
          minScale: 0.1,
          step: 0.2,
          canvas: true,
          excludeClass: 'panzoom-exclude'
        });

        setupReachTracing(renderedSvg);
        requestAnimationFrame(() => requestAnimationFrame(fitToScreen));
      } catch (err) {
        if (generation !== renderGeneration) return;
        console.error(err);
        errorBox.style.display = 'block';
        errorBox.textContent = '❌ Lỗi cú pháp Mermaid: ' + (err.message || err);
        diagramOutput.innerHTML = '<div style="max-width: 520px; padding: 24px; color: #b91c1c; background: #fff1f2; border: 1px solid #fecdd3; border-radius: 12px; font-family: Arial, sans-serif;">Mermaid could not render this diagram. Read the error message in the left panel, then simplify the selected graph.</div>';
      }
    }

    // --- Interactive Reach Tracing Engine ---
    let activeReachNode = null;

    function clearReachTracing() {
      activeReachNode = null;
      const reachBar = document.getElementById('reach-bar');
      if (reachBar) reachBar.style.display = 'none';

      const nodes = diagramOutput.querySelectorAll('.node, g[id*="flowchart-"]');
      nodes.forEach(n => {
        n.classList.remove('reach-focused', 'reach-upstream', 'reach-downstream', 'reach-dimmed');
        n.style.opacity = '1';
        n.style.transform = '';
        n.querySelectorAll('path, rect, circle, polygon').forEach(shape => {
          shape.style.stroke = '';
          shape.style.strokeWidth = '';
          shape.style.fill = '';
        });
        n.querySelectorAll('.nodeLabel, text, span, div').forEach(txt => {
          txt.style.color = '';
          txt.style.fontWeight = '';
        });
      });

      const edgePaths = diagramOutput.querySelectorAll('.edgePath, .edgePaths > g, path.flowchart-link, .edgeLabel');
      edgePaths.forEach(e => {
        e.classList.remove('reach-highlight-up', 'reach-highlight-down', 'reach-dimmed');
        e.style.opacity = '1';
        e.querySelectorAll('path').forEach(p => {
          p.style.stroke = '';
          p.style.strokeWidth = '';
        });
      });
    }

    function normalizeId(id) {
      if (!id) return '';
      let s = String(id).trim();
      s = s.replace(/^flowchart-/, '').replace(/-\d+$/, '');
      return s;
    }

    function setupReachTracing(svgElement) {
      if (!svgElement) return;
      clearReachTracing();

      const nodes = Array.from(svgElement.querySelectorAll('.node, g[id*="flowchart-"]'));
      if (!nodes.length) return;
      const nodeEntries = nodes.map(elem => ({
        elem,
        id: normalizeId(elem.id || elem.textContent?.trim().split(/\s+/)[0] || ''),
        shapes: Array.from(elem.querySelectorAll('path, rect, circle, polygon')),
        texts: Array.from(elem.querySelectorAll('.nodeLabel, text, span, div'))
      }));

      const code = codeArea.value;
      const adjOut = new Map(); // src -> Set(target)
      const adjIn = new Map();  // target -> Set(src)

      // 1. Infallible multi-syntax Mermaid Edge Parser
      const lines = code.split('\n');
      lines.forEach(line => {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('%%') || trimmed.startsWith('subgraph') || trimmed.startsWith('flowchart') || trimmed.startsWith('graph')) return;

        const m = trimmed.match(/^([A-Za-z0-9_]+)(?:\[.*?\]|\(.*?\)|\{.*?\}|\>.*?\])?\s*(?:-->|-.->|==>|---|-->\s*\|[^|]+\||-\.->\s*\|[^|]+\||==>\s*\|[^|]+\||--\s*\|[^|]+\|\s*-->|--\s*[^-\n\r|]+\s*-->)\s*([A-Za-z0-9_]+)/);
        if (m) {
          const u = normalizeId(m[1]);
          const v = normalizeId(m[2]);
          if (u && v && u !== v) {
            if (!adjOut.has(u)) adjOut.set(u, new Set());
            if (!adjIn.has(v)) adjIn.set(v, new Set());
            adjOut.get(u).add(v);
            adjIn.get(v).add(u);
          }
        }
      });

      // 2. Also parse Mermaid SVG edge classes: LS-NodeA LE-NodeB or L-NodeA-NodeB
      const edgeContainers = Array.from(svgElement.querySelectorAll('.edgePath, .edgePaths > g'));
      const edgeContainerSet = new Set(edgeContainers);
      const standaloneEdgePaths = Array.from(svgElement.querySelectorAll('path.flowchart-link')).filter(path => {
        let parent = path.parentElement;
        while (parent && parent !== svgElement) {
          if (edgeContainerSet.has(parent)) return false;
          parent = parent.parentElement;
        }
        return true;
      });
      const edgeElems = [...edgeContainers, ...standaloneEdgePaths];
      const edgeEntries = [];
      edgeElems.forEach(edge => {
        let cls = edge.getAttribute('class') || '';
        let edgeId = edge.getAttribute('id') || '';
        let ls = cls.match(/LS-([A-Za-z0-9_\-]+)/);
        let le = cls.match(/LE-([A-Za-z0-9_\-]+)/);
        let u = ls ? normalizeId(ls[1]) : '';
        let v = le ? normalizeId(le[1]) : '';

        if (!u || !v) {
          let mId = edgeId.match(/L[_-]([A-Za-z0-9_]+)[_-]([A-Za-z0-9_]+)/);
          if (mId) {
            u = normalizeId(mId[1]);
            v = normalizeId(mId[2]);
          }
        }

        if (u && v) {
          if (!adjOut.has(u)) adjOut.set(u, new Set());
          if (!adjIn.has(v)) adjIn.set(v, new Set());
          adjOut.get(u).add(v);
          adjIn.get(v).add(u);
        }
        const paths = edge.matches('path') ? [edge] : Array.from(edge.querySelectorAll('path'));
        edgeEntries.push({ u, v, elem: edge, paths });
      });

      function handleNodeClick(node) {
        if (!node) return;
        const rawId = node.id || '';
        let startNodeId = normalizeId(rawId);
        if (!startNodeId) {
          const txt = node.textContent?.trim().split(/\s+/)[0] || '';
          startNodeId = normalizeId(txt) || rawId;
        }

        if (activeReachNode === startNodeId) {
          clearReachTracing();
          return;
        }
        activeReachNode = startNodeId;

        // Helper to get neighbors across ID variants
        function getOutNeighbors(curr) {
          const res = new Set();
          const keys = [curr, 'N_' + curr, curr.replace(/^N_/, '')];
          keys.forEach(k => {
            const s = adjOut.get(k);
            if (s) s.forEach(item => { res.add(normalizeId(item)); });
          });
          return Array.from(res);
        }

        function getInNeighbors(curr) {
          const res = new Set();
          const keys = [curr, 'N_' + curr, curr.replace(/^N_/, '')];
          keys.forEach(k => {
            const s = adjIn.get(k);
            if (s) s.forEach(item => { res.add(normalizeId(item)); });
          });
          return Array.from(res);
        }

        // BFS Upstream (Callers / Ancestors)
        const upstreamNodes = new Set([startNodeId]);
        const qUp = [startNodeId];
        let qUpIndex = 0;
        while (qUpIndex < qUp.length) {
          const curr = qUp[qUpIndex++];
          const preds = getInNeighbors(curr);
          preds.forEach(p => {
            if (!upstreamNodes.has(p) && p !== startNodeId) {
              upstreamNodes.add(p);
              qUp.push(p);
            }
          });
        }
        upstreamNodes.delete(startNodeId);

        // BFS Downstream (Dependencies / Successors)
        const downstreamNodes = new Set([startNodeId]);
        const qDown = [startNodeId];
        let qDownIndex = 0;
        while (qDownIndex < qDown.length) {
          const curr = qDown[qDownIndex++];
          const succs = getOutNeighbors(curr);
          succs.forEach(s => {
            if (!downstreamNodes.has(s) && s !== startNodeId) {
              downstreamNodes.add(s);
              qDown.push(s);
            }
          });
        }
        downstreamNodes.delete(startNodeId);

        // Apply Direct Inline Node Styling (100% Reliable across all browsers)
        nodeEntries.forEach(entry => {
          const n = entry.elem;
          const nId = entry.id;
          n.classList.remove('reach-focused', 'reach-upstream', 'reach-downstream', 'reach-dimmed');

          const isFocus = (nId === startNodeId || nId === 'N_' + startNodeId || startNodeId === 'N_' + nId || n === node);
          const isUp = upstreamNodes.has(nId) || upstreamNodes.has(nId.replace(/^N_/, '')) || upstreamNodes.has('N_' + nId);
          const isDown = downstreamNodes.has(nId) || downstreamNodes.has(nId.replace(/^N_/, '')) || downstreamNodes.has('N_' + nId);

          if (isFocus) {
            n.classList.add('reach-focused');
            n.style.opacity = '1';
            n.style.transform = 'scale(1.06)';
            entry.shapes.forEach(shape => {
              shape.style.stroke = '#f59e0b';
              shape.style.strokeWidth = '4px';
              shape.style.fill = '#fef3c7';
            });
            entry.texts.forEach(txt => {
              txt.style.color = '#78350f';
              txt.style.fontWeight = 'bold';
            });
          } else if (isUp) {
            n.classList.add('reach-upstream');
            n.style.opacity = '1';
            n.style.transform = 'scale(1.02)';
            entry.shapes.forEach(shape => {
              shape.style.stroke = '#0284c7';
              shape.style.strokeWidth = '3.5px';
              shape.style.fill = '#e0f2fe';
            });
            entry.texts.forEach(txt => {
              txt.style.color = '#0369a1';
              txt.style.fontWeight = 'bold';
            });
          } else if (isDown) {
            n.classList.add('reach-downstream');
            n.style.opacity = '1';
            n.style.transform = 'scale(1.02)';
            entry.shapes.forEach(shape => {
              shape.style.stroke = '#16a34a';
              shape.style.strokeWidth = '3.5px';
              shape.style.fill = '#dcfce7';
            });
            entry.texts.forEach(txt => {
              txt.style.color = '#14532d';
              txt.style.fontWeight = 'bold';
            });
          } else {
            n.classList.add('reach-dimmed');
            n.style.opacity = '0.34';
            n.style.transform = 'none';
            entry.shapes.forEach(shape => {
              shape.style.stroke = '';
              shape.style.strokeWidth = '';
              shape.style.fill = '';
            });
          }
        });

        // Apply Direct Inline Edge Styling
        edgeEntries.forEach(entry => {
          entry.elem.classList.remove('reach-highlight-up', 'reach-highlight-down', 'reach-dimmed');
          const u = entry.u;
          const v = entry.v;

          if (u && v) {
            const uFocus = (u === startNodeId || u === 'N_' + startNodeId);
            const vFocus = (v === startNodeId || v === 'N_' + startNodeId);
            const uUp = upstreamNodes.has(u) || upstreamNodes.has(u.replace(/^N_/, ''));
            const vUp = upstreamNodes.has(v) || upstreamNodes.has(v.replace(/^N_/, ''));
            const uDown = downstreamNodes.has(u) || downstreamNodes.has(u.replace(/^N_/, ''));
            const vDown = downstreamNodes.has(v) || downstreamNodes.has(v.replace(/^N_/, ''));

            if ((uUp || uFocus) && (vUp || vFocus) && (uUp || vUp)) {
              entry.elem.classList.add('reach-highlight-up');
              entry.elem.style.opacity = '1';
              entry.paths.forEach(p => {
                p.style.stroke = '#0284c7';
                p.style.strokeWidth = '4px';
              });
            } else if ((uDown || uFocus) && (vDown || vFocus) && (uDown || vDown)) {
              entry.elem.classList.add('reach-highlight-down');
              entry.elem.style.opacity = '1';
              entry.paths.forEach(p => {
                p.style.stroke = '#16a34a';
                p.style.strokeWidth = '4px';
              });
            } else {
              entry.elem.classList.add('reach-dimmed');
              entry.elem.style.opacity = '0.16';
              entry.paths.forEach(p => {
                p.style.stroke = '';
                p.style.strokeWidth = '';
              });
            }
          } else {
            entry.elem.classList.add('reach-dimmed');
            entry.elem.style.opacity = '0.16';
          }
        });

        // Show floating Reach Bar
        const reachBar = document.getElementById('reach-bar');
        const reachTitle = document.getElementById('reach-title');
        const reachUp = document.getElementById('reach-up-count');
        const reachDown = document.getElementById('reach-down-count');
        if (reachBar && reachTitle && reachUp && reachDown) {
          const labelText = node.querySelector('text, span, div')?.textContent?.trim() || startNodeId;
          reachTitle.innerHTML = `🎯 <b>Đang chọn:</b> ${htmlEscape(labelText.slice(0, 26))}`;
          reachUp.textContent = `🔵 ${upstreamNodes.size} Nút gọi đến (Upstream)`;
          reachDown.textContent = `🟢 ${downstreamNodes.size} Nút phụ thuộc (Downstream)`;
          reachBar.style.display = 'flex';
        }
      }

      // A node click is selection, never a Panzoom drag. Use one handler only
      // so one gesture cannot select and immediately clear the same node.
      nodes.forEach(node => {
        node.style.cursor = 'pointer';
        node.classList.add('panzoom-exclude');
        node.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          handleNodeClick(node);
        };
      });
    }

    function htmlEscape(str) {
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    const reachClearBtn = document.getElementById('reach-clear-btn');
    if (reachClearBtn) {
      reachClearBtn.onclick = clearReachTracing;
    }

    // --- Animated Signal Flow ---
    let isFlowAnimated = false;
    const toggleFlowBtn = document.getElementById('toggle-flow');
    if (toggleFlowBtn) {
      toggleFlowBtn.onclick = () => {
        isFlowAnimated = !isFlowAnimated;
        if (isFlowAnimated) {
          diagramOutput.classList.add('flow-animated');
          toggleFlowBtn.style.background = '#6366f1';
          toggleFlowBtn.style.color = '#ffffff';
          toggleFlowBtn.innerHTML = '<span>✨</span> <b>Luồng (Đang chạy)</b>';
        } else {
          diagramOutput.classList.remove('flow-animated');
          toggleFlowBtn.style.background = 'transparent';
          toggleFlowBtn.style.color = 'var(--text-main)';
          toggleFlowBtn.innerHTML = '<span>✨</span> <span>Luồng</span>';
        }
      };
    }

    // --- 1200x630 Social / README Share Card Generator ---
    const exportCardBtn = document.getElementById('export-card');
    if (exportCardBtn) {
      exportCardBtn.onclick = () => {
        const svgElement = diagramOutput.querySelector('svg');
        if (!svgElement) return alert('Chưa có sơ đồ để xuất Share Card!');

        const box = svgElement.viewBox?.baseVal;
        const svgW = (box && box.width) ? box.width : (svgElement.clientWidth || 800);
        const svgH = (box && box.height) ? box.height : (svgElement.clientHeight || 600);

        const cardW = 1200;
        const cardH = 630;
        const cardBoxX = 60;
        const cardBoxY = 160;
        const cardBoxW = 1080;
        const cardBoxH = 410;

        const maxW = cardBoxW - 40;
        const maxH = cardBoxH - 50;
        const scale = Math.min(maxW / svgW, maxH / svgH, 1.2);
        const drawW = svgW * scale;
        const drawH = svgH * scale;
        const drawX = cardBoxX + (cardBoxW - drawW) / 2;
        const drawY = cardBoxY + 36 + (cardBoxH - 36 - drawH) / 2;

        const innerSvgContent = svgElement.innerHTML;
        const projectTitle = document.title || 'Codebase Architecture';

        const fullCardSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${cardW} ${cardH}" width="${cardW}" height="${cardH}">
  <defs>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="50%" stop-color="#1e1b4b" />
      <stop offset="100%" stop-color="#090d16" />
    </linearGradient>
  </defs>
  <rect width="${cardW}" height="${cardH}" fill="url(#cardGrad)" rx="16" />
  <text x="60" y="60" fill="#818cf8" font-family="Inter, system-ui, sans-serif" font-size="14" font-weight="bold" letter-spacing="1.5">EXCALIFLOW STUDIO • ARCHITECTURE MAP</text>
  <text x="60" y="105" fill="#ffffff" font-family="'Shantell Sans', Georgia, sans-serif" font-size="34" font-weight="bold">${htmlEscape(projectTitle)}</text>
  <text x="60" y="135" fill="#94a3b8" font-family="Inter, system-ui, sans-serif" font-size="16">Local-First &amp; Air-Gapped Codebase Intelligence Engine</text>

  <!-- Window Frame -->
  <rect x="${cardBoxX}" y="${cardBoxY}" width="${cardBoxW}" height="${cardBoxH}" rx="12" fill="#0b1120" stroke="#3b82f6" stroke-width="1.5" />
  <circle cx="${cardBoxX + 24}" cy="${cardBoxY + 20}" r="5" fill="#ef4444" />
  <circle cx="${cardBoxX + 40}" cy="${cardBoxY + 20}" r="5" fill="#f59e0b" />
  <circle cx="${cardBoxX + 56}" cy="${cardBoxY + 20}" r="5" fill="#10b981" />

  <!-- Embedded Architecture Diagram -->
  <g transform="translate(${drawX}, ${drawY}) scale(${scale})">
    ${innerSvgContent}
  </g>

  <text x="60" y="600" fill="#64748b" font-family="Inter, system-ui, sans-serif" font-size="12">Generated by ExcaliFlow Studio • 100% Offline • github.com/Nakazasen/ExcaliFlow-Studio</text>
</svg>`;

        // Download High-Resolution Vector Share Card SVG directly
        const svgBlob = new Blob([fullCardSvg], { type: 'image/svg+xml;charset=utf-8' });
        const svgUrl = URL.createObjectURL(svgBlob);
        const a = document.createElement('a');
        a.href = svgUrl;
        a.download = `architecture-share-card.svg`;
        a.click();
        setTimeout(() => URL.revokeObjectURL(svgUrl), 2000);
      };
    }

    function toggleSidebar() {
      const sidebar = document.getElementById('sidebar');
      sidebar.classList.toggle('collapsed');
    }

    document.getElementById('btn-render').onclick = renderDiagram;
    
    document.getElementById('btn-copy').onclick = () => {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(codeArea.value).then(() => {
          alert('Đã sao chép mã Mermaid vào clipboard!');
        }).catch(() => {
          fallbackCopyText(codeArea.value);
        });
      } else {
        fallbackCopyText(codeArea.value);
      }
    };

    function fallbackCopyText(text) {
      codeArea.select();
      document.execCommand('copy');
      alert('Đã sao chép mã Mermaid vào clipboard!');
    }

    document.getElementById('toggle-sidebar').onclick = toggleSidebar;
    
    const btnCollapse = document.getElementById('btn-collapse-sidebar');
    if (btnCollapse) {
      btnCollapse.onclick = toggleSidebar;
    }

    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        toggleSidebar();
      }
    });

    document.getElementById('zoom-in').onclick = () => panzoomInstance && panzoomInstance.zoomIn();
    document.getElementById('zoom-out').onclick = () => panzoomInstance && panzoomInstance.zoomOut();
    document.getElementById('zoom-reset').onclick = () => {
      if (panzoomInstance) {
        panzoomInstance.reset();
        updateZoomBadge(panzoomInstance.getScale());
      }
    };
    document.getElementById('zoom-fit').onclick = fitToScreen;

    document.getElementById('export-svg').onclick = () => {
      const svgElement = diagramOutput.querySelector('svg');
      if (!svgElement) return alert('Chưa có sơ đồ để xuất!');
      
      const svgData = new XMLSerializer().serializeToString(svgElement);
      const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `architecture-${currentTab}.svg`;
      a.click();
      URL.revokeObjectURL(url);
    };

    document.getElementById('export-png').onclick = () => {
      const svgElement = diagramOutput.querySelector('svg');
      if (!svgElement) return alert('Chưa có sơ đồ để xuất!');

      const svgData = new XMLSerializer().serializeToString(svgElement);
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();

      const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(svgBlob);

      img.onload = () => {
        const scale = 2;
        const box = svgElement.viewBox?.baseVal;
        const w = (box && box.width) ? box.width : (svgElement.clientWidth || 1200);
        const h = (box && box.height) ? box.height : (svgElement.clientHeight || 800);
        
        canvas.width = w * scale;
        canvas.height = h * scale;
        
        ctx.fillStyle = '#fdfbf7';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        const pngUrl = canvas.toDataURL('image/png');
        const a = document.createElement('a');
        a.href = pngUrl;
        a.download = `architecture-${currentTab}.png`;
        a.click();
        URL.revokeObjectURL(url);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        alert('Không thể xuất ảnh PNG từ SVG!');
      };
      img.src = url;
    };

    window.addEventListener('DOMContentLoaded', () => {
      selectTab(currentTab);
    });
  </script>
</body>
</html>
"""

def smart_truncate_text(text: str, limit: int) -> str:
    """Smartly truncate text at word boundaries when possible, without slicing mid-word."""
    clean = " ".join(str(text or "").split())
    if len(clean) <= limit:
        return clean
    target = clean[:limit]
    if len(clean) > limit and clean[limit] == " ":
        return target.rstrip() + "…"
    last_space = target.rfind(" ")
    if last_space > int(limit * 0.4):
        return target[:last_space].rstrip() + "…"
    return target[:-1].rstrip() + "…"


def editorial_text(value, limit=200):
    """Return XML-safe one-line copy with smart word-boundary truncation."""
    truncated = smart_truncate_text(value, limit)
    return xml_escape(truncated, quote=True)


def render_editorial_multiline_svg_with_count(
    text: str,
    x: float,
    y: float,
    css_class: str = "label",
    line_limit: int = 35,
    max_lines: int = 3,
    line_height: float = 18.0,
    anchor: str = "",
    extra_attrs: str = "",
    include_tooltip: bool = True,
) -> tuple[str, int]:
    """Render smart word-wrapped multi-line SVG text using <tspan> with tooltip and line count."""
    raw_text = " ".join(str(text or "").split())
    if not raw_text:
        return ("", 0)

    words = raw_text.split()
    lines = []
    current_line = []
    current_len = 0

    for word in words:
        added_len = len(word) if not current_line else len(word) + 1
        if current_len + added_len <= line_limit:
            current_line.append(word)
            current_len += added_len
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_len = len(word)
    if current_line:
        lines.append(" ".join(current_line))

    if len(lines) > max_lines:
        reconstructed_tail = " ".join(lines[max_lines - 1 :])
        lines = lines[: max_lines - 1]
        lines.append(smart_truncate_text(reconstructed_tail, line_limit))

    anchor_attr = f' text-anchor="{anchor}"' if anchor else ""
    extra = f" {extra_attrs.strip()}" if extra_attrs.strip() else ""
    tooltip = f"<title>{xml_escape(raw_text, quote=True)}</title>" if include_tooltip else ""

    if len(lines) == 1:
        return (
            f'<text class="{css_class}"{anchor_attr} x="{x:.1f}" y="{y:.1f}"{extra}>{tooltip}{xml_escape(lines[0], quote=True)}</text>',
            1,
        )

    tspans = []
    for i, line in enumerate(lines):
        dy_attr = f' dy="{line_height:.1f}"' if i > 0 else ""
        tspans.append(f'<tspan x="{x:.1f}"{dy_attr}>{xml_escape(line, quote=True)}</tspan>')

    return (
        f'<text class="{css_class}"{anchor_attr} x="{x:.1f}" y="{y:.1f}"{extra}>{tooltip}{"".join(tspans)}</text>',
        len(lines),
    )


def editorial_number(value, field_name, minimum=None, maximum=None, strict_minimum=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise EditorialValidationError(f"{field_name} must be a finite number.")
    if minimum is not None and (value <= minimum if strict_minimum else value < minimum):
        comparator = "greater than" if strict_minimum else "at least"
        raise EditorialValidationError(f"{field_name} must be {comparator} {minimum}.")
    if maximum is not None and value > maximum:
        raise EditorialValidationError(f"{field_name} must be at most {maximum}.")
    return float(value)


def require_editorial_string(value, field_name, maximum):
    if not isinstance(value, str) or not value.strip():
        raise EditorialValidationError(f"{field_name} must be a non-empty string.")
    if len(value.strip()) > maximum:
        raise EditorialValidationError(f"{field_name} must be at most {maximum} characters.")
    return value.strip()


def load_visual_brief(path):
    brief_path = Path(path)
    try:
        payload = json.loads(brief_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise EditorialValidationError(f"Visual brief was not found: {brief_path}") from error
    except json.JSONDecodeError as error:
        raise EditorialValidationError(f"Visual brief is not valid JSON: {error.msg}") from error
    if not isinstance(payload, dict):
        raise EditorialValidationError("Visual brief root must be a JSON object.")
    return payload


def validate_visual_brief(visual_type, brief):
    """Validate supplied editorial facts before renderer selection or file creation."""
    if visual_type not in EDITORIAL_TYPES:
        raise EditorialValidationError(f"Unsupported editorial visual type: {visual_type}.")
    if visual_type == "architecture":
        return None
    if not isinstance(brief, dict):
        raise EditorialValidationError(f"{visual_type} requires a JSON visual brief.")
    title = require_editorial_string(brief.get("title"), "title", 200)
    subtitle = brief.get("subtitle", "")
    if subtitle:
        subtitle = require_editorial_string(subtitle, "subtitle", 300)
    if brief.get("type") != visual_type:
        raise EditorialValidationError(f"Visual brief type must be '{visual_type}'.")
    data = brief.get("data")
    if not isinstance(data, dict):
        raise EditorialValidationError("visual brief data must be an object.")

    if visual_type == "sankey":
        nodes, links = data.get("nodes"), data.get("links")
        if not isinstance(nodes, list) or not 2 <= len(nodes) <= 12:
            raise EditorialValidationError("Sankey requires 2 to 12 nodes.")
        if not isinstance(links, list) or not 1 <= len(links) <= 24:
            raise EditorialValidationError("Sankey requires 1 to 24 links.")
        node_ids, clean_nodes = set(), []
        for index, node in enumerate(nodes, 1):
            if not isinstance(node, dict):
                raise EditorialValidationError(f"Sankey node {index} must be an object.")
            node_id = require_editorial_string(node.get("id"), f"Sankey node {index} id", 100)
            if node_id in node_ids:
                raise EditorialValidationError(f"Sankey node id '{node_id}' is duplicated.")
            node_ids.add(node_id)
            clean_nodes.append({"id": node_id, "label": require_editorial_string(node.get("label"), f"Sankey node {index} label", 160)})
        clean_links = []
        for index, link in enumerate(links, 1):
            if not isinstance(link, dict):
                raise EditorialValidationError(f"Sankey link {index} must be an object.")
            source = require_editorial_string(link.get("source"), f"Sankey link {index} source", 100)
            target = require_editorial_string(link.get("target"), f"Sankey link {index} target", 100)
            if source == target or source not in node_ids or target not in node_ids:
                raise EditorialValidationError(f"Sankey link {index} must join two different known nodes.")
            clean_links.append({"source": source, "target": target, "value": editorial_number(link.get("value"), f"Sankey link {index} value", 0, strict_minimum=True), "label": str(link.get("label", "")).strip()})
        return {"title": title, "subtitle": subtitle, "type": visual_type, "data": {"nodes": clean_nodes, "links": clean_links}}

    if visual_type == "wardley":
        components = data.get("components")
        if not isinstance(components, list) or not 1 <= len(components) <= 12:
            raise EditorialValidationError("Wardley requires 1 to 12 components.")
        names, clean_components = set(), []
        for index, component in enumerate(components, 1):
            if not isinstance(component, dict):
                raise EditorialValidationError(f"Wardley component {index} must be an object.")
            name = require_editorial_string(component.get("name"), f"Wardley component {index} name", 160)
            if name in names:
                raise EditorialValidationError(f"Wardley component name '{name}' is duplicated.")
            names.add(name)
            clean_components.append({"name": name, "evolution": editorial_number(component.get("evolution"), f"Wardley component {index} evolution", 0, 1), "value": editorial_number(component.get("value"), f"Wardley component {index} value", 0, 1), "note": str(component.get("note", "")).strip()})
        return {"title": title, "subtitle": subtitle, "type": visual_type, "data": {"components": clean_components}}

    stages = data.get("stages")
    if not isinstance(stages, list) or not 2 <= len(stages) <= 12:
        raise EditorialValidationError("Journey requires 2 to 12 stages.")
    clean_stages = []
    for index, stage in enumerate(stages, 1):
        if not isinstance(stage, dict):
            raise EditorialValidationError(f"Journey stage {index} must be an object.")
        clean_stages.append({"name": require_editorial_string(stage.get("name"), f"Journey stage {index} name", 120), "action": require_editorial_string(stage.get("action"), f"Journey stage {index} action", 160), "sentiment": editorial_number(stage.get("sentiment"), f"Journey stage {index} sentiment", -2, 2), "note": str(stage.get("note", "")).strip()})
    return {"title": title, "subtitle": subtitle, "type": visual_type, "data": {"stages": clean_stages}}


def validate_report_brief(visual_type, brief):
    if visual_type not in REPORT_TYPES:
        raise EditorialValidationError(f"Unsupported report visual type: {visual_type}.")
    if not isinstance(brief, dict) or brief.get("type") != visual_type:
        raise EditorialValidationError(f"Report brief type must be '{visual_type}'.")
    title = require_editorial_string(brief.get("title"), "title", 200)
    items = brief.get("data", {}).get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= 12:
        raise EditorialValidationError(f"{visual_type} requires 1 to 12 data items.")
    clean = []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise EditorialValidationError(f"Report item {index} must be an object.")
        label = require_editorial_string(item.get("label"), f"Report item {index} label", 120)
        value = item.get("value")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = editorial_number(value, f"Report item {index} value")
        elif not isinstance(value, str) or not value.strip():
            raise EditorialValidationError(f"Report item {index} value must be a number or non-empty string.")
        x = item.get("x")
        y = item.get("y")
        if visual_type in {"quadrant", "matrix", "risk"}:
            x, y = editorial_number(x, f"Report item {index} x", 0, 1), editorial_number(y, f"Report item {index} y", 0, 1)
        clean.append({"label": label, "value": value, "note": str(item.get("note", "")).strip(), "x": x, "y": y})
    return {"title": title, "subtitle": str(brief.get("subtitle", "")).strip(), "type": visual_type, "data": {"items": clean}}


def render_business_report(brief, width, height):
    kind, items = brief["type"], brief["data"]["items"]
    left, top, usable_width, usable_height = 96, 270, width - 192, height - 420
    parts = [f'<text class="small" x="96" y="222">BUSINESS REPORT · {editorial_text(kind.upper(), 20)}</text>']
    if kind == "kpi":
        card_width = (usable_width - 24 * (len(items) - 1)) / len(items)
        for index, item in enumerate(items):
            x = left + index * (card_width + 24)
            parts += [f'<rect class="node" x="{x:.1f}" y="{top}" width="{card_width:.1f}" height="190" rx="16"/>', f'<text class="small" x="{x + 24:.1f}" y="{top + 46}">{editorial_text(item["label"], 28)}</text>', f'<text class="title" x="{x + 24:.1f}" y="{top + 118}">{editorial_text(item["value"], 16)}</text>']
    elif kind in {"quadrant", "matrix", "risk"}:
        parts += [f'<rect class="node" x="{left}" y="{top}" width="{usable_width}" height="{usable_height}"/>', f'<line x1="{left + usable_width / 2}" y1="{top}" x2="{left + usable_width / 2}" y2="{top + usable_height}" class="line"/>', f'<line x1="{left}" y1="{top + usable_height / 2}" x2="{left + usable_width}" y2="{top + usable_height / 2}" class="line"/>']
        for item in items:
            x, y = left + item["x"] * usable_width, top + (1 - item["y"]) * usable_height
            parts += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="13" class="accent"/>', f'<text class="label" x="{x + 18:.1f}" y="{y + 6:.1f}">{editorial_text(item["label"], 28)}</text>']
    else:
        segment = usable_width / len(items)
        is_process = kind == "process"
        box_height = 172 if is_process else 120
        for index, item in enumerate(items):
            x = left + index * segment
            y = top + (index % 2) * 36 if kind == "timeline" else top
            parts.append(f'<rect class="node" x="{x + 8:.1f}" y="{y}" width="{segment - 16:.1f}" height="{box_height}" rx="14"/>')
            if is_process:
                label_svg, label_lines = render_editorial_multiline_svg_with_count(
                    item["label"], x=x + 20, y=y + 34, css_class="label", line_limit=22, max_lines=2, line_height=17
                )
                value_svg, _ = render_editorial_multiline_svg_with_count(
                    item["value"], x=x + 20, y=y + 40 + label_lines * 17, css_class="small", line_limit=25, max_lines=5, line_height=14
                )
                parts.extend([label_svg, value_svg])
            else:
                parts.extend([f'<text class="label" x="{x + 26:.1f}" y="{y + 46}">{editorial_text(item["label"], 24)}</text>', f'<text class="small" x="{x + 26:.1f}" y="{y + 78}">{editorial_text(item["value"], 28)}</text>'])
            if index:
                parts.append(f'<line x1="{x - 8:.1f}" y1="{y + box_height / 2:.1f}" x2="{x + 8:.1f}" y2="{y + box_height / 2:.1f}" class="accent-stroke" stroke-width="4"/>')
    return "".join(parts)


def editorial_svg_shell(title, subtitle, visual_type, canvas, source_mode, body):
    width, height = EDITORIAL_CANVASES[canvas]
    subtitle_markup = f'<text class="subtitle" x="96" y="156">{editorial_text(subtitle, 180)}</text>' if subtitle else ""
    receipt = f"Grammar: {visual_type} · Canvas: {canvas} · Source: {source_mode}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc" viewBox="0 0 {width} {height}">
  <title id="title">{editorial_text(title, 100)}</title>
  <desc id="desc">Original local editorial diagram. {editorial_text(receipt, 160)}</desc>
  <style>
    .paper {{ fill: #fbfaf7; }} .ink {{ fill: #172033; }} .muted {{ fill: #667085; }}
    .title {{ font-family: Georgia, 'Times New Roman', serif; font-size: 46px; font-weight: 700; fill: #172033; }}
    .subtitle {{ font-family: Arial, sans-serif; font-size: 20px; fill: #667085; }}
    .label {{ font-family: Arial, sans-serif; font-size: 18px; font-weight: 700; fill: #172033; }}
    .small {{ font-family: Arial, sans-serif; font-size: 15px; fill: #667085; }}
    .receipt {{ font-family: Arial, sans-serif; font-size: 14px; fill: #667085; letter-spacing: .4px; }}
    .node {{ fill: #ffffff; stroke: #172033; stroke-width: 2; }} .accent {{ fill: #cb5d3f; }}
    .accent-stroke {{ stroke: #cb5d3f; }} .line {{ stroke: #98a2b3; stroke-width: 2; fill: none; }}
  </style>
  <rect class="paper" width="{width}" height="{height}"/>
  <rect x="64" y="50" width="8" height="110" rx="4" class="accent"/>
  <text class="title" x="96" y="110">{editorial_text(title, 100)}</text>
  {subtitle_markup}
  <line x1="96" y1="190" x2="{width - 96}" y2="190" class="line"/>
  {body}
  <line x1="96" y1="{height - 72}" x2="{width - 96}" y2="{height - 72}" class="line"/>
  <text class="receipt" x="96" y="{height - 38}">{editorial_text(receipt, 160)}</text>
</svg>'''


def editorial_architecture_brief(project_dir):
    project_info = scan_project_structure(Path(project_dir).resolve())
    modules = []
    for directory, files in project_info["file_tree"].items():
        if directory == "." or not files:
            continue
        modules.append({"label": directory, "detail": f"{len(files)} file{'s' if len(files) != 1 else ''}"})
        if len(modules) == 9:
            break
    if not modules:
        modules = [{"label": project_info["root_name"], "detail": "Local source scan"}]
    return {"title": f"{project_info['root_name']} architecture", "subtitle": "Local structural analysis for an editorial overview.", "modules": modules}


def render_editorial_architecture(brief, width, height):
    modules, columns = brief["modules"], 3
    box_width = (width - 192 - (columns - 1) * 28) / columns
    box_height, start_y = 112, 250
    parts = [f'<text class="small" x="96" y="222">ANALYSIS OVERVIEW</text>']
    for index, module in enumerate(modules):
        column, row = index % columns, index // columns
        x, y = 96 + column * (box_width + 28), start_y + row * 148
        parts.append(f'<rect class="node" x="{x:.1f}" y="{y}" width="{box_width:.1f}" height="{box_height}" rx="14"/>')
        parts.append(f'<rect x="{x:.1f}" y="{y}" width="8" height="{box_height}" rx="4" class="accent"/>')
        label_svg, label_lines = render_editorial_multiline_svg_with_count(
            module["label"], x=x + 26, y=y + 42, css_class="label", line_limit=36, max_lines=2, line_height=18
        )
        parts.append(label_svg)
        detail_y = y + 42 + label_lines * 18 + 6
        detail_svg, _ = render_editorial_multiline_svg_with_count(
            module["detail"], x=x + 26, y=detail_y, css_class="small", line_limit=42, max_lines=2, line_height=15
        )
        parts.append(detail_svg)
    return "".join(parts)


def render_editorial_sankey(brief, width, height):
    nodes, links = brief["data"]["nodes"], brief["data"]["links"]
    incoming = {node["id"]: [] for node in nodes}
    outgoing = {node["id"]: [] for node in nodes}
    for link in links:
        incoming[link["target"]].append(link)
        outgoing[link["source"]].append(link)
    levels = {node["id"]: 0 for node in nodes if not incoming[node["id"]]}
    for _ in range(len(nodes)):
        changed = False
        for link in links:
            source_level = levels.get(link["source"], 0)
            target_level = source_level + 1
            if levels.get(link["target"], -1) < target_level:
                levels[link["target"]] = target_level
                changed = True
        if not changed:
            break
    for node in nodes:
        levels.setdefault(node["id"], 0)
    max_level = max(levels.values()) or 1
    columns = {}
    for node in nodes:
        columns.setdefault(levels[node["id"]], []).append(node)
    positions, top, diagram_height = {}, 258, height - 390
    for level, grouped_nodes in columns.items():
        x = 116 + (width - 232) * level / max_level
        gap = diagram_height / (len(grouped_nodes) + 1)
        for index, node in enumerate(grouped_nodes, 1):
            positions[node["id"]] = (x, top + gap * index)
    max_value = max(link["value"] for link in links)
    parts = ['<text class="small" x="96" y="222">FLOW OF SUPPLIED QUANTITIES</text>']
    for link in links:
        sx, sy = positions[link["source"]]
        tx, ty = positions[link["target"]]
        stroke_width = 8 + 32 * link["value"] / max_value
        mid_x = (sx + tx) / 2
        parts.append(f'<path d="M {sx + 18:.1f} {sy:.1f} C {mid_x:.1f} {sy:.1f}, {mid_x:.1f} {ty:.1f}, {tx - 18:.1f} {ty:.1f}" stroke="#cb5d3f" stroke-opacity="0.48" stroke-width="{stroke_width:.2f}" fill="none" stroke-linecap="round"/>')
    for node in nodes:
        x, y = positions[node["id"]]
        parts.append(f'<rect class="node" x="{x - 18:.1f}" y="{y - 30:.1f}" width="36" height="60" rx="8"/>')
        label_svg, _ = render_editorial_multiline_svg_with_count(
            node["label"], x=x + 30, y=y - 4, css_class="label", line_limit=32, max_lines=2, line_height=16
        )
        parts.append(label_svg)
    return "".join(parts)


def render_editorial_wardley(brief, width, height):
    left, top, chart_width, chart_height = 180, 270, width - 300, height - 430
    parts = [
        '<text class="small" x="96" y="222">VALUE CHAIN AND EVOLUTION</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" class="line"/>',
        f'<line x1="{left}" y1="{top + chart_height}" x2="{left + chart_width}" y2="{top + chart_height}" class="line"/>',
        f'<text class="small" x="{left - 108}" y="{top + 18}">Visible</text>',
        f'<text class="small" x="{left - 108}" y="{top + chart_height}">Invisible</text>',
        f'<text class="small" x="{left}" y="{top + chart_height + 42}">Genesis</text>',
        f'<text class="small" x="{left + chart_width - 92}" y="{top + chart_height + 42}">Commodity</text>',
    ]
    for component in brief["data"]["components"]:
        x = left + component["evolution"] * chart_width
        y = top + (1 - component["value"]) * chart_height
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" class="accent"/>')
        align_left = component["evolution"] > 0.65
        tx = x - 20 if align_left else x + 20
        anchor = "end" if align_left else ""
        name_svg, name_lines = render_editorial_multiline_svg_with_count(
            component["name"], x=tx, y=y + 6, css_class="label", line_limit=32, max_lines=3, line_height=18, anchor=anchor
        )
        parts.append(name_svg)
        if component.get("note"):
            note_y = y + 6 + name_lines * 18 + 4
            note_svg, _ = render_editorial_multiline_svg_with_count(
                component["note"], x=tx, y=note_y, css_class="small", line_limit=38, max_lines=3, line_height=15, anchor=anchor
            )
            parts.append(note_svg)
    return "".join(parts)


def render_editorial_journey(brief, width, height):
    stages, left, right = brief["data"]["stages"], 150, width - 150
    baseline, span = 480, 230
    points = []
    for index, stage in enumerate(stages):
        x = left + (right - left) * index / (len(stages) - 1)
        y = baseline - stage["sentiment"] * span / 2
        points.append((x, y))
    parts = [
        '<text class="small" x="96" y="222">EXPERIENCE OVER TIME</text>',
        f'<line x1="{left}" y1="{baseline}" x2="{right}" y2="{baseline}" class="line"/>',
        f'<text class="small" x="96" y="{baseline - span + 6}">Positive</text>',
        f'<text class="small" x="96" y="{baseline + span + 6}">Friction</text>',
        f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in points)}" fill="none" stroke="#cb5d3f" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>',
    ]
    for (x, y), stage in zip(points, stages):
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" class="accent"/>')
        name_svg, name_lines = render_editorial_multiline_svg_with_count(
            stage["name"], x=x, y=baseline + 62, css_class="label", line_limit=24, max_lines=2, line_height=16, anchor="middle"
        )
        parts.append(name_svg)
        action_y = baseline + 62 + name_lines * 16 + 8
        action_svg, action_lines = render_editorial_multiline_svg_with_count(
            stage["action"], x=x, y=action_y, css_class="small", line_limit=28, max_lines=2, line_height=14, anchor="middle"
        )
        parts.append(action_svg)
        if stage.get("note"):
            note_y = action_y + action_lines * 14 + 6
            note_svg, _ = render_editorial_multiline_svg_with_count(
                stage["note"], x=x, y=note_y, css_class="small", line_limit=28, max_lines=2, line_height=14, anchor="middle"
            )
            parts.append(note_svg)
    return "".join(parts)


def build_editorial_svg(project_dir, visual_type="architecture", visual_data=None, canvas="document"):
    if canvas not in EDITORIAL_CANVASES:
        raise EditorialValidationError(f"Unsupported canvas: {canvas}. Choose document, slide, or social.")
    if visual_type not in EDITORIAL_TYPES | REPORT_TYPES:
        raise EditorialValidationError(f"Unsupported editorial visual type: {visual_type}.")
    width, height = EDITORIAL_CANVASES[canvas]
    if visual_type == "architecture":
        brief = editorial_architecture_brief(project_dir)
        body, source_mode = render_editorial_architecture(brief, width, height), "analysis"
    elif visual_type in EDITORIAL_TYPES:
        brief = validate_visual_brief(visual_type, visual_data)
        renderer = {"sankey": render_editorial_sankey, "wardley": render_editorial_wardley, "journey": render_editorial_journey}[visual_type]
        body, source_mode = renderer(brief, width, height), "brief"
    else:
        brief = validate_report_brief(visual_type, visual_data)
        body, source_mode = render_business_report(brief, width, height), "brief"
    return editorial_svg_shell(brief["title"], brief.get("subtitle", ""), visual_type, canvas, source_mode, body)


def generate_editorial_file(project_dir=".", output_path="editorial.svg", visual_type="architecture", visual_data=None, canvas="document"):
    """Create one original local editorial SVG or a self-contained HTML wrapper."""
    project_path = Path(project_dir).resolve()
    svg = build_editorial_svg(project_path, visual_type=visual_type, visual_data=visual_data, canvas=canvas)
    output = Path(output_path)
    if not output.is_absolute():
        output = project_path / output
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".svg":
        output.write_text(svg, encoding="utf-8")
    else:
        output.write_text(f'<!doctype html><html lang="en"><meta charset="utf-8"><title>Editorial diagram</title><style>body{{margin:0;background:#fbfaf7}}svg{{display:block;width:100%;height:auto}}</style><body>{svg}</body></html>', encoding="utf-8")
    print(f"[*] Created editorial {visual_type} artifact: {output.resolve()}")
    return output.resolve()


def build_excalidraw_scene(diagrams: dict) -> dict:
    """Create a portable editable Excalidraw scene from the first flowchart-like diagram."""
    primary = next(iter(diagrams.values()), {"code": ""})["code"]
    nodes = re.findall(r"^\s*([A-Za-z_]\w*)\[\"?([^\]\"]+)", primary, re.MULTILINE)
    edges = re.findall(r"^\s*([A-Za-z_]\w*)\s*--.*?>\|?[^|]*\|?\s*([A-Za-z_]\w*)", primary, re.MULTILINE)
    elements, positions = [], {}
    now = 1
    for index, (node_id, label) in enumerate(nodes):
        x, y = (index % 4) * 260, (index // 4) * 160
        rect_id, text_id = uuid.uuid4().hex, uuid.uuid4().hex
        positions[node_id] = (x, y, rect_id)
        elements.extend([
            {"id": rect_id, "type": "rectangle", "x": x, "y": y, "width": 210, "height": 96, "angle": 0, "strokeColor": "#334155", "backgroundColor": "#e0f2fe", "fillStyle": "solid", "strokeWidth": 2, "roughness": 1, "opacity": 100, "seed": index + 1, "version": 1, "versionNonce": index + 11, "isDeleted": False, "groupIds": [], "frameId": None, "roundness": {"type": 3}, "boundElements": [{"id": text_id, "type": "text"}], "updated": now, "link": None, "locked": False},
            {"id": text_id, "type": "text", "x": x + 12, "y": y + 24, "width": 186, "height": 24, "angle": 0, "strokeColor": "#0f172a", "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 1, "roughness": 0, "opacity": 100, "seed": index + 101, "version": 1, "versionNonce": index + 111, "isDeleted": False, "groupIds": [], "frameId": None, "roundness": None, "boundElements": [], "updated": now, "link": None, "locked": False, "text": re.sub(r"<br\\s*/?>", "\n", label).strip(), "fontSize": 18, "fontFamily": 1, "textAlign": "center", "verticalAlign": "middle", "containerId": rect_id, "originalText": re.sub(r"<br\\s*/?>", "\n", label).strip(), "autoResize": True, "lineHeight": 1.25}
        ])
    for index, (source, target) in enumerate(edges):
        if source not in positions or target not in positions:
            continue
        sx, sy, source_id = positions[source]
        tx, ty, target_id = positions[target]
        arrow_id = uuid.uuid4().hex
        elements.append({"id": arrow_id, "type": "arrow", "x": sx + 210, "y": sy + 48, "width": tx - sx - 210, "height": ty - sy, "angle": 0, "strokeColor": "#334155", "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 2, "roughness": 1, "opacity": 100, "seed": index + 201, "version": 1, "versionNonce": index + 211, "isDeleted": False, "groupIds": [], "frameId": None, "roundness": {"type": 2}, "boundElements": [], "updated": now, "link": None, "locked": False, "points": [[0, 0], [tx - sx - 210, ty - sy]], "lastCommittedPoint": None, "startBinding": {"elementId": source_id, "focus": 0, "gap": 1}, "endBinding": {"elementId": target_id, "focus": 0, "gap": 1}, "startArrowhead": None, "endArrowhead": "arrow"})
    return {"type": "excalidraw", "version": 2, "source": "https://excaliflow.local", "elements": elements, "appState": {"viewBackgroundColor": "#fdfbf7", "gridSize": 20}, "files": {}}


def generate_html_file(
    project_dir: str = ".",
    output_path: str = "architecture_viewer.html",
    excalidraw_output: str | None = None,
    auto_graphify: bool = True,
    strict: bool = False,
    diff_target: str | None = None,
):
    """Sinh file HTML Excalidraw Viewer chứa dữ liệu Mermaid từ dự án chỉ định"""
    proj_path = Path(project_dir).resolve()
    
    # 1. Kiểm tra xem có Đồ thị tri thức (Graphify hoặc Understand-Anything) hay không
    kg_type, kg_path = find_knowledge_graph(proj_path, auto_trigger=auto_graphify, strict=strict)
    
    diagrams = {}
    if kg_type == "graphify":
        print(f"[*] Phat hien Knowledge Graph tu Graphify: {kg_path}")
        gdata = parse_graphify_graph(kg_path)
        if gdata:
            diagrams = generate_mermaid_from_graphify(gdata, proj_path.name)
            
    elif kg_type == "understand":
        print(f"[*] Phat hien Knowledge Graph tu Understand-Anything: {kg_path}")
        udata = parse_understand_graph(kg_path)
        if udata:
            diagrams = generate_mermaid_from_understand(udata, proj_path.name)

    # 2. Nếu không tìm thấy hoặc trích xuất không thành công, fallback về quét AST & Folder Tree
    if not diagrams:
        if strict:
            raise RuntimeError(f"Fail-Closed: Could not generate diagrams from knowledge graph in strict mode for {proj_path}")
        print("[*] Quet cau truc thu muc va phan tich ma nguon...")
        project_info = scan_project_structure(proj_path)
        ast_data = None
        if project_info["is_python"]:
            try:
                ast_data = scan_python_ast(proj_path)
            except Exception as e:
                print(f"[!] AST Notice: {e}")
        diagrams = generate_mermaid_from_project(project_info, ast_data)
        diagrams.update(generate_mermaid_from_language_analysis(project_info, scan_language_sources(proj_path)))

    # 3. Tính toán Architecture Diff nếu có yêu cầu so sánh
    if diff_target:
        print(f"[*] Dang tinh toan Architecture Diff voi muc tieu: {diff_target}...")
        old_analysis = load_diff_baseline(diff_target, proj_path)
        current_lang = scan_language_sources(proj_path)
        diff_res = compute_architecture_diff(old_analysis, current_lang)
        combined = diff_res
        combined.update(diagrams)
        diagrams = combined

    diagrams_json = json.dumps(diagrams, ensure_ascii=False, indent=2)
    # Tránh làm vỡ thẻ script khi trong label hoặc code Mermaid chứa chuỗi </script>
    diagrams_json = diagrams_json.replace("</script>", "<\\/script>").replace("</SCRIPT>", "<\\/SCRIPT>")
    runtime = load_offline_runtime()
    html_content = HTML_TEMPLATE.replace("__DIAGRAMS_DATA__", diagrams_json).replace("__MERMAID_RUNTIME__", runtime["mermaid"]).replace("__PANZOOM_RUNTIME__", runtime["panzoom"])
    
    out_file = Path(output_path)
    if not out_file.is_absolute():
        out_file = proj_path / out_file
        
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html_content, encoding="utf-8")
    print(f"[*] Da tao thanh cong file giao dien: {out_file.resolve()}")
    if excalidraw_output:
        scene_path = Path(excalidraw_output)
        if not scene_path.is_absolute():
            scene_path = proj_path / scene_path
        scene_path.parent.mkdir(parents=True, exist_ok=True)
        scene_path.write_text(json.dumps(build_excalidraw_scene(diagrams), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[*] Da tao thanh cong scene Excalidraw: {scene_path.resolve()}")
    return out_file.resolve()


def install_git_hooks(project_dir: str = ".", force: bool = False) -> bool:
    """Cài đặt Git Post-commit Hook để tự động làm mới sơ đồ cục bộ sau mỗi commit."""
    proj_path = Path(project_dir).resolve()
    hooks_dir = proj_path / ".git" / "hooks"
    if not hooks_dir.exists():
        print(f"[!] Khong tim thay thu muc {hooks_dir}. Hay dam bao ban dang o trong git repository.")
        return False

    script_path = Path(__file__).resolve()
    marker = "# excaliflow-managed-hook"

    post_commit = hooks_dir / "post-commit"
    if post_commit.exists():
        existing = post_commit.read_text(encoding="utf-8", errors="ignore")
        if marker not in existing and not force:
            print(f"[!] Tu choi ghi de hook hien co: {post_commit}. Dung --force-hook chi voi hook do Excali-Flow quan ly.")
            return False

    post_commit_content = f"""#!/bin/sh
{marker}
set -e

# ExcaliFlow tu kiem tra phien ban va chi goi Graphify mot lan khi can.
echo "[excaliflow-hook] Lam moi so do ExcaliFlow cuc bo..."
if command -v excaliflow >/dev/null 2>&1; then
    excaliflow --dir "$PWD" --out architecture_viewer.html --with-excalidraw
else
    REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
    if command -v py >/dev/null 2>&1; then
        PY_EXE="py -3"
    elif command -v python3 >/dev/null 2>&1; then
        PY_EXE="python3"
    else
        PY_EXE="python"
    fi

    if [ -f "$REPO_ROOT/scripts/generate_diagram.py" ]; then
        $PY_EXE "$REPO_ROOT/scripts/generate_diagram.py" --dir "$PWD" --out architecture_viewer.html --with-excalidraw
    fi
fi
"""
    post_commit.write_text(post_commit_content, encoding="utf-8")
    try:
        post_commit.chmod(0o755)
    except Exception:
        pass

    # Clean legacy pre-commit hook if managed by excaliflow
    pre_commit = hooks_dir / "pre-commit"
    if pre_commit.exists():
        existing_pre = pre_commit.read_text(encoding="utf-8", errors="ignore")
        if marker in existing_pre:
            try:
                pre_commit.unlink()
            except Exception:
                pass

    print(f"[*] Da cai dat thanh cong Git Hook tai:\n  - {post_commit}")
    return True


def watch_source_snapshot(project_dir: Path, excluded_files: set[Path] | None = None) -> dict[str, tuple[int, int]]:
    """Snapshot only architecture inputs while pruning generated and dependency trees."""
    excluded = {path.resolve() for path in (excluded_files or set())}
    snapshot: dict[str, tuple[int, int]] = {}
    for current_root, directories, filenames in os.walk(project_dir, topdown=True):
        directories[:] = sorted(
            name for name in directories
            if name not in WATCH_EXCLUDED_DIRS and not name.startswith(".")
        )
        for filename in filenames:
            path = Path(current_root) / filename
            if path.resolve() in excluded:
                continue
            if path.suffix.lower() not in SOURCE_SUFFIXES and filename not in WATCH_CONFIG_NAMES:
                continue
            try:
                stat = path.stat()
                snapshot[path.relative_to(project_dir).as_posix()] = (stat.st_mtime_ns, stat.st_size)
            except OSError:
                pass
    return snapshot


def watch_mode(project_dir: str = ".", interval: float = 1.5, output_path: str = "architecture_viewer.html"):
    """Lắng nghe thay đổi file và tự động build lại"""
    proj_path = Path(project_dir).resolve()
    print(f"[*] Che do Watch Mode dang hoat dong tai {proj_path}... Nhan Ctrl+C de dung.")
    output = Path(output_path)
    if not output.is_absolute():
        output = proj_path / output
    excluded = {output.resolve(), output.with_suffix(".excalidraw").resolve()}
    last_mtimes = watch_source_snapshot(proj_path, excluded)
    generate_html_file(str(proj_path), str(output))

    while True:
        try:
            time.sleep(interval)
            current_mtimes = watch_source_snapshot(proj_path, excluded)
            if current_mtimes != last_mtimes:
                print(f"[*] Phat hien thay doi file lúc {time.strftime('%H:%M:%S')}. Dang cap nhat so do...")
                generate_html_file(str(proj_path), str(output))
                last_mtimes = watch_source_snapshot(proj_path, excluded)
        except KeyboardInterrupt:
            print("\n[*] Da dung Watch Mode.")
            break


def main():
    parser = argparse.ArgumentParser(description="Excali-Flow: Universal Architecture & Diagram Generator.")
    parser.add_argument("target", nargs="?", default=None, help="Thu muc du an can quet (mac dinh: .)")
    parser.add_argument("-d", "--dir", default=None, help="Thu muc du an can quet (mac dinh: .)")
    parser.add_argument("-o", "--out", default="architecture_viewer.html", help="Duong dan file HTML dau ra")
    parser.add_argument("--open", action="store_true", help="Tu dong mo trinh duyet sau khi tao")
    parser.add_argument("--install-hook", action="store_true", help="Cai dat Git Hooks cho du an")
    parser.add_argument("--force-hook", action="store_true", help="Cho phep cap nhat hook do Excali-Flow quan ly")
    parser.add_argument("--watch", action="store_true", help="Tu dong lang nghe thay doi file va render lai")
    parser.add_argument("--excalidraw-out", help="Duong dan scene .excalidraw co the chinh sua")
    parser.add_argument("--with-excalidraw", action="store_true", help="Tao scene .excalidraw ben canh HTML")
    parser.add_argument("--offline-check", action="store_true", help="Kiem tra runtime offline va thoat")
    parser.add_argument("--no-graphify", action="store_true", help="Bo qua tu dong chay Graphify khi chua co graph.json")
    parser.add_argument("--strict", action="store_true", help="Che do Fail-Closed: bao loi va thoat ngay neu Graphify hoac do thi that bai")
    parser.add_argument("--diff", help="So sanh kien truc hien tai voi file snapshot, thu muc, hoac git ref")
    parser.add_argument("--share-card", help="Xuat the anh chia se 1200x630 (README / Social Card) ra duong dan chi dinh")
    parser.add_argument("--editorial-out", help="Xuat SVG hoac HTML editorial tu chua")
    parser.add_argument("--visual-type", choices=sorted(EDITORIAL_TYPES | REPORT_TYPES), help="Grammar cho editorial output")
    parser.add_argument("--visual-data", help="Duong dan JSON brief cho Sankey, Wardley, hoac journey")
    parser.add_argument("--canvas", choices=sorted(EDITORIAL_CANVASES), default="document", help="Canvas editorial: document, slide, hoac social")
    args = parser.parse_args()

    target_dir = args.dir or args.target or "."
    out_path = args.out

    if args.offline_check:
        load_offline_runtime()
        print("[*] Offline runtime hop le: Mermaid va Panzoom da duoc dong goi.")
        return
    if args.install_hook:
        raise SystemExit(0 if install_git_hooks(target_dir, args.force_hook) else 1)

    if args.share_card:
        card_path = generate_share_card_file(target_dir, args.share_card)
        if args.open:
            print("[*] Dang mo Share Card tren trinh duyet...")
            webbrowser.open(f"file:///{card_path}")
        return

    if args.editorial_out:
        visual_type = args.visual_type or "architecture"
        try:
            visual_data = load_visual_brief(args.visual_data) if args.visual_data else None
            full_path = generate_editorial_file(target_dir, args.editorial_out, visual_type, visual_data, args.canvas)
        except EditorialValidationError as error:
            parser.error(str(error))
        if args.open:
            print("[*] Dang mo tren trinh duyet...")
            webbrowser.open(f"file:///{full_path}")
        return

    if args.watch:
        watch_mode(target_dir, output_path=out_path)
        return

    excalidraw_out = args.excalidraw_out
    if args.with_excalidraw and not excalidraw_out:
        excalidraw_out = str(Path(out_path).with_suffix(".excalidraw"))
    try:
        full_path = generate_html_file(
            target_dir,
            out_path,
            excalidraw_out,
            auto_graphify=not args.no_graphify,
            strict=args.strict,
            diff_target=args.diff
        )
    except RuntimeError as err:
        parser.error(str(err))

    if args.open:
        print("[*] Dang mo tren trinh duyet...")
        webbrowser.open(f"file:///{full_path}")


if __name__ == "__main__":
    main()
