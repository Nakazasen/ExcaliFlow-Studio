"""Offline Codebase Atlas: relationship graph, explanations, and local Q&A."""

from __future__ import annotations

import html
import json
import math
from collections import Counter
from pathlib import Path


def _module_keys(path: str) -> set[str]:
    module = Path(path).with_suffix("").as_posix().replace("/", ".")
    keys = {module, module.rsplit(".", 1)[-1]}
    if module.startswith("src."):
        keys.add(module.removeprefix("src."))
    return keys


def _atlas_model(report: dict) -> dict:
    keys_to_file: dict[str, str] = {}
    for file in report["files"]:
        for key in _module_keys(file):
            keys_to_file.setdefault(key, file)
    symbol_count = Counter(symbol["file"] for symbol in report["symbols"])
    ranked_files = sorted(report["files"], key=lambda file: (-symbol_count[file], file))[:32]
    selected = set(ranked_files)
    nodes = [{"id": f"n{index}", "file": file, "symbols": symbol_count[file]} for index, file in enumerate(ranked_files)]
    node_id = {node["file"]: node["id"] for node in nodes}
    edges: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for relation in report["relationships"]:
        target = relation["to"].lstrip(".")
        target_file = keys_to_file.get(target) or keys_to_file.get(target.split(".")[0])
        source_file = relation["from"]
        pair = (source_file, target_file or "")
        if target_file and source_file in selected and target_file in selected and source_file != target_file and pair not in seen:
            edges.append({"from": node_id[source_file], "to": node_id[target_file], "source": source_file, "target": target_file, "line": relation["line"]})
            seen.add(pair)
    columns = max(1, math.ceil(math.sqrt(len(nodes))))
    for index, node in enumerate(nodes):
        node["x"] = 80 + (index % columns) * 230
        node["y"] = 80 + (index // columns) * 145
    width = max(720, columns * 230 + 80)
    rows = max(1, math.ceil(len(nodes) / columns))
    height = max(480, rows * 145 + 100)
    symbols_by_file: dict[str, list[dict]] = {file: [] for file in ranked_files}
    for symbol in report["symbols"]:
        if symbol["file"] in symbols_by_file:
            symbols_by_file[symbol["file"]].append(symbol)
    return {"nodes": nodes, "edges": edges, "symbols_by_file": symbols_by_file, "width": width, "height": height}


def build_atlas_html(report: dict, audience: str = "engineer") -> str:
    """Build a single-file UI without a server or browser dependency."""
    if audience not in {"engineer", "learner"}:
        raise ValueError("Audience must be engineer or learner.")
    atlas = _atlas_model(report)
    payload = {"report": report, "atlas": atlas, "defaultAudience": audience}
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    edge_svg = "".join(
        f'<line class="edge" x1="{next(node for node in atlas["nodes"] if node["id"] == edge["from"])["x"] + 155}" y1="{next(node for node in atlas["nodes"] if node["id"] == edge["from"])["y"] + 35}" x2="{next(node for node in atlas["nodes"] if node["id"] == edge["to"])["x"]}" y2="{next(node for node in atlas["nodes"] if node["id"] == edge["to"])["y"] + 35}" />'
        for edge in atlas["edges"]
    )
    node_svg = "".join(
        f'<g class="graph-node" data-node="{node["id"]}" tabindex="0"><rect x="{node["x"]}" y="{node["y"]}" width="155" height="70" rx="14"/><text x="{node["x"] + 12}" y="{node["y"] + 29}">{html.escape(Path(node["file"]).name)[:21]}</text><text class="caption" x="{node["x"] + 12}" y="{node["y"] + 52}">{node["symbols"]} declarations</text></g>'
        for node in atlas["nodes"]
    )
    sidebar_nodes = "".join(f'<button class="node-list-item" data-node="{node["id"]}">{html.escape(node["file"])}</button>' for node in atlas["nodes"])
    title = html.escape(Path(report["root"]).name)
    template = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ - Codebase Atlas</title>
<style>
:root{--ink:#17212b;--muted:#617083;--paper:#f7f3ec;--panel:#fffdf9;--accent:#ec6b2d;--line:#d9d2c5;--blue:#345a93}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.45 "Segoe UI",Arial,sans-serif}.app{display:grid;grid-template-columns:250px minmax(460px,1fr) 340px;min-height:100vh}.left,.right{background:var(--panel);padding:22px;border-color:var(--line)}.left{border-right:1px solid var(--line)}.right{border-left:1px solid var(--line)}.eyebrow{font-size:11px;letter-spacing:.12em;color:var(--accent);font-weight:700;text-transform:uppercase}h1{font-size:25px;line-height:1.05;margin:6px 0 10px}h2{font-size:15px;margin:18px 0 8px}.meta{color:var(--muted);font-size:12px}.node-list-item{display:block;text-align:left;width:100%;border:0;background:transparent;padding:8px 6px;border-radius:7px;color:#293847;cursor:pointer;overflow-wrap:anywhere}.node-list-item:hover,.node-list-item.active{background:#ffe9da;color:#9c3d13}.canvas-head{display:flex;align-items:start;justify-content:space-between;padding:24px 28px 14px}.canvas{min-width:0}.graph-wrap{margin:0 20px 25px;border:1px solid var(--line);border-radius:16px;background:#fffefa;overflow:auto;min-height:520px}.graph{min-width:720px;width:100%;display:block}.edge{stroke:#93a0aa;stroke-width:2;marker-end:url(#arrow)}.graph-node{cursor:pointer}.graph-node rect{fill:#fff8f2;stroke:#e88351;stroke-width:2}.graph-node:hover rect,.graph-node.active rect{fill:#ffe4d4;stroke:#c74918;stroke-width:3}.graph-node text{font-size:13px;fill:var(--ink);font-weight:700}.graph-node .caption{font-size:11px;fill:var(--muted);font-weight:400}.toggle{display:flex;gap:6px}.toggle button,.ask button{border:1px solid var(--line);border-radius:7px;background:#fff;padding:7px 9px;cursor:pointer}.toggle button.active{background:var(--ink);color:#fff;border-color:var(--ink)}#detail{background:#f4f7fa;border-radius:10px;padding:12px;min-height:122px;white-space:pre-wrap}.ask{margin-top:18px}.ask textarea{width:100%;min-height:72px;resize:vertical;border:1px solid var(--line);border-radius:8px;padding:9px;font:inherit}.ask button{margin-top:8px;background:var(--accent);border-color:var(--accent);color:#fff;font-weight:700}.answer{margin-top:10px;padding:11px;background:#fff7ef;border-left:3px solid var(--accent);white-space:pre-wrap}.fidelity{margin-top:16px;color:var(--muted);font-size:12px}@media(max-width:980px){.app{grid-template-columns:220px 1fr}.right{grid-column:1/-1;border-left:0;border-top:1px solid var(--line)}}@media(max-width:650px){.app{display:block}.left{border-right:0;border-bottom:1px solid var(--line)}}
</style></head><body><main class="app"><aside class="left"><div class="eyebrow">Graph Workspace</div><h1>Codebase Atlas</h1><div class="meta">__TITLE__</div><h2>Modules</h2><div id="module-list">__SIDEBAR_NODES__</div></aside><section class="canvas"><header class="canvas-head"><div><div class="eyebrow">Relationships</div><h2>Internal import map</h2><div class="meta" id="graph-stats"></div></div></header><div class="graph-wrap"><svg class="graph" viewBox="0 0 __WIDTH__ __HEIGHT__" role="img" aria-label="Codebase relationship graph"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#93a0aa"/></marker></defs>__EDGES____NODES__</svg></div></section><aside class="right"><div class="eyebrow">Explain</div><div class="toggle"><button data-audience="engineer">Engineer</button><button data-audience="learner">Learner</button></div><h2 id="detail-title">Select a module</h2><div id="detail">Select a module in the graph to see source-backed declarations and relationships.</div><div class="ask"><div class="eyebrow">Ask the atlas</div><textarea id="question" placeholder="What is UserService? How do imports connect?"></textarea><button id="ask-button">Answer from source evidence</button><div class="answer" id="answer">Answers cite declarations or imports found in the local scan.</div></div><div class="fidelity" id="fidelity"></div></aside></main><script>const DATA=__DATA__;let audience=DATA.defaultAudience;const byId=Object.fromEntries(DATA.atlas.nodes.map(n=>[n.id,n]));const symbols=DATA.report.symbols;document.getElementById('graph-stats').textContent=`${DATA.atlas.nodes.length} modules · ${DATA.atlas.edges.length} internal imports`;document.getElementById('fidelity').textContent=DATA.report.fidelity;function words(value){return (value.toLowerCase().match(/[a-z_][a-z0-9_]*/g)||[]).filter(w=>!['what','is','the','how','do','imports','connect','explain','about'].includes(w))}function selectNode(id){const node=byId[id];if(!node)return;document.querySelectorAll('[data-node]').forEach(el=>el.classList.toggle('active',el.dataset.node===id));const found=symbols.filter(s=>s.file===node.file).slice(0,8);const intro=audience==='learner'?`${node.file} is one part of the project. Start by recognizing its named building blocks.`:`${node.file} contains implementation declarations and participates in the import graph.`;document.getElementById('detail-title').textContent=node.file;document.getElementById('detail').textContent=intro+'\n\n'+(found.map(s=>`${s.kind} ${s.qualified_name} (${s.file}:${s.line})${s.docstring?' — '+s.docstring:''}`).join('\n')||'No supported declarations were found in this file.')}document.querySelectorAll('.graph-node').forEach(el=>el.classList.toggle('active',el.dataset.node===id));}function answer(){const q=document.getElementById('question').value.trim();const out=document.getElementById('answer');if(!q){out.textContent='Ask about a module, class, function, dependency, or import.';return}if(/depend|import|relationship|connect/i.test(q)){const edges=DATA.atlas.edges.slice(0,8);out.textContent=edges.length?edges.map(e=>`${e.source}:${e.line} imports ${e.target}`).join('\n')+'\n\nEvidence: local import scan.':'No internal import relationship was found in the displayed atlas.';return}const query=words(q);const matches=symbols.map(s=>({s,score:query.reduce((n,w)=>n+(s.name+' '+s.qualified_name+' '+s.file).toLowerCase().includes(w),0)})).filter(x=>x.score).sort((a,b)=>b.score-a.score).slice(0,4);out.textContent=matches.length?matches.map(({s})=>audience==='learner'?`${s.qualified_name} is a ${s.kind}, a named building block in the program. Evidence: ${s.file}:${s.line}`:`${s.qualified_name} is declared as a ${s.kind}. Evidence: ${s.file}:${s.line}`).join('\n\n'):'No matching declaration found. Try an exact module, class, or function name.';}document.querySelectorAll('[data-node]').forEach(el=>el.addEventListener('click',()=>selectNode(el.dataset.node)));document.querySelectorAll('[data-audience]').forEach(button=>{button.classList.toggle('active',button.dataset.audience===audience);button.addEventListener('click',()=>{audience=button.dataset.audience;document.querySelectorAll('[data-audience]').forEach(b=>b.classList.toggle('active',b===button));const active=document.querySelector('.node-list-item.active');if(active)selectNode(active.dataset.node);});});document.getElementById('ask-button').addEventListener('click',answer);</script></body></html>"""
    return (template.replace("__TITLE__", title).replace("__SIDEBAR_NODES__", sidebar_nodes).replace("__WIDTH__", str(atlas["width"])).replace("__HEIGHT__", str(atlas["height"])).replace("__EDGES__", edge_svg).replace("__NODES__", node_svg).replace("__DATA__", data))


def write_atlas(project_dir: str | Path, output_path: str | Path, audience: str = "engineer") -> Path:
    from excaliflow.explorer import inspect_codebase

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_atlas_html(inspect_codebase(project_dir), audience), encoding="utf-8")
    return output
