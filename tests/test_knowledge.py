import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from excaliflow.evidence_atlas import build_evidence_atlas_html
from excaliflow.knowledge import EvidenceValidationError, graph_from_rag_trace, load_evidence_graph, write_evidence_graph


ROOT = Path(__file__).resolve().parents[1]


def valid_trace() -> dict:
    return {
        "schema_version": "rag-trace/v1",
        "title": "Password reset investigation",
        "query": "Why did password reset fail?",
        "answer": {
            "id": "answer-reset",
            "text": "The reset service requires a verified email before creating a token.",
            "citations": ["chunk-reset-rule"],
        },
        "documents": [
            {"id": "doc-runbook", "title": "Reset runbook", "location": "docs/reset-runbook.md"},
        ],
        "chunks": [
            {
                "id": "chunk-reset-rule",
                "document_id": "doc-runbook",
                "text": "A password reset token is created only after email verification succeeds.",
                "location": "docs/reset-runbook.md:12-14",
                "score": 0.91,
            },
        ],
        "entities": [
            {"id": "entity-reset-service", "label": "Password reset service", "kind": "component"},
            {"id": "entity-email-check", "label": "Email verification", "kind": "process"},
        ],
        "claims": [
            {
                "id": "claim-prerequisite",
                "text": "The reset service depends on email verification.",
                "subject_id": "entity-reset-service",
                "object_id": "entity-email-check",
                "relation": "depends_on",
                "origin": "llm_extracted",
                "confidence": 0.72,
                "review_status": "needs_review",
                "citations": ["chunk-reset-rule"],
            },
        ],
        "code_references": [
            {
                "id": "code-reset-token",
                "label": "reset_password in src/reset.py",
                "location": "src/reset.py:42",
                "kind": "function",
                "target_id": "entity-reset-service",
                "relation": "implemented_by",
                "origin": "source_scan",
                "confidence": 1.0,
                "review_status": "verified",
            },
        ],
    }


class KnowledgeTests(unittest.TestCase):
    def test_rag_trace_becomes_answer_citation_and_claim_graph(self):
        graph = graph_from_rag_trace(valid_trace())
        self.assertEqual(graph["schema_version"], "evidence-graph/v1")
        self.assertTrue(any(node["id"] == "answer-reset" and node["type"] == "answer" for node in graph["nodes"]))
        support = next(edge for edge in graph["edges"] if edge["relation"] == "supported_by")
        self.assertEqual((support["from"], support["to"]), ("answer-reset", "chunk-reset-rule"))
        self.assertEqual(support["receipts"][0]["source_node_id"], "chunk-reset-rule")
        claim = next(node for node in graph["nodes"] if node["id"] == "claim-prerequisite")
        self.assertEqual(claim["review_status"], "needs_review")
        self.assertTrue(any(edge["from"] == "claim-prerequisite" and edge["to"] == "chunk-reset-rule" for edge in graph["edges"]))
        code = next(node for node in graph["nodes"] if node["id"] == "code-reset-token")
        self.assertEqual(code["type"], "code")
        self.assertTrue(any(edge["from"] == "code-reset-token" and edge["to"] == "entity-reset-service" for edge in graph["edges"]))

    def test_uncited_answer_fails_before_output_is_written(self):
        trace = valid_trace()
        trace["answer"]["citations"] = []
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "evidence-graph.json"
            with self.assertRaisesRegex(EvidenceValidationError, "at least one citation"):
                write_evidence_graph(trace, output)
            self.assertFalse(output.exists())

    def test_uncited_llm_claim_and_dangling_reference_fail_closed(self):
        trace = valid_trace()
        trace["claims"][0]["citations"] = []
        with self.assertRaisesRegex(EvidenceValidationError, "LLM-extracted claim"):
            graph_from_rag_trace(trace)
        trace = valid_trace()
        trace["claims"][0]["object_id"] = "missing-entity"
        with self.assertRaisesRegex(EvidenceValidationError, "unknown object"):
            graph_from_rag_trace(trace)

    def test_evidence_atlas_is_offline_and_discloses_provenance(self):
        atlas = build_evidence_atlas_html(graph_from_rag_trace(valid_trace()))
        self.assertIn("Evidence Atlas", atlas)
        self.assertIn("Câu trả lời", atlas)
        self.assertIn("Nguồn bằng chứng", atlas)
        self.assertIn("Cần xem lại", atlas)
        self.assertIn('data-view="answer"', atlas)
        self.assertIn('data-view="full"', atlas)
        self.assertNotIn("https://", atlas)

    def test_cli_import_and_atlas_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trace_path = root / "rag-trace.json"
            graph_path = root / "evidence-graph.json"
            atlas_path = root / "evidence-atlas.html"
            trace_path.write_text(json.dumps(valid_trace(), ensure_ascii=False), encoding="utf-8")
            env = {**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")}
            imported = subprocess.run(
                [sys.executable, "-m", "excaliflow.cli", "knowledge", "import", "--trace", str(trace_path), "--out", str(graph_path)],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertIn("Wrote Evidence Graph", imported.stdout)
            self.assertEqual(load_evidence_graph(graph_path)["schema_version"], "evidence-graph/v1")
            rendered = subprocess.run(
                [sys.executable, "-m", "excaliflow.cli", "knowledge", "atlas", "--graph", str(graph_path), "--out", str(atlas_path)],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            self.assertIn("Wrote offline Evidence Atlas", rendered.stdout)
            self.assertIn("Evidence Atlas", atlas_path.read_text(encoding="utf-8"))
