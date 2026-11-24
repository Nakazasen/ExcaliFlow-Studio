"""Workspace domain knowledge graph scanner and Excalidraw exporter."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from excaliflow.explorer import IGNORED_DIRECTORIES, LANGUAGES, inspect_codebase
from excaliflow.knowledge import GRAPH_SCHEMA, validate_evidence_graph


MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
MD_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
INI_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]", re.MULTILINE)
YAML_KEY_RE = re.compile(r"^([A-Za-z_][\w.-]*)\s*:", re.MULTILINE)
TOML_SECTION_RE = re.compile(r"^\s*\[{1,2}\s*([^\]]+?)\s*\]{1,2}", re.MULTILINE)
SQL_DECL_RE = re.compile(
    r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP(?:ORARY)?\s+)?(TABLE|VIEW|FUNCTION|PROCEDURE)\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z_][\w.\[\]\"`]*)",
    re.MULTILINE | re.IGNORECASE,
)

TYPE_COLORS = {
    "answer": "#ff7a45",
    "document": "#5d83d6",
    "chunk": "#4ba980",
    "entity": "#a46cdb",
    "claim": "#d49a29",
    "code": "#2c8498",
    "case": "#ce5c70",
}

SCAN_EXTENSIONS = {
    ".md", ".csv", ".json", ".ini", ".yaml", ".yml", ".toml", ".sql",
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".cs", ".bas", ".cls",
}


def write_text_atomic(content: str, output_path: str | Path) -> Path:
    """Atomically write UTF-8 text via a temporary sibling file and os.replace."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, delete=False, suffix=".tmp") as handle:
        temporary = Path(handle.name)
        handle.write(content)
    try:
        os.replace(temporary, output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return output


def _stable_id(prefix: str, raw: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw).strip("-").lower()[:40]
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}-{slug}-{digest}" if slug else f"{prefix}-{digest}"


def _read_text_safe(path: Path, limit: int = 250_000) -> str:
    raw = path.read_bytes()[:limit]
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _walk_workspace_files(root: Path, include_globs: list[str] | None = None) -> list[Path]:
    files: list[Path] = []
    skipped_dirs = set(IGNORED_DIRECTORIES) | {"backups", "Audio_Lectures", "__pycache__"}
    for current_root, dirs, names in os.walk(root, topdown=True):
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in skipped_dirs
            and not d.startswith((".venv", "venv"))
            and not (Path(current_root) / d).is_symlink()
        )
        cur = Path(current_root)
        for name in sorted(names):
            path = cur / name
            if path.suffix.lower() not in SCAN_EXTENSIONS:
                continue
            rel = path.relative_to(root).as_posix()
            if include_globs and not any(path.match(pat) or Path(rel).match(pat) for pat in include_globs):
                continue
            files.append(path)
    return files


