# Implementation Plan: Evidence Graph Atlas

## Technical Context

The current package separates code scanning (`explorer.py`) from the offline
Codebase Atlas (`atlas.py`) and CLI dispatch (`cli.py`). Evidence Graph must be
additive: it consumes explicit RAG traces, creates a canonical JSON graph, and
has its own renderer so code-scan fidelity remains unchanged.

## Architecture Decisions

1. Add `knowledge.py` for contract parsing, fail-closed validation, and RAG
   trace conversion. It uses only the Python standard library.
2. Use `evidence-graph.json` as the source of truth. SVG, HTML, Mermaid, and
   Excalidraw exports are derived views, never the canonical data.
3. Store receipts on edges and make them mandatory for all imported claims;
   answer nodes must have at least one `supported_by` edge to a chunk.
4. Add `evidence_atlas.py` as an independent self-contained renderer. Start at
   the answer-and-citations path, expose full graph as an explicit mode, and
   show a side receipt panel on selection.
5. Add `excaliflow knowledge import` and `excaliflow knowledge atlas` CLI
   commands. Both work strictly from local files and never start AI Bridge.
6. Include a small JSON trace fixture and README examples. The fixture models a
   support-answer path and a review-required claim, without claiming model
   extraction is a verified fact.

## Affected Components

| Component | Responsibility |
|---|---|
| `src/excaliflow/knowledge.py` | Canonical contract, validation, and RAG trace conversion. |
| `src/excaliflow/evidence_atlas.py` | Offline answer-centric Evidence Atlas renderer. |
| `src/excaliflow/cli.py` | Local `knowledge import` and `knowledge atlas` commands. |
| `tests/test_knowledge.py` | Contract, failure, renderer, and CLI regression coverage. |
| `examples/rag-trace.json` | Portable trace example for other RAG systems. |
| `README.md`, `SKILL.md` | User workflow and safety/provenance boundary. |

## Validation and Rollback

- Tests cover positive conversion, no-partial-file failures, source receipts,
  generated HTML, and both CLI commands.
- Run the full test suite, bytecode compile, whitespace check, and generated
  artifact smoke test before commit.
- Rollback is one commit revert. No source data or remote service is modified.
