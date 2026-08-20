# Implementation Plan: Create Atlas Bridge

## Technical Context

The existing Atlas browser discovers `.excaliflow/ide-bridge.json` and local runtime candidates. Add a project-local loopback proxy so projects without an IDE-specific bridge receive the same Atlas contract.

## Architecture Decisions

1. Add an isolated bridge-server module to own manifest creation, loopback validation, health checks, request forwarding, and server lifecycle.
2. Keep CLI orchestration in the existing package entry point with `bridge init`, `bridge serve`, `bridge start`, and Atlas `--create-bridge`.
3. Preserve the current bridge discovery module; add only the external-processing manifest field it needs to faithfully label the source.
4. Use an upstream readiness endpoint before reporting bridge health as available.
5. Test manifest, CLI, loopback boundary, end-to-end forwarding, and existing Atlas discovery behavior with an in-process fake compatible upstream.

## Affected Components

| Component | Responsibility |
|---|---|
| `src/excaliflow/bridge_server.py` | Create and serve safe local Atlas Bridge instances. |
| `src/excaliflow/cli.py` | Expose clear non-technical bridge commands. |
| `src/excaliflow/bridge.py` | Surface external-processing information from manifests. |
| `tests/test_explorer.py` | Cover user-visible bridge scenarios. |
| `README.md` | Explain prerequisites, boundaries, and commands. |

## Validation and Rollback

- Run Explorer-focused tests, the full test suite, compilation, and whitespace checks.
- Rollback is a single commit revert; existing IDE bridge manifests remain untouched because initialization rejects overwrites.
