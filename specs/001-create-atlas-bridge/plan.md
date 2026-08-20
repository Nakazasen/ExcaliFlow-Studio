# Implementation Plan: Create Atlas Bridge

## Technical Context

The existing Atlas browser discovers `.excaliflow/ide-bridge.json` and local runtime candidates. Add a project-local loopback proxy so projects without an IDE-specific bridge receive the same Atlas contract.

## Architecture Decisions

1. Add an isolated bridge-server module to own manifest creation, loopback validation, health checks, request forwarding, and server lifecycle.
2. Keep CLI orchestration in the existing package entry point with `bridge init`, `bridge serve`, `bridge start`, and Atlas `--create-bridge`.
3. Preserve the current bridge discovery module; add only the external-processing manifest field it needs to faithfully label the source.
4. Use an upstream readiness endpoint before reporting bridge health as available.
5. Test manifest, CLI, loopback boundary, end-to-end forwarding, and existing Atlas discovery behavior with an in-process fake compatible upstream.
6. Productize the verified runtime procedure as a portable playbook and a local-only diagnosis command; retain explicit user control over third-party installation and process startup.
7. Add a learner-first launcher that writes a predictable project-local Atlas and opens it, while leaving Bridge setup optional and hidden from the default path.
8. Keep full-graph SVG dimensions intrinsic, then add local overview/detail controls instead of scaling all nodes down to fit the visible panel.
9. Keep Full codebase side panels sticky and independently scrollable on desktop; expose the existing local Bridge discovery as a visible, copyable activation workflow rather than trying to launch a process from static browser JavaScript.

## Affected Components

| Component | Responsibility |
|---|---|
| `src/excaliflow/bridge_server.py` | Create and serve safe local Atlas Bridge instances. |
| `src/excaliflow/cli.py` | Expose clear non-technical bridge commands. |
| `src/excaliflow/bridge.py` | Surface external-processing information from manifests. |
| `src/excaliflow/installer.py` | Include the runtime playbook in installed skills. |
| `scripts/Open-ExcaliFlow.cmd` | Provide a Windows folder-picker launcher shipped in portable skills. |
| `src/excaliflow/atlas.py` | Render a readable, scrollable full graph with local zoom controls. |
| `tests/test_explorer.py` | Cover user-visible bridge scenarios. |
| `README.md`, `SKILL.md`, `docs/` | Explain prerequisites, boundaries, operation, and troubleshooting. |

## Validation and Rollback

- Run Explorer-focused tests, the full test suite, compilation, and whitespace checks.
- Rollback is a single commit revert; existing IDE bridge manifests remain untouched because initialization rejects overwrites.
