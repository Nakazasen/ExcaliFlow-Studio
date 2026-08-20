"""Portable, fail-closed Evidence Graph contracts for local RAG traces."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


TRACE_SCHEMA = "rag-trace/v1"
GRAPH_SCHEMA = "evidence-graph/v1"
NODE_TYPES = {"answer", "document", "chunk", "entity", "claim", "case", "code"}
EDGE_ORIGINS = {"retrieval", "user", "llm_extracted", "source_document", "source_scan"}
REVIEW_STATUSES = {"verified", "needs_review"}


class EvidenceValidationError(ValueError):
    """Raised when an evidence graph cannot be trusted enough to render."""


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceValidationError(f"{name} must be an object.")
    return value


def _items(value: Any, name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise EvidenceValidationError(f"{name} must be a list.")
    return [_mapping(item, f"{name} item") for item in value]


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceValidationError(f"{name} must be non-empty text.")
    return value.strip()


def _confidence(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise EvidenceValidationError(f"{name} must be a number from 0 to 1.")
    return float(value)


def _unique_id(item: dict[str, Any], node_ids: set[str], name: str) -> str:
    identifier = _text(item.get("id"), f"{name}.id")
    if identifier in node_ids:
        raise EvidenceValidationError(f"Duplicate identifier: {identifier}.")
    node_ids.add(identifier)
    return identifier


def _receipt(source_node_id: str, location: str) -> dict[str, str]:
    return {"source_node_id": source_node_id, "location": location}


def _citation_receipts(citations: list[str], chunks: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    return [_receipt(chunk_id, _text(chunks[chunk_id].get("location"), f"chunk {chunk_id}.location")) for chunk_id in citations]


def _citation_ids(value: Any, chunks: dict[str, dict[str, Any]], name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise EvidenceValidationError(f"{name} must have at least one citation.")
    citations = [_text(item, f"{name} citation") for item in value]
    if len(set(citations)) != len(citations):
        raise EvidenceValidationError(f"{name} contains duplicate citations.")
    missing = [citation for citation in citations if citation not in chunks]
    if missing:
        raise EvidenceValidationError(f"{name} cites unknown chunk: {missing[0]}.")
    return citations


def graph_from_rag_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Convert a vendor-neutral RAG trace into the canonical evidence graph.

    The importer deliberately accepts only explicit evidence. It does not infer
    entities, invent links, invoke an LLM, or contact a retrieval system.
    """

    trace = _mapping(trace, "RAG trace")
    if trace.get("schema_version") != TRACE_SCHEMA:
        raise EvidenceValidationError(f"schema_version must be {TRACE_SCHEMA}.")
    title = _text(trace.get("title") or trace.get("query"), "trace title or query")
    query = _text(trace.get("query"), "query")
    node_ids: set[str] = set()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    documents: dict[str, dict[str, Any]] = {}
    for document in _items(trace.get("documents", []), "documents"):
        identifier = _unique_id(document, node_ids, "document")
        location = _text(document.get("location"), f"document {identifier}.location")
        label = _text(document.get("title") or document.get("label"), f"document {identifier}.title")
        documents[identifier] = document
        nodes.append({"id": identifier, "type": "document", "label": label, "properties": {"location": location}})

    chunks: dict[str, dict[str, Any]] = {}
    for chunk in _items(trace.get("chunks", []), "chunks"):
        identifier = _unique_id(chunk, node_ids, "chunk")
        document_id = _text(chunk.get("document_id"), f"chunk {identifier}.document_id")
        if document_id not in documents:
            raise EvidenceValidationError(f"Chunk {identifier} references unknown document: {document_id}.")
        text = _text(chunk.get("text"), f"chunk {identifier}.text")
        location = _text(chunk.get("location"), f"chunk {identifier}.location")
        score = _confidence(chunk.get("score"), f"chunk {identifier}.score")
        chunks[identifier] = chunk
        nodes.append({"id": identifier, "type": "chunk", "label": text, "properties": {"location": location, "score": score, "document_id": document_id}})
        edges.append({
            "id": f"edge-{document_id}-{identifier}-contains",
            "from": document_id,
            "to": identifier,
            "relation": "contains",
            "origin": "source_document",
            "confidence": 1.0,
            "review_status": "verified",
            "receipts": [_receipt(document_id, _text(documents[document_id].get("location"), f"document {document_id}.location"))],
        })

    answer = _mapping(trace.get("answer"), "answer")
    answer_id = _unique_id(answer, node_ids, "answer")
    answer_text = _text(answer.get("text"), "answer.text")
    answer_citations = _citation_ids(answer.get("citations"), chunks, "answer")
    nodes.append({"id": answer_id, "type": "answer", "label": answer_text, "properties": {"query": query}})
    for citation in answer_citations:
        edges.append({
            "id": f"edge-{answer_id}-{citation}-supported-by",
            "from": answer_id,
            "to": citation,
            "relation": "supported_by",
            "origin": "retrieval",
            "confidence": _confidence(chunks[citation].get("score"), f"chunk {citation}.score"),
            "review_status": "verified",
            "receipts": _citation_receipts([citation], chunks),
        })

    entities: dict[str, dict[str, Any]] = {}
    for entity in _items(trace.get("entities", []), "entities"):
        identifier = _unique_id(entity, node_ids, "entity")
        label = _text(entity.get("label"), f"entity {identifier}.label")
        kind = _text(entity.get("kind") or "concept", f"entity {identifier}.kind")
        entities[identifier] = entity
        nodes.append({"id": identifier, "type": "entity", "label": label, "properties": {"kind": kind}})

    for claim in _items(trace.get("claims", []), "claims"):
        identifier = _unique_id(claim, node_ids, "claim")
        subject_id = _text(claim.get("subject_id"), f"claim {identifier}.subject_id")
        object_id = _text(claim.get("object_id"), f"claim {identifier}.object_id")
        if subject_id not in entities:
            raise EvidenceValidationError(f"Claim {identifier} references unknown subject: {subject_id}.")
        if object_id not in entities:
            raise EvidenceValidationError(f"Claim {identifier} references unknown object: {object_id}.")
        origin = _text(claim.get("origin"), f"claim {identifier}.origin")
        if origin not in EDGE_ORIGINS:
            raise EvidenceValidationError(f"Claim {identifier} has unsupported origin: {origin}.")
        review_status = _text(claim.get("review_status"), f"claim {identifier}.review_status")
        if review_status not in REVIEW_STATUSES:
            raise EvidenceValidationError(f"Claim {identifier} has unsupported review_status: {review_status}.")
        citations = _citation_ids(claim.get("citations"), chunks, f"LLM-extracted claim {identifier}" if origin == "llm_extracted" else f"claim {identifier}")
        confidence = _confidence(claim.get("confidence"), f"claim {identifier}.confidence")
        relation = _text(claim.get("relation"), f"claim {identifier}.relation")
        text = _text(claim.get("text"), f"claim {identifier}.text")
        receipts = _citation_receipts(citations, chunks)
        nodes.append({"id": identifier, "type": "claim", "label": text, "origin": origin, "confidence": confidence, "review_status": review_status, "properties": {"relation": relation}})
        for role, target in (("subject", subject_id), ("object", object_id)):
            edges.append({
                "id": f"edge-{identifier}-{target}-{role}",
                "from": identifier,
                "to": target,
                "relation": role,
                "origin": origin,
                "confidence": confidence,
                "review_status": review_status,
                "receipts": receipts,
            })
        for citation in citations:
            edges.append({
                "id": f"edge-{identifier}-{citation}-supported-by",
                "from": identifier,
                "to": citation,
                "relation": "supported_by",
                "origin": origin,
                "confidence": confidence,
                "review_status": review_status,
                "receipts": _citation_receipts([citation], chunks),
            })

    for reference in _items(trace.get("code_references", []), "code_references"):
        identifier = _unique_id(reference, node_ids, "code reference")
        label = _text(reference.get("label"), f"code reference {identifier}.label")
        location = _text(reference.get("location"), f"code reference {identifier}.location")
        kind = _text(reference.get("kind") or "symbol", f"code reference {identifier}.kind")
        target_id = _text(reference.get("target_id"), f"code reference {identifier}.target_id")
        if target_id not in node_ids:
            raise EvidenceValidationError(f"Code reference {identifier} targets an unknown node: {target_id}.")
        origin = _text(reference.get("origin"), f"code reference {identifier}.origin")
        if origin not in EDGE_ORIGINS:
            raise EvidenceValidationError(f"Code reference {identifier} has unsupported origin: {origin}.")
        review_status = _text(reference.get("review_status"), f"code reference {identifier}.review_status")
        if review_status not in REVIEW_STATUSES:
            raise EvidenceValidationError(f"Code reference {identifier} has unsupported review_status: {review_status}.")
        confidence = _confidence(reference.get("confidence"), f"code reference {identifier}.confidence")
        relation = _text(reference.get("relation"), f"code reference {identifier}.relation")
        nodes.append({"id": identifier, "type": "code", "label": label, "origin": origin, "confidence": confidence, "review_status": review_status, "properties": {"kind": kind, "location": location}})
        edges.append({
            "id": f"edge-{identifier}-{target_id}-{relation}",
            "from": identifier,
            "to": target_id,
            "relation": relation,
            "origin": origin,
            "confidence": confidence,
            "review_status": review_status,
            "receipts": [_receipt(identifier, location)],
        })

    graph = {"schema_version": GRAPH_SCHEMA, "title": title, "query": query, "nodes": nodes, "edges": edges}
    validate_evidence_graph(graph)
    return graph


