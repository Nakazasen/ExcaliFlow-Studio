"""Offline, answer-centric Flowsint 2.0 Evidence Atlas renderer for a validated Evidence Graph."""

from __future__ import annotations

from collections import defaultdict
import html
import json
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from excaliflow.knowledge import REVIEW_STATUSES, validate_evidence_graph


TYPE_LABELS = {
    "answer": "Câu trả lời",
    "document": "Tài liệu nguồn",
    "chunk": "Đoạn bằng chứng",
    "entity": "Khái niệm",
    "claim": "Nhận định",
    "code": "Mã nguồn",
    "case": "Case",
}

TYPE_COLORS = {
    "answer": "#ff7a45",
    "document": "#5d83d6",
    "chunk": "#4ba980",
    "entity": "#a46cdb",
    "claim": "#d49a29",
    "code": "#2c8498",
    "case": "#ce5c70",
}


def _relation_label(relation: Any) -> str:
    labels = {
        "supports": "dẫn chứng cho",
        "supported by": "dẫn chứng cho",
        "supported_by": "dẫn chứng cho",
        "cites": "trích từ",
        "extracted_from": "trích từ",
        "extracted from": "trích từ",
        "derived_from": "suy ra từ",
        "derived from": "suy ra từ",
        "mentions": "liên quan tới",
        "contains": "chứa đoạn",
        "depends_on": "phụ thuộc vào",
        "implemented_by": "triển khai bởi",
    }
    raw = str(relation or "liên kết").strip().lower().replace("-", " ")
    return labels.get(raw, raw.replace("_", " "))


def _display_label(node: dict) -> str:
    text = node["label"]
    return text if len(text) <= 80 else text[:77].rstrip() + "…"