def build_workspace_knowledge_graph(
    root: str | Path,
    include_globs: list[str] | None = None,
    max_nodes: int = 120,
) -> dict[str, Any]:
    """Scan markdown, CSV, JSON/INI, C#, VBA, and source files into a validated evidence-graph/v1."""
    workspace = Path(root).resolve()
    if not workspace.is_dir():
        raise ValueError(f"Workspace directory does not exist: {workspace}")

    budget = max(12, int(max_nodes))
    files = _walk_workspace_files(workspace, include_globs)
    if not files:
        raise ValueError(f"No supported documentation or source files found in: {workspace}")

    code_report = inspect_codebase(workspace)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_map: dict[str, dict[str, Any]] = {}
    edge_ids: set[str] = set()

    def add_node(node: dict[str, Any]) -> bool:
        nid = node["id"]
        if nid in node_map:
            return True
        if len(nodes) >= budget:
            return False
        node_map[nid] = node
        nodes.append(node)
        return True

    def add_edge(
        from_id: str,
        to_id: str,
        relation: str,
        *,
        origin: str = "source_scan",
        confidence: float = 0.92,
        review_status: str = "verified",
        location: str,
        source_node_id: str | None = None,
    ) -> None:
        if from_id not in node_map or to_id not in node_map:
            return
        eid = _stable_id("edge", f"{from_id}->{to_id}:{relation}")
        if eid in edge_ids:
            return
        edge_ids.add(eid)
        edges.append({
            "id": eid,
            "from": from_id,
            "to": to_id,
            "relation": relation,
            "origin": origin,
            "confidence": round(min(1.0, max(0.0, float(confidence))), 3),
            "review_status": review_status,
            "receipts": [{"source_node_id": source_node_id or to_id, "location": location}],
        })

    # Reserve room for core summary answer + primary chunk
    md_files = [p for p in files if p.suffix.lower() == ".md"]
    csv_files = [p for p in files if p.suffix.lower() == ".csv"]
    cfg_files = [p for p in files if p.suffix.lower() in {".json", ".ini", ".yaml", ".yml", ".toml"}]
    sql_files = [p for p in files if p.suffix.lower() == ".sql"]
    code_files = [p for p in files if p.suffix.lower() in LANGUAGES] + sql_files

    answer_id = "answer-workspace-map"
    summary_text = (
        f"Workspace '{workspace.name}': {len(md_files)} Markdown docs, {len(csv_files)} CSV datasets, "
        f"{len(cfg_files)} config files, {len(code_files)} source/SQL files ({len(code_report['symbols'])} symbols)."
    )
    add_node({
        "id": answer_id,
        "type": "answer",
        "label": f"{workspace.name} Knowledge Architecture",
        "origin": "source_scan",
        "confidence": 0.98,
        "review_status": "verified",
        "properties": {"location": ".", "text": summary_text},
    })

    # Proportional document budget so markdown-heavy repos never starve code or config nodes
    doc_nodes_by_rel: dict[str, str] = {}
    doc_nodes_by_name: dict[str, str] = {}
    chunk_ids: list[str] = []
    md_links_queue: list[tuple[str, str, str]] = []
    symbol_mentions_candidates: list[tuple[str, str, str]] = []
    sql_symbols: list[dict[str, Any]] = []

    doc_budget_slots = max(6, int(budget * 0.52) - len(nodes))
    buckets = [lst for lst in (md_files, csv_files + cfg_files, code_files) if lst]
    prioritized_docs: list[Path] = []
    seen_doc_paths: set[Path] = set()
    indices = [0] * len(buckets)
    while len(prioritized_docs) < doc_budget_slots:
        progressed = False
        for b_idx, bucket in enumerate(buckets):
            if indices[b_idx] < len(bucket) and len(prioritized_docs) < doc_budget_slots:
                candidate = bucket[indices[b_idx]]
                indices[b_idx] += 1
                if candidate not in seen_doc_paths:
                    seen_doc_paths.add(candidate)
                    prioritized_docs.append(candidate)
                    progressed = True
        if not progressed:
            break

    for path in prioritized_docs:
        if len(nodes) >= max(8, int(budget * 0.52)):
            break
        rel = path.relative_to(workspace).as_posix()
        suffix = path.suffix.lower()
        text = _read_text_safe(path)
        title = path.name
        detail_lines: list[str] = [f"File: {rel}"]
        if suffix == ".md":
            h_match = MD_HEADING_RE.search(text)
            if h_match:
                title = h_match.group(2).strip()[:64]
            headings = [m.group(2).strip() for _, m in zip(range(6), MD_HEADING_RE.finditer(text))]
            if headings:
                detail_lines.append("Headings: " + " | ".join(headings))
            for link_match in MD_LINK_RE.finditer(text):
                md_links_queue.append((rel, link_match.group(1).strip(), link_match.group(2).strip()))
            symbol_mentions_candidates.append((rel, text, suffix))
        elif suffix == ".csv":
            rows = text.splitlines()
            header = rows[0][:140] if rows else ""
            detail_lines.append(f"Rows: {max(0, len(rows) - 1)} | Columns: {header}")
        elif suffix == ".json":
            detail_lines.append(f"JSON size: {path.stat().st_size} bytes")
        elif suffix == ".ini":
            sections = [m.group(1) for _, m in zip(range(8), INI_SECTION_RE.finditer(text))]
            if sections:
                detail_lines.append("Sections: " + ", ".join(sections))
        elif suffix in {".yaml", ".yml"}:
            keys = [m.group(1) for _, m in zip(range(10), YAML_KEY_RE.finditer(text))]
            if keys:
                detail_lines.append("Keys: " + ", ".join(keys))
        elif suffix == ".toml":
            sections = [m.group(1) for _, m in zip(range(8), TOML_SECTION_RE.finditer(text))]
            if sections:
                detail_lines.append("Sections: " + ", ".join(sections))
        elif suffix == ".sql":
            decls: list[str] = []
            for m in SQL_DECL_RE.finditer(text):
                obj_kind, obj_name = m.group(1).lower(), m.group(2).strip('"`[]')
                line_no = text.count("\n", 0, m.start()) + 1
                decls.append(f"{obj_kind} {obj_name}")
                sql_symbols.append({
                    "name": obj_name.split(".")[-1],
                    "qualified_name": obj_name,
                    "kind": obj_kind,
                    "file": rel,
                    "line": line_no,
                })
            if decls:
                detail_lines.append("SQL Objects: " + ", ".join(decls[:8]))
        else:
            detail_lines.append(f"Language: {LANGUAGES.get(suffix, suffix)}")

        did = _stable_id("doc", rel)
        is_doc_artifact = suffix in {".md", ".csv", ".json", ".ini", ".yaml", ".yml", ".toml"}
        if add_node({
            "id": did,
            "type": "document",
            "label": title if suffix == ".md" else path.name,
            "origin": "source_document" if is_doc_artifact else "source_scan",
            "confidence": 0.96,
            "review_status": "verified",
            "properties": {"location": rel, "kind": suffix.lstrip("."), "text": "\n".join(detail_lines)},
        }):
            doc_nodes_by_rel[rel] = did
            doc_nodes_by_name.setdefault(path.name.lower(), did)

    # Create verified evidence chunk nodes so answer always has supported_by -> chunk
    chunk_sources = md_files[:8] or csv_files[:4] or cfg_files[:3] or code_files[:4]
    for path in chunk_sources:
        if len(nodes) >= max(10, int(budget * 0.68)):
            break
        rel = path.relative_to(workspace).as_posix()
        text = _read_text_safe(path, 20_000)
        snippet_lines = [line.strip() for line in text.splitlines() if line.strip()][:5]
        snippet = "\n".join(snippet_lines)[:420] or f"Indexed artifact {rel}"
        cid = _stable_id("chunk", rel)
        parent_doc = doc_nodes_by_rel.get(rel)
        loc = f"{rel}:1-{max(1, min(12, len(snippet_lines) + 1))}"
        if add_node({
            "id": cid,
            "type": "chunk",
            "label": f"{path.name} §1",
            "origin": "source_document",
            "confidence": 0.95,
            "review_status": "verified",
            "properties": {"location": loc, "text": snippet, "score": 0.95},
        }):
            chunk_ids.append(cid)
            add_edge(answer_id, cid, "supported_by", origin="retrieval", confidence=0.95, location=loc, source_node_id=cid)
            if parent_doc:
                add_edge(cid, parent_doc, "extracted_from", origin="source_document", confidence=0.98, location=loc, source_node_id=parent_doc)

    # Guarantee at least one chunk if budget cut it short
    if not chunk_ids:
        first_rel = files[0].relative_to(workspace).as_posix()
        fallback_cid = _stable_id("chunk", f"overview-{first_rel}")
        node_map[fallback_cid] = {
            "id": fallback_cid,
            "type": "chunk",
            "label": f"{files[0].name} overview",
            "origin": "source_scan",
            "confidence": 0.9,
            "review_status": "verified",
            "properties": {"location": f"{first_rel}:1", "text": summary_text, "score": 0.9},
        }
        nodes.append(node_map[fallback_cid])
        chunk_ids.append(fallback_cid)
        add_edge(answer_id, fallback_cid, "supported_by", origin="retrieval", confidence=0.9, location=f"{first_rel}:1", source_node_id=fallback_cid)

    # Add top code symbols across Python, C#, VBA, SQL, etc.
    symbol_nodes_by_name: dict[str, list[str]] = defaultdict(list)
    kind_rank = {"class": 0, "interface": 0, "module": 0, "table": 0, "view": 1, "struct": 1, "function": 2, "procedure": 2, "sub": 2, "method": 3, "declaration": 4}
    all_symbols = list(code_report["symbols"]) + sql_symbols
    sorted_symbols = sorted(all_symbols, key=lambda s: (kind_rank.get(s.get("kind", ""), 5), s["file"], s["line"]))
    seen_symbol_keys: set[tuple[str, str]] = set()
    for sym in sorted_symbols:
        if len(nodes) >= int(budget * 0.88):
            break
        key = (sym["file"], sym["qualified_name"])
        if key in seen_symbol_keys:
            continue
        seen_symbol_keys.add(key)
        loc = f"{sym['file']}:{sym['line']}"
        code_id = _stable_id("code", loc + ":" + sym["qualified_name"])
        if add_node({
            "id": code_id,
            "type": "code",
            "label": sym["qualified_name"],
            "origin": "source_scan",
            "confidence": 1.0,
            "review_status": "verified",
            "properties": {"location": loc, "file": sym["file"], "line": sym["line"], "kind": sym.get("kind", "symbol"), "text": f"{sym.get('kind', 'symbol')} {sym['qualified_name']} at {loc}"},
        }):
            symbol_nodes_by_name[sym["name"].lower()].append(code_id)
            parent_doc = doc_nodes_by_rel.get(sym["file"]) or doc_nodes_by_name.get(Path(sym["file"]).name.lower())
            if parent_doc:
                add_edge(code_id, parent_doc, "defined_in", origin="source_scan", confidence=1.0, location=loc, source_node_id=parent_doc)

    # Connect internal code-to-code dependencies across scanned files
    module_key_to_doc: dict[str, str] = {}
    for rel, did in doc_nodes_by_rel.items():
        if Path(rel).suffix.lower() not in LANGUAGES:
            continue
        mod = Path(rel).with_suffix("").as_posix().replace("/", ".")
        module_key_to_doc.setdefault(mod.lower(), did)
        module_key_to_doc.setdefault(Path(rel).stem.lower(), did)
        if mod.startswith("src."):
            module_key_to_doc.setdefault(mod.removeprefix("src.").lower(), did)
    for sym in code_report["symbols"]:
        if sym.get("kind") in {"class", "interface", "module", "struct"}:
            parent_doc = doc_nodes_by_rel.get(sym["file"])
            if parent_doc:
                module_key_to_doc.setdefault(sym["name"].lower(), parent_doc)
                module_key_to_doc.setdefault(sym["qualified_name"].lower(), parent_doc)

    for rel_item in code_report["relationships"]:
        src_doc = doc_nodes_by_rel.get(rel_item["from"])
        if not src_doc:
            continue
        raw_target = str(rel_item["to"]).lstrip(".").strip()
        if not raw_target:
            continue
        candidates = [
            raw_target.lower(),
            raw_target.split(".")[0].lower(),
            Path(raw_target).stem.lower(),
        ]
        tgt_doc = next((module_key_to_doc[c] for c in candidates if c in module_key_to_doc), None)
        if tgt_doc and tgt_doc != src_doc:
            add_edge(
                src_doc,
                tgt_doc,
                "depends_on",
                origin="source_scan",
                confidence=0.94,
                location=f"{rel_item['from']}:{rel_item['line']}",
                source_node_id=src_doc,
            )

    # Add cross-file markdown link claims
    for src_rel, link_label, target_raw in md_links_queue:
        if target_raw.startswith(("http://", "https://", "#")):
            continue
        src_doc = doc_nodes_by_rel.get(src_rel)
        if not src_doc:
            continue
        clean_target = target_raw.split("#")[0].replace("\\", "/")
        basename = Path(clean_target.replace("file:///", "")).name.lower()
        tgt_doc = doc_nodes_by_rel.get(clean_target) or doc_nodes_by_name.get(basename)
        if tgt_doc and tgt_doc != src_doc:
            add_edge(src_doc, tgt_doc, "references", origin="source_document", confidence=0.9, location=f"{src_rel} -> {basename}", source_node_id=src_doc)

    # Connect shared entities (filenames or prominent code classes/modules mentioned in markdown docs)
    entity_candidates: Counter[str] = Counter()
    for sym in sorted_symbols:
        if len(sym["name"]) >= 4 and sym.get("kind") in {"class", "interface", "module", "function", "sub", "declaration"}:
            entity_candidates[sym["name"]] += 1

    for sym_name, _ in entity_candidates.most_common(12):
        if len(nodes) >= budget:
            break
        code_ids = symbol_nodes_by_name.get(sym_name.lower(), [])
        if not code_ids:
            continue
        eid = _stable_id("entity", sym_name)
        matching_docs = [
            doc_nodes_by_rel[rel]
            for rel, md_text, _ in symbol_mentions_candidates
            if rel in doc_nodes_by_rel and re.search(rf"\b{re.escape(sym_name)}\b", md_text)
        ]
        if add_node({
            "id": eid,
            "type": "entity",
            "label": sym_name,
            "origin": "source_scan",
            "confidence": 0.9,
            "review_status": "verified",
            "properties": {"kind": "symbol_concept", "text": f"Cross-referenced symbol '{sym_name}' across code and documentation."},
        }):
            for cid in code_ids[:2]:
                loc = str(node_map[cid].get("properties", {}).get("location", sym_name))
                add_edge(cid, eid, "implements", origin="source_scan", confidence=0.95, location=loc, source_node_id=cid)
            for did in matching_docs[:3]:
                loc = str(node_map[did].get("properties", {}).get("location", sym_name))
                add_edge(did, eid, "mentions", origin="source_document", confidence=0.82, review_status="verified", location=loc, source_node_id=did)

    graph = {
        "schema_version": GRAPH_SCHEMA,
        "title": f"{workspace.name} Knowledge Graph",
        "query": f"Workspace scan: {workspace.name}",
        "nodes": nodes,
        "edges": edges,
    }
    validate_evidence_graph(graph)
    return graph


