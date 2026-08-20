import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from excaliflow.atlas import build_atlas_html
from excaliflow.bridge import discover_ide_bridge
from excaliflow.explorer import answer_question, explain_codebase, inspect_codebase


ROOT = Path(__file__).resolve().parents[1]


class ExplorerTests(unittest.TestCase):
    def make_project(self, root: Path) -> None:
        (root / "service.py").write_text(
            'class Greeter:\n    """Formats a greeting for a person."""\n    def greet(self, name):\n        return f"Hello {name}"\n',
            encoding="utf-8",
        )
        (root / "app.py").write_text("from service import Greeter\n\ndef main():\n    return Greeter().greet('Ada')\n", encoding="utf-8")

    def test_learner_guide_and_symbol_answer_are_source_backed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project(root)
            report = inspect_codebase(root)
            guide = explain_codebase(report, "learner")
            answer = answer_question(report, "What is Greeter?", "learner")
            self.assertIn("Suggested reading order", guide)
            self.assertIn("service.py:1", answer)
            self.assertIn("named piece of the program", answer)

    def test_dependency_question_reports_import_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project(root)
            answer = answer_question(inspect_codebase(root), "How do the imports connect?", "engineer")
            self.assertIn("app.py:1", answer)
            self.assertIn("service", answer)

    def test_dependency_question_prioritises_project_relationships(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project(root)
            answer = answer_question(inspect_codebase(root), "How do the imports connect?", "engineer")
            self.assertLess(answer.index("`app.py:1`"), answer.index("## Fidelity"))

    def test_package_cli_writes_json_for_other_ai_tools(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project(root)
            output = root / "report.json"
            result = subprocess.run(
                [sys.executable, "-m", "excaliflow.cli", "explain", "--dir", str(root), "--format", "json", "--out", str(output)],
                cwd=ROOT,
                env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Wrote source-backed explain output", result.stdout)
            self.assertIn('"Greeter"', output.read_text(encoding="utf-8"))

    def test_symbol_containing_codebase_is_not_mistaken_for_an_overview_question(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scanner.py").write_text("def inspect_codebase():\n    return {}\n", encoding="utf-8")
            answer = answer_question(inspect_codebase(root), "What is inspect_codebase?", "engineer")
            self.assertIn("Source-backed answer", answer)
            self.assertIn("scanner.py:1", answer)

    def test_atlas_is_an_offline_graph_with_explanation_and_question_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project(root)
            atlas = build_atlas_html(inspect_codebase(root))
            self.assertIn("Codebase Atlas", atlas)
            self.assertIn("<svg", atlas)
            self.assertIn("Trả lời từ bằng chứng mã nguồn", atlas)
            self.assertIn("app.py", atlas)
            self.assertNotIn("https://", atlas)

    def test_atlas_is_learner_first_but_keeps_full_codebase_and_source_terms(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project(root)
            atlas = build_atlas_html(inspect_codebase(root))
            self.assertIn("Ứng dụng này làm gì?", atlas)
            self.assertIn("Học codebase", atlas)
            self.assertIn("Full codebase", atlas)
            self.assertIn("App này làm gì?", atlas)
            self.assertIn("Tệp này dùng tệp kia", atlas)
            self.assertIn('"defaultAudience": "learner"', atlas)

    def test_atlas_detects_aios_bridge_without_claiming_it_is_running(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project(root)
            (root / "src" / "aios_habit").mkdir(parents=True)
            (root / "scripts").mkdir(exist_ok=True)
            (root / "src" / "aios_habit" / "antigravity_bridge.py").write_text("", encoding="utf-8")
            (root / "scripts" / "antigravity_sidecar_daemon.py").write_text("", encoding="utf-8")
            bridge = discover_ide_bridge(root)
            atlas = build_atlas_html(inspect_codebase(root))
            self.assertTrue(bridge["detected"])
            self.assertEqual(bridge["health_url"], "http://127.0.0.1:8585/health")
            self.assertIn("Antigravity IDE Bridge", atlas)
            self.assertIn("checkBridge", atlas)

    def test_custom_bridge_manifest_rejects_remote_urls(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".excaliflow").mkdir()
            (root / ".excaliflow" / "ide-bridge.json").write_text(
                '{"health_url":"https://example.com/health","completion_url":"https://example.com/chat"}',
                encoding="utf-8",
            )
            bridge = discover_ide_bridge(root)
            self.assertFalse(bridge["detected"])
            self.assertIn("localhost", bridge["reason"])

    def test_source_scan_prunes_runtime_and_virtual_environment_trees(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.make_project(root)
            (root / "local_runs").mkdir()
            (root / ".venv-rag" / "site-packages").mkdir(parents=True)
            (root / "local_runs" / "stale.py").write_text("def stale(): pass\n", encoding="utf-8")
            (root / ".venv-rag" / "site-packages" / "dependency.py").write_text("def dependency(): pass\n", encoding="utf-8")
            report = inspect_codebase(root)
            self.assertEqual(report["files"], ["app.py", "service.py"])
