# Implementation Plan: Update Notification

## Architecture Decisions

1. Add a root `VERSION` receipt as the version source for portable installs.
2. Add `update.py` with strict local SemVer parsing and manifest validation.
   It uses standard-library `urllib` only when a person explicitly invokes the
   CLI command.
3. Return a friendly `unavailable` state for network or manifest failure; do
   not silently fall back to an unverified update source.
4. Add `excaliflow update check`, with optional HTTPS manifest URL override for
   self-hosted GitHub Enterprise or testing.
5. On release tags, reject tag/version mismatch, generate a simple unsigned
   `update.json`, then upload it with the existing ZIP. No signature is added
   by user direction.
6. Include `VERSION` in both Python and PowerShell installer copy lists.

## Affected Components

| Component | Responsibility |
|---|---|
| `VERSION` | Version receipt copied into every installed skill. |
| `src/excaliflow/update.py` | Version/manifest validation and explicit check. |
| `src/excaliflow/cli.py` | Human-friendly update command. |
| `src/excaliflow/installer.py` | Copy the version receipt into IDE targets. |
| `installers/*.ps1` | Include and verify the version receipt in Windows ZIP setup. |
| `.github/workflows/release-windows.yml` | Generate and upload update manifest. |
| `tests/test_update.py` | Contract and CLI behavior without external network. |

## Validation and Rollback

- Verify command behavior with injected responses, release bundle contents, and
  workflow text regression tests.
- Run full suite, compile, release-bundle smoke test, and diff check.
- Rollback is a single commit revert; checking never changes installations.
