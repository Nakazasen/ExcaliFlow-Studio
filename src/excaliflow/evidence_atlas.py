"""Offline, answer-centric Flowsint 2.0 Evidence Atlas renderer for a validated Evidence Graph."""

from __future__ import annotations

from collections import defaultdict
import html
import json
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from excaliflow.knowledge import REVIEW_STATUSES, validate_evidence_graph


_ATLAS_I18N: Dict[str, Dict[str, Any]] = {
    "vi": {
        "eyebrow": "Nguồn bằng chứng · local file",
        "lede": "Bản đồ này hiển thị quan hệ có nguồn; đường nét đứt và nhãn “Cần xem lại” là nhận định chưa được xác minh.",
        "view_answer": "Câu trả lời & nguồn",
        "view_full": "Toàn bộ knowledge graph",
        "status_prefix": "Đang xem: ",
        "search_placeholder": "Tìm kiếm thực thể...",
        "canvas_aria": "Đồ thị bằng chứng",
        "toggle_layout": "Chuyển đổi giao diện Thiên hà / Phân tầng",
        "zoom_in": "Phóng to",
        "zoom_out": "Thu nhỏ",
        "zoom_fit": "Vừa khung hình",
        "fullscreen": "Toàn màn hình",
        "collapse_panel": "Thu gọn bảng",
        "expand_panel": "Mở rộng bảng",
        "switch_hier": "Chuyển sang giao diện Phân tầng chuẩn",
        "switch_galaxy": "Chuyển sang giao diện Thiên hà động lực",
        "inspector_eyebrow": "Nguồn bằng chứng",
        "start_title": "Bắt đầu từ câu trả lời",
        "radar_title": "🛰️ Vệ tinh lân cận",
        "neighbor_suffix": " lân cận",
        "conf_title": "Độ tin cậy trích xuất",
        "inbound_title": "📥 Được dẫn chứng từ",
        "outbound_title": "📤 Dẫn chứng cho",
        "empty_rel": "(Không có)",
        "start_hint": "Chọn câu trả lời, đoạn tài liệu, nhận định hoặc đường nối để xem nguồn, vị trí và độ tin cậy.",
        "review_needed": "Cần xem lại",
        "needs_review_note": "\nTrạng thái: Cần xem lại (chưa được xác minh)",
        "copy_btn": "📋 Sao chép",
        "copied_btn": "Đã sao chép!",
        "open_portal": "📂 Mở trong Portal",
        "opened_portal": "Đã gửi yêu cầu mở file!",
        "edge_title": "Quan hệ liên kết",
        "edge_loc_prefix": "Vị trí: ",
        "filter_all": "Tất cả",
        "clear_selection": "Bỏ chọn (Esc)",
        "export_svg": "Xuất file SVG",
        "edge_confidence": "Độ tin cậy liên kết",
        "edge_origin": "Nguồn trích xuất",
        "edge_status_verified": "Đã xác minh",
        "edge_status_review": "Cần xem lại",
        "type_labels": {
            "answer": "Câu trả lời",
            "document": "Tài liệu nguồn",
            "chunk": "Đoạn bằng chứng",
            "entity": "Khái niệm",
            "claim": "Nhận định",
            "code": "Mã nguồn",
            "case": "Case",
        },
        "rel_labels": {
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
            "defined_in": "định nghĩa trong",
            "references": "tham chiếu",
            "implements": "triển khai",
        },
    },
    "ja": {
        "eyebrow": "エビデンスアトラス · ローカル解析",
        "lede": "根拠付きの知識関係を表示します。破線および「要確認」ラベルは未検証の推定ノードです。",
        "view_answer": "回答・根拠パス",
        "view_full": "全ナレッジグラフ",
        "status_prefix": "表示中: ",
        "search_placeholder": "ノード・記号を検索...",
        "canvas_aria": "エビデンスグラフ",
        "toggle_layout": "ギャラクシー / 階層レイアウト切替",
        "zoom_in": "拡大",
        "zoom_out": "縮小",
        "zoom_fit": "画面に合わせる",
        "fullscreen": "全画面表示",
        "collapse_panel": "パネルを折りたたむ",
        "expand_panel": "パネルを開く",
        "switch_hier": "階層レイアウトへ切替",
        "switch_galaxy": "力学ギャラクシーへ切替",
        "inspector_eyebrow": "エビデンス詳細",
        "start_title": "ノードを選択してください",
        "radar_title": "🛰️ 近傍ノード",
        "neighbor_suffix": " 件",
        "conf_title": "抽出信頼度",
        "inbound_title": "📥 参照元",
        "outbound_title": "📤 参照先",
        "empty_rel": "(なし)",
        "start_hint": "ノードまたはエッジをクリックすると、参照元ファイル・信頼度・近傍関係が表示されます。",
        "review_needed": "要確認",
        "needs_review_note": "\n状態: 要確認（未検証）",
        "copy_btn": "📋 コピー",
        "copied_btn": "コピー済み！",
        "open_portal": "📂 ポータルで開く",
        "opened_portal": "開く要求を送信しました！",
        "edge_title": "関連リンク",
        "edge_loc_prefix": "参照元: ",
        "filter_all": "すべて",
        "clear_selection": "選択解除 (Esc)",
        "export_svg": "SVGを書き出す",
        "edge_confidence": "リンク信頼度",
        "edge_origin": "抽出元",
        "edge_status_verified": "検証済み",
        "edge_status_review": "要確認",
        "type_labels": {
            "answer": "回答要約",
            "document": "ソース資料",
            "chunk": "根拠抜粋",
            "entity": "概念・識別子",
            "claim": "抽出クレーム",
            "code": "ソースコード",
            "case": "ケース",
        },
        "rel_labels": {
            "supports": "裏付け",
            "supported by": "根拠引用",
            "supported_by": "根拠引用",
            "cites": "引用元",
            "extracted_from": "抽出元",
            "extracted from": "抽出元",
            "derived_from": "派生元",
            "derived from": "派生元",
            "mentions": "言及",
            "contains": "包含",
            "depends_on": "依存",
            "implemented_by": "実装先",
            "defined_in": "定義元",
            "references": "相互参照",
            "implements": "実装",
        },
    },
    "en": {
        "eyebrow": "Evidence Atlas · local workspace",
        "lede": "Displays source-backed knowledge relations; dashed outlines indicate needs-review claims.",
        "view_answer": "Answer & Citations",
        "view_full": "Full Knowledge Graph",
        "status_prefix": "Viewing: ",
        "search_placeholder": "Search nodes...",
        "canvas_aria": "Evidence Graph",
        "toggle_layout": "Toggle Galaxy / Hierarchical",
        "zoom_in": "Zoom in",
        "zoom_out": "Zoom out",
        "zoom_fit": "Fit view",
        "fullscreen": "Fullscreen",
        "collapse_panel": "Collapse inspector",
        "expand_panel": "Expand inspector",
        "switch_hier": "Switch to hierarchical layout",
        "switch_galaxy": "Switch to force-directed galaxy",
        "inspector_eyebrow": "Evidence Inspector",
        "start_title": "Select a node to inspect",
        "radar_title": "🛰️ Local Neighborhood",
        "neighbor_suffix": " neighbors",
        "conf_title": "Extraction Confidence",
        "inbound_title": "📥 Referenced by",
        "outbound_title": "📤 References",
        "empty_rel": "(None)",
        "start_hint": "Click a node or edge to inspect source receipts, file location, and confidence.",
        "review_needed": "Needs review",
        "needs_review_note": "\nStatus: Needs review (unverified)",
        "copy_btn": "📋 Copy",
        "copied_btn": "Copied!",
        "open_portal": "📂 Open in Portal",
        "opened_portal": "Sent open request!",
        "edge_title": "Relation Link",
        "edge_loc_prefix": "Location: ",
        "filter_all": "All",
        "clear_selection": "Clear selection (Esc)",
        "export_svg": "Export SVG",
        "edge_confidence": "Edge Confidence",
        "edge_origin": "Origin",
        "edge_status_verified": "Verified",
        "edge_status_review": "Needs review",
        "type_labels": {
            "answer": "Answer",
            "document": "Document",
            "chunk": "Evidence Chunk",
            "entity": "Entity",
            "claim": "Claim",
            "code": "Source Code",
            "case": "Case",
        },
        "rel_labels": {
            "supports": "supports",
            "supported by": "supported by",
            "supported_by": "supported by",
            "cites": "cites",
            "extracted_from": "extracted from",
            "extracted from": "extracted from",
            "derived_from": "derived from",
            "derived from": "derived from",
            "mentions": "mentions",
            "contains": "contains",
            "depends_on": "depends on",
            "implemented_by": "implemented by",
            "defined_in": "defined in",
            "references": "references",
            "implements": "implements",
        },
    },
}

