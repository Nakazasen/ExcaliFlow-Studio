"""Offline, answer-centric renderer for a validated Evidence Graph."""

from __future__ import annotations

import html
import json
from collections import defaultdict

from excaliflow.knowledge import REVIEW_STATUSES, validate_evidence_graph


TYPE_LABELS = {
    "answer": "Câu trả lời",
    "document": "Tài liệu",
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


def _display_label(node: dict) -> str:
    text = node["label"]
    return text if len(text) <= 80 else text[:77].rstrip() + "…"


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
    status = "Cần xem lại" if edge["review_status"] == "needs_review" else "Đã có bằng chứng"
    locations = ", ".join(receipt["location"] for receipt in edge["receipts"])
    return f"{status}. Nguồn: {edge['origin']}; confidence {edge['confidence']:.0%}; vị trí: {locations}."


def build_evidence_atlas_html(graph: dict) -> str:
    """Create one standalone HTML document from a validated evidence graph."""

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
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    edge_svg = "".join(
        f'<line class="edge{(" focus" if edge["id"] in focus_edges else "")}" data-edge="{html.escape(edge["id"])}" '
        f'x1="{positions[edge["from"]][0] + 130}" y1="{positions[edge["from"]][1] + 42}" '
        f'x2="{positions[edge["to"]][0] + 130}" y2="{positions[edge["to"]][1] + 42}" />'
        for edge in graph["edges"]
    )
    node_svg = "".join(
        f'<g class="node{(" focus" if node["id"] in focus_ids else "")}{(" needs-review" if node.get("review_status") == "needs_review" else "")}" '
        f'data-node="{html.escape(node["id"])}" tabindex="0" role="button"><rect x="{positions[node["id"]][0]}" '
        f'y="{positions[node["id"]][1]}" width="260" height="84" rx="14" style="--node-color:{TYPE_COLORS[node["type"]]}"/>'
        f'<text class="node-type" x="{positions[node["id"]][0] + 14}" y="{positions[node["id"]][1] + 24}">{TYPE_LABELS[node["type"]]}</text>'
        f'<text class="node-label" x="{positions[node["id"]][0] + 14}" y="{positions[node["id"]][1] + 51}">{html.escape(_display_label(node))}</text>'
        f'{f"<text class=\"review-label\" x=\"{positions[node["id"]][0] + 14}\" y=\"{positions[node["id"]][1] + 72}\">Cần xem lại</text>" if node.get("review_status") == "needs_review" else ""}'
        f'</g>'
        for node in graph["nodes"]
    )
    payload = json.dumps(graph, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape(graph["title"])
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidence Atlas — {title}</title>
<style>
:root{{--ink:#162231;--muted:#5f6c78;--paper:#faf8f2;--line:#ded8cd;--orange:#f16536}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif}}header{{padding:28px max(24px,calc((100vw - 1240px)/2));border-bottom:1px solid var(--line);background:#fffdf9}}.eyebrow{{color:#ce542a;text-transform:uppercase;letter-spacing:.13em;font-size:11px;font-weight:800}}h1{{margin:7px 0 8px;font-size:31px}}.lede{{margin:0;color:var(--muted);max-width:800px}}main{{max-width:1240px;margin:auto;padding:24px}}.toolbar{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:15px}}button{{font:inherit;border:1px solid var(--line);background:#fff;border-radius:9px;padding:9px 12px;cursor:pointer;color:var(--ink)}}button.active{{background:var(--ink);color:#fff;border-color:var(--ink)}}.legend{{color:var(--muted);font-size:13px}}.layout{{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:20px}}.canvas{{overflow:auto;border:1px solid var(--line);border-radius:18px;background:#fffefa;min-height:560px}}svg{{display:block;min-width:{width}px}}.edge{{stroke:#a6afb5;stroke-width:2;opacity:.34}}.node{{cursor:pointer}}.node rect{{fill:#fff;stroke:var(--node-color);stroke-width:2.4}}.node.needs-review rect{{stroke-dasharray:7 4}}.node:hover rect,.node.active rect{{fill:#fff2e9;stroke-width:4}}.node-type{{font-size:12px;font-weight:800;fill:#5f6c78}}.node-label{{font-size:14px;font-weight:700;fill:#162231}}.review-label{{font-size:11px;font-weight:800;fill:#b66a00}}body[data-view="answer"] .node:not(.focus),body[data-view="answer"] .edge:not(.focus){{display:none}}aside{{position:sticky;top:18px;align-self:start;border:1px solid var(--line);border-radius:18px;background:#fff;padding:18px;max-height:calc(100vh - 36px);overflow:auto}}aside h2{{font-size:19px;margin:8px 0}}.receipt{{white-space:pre-wrap;line-height:1.55;font-size:14px;background:#f5f7f8;padding:12px;border-radius:10px}}.badge{{display:inline-block;padding:4px 7px;border-radius:999px;background:#fff1df;color:#9a4b12;font-size:12px;font-weight:700;margin:2px 3px 2px 0}}.notice{{border-left:3px solid #d39a1c;padding-left:10px;color:#6d5114;font-size:13px}}@media(max-width:850px){{.layout{{display:block}}aside{{position:static;max-height:none;margin-top:18px}}h1{{font-size:25px}}}}
</style></head><body data-view="answer"><header><div class="eyebrow">Evidence Graph · local file</div><h1>Evidence Atlas</h1><p class="lede">{title}. Bản đồ này hiển thị quan hệ có nguồn; đường nét đứt và nhãn “Cần xem lại” là nhận định chưa được xác minh.</p></header><main><div class="toolbar"><button data-view="answer" class="active">Câu trả lời &amp; nguồn</button><button data-view="full">Toàn bộ knowledge graph</button><span class="legend">Bấm một khối hoặc đường nối để xem biên lai bằng chứng.</span></div><div class="layout"><section class="canvas" aria-label="Evidence Graph"><svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Evidence graph for {title}">{edge_svg}{node_svg}</svg></section><aside><div class="eyebrow">Nguồn bằng chứng</div><h2 id="detail-title">Bắt đầu từ câu trả lời</h2><div id="detail" class="receipt">Chọn câu trả lời, đoạn tài liệu, nhận định hoặc đường nối để xem nguồn, vị trí và độ tin cậy.</div></aside></div></main><script>const DATA={payload};const nodeById=Object.fromEntries(DATA.nodes.map(n=>[n.id,n]));const edgesByNode={{}};for(const edge of DATA.edges){{for(const id of [edge.from,edge.to]){{(edgesByNode[id]??=[]).push(edge);}}}}function showNode(id){{const node=nodeById[id];const edges=edgesByNode[id]||[];document.querySelectorAll('.node').forEach(el=>el.classList.toggle('active',el.dataset.node===id));const props=Object.entries(node.properties||{{}}).map(([k,v])=>`${{k}}: ${{v}}`).join('\n');const status=node.review_status==='needs_review'?'\nTrạng thái: Cần xem lại (không phải fact đã xác minh).':'';const receipts=edges.flatMap(edge=>edge.receipts.map(receipt=>`• ${{edge.relation}} — ${{_receipt_text(edge)}}`)).join('\n');document.getElementById('detail-title').textContent=node.label;document.getElementById('detail').textContent=`Loại: ${{node.type}}${{status}}\n${{props?`\n${{props}}`:''}}${{receipts?`\n\nBiên lai:\n${{receipts}}`:''}}`;}}function showEdge(id){{const edge=DATA.edges.find(item=>item.id===id);document.querySelectorAll('.node').forEach(el=>el.classList.remove('active'));document.getElementById('detail-title').textContent=`${{edge.relation}}`;document.getElementById('detail').textContent=`${{nodeById[edge.from].label}} → ${{nodeById[edge.to].label}}\n\n${{_receipt_text(edge)}}`;}}document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{{document.body.dataset.view=button.dataset.view;document.querySelectorAll('[data-view]').forEach(item=>item.classList.toggle('active',item===button));}}));document.querySelectorAll('[data-node]').forEach(item=>{{item.addEventListener('click',()=>showNode(item.dataset.node));item.addEventListener('keydown',event=>{{if(event.key==='Enter'||event.key===' '){{event.preventDefault();showNode(item.dataset.node);}}}});}});document.querySelectorAll('[data-edge]').forEach(item=>item.addEventListener('click',()=>showEdge(item.dataset.edge)));</script></body></html>"""
