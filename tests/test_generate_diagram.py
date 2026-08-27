import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch, MagicMock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_diagram.py"
SPEC = importlib.util.spec_from_file_location("excaliflow_generator", SCRIPT)
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


class ExcaliFlowTests(unittest.TestCase):
    def test_graphify_package_constraint_matches_runtime_policy(self):
        pyproject = tomllib.loads((SCRIPT.parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertIn(
            f"graphifyy{generator.GRAPHIFY_VERSION_SPEC}",
            pyproject["project"]["dependencies"],
        )

    def test_graphify_compatible_patch_version_is_accepted(self):
        result = MagicMock(returncode=0, stdout="graphify 0.9.50\n", stderr="")
        with patch("subprocess.run", return_value=result):
            compatible, version = generator.graphify_version_status("graphify")
        self.assertTrue(compatible)
        self.assertEqual(version, "0.9.50")

    def test_graphify_next_minor_is_rejected_and_strict_fails_closed(self):
        result = MagicMock(returncode=0, stdout="graphify 0.10.0\n", stderr="")
        with patch("subprocess.run", return_value=result):
            self.assertIsNone(generator.compatible_graphify_binary("graphify"))
            with self.assertRaisesRegex(RuntimeError, "Fail-Closed"):
                generator.compatible_graphify_binary("graphify", strict=True)

    def test_language_aware_scan_detects_supported_languages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "app.ts").write_text('import { helper } from "./helper"; export function route() {}', encoding="utf-8")
            (root / "main.go").write_text('package main\nfunc Run() {}', encoding="utf-8")
            (root / "lib.rs").write_text('use crate::engine::run;\nstruct Engine {}', encoding="utf-8")
            result = generator.scan_language_sources(root)
            self.assertEqual(result["provenance"], "language_aware")
            self.assertTrue({"TypeScript", "Go", "Rust"}.issubset(result["languages"]))
            self.assertGreaterEqual(len(result["symbols"]), 3)

    def test_language_scan_prunes_dependencies_and_uses_stable_external_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "app.ts").write_text(
                'import { helper } from "shared-lib"; export function route() {}', encoding="utf-8"
            )
            ignored = root / "node_modules" / "large-package"
            ignored.mkdir(parents=True)
            (ignored / "noise.ts").write_text("export function noise() {}", encoding="utf-8")
            analysis = generator.scan_language_sources(root)
            self.assertFalse(any(item["name"] == "noise" for item in analysis["symbols"]))
            first = generator.generate_mermaid_from_language_analysis({"root_name": "demo"}, analysis)
            second = generator.generate_mermaid_from_language_analysis({"root_name": "demo"}, analysis)
            self.assertEqual(first, second)
            self.assertIn("EXT_E2EE005CED", first["source_analysis"]["code"])

    def test_python_ast_does_not_duplicate_methods_as_top_level_functions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text(
                "class Service:\n    def run(self):\n        return True\n\ndef main():\n    return Service().run()\n",
                encoding="utf-8",
            )
            analysis = generator.scan_python_ast(root)
            self.assertIn("Service", analysis["classes"])
            self.assertIn("main", analysis["functions"])
            self.assertNotIn("run", analysis["functions"])

    def test_offline_viewer_and_native_scene(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text("def run():\n    return 1\n", encoding="utf-8")
            viewer, scene = root / "viewer.html", root / "viewer.excalidraw"
            generator.generate_html_file(root, viewer, scene)
            html = viewer.read_text(encoding="utf-8")
            payload = json.loads(scene.read_text(encoding="utf-8"))
            self.assertNotIn('<script src="http', html)
            self.assertIn("mermaid", html)
            self.assertIn("requestAnimationFrame(() => requestAnimationFrame(fitToScreen))", html)
            self.assertIn("#diagram-output > svg", html)
            self.assertEqual(payload["type"], "excalidraw")
            self.assertGreater(len(payload["elements"]), 0)

    def test_existing_hook_is_preserved_without_force(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            hooks = root / ".git" / "hooks"
            hooks.mkdir(parents=True)
            hook = hooks / "post-commit"
            hook.write_text("#!/bin/sh\necho user-hook\n", encoding="utf-8")
            self.assertFalse(generator.install_git_hooks(root))
            self.assertEqual(hook.read_text(encoding="utf-8"), "#!/bin/sh\necho user-hook\n")

    def test_editorial_architecture_svg_is_offline_and_uses_slide_canvas(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            root.mkdir()
            (root / "main.py").write_text("def publish():\n    return True\n", encoding="utf-8")
            output = root / "architecture.svg"
            generator.generate_editorial_file(root, output, visual_type="architecture", canvas="slide")
            svg = output.read_text(encoding="utf-8")
            document = ET.fromstring(svg)
            self.assertEqual(document.attrib["viewBox"], "0 0 1600 900")
            self.assertIn("Grammar: architecture", svg)
            self.assertIn("Source: analysis", svg)
            self.assertNotIn("<script", svg)
            self.assertNotIn("<link", svg)
            self.assertNotIn("url(http", svg)

    def test_editorial_grammar_briefs_render_parseable_svg(self):
        cases = {
            "sankey": {
                "title": "Qualified funnel",
                "type": "sankey",
                "data": {
                    "nodes": [{"id": "lead", "label": "Leads"}, {"id": "demo", "label": "Demos"}, {"id": "won", "label": "Won"}],
                    "links": [{"source": "lead", "target": "demo", "value": 80}, {"source": "demo", "target": "won", "value": 30}],
                },
            },
            "wardley": {
                "title": "Platform evolution",
                "type": "wardley",
                "data": {"components": [{"name": "Need", "evolution": 0.1, "value": 0.9}, {"name": "Platform", "evolution": 0.8, "value": 0.35}]},
            },
            "journey": {
                "title": "Member journey",
                "type": "journey",
                "data": {"stages": [{"name": "Discover", "action": "Read", "sentiment": 1}, {"name": "Decide", "action": "Compare", "sentiment": -1}, {"name": "Adopt", "action": "Start", "sentiment": 2}]},
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for visual_type, brief in cases.items():
                output = root / f"{visual_type}.svg"
                generator.generate_editorial_file(root, output, visual_type=visual_type, visual_data=brief, canvas="document")
                svg = output.read_text(encoding="utf-8")
                ET.fromstring(svg)
                self.assertIn(f"Grammar: {visual_type}", svg)
                self.assertIn(brief["title"], svg)
                self.assertNotIn("<script", svg)
                self.assertNotIn("<link", svg)
                self.assertNotIn("url(http", svg)

    def test_invalid_editorial_briefs_fail_before_output_is_written(self):
        invalid_briefs = [
            ("sankey", {"title": "Bad Sankey", "type": "sankey", "data": {"nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "links": [{"source": "a", "target": "missing", "value": 1}]}}),
            ("wardley", {"title": "Bad Wardley", "type": "wardley", "data": {"components": [{"name": "Oops", "evolution": 1.1, "value": 0.5}]}}),
            ("journey", {"title": "Bad Journey", "type": "journey", "data": {"stages": [{"name": "Only", "action": "Wait", "sentiment": 0}]}}),
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for visual_type, brief in invalid_briefs:
                output = root / f"{visual_type}.svg"
                with self.assertRaises(generator.EditorialValidationError):
                    generator.generate_editorial_file(root, output, visual_type=visual_type, visual_data=brief)
                self.assertFalse(output.exists())

    def test_editorial_html_wraps_svg_without_remote_resources(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            brief = {
                "title": "Journey summary",
                "subtitle": "A short factual summary",
                "type": "journey",
                "data": {"stages": [{"name": "Start", "action": "Open", "sentiment": 0}, {"name": "Finish", "action": "Share", "sentiment": 2}]},
            }
            output = root / "journey.html"
            generator.generate_editorial_file(root, output, visual_type="journey", visual_data=brief, canvas="social")
            html = output.read_text(encoding="utf-8")
            self.assertIn("<svg", html)
            self.assertIn("Grammar: journey", html)
            self.assertNotIn("<script src=", html)
            self.assertNotIn("<link href=", html)
            self.assertNotIn("url(http", html)

    def test_editorial_cli_accepts_json_brief(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            brief_path, output = root / "sankey.json", root / "sankey.svg"
            brief_path.write_text(json.dumps({
                "title": "CLI funnel",
                "type": "sankey",
                "data": {
                    "nodes": [{"id": "visit", "label": "Visits"}, {"id": "buy", "label": "Purchases"}],
                    "links": [{"source": "visit", "target": "buy", "value": 12}],
                },
            }), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(SCRIPT), "--editorial-out", str(output), "--visual-type", "sankey",
                "--visual-data", str(brief_path), "--canvas", "social",
            ], cwd=root, text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertIn("Canvas: social", output.read_text(encoding="utf-8"))

    def test_business_report_grammars_render_and_validate_positions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for visual_type in ("kpi", "funnel", "timeline", "process", "quadrant", "matrix", "risk"):
                items = [{"label": "Revenue", "value": 42}, {"label": "Plan", "value": 60}]
                if visual_type in {"quadrant", "matrix", "risk"}:
                    items = [{"label": "Priority", "value": 42, "x": 0.7, "y": 0.8}]
                brief = {"title": f"{visual_type} report", "type": visual_type, "data": {"items": items}}
                output = root / f"{visual_type}.svg"
                generator.generate_editorial_file(root, output, visual_type=visual_type, visual_data=brief, canvas="slide")
                ET.fromstring(output.read_text(encoding="utf-8"))
            invalid = {"title": "Bad", "type": "risk", "data": {"items": [{"label": "Bad", "value": 1, "x": 2, "y": 0.5}]}}
            with self.assertRaises(generator.EditorialValidationError):
                generator.generate_editorial_file(root, root / "bad.svg", visual_type="risk", visual_data=invalid)

    def test_smart_multiline_text_rendering(self):
        # 1. Test smart truncation preserves word boundaries
        vietnamese_text = "Hệ thống xác thực và phân quyền người dùng tập trung"
        truncated = generator.smart_truncate_text(vietnamese_text, 30)
        self.assertFalse(truncated.endswith("quyề…"))
        self.assertTrue(truncated.endswith("…"))
        self.assertLessEqual(len(truncated), 31)

        # 2. Test multi-line SVG rendering with <title> tooltip
        svg_chunk, count = generator.render_editorial_multiline_svg_with_count(
            "Cổng kết nối thanh toán trực tuyến đa kênh an toàn",
            x=100.0, y=200.0, line_limit=25, max_lines=3, line_height=18.0, anchor="end"
        )
        self.assertGreater(count, 1)
        self.assertIn("<title>Cổng kết nối thanh toán trực tuyến đa kênh an toàn</title>", svg_chunk)
        self.assertIn("<tspan", svg_chunk)
        self.assertIn('text-anchor="end"', svg_chunk)

        # 3. Test end-to-end Wardley map with long Vietnamese names and notes
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wardley_brief = {
                "title": "Bản đồ tiến hóa kiến trúc hệ thống thương mại điện tử đa quốc gia",
                "type": "wardley",
                "data": {
                    "components": [
                        {
                            "name": "Hạ tầng máy chủ đám mây & Kubernetes Cluster tự động co giãn",
                            "evolution": 0.85,
                            "value": 0.2,
                            "note": "Cung cấp nền tảng container hóa chuẩn quốc tế với độ sẵn sàng cao 99.99%",
                        },
                        {
                            "name": "Thuật toán gợi ý sản phẩm cá nhân hóa bằng học máy chuyên sâu",
                            "evolution": 0.25,
                            "value": 0.9,
                            "note": "Mô hình transformer phân tích thói quen thời gian thực",
                        },
                    ]
                },
            }
            output = root / "wardley_vn.svg"
            generator.generate_editorial_file(root, output, visual_type="wardley", visual_data=wardley_brief, canvas="slide")
            svg_content = output.read_text(encoding="utf-8")
            ET.fromstring(svg_content)
            self.assertIn("Hạ tầng máy chủ", svg_content)
            self.assertIn("Kubernetes Cluster", svg_content)
            self.assertIn("text-anchor=\"end\"", svg_content)
            self.assertIn("<title>Hạ tầng máy chủ đám mây", svg_content)

    def test_stale_graph_detection_triggers_graphify_update(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src_file = root / "service.py"
            src_file.write_text("class PaymentProcessor:\n    def process(self): pass\n", encoding="utf-8")
            
            g_out = root / "graphify-out" / "graph.json"
            g_out.parent.mkdir(parents=True, exist_ok=True)
            g_out.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
            
            # Set graph.json mtime in the past, and src_file mtime in the future (staleness)
            os.utime(g_out, (1000.0, 1000.0))
            os.utime(src_file, (2000.0, 2000.0))
            
            with patch("shutil.which", return_value="/fake/bin/graphify"), \
                 patch.object(generator, "compatible_graphify_binary", return_value="/fake/bin/graphify"), \
                 patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
                kg_type, kg_path = generator.find_knowledge_graph(root, auto_trigger=True)
                
                self.assertEqual(kg_type, "graphify")
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                self.assertEqual(call_args[0], "/fake/bin/graphify")
                self.assertEqual(call_args[1], "extract")
                self.assertIn("--code-only", call_args)

    def test_fresh_graph_does_not_retrigger_graphify(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src_file = root / "service.py"
            src_file.write_text("class PaymentProcessor:\n    def process(self): pass\n", encoding="utf-8")
            
            g_out = root / "graphify-out" / "graph.json"
            g_out.parent.mkdir(parents=True, exist_ok=True)
            g_out.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
            
            # Set graph.json newer than src_file (fresh)
            os.utime(src_file, (1000.0, 1000.0))
            os.utime(g_out, (2000.0, 2000.0))
            
            with patch("shutil.which", return_value="/fake/bin/graphify"), \
                 patch("subprocess.run") as mock_run:
                kg_type, kg_path = generator.find_knowledge_graph(root, auto_trigger=True)
                
                self.assertEqual(kg_type, "graphify")
                self.assertEqual(kg_path, g_out)
                mock_run.assert_not_called()

    def test_graphify_error_reporting_not_silenced(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Graphify syntax extraction error")
                success = generator.run_graphify_extract(root, "graphify")
                self.assertFalse(success)

    def test_git_hooks_install_post_commit_cleanly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git" / "hooks").mkdir(parents=True)
            
            installed = generator.install_git_hooks(root)
            self.assertTrue(installed)
            
            post_commit = root / ".git" / "hooks" / "post-commit"
            self.assertTrue(post_commit.is_file())
            
            post_text = post_commit.read_text(encoding="utf-8")
            self.assertIn("set -e", post_text)
            self.assertNotIn("graphify extract", post_text)
            self.assertIn("ExcaliFlow tu kiem tra phien ban", post_text)
            self.assertNotIn("|| true", post_text)
            self.assertNotIn("git add", post_text)

    def test_strict_mode_fail_closed_on_graphify_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src_file = root / "main.py"
            src_file.write_text("print('hello')", encoding="utf-8")
            
            with patch("shutil.which", return_value="/fake/bin/graphify"), \
                 patch.object(generator, "compatible_graphify_binary", return_value="/fake/bin/graphify"), \
                 patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Fatal graphify extraction error")
                with self.assertRaises(RuntimeError) as ctx:
                    generator.find_knowledge_graph(root, auto_trigger=True, strict=True)
                self.assertIn("Fail-Closed", str(ctx.exception))

    def test_strict_mode_fail_closed_on_missing_graph(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(RuntimeError) as ctx:
                generator.find_knowledge_graph(root, auto_trigger=False, strict=True)
            self.assertIn("Fail-Closed", str(ctx.exception))

    def test_strict_mode_fail_closed_on_stale_graph_without_graphify(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src_file = root / "app.py"
            src_file.write_text("def run(): pass\n", encoding="utf-8")
            
            g_out = root / "graphify-out" / "graph.json"
            g_out.parent.mkdir(parents=True, exist_ok=True)
            g_out.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
            
            # Make graph older than source
            os.utime(src_file, (2000.0, 2000.0))
            os.utime(g_out, (1000.0, 1000.0))
            
            with patch("shutil.which", return_value=None):
                with self.assertRaises(RuntimeError) as ctx:
                    generator.find_knowledge_graph(root, auto_trigger=True, strict=True)
                self.assertIn("Fail-Closed", str(ctx.exception))
                self.assertIn("Stale graph detected", str(ctx.exception))

    def test_strict_mode_fail_closed_on_stale_graph_with_auto_trigger_disabled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src_file = root / "app.py"
            src_file.write_text("def run(): pass\n", encoding="utf-8")
            
            g_out = root / "graphify-out" / "graph.json"
            g_out.parent.mkdir(parents=True, exist_ok=True)
            g_out.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
            
            # Make graph older than source
            os.utime(src_file, (2000.0, 2000.0))
            os.utime(g_out, (1000.0, 1000.0))
            
            with patch("shutil.which", return_value="/fake/bin/graphify"):
                with self.assertRaises(RuntimeError) as ctx:
                    generator.find_knowledge_graph(root, auto_trigger=False, strict=True)
                self.assertIn("Fail-Closed", str(ctx.exception))
                self.assertIn("Stale graph detected", str(ctx.exception))

    def test_strict_mode_fail_closed_on_nested_stale_graph_without_graphify(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src_file = root / "app.py"
            src_file.write_text("def run(): pass\n", encoding="utf-8")
            
            nested_g = root / "graphify-out" / "old-run" / "graph.json"
            nested_g.parent.mkdir(parents=True, exist_ok=True)
            nested_g.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
            
            # Make nested graph older than source
            os.utime(src_file, (2000.0, 2000.0))
            os.utime(nested_g, (1000.0, 1000.0))
            
            with patch("shutil.which", return_value=None):
                with self.assertRaises(RuntimeError) as ctx:
                    generator.find_knowledge_graph(root, auto_trigger=True, strict=True)
                self.assertIn("Fail-Closed", str(ctx.exception))
                self.assertIn("Stale graph detected", str(ctx.exception))

    def test_strict_mode_fail_closed_on_root_stale_graph_without_graphify(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src_file = root / "app.py"
            src_file.write_text("def run(): pass\n", encoding="utf-8")
            
            root_g = root / "graph.json"
            root_g.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
            
            # Make root graph older than source
            os.utime(src_file, (2000.0, 2000.0))
            os.utime(root_g, (1000.0, 1000.0))
            
            with patch("shutil.which", return_value=None):
                with self.assertRaises(RuntimeError) as ctx:
                    generator.find_knowledge_graph(root, auto_trigger=True, strict=True)
                self.assertIn("Fail-Closed", str(ctx.exception))
                self.assertIn("Stale graph detected", str(ctx.exception))

    def test_empty_graphify_out_directory_does_not_mask_root_graph(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            # Create an empty graphify-out folder
            (root / "graphify-out").mkdir()
            
            # Create valid graph.json at root
            root_g = root / "graph.json"
            root_g.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
            
            kg_type, kg_path = generator.find_knowledge_graph(root, auto_trigger=False, strict=True)
            self.assertEqual(kg_type, "graphify")
            self.assertEqual(kg_path, root_g)

    def test_strict_mode_fail_closed_on_stale_understand_graph(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src_file = root / "service.py"
            src_file.write_text("class Auth: pass\n", encoding="utf-8")
            
            u_dir = root / ".understand"
            u_dir.mkdir()
            u_graph = u_dir / "knowledge-graph.json"
            u_graph.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
            
            # Set understand graph older than source
            os.utime(src_file, (2000.0, 2000.0))
            os.utime(u_graph, (1000.0, 1000.0))
            
            with self.assertRaises(RuntimeError) as ctx:
                generator.find_knowledge_graph(root, auto_trigger=False, strict=True)
            self.assertIn("Fail-Closed: Stale Understand knowledge graph detected", str(ctx.exception))

    def test_strict_mode_fail_closed_when_graphify_succeeds_but_graph_remains_stale(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src_file = root / "app.py"
            src_file.write_text("def run(): pass\n", encoding="utf-8")
            
            g_out = root / "graphify-out" / "graph.json"
            g_out.parent.mkdir(parents=True, exist_ok=True)
            g_out.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
            
            # Set graph older than source
            os.utime(src_file, (2000.0, 2000.0))
            os.utime(g_out, (1000.0, 1000.0))
            
            # Mock subprocess.run to return returncode=0, but do NOT update file timestamp
            with patch("shutil.which", return_value="/fake/bin/graphify"), \
                 patch.object(generator, "compatible_graphify_binary", return_value="/fake/bin/graphify"), \
                 patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="Graphify finished with 0 errors", stderr="")
                with self.assertRaises(RuntimeError) as ctx:
                    generator.find_knowledge_graph(root, auto_trigger=True, strict=True)
                self.assertIn("Fail-Closed: Graphify reported success but output graph is still stale", str(ctx.exception))

    def test_compute_architecture_diff_detects_changes(self):
        old_analysis = {
            "symbols": [
                {"id": "s1", "name": "UserService", "file": "user.py"},
                {"id": "s2", "name": "LegacyAuth", "file": "auth_old.py"}
            ],
            "relations": [
                {"source": "user.py", "target": "LegacyAuth", "kind": "imports"}
            ]
        }
        new_analysis = {
            "symbols": [
                {"id": "s1", "name": "UserService", "file": "user.py"},
                {"id": "s3", "name": "OAuthProvider", "file": "oauth.py"}
            ],
            "relations": [
                {"source": "user.py", "target": "OAuthProvider", "kind": "imports"}
            ]
        }
        diff_res = generator.compute_architecture_diff(old_analysis, new_analysis)
        self.assertIn("architecture_diff", diff_res)
        diff_data = diff_res["architecture_diff"]
        self.assertIn("Architecture Diff (Before vs After)", diff_data["title"])
        self.assertEqual(diff_data["stats"]["added_nodes"], 1)
        self.assertEqual(diff_data["stats"]["removed_nodes"], 1)
        self.assertIn("[+] OAuthProvider", diff_data["code"])
        self.assertIn("[-] LegacyAuth", diff_data["code"])

    def test_html_template_contains_reach_tracing_and_flow_features(self):
        template = generator.HTML_TEMPLATE
        self.assertIn("reach-focused", template)
        self.assertIn("reach-upstream", template)
        self.assertIn("reach-downstream", template)
        self.assertIn("flow-animated", template)
        self.assertIn("export-card", template)
        self.assertIn("setupReachTracing", template)
        self.assertIn("excludeClass: 'panzoom-exclude'", template)
        self.assertIn("node.classList.add('panzoom-exclude')", template)
        self.assertIn("opacity: 0.34", template)
        self.assertIn("filter: none", template)
        self.assertIn("let qUpIndex = 0", template)
        self.assertIn("let qDownIndex = 0", template)
        self.assertNotIn("grayscale(95%) blur(0.4px) opacity(0.35)", template)
        self.assertNotIn("svgElement.addEventListener('pointerup'", template)
        self.assertIn("let renderGeneration = 0", template)
        self.assertIn("if (generation !== renderGeneration) return", template)
        self.assertIn("const nodeEntries = nodes.map", template)
        self.assertIn("const edgeContainers = Array.from", template)
        self.assertNotIn("g[class*=\"edge\"]", template)

    def test_generate_share_card_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text("class CoreApp:\n    pass\n", encoding="utf-8")
            out_card = root / "test-card.svg"
            card_path = generator.generate_share_card_file(str(root), str(out_card))
            self.assertTrue(card_path.is_file())
            content = card_path.read_text(encoding="utf-8")
            self.assertIn('viewBox="0 0 1200 630"', content)
            self.assertIn("EXCALIFLOW", content)

    def test_generate_html_file_with_diff_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text("class CoreApp:\n    pass\n", encoding="utf-8")
            old_graph = root / "old.json"
            old_graph.write_text(json.dumps({
                "symbols": [{"id": "s_old", "name": "OldModule", "file": "old.py"}],
                "relations": []
            }), encoding="utf-8")
            
            out_html = root / "viewer.html"
            generator.generate_html_file(str(root), str(out_html), auto_graphify=False, diff_target=str(old_graph))
            self.assertTrue(out_html.is_file())
            html_text = out_html.read_text(encoding="utf-8")
            self.assertIn("Architecture Diff", html_text)


if __name__ == "__main__":
    unittest.main()
