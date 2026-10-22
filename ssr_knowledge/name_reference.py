"""Import bounded, reviewed name-reference text, without a network collector."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .acquisition import safe_url
from .catalog import Catalog, USAGE_PURPOSES, digest, identifier, required_text
from .contracts import ContractError
from .store import utc_now


def import_name_reference(store: Catalog, path: str, receipt: Any) -> dict[str, Any]:
    fields = {"source_id", "source_url", "title", "locale", "evidence_kind", "acquisition_method", "version",
              "upstream_commit", "upstream_blob_sha", "raw_sha256", "license_statement", "license_url", "reviewed_at", "uses"}
    if not isinstance(receipt, dict) or set(receipt) != fields:
        raise ContractError("name reference receipt must contain exactly the documented fields")
    identifier(receipt["source_id"])
    url, license_url = safe_url(receipt["source_url"]), safe_url(receipt["license_url"])
    for key in {"title", "acquisition_method", "version", "license_statement", "reviewed_at"}:
        required_text(receipt[key], key, 2000)
    if receipt["locale"] not in {"en", "zh-TW", "zh-CN"} or receipt["evidence_kind"] not in {"community_mod", "official_marketing"}:
        raise ContractError("this reference route accepts community mod or official marketing text, not game UI proof")
    if receipt["acquisition_method"] not in {"github_connector", "web_reference_excerpt"}:
        raise ContractError("explicit connector/excerpt acquisition method required")
    try:
        if datetime.fromisoformat(receipt["reviewed_at"]).tzinfo is None: raise ValueError
    except (TypeError, ValueError) as exc:
        raise ContractError("reviewed_at requires a timezone") from exc
    uses = receipt["uses"]
    if not isinstance(uses, dict) or set(uses) != USAGE_PURPOSES:
        raise ContractError("reference uses must separately record four purposes")
    for use in uses.values():
        if not isinstance(use, dict) or set(use) != {"status", "basis"} or use["status"] not in {"allowed", "prohibited", "unknown"}:
            raise ContractError("invalid reference usage review")
        required_text(use["basis"], "reference usage basis")
    if uses["local_cache"]["status"] != "allowed":
        raise ContractError("local_cache must be reviewed allowed")
    file = Path(path)
    if not file.is_file() or not 1 <= file.stat().st_size <= 2_000_000:
        raise ContractError("name reference must be a 1-byte to 2-MB UTF-8 file")
    raw = file.read_bytes()
    body = raw.decode("utf-8-sig", errors="strict")
    if "\x00" in body or digest(raw) != receipt["raw_sha256"]:
        raise ContractError("name reference text/hash mismatch")
    commit, blob = receipt["upstream_commit"], receipt["upstream_blob_sha"]
    if receipt["acquisition_method"] == "github_connector":
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit) or not isinstance(blob, str) or not re.fullmatch(r"[0-9a-f]{40}", blob):
            raise ContractError("connector reference requires pinned full commit and blob SHA")
        if "/blob/" + commit + "/" not in url:
            raise ContractError("connector attribution URL must pin the same commit")
        if hashlib.sha1(("blob " + str(len(raw)) + "\0").encode() + raw).hexdigest() != blob:
            raise ContractError("upstream Git blob SHA does not match exact bytes")
    elif commit is not None or blob is not None:
        raise ContractError("web excerpt is not a Git blob or full website snapshot")
    source = {"source_id": receipt["source_id"], "url": url, "original_url": url,
              "source_type": "wiki" if receipt["evidence_kind"] == "community_mod" else "official", "title": receipt["title"],
              "language": receipt["locale"], "declared_version": receipt["version"], "selector": {"tag": "body"}, "interval_seconds": 3,
              "acquisition": {"kind": "local_name_reference", "method": receipt["acquisition_method"]},
              "policy": {"allow_fetch": False, "allow_import": True, "reviewed_at": receipt["reviewed_at"], "terms_url": license_url,
                         "notes": "Local reviewed name reference only; no direct HTTP route. " + receipt["license_statement"], "uses": uses}}
    metadata = {"acquisition_kind": "local_name_reference", "receipt": receipt, "imported_at": utc_now(), "extractor_version": "name-reference-utf8-v1",
                "original_url": url, "canonical_url": url, "requested_url": None, "canonical_basis": "connector/excerpt attribution, not a collector HTTP fetch",
                "body_locator": {"format": "local_name_reference", "line_count": len(body.splitlines())},
                "source_updated_at": None, "source_updated_basis": "unknown; fixed commit/version retained separately",
                "license_statement": receipt["license_statement"], "license_url": license_url,
                "name_evidence": {"kind": receipt["evidence_kind"], "locale": receipt["locale"]}, "collector_called_llm": False, "http_requests": 0}
    store.register_source(source)
    result = store.save_snapshot(source, raw, body, metadata)
    store.event(source["source_id"], "name_reference_import", {**result, "http_requests": 0})
    return {**result, "acquisition_kind": "local_name_reference", "http_requests": 0}
