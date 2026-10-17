from __future__ import annotations

from uuid import uuid4
from typing import Any

from .contracts import ContractError, validate
from .store import LocalKnowledgeStore, utc_now


def _candidate(
    origin: str, source_reference: str, records: list[dict[str, Any]], research_id: str | None = None
) -> dict[str, Any]:
    candidate = {
        "candidate_id": f"candidate-{uuid4().hex}",
        "origin": origin,
        "status": "pending_review",
        "created_at": utc_now(),
        "source_reference": source_reference,
        "research_id": research_id,
        "records": records,
        "review": None,
    }
    validate(candidate, "candidate.schema.json")
    return candidate


def prepare_prebuild(source: dict[str, Any], store: LocalKnowledgeStore) -> dict[str, Any]:
    validate(source, "prebuild-source.schema.json")
    candidate = _candidate("prebuild", source["bundle_id"], source["records"])
    store.save_candidate(candidate)
    return candidate


def prepare_gap_research(
    gaps: dict[str, Any], supplied_records: dict[str, Any], store: LocalKnowledgeStore
) -> dict[str, Any]:
    validate(gaps, "gap-export.schema.json")
    validate(supplied_records, "supplement-records.schema.json")
    if not gaps["gaps"]:
        raise ContractError("research packet requires at least one imported gap")
    known_gap_ids = {gap["gap_id"] for gap in gaps["gaps"]}
    covered_gap_ids = {record.get("gap_id") for record in supplied_records["records"]}
    if known_gap_ids != covered_gap_ids:
        raise ContractError("supplement records must cover each imported gap and contain no unknown gap")
    purpose_by_gap = {gap["gap_id"]: gap["purpose"] for gap in gaps["gaps"]}
    if any(record["kind"] != purpose_by_gap[record["gap_id"]] for record in supplied_records["records"]):
        raise ContractError("supplement record kind must match the imported gap purpose")
    packet = {
        "research_id": f"research-{uuid4().hex}",
        "export_id": gaps["export_id"],
        "status": "complete",
        "created_at": utc_now(),
        "gaps": gaps["gaps"],
        "records": supplied_records["records"],
    }
    store.save_research_packet(packet)
    return packet


def prepare_gap_supplement(research_id: str, store: LocalKnowledgeStore) -> dict[str, Any]:
    packet = store.load_research_packet(research_id)
    candidate = _candidate(
        "gap_supplement", research_id, packet["records"], research_id=research_id
    )
    store.save_candidate(candidate)
    return candidate


def review_candidate(
    candidate_id: str, decision: str, reviewer: str, note: str, store: LocalKnowledgeStore
) -> dict[str, Any]:
    if decision not in {"approve", "reject"}:
        raise ContractError("decision must be approve or reject")
    if not reviewer.strip():
        raise ContractError("reviewer is required")
    candidate = store.load_candidate(candidate_id)
    if candidate["status"] != "pending_review":
        raise ContractError("only pending candidates may be reviewed")
    candidate["status"] = "approved" if decision == "approve" else "rejected"
    candidate["review"] = {"decision": decision, "reviewer": reviewer, "note": note, "reviewed_at": utc_now()}
    store.update_candidate(candidate, "candidate_reviewed")
    return candidate


def query_published(
    version: str, kind: str, text: str, store: LocalKnowledgeStore
) -> dict[str, Any]:
    bundle = store.read_published(version)
    normalized = text.casefold().strip()
    matches = [
        record
        for record in bundle["records"]
        if record["kind"] == kind
        and (not normalized or normalized in " ".join([record["topic"], record["summary"], *record["tags"]]).casefold())
    ]
    return {
        "status": "ok" if matches else "no_data",
        "materials": [{key: value for key, value in record.items() if key not in {"source", "gap_id"}} for record in matches],
        "sources": list({record["source"]["source_id"]: record["source"] for record in matches}.values()),
    }