def _rect_border_point(rect: dict[str, Any], target_x: float, target_y: float) -> tuple[float, float]:
    """Compute intersection point on a rectangle border toward (target_x, target_y)."""
    cx = float(rect["x"]) + float(rect["width"]) / 2.0
    cy = float(rect["y"]) + float(rect["height"]) / 2.0
    dx = target_x - cx
    dy = target_y - cy
    if dx == 0 and dy == 0:
        return cx, cy
    half_w = float(rect["width"]) / 2.0
    half_h = float(rect["height"]) / 2.0
    scale_x = abs(dx) / half_w if half_w else 0.0
    scale_y = abs(dy) / half_h if half_h else 0.0
    denom = max(scale_x, scale_y, 1e-6)
    return round(cx + dx / denom, 2), round(cy + dy / denom, 2)


def export_excalidraw_scene(graph: dict[str, Any], lang: str = "vi") -> dict[str, Any]:
    """Convert a validated evidence-graph/v1 into an Excalidraw v2 scene JSON with bound arrows & labels."""
    from excaliflow.evidence_atlas import _layout, _relation_label

    validate_evidence_graph(graph)
    positions, _, _ = _layout(graph)
    elements: list[dict[str, Any]] = []
    node_rects: dict[str, dict[str, Any]] = {}
    now = 1

    for index, node in enumerate(graph["nodes"]):
        nid = str(node["id"])
        x, y = positions.get(nid, (80 + (index % 3) * 320, 80 + (index // 3) * 140))
        ntype = str(node.get("type", "entity"))
        stroke = TYPE_COLORS.get(ntype, "#38bdf8")
        rect_id = f"rect-{nid}"
        text_id = f"text-{nid}"
        label = f"[{ntype.upper()}] {node.get('label', nid)}"
        if len(label) > 72:
            label = label[:69].rstrip() + "..."
        rect = {
            "id": rect_id,
            "type": "rectangle",
            "x": float(x),
            "y": float(y),
            "width": 260,
            "height": 84,
            "angle": 0,
            "strokeColor": stroke,
            "backgroundColor": "#1e293b",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "dashed" if node.get("review_status") == "needs_review" else "solid",
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": {"type": 3},
            "seed": (index + 1) * 131,
            "version": 1,
            "versionNonce": (index + 1) * 911,
            "isDeleted": False,
            "boundElements": [{"type": "text", "id": text_id}],
            "updated": now,
            "link": None,
            "locked": False,
        }
        txt = {
            "id": text_id,
            "type": "text",
            "x": float(x + 12),
            "y": float(y + 18),
            "width": 236,
            "height": 48,
            "angle": 0,
            "strokeColor": "#e2e8f0",
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "roughness": 0,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": None,
            "boundElements": [],
            "text": label,
            "originalText": label,
            "autoResize": True,
            "lineHeight": 1.25,
            "fontSize": 14,
            "fontFamily": 1,
            "textAlign": "left",
            "verticalAlign": "middle",
            "containerId": rect_id,
            "seed": (index + 1) * 257,
            "version": 1,
            "versionNonce": (index + 1) * 977,
            "isDeleted": False,
            "updated": now,
            "link": None,
            "locked": False,
        }
        elements.extend((rect, txt))
        node_rects[nid] = rect

    for e_idx, edge in enumerate(graph["edges"]):
        src = node_rects.get(str(edge["from"]))
        tgt = node_rects.get(str(edge["to"]))
        if not src or not tgt:
            continue
        tgt_cx = tgt["x"] + tgt["width"] / 2.0
        tgt_cy = tgt["y"] + tgt["height"] / 2.0
        src_cx = src["x"] + src["width"] / 2.0
        src_cy = src["y"] + src["height"] / 2.0
        sx, sy = _rect_border_point(src, tgt_cx, tgt_cy)
        tx, ty = _rect_border_point(tgt, src_cx, src_cy)
        dx = round(tx - sx, 2)
        dy = round(ty - sy, 2)
        arrow_id = f"arrow-{edge['id']}"
        label_id = f"label-{edge['id']}"
        rel_text = _relation_label(edge.get("relation", ""), lang)
        arrow = {
            "id": arrow_id,
            "type": "arrow",
            "x": float(sx),
            "y": float(sy),
            "width": float(abs(dx)),
            "height": float(abs(dy)),
            "points": [[0, 0], [dx, dy]],
            "angle": 0,
            "strokeColor": "#64748b",
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1.5,
            "strokeStyle": "dashed" if edge.get("review_status") == "needs_review" else "solid",
            "roughness": 1,
            "opacity": 85,
            "groupIds": [],
            "frameId": None,
            "roundness": {"type": 2},
            "boundElements": [{"type": "text", "id": label_id}],
            "startBinding": {"elementId": src["id"], "focus": 0, "gap": 4},
            "endBinding": {"elementId": tgt["id"], "focus": 0, "gap": 4},
            "lastCommittedPoint": None,
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "seed": (e_idx + 1) * 389,
            "version": 1,
            "versionNonce": (e_idx + 1) * 1013,
            "isDeleted": False,
            "updated": now,
            "link": None,
            "locked": False,
        }
        src["boundElements"].append({"type": "arrow", "id": arrow_id})
        tgt["boundElements"].append({"type": "arrow", "id": arrow_id})
        label_w = min(140, max(56, len(rel_text) * 7 + 12))
        arrow_label = {
            "id": label_id,
            "type": "text",
            "x": round(sx + dx / 2.0 - label_w / 2.0, 2),
            "y": round(sy + dy / 2.0 - 10.0, 2),
            "width": float(label_w),
            "height": 20.0,
            "angle": 0,
            "strokeColor": "#94a3b8",
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "roughness": 0,
            "opacity": 95,
            "groupIds": [],
            "frameId": None,
            "roundness": None,
            "boundElements": [],
            "text": rel_text,
            "originalText": rel_text,
            "autoResize": True,
            "lineHeight": 1.2,
            "fontSize": 11,
            "fontFamily": 1,
            "textAlign": "center",
            "verticalAlign": "middle",
            "containerId": arrow_id,
            "seed": (e_idx + 1) * 433,
            "version": 1,
            "versionNonce": (e_idx + 1) * 1091,
            "isDeleted": False,
            "updated": now,
            "link": None,
            "locked": False,
        }
        elements.extend((arrow, arrow_label))

    return {
        "type": "excalidraw",
        "version": 2,
        "source": f"excaliflow-studio:{lang}",
        "elements": elements,
        "appState": {
            "gridSize": 20,
            "viewBackgroundColor": "#0b1120",
        },
        "files": {},
    }
