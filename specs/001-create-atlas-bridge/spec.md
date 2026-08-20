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

### User Story 4 - Reuse a verified AI runtime recipe (Priority: P2)

A person or an AI host can diagnose the local Gemini runtime and follow one durable, privacy-explicit playbook instead of relying on a previous chat session.

**Acceptance Scenarios**:

1. **Given** an unavailable bridge or upstream, **when** the person runs the bridge diagnosis, **then** it states which local component is unavailable and the next safe action.
2. **Given** a supported host receives the ExcaliFlow skill, **when** it needs Atlas AI questions, **then** it can read the bundled runtime playbook.

### User Story 5 - Open a project without technical setup (Priority: P1)

A non-technical person can choose a project folder and immediately see a beginner-friendly Atlas without knowing command options, output paths, ports, or AI Bridge terms.

**Acceptance Scenarios**:

1. **Given** a project folder, **when** the person uses the simple open command, **then** Atlas is generated in a predictable project-local location and opened in their browser.
2. **Given** Windows and a portable installed skill, **when** the person double-clicks the launcher without an argument, **then** they can choose a project folder in a standard folder picker.
3. **Given** the optional AI service is unavailable, **when** the person opens Atlas, **then** source-backed learning remains usable and they are not asked to configure a bridge to begin.

### User Story 6 - Read a full codebase map (Priority: P1)

A person opening Full codebase can read file names in a large project instead of seeing the entire graph compressed into an unreadable thumbnail.

**Acceptance Scenarios**:

1. **Given** a graph with hundreds of files, **when** the person opens Full codebase, **then** nodes retain readable dimensions and the map scrolls rather than shrinking all nodes to fit the viewport.
2. **Given** a large full map, **when** the person needs orientation or detail, **then** they can switch between overview, reset, zoom in, and zoom out controls.

## Requirements

- **FR-001**: The product MUST create a bridge manifest in the selected repository without overwriting an existing manifest.
- **FR-002**: The created bridge MUST accept connections only on the local machine and forward only to a local AI source.
- **FR-003**: The bridge MUST expose a readiness check and a chat request endpoint compatible with Atlas.
- **FR-004**: The readiness check MUST fail closed when the upstream AI source is not reachable.
- **FR-005**: The manifest MUST mark that requests are externally processed when it forwards to the AI source.
- **FR-006**: The command-line workflow MUST support initialize, run, and initialize-with-Atlas flows.
- **FR-007**: Setup documentation MUST state the local endpoints, upstream prerequisite, non-overwrite behavior, and data-boundary implication.
- **FR-008**: The command-line workflow MUST provide a local-only diagnostic that distinguishes a missing project manifest, unavailable upstream, and unavailable Atlas Bridge.
- **FR-009**: The portable skill MUST include an operational playbook for Gemini Web2API with loopback-only configuration, temporary-chat guidance, lifecycle commands, verification, and troubleshooting.
- **FR-010**: The product MUST provide one simple project-opening workflow that needs only a project folder and does not create or start an AI Bridge.
- **FR-011**: The portable Windows skill MUST include a double-click launcher with a folder picker and clear failure output.
- **FR-012**: Full codebase rendering MUST preserve a readable physical node size for large graphs instead of forcing the full SVG to the viewport width.
- **FR-013**: Full codebase rendering MUST provide local zoom and overview controls without a network runtime.

## Success Criteria

- **SC-001**: A person can create an Atlas Bridge for a valid repository with one command and no file editing.
- **SC-002**: An unavailable upstream is reported as unavailable in every readiness test; no false-ready response is produced.
- **SC-003**: Existing project bridge configuration is preserved in 100% of initialization attempts.
- **SC-004**: The full automated suite passes after adding the feature.
- **SC-005**: When a local runtime is unavailable, the diagnostic gives a concrete next action without suggesting that AI questions are working.
- **SC-006**: A person can produce and open an Atlas with one command containing only the project location.
- **SC-007**: A graph of 100 or more files renders with an intrinsic scrollable canvas and controls for overview and readable detail.

## Assumptions

- The person separately installs and starts a compatible local AI source if they want AI answers.
- The default local AI source is Gemini Web2API; users may point the bridge at another loopback-compatible source.
- The bridge must not manage credentials, install software, or automatically start external services.

## Out of Scope

- Installing or configuring Gemini Web2API.
- Creating a Windows background service or autostart entry.
- Supporting remote upstreams or remote bridge listeners.
