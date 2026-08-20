"""Offline Codebase Atlas: learner-first overview, full graph, and local Q&A."""

from __future__ import annotations

import html
import json
import math
from collections import Counter
from pathlib import Path

from excaliflow.bridge import discover_ide_bridge


def _module_keys(path: str) -> set[str]:
    module = Path(path).with_suffix("").as_posix().replace("/", ".")
    keys = {module, module.rsplit(".", 1)[-1]}
    if module.startswith("src."):
        keys.add(module.removeprefix("src."))
    return keys


def _atlas_model(report: dict) -> dict:
    """Return every scanned source file and the import edges proven locally."""
    keys_to_file: dict[str, str] = {}
    for file in report["files"]:
        for key in _module_keys(file):
            keys_to_file.setdefault(key, file)
    symbol_count = Counter(symbol["file"] for symbol in report["symbols"])
    ranked_files = sorted(report["files"], key=lambda file: (-symbol_count[file], file))
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
            edges.append(
                {
                    "from": node_id[source_file],
                    "to": node_id[target_file],
                    "source": source_file,
                    "target": target_file,
                    "line": relation["line"],
                }
            )
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


def _learning_category(file: str) -> str:
    """Classify by path/name hints only; never infer product behavior."""
    value = file.lower().replace("\\", "/")
    tokens = {piece for segment in value.split("/") for piece in segment.replace(".", "_").split("_")}
    if tokens & {"ui", "view", "views", "page", "pages", "component", "components", "frontend", "web", "screen", "screens"}:
        return "ui"
    if tokens & {"data", "database", "store", "stores", "repository", "repositories", "model", "models", "schema", "schemas", "persistence"}:
        return "data"
    if tokens & {"api", "client", "clients", "adapter", "adapters", "integration", "integrations", "external", "vendor"}:
        return "integration"
    return "processing"


def _learning_model(report: dict, atlas: dict) -> dict:
    labels = {
        "ui": ("Giao diện", "Phần nhận thao tác và hiển thị kết quả cho người dùng."),
        "processing": ("Xử lý", "Phần biến dữ liệu đầu vào thành quyết định hoặc kết quả."),
        "data": ("Dữ liệu", "Phần đọc, lưu, hoặc tổ chức thông tin."),
        "integration": ("Tích hợp", "Phần kết nối với công cụ, API, hoặc hệ thống bên ngoài."),
    }
    grouped: dict[str, list[str]] = {key: [] for key in labels}
    for file in report["files"]:
        grouped[_learning_category(file)].append(file)
    symbols = Counter(symbol["file"] for symbol in report["symbols"])
    degree = Counter(edge["source"] for edge in atlas["edges"]) + Counter(edge["target"] for edge in atlas["edges"])
    start_file = max(report["files"], key=lambda file: (degree[file], symbols[file], file), default=None)
    blocks = []
    for key in ("ui", "processing", "data", "integration"):
        files = sorted(grouped[key])
        if files:
            label, plain_language = labels[key]
            blocks.append(
                {
                    "id": key,
                    "label": label,
                    "plain_language": plain_language,
                    "files": files,
                    "symbols": sum(symbols[file] for file in files),
                }
            )
    suffixes = sorted({Path(file).suffix.lstrip(".") or "other" for file in report["files"]})
    overview = (
        f"Bản quét này tìm thấy {len(report['files'])} tệp mã nguồn, "
        f"{len(report['symbols'])} thao tác/khối có tên, và {len(atlas['edges'])} liên kết nội bộ. "
        f"Loại tệp phát hiện: {', '.join(suffixes) or 'không xác định'}."
    )
    return {"blocks": blocks, "start_file": start_file, "overview": overview}


