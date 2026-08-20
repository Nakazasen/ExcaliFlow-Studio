import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from excaliflow.atlas import build_atlas_html
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
            atlas = build_atlas_html(inspect_codebase(root), "learner")
            self.assertIn("Codebase Atlas", atlas)
            self.assertIn("<svg", atlas)
            self.assertIn("Answer from source evidence", atlas)
            self.assertIn("app.py", atlas)
            self.assertNotIn("https://", atlas)
