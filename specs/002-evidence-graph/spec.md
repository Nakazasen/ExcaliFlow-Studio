# Feature Specification: Evidence Graph Atlas

**Feature branch**: `main`
**Created**: 2026-08-21
**Status**: In progress

## Purpose

Extend ExcaliFlow Studio from a code-only relationship viewer into an offline
Evidence Graph Atlas. A person can import the trace of one RAG answer and see
the answer, the retrieved passages, named concepts, and asserted relationships
as a navigable graph with source receipts. Code relationships remain a separate,
locally proven view.

## User Scenarios and Testing

### User Story 1 - Explain where an answer came from (Priority: P1)

A learner imports a portable RAG trace and opens an HTML Atlas. They can see an
answer connected to its citations, read the cited passage, and identify whether
each relationship came from retrieval, a user-supplied assertion, or an LLM
extraction.

**Acceptance Scenarios**:

1. Given a valid RAG trace with an answer and citations, when it is imported,
   then the generated graph contains an answer node and `supported_by` edges to
   the cited chunks.
2. Given a citation with a document, text span, score, and source location,
   when a person selects it, then the Atlas shows those fields in a visible
   evidence receipt.
3. Given a trace whose answer has no citations, when importing it, then import
   fails and no output graph is written.

### User Story 2 - Model knowledge without overstating facts (Priority: P1)

A knowledge worker can represent concepts and relationships from a RAG result
while distinguishing evidence from a model suggestion.

**Acceptance Scenarios**:

1. Given entities and claims in a valid trace, when importing it, then entity
   and claim nodes use stable IDs and their relationships retain origin,
   confidence, and review status.
2. Given an LLM-extracted claim that lacks a source citation, when importing it,
   then the importer rejects the trace.
3. Given a non-verified claim, when it appears in the Atlas, then its receipt
   explicitly says it needs review instead of presenting it as a fact.

### User Story 3 - Use it without a particular RAG vendor (Priority: P1)

An engineer can export a minimal JSON trace from any RAG system and create an
offline Evidence Atlas with one command.

**Acceptance Scenarios**:

1. Given a UTF-8 JSON trace conforming to schema version 1, when the person
   runs the import command, then ExcaliFlow writes an `evidence-graph.json`.
2. Given that graph, when the person runs the Atlas command, then ExcaliFlow
   writes self-contained HTML containing no remote URL or browser dependency.
3. Given invalid JSON, unknown node references, duplicate identifiers, a
   non-loopback URL is not relevant because no network is contacted; the command
   instead reports a clear validation error and makes no partial artifact.

## Requirements

- **FR-001**: Provide a versioned, portable `evidence-graph.json` contract.
- **FR-002**: Nodes MUST support answer, document, chunk, entity, claim, case,
  and code types; nodes retain human labels and optional properties.
- **FR-003**: Every edge MUST retain relation, origin, confidence, review
  status, and at least one source receipt pointing to a known node or source
  span. `supported_by` is mandatory for answer nodes.
- **FR-004**: The RAG trace importer MUST validate complete references,
  identifiers, confidence range, and citation requirements before writing.
- **FR-005**: A local CLI command MUST convert `rag-trace.json` into the
  canonical graph and another command MUST generate a standalone Evidence
  Atlas HTML file.
- **FR-006**: Evidence Atlas MUST begin with an intelligible answer-centric
  view and offer a full graph view; selecting nodes/edges MUST show provenance.
- **FR-007**: Evidence Atlas MUST visually distinguish verified evidence from
  LLM-extracted or review-required claims without relying on colour alone.
- **FR-008**: No importer or renderer MAY call a model, retrieve a URL, start a
  service, or label an uncited model claim as verified.
- **FR-009**: Documentation MUST include a vendor-neutral trace example and
  explain how AIOS or another RAG system adapts its retrieval output.
- **FR-010**: A trace MAY include source-backed code references linking a file
  or symbol (`file:line`) to an answer, claim, or entity in the same graph.

## Success Criteria

- **SC-001**: Valid traces create a canonical graph and self-contained Atlas
  from a clean temporary project in automated tests.
- **SC-002**: Invalid answer provenance, dangling references, and malformed
  confidence values fail before an output file is created in automated tests.
- **SC-003**: The rendered Atlas visibly includes answer, cited-source,
  provenance receipt, full-graph control, and review language in tests.
- **SC-004**: Existing codebase Atlas, bridge, and installer tests still pass.

## Assumptions

- A host RAG system exports retrieval results; v1 does not query its vector
  store, model, or database directly.
- AIOS integration begins with the same vendor-neutral trace contract, not a
  hard dependency on AIOS internals.

## Out of Scope

- A graph database service, autonomous model training, prediction scoring, and
  automatic promotion of hypotheses to verified knowledge.
- Importing arbitrary Mermaid as a canonical knowledge graph.
