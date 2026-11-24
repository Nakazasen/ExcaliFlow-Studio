import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from excaliflow.domain_graph import build_workspace_knowledge_graph, export_excalidraw_scene
from excaliflow.evidence_atlas import build_evidence_atlas_html
from excaliflow.explorer import inspect_codebase
from excaliflow.knowledge import load_evidence_graph, validate_evidence_graph


ROOT = Path(__file__).resolve().parents[1]


def _load_generator():
    path = ROOT / "scripts" / "generate_diagram.py"
    spec = importlib.util.spec_from_file_location("generate_diagram", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class DomainGraphAndVbaCSharpTests(unittest.TestCase):
    def _create_mixed_workspace(self, root: Path) -> None:
        (root / "docs").mkdir(parents=True, exist_ok=True)
        (root / "src").mkdir(parents=True, exist_ok=True)
        (root / "data").mkdir(parents=True, exist_ok=True)
        (root / "docs" / "Cuon_01.md").write_text(
            "# Cuon 01 Architecture\n\nUses [CommandAdapter](../src/CommandAdapter.cs) and [Macro](./Macro.bas).\n",
            encoding="utf-8",
        )
        (root / "src" / "CommandAdapter.cs").write_text(
            "using System;\nnamespace AthenaBridge {\n  public class CommandAdapter {\n    public int SendDinq(string cmd) { return 0; }\n  }\n}\n",
            encoding="utf-8",
        )
        (root / "docs" / "Macro.bas").write_text(
            'Attribute VB_Name = "AthenaMacro"\nPublic Declare PtrSafe Function SendUdp Lib "ws2_32.dll" () As Long\nPublic Sub RunDinq()\nEnd Sub\n',
            encoding="utf-8",
        )
        (root / "data" / "master.csv").write_text("StepId,CmdName,ComType\n1,DINQ,TCPIP\n", encoding="utf-8")
        (root / "data" / "seq.json").write_text('{"steps":[{"cmd":"DINQ"}]}', encoding="utf-8")
        (root / "data" / "cfg.ini").write_text("[Network]\nPort=5000\n", encoding="utf-8")

    def test_explorer_and_generator_extract_csharp_and_vba_symbols(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_mixed_workspace(root)
            report = inspect_codebase(root)
            self.assertIn("C#", report["languages"])
            self.assertIn("VBA", report["languages"])
            names = {sym["name"] for sym in report["symbols"]}
            self.assertIn("CommandAdapter", names)
            self.assertIn("SendDinq", names)
            self.assertIn("AthenaMacro", names)
            self.assertIn("RunDinq", names)
            gen = _load_generator()
            lang_scan = gen.scan_language_sources(root)
            self.assertTrue({"C#", "VBA"}.issubset(lang_scan["languages"]))

    def test_workspace_knowledge_graph_and_excalidraw_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._create_mixed_workspace(root)
            graph = build_workspace_knowledge_graph(root, max_nodes=60)
            validate_evidence_graph(graph)
            self.assertLessEqual(len(graph["nodes"]), 60)
            node_types = {node["type"] for node in graph["nodes"]}
            self.assertIn("answer", node_types)
            self.assertIn("chunk", node_types)
            self.assertIn("document", node_types)
            self.assertIn("code", node_types)

            scene = export_excalidraw_scene(graph, lang="vi")
            self.assertEqual(scene["type"], "excalidraw")
            self.assertEqual(scene["version"], 2)
            self.assertGreater(len(scene["elements"]), 2)

            ja_html = build_evidence_atlas_html(graph, lang="ja")
            self.assertIn("エビデンス", ja_html)
            self.assertIn("ポータルで開く", ja_html)
            self.assertIn("excaliflow:open-location", ja_html)
            self.assertIn('id="atlas-zoom-badge"', ja_html)
            self.assertNotIn("https://", ja_html)

    def test_cli_direct_invocation_without_pythonpath_scans_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ws"
            root.mkdir()
            self._create_mixed_workspace(root)
            out_graph = Path(tmp) / "domain-graph.json"
            out_atlas = Path(tmp) / "domain-atlas.html"
            out_excalidraw = Path(tmp) / "domain.excalidraw"
            env = {k: v for k, v in os.environ.items() if k.upper() != "PYTHONPATH"}
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "src" / "excaliflow" / "cli.py"),
                    "knowledge",
                    "scan",
                    "--dir",
                    str(root),
                    "--lang",
                    "ja",
                    "--max-nodes",
                    "40",
                    "--out",
                    str(out_graph),
                    "--atlas-out",
                    str(out_atlas),
                    "--excalidraw",
                    str(out_excalidraw),
                ],
                cwd=tmp,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(out_graph.is_file())
            self.assertTrue(out_atlas.is_file())
            self.assertTrue(out_excalidraw.is_file())
            loaded = load_evidence_graph(out_graph)
            self.assertGreaterEqual(len(loaded["nodes"]), 4)
            scene = json.loads(out_excalidraw.read_text(encoding="utf-8"))
            self.assertEqual(scene["type"], "excalidraw")
            self.assertIn("excaliflow:open-location", out_atlas.read_text(encoding="utf-8"))

    def test_scans_yaml_toml_sql_and_proportional_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            for i in range(25):
                (root / "docs" / f"doc_{i:02d}.md").write_text(f"# Doc {i}\nBody {i}\n", encoding="utf-8")
            (root / "config.yaml").write_text("service: excaliflow\nport: 8788\n", encoding="utf-8")
            (root / "settings.toml").write_text("[runtime]\nmode = 'offline'\n", encoding="utf-8")
            (root / "schema.sql").write_text("CREATE TABLE IF NOT EXISTS users (id INT PRIMARY KEY);\n", encoding="utf-8")
            (root / "app.py").write_text("def run_app():\n    return 1\n", encoding="utf-8")

            graph = build_workspace_knowledge_graph(root, max_nodes=35)
            validate_evidence_graph(graph)
            locations = {node.get("properties", {}).get("location") for node in graph["nodes"]}
            self.assertIn("app.py", locations)
            self.assertTrue(any(loc in {"config.yaml", "settings.toml", "schema.sql"} for loc in locations if loc))
            self.assertTrue(any(node["type"] == "code" and node["label"] == "users" for node in graph["nodes"]))

    def test_internal_code_depends_on_and_excalidraw_v2_bindings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "helper.py").write_text("def compute():\n    return 42\n", encoding="utf-8")
            (root / "main.py").write_text("from helper import compute\n\ndef entry():\n    return compute()\n", encoding="utf-8")

            graph = build_workspace_knowledge_graph(root, max_nodes=40)
            validate_evidence_graph(graph)
            dep_edges = [e for e in graph["edges"] if e["relation"] == "depends_on"]
            self.assertTrue(dep_edges)
            self.assertEqual(dep_edges[0]["receipts"][0]["location"], "main.py:1")

            scene = export_excalidraw_scene(graph, lang="en")
            arrows = [el for el in scene["elements"] if el["type"] == "arrow"]
            rects = {el["id"]: el for el in scene["elements"] if el["type"] == "rectangle"}
            self.assertTrue(arrows)
            first_arrow = arrows[0]
            self.assertIn("startBinding", first_arrow)
            self.assertIn("endBinding", first_arrow)
            src_rect = rects[first_arrow["startBinding"]["elementId"]]
            self.assertTrue(any(b["id"] == first_arrow["id"] for b in src_rect["boundElements"]))
            arrow_labels = [el for el in scene["elements"] if el["type"] == "text" and el.get("containerId") == first_arrow["id"]]
            self.assertEqual(len(arrow_labels), 1)

    def test_cli_knowledge_scan_include_glob_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ws"
            root.mkdir()
            (root / "keep.py").write_text("def kept():\n    return 1\n", encoding="utf-8")
            (root / "ignore.ini").write_text("[Section]\nk=1\n", encoding="utf-8")
            out_graph = Path(tmp) / "filtered.json"
            env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "excaliflow.cli",
                    "knowledge",
                    "scan",
                    "--dir",
                    str(root),
                    "--include",
                    "*.py",
                    "--out",
                    str(out_graph),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            loaded = load_evidence_graph(out_graph)
            locs = {n.get("properties", {}).get("location") for n in loaded["nodes"]}
            self.assertIn("keep.py", locs)
            self.assertNotIn("ignore.ini", locs)
