import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_diagram.py"
SPEC = importlib.util.spec_from_file_location("excaliflow_generator", SCRIPT)
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


class ExcaliFlowTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