def build_atlas_html(report: dict, audience: str = "learner") -> str:
    """Build one self-contained, offline Atlas HTML document."""
    if audience not in {"engineer", "learner"}:
        raise ValueError("Audience must be engineer or learner.")
    atlas = _atlas_model(report)
    learning = _learning_model(report, atlas)
    bridge = discover_ide_bridge(report["root"])
    payload = {"report": report, "atlas": atlas, "learning": learning, "bridge": bridge, "defaultAudience": audience}
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    node_by_id = {node["id"]: node for node in atlas["nodes"]}
    edge_svg = "".join(
        f'<line class="edge" x1="{node_by_id[edge["from"]]["x"] + 155}" y1="{node_by_id[edge["from"]]["y"] + 35}" x2="{node_by_id[edge["to"]]["x"]}" y2="{node_by_id[edge["to"]]["y"] + 35}" />'
        for edge in atlas["edges"]
    )
    node_svg = "".join(
        f'<g class="graph-node" data-node="{node["id"]}" tabindex="0"><rect x="{node["x"]}" y="{node["y"]}" width="155" height="70" rx="14"/><text x="{node["x"] + 12}" y="{node["y"] + 29}">{html.escape(Path(node["file"]).name)[:21]}</text><text class="caption" x="{node["x"] + 12}" y="{node["y"] + 52}">{node["symbols"]} declarations</text></g>'
        for node in atlas["nodes"]
    )
    sidebar_nodes = "".join(
        f'<button class="node-list-item" data-node="{node["id"]}">{html.escape(node["file"])}</button>' for node in atlas["nodes"]
    )
    block_cards = "".join(
        f'<button class="block-card" data-block="{block["id"]}"><span class="block-name">{html.escape(block["label"])}</span><span>{html.escape(block["plain_language"])}</span><small>{len(block["files"])} tệp · {block["symbols"]} thao tác có tên</small></button>'
        for block in learning["blocks"]
    )
    title = html.escape(Path(report["root"]).name)
    template = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ - Codebase Atlas</title>