def validate_evidence_graph(graph: dict[str, Any]) -> None:
    """Validate a canonical graph before it is persisted or rendered."""

    graph = _mapping(graph, "Evidence Graph")
    if graph.get("schema_version") != GRAPH_SCHEMA:
        raise EvidenceValidationError(f"schema_version must be {GRAPH_SCHEMA}.")
    _text(graph.get("title"), "graph.title")
    _text(graph.get("query"), "graph.query")
    node_ids: set[str] = set()
    node_types: dict[str, str] = {}
    for node in _items(graph.get("nodes"), "nodes"):
        identifier = _unique_id(node, node_ids, "node")
        node_type = _text(node.get("type"), f"node {identifier}.type")
        if node_type not in NODE_TYPES:
            raise EvidenceValidationError(f"Node {identifier} has unsupported type: {node_type}.")
        _text(node.get("label"), f"node {identifier}.label")
        node_types[identifier] = node_type
    edge_ids: set[str] = set()
    supported_answers: set[str] = set()
    for edge in _items(graph.get("edges"), "edges"):
        edge_id = _text(edge.get("id"), "edge.id")
        if edge_id in edge_ids:
            raise EvidenceValidationError(f"Duplicate edge identifier: {edge_id}.")
        edge_ids.add(edge_id)
        source = _text(edge.get("from"), f"edge {edge_id}.from")
        target = _text(edge.get("to"), f"edge {edge_id}.to")
        if source not in node_ids or target not in node_ids:
            raise EvidenceValidationError(f"Edge {edge_id} references an unknown node.")
        relation = _text(edge.get("relation"), f"edge {edge_id}.relation")
        origin = _text(edge.get("origin"), f"edge {edge_id}.origin")
        if origin not in EDGE_ORIGINS:
            raise EvidenceValidationError(f"Edge {edge_id} has unsupported origin: {origin}.")
        _confidence(edge.get("confidence"), f"edge {edge_id}.confidence")
        review_status = _text(edge.get("review_status"), f"edge {edge_id}.review_status")
        if review_status not in REVIEW_STATUSES:
            raise EvidenceValidationError(f"Edge {edge_id} has unsupported review_status: {review_status}.")
        receipts = _items(edge.get("receipts"), f"edge {edge_id}.receipts")
        if not receipts:
            raise EvidenceValidationError(f"Edge {edge_id} must have at least one receipt.")
        for receipt in receipts:
            receipt_node = _text(receipt.get("source_node_id"), f"edge {edge_id} receipt.source_node_id")
            if receipt_node not in node_ids:
                raise EvidenceValidationError(f"Edge {edge_id} receipt references an unknown node: {receipt_node}.")
            _text(receipt.get("location"), f"edge {edge_id} receipt.location")
        if relation == "supported_by" and node_types.get(source) == "answer" and node_types.get(target) == "chunk":
            supported_answers.add(source)
    missing_answers = [node_id for node_id, node_type in node_types.items() if node_type == "answer" and node_id not in supported_answers]
    if missing_answers:
        raise EvidenceValidationError(f"Answer {missing_answers[0]} must have at least one citation edge.")


def write_evidence_graph(trace: dict[str, Any], output_path: str | Path) -> Path:
    """Validate first, then atomically write a canonical graph."""

    graph = graph_from_rag_trace(trace)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, delete=False, suffix=".tmp") as handle:
        temporary = Path(handle.name)
        json.dump(graph, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    try:
        os.replace(temporary, output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return output


def load_evidence_graph(input_path: str | Path) -> dict[str, Any]:
    """Load and validate an existing canonical graph without network access."""

    path = Path(input_path)
    try:
        graph = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise EvidenceValidationError(f"Evidence Graph file does not exist: {path}.") from error
    except json.JSONDecodeError as error:
        raise EvidenceValidationError(f"Evidence Graph is not valid JSON: {error.msg}.") from error
    validate_evidence_graph(graph)
    return graph
