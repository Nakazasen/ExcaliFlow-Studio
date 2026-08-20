# Tasks: Create Atlas Bridge

## Phase 1: Specification and Safety

- [X] T001 Specify local-only bridge behavior, external-processing disclosure, and no-overwrite protection in `spec.md`.
- [X] T002 Map existing Atlas discovery and CLI dependencies with Graphify.

## Phase 2: Tests

- [X] T003 Add manifest creation and no-overwrite tests in `tests/test_explorer.py`.
- [X] T004 Add CLI creation and in-process local upstream forwarding tests in `tests/test_explorer.py`.

## Phase 3: Implementation

- [X] T005 Add loopback-only manifest creation, health checks, and forwarding in `src/excaliflow/bridge_server.py`.
- [X] T006 Add bridge commands and Atlas manifest creation option in `src/excaliflow/cli.py`.
- [X] T007 Mark explicit bridge manifests as external processing in `src/excaliflow/bridge.py`.

## Phase 4: Documentation and Verification

- [X] T008 Document the commands, boundary, and upstream prerequisite in `README.md`.
- [X] T009 Run focused and full tests, bytecode compilation, and diff hygiene checks.

## Phase 5: Operational Learning

- [X] T010 Add local-only bridge diagnosis with actionable status in `src/excaliflow/bridge_server.py` and `src/excaliflow/cli.py`.
- [X] T011 Add regression coverage for diagnosis in `tests/test_explorer.py`.
- [X] T012 Add and package a Gemini Web2API runtime playbook in `docs/`, `SKILL.md`, `README.md`, and `src/excaliflow/installer.py`.
- [X] T013 Run focused and full tests, bytecode compilation, and diff hygiene checks.

## Phase 6: Learner-First Launch

- [X] T014 Add a no-flag project-opening command in `src/excaliflow/cli.py` and its regression test in `tests/test_explorer.py`.
- [X] T015 Add a portable Windows folder-picker launcher in `scripts/Open-ExcaliFlow.cmd` and package coverage in `tests/test_package_entrypoint.py`.
- [X] T016 Update `README.md` and `SKILL.md` so AI hosts recommend the learner-first entry point before technical commands.
- [X] T017 Run focused and full tests, bytecode compilation, and diff hygiene checks.

## Phase 7: Readable Full Graph

- [X] T018 Keep the intrinsic Atlas SVG canvas and add local zoom, reset, and overview controls in `src/excaliflow/atlas.py`.
- [X] T019 Add regression coverage for a large Atlas canvas and controls in `tests/test_explorer.py`.
- [X] T020 Run focused and full tests, bytecode compilation, and diff hygiene checks.

## Phase 8: Visible AI Assistance

- [X] T021 Keep the Full codebase explanation panel sticky on desktop and add a visible AI connection card in `src/excaliflow/atlas.py`.
- [X] T022 Add local recheck and copyable Gemini Web2API / Atlas Bridge activation guidance that accurately preserves the static-HTML boundary in `src/excaliflow/atlas.py`.
- [X] T023 Add regression coverage for sticky assistance controls and run focused/full verification in `tests/test_explorer.py`.