<style>
:root{--ink:#17212b;--muted:#617083;--paper:#f7f3ec;--panel:#fffdf9;--accent:#ec6b2d;--line:#d9d2c5;--blue:#345a93;--soft:#fff2e8}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 "Segoe UI",Arial,sans-serif}.app{min-height:100vh}.topbar{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:18px clamp(18px,4vw,56px);background:var(--panel);border-bottom:1px solid var(--line)}.brand{font-size:22px;font-weight:800}.eyebrow{font-size:11px;letter-spacing:.12em;color:var(--accent);font-weight:700;text-transform:uppercase}.mode-switch,.toggle,.sample-questions{display:flex;gap:8px;flex-wrap:wrap}.mode-switch button,.toggle button,.ask button,.sample-questions button{border:1px solid var(--line);border-radius:8px;background:#fff;padding:8px 11px;cursor:pointer;color:var(--ink);font:inherit}.mode-switch button.active,.toggle button.active{background:var(--ink);color:#fff;border-color:var(--ink)}.view{display:none}.view.active{display:block}.learner-shell{max-width:1120px;margin:auto;padding:clamp(24px,5vw,64px) clamp(18px,4vw,40px)}.learner-hero{max-width:760px}.learner-hero h1{font-size:clamp(34px,5vw,58px);line-height:1.02;margin:7px 0 16px}.lead{font-size:18px;color:#334454}.evidence-note{margin-top:16px;padding:12px 14px;background:#fff8ef;border-left:4px solid var(--accent);color:#51443c}.blocks{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:28px 0}.block-card{border:1px solid var(--line);background:var(--panel);border-radius:14px;padding:17px;text-align:left;cursor:pointer;color:var(--ink);display:grid;gap:8px;font:inherit}.block-card:hover,.block-card.active{border-color:var(--accent);box-shadow:0 8px 22px #de91612b}.block-name{font-size:19px;font-weight:800}.block-card small{color:var(--muted)}.learning-grid{display:grid;grid-template-columns:1.15fr .85fr;gap:22px;margin-top:28px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:20px}.panel h2{margin:0 0 12px;font-size:21px}.path-step{display:grid;grid-template-columns:30px 1fr;gap:10px;margin:13px 0}.step-number{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;background:var(--accent);color:#fff;font-weight:800}.glossary{color:#455566}.glossary strong{color:var(--ink)}.full-shell{display:grid;grid-template-columns:250px minmax(460px,1fr) 340px;min-height:calc(100vh - 72px)}.left,.right{background:var(--panel);padding:22px;border-color:var(--line)}.left{border-right:1px solid var(--line)}.right{border-left:1px solid var(--line)}.left h2,.right h2{font-size:17px;margin:15px 0 8px}.meta{color:var(--muted);font-size:13px}.node-list-item{display:block;text-align:left;width:100%;border:0;background:transparent;padding:8px 6px;border-radius:7px;color:#293847;cursor:pointer;overflow-wrap:anywhere}.node-list-item:hover,.node-list-item.active{background:#ffe9da;color:#9c3d13}.canvas{min-width:0}.canvas-head{display:flex;align-items:start;justify-content:space-between;padding:24px 28px 14px}.graph-wrap{margin:0 20px 25px;border:1px solid var(--line);border-radius:16px;background:#fffefa;overflow:auto;min-height:520px}.graph{min-width:720px;width:100%;display:block}.edge{stroke:#93a0aa;stroke-width:2;marker-end:url(#arrow)}.graph-node{cursor:pointer}.graph-node rect{fill:#fff8f2;stroke:#e88351;stroke-width:2}.graph-node:hover rect,.graph-node.active rect{fill:#ffe4d4;stroke:#c74918;stroke-width:3}.graph-node text{font-size:13px;fill:var(--ink);font-weight:700}.graph-node .caption{font-size:11px;fill:var(--muted);font-weight:400}#detail{background:#f4f7fa;border-radius:10px;padding:12px;min-height:122px;white-space:pre-wrap}.ask{margin-top:18px}.ask textarea{width:100%;min-height:72px;resize:vertical;border:1px solid var(--line);border-radius:8px;padding:9px;font:inherit}.ask button{margin-top:8px;background:var(--accent);border-color:var(--accent);color:#fff;font-weight:700}.answer{margin-top:10px;padding:11px;background:#fff7ef;border-left:3px solid var(--accent);white-space:pre-wrap}.fidelity{margin-top:16px;color:var(--muted);font-size:12px}@media(max-width:980px){.learning-grid{grid-template-columns:1fr}.full-shell{grid-template-columns:220px 1fr}.right{grid-column:1/-1;border-left:0;border-top:1px solid var(--line)}}@media(max-width:650px){.topbar{align-items:start;flex-direction:column}.full-shell{display:block}.left{border-right:0;border-bottom:1px solid var(--line)}}
</style></head><body><main class="app"><header class="topbar"><div><div class="eyebrow">Offline source-backed guide</div><div class="brand">Codebase Atlas</div></div><nav class="mode-switch" aria-label="Chế độ Atlas"><button data-mode="learner">Học codebase</button><button data-mode="full">Full codebase</button><button data-audience="engineer">Engineer mode</button></nav></header><section class="view learner-shell" id="learner-view"><div class="learner-hero"><div class="eyebrow">Bắt đầu ở đây</div><h1>Ứng dụng này làm gì?</h1><p class="lead" id="overview"></p><p class="evidence-note">Đây là tổng quan cấu trúc từ mã nguồn cục bộ. Các khối bên dưới được nhóm theo tên và đường dẫn tệp; Atlas không tự khẳng định nghiệp vụ mà mã nguồn chưa chứng minh.</p></div><div class="blocks" id="blocks">__BLOCK_CARDS__</div><div class="learning-grid"><section class="panel"><h2>Lộ trình đọc nhanh</h2><div class="path-step"><span class="step-number">1</span><div><strong>Bắt đầu từ tệp được kết nối nhiều nhất.</strong><br><span id="start-file"></span></div></div><div class="path-step"><span class="step-number">2</span><div><strong>Theo dấu liên kết.</strong><br>“Tệp này dùng tệp kia” là cách nói dễ hiểu của <em>import</em>.</div></div><div class="path-step"><span class="step-number">3</span><div><strong>Mở Full codebase khi cần.</strong><br>Xem toàn bộ tệp và các liên kết nội bộ trong một bản đồ.</div></div></section><section class="panel"><h2>Hỏi nhanh</h2><div class="sample-questions"><button data-question="App này làm gì?">App này làm gì?</button><button data-question="Dữ liệu đi qua đâu?">Dữ liệu đi qua đâu?</button><button data-question="Tôi nên đọc file nào trước?">Tôi nên đọc file nào trước?</button></div><div class="answer" id="learner-answer">Chọn một câu hỏi mẫu để bắt đầu. Câu trả lời chỉ dùng bằng chứng từ lần quét cục bộ.</div><p class="glossary"><strong>Function</strong> = một thao tác chương trình có thể làm.<br><strong>Import</strong> = tệp này dùng tệp kia.</p></section></div></section><section class="view full-shell" id="full-view"><aside class="left"><div class="eyebrow">Toàn bộ mã nguồn</div><h2>Modules</h2><div class="meta" id="module-count"></div><div id="module-list">__SIDEBAR_NODES__</div></aside><section class="canvas"><header class="canvas-head"><div><div class="eyebrow">Full codebase</div><h2>Internal import map</h2><div class="meta" id="graph-stats"></div></div></header><div class="graph-wrap"><svg class="graph" viewBox="0 0 __WIDTH__ __HEIGHT__" role="img" aria-label="Full codebase relationship graph"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#93a0aa"/></marker></defs>__EDGES____NODES__</svg></div></section><aside class="right"><div class="eyebrow">Giải thích</div><div class="toggle"><button data-audience="learner">Learner</button><button data-audience="engineer">Engineer</button></div><h2 id="detail-title">Chọn một tệp</h2><div id="detail">Chọn một tệp trong danh sách hoặc trên bản đồ để xem bằng chứng từ mã nguồn.</div><div class="ask"><div class="eyebrow">Ask the Atlas</div><textarea id="question" placeholder="App này làm gì? Tệp nào dùng tệp nào?"></textarea><button id="ask-button">Trả lời từ bằng chứng mã nguồn</button><div class="answer" id="answer">Câu trả lời trích từ khai báo hoặc import tìm thấy trong lần quét cục bộ.</div></div><div class="fidelity" id="fidelity"></div></aside></section></main><script>
const DATA=__DATA__;let audience=DATA.defaultAudience;let mode='learner';const byId=Object.fromEntries(DATA.atlas.nodes.map(n=>[n.id,n]));const symbols=DATA.report.symbols;
document.getElementById('overview').textContent=DATA.learning.overview;document.getElementById('start-file').textContent=DATA.learning.start_file?`Gợi ý: ${DATA.learning.start_file} (dựa trên số liên kết/khai báo đã quét).`:'Không có tệp mã nguồn được hỗ trợ để đề xuất.';document.getElementById('graph-stats').textContent=`${DATA.atlas.nodes.length} tệp · ${DATA.atlas.edges.length} liên kết import nội bộ`;document.getElementById('module-count').textContent=`Hiển thị đủ ${DATA.atlas.nodes.length} tệp đã quét`;document.getElementById('fidelity').textContent=DATA.report.fidelity;
function setMode(next){mode=next;document.getElementById('learner-view').classList.toggle('active',mode==='learner');document.getElementById('full-view').classList.toggle('active',mode==='full');document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));}
function setAudience(next){audience=next;document.querySelectorAll('[data-audience]').forEach(b=>b.classList.toggle('active',b.dataset.audience===audience));const active=document.querySelector('.node-list-item.active');if(active)selectNode(active.dataset.node);}
function words(value){return(value.toLowerCase().match(/[a-zà-ỹ_][a-z0-9à-ỹ_]*/g)||[]).filter(w=>!['what','is','the','how','do','imports','connect','explain','about','app','này','làm','gì','dữ','liệu','đi','qua','đâu','tôi','nên','đọc','file','nào','trước'].includes(w));}
function selectNode(id){const node=byId[id];if(!node)return;document.querySelectorAll('.node-list-item').forEach(el=>el.classList.toggle('active',el.dataset.node===id));document.querySelectorAll('.graph-node').forEach(el=>el.classList.toggle('active',el.dataset.node===id));const found=symbols.filter(s=>s.file===node.file).slice(0,8);const intro=audience==='learner'?`${node.file} là một phần của dự án. Function là một thao tác; import nghĩa là tệp này dùng tệp kia.`:`${node.file} chứa các khai báo triển khai và tham gia vào đồ thị import.`;document.getElementById('detail-title').textContent=node.file;document.getElementById('detail').textContent=intro+'\n\n'+(found.map(s=>`${s.kind} ${s.qualified_name} (${s.file}:${s.line})${s.docstring?' - '+s.docstring:''}`).join('\n')||'Không tìm thấy khai báo được hỗ trợ trong tệp này.');}
function questionAnswer(question){const q=question.toLowerCase();if(/app.*làm gì|what.*app.*do|ứng dụng.*làm gì/.test(q))return DATA.learning.overview+'\n\nBằng chứng: số tệp, khai báo và import được quét cục bộ.';if(/dữ liệu|data/.test(q)){const block=DATA.learning.blocks.find(b=>b.id==='data');return block?`Khối Dữ liệu có ${block.files.length} tệp: ${block.files.slice(0,8).join(', ')}. Đây là nhóm theo tên/đường dẫn, không phải suy đoán luồng nghiệp vụ.\n\nBằng chứng: ${block.files.slice(0,8).join(', ')}`:'Lần quét không thấy tệp có tên/đường dẫn gợi ý phần dữ liệu. Hãy mở Full codebase để xem mọi liên kết import đã chứng minh.';}if(/đọc file nào|read.*file.*first|bắt đầu/.test(q)){return DATA.learning.start_file?`Nên bắt đầu với ${DATA.learning.start_file}, vì nó có nhiều liên kết hoặc khai báo nhất trong lần quét.\n\nBằng chứng: đồ thị import và khai báo cục bộ.`:'Không có tệp mã nguồn được hỗ trợ để đề xuất.';}if(/depend|import|relationship|connect|liên kết|tệp nào dùng/.test(q)){const edges=DATA.atlas.edges.slice(0,8);return edges.length?edges.map(e=>`${e.source}:${e.line} dùng ${e.target}`).join('\n')+'\n\nBằng chứng: local import scan.':'Không tìm thấy liên kết import nội bộ trong lần quét.';}const query=words(question);const matches=symbols.map(s=>({s,score:query.reduce((n,w)=>n+Number((s.name+' '+s.qualified_name+' '+s.file).toLowerCase().includes(w)),0)})).filter(x=>x.score).sort((a,b)=>b.score-a.score).slice(0,4);return matches.length?matches.map(({s})=>audience==='learner'?`${s.qualified_name} là ${s.kind}, một khối/thao tác có tên trong chương trình. Bằng chứng: ${s.file}:${s.line}`:`${s.qualified_name} được khai báo là ${s.kind}. Bằng chứng: ${s.file}:${s.line}`).join('\n\n'):'Không tìm thấy khai báo khớp. Hãy thử đúng tên tệp, class hoặc function.';}
function answer(){const q=document.getElementById('question').value.trim();document.getElementById('answer').textContent=q?questionAnswer(q):'Hãy hỏi về tệp, class, function hoặc liên kết import.';}
document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>setMode(button.dataset.mode)));document.querySelectorAll('[data-audience]').forEach(button=>button.addEventListener('click',()=>{setAudience(button.dataset.audience);setMode('full');}));document.querySelectorAll('[data-node]').forEach(el=>el.addEventListener('click',()=>selectNode(el.dataset.node)));document.querySelectorAll('[data-block]').forEach(button=>button.addEventListener('click',()=>{const block=DATA.learning.blocks.find(item=>item.id===button.dataset.block);document.querySelectorAll('[data-block]').forEach(item=>item.classList.toggle('active',item===button));document.getElementById('learner-answer').textContent=`${block.label}: ${block.plain_language}\n\nTệp có bằng chứng trong nhóm này: ${block.files.slice(0,10).join(', ')}${block.files.length>10?' …':''}`;}));document.querySelectorAll('[data-question]').forEach(button=>button.addEventListener('click',()=>{document.getElementById('learner-answer').textContent=questionAnswer(button.dataset.question);}));document.getElementById('ask-button').addEventListener('click',answer);setMode('learner');setAudience(audience);
</script></body></html>"""
    bridge_script = r"""
