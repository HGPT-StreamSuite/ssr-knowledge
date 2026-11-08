"""Bounded, synthetic-only native acceptance adapter. No server or client paths."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from .catalog import Catalog, required_text
from .contracts import ContractError, read_json, validate
from .store import LocalKnowledgeStore
from .workflows import prepare_prebuild, prepare_gap_research, prepare_gap_supplement

FORMAT = "ssr.knowledge.acceptance.request.v1"
MAX_BYTES = 65536
ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = frozenset({"candidate.schema.json", "gap-export.schema.json", "prebuild-source.schema.json",
                     "published-bundle.schema.json", "record.schema.json", "research-packet.schema.json",
                     "supplement-records.schema.json", "tool-config.schema.json"})
OPERATIONS = frozenset({"validate", "prebuild_preview", "gap_supplement_preview", "catalog_check"})
SCENARIOS = frozenset({"pending", "published", "policy_denied", "source_changed", "bad_citation"})
BASE_RESPONSE = {"format": "ssr.knowledge.acceptance.response.v1", "synthetic_only": True,
                 "network_used": False, "llm_used": False, "production_data_used": False}


def exact(value: Any, fields: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise ContractError(label + " must contain exactly: " + ", ".join(sorted(fields)))


def bounded(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_BYTES:
        raise ContractError("request exceeds 65536 UTF-8 bytes")
    pending = [(value, 0)]; nodes = 0
    while pending:
        item, depth = pending.pop(); nodes += 1
        if depth > 32 or nodes > 5000:
            raise ContractError("request exceeds depth 32 or 5000 nodes")
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise ContractError("JSON object keys must be strings")
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)


def synthetic_records(records: Any) -> None:
    if not isinstance(records, list) or not 1 <= len(records) <= 10:
        raise ContractError("acceptance requires 1 to 10 synthetic records")
    for record in records:
        validate(record, "record.schema.json")
        source = record["source"]
        if (not record["record_id"].startswith("fixture-") or
                source["source_type"] not in {"fictional_wiki", "fictional_primary_source", "synthetic"} or
                not source["locator"].startswith("fixture://")):
            raise ContractError("only fixture- records with fictional sources and fixture:// locators are accepted")


def check_request(request: Any) -> tuple[str, dict]:
    bounded(request)
    exact(request, {"format", "operation", "input"}, "request")
    if request["format"] != FORMAT or not isinstance(request["operation"], str) or request["operation"] not in OPERATIONS:
        raise ContractError("unsupported request format or fixed operation")
    operation, payload = request["operation"], request["input"]
    if operation == "validate":
        exact(payload, {"schema", "value"}, "validate input")
        if not isinstance(payload["schema"], str) or payload["schema"] not in SCHEMAS:
            raise ContractError("schema must be one of the eight fixed repo contracts")
    elif operation == "prebuild_preview":
        exact(payload, {"source"}, "prebuild input")
        validate(payload["source"], "prebuild-source.schema.json")
        synthetic_records(payload["source"]["records"])
    elif operation == "gap_supplement_preview":
        exact(payload, {"gaps", "records"}, "supplement input")
        validate(payload["gaps"], "gap-export.schema.json")
        validate(payload["records"], "supplement-records.schema.json")
        synthetic_records(payload["records"]["records"])
    else:
        exact(payload, {"scenario", "query"}, "catalog input")
        if not isinstance(payload["scenario"], str) or payload["scenario"] not in SCENARIOS:
            raise ContractError("unknown fixed synthetic catalog scenario")
        required_text(payload["query"], "search text", 200)
    return operation, payload


def catalog_check(payload: dict, root: Path) -> dict:
    """Execute real Catalog methods against a fresh, self-authored fictional DB."""
    config = read_json(ROOT / "fixtures" / "collection-example-source.synthetic.json")
    config["source_type"] = "wiki"
    body = "Synthetic Lunar Rope is fictional. It makes a blue landing platform."
    with Catalog(root / "catalog") as store:
        before = store.stats()["counts"]
        store.register_source(config)
        snapshot = store.save_snapshot(config, body.encode(), body, {"fixture_only": True, "http_requests": 0})
        draft = {"entry_id": "fixture-native-rope", "game": "PEAK:3527290", "category": "item",
                 "name_en": "Lunar Rope", "name_zh": "月光繩", "aliases": ["月繩"],
                 "summary_zh": "合成測試：虛構月光繩形成藍色平台。", "evidence_class": "wiki",
                 "editor": "synthetic-acceptance", "game_version": "synthetic-v1",
                 "limitations": "Fictional fixture; no real PEAK facts or user approval.",
                 "citations": [{"snapshot_id": snapshot["snapshot_id"], "locator": "synthetic body",
                                "evidence_quote": "Lunar Rope is fictional."}]}
        if payload["scenario"] == "bad_citation":
            draft["citations"][0]["evidence_quote"] = "Invented quote absent from the saved body"
            try:
                store.import_drafts({"entries": [draft]})
            except ContractError as exc:
                return {"state": "rejected", "reason": str(exc), "before": before, "after": store.stats()["counts"]}
            raise RuntimeError("invalid synthetic citation was accepted")
        saved = store.import_drafts({"entries": [draft]})[0]
        duplicate = store.import_drafts({"entries": [draft]})[0]
        publication_block = None
        if payload["scenario"] == "pending":
            try:
                store.publish(draft["entry_id"], saved["revision_id"])
            except ContractError as exc:
                publication_block = str(exc)
        else:
            # This attestation is deliberately a synthetic test event in a disposable DB.
            store.review(draft["entry_id"], saved["revision_id"], "approve", "synthetic-fixture-only",
                         "Simulated review of fictional acceptance data, not a user decision.", True)
            store.publish(draft["entry_id"], saved["revision_id"])
        if payload["scenario"] == "policy_denied":
            config["policy"]["uses"]["search_index"] = {"status": "prohibited", "basis": "Fixed negative synthetic scenario."}
            store.register_source(config)
        elif payload["scenario"] == "source_changed":
            store.save_snapshot(config, (body + " Changed source.").encode(), body + " Changed source.", {"fixture_only": True})
        entry = store.entry(draft["entry_id"])
        result = {"state": "executed", "before": before, "saved": saved, "duplicate": duplicate,
                  "publication_block": publication_block, "entry": entry,
                  "formal": store.search(payload["query"]), "preview": store.search(payload["query"], preview=True),
                  "after": store.stats()["counts"]}
    # A genuinely new read-only connection, after closing the writer.
    with Catalog(root / "catalog", read_only=True) as reader:
        result["readback"] = {"revision_id": reader.entry(draft["entry_id"])["revision_id"],
                              "formal": reader.search(payload["query"]), "query_only": reader.db.execute("PRAGMA query_only").fetchone()[0]}
    return result


def handle_request(request: Any) -> dict:
    response = dict(BASE_RESPONSE)
    try:
        operation, payload = check_request(request)
    except (ContractError, ValueError, TypeError, RecursionError) as exc:
        return {**response, "status": "rejected", "errors": [str(exc)], "temporary_state_created": False}
    response["operation"] = operation
    if operation == "validate":
        try:
            validate(payload["value"], payload["schema"])
            result = {"status": "schema_valid", "schema": payload["schema"], "errors": []}
        except ContractError as exc:
            result = {"status": "schema_invalid", "schema": payload["schema"], "errors": str(exc).split("; ")}
        return {**response, "status": "ok", "data": result, "temporary_state_created": False}
    try:
        with tempfile.TemporaryDirectory(prefix="ssr-knowledge-acceptance-") as directory:
            root = Path(directory)
            response.update(temporary_state_created=True, before={"files": 0})
            try:
                if operation == "catalog_check":
                    result = catalog_check(payload, root)
                else:
                    store = LocalKnowledgeStore(root / "offline")
                    if operation == "prebuild_preview":
                        candidate = prepare_prebuild(payload["source"], store)
                        result = {"candidate": candidate, "readback": store.load_candidate(candidate["candidate_id"])}
                    else:
                        packet = prepare_gap_research(payload["gaps"], payload["records"], store)
                        candidate = prepare_gap_supplement(packet["research_id"], store)
                        result = {"research": packet, "candidate": candidate,
                                  "readback": store.load_candidate(candidate["candidate_id"])}
                response.update(status="ok", data=result)
            except ContractError as exc:
                response.update(status="rejected", errors=[str(exc)])
            response["after"] = {"artifacts": [{"name": file.relative_to(root).as_posix(), "bytes": file.stat().st_size,
                                                "sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
                                               for file in sorted(root.rglob("*")) if file.is_file()]}
        response["temporary_state_removed"] = not root.exists()
        return response
    except OSError as exc:
        return {**response, "status": "error", "errors": ["native temporary workspace I/O error"],
                "error_type": type(exc).__name__, "errno": exc.errno}


def handle_json(raw: bytes) -> dict:
    if len(raw) > MAX_BYTES:
        return {**BASE_RESPONSE, "status": "rejected", "errors": ["request exceeds 65536 UTF-8 bytes"]}
    try:
        def invalid_constant(value):
            raise ValueError("non-finite JSON number is not accepted")
        return handle_request(json.loads(raw.decode("utf-8"), parse_constant=invalid_constant))
    except (UnicodeError, ValueError, RecursionError) as exc:
        return {**BASE_RESPONSE, "status": "rejected", "errors": ["invalid strict UTF-8 JSON: " + str(exc)]}