TYPE_LABELS = _ATLAS_I18N["vi"]["type_labels"]

TYPE_COLORS = {
    "answer": "#ff7a45",
    "document": "#5d83d6",
    "chunk": "#4ba980",
    "entity": "#a46cdb",
    "claim": "#d49a29",
    "code": "#2c8498",
    "case": "#ce5c70",
}


def _relation_label(relation: Any, lang: str = "vi") -> str:
    tr = _ATLAS_I18N.get(lang, _ATLAS_I18N["vi"])
    labels = tr["rel_labels"]
    raw = str(relation or "link").strip().lower().replace("-", " ")
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


def _node_svg(node: dict, position: tuple[int, int], is_focused: bool, lang: str = "vi") -> str:
    """Render one evidence node with pill shape and clean multi-line label."""
    tr = _ATLAS_I18N.get(lang, _ATLAS_I18N["vi"])
    x, y = position
    classes = "node"
    if is_focused:
        classes += " focus"
    if node.get("review_status") == "needs_review":
        classes += " needs-review"
        review_label = f'<text class="review-label" x="{x + 14}" y="{y + 72}">{html.escape(tr["review_needed"])}</text>'
    else:
        review_label = ""

    lines = _label_lines(node.get("label", ""))
    tspans = "".join(
        f'<tspan x="{x + 14}" dy="{0 if i == 0 else 17}">{html.escape(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    node_type_label = tr["type_labels"].get(node.get("type", ""), node.get("type", "").upper())

    return (
        f'<g class="{classes}" data-node="{html.escape(str(node["id"]))}" tabindex="0" role="button">'
        f'<rect x="{x}" y="{y}" width="260" height="84" rx="14" '
        f'style="--node-color:{TYPE_COLORS.get(node["type"], "#38bdf8")}"/>'
        f'<text class="node-type" x="{x + 14}" y="{y + 24}">{html.escape(node_type_label)}</text>'
        f'<text class="node-label" x="{x + 14}" y="{y + 46}">{tspans}</text>'
        f'{review_label}</g>'
    )


def build_evidence_atlas_html(graph: dict, lang: str = "vi") -> str:
    """Create one standalone Flowsint 2.0 HTML document from a validated evidence graph."""
    validate_evidence_graph(graph)
    norm_lang = lang if lang in _ATLAS_I18N else "vi"
    tr = _ATLAS_I18N[norm_lang]
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

        rel_text = html.escape(_relation_label(edge.get("relation", ""), norm_lang))
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
                f'<g class="edge-label" data-from="{html.escape(str(edge["from"]))}" data-to="{html.escape(str(edge["to"]))}">'
                f'<rect x="{bx1}" y="{by1}" width="{w_lbl}" height="{h_lbl}" rx="9999"/>'
                f'<text x="{cand_x}" y="{cand_y_pt + 3}" text-anchor="middle">{rel_text}</text></g>'
            )

    node_svg = "".join(
        _node_svg(node, positions[node["id"]], node["id"] in focus_ids, norm_lang)
        for node in graph["nodes"]
    )
    payload = json.dumps(graph, ensure_ascii=False).replace("</", "<\\/")
    tr_json = json.dumps(tr, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape(graph.get("title", "Evidence Graph"))

    return f"""<!doctype html>
<html lang="{norm_lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidence Atlas — {title}</title>
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
.type-filters {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
  align-items: center;
}}
.type-filter-pill {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #334155;
  background: #0f172a;
  color: #cbd5e1;
  border-radius: 9999px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
}}
.type-filter-pill:hover {{
  border-color: var(--accent);
  color: #fff;
}}
.type-filter-pill.active {{
  background: rgba(56, 189, 248, 0.16);
  border-color: var(--accent);
  color: #f8fafc;
}}
.type-dot {{
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}}
.node.type-hidden, .edge.type-hidden, .edge-label.type-hidden {{
  display: none !important;
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
.atlas-tool-btn.active-mode {{
  background: rgba(56, 189, 248, 0.2);
  border-color: var(--accent);
  color: var(--accent);
  box-shadow: 0 0 8px rgba(56, 189, 248, 0.4);
}}
.layout.galaxy-mode .edge-label {{
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
}}
.micro-dots .node text, .micro-dots .edge-label {{
  display: none;
}}
.micro-dots .node rect {{
  rx: 9999px;
  transform: scale(0.35);
  transform-origin: center;
}}
.mini-radar-card {{
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 10px 12px;
  margin: 10px 0;
  overflow: hidden;
  box-sizing: border-box;
}}
.mini-radar-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  margin-bottom: 6px;
}}
.mini-radar-count {{
  color: var(--accent);
  font-weight: 800;
}}
.mini-radar-canvas-wrap {{
  display: flex;
  justify-content: center;
  align-items: center;
  background: #0f172a;
  border-radius: 6px;
  padding: 4px 0;
  border: 1px solid rgba(255, 255, 255, 0.05);
  overflow: hidden;
  max-width: 100%;
  box-sizing: border-box;
}}
.radar-orbit {{
  fill: none;
  stroke: #334155;
  stroke-width: 1;
  stroke-dasharray: 2 3;
}}
.radar-orbit.inner {{
  stroke: #1e293b;
}}
.radar-ray {{
  stroke: rgba(56, 189, 248, 0.35);
  stroke-width: 1;
  stroke-dasharray: 2 2;
}}
.radar-dot {{
  stroke: #0f172a;
  stroke-width: 1.5;
  transition: all 0.2s ease;
  cursor: pointer;
}}
.radar-dot-group:hover .radar-dot {{
  r: 8;
  filter: drop-shadow(0 0 6px var(--accent));
}}
.radar-center {{
  fill: var(--accent);
  stroke: #0f172a;
  stroke-width: 2;
  filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.8));
}}
.canvas svg {{
  display: block;
  min-width: {width}px;
  transform-origin: 0 0;
  transition: transform 0.05s ease-out;
}}
#atlas-mini-radar-svg {{
  min-width: 0 !important;
  width: 160px !important;
  max-width: 160px !important;
  height: 140px !important;
  display: block;
  margin: 0 auto;
  transform: none !important;
}}

/* Celestial Concentric Orbits Backdrop */
.galaxy-orbit-backdrop {{
  display: none;
  pointer-events: none;
}}
.layout.galaxy-mode .galaxy-orbit-backdrop {{
  display: block;
}}
.celestial-orbit {{
  fill: none;
  stroke-width: 1.2;
}}
.celestial-orbit.orbit-core {{
  stroke: rgba(56, 189, 248, 0.22);
  stroke-dasharray: 4 6;
}}
.celestial-orbit.orbit-mid {{
  stroke: rgba(75, 169, 128, 0.22);
  stroke-dasharray: 4 6;
}}
.celestial-orbit.orbit-outer {{
  stroke: rgba(93, 131, 214, 0.22);
  stroke-dasharray: 6 8;
}}
.celestial-axis {{
  stroke: rgba(148, 163, 184, 0.08);
  stroke-width: 1;
  stroke-dasharray: 3 5;
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
.atlas-open-btn {{
  background: rgba(56, 189, 248, 0.16);
  color: #7dd3fc;
  border-color: rgba(56, 189, 248, 0.45);
  margin-left: 6px;
}}
.atlas-open-btn:hover {{
  background: rgba(56, 189, 248, 0.28);
  color: #fff;
}}
.atlas-zoom-badge {{
  display: inline-flex;
  align-items: center;
  padding: 0 7px;
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
}}
@media (max-width: 850px) {{
  .layout {{ display: block; }}
  aside {{ position: static; max-height: none; margin-top: 16px; }}
  h1 {{ font-size: 18px; }}
}}
</style></head><body data-view="answer"><header><div class="eyebrow">{html.escape(tr["eyebrow"])}</div><h1>Evidence Atlas</h1><p class="lede">{title}. {html.escape(tr["lede"])}</p></header><main><div class="toolbar"><button data-view="answer" class="active">{html.escape(tr["view_answer"])}</button><button data-view="full">{html.escape(tr["view_full"])}</button><span id="atlas-view-status" class="legend" aria-live="polite">{html.escape(tr["status_prefix"] + tr["view_answer"])}</span><div class="atlas-search-box"><span class="atlas-search-icon">🔍</span><input type="text" id="atlas-search-input" placeholder="{html.escape(tr["search_placeholder"])}" class="atlas-search-input" /></div></div><div id="atlas-type-filters" class="type-filters" role="group" aria-label="Filter by node type"></div><div class="layout"><section class="canvas" aria-label="{html.escape(tr["canvas_aria"])}"><div class="atlas-floating-toolbar" role="toolbar" aria-label="Canvas controls"><button type="button" id="atlas-btn-toggle-layout" class="atlas-tool-btn active-mode" title="{html.escape(tr["toggle_layout"])}">🌌</button><button type="button" id="atlas-btn-zoom-in" class="atlas-tool-btn" title="{html.escape(tr["zoom_in"])}">＋</button><button type="button" id="atlas-btn-zoom-out" class="atlas-tool-btn" title="{html.escape(tr["zoom_out"])}">－</button><span id="atlas-zoom-badge" class="atlas-zoom-badge">100%</span><button type="button" id="atlas-btn-fit" class="atlas-tool-btn" title="{html.escape(tr["zoom_fit"])}">⊡</button><button type="button" id="atlas-btn-reset-selection" class="atlas-tool-btn" title="{html.escape(tr["clear_selection"])}">↺</button><button type="button" id="atlas-btn-export-svg" class="atlas-tool-btn" title="{html.escape(tr["export_svg"])}">⬇</button><button type="button" id="atlas-btn-fullscreen" class="atlas-tool-btn" title="{html.escape(tr["fullscreen"])}">⛶</button></div><svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Evidence graph for {title}"><defs><marker id="atlas-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6" fill="none" stroke="#38bdf8" stroke-width="1.3"/></marker></defs><g class="galaxy-orbit-backdrop" id="galaxy-backdrop"><circle cx="{width // 2}" cy="{height // 2}" r="75" class="celestial-orbit orbit-core" /><circle cx="{width // 2}" cy="{height // 2}" r="210" class="celestial-orbit orbit-mid" /><circle cx="{width // 2}" cy="{height // 2}" r="380" class="celestial-orbit orbit-outer" /><line x1="{width // 2 - 420}" y1="{height // 2}" x2="{width // 2 + 420}" y2="{height // 2}" class="celestial-axis" /><line x1="{width // 2}" y1="{height // 2 - 420}" x2="{width // 2}" y2="{height // 2 + 420}" class="celestial-axis" /></g>{''.join(edge_svg_paths)}{''.join(node_svg)}{''.join(edge_label_svgs)}</svg></section><aside><button type="button" id="atlas-toggle-inspector" class="atlas-collapse-btn" title="{html.escape(tr["collapse_panel"])}">›</button><div class="eyebrow">{html.escape(tr["inspector_eyebrow"])}</div><h2 id="detail-title">{html.escape(tr["start_title"])}</h2><div id="atlas-mini-radar-container" class="mini-radar-card" style="display:none;"><div class="mini-radar-header"><span>{html.escape(tr["radar_title"])}</span><span id="atlas-mini-radar-count" class="mini-radar-count">0{html.escape(tr["neighbor_suffix"])}</span></div><div class="mini-radar-canvas-wrap"><svg id="atlas-mini-radar-svg" viewBox="-80 -80 160 160" width="100%" height="150"><circle cx="0" cy="0" r="58" class="radar-orbit" /><circle cx="0" cy="0" r="32" class="radar-orbit inner" /><g id="atlas-radar-rays"></g><g id="atlas-radar-neighbors"></g><circle id="atlas-radar-center-node" cx="0" cy="0" r="9" class="radar-center" /></svg></div></div><div id="atlas-confidence-box" class="confidence-gauge-card" style="display:none;"><div class="gauge-header"><span class="gauge-title">{html.escape(tr["conf_title"])}</span><span id="atlas-conf-pct" class="gauge-pct">--%</span></div><div class="gauge-track"><div id="atlas-conf-fill" class="gauge-fill" style="width:0%;"></div></div></div><div id="atlas-links-box" class="atlas-links-card" style="display:none;"><div id="atlas-inbound-section" style="margin-bottom:10px;"><div class="links-title">{html.escape(tr["inbound_title"])} (<span id="atlas-in-count">0</span>)</div><div id="atlas-in-chips" class="links-chips-wrap"></div></div><div id="atlas-outbound-section"><div class="links-title">{html.escape(tr["outbound_title"])} (<span id="atlas-out-count">0</span>)</div><div id="atlas-out-chips" class="links-chips-wrap"></div></div></div><div id="detail" class="receipt">{html.escape(tr["start_hint"])}</div></aside></div></main><script>
(() => {{
  const DATA = {payload};
  const TR = {tr_json};
  const POSITIONS = {json.dumps(positions)};
  const SVG_WIDTH = {width};
  const SVG_HEIGHT = {height};
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
  const zoomBadge = document.getElementById('atlas-zoom-badge');
  const layout = document.querySelector('.layout');
  const toggleInspectorBtn = document.getElementById('atlas-toggle-inspector');
  const searchInput = document.getElementById('atlas-search-input');
  const toggleLayoutBtn = document.getElementById('atlas-btn-toggle-layout');

  const TYPE_NAMES = TR.type_labels || {{}};
  const nodeElemById = Object.create(null);
  document.querySelectorAll('.node').forEach(el => {{
    if (el.dataset.node) nodeElemById[el.dataset.node] = el;
  }});
  const edgeElemById = Object.create(null);
  document.querySelectorAll('.edge').forEach(el => {{
    if (el.dataset.edge) edgeElemById[el.dataset.edge] = el;
  }});
  let activeTypeFilter = 'all';
  let selectedNodeId = null;
  let selectedEdgeId = null;

  function escapeHtml(val) {{
    return String(val ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
  }}

  function openAtlasLocation(locationStr, nodeId, label) {{
    if (!locationStr) return false;
    if (window.parent && window.parent !== window) {{
      window.parent.postMessage({{ type: 'excaliflow:open-location', location: locationStr, nodeId: nodeId || '', label: label || '' }}, '*');
      return true;
    }}
    return false;
  }}

  const TYPE_COLORS = {{
    'answer': '#ff7a45',
    'document': '#5d83d6',
    'chunk': '#4ba980',
    'entity': '#a46cdb',
    'claim': '#d49a29',
    'code': '#2c8498',
    'case': '#ce5c70'
  }};

  const radarRaysGroup = document.getElementById('atlas-radar-rays');
  const radarNeighborsGroup = document.getElementById('atlas-radar-neighbors');
  if (radarNeighborsGroup) {{
    radarNeighborsGroup.addEventListener('click', (e) => {{
      const target = e.target.closest('[data-target-node]');
      if (target && target.dataset.targetNode) {{
        window.selectAtlasNode(target.dataset.targetNode);
      }}
    }});
  }}
  if (inChips) {{
    inChips.addEventListener('click', (e) => {{
      const chip = e.target.closest('[data-target-node]');
      if (chip && chip.dataset.targetNode) {{
        window.selectAtlasNode(chip.dataset.targetNode);
      }}
    }});
  }}
  if (outChips) {{
    outChips.addEventListener('click', (e) => {{
      const chip = e.target.closest('[data-target-node]');
      if (chip && chip.dataset.targetNode) {{
        window.selectAtlasNode(chip.dataset.targetNode);
      }}
    }});
  }}

  function updateAtlasMiniRadar(nodeId) {{
    const radarContainer = document.getElementById('atlas-mini-radar-container');
    if (!radarContainer) return;

    const inEdges = DATA.edges.filter(e => e.to === nodeId);
    const outEdges = DATA.edges.filter(e => e.from === nodeId);
    const neighborIds = [...new Set([...inEdges.map(e => e.from), ...outEdges.map(e => e.to)])].filter(id => id !== nodeId);

    const countSpan = document.getElementById('atlas-mini-radar-count');
    if (countSpan) {{
      countSpan.textContent = neighborIds.length + (TR.neighbor_suffix || ' lân cận');
    }}

    if (neighborIds.length === 0) {{
      radarContainer.style.display = 'none';
      return;
    }}
    radarContainer.style.display = 'block';

    const centerNode = document.getElementById('atlas-radar-center-node');
    if (!radarRaysGroup || !radarNeighborsGroup) return;

    const currNode = nodeById[nodeId];
    if (centerNode && currNode) {{
      centerNode.setAttribute('fill', TYPE_COLORS[currNode.type] || '#38bdf8');
    }}

    radarRaysGroup.innerHTML = '';
    radarNeighborsGroup.innerHTML = '';

    const R = 58;
    const n = neighborIds.length;
    let raysHtml = '';
    let dotsHtml = '';
    neighborIds.forEach((nbId, idx) => {{
      const angle = (2 * Math.PI * idx / n) - Math.PI / 2;
      const nx = Math.cos(angle) * R;
      const ny = Math.sin(angle) * R;
      const nbObj = nodeById[nbId] || {{}};
      const ntype = nbObj.type || 'chunk';
      const nbLabel = escapeHtml(nbObj.label || nbId);
      const color = TYPE_COLORS[ntype] || '#38bdf8';

      raysHtml += `<line x1="0" y1="0" x2="${{nx.toFixed(1)}}" y2="${{ny.toFixed(1)}}" class="radar-ray" />`;
      dotsHtml += `<g class="radar-dot-group" cursor="pointer" data-target-node="${{escapeHtml(nbId)}}">` +
                  `<circle cx="${{nx.toFixed(1)}}" cy="${{ny.toFixed(1)}}" r="5.5" fill="${{color}}" class="radar-dot"><title>${{nbLabel}}</title></circle></g>`;
    }});
    radarRaysGroup.innerHTML = raysHtml;
    radarNeighborsGroup.innerHTML = dotsHtml;
  }}

  // --- Force-Directed Galaxy Simulation Engine ---
  const cx = SVG_WIDTH / 2;
  const cy = SVG_HEIGHT / 2;
  let currentLayout = 'galaxy';
  let simNodes = [];
  let simEdges = [];
  let simRunning = true;
  let animFrameId = null;
  let alpha = 1.0;
  let draggedNode = null;
  let dragStartX = 0;
  let dragStartY = 0;
  let nodeStartX = 0;
  let nodeStartY = 0;

  function physicsTick() {{
    if (currentLayout !== 'galaxy') return;

    // Repulsion
    const kRepel = 4500;
    for (let i = 0; i < simNodes.length; i++) {{
      const n1 = simNodes[i];
      for (let j = i + 1; j < simNodes.length; j++) {{
        const n2 = simNodes[j];
        let dx = n1.x - n2.x;
        let dy = n1.y - n2.y;
        let d2 = dx * dx + dy * dy + 1;
        let d = Math.sqrt(d2);
        if (d < 700) {{
          let force = (kRepel / (d2 + 100)) * alpha;
          let fx = (dx / d) * force;
          let fy = (dy / d) * force;
          if (n1 !== draggedNode) {{ n1.vx += fx / n1.mass; n1.vy += fy / n1.mass; }}
          if (n2 !== draggedNode) {{ n2.vx -= fx / n2.mass; n2.vy -= fy / n2.mass; }}
        }}
      }}
    }}

    // Springs between connected nodes
    const kSpring = 0.035;
    for (let e of simEdges) {{
      let dx = e.target.x - e.source.x;
      let dy = e.target.y - e.source.y;
      let d = Math.sqrt(dx * dx + dy * dy) || 1;
      let targetDist = 160;
      if (e.source.isHub || e.target.isHub) {{
        targetDist = 180;
      }} else if (e.source.isDoc || e.target.isDoc) {{
        targetDist = 200;
      }}
      let force = (d - targetDist) * kSpring * alpha;
      let fx = (dx / d) * force;
      let fy = (dy / d) * force;
      if (e.source !== draggedNode) {{ e.source.vx += fx / e.source.mass; e.source.vy += fy / e.source.mass; }}
      if (e.target !== draggedNode) {{ e.target.vx -= fx / e.target.mass; e.target.vy -= fy / e.target.mass; }}
    }}

    // Center gravity & Orbital concentric bias
    const kGravity = 0.012;
    const kOrbit = 0.008;
    for (let n of simNodes) {{
      if (n === draggedNode) continue;
      let dxC = n.x - cx;
      let dyC = n.y - cy;
      let distC = Math.sqrt(dxC * dxC + dyC * dyC) || 1;
      let rDelta = distC - n.idealRadius;
      n.vx -= (dxC / distC) * rDelta * kOrbit * alpha;
      n.vy -= (dyC / distC) * rDelta * kOrbit * alpha;

      n.vx += (cx - n.x) * kGravity * alpha;
      n.vy += (cy - n.y) * kGravity * alpha;
      n.vx *= 0.88;
      n.vy *= 0.88;
      n.x += n.vx;
      n.y += n.vy;
    }}

    // AABB Box Collision Resolution (Strict no-overlap)
    const pad = 12;
    for (let i = 0; i < simNodes.length; i++) {{
      const n1 = simNodes[i];
      const halfW1 = (n1.width / 2) + pad;
      const halfH1 = (n1.height / 2) + pad;
      for (let j = i + 1; j < simNodes.length; j++) {{
        const n2 = simNodes[j];
        const halfW2 = (n2.width / 2) + pad;
        const halfH2 = (n2.height / 2) + pad;

        let dx = n1.x - n2.x;
        let dy = n1.y - n2.y;
        let minX = halfW1 + halfW2;
        let minY = halfH1 + halfH2;

        let overlapX = minX - Math.abs(dx);
        let overlapY = minY - Math.abs(dy);

        if (overlapX > 0 && overlapY > 0) {{
          if (overlapX < overlapY) {{
            let signX = dx >= 0 ? 1 : -1;
            let pushX = overlapX * 0.5;
            if (n1 !== draggedNode) n1.x += pushX * signX;
            if (n2 !== draggedNode) n2.x -= pushX * signX;
            n1.vx *= 0.5;
            n2.vx *= 0.5;
          }} else {{
            let signY = dy >= 0 ? 1 : -1;
            let pushY = overlapY * 0.5;
            if (n1 !== draggedNode) n1.y += pushY * signY;
            if (n2 !== draggedNode) n2.y -= pushY * signY;
            n1.vy *= 0.5;
            n2.vy *= 0.5;
          }}
        }}
      }}
    }}

    // Update node positions
    for (let n of simNodes) {{
      if (n.elem) {{
        const dx = n.x - (n.baseX + 130);
        const dy = n.y - (n.baseY + 42);
        n.elem.setAttribute('transform', `translate(${{dx.toFixed(1)}}, ${{dy.toFixed(1)}})`);
      }}
    }}

    // Update edge positions
    for (let e of simEdges) {{
      if (e.elem) {{
        const x1 = e.source.x;
        const y1 = e.source.y;
        const x2 = e.target.x;
        const y2 = e.target.y;
        const dx = x2 - x1;
        const dy = y2 - y1;
        let cx1, cy1, cx2, cy2;
        if (Math.abs(dy) >= 10) {{
          cx1 = x1;
          cy1 = y1 + dy * 0.45;
          cx2 = x2;
          cy2 = y2 - dy * 0.45;
        }} else {{
          cx1 = x1 + dx * 0.45;
          cy1 = y1 - 25;
          cx2 = x2 - dx * 0.45;
          cy2 = y2 - 25;
        }}
        e.elem.setAttribute('d', `M ${{x1.toFixed(1)}},${{y1.toFixed(1)}} C ${{cx1.toFixed(1)}},${{cy1.toFixed(1)}} ${{cx2.toFixed(1)}},${{cy2.toFixed(1)}} ${{x2.toFixed(1)}},${{y2.toFixed(1)}}`);
      }}
    }}

    alpha *= 0.993;
    if (alpha > 0.005 || draggedNode) {{
      animFrameId = requestAnimationFrame(physicsTick);
    }} else {{
      simRunning = false;
    }}
  }}

  function resumeSimulation(boostAlpha = 0.35) {{
    if (currentLayout !== 'galaxy') return;
    alpha = Math.max(alpha, boostAlpha);
    if (!simRunning) {{
      simRunning = true;
      animFrameId = requestAnimationFrame(physicsTick);
    }}
  }}

  function initForceSimulation() {{
    if (animFrameId) cancelAnimationFrame(animFrameId);
    const hubs = DATA.nodes.filter(n => n.type === 'answer' || n.type === 'case');
    const citations = DATA.nodes.filter(n => n.type === 'chunk' || n.type === 'claim' || n.type === 'entity' || n.type === 'code');
    const docs = DATA.nodes.filter(n => n.type === 'document');

    let hubIdx = 0, citeIdx = 0, docIdx = 0;
    simNodes = DATA.nodes.map((n) => {{
      const isHub = (n.type === 'answer' || n.type === 'case');
      const isCite = (n.type === 'chunk' || n.type === 'claim' || n.type === 'entity' || n.type === 'code');
      const isDoc = (n.type === 'document');

      let dist = 210;
      let angle = 0;
      let idealRadius = 210;
      let mass = 1.0;
      let w = 220;
      let h = 70;

      if (isHub) {{
        mass = 5.0;
        idealRadius = 35;
        dist = 15 + (hubIdx * 25);
        angle = hubs.length > 1 ? (2 * Math.PI * hubIdx / hubs.length) - Math.PI / 2 : 0;
        w = 260;
        h = 84;
        hubIdx++;
      }} else if (isCite) {{
        mass = 1.2;
        idealRadius = 210;
        dist = 200 + (citeIdx % 3) * 15;
        angle = (2 * Math.PI * citeIdx / (citations.length || 1)) - Math.PI / 2 + 0.15;
        w = 180;
        h = 64;
        citeIdx++;
      }} else if (isDoc) {{
        mass = 2.8;
        idealRadius = 380;
        dist = 370 + (docIdx % 3) * 20;
        angle = (2 * Math.PI * docIdx / (docs.length || 1)) - Math.PI / 2 + 0.35;
        w = 240;
        h = 76;
        docIdx++;
      }}

      const basePos = POSITIONS[n.id] || [cx, cy];
      const baseX = Number(basePos[0]);
      const baseY = Number(basePos[1]);

      return {{
        id: n.id,
        baseX: baseX,
        baseY: baseY,
        width: w,
        height: h,
        x: cx + Math.cos(angle) * dist,
        y: cy + Math.sin(angle) * dist,
        vx: 0,
        vy: 0,
        isHub: isHub,
        isCite: isCite,
        isDoc: isDoc,
        idealRadius: idealRadius,
        mass: mass,
        elem: nodeElemById[n.id] || null
      }};
    }});

    const simById = Object.fromEntries(simNodes.map(sn => [sn.id, sn]));
    simEdges = DATA.edges.map(e => {{
      const edgeElem = edgeElemById[e.id] || null;
      return {{
        id: e.id,
        source: simById[e.from],
        target: simById[e.to],
        origD: edgeElem ? edgeElem.getAttribute('d') : '',
        elem: edgeElem
      }};
    }}).filter(e => e.source && e.target);

    alpha = 1.0;
    simRunning = true;
    animFrameId = requestAnimationFrame(physicsTick);
  }}

  function switchLayout(mode) {{
    currentLayout = mode;
    if (layout) {{
      layout.classList.toggle('galaxy-mode', mode === 'galaxy');
    }}
    if (toggleLayoutBtn) {{
      toggleLayoutBtn.classList.toggle('active-mode', mode === 'galaxy');
      toggleLayoutBtn.textContent = mode === 'galaxy' ? '🌌' : '📑';
      toggleLayoutBtn.title = mode === 'galaxy' ? TR.switch_hier : TR.switch_galaxy;
    }}

    if (mode === 'hierarchical') {{
      if (animFrameId) cancelAnimationFrame(animFrameId);
      simRunning = false;
      for (let n of simNodes) {{
        if (n.elem) n.elem.removeAttribute('transform');
      }}
      for (let e of simEdges) {{
        if (e.elem && e.origD) e.elem.setAttribute('d', e.origD);
      }}
    }} else {{
      initForceSimulation();
    }}
  }}

  if (toggleLayoutBtn) {{
    toggleLayoutBtn.addEventListener('click', () => {{
      switchLayout(currentLayout === 'galaxy' ? 'hierarchical' : 'galaxy');
    }});
  }}

  // --- Pan & Zoom Engine ---
  let scale = 1.0;
  let panX = 0;
  let panY = 0;
  let isPanning = false;
  let panMoved = false;
  let startX = 0;
  let startY = 0;

  const updateTransform = () => {{
    if (!svgElem) return;
    svgElem.style.transform = `translate(${{panX}}px, ${{panY}}px) scale(${{scale}})`;
    if (zoomBadge) {{
      zoomBadge.textContent = Math.round(scale * 100) + '%';
    }}
    if (scale < 0.55) {{
      svgElem.classList.add('micro-dots');
    }} else {{
      svgElem.classList.remove('micro-dots');
    }}
  }};

  function fitToView() {{
    if (!canvasSec || !svgElem) return;
    const activeView = document.body.dataset.view || 'answer';
    const simById = Object.fromEntries(simNodes.map(sn => [sn.id, sn]));
    const visibleCoords = [];
    DATA.nodes.forEach(node => {{
      const el = nodeElemById[node.id];
      if (!el || el.classList.contains('type-hidden')) return;
      if (activeView === 'answer' && !el.classList.contains('focus')) return;
      if (currentLayout === 'galaxy' && simById[node.id]) {{
        const sn = simById[node.id];
        visibleCoords.push([sn.x - 130, sn.y - 42, sn.x + 130, sn.y + 42]);
      }} else {{
        const pos = POSITIONS[node.id] || [0, 0];
        visibleCoords.push([pos[0], pos[1], pos[0] + 260, pos[1] + 84]);
      }}
    }});
    if (!visibleCoords.length) {{
      scale = 1.0;
      panX = 0;
      panY = 0;
      updateTransform();
      return;
    }}
    const minX = Math.min(...visibleCoords.map(b => b[0]));
    const minY = Math.min(...visibleCoords.map(b => b[1]));
    const maxX = Math.max(...visibleCoords.map(b => b[2]));
    const maxY = Math.max(...visibleCoords.map(b => b[3]));
    const boxW = Math.max(260, maxX - minX);
    const boxH = Math.max(120, maxY - minY);
    const viewW = Math.max(300, canvasSec.clientWidth || SVG_WIDTH);
    const viewH = Math.max(300, canvasSec.clientHeight || SVG_HEIGHT);
    const padding = 48;
    scale = Math.min(1.6, Math.max(0.3, Math.min((viewW - padding * 2) / boxW, (viewH - padding * 2) / boxH)));
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    panX = viewW / 2 - centerX * scale;
    panY = viewH / 2 - centerY * scale;
    updateTransform();
  }}

  function clearAtlasSelection() {{
    selectedNodeId = null;
    selectedEdgeId = null;
    Object.values(nodeElemById).forEach(el => el.classList.remove('active', 'dimmed'));
    Object.values(edgeElemById).forEach(el => el.classList.remove('active', 'dimmed'));
    const radarContainer = document.getElementById('atlas-mini-radar-container');
    if (radarContainer) radarContainer.style.display = 'none';
    if (confBox) confBox.style.display = 'none';
    if (linksBox) linksBox.style.display = 'none';
    if (detailTitle) detailTitle.textContent = TR.start_title;
    if (detail) detail.textContent = TR.start_hint;
    applyFiltersAndSearch();
  }}

  function exportCurrentSvg() {{
    if (!svgElem) return;
    const clone = svgElem.cloneNode(true);
    clone.removeAttribute('style');
    const styleEl = svgElem.ownerDocument.createElementNS(svgElem.namespaceURI, 'style');
    styleEl.textContent =
      '.node rect{{fill:#0f172a;stroke:var(--node-color,#38bdf8);stroke-width:1.8}}' +
      '.node.needs-review rect{{stroke-dasharray:6 3}}' +
      '.node-type{{font-size:11px;font-weight:800;fill:#94a3b8;font-family:sans-serif}}' +
      '.node-label{{font-size:13px;font-weight:600;fill:#f8fafc;font-family:sans-serif}}' +
      '.review-label{{font-size:11px;font-weight:800;fill:#f59e0b;font-family:sans-serif}}' +
      '.edge{{stroke:#475569;stroke-width:1.8;fill:none;opacity:0.75}}' +
      '.edge.focus{{stroke:#38bdf8;stroke-width:2.5;opacity:1}}' +
      '.edge-label rect{{fill:#0f172a;stroke:#334155;stroke-width:1}}' +
      '.edge-label text{{font-size:10px;fill:#94a3b8;font-family:sans-serif}}';
    const bgRect = svgElem.ownerDocument.createElementNS(svgElem.namespaceURI, 'rect');
    bgRect.setAttribute('x', '0');
    bgRect.setAttribute('y', '0');
    bgRect.setAttribute('width', String(SVG_WIDTH));
    bgRect.setAttribute('height', String(SVG_HEIGHT));
    bgRect.setAttribute('fill', '#070b14');
    clone.insertBefore(bgRect, clone.firstChild);
    clone.insertBefore(styleEl, clone.firstChild);
    const serialized = new XMLSerializer().serializeToString(clone);
    const blob = new Blob([serialized], {{ type: 'image/svg+xml;charset=utf-8' }});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'evidence-atlas.svg';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }}

  if (canvasSec && svgElem) {{
    canvasSec.addEventListener('mousedown', (e) => {{
      if (e.target.closest('.node') || e.target.closest('.edge') || e.target.closest('button') || e.target.closest('input')) return;
      isPanning = true;
      panMoved = false;
      startX = e.clientX - panX;
      startY = e.clientY - panY;
      canvasSec.style.cursor = 'grabbing';
    }});

    window.addEventListener('mousemove', (e) => {{
      if (!isPanning) return;
      panMoved = true;
      panX = e.clientX - startX;
      panY = e.clientY - startY;
      updateTransform();
    }});

    window.addEventListener('mouseup', (e) => {{
      const wasBackgroundClick = isPanning && !panMoved && !e.target.closest('.node') && !e.target.closest('.edge') && !e.target.closest('button');
      isPanning = false;
      if (canvasSec) canvasSec.style.cursor = 'grab';
      if (wasBackgroundClick) clearAtlasSelection();
    }});

    canvasSec.addEventListener('wheel', (e) => {{
      e.preventDefault();
      const rect = canvasSec.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      const zoomFactor = e.deltaY < 0 ? 1.12 : 0.88;
      const nextScale = Math.min(Math.max(0.3, scale * zoomFactor), 3.0);
      const ratio = nextScale / scale;
      panX = mouseX - (mouseX - panX) * ratio;
      panY = mouseY - (mouseY - panY) * ratio;
      scale = nextScale;
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

  document.getElementById('atlas-btn-fit')?.addEventListener('click', fitToView);
  document.getElementById('atlas-btn-reset-selection')?.addEventListener('click', clearAtlasSelection);
  document.getElementById('atlas-btn-export-svg')?.addEventListener('click', exportCurrentSvg);

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
      toggleInspectorBtn.title = isCollapsed ? TR.expand_panel : TR.collapse_panel;
    }});
  }}

  // --- Type Filter Pills + Real-time Search ---
  function applyFiltersAndSearch() {{
    const q = (searchInput?.value || '').toLowerCase().trim();
    const visibleNodeIds = new Set();

    DATA.nodes.forEach(nObj => {{
      const nodeEl = nodeElemById[nObj.id];
      if (!nodeEl) return;
      const typeOk = activeTypeFilter === 'all' || nObj.type === activeTypeFilter;
      nodeEl.classList.toggle('type-hidden', !typeOk);
      if (typeOk) visibleNodeIds.add(nObj.id);
      if (!q) {{
        nodeEl.classList.remove('search-matched');
        if (!selectedNodeId && !selectedEdgeId) nodeEl.classList.remove('dimmed');
        return;
      }}
      const haystack = ((nObj.label || '') + ' ' + (nObj.properties?.text || '') + ' ' + (nObj.properties?.location || '')).toLowerCase();
      const matched = typeOk && haystack.includes(q);
      nodeEl.classList.toggle('search-matched', matched);
      nodeEl.classList.toggle('dimmed', !matched);
    }});

    DATA.edges.forEach(eObj => {{
      const edgeEl = edgeElemById[eObj.id];
      if (!edgeEl) return;
      const bothTypesVisible = visibleNodeIds.has(eObj.from) && visibleNodeIds.has(eObj.to);
      edgeEl.classList.toggle('type-hidden', !bothTypesVisible);
      if (!q) {{
        if (!selectedNodeId && !selectedEdgeId) edgeEl.classList.remove('dimmed');
        return;
      }}
      const sMatch = nodeElemById[eObj.from]?.classList.contains('search-matched');
      const tMatch = nodeElemById[eObj.to]?.classList.contains('search-matched');
      edgeEl.classList.toggle('dimmed', !(sMatch && tMatch));
    }});

    document.querySelectorAll('.edge-label').forEach(lbl => {{
      const fromId = lbl.dataset.from;
      const toId = lbl.dataset.to;
      if (fromId && toId) {{
        lbl.classList.toggle('type-hidden', !(visibleNodeIds.has(fromId) && visibleNodeIds.has(toId)));
      }}
    }});
  }}

  const filterBar = document.getElementById('atlas-type-filters');
  if (filterBar) {{
    const typeCounts = Object.create(null);
    DATA.nodes.forEach(n => {{ typeCounts[n.type] = (typeCounts[n.type] || 0) + 1; }});
    const order = ['answer', 'claim', 'entity', 'code', 'chunk', 'document', 'case'];
    let pillsHtml = `<button type="button" class="type-filter-pill active" data-type-filter="all">${{escapeHtml(TR.filter_all || 'All')}} (${{DATA.nodes.length}})</button>`;
    order.forEach(t => {{
      if (!typeCounts[t]) return;
      const label = TYPE_NAMES[t] || t;
      const color = TYPE_COLORS[t] || '#38bdf8';
      pillsHtml += `<button type="button" class="type-filter-pill" data-type-filter="${{t}}"><span class="type-dot" style="background:${{color}};"></span>${{escapeHtml(label)}} (${{typeCounts[t]}})</button>`;
    }});
    filterBar.innerHTML = pillsHtml;
    filterBar.addEventListener('click', (e) => {{
      const btn = e.target.closest('[data-type-filter]');
      if (!btn) return;
      activeTypeFilter = btn.dataset.typeFilter || 'all';
      filterBar.querySelectorAll('.type-filter-pill').forEach(p => p.classList.toggle('active', p === btn));
      applyFiltersAndSearch();
    }});
  }}

  if (searchInput) {{
    searchInput.addEventListener('input', applyFiltersAndSearch);
  }}

  // Node dragging physics (resumes in-place without resetting positions)
  document.querySelectorAll('.node').forEach(nodeEl => {{
    nodeEl.addEventListener('mousedown', (e) => {{
      if (currentLayout !== 'galaxy') return;
      const nid = nodeEl.dataset.node;
      const sn = simNodes.find(n => n.id === nid);
      if (!sn) return;
      draggedNode = sn;
      dragStartX = e.clientX;
      dragStartY = e.clientY;
      nodeStartX = sn.x;
      nodeStartY = sn.y;
      e.stopPropagation();
      resumeSimulation(0.35);
    }});
  }});

  window.addEventListener('mousemove', (e) => {{
    if (draggedNode && currentLayout === 'galaxy') {{
      const mouseDx = (e.clientX - dragStartX) / scale;
      const mouseDy = (e.clientY - dragStartY) / scale;
      draggedNode.x = nodeStartX + mouseDx;
      draggedNode.y = nodeStartY + mouseDy;
      draggedNode.vx = 0;
      draggedNode.vy = 0;
    }}
  }});

  window.addEventListener('mouseup', () => {{
    if (draggedNode) {{
      draggedNode = null;
    }}
  }});

  // --- Node Selection & Focus ---
  window.selectAtlasNode = (nodeId) => {{
    const node = nodeById[nodeId];
    if (!node || !detailTitle || !detail) return;
    selectedNodeId = nodeId;
    selectedEdgeId = null;

    detailTitle.textContent = node.label;
    const typeLabel = TYPE_NAMES[node.type] || node.type;
    const loc = node.properties?.location || node.properties?.source_id || '';
    const text = node.properties?.text || node.label || '';
    const statusNote = node.review_status === 'needs_review' ? (TR.needs_review_note || '\\nCần xem lại') : '';

    detail.innerHTML = `
      <div style="font-size:11px; font-weight:700; color:#38bdf8; margin-bottom:6px;">${{escapeHtml(typeLabel)}}</div>
      ${{loc ? `<div style="font-size:11px; color:#a78bfa; margin-bottom:8px; word-break:break-all;">📁 ${{escapeHtml(loc)}}</div>` : ''}}
      <div style="font-size:12px; line-height:1.6; color:#e2e8f0; white-space:pre-wrap; word-break:break-word;">${{escapeHtml(text + statusNote)}}</div>
      <div>
        <button type="button" class="atlas-copy-btn">${{escapeHtml(TR.copy_btn)}}</button>
        ${{loc ? `<button type="button" class="atlas-copy-btn atlas-open-btn">${{escapeHtml(TR.open_portal)}}</button>` : ''}}
      </div>
    `;
    const copyBtn = detail.querySelector('.atlas-copy-btn:not(.atlas-open-btn)');
    if (copyBtn) {{
      copyBtn.addEventListener('click', () => {{
        navigator.clipboard?.writeText(text);
        copyBtn.textContent = TR.copied_btn;
        setTimeout(() => {{ copyBtn.textContent = TR.copy_btn; }}, 2000);
      }});
    }}
    const openBtn = detail.querySelector('.atlas-open-btn');
    if (openBtn && loc) {{
      openBtn.addEventListener('click', () => {{
        openAtlasLocation(loc, nodeId, node.label);
        openBtn.textContent = TR.opened_portal;
        setTimeout(() => {{ openBtn.textContent = TR.open_portal; }}, 2000);
      }});
    }}

    // Update Mini Radar
    updateAtlasMiniRadar(nodeId);

    // Update Confidence Gauge (supports 0 and top-level node.confidence)
    if (confBox && confPct && confFill) {{
      const rawScore = node.properties?.score ?? node.properties?.confidence ?? node.confidence ?? (node.review_status === 'needs_review' ? 0.45 : null);
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
        return `<div class="atlas-link-chip" data-target-node="${{escapeHtml(e.from)}}">${{escapeHtml(srcLabel)}}</div>`;
      }}).join('') || `<span style="font-size:11px; color:#64748b;">${{escapeHtml(TR.empty_rel)}}</span>`;

      outCount.textContent = outboundEdges.length;
      outChips.innerHTML = outboundEdges.map(e => {{
        const tgt = nodeById[e.to];
        const tgtLabel = tgt?.label || e.to;
        return `<div class="atlas-link-chip" data-target-node="${{escapeHtml(e.to)}}">${{escapeHtml(tgtLabel)}}</div>`;
      }}).join('') || `<span style="font-size:11px; color:#64748b;">${{escapeHtml(TR.empty_rel)}}</span>`;

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

    Object.entries(nodeElemById).forEach(([nid, el]) => {{
      const isSelf = nid === nodeId;
      el.classList.toggle('active', isSelf);
      el.classList.toggle('dimmed', !connectedNodeIds.has(nid));
    }});

    Object.entries(edgeElemById).forEach(([eid, el]) => {{
      const isConnected = connectedEdges.has(eid);
      el.classList.toggle('active', isConnected);
      el.classList.toggle('dimmed', !isConnected);
    }});
  }};

  function selectAtlasEdge(edgeId) {{
    const edge = edgeById[edgeId];
    if (!edge || !detailTitle || !detail) return;
    selectedNodeId = null;
    selectedEdgeId = edgeId;
    const relName = edge.relation.replaceAll('_', ' ');
    detailTitle.textContent = relName;
    const source = nodeById[edge.from]?.label || edge.from;
    const target = nodeById[edge.to]?.label || edge.to;
    const locations = (edge.receipts || []).map(item => item.location).filter(Boolean).join(', ');
    const statusLabel = edge.review_status === 'needs_review' ? (TR.edge_status_review || TR.review_needed) : (TR.edge_status_verified || 'Verified');
    detail.innerHTML = `
      <div style="font-size:12px; color:#38bdf8; font-weight:700; margin-bottom:6px;">${{escapeHtml(TR.edge_title)}}</div>
      <div style="margin-bottom:8px;"><span class="badge">${{escapeHtml(edge.origin || 'local')}}</span><span class="badge">${{escapeHtml(statusLabel)}}</span></div>
      <div style="font-size:12.5px; color:#f8fafc; line-height:1.5;"><strong>${{escapeHtml(source)}}</strong><br>───▶ <strong>${{escapeHtml(target)}}</strong></div>
      ${{locations ? `<div style="font-size:11px; color:#a78bfa; margin-top:8px; word-break:break-all;">${{escapeHtml(TR.edge_loc_prefix + locations)}}</div>` : ''}}
    `;
    const radarContainer = document.getElementById('atlas-mini-radar-container');
    if (radarContainer) radarContainer.style.display = 'none';
    if (linksBox) linksBox.style.display = 'none';
    if (confBox && confPct && confFill) {{
      if (edge.confidence !== undefined && edge.confidence !== null) {{
        const pct = Math.round(Number(edge.confidence) * 100);
        confPct.textContent = pct + '%';
        confFill.style.width = pct + '%';
        confFill.style.backgroundColor = pct >= 80 ? 'var(--success)' : (pct >= 50 ? 'var(--warning)' : 'var(--danger)');
        confBox.style.display = 'block';
      }} else {{
        confBox.style.display = 'none';
      }}
    }}
    const endpoints = new Set([edge.from, edge.to]);
    Object.entries(nodeElemById).forEach(([nid, el]) => {{
      el.classList.remove('active');
      el.classList.toggle('dimmed', !endpoints.has(nid));
    }});
    Object.entries(edgeElemById).forEach(([eid, el]) => {{
      const isSelected = eid === edgeId;
      el.classList.toggle('active', isSelected);
      el.classList.toggle('dimmed', !isSelected);
    }});
  }}

  const setView = (view) => {{
    document.body.dataset.view = view;
    document.querySelectorAll('button[data-view]').forEach(button => {{
      button.classList.toggle('active', button.dataset.view === view);
    }});
    if (status) status.textContent = (TR.status_prefix || '') + (view === 'full' ? TR.view_full : TR.view_answer);
  }};

  document.querySelectorAll('button[data-view]').forEach(button => {{
    button.addEventListener('click', () => setView(button.dataset.view));
  }});

  document.querySelectorAll('[data-node]').forEach(element => {{
    element.addEventListener('click', () => window.selectAtlasNode(element.dataset.node));
    element.addEventListener('keydown', (event) => {{
      if (event.key === 'Enter' || event.key === ' ') {{
        event.preventDefault();
        window.selectAtlasNode(element.dataset.node);
      }}
    }});
  }});

  document.querySelectorAll('[data-edge]').forEach(element => {{
    element.addEventListener('click', () => selectAtlasEdge(element.dataset.edge));
    element.addEventListener('keydown', (event) => {{
      if (event.key === 'Enter' || event.key === ' ') {{
        event.preventDefault();
        selectAtlasEdge(element.dataset.edge);
      }}
    }});
  }});

  document.addEventListener('keydown', (event) => {{
    if (event.key === 'Escape') {{
      clearAtlasSelection();
    }}
  }});

  if (layout) {{
    layout.classList.add('galaxy-mode');
  }}
  initForceSimulation();
}})();
</script></body></html>"""