const BRIDGE=DATA.bridge;let bridgeReady=false;
const bridgeStyle=document.createElement('style');bridgeStyle.textContent='.ai-source{margin:10px 0;padding:9px 10px;border-radius:8px;background:#edf6ef;color:#245c35;font-size:13px}.ai-source.local{background:#f4f2ee;color:#5d5a53}';document.head.appendChild(bridgeStyle);
function addAiSource(answerId){const answer=document.getElementById(answerId);const source=document.createElement('div');source.className='ai-source local';source.dataset.aiSource='';source.textContent='Nguồn trả lời: quét mã nguồn cục bộ.';answer.parentNode.insertBefore(source,answer);}
addAiSource('learner-answer');addAiSource('answer');
function setAiSource(message,isBridge){document.querySelectorAll('[data-ai-source]').forEach(el=>{el.textContent=message;el.classList.toggle('local',!isBridge);});}
async function checkBridge(){if(!BRIDGE.detected){setAiSource('Nguồn trả lời: quét mã nguồn cục bộ.',false);return false;}setAiSource(`Đang kiểm tra ${BRIDGE.name}…`,false);try{const response=await fetch(BRIDGE.health_url,{method:'GET'});bridgeReady=response.ok;}catch(error){bridgeReady=false;}setAiSource(bridgeReady?`Nguồn AI: ${BRIDGE.name} (cục bộ, đang kết nối).`:`Nguồn trả lời: quét mã nguồn cục bộ. ${BRIDGE.name} chưa chạy.`,bridgeReady);return bridgeReady;}
function bridgeContext(){const files=DATA.atlas.nodes.slice(0,100).map(node=>`${node.file} (${node.symbols} declarations)`).join('\n');const links=DATA.atlas.edges.slice(0,120).map(edge=>`${edge.source}:${edge.line} imports ${edge.target}`).join('\n');return `Codebase root: ${DATA.report.root}\nStructural scan overview: ${DATA.learning.overview}\nFiles:\n${files}\nInternal imports:\n${links}`;}
async function answerWithPreferredSource(question){if(!bridgeReady)await checkBridge();if(!bridgeReady)return questionAnswer(question);try{const response=await fetch(BRIDGE.completion_url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:BRIDGE.model,messages:[{role:'system',content:'You are a codebase learning assistant. Answer in Vietnamese. Use only the supplied structural source evidence; state limits when evidence is insufficient. Explain simply for a learner and cite file:line when an import is available.'},{role:'user',content:`Question: ${question}\n\n${bridgeContext()}`}],temperature:0.2,stream:false})});const payload=await response.json();const text=payload&&payload.choices&&payload.choices[0]&&payload.choices[0].message&&payload.choices[0].message.content;if(!response.ok||!text)throw new Error('Bridge returned no answer.');setAiSource(`Nguồn AI: ${BRIDGE.name} (cục bộ).`,true);return text.trim();}catch(error){bridgeReady=false;setAiSource(`Nguồn trả lời: quét mã nguồn cục bộ. ${BRIDGE.name} không phản hồi.`,false);return questionAnswer(question);}}
document.querySelectorAll('[data-question]').forEach(button=>button.addEventListener('click',async()=>{const answer=document.getElementById('learner-answer');answer.textContent='Đang trả lời…';answer.textContent=await answerWithPreferredSource(button.dataset.question);}));
document.getElementById('ask-button').addEventListener('click',async()=>{const question=document.getElementById('question').value.trim();if(!question)return;const answer=document.getElementById('answer');answer.textContent='Đang trả lời…';answer.textContent=await answerWithPreferredSource(question);});
checkBridge();
"""
    template = template.replace("setMode('learner');setAudience(audience);", "setMode('learner');setAudience(audience);" + bridge_script)
    return (
        template.replace("__TITLE__", title)
        .replace("__BLOCK_CARDS__", block_cards)
        .replace("__SIDEBAR_NODES__", sidebar_nodes)
        .replace("__WIDTH__", str(atlas["width"]))
        .replace("__HEIGHT__", str(atlas["height"]))
        .replace("__EDGES__", edge_svg)
        .replace("__NODES__", node_svg)
        .replace("__DATA__", data)
    )


def write_atlas(project_dir: str | Path, output_path: str | Path, audience: str = "learner") -> Path:
    from excaliflow.explorer import inspect_codebase

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_atlas_html(inspect_codebase(project_dir), audience), encoding="utf-8")
    return output
