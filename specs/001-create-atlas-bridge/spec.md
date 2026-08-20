# Feature Specification: Create Atlas Bridge

**Feature branch**: `main`
**Created**: 2026-08-20
**Status**: Complete

## User Scenarios and Testing

### User Story 1 - Enable questions in an unbridged repository (Priority: P1)

A person opens Codebase Atlas for a repository that has no IDE Bridge and creates a project-local bridge so Atlas can use an already-running local AI source.

**Acceptance Scenarios**:

1. **Given** a valid repository without a bridge manifest, **when** the person initializes a bridge, **then** the repository receives one documented bridge manifest.
2. **Given** a repository with an existing bridge manifest, **when** initialization is requested, **then** the existing manifest remains unchanged and the person receives an error.
3. **Given** the local AI source is unavailable, **when** Atlas checks the created bridge, **then** it reports unavailable instead of claiming that AI answers work.

### User Story 2 - Keep source-context boundaries visible (Priority: P1)

A person can tell that a created bridge uses an external AI provider and decides whether their code context may leave the machine.

**Acceptance Scenarios**:

1. **Given** a bridge created by ExcaliFlow, **when** Atlas reads it, **then** it identifies the bridge as external processing.
2. **Given** a person reads the setup guide, **when** choosing a bridge, **then** they can see that the bridge does not install or start the upstream AI service.

### User Story 3 - Use the same workflow from Atlas creation (Priority: P2)

A person can create the manifest while producing an Atlas without starting a background server.

**Acceptance Scenarios**:

1. **Given** a valid unbridged repository, **when** the person asks Atlas generation to create a bridge, **then** both the Atlas output and bridge manifest are created.

## Requirements

- **FR-001**: The product MUST create a bridge manifest in the selected repository without overwriting an existing manifest.
- **FR-002**: The created bridge MUST accept connections only on the local machine and forward only to a local AI source.
- **FR-003**: The bridge MUST expose a readiness check and a chat request endpoint compatible with Atlas.
- **FR-004**: The readiness check MUST fail closed when the upstream AI source is not reachable.
- **FR-005**: The manifest MUST mark that requests are externally processed when it forwards to the AI source.
- **FR-006**: The command-line workflow MUST support initialize, run, and initialize-with-Atlas flows.
- **FR-007**: Setup documentation MUST state the local endpoints, upstream prerequisite, non-overwrite behavior, and data-boundary implication.

## Success Criteria

- **SC-001**: A person can create an Atlas Bridge for a valid repository with one command and no file editing.
- **SC-002**: An unavailable upstream is reported as unavailable in every readiness test; no false-ready response is produced.
- **SC-003**: Existing project bridge configuration is preserved in 100% of initialization attempts.
- **SC-004**: The full automated suite passes after adding the feature.

## Assumptions

- The person separately installs and starts a compatible local AI source if they want AI answers.
- The default local AI source is Gemini Web2API; users may point the bridge at another loopback-compatible source.
- The bridge must not manage credentials, install software, or automatically start external services.

## Out of Scope

- Installing or configuring Gemini Web2API.
- Creating a Windows background service or autostart entry.
- Supporting remote upstreams or remote bridge listeners.