def _label_lines(value: Any) -> List[str]:
    """Fit one node label inside its card, including CJK and Vietnamese filenames."""
    text = " ".join(str(value or "").split()) or "-"
    contains_wide = any(ord(c) >= 0x2E80 for c in text)
    limit = 18 if contains_wide else 28
    lines: List[str] = []
    remaining = text
    while remaining and len(lines) < 2:
        if len(remaining) <= limit:
            lines.append(remaining)
            remaining = ""
            break
        split_at = remaining.rfind(" ", 0, limit + 1)
        if split_at < max(5, limit // 2):
            split_at = limit
        lines.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        lines[-1] = f"{lines[-1][:max(1, limit - 3)].rstrip()}..."
    return lines or ["-"]


def _layout(graph: dict) -> tuple[dict[str, tuple[int, int]], int, int]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for node in graph["nodes"]:
        groups[node["type"]].append(node)
    order = ("answer", "claim", "entity", "code", "chunk", "document", "case")
    positions: dict[str, tuple[int, int]] = {}
    y = 75
    width = 1080
    for node_type in order:
        items = groups[node_type]
        if not items:
            continue
        columns = min(3, len(items))
        for index, node in enumerate(items):
            positions[node["id"]] = (70 + (index % columns) * 335, y + (index // columns) * 140)
        y += ((len(items) + columns - 1) // columns) * 140 + 55
    return positions, width, max(420, y)


def _receipt_text(edge: dict) -> str:
    status = "Cần xem lại" if edge.get("review_status") == "needs_review" else "Đã có bằng chứng"
    locations = ", ".join(receipt.get("location", "") for receipt in edge.get("receipts", []) if receipt.get("location"))
    origin = edge.get("origin", "local")
    conf = edge.get("confidence")
    conf_str = f"; độ tin cậy {conf:.0%}" if conf is not None else ""
    loc_str = f"; vị trí: {locations}" if locations else ""
    return f"{status}. Nguồn: {origin}{conf_str}{loc_str}."


def _node_svg(node: dict, position: tuple[int, int], is_focused: bool) -> str:
    """Render one evidence node with pill shape and clean multi-line label."""
    x, y = position
    classes = "node"
    if is_focused:
        classes += " focus"
    if node.get("review_status") == "needs_review":
        classes += " needs-review"
        review_label = f'<text class="review-label" x="{x + 14}" y="{y + 72}">Cần xem lại</text>'
    else:
        review_label = ""

    lines = _label_lines(node.get("label", ""))
    tspans = "".join(
        f'<tspan x="{x + 14}" dy="{0 if i == 0 else 17}">{html.escape(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    node_type_label = TYPE_LABELS.get(node.get("type", ""), node.get("type", "").upper())

    return (
        f'<g class="{classes}" data-node="{html.escape(str(node["id"]))}" tabindex="0" role="button">'
        f'<rect x="{x}" y="{y}" width="260" height="84" rx="14" '
        f'style="--node-color:{TYPE_COLORS.get(node["type"], "#38bdf8")}"/>'
        f'<text class="node-type" x="{x + 14}" y="{y + 24}">{html.escape(node_type_label)}</text>'
        f'<text class="node-label" x="{x + 14}" y="{y + 46}">{tspans}</text>'
        f'{review_label}</g>'
    )


def build_evidence_atlas_html(graph: dict) -> str:
    """Create one standalone Flowsint 2.0 HTML document from a validated evidence graph."""
    validate_evidence_graph(graph)
    positions, width, height = _layout(graph)
    focus_ids = {
        node["id"]
        for node in graph["nodes"]
        if node["type"] in {"answer", "chunk", "document"}
    }
    focus_edges = {
        edge["id"]
        for edge in graph["edges"]
        if edge["from"] in focus_ids and edge["to"] in focus_ids
    }

    # Bounding boxes of all nodes with safety margin (labels must never collide)
    node_boxes = [
        (p[0] - 16, p[1] - 16, p[0] + 260 + 16, p[1] + 84 + 16)
        for p in positions.values()
    ]

    # Calculate vertical bounds for each tier
    tier_ranges: Dict[str, List[int]] = {}
    for n in graph.get("nodes", []):
        nid = str(n.get("id", ""))
        ntype = str(n.get("type", ""))
        p = positions.get(nid)
        if p:
            y1, y2 = p[1], p[1] + 84
            if ntype not in tier_ranges:
                tier_ranges[ntype] = [y1, y2]
            else:
                tier_ranges[ntype][0] = min(tier_ranges[ntype][0], y1)
                tier_ranges[ntype][1] = max(tier_ranges[ntype][1], y2)

    band_y1 = None
    if "answer" in tier_ranges and "chunk" in tier_ranges:
        band_y1 = (tier_ranges["answer"][1] + tier_ranges["chunk"][0]) // 2

    band_y2 = None
    if "chunk" in tier_ranges and "document" in tier_ranges:
        band_y2 = (tier_ranges["chunk"][1] + tier_ranges["document"][0]) // 2

    edge_svg_paths: List[str] = []
    edge_label_svgs: List[str] = []
    placed_label_coords: List[Tuple[int, int]] = []

    for edge in graph.get("edges", []):
        p_from = positions.get(edge["from"])
        p_to = positions.get(edge["to"])
        if not p_from or not p_to:
            continue

        x1, y1 = float(p_from[0] + 130), float(p_from[1] + 42)
        x2, y2 = float(p_to[0] + 130), float(p_to[1] + 42)
        dy = y2 - y1
        dx = x2 - x1

        if abs(dy) >= 10:
            cx1, cy1 = x1, y1 + dy * 0.45
            cx2, cy2 = x2, y2 - dy * 0.45
        else:
            cx1, cy1 = x1 + dx * 0.45, y1 - 25
            cx2, cy2 = x2 - dx * 0.45, y2 - 25

        d = f"M {x1:.1f},{y1:.1f} C {cx1:.1f},{cy1:.1f} {cx2:.1f},{cy2:.1f} {x2:.1f},{y2:.1f}"
        is_focus = edge["id"] in focus_edges
        cls_str = "edge focus" if is_focus else "edge"

        edge_svg_paths.append(
            f'<path marker-end="url(#atlas-arrow)" fill="none" class="{cls_str}" '
            f'data-edge="{html.escape(edge["id"])}" d="{d}" />'
        )

        # Calculate safe position for relation label
        cand_y = None
        if p_from[1] < p_to[1]:
            if band_y1 is not None and y1 < band_y1 < y2:
                cand_y = band_y1
            elif band_y2 is not None and y1 < band_y2 < y2:
                cand_y = band_y2
        else:
            if band_y2 is not None and y2 < band_y2 < y1:
                cand_y = band_y2
            elif band_y1 is not None and y2 < band_y1 < y1:
                cand_y = band_y1

        if cand_y is not None and y2 != y1:
            t_param = max(0.0, min(1.0, (cand_y - y1) / (y2 - y1)))
            cand_x = int(
                (1 - t_param)**3 * x1
                + 3 * (1 - t_param)**2 * t_param * cx1
                + 3 * (1 - t_param) * t_param**2 * cx2
                + t_param**3 * x2
            )
            cand_y_pt = int(
                (1 - t_param)**3 * y1
                + 3 * (1 - t_param)**2 * t_param * cy1
                + 3 * (1 - t_param) * t_param**2 * cy2
                + t_param**3 * y2
            )
        else:
            cand_x = int(0.125 * x1 + 0.375 * cx1 + 0.375 * cx2 + 0.125 * x2)
            cand_y_pt = int(0.125 * y1 + 0.375 * cy1 + 0.375 * cy2 + 0.125 * y2)

        rel_text = html.escape(_relation_label(edge.get("relation", "")))
        w_lbl = min(140, max(76, 16 + len(rel_text) * 6))
        h_lbl = 20
        bx1 = cand_x - w_lbl // 2
        bx2 = cand_x + w_lbl // 2
        by1 = cand_y_pt - h_lbl // 2
        by2 = cand_y_pt + h_lbl // 2

        collides_node = any(
            not (bx2 < nx1 or bx1 > nx2 or by2 < ny1 or by1 > ny2)
            for nx1, ny1, nx2, ny2 in node_boxes
        )
        collides_label = any(
            math.hypot(cand_x - px, cand_y_pt - py) < 70
            for px, py in placed_label_coords
        )

        if not collides_node and not collides_label:
            placed_label_coords.append((cand_x, cand_y_pt))
            edge_label_svgs.append(
                f'<g class="edge-label"><rect x="{bx1}" y="{by1}" width="{w_lbl}" height="{h_lbl}" rx="9999"/>'
                f'<text x="{cand_x}" y="{cand_y_pt + 3}" text-anchor="middle">{rel_text}</text></g>'
            )

    node_svg = "".join(
        _node_svg(node, positions[node["id"]], node["id"] in focus_ids)
        for node in graph["nodes"]
    )
    payload = json.dumps(graph, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape(graph.get("title", "Evidence Graph"))

    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidence Atlas — {title}</title>
<style>
:root {{
  --ink: #f8fafc;
  --muted: #94a3b8;
  --paper: #070b14;
  --panel: #0f172a;
  --line: #1e293b;
  --accent: #38bdf8;
  --orange: #f97316;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  overflow-x: hidden;
}}
header {{
  padding: 12px 20px;
  border-bottom: 1px solid var(--line);
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 100;
}}
.eyebrow {{
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 11px;
  font-weight: 700;
}}
h1 {{
  margin: 4px 0 6px;
  font-size: 18px;
  font-weight: 700;
  color: #f8fafc;
}}
.lede {{
  margin: 0;
  color: var(--muted);
  max-width: 850px;
  font-size: 12px;
  line-height: 1.5;
}}
main {{
  max-width: 1400px;
  margin: auto;
  padding: 16px;
}}
.toolbar {{
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 14px;
}}
button {{
  font: inherit;
  border: 1px solid #334155;
  background: #1e293b;
  border-radius: 9999px;
  padding: 6px 14px;
  cursor: pointer;
  color: #cbd5e1;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.15s ease;
}}
button:hover {{
  background: #334155;
  color: #fff;
  border-color: #475569;
}}
button.active {{
  background: rgba(56, 189, 248, 0.15);
  color: var(--accent);
  border-color: var(--accent);
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.25);
  font-weight: 700;
}}
.legend {{
  color: #64748b;
  font-size: 12px;
  margin-left: 6px;
}}
.atlas-search-box {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 9999px;
  padding: 4px 12px;
  margin-left: auto;
}}
.atlas-search-icon {{
  font-size: 12px;
}}
.atlas-search-input {{
  background: transparent;
  border: none;
  color: #f8fafc;
  font-size: 12px;
  outline: none;
  width: 160px;
  transition: width 0.2s ease;
}}
.atlas-search-input:focus {{
  width: 230px;
}}
.layout {{
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
  transition: grid-template-columns 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}}
.layout.inspector-collapsed {{
  grid-template-columns: minmax(0, 1fr) 42px;
}}
.layout.inspector-collapsed aside > *:not(.atlas-collapse-btn) {{
  display: none !important;
}}
.canvas {{
  overflow: hidden;
  position: relative;
  border: 1px solid var(--line);
  border-radius: 12px;
  background-color: var(--paper);
  background-image: radial-gradient(#1e293b 1px, transparent 1px);
  background-size: 20px 20px;
  min-height: 580px;
  box-shadow: inset 0 2px 12px rgba(0, 0, 0, 0.5);
  cursor: grab;
  user-select: none;
}}
.canvas:active {{
  cursor: grabbing;
}}
.atlas-floating-toolbar {{
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 40;
  display: flex;
  gap: 6px;
  background: rgba(15, 23, 42, 0.88);
  backdrop-filter: blur(8px);
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 4px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
}}
.atlas-tool-btn {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #cbd5e1;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}}
.atlas-tool-btn:hover {{
  background: #334155;
  border-color: #38bdf8;
  color: #38bdf8;
}}
svg {{
  display: block;
  min-width: {width}px;
  transform-origin: 0 0;
  transition: transform 0.05s ease-out;
}}
@keyframes flowDash {{
  from {{ stroke-dashoffset: 24; }}
  to {{ stroke-dashoffset: 0; }}
}}
.edge {{
  stroke: #475569;
  stroke-width: 1.8;
  opacity: 0.7;
  transition: stroke 0.2s, stroke-width 0.2s, opacity 0.2s;
  fill: none;
}}
.edge:hover, .edge.active, .edge.focus {{
  stroke: var(--accent) !important;
  stroke-width: 2.8 !important;
  opacity: 1 !important;
  stroke-dasharray: 6 3 !important;
  animation: flowDash 0.8s linear infinite !important;
  filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.7));
}}
.edge.dimmed, .node.dimmed {{
  opacity: 0.15 !important;
}}
.node.search-matched rect {{
  stroke: var(--success) !important;
  stroke-width: 3px !important;
  filter: drop-shadow(0 0 10px rgba(16, 185, 129, 0.6)) !important;
}}
.edge-label {{
  pointer-events: none;
}}
.edge-label rect {{
  fill: #0f172a;
  stroke: #334155;
  stroke-width: 1;
}}
.edge-label text {{
  font-size: 10px;
  font-weight: 600;
  fill: #94a3b8;
}}
.node {{
  cursor: pointer;
  outline: none;
}}
.node rect {{
  fill: var(--panel);
  stroke: var(--node-color);
  stroke-width: 1.8;
  rx: 12px;
  transition: all 0.15s ease;
}}
.node.needs-review rect {{
  stroke-dasharray: 6 3;
}}
.node:hover rect, .node.active rect {{
  fill: #1e293b;
  stroke-width: 3.2;
  filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.5));
}}
.node-type {{
  font-size: 11px;
  font-weight: 800;
  fill: #94a3b8;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}}
.node-label {{
  font-size: 13px;
  font-weight: 600;
  fill: #f8fafc;
  line-height: 1.4;
}}
.review-label {{
  font-size: 11px;
  font-weight: 800;
  fill: #f59e0b;
}}
body[data-view="answer"] .node:not(.focus), body[data-view="answer"] .edge:not(.focus) {{
  display: none;
}}
aside {{
  position: sticky;
  top: 70px;
  align-self: start;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--panel);
  padding: 16px;
  max-height: calc(100vh - 90px);
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}}
aside h2 {{
  font-size: 14px;
  font-weight: 700;
  color: var(--accent);
  margin: 4px 0 10px;
  word-break: break-word;
}}
.atlas-collapse-btn {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #94a3b8;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 8px;
  transition: all 0.15s ease;
}}
.atlas-collapse-btn:hover {{
  background: #334155;
  color: #38bdf8;
}}
.confidence-gauge-card {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 8px 12px;
  margin: 10px 0;
}}
.gauge-header {{
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  margin-bottom: 4px;
}}
.gauge-pct {{
  color: #38bdf8;
  font-weight: 800;
}}
.gauge-track {{
  height: 6px;
  background: #0f172a;
  border-radius: 9999px;
  overflow: hidden;
}}
.gauge-fill {{
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease, background 0.3s ease;
}}
.atlas-links-card {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 8px 12px;
  margin: 10px 0;
}}
.links-title {{
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  margin-bottom: 6px;
}}
.links-chips-wrap {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}}
.atlas-link-chip {{
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #e2e8f0;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
.atlas-link-chip:hover {{
  background: #334155;
  border-color: #38bdf8;
  color: #38bdf8;
}}
.receipt {{
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 12.5px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  color: #e2e8f0;
  padding: 12px;
  word-break: break-word;
}}
.badge {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 9999px;
  background: rgba(56, 189, 248, 0.15);
  color: var(--accent);
  border: 1px solid rgba(56, 189, 248, 0.3);
  font-size: 11px;
  font-weight: 700;
  margin: 2px 4px 4px 0;
}}
.notice {{
  border-left: 3px solid #f59e0b;
  background: rgba(245, 158, 11, 0.1);
  padding: 8px 12px;
  color: #fde68a;
  border-radius: 4px;
  font-size: 12px;
  margin-top: 10px;
}}
.atlas-copy-btn {{
  background: #334155;
  color: #f8fafc;
  border: 1px solid #475569;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
}}
.atlas-copy-btn:hover {{
  background: #475569;
}}
@media (max-width: 850px) {{
  .layout {{ display: block; }}
  aside {{ position: static; max-height: none; margin-top: 16px; }}
  h1 {{ font-size: 18px; }}
}}
</style></head><body data-view="answer"><header><div class="eyebrow">Nguồn bằng chứng · local file</div><h1>Evidence Atlas</h1><p class="lede">{title}. Bản đồ này hiển thị quan hệ có nguồn; đường nét đứt và nhãn “Cần xem lại” là nhận định chưa được xác minh.</p></header><main><div class="toolbar"><button data-view="answer" class="active">Câu trả lời &amp; nguồn</button><button data-view="full">Toàn bộ knowledge graph</button><span id="atlas-view-status" class="legend" aria-live="polite">Đang xem: Câu trả lời &amp; nguồn</span><div class="atlas-search-box"><span class="atlas-search-icon">🔍</span><input type="text" id="atlas-search-input" placeholder="Tìm kiếm thực thể..." class="atlas-search-input" /></div></div><div class="layout"><section class="canvas" aria-label="Evidence Graph"><div class="atlas-floating-toolbar" role="toolbar" aria-label="Canvas controls"><button type="button" id="atlas-btn-zoom-in" class="atlas-tool-btn" title="Phóng to">➕</button><button type="button" id="atlas-btn-zoom-out" class="atlas-tool-btn" title="Thu nhỏ">➖</button><button type="button" id="atlas-btn-fit" class="atlas-tool-btn" title="Vừa khung hình">⊡</button><button type="button" id="atlas-btn-fullscreen" class="atlas-tool-btn" title="Toàn màn hình">⛶</button></div><svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Evidence graph for {title}"><defs><marker id="atlas-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6" fill="none" stroke="#38bdf8" stroke-width="1.3"/></marker></defs>{''.join(edge_svg_paths)}{''.join(node_svg)}{''.join(edge_label_svgs)}</svg></section><aside><button type="button" id="atlas-toggle-inspector" class="atlas-collapse-btn" title="Thu gọn bảng">›</button><div class="eyebrow">Nguồn bằng chứng</div><h2 id="detail-title">Bắt đầu từ câu trả lời</h2><div id="atlas-confidence-box" class="confidence-gauge-card" style="display:none;"><div class="gauge-header"><span class="gauge-title">Độ tin cậy trích xuất</span><span id="atlas-conf-pct" class="gauge-pct">--%</span></div><div class="gauge-track"><div id="atlas-conf-fill" class="gauge-fill" style="width:0%;"></div></div></div><div id="atlas-links-box" class="atlas-links-card" style="display:none;"><div id="atlas-inbound-section" style="margin-bottom:10px;"><div class="links-title">📥 Được dẫn chứng từ (<span id="atlas-in-count">0</span>)</div><div id="atlas-in-chips" class="links-chips-wrap"></div></div><div id="atlas-outbound-section"><div class="links-title">📤 Dẫn chứng cho (<span id="atlas-out-count">0</span>)</div><div id="atlas-out-chips" class="links-chips-wrap"></div></div></div><div id="detail" class="receipt">Chọn câu trả lời, đoạn tài liệu, nhận định hoặc đường nối để xem nguồn, vị trí và độ tin cậy.</div></aside></div></main><script>
(() => {{
  const DATA = {payload};
  const nodeById = Object.fromEntries(DATA.nodes.map(node => [node.id, node]));
  const edgeById = Object.fromEntries(DATA.edges.map(edge => [edge.id, edge]));
  const status = document.getElementById('atlas-view-status');
  const detailTitle = document.getElementById('detail-title');
  const detail = document.getElementById('detail');

  const confBox = document.getElementById('atlas-confidence-box');
  const confPct = document.getElementById('atlas-conf-pct');
  const confFill = document.getElementById('atlas-conf-fill');

  const linksBox = document.getElementById('atlas-links-box');
  const inChips = document.getElementById('atlas-in-chips');
  const inCount = document.getElementById('atlas-in-count');
  const outChips = document.getElementById('atlas-out-chips');
  const outCount = document.getElementById('atlas-out-count');

  const canvasSec = document.querySelector('.canvas');
  const svgElem = canvasSec ? canvasSec.querySelector('svg') : null;
  const layout = document.querySelector('.layout');
  const toggleInspectorBtn = document.getElementById('atlas-toggle-inspector');
  const searchInput = document.getElementById('atlas-search-input');

  const TYPE_NAMES = {{
    'document': '📁 Tệp tài liệu nguồn',
    'chunk': '🏷️ Đoạn trích bằng chứng',
    'answer': '💡 Câu trả lời tổng hợp',
    'question': '❓ Câu hỏi truy vấn',
    'claim': '📌 Nhận định trích xuất',
    'code': '💻 Mã nguồn',
    'entity': '🧩 Khái niệm'
  }};

  // --- Pan & Zoom Engine ---
  let scale = 1.0;
  let panX = 0;
  let panY = 0;
  let isPanning = false;
  let startX = 0;
  let startY = 0;

  const updateTransform = () => {{
    if (!svgElem) return;
    svgElem.style.transform = `translate(${{panX}}px, ${{panY}}px) scale(${{scale}})`;
  }};

  if (canvasSec && svgElem) {{
    canvasSec.addEventListener('mousedown', (e) => {{
      if (e.target.closest('.node') || e.target.closest('button') || e.target.closest('input')) return;
      isPanning = true;
      startX = e.clientX - panX;
      startY = e.clientY - panY;
      canvasSec.style.cursor = 'grabbing';
    }});

    window.addEventListener('mousemove', (e) => {{
      if (!isPanning) return;
      panX = e.clientX - startX;
      panY = e.clientY - startY;
      updateTransform();
    }});

    window.addEventListener('mouseup', () => {{
      isPanning = false;
      if (canvasSec) canvasSec.style.cursor = 'grab';
    }});

    canvasSec.addEventListener('wheel', (e) => {{
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.12 : 0.88;
      scale = Math.min(Math.max(0.3, scale * zoomFactor), 3.0);
      updateTransform();
    }}, {{ passive: false }});
  }}

  // Toolbar button handlers
  document.getElementById('atlas-btn-zoom-in')?.addEventListener('click', () => {{
    scale = Math.min(3.0, scale * 1.2);
    updateTransform();
  }});

  document.getElementById('atlas-btn-zoom-out')?.addEventListener('click', () => {{
    scale = Math.max(0.3, scale / 1.2);
    updateTransform();
  }});

  document.getElementById('atlas-btn-fit')?.addEventListener('click', () => {{
    scale = 1.0;
    panX = 0;
    panY = 0;
    updateTransform();
  }});

  document.getElementById('atlas-btn-fullscreen')?.addEventListener('click', () => {{
    const target = canvasSec || document.documentElement;
    if (!document.fullscreenElement) {{
      target.requestFullscreen().catch(() => {{}});
    }} else {{
      document.exitFullscreen().catch(() => {{}});
    }}
  }});

  // --- Collapsible Inspector ---
  if (toggleInspectorBtn && layout) {{
    toggleInspectorBtn.addEventListener('click', () => {{
      const isCollapsed = layout.classList.toggle('inspector-collapsed');
      toggleInspectorBtn.textContent = isCollapsed ? '‹' : '›';
      toggleInspectorBtn.title = isCollapsed ? 'Mở rộng bảng' : 'Thu gọn bảng';
    }});
  }}

  // --- Real-time Search ---
  if (searchInput) {{
    searchInput.addEventListener('input', () => {{
      const q = searchInput.value.toLowerCase().trim();
      document.querySelectorAll('.node').forEach(nodeEl => {{
        const nid = nodeEl.dataset.node;
        const nObj = nodeById[nid];
        if (!q) {{
          nodeEl.classList.remove('search-matched', 'dimmed');
          return;
        }}
        const haystack = ((nObj?.label || '') + ' ' + (nObj?.properties?.text || '') + ' ' + (nObj?.properties?.location || '')).toLowerCase();
        const matched = haystack.includes(q);
        nodeEl.classList.toggle('search-matched', matched);
        nodeEl.classList.toggle('dimmed', !matched);
      }});

      document.querySelectorAll('.edge').forEach(edgeEl => {{
        if (!q) {{
          edgeEl.classList.remove('dimmed');
          return;
        }}
        const eObj = edgeById[edgeEl.dataset.edge];
        if (!eObj) return;
        const sMatch = document.querySelector(`.node[data-node="${{eObj.from}}"]`)?.classList.contains('search-matched');
        const tMatch = document.querySelector(`.node[data-node="${{eObj.to}}"]`)?.classList.contains('search-matched');
        edgeEl.classList.toggle('dimmed', !(sMatch && tMatch));
      }});
    }});
  }}

  // --- Node Selection & Focus ---
  window.selectAtlasNode = (nodeId) => {{
    const node = nodeById[nodeId];
    if (!node || !detailTitle || !detail) return;

    detailTitle.textContent = node.label;
    const typeLabel = TYPE_NAMES[node.type] || node.type;
    const loc = node.properties?.location || node.properties?.source_id || '';
    const text = node.properties?.text || node.label || '';
    const statusNote = node.review_status === 'needs_review' ? '\nTrạng thái: Cần xem lại (chưa được xác minh)' : '';

    detail.innerHTML = `
      <div style="font-size:11px; font-weight:700; color:#38bdf8; margin-bottom:6px;">${{typeLabel}}</div>
      ${{loc ? `<div style="font-size:11px; color:#a78bfa; margin-bottom:8px; word-break:break-all;">📁 ${{loc}}</div>` : ''}}
      <div style="font-size:12px; line-height:1.6; color:#e2e8f0; white-space:pre-wrap; word-break:break-word;">${{text}}${{statusNote}}</div>
      <button type="button" class="atlas-copy-btn" onclick="navigator.clipboard.writeText(this.dataset.snippet); this.textContent='Đã sao chép!'; setTimeout(() => this.textContent='Sao chép', 2000);" data-snippet="${{encodeURIComponent(text)}}">
        📋 Sao chép
      </button>
    `;
    const btn = detail.querySelector('.atlas-copy-btn');
    if (btn) btn.dataset.snippet = text;

    // Update Confidence Gauge
    if (confBox && confPct && confFill) {{
      const rawScore = node.properties?.score || node.properties?.confidence || (node.review_status === 'needs_review' ? 0.45 : null);
      if (rawScore !== undefined && rawScore !== null) {{
        const pct = Math.round(Number(rawScore) * 100);
        confPct.textContent = pct + '%';
        confFill.style.width = pct + '%';
        confFill.style.backgroundColor = pct >= 80 ? 'var(--success)' : (pct >= 50 ? 'var(--warning)' : 'var(--danger)');
        confBox.style.display = 'block';
      }} else {{
        confBox.style.display = 'none';
      }}
    }}

    // Update Inbound & Outbound Connections
    if (linksBox && inChips && outChips && inCount && outCount) {{
      const inboundEdges = DATA.edges.filter(e => e.to === nodeId);
      const outboundEdges = DATA.edges.filter(e => e.from === nodeId);

      inCount.textContent = inboundEdges.length;
      inChips.innerHTML = inboundEdges.map(e => {{
        const src = nodeById[e.from];
        const srcLabel = src?.label || e.from;
        return `<div class="atlas-link-chip" onclick="selectAtlasNode('${{e.from}}')">${{srcLabel}}</div>`;
      }}).join('') || '<span style="font-size:11px; color:#64748b;">(Không có)</span>';

      outCount.textContent = outboundEdges.length;
      outChips.innerHTML = outboundEdges.map(e => {{
        const tgt = nodeById[e.to];
        const tgtLabel = tgt?.label || e.to;
        return `<div class="atlas-link-chip" onclick="selectAtlasNode('${{e.to}}')">${{tgtLabel}}</div>`;
      }}).join('') || '<span style="font-size:11px; color:#64748b;">(Không có)</span>';

      linksBox.style.display = (inboundEdges.length > 0 || outboundEdges.length > 0) ? 'block' : 'none';
    }}

    // Visual active & highlight states
    const connectedEdges = new Set();
    const connectedNodeIds = new Set([nodeId]);

    DATA.edges.forEach(edge => {{
      if (edge.from === nodeId || edge.to === nodeId) {{
        connectedEdges.add(edge.id);
        connectedNodeIds.add(edge.from);
        connectedNodeIds.add(edge.to);
      }}
    }});

    document.querySelectorAll('.node').forEach(el => {{
      const isSelf = el.dataset.node === nodeId;
      el.classList.toggle('active', isSelf);
      el.classList.toggle('dimmed', !connectedNodeIds.has(el.dataset.node));
    }});

    document.querySelectorAll('.edge').forEach(el => {{
      const isConnected = connectedEdges.has(el.dataset.edge);
      el.classList.toggle('active', isConnected);
      el.classList.toggle('dimmed', !isConnected);
    }});
  }};

  const setView = (view) => {{
    document.body.dataset.view = view;
    document.querySelectorAll('button[data-view]').forEach(button => {{
      button.classList.toggle('active', button.dataset.view === view);
    }});
    if (status) status.textContent = view === 'full'
      ? 'Đang xem: Toàn bộ knowledge graph'
      : 'Đang xem: Câu trả lời & nguồn';
  }};

  document.querySelectorAll('button[data-view]').forEach(button => {{
    button.addEventListener('click', () => setView(button.dataset.view));
  }});

  document.querySelectorAll('[data-node]').forEach(element => {{
    element.addEventListener('click', () => window.selectAtlasNode(element.dataset.node));
  }});

  document.querySelectorAll('[data-edge]').forEach(element => {{
    element.addEventListener('click', () => {{
      const edge = edgeById[element.dataset.edge];
      if (!edge || !detailTitle || !detail) return;
      const relName = edge.relation.replaceAll('_', ' ');
      detailTitle.textContent = relName;
      const source = nodeById[edge.from]?.label || edge.from;
      const target = nodeById[edge.to]?.label || edge.to;
      const locations = (edge.receipts || []).map(item => item.location).filter(Boolean).join(', ');
      detail.innerHTML = `
        <div style="font-size:12px; color:#38bdf8; font-weight:700; margin-bottom:6px;">Quan hệ liên kết</div>
        <div style="font-size:12.5px; color:#f8fafc; line-height:1.5;"><strong>${{source}}</strong><br>───▶ <strong>${{target}}</strong></div>
        ${{locations ? `<div style="font-size:11px; color:#a78bfa; margin-top:8px;">Vị trí: ${{locations}}</div>` : ''}}
      `;
      if (confBox) confBox.style.display = 'none';
      if (linksBox) linksBox.style.display = 'none';
    }});
  }});
}})();
</script></body></html>"""
