# Feature Specification: Update Notification

**Feature branch**: `main`
**Created**: 2026-08-21
**Status**: In progress

## User Scenarios and Testing

### User Story 1 - Know when a newer release exists (Priority: P1)

A person or AI host using an installed ExcaliFlow skill can run one command and
see whether a newer stable release is available.

**Acceptance Scenarios**:

1. Given an installed `VERSION` and a newer valid local manifest response,
   when `excaliflow update check` runs, then it shows installed version, latest
   version, release notes URL, and ZIP download URL.
2. Given the same version or a newer installed version, when the command runs,
   then it says the installation is up to date and does not claim an update.
3. Given an unreachable, malformed, HTTP, or invalid-version manifest, when
   the command runs, then it says update status is unavailable and does not
   raise a stack trace or change local files.

### User Story 2 - Publish a machine-readable latest release (Priority: P1)

A maintainer tagging a release publishes one manifest that every installed
version can query.

**Acceptance Scenarios**:

1. Given tag `vX.Y.Z` whose repository `VERSION` is `X.Y.Z`, when the Windows
   release workflow succeeds, then the GitHub Release contains
   `ExcaliFlow-Setup-windows.zip` and `update.json`.
2. Given a tag/version mismatch, when release preparation runs, then it fails
   before publishing a misleading update manifest.

## Requirements

- **FR-001**: The portable skill and Windows setup bundle MUST include a plain
  `VERSION` file.
- **FR-002**: `excaliflow update check` MUST fetch the default GitHub Release
  manifest only when explicitly invoked; it MUST not run in the background.
- **FR-003**: The manifest MUST contain schema version, SemVer version, release
  notes URL, and HTTPS ZIP asset URL.
- **FR-004**: Invalid/missing/unreachable manifests MUST fail closed as an
  unavailable update status and MUST not modify an installed skill.
- **FR-005**: The tagged workflow MUST enforce that the release tag and
  repository `VERSION` agree, generate `update.json`, and upload it alongside
  the Windows ZIP.
- **FR-006**: This feature MUST NOT introduce code-signature, credential,
  background-process, auto-download, or auto-install behavior.

## Success Criteria

- **SC-001**: Tests prove newer, equal, malformed, and unreachable manifest
  outcomes without making external network calls.
- **SC-002**: Tests prove installer/bundle includes `VERSION` and workflow
  publishes the update manifest.
- **SC-003**: Full regression suite and diff hygiene pass.

## Out of Scope

- Automatic download/install, scheduled update polling, installer signatures,
  update channels, and update rollback.
