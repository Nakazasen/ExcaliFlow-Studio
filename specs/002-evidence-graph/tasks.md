# Tasks: Evidence Graph Atlas

## Phase 1: Specification and Architecture

- [X] T001 Define portable RAG trace and Evidence Graph safety requirements in `spec.md`.
- [X] T002 Query the updated Graphify graph for CLI, code scan, and Atlas boundaries.
- [X] T003 Record the additive contract and renderer design in `plan.md`.

## Phase 2: Tests First

- [X] T004 Add contract, failure, renderer, and CLI tests in `tests/test_knowledge.py`.

## Phase 3: Contract and Importer

- [X] T005 Add fail-closed RAG trace conversion and canonical graph validation in `src/excaliflow/knowledge.py`.
- [X] T006 Add the portable trace example in `examples/rag-trace.json`.

## Phase 4: Offline Evidence Atlas

- [X] T007 Add answer-centric, provenance-visible HTML rendering in `src/excaliflow/evidence_atlas.py`.
- [X] T008 Add local knowledge CLI commands in `src/excaliflow/cli.py`.

## Phase 5: Documentation and Verification

- [X] T009 Document vendor-neutral RAG/AIOS adaptation and safety boundary in `README.md` and `SKILL.md`.
- [X] T010 Run focused and full tests, compile checks, artifact smoke test, diff hygiene, commit, and push.
