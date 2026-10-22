"""Import bounded operator-selected index excerpts, never a full page fetch."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .acquisition import safe_url
from .catalog import Catalog, USAGE_PURPOSES, digest, identifier, required_text
from .contracts import ContractError
from .store import utc_now


def import_web_excerpt(store: Catalog, path: str, receipt: Any) -> dict[str, Any]:
    fields = {"source_id", "source_url", "title", "retrieved_at", "index_date_label", "raw_sha256", "queries",
              "direct_fetch_status", "license_statement", "license_url", "uses", "method"}
    if not isinstance(receipt, dict) or set(receipt) != fields or receipt["method"] != "web_search_index_excerpt":
        raise ContractError("exact search-index receipt required; this is not a direct HTTP page fetch")
    identifier(receipt["source_id"])
    url, license_url = safe_url(receipt["source_url"]), safe_url(receipt["license_url"])
    for key in ("title", "index_date_label", "license_statement"):
        required_text(receipt[key], key, 2000)
    try:
        at = datetime.fromisoformat(receipt["retrieved_at"])
        if at.tzinfo is None or not 0 <= (datetime.now(timezone.utc) - at).total_seconds() <= 31 * 86400: raise ValueError
    except (TypeError, ValueError) as exc:
        raise ContractError("recent timezone-aware retrieval timestamp required") from exc
    if type(receipt["direct_fetch_status"]) is not int or not 400 <= receipt["direct_fetch_status"] <= 599:
        raise ContractError("retain the observed page failure; excerpt import is not HTTP 200")
    if not isinstance(receipt["queries"], list) or not 1 <= len(receipt["queries"]) <= 10:
        raise ContractError("one to ten actual search queries required")
    for query in receipt["queries"]: required_text(query, "query", 500)
    uses = receipt["uses"]
    if not isinstance(uses, dict) or set(uses) != USAGE_PURPOSES: raise ContractError("four purpose reviews required")
    for use in uses.values():
        if not isinstance(use, dict) or set(use) != {"status", "basis"} or use["status"] not in {"allowed", "prohibited", "unknown"}:
            raise ContractError("invalid excerpt purpose review")
        required_text(use["basis"], "purpose basis")
    if uses["local_cache"]["status"] != "allowed": raise ContractError("bounded excerpt caching requires a recorded basis")
    file = Path(path)
    if not file.is_file() or not 1 <= file.stat().st_size <= 8000: raise ContractError("bounded UTF-8 excerpt file required")
    raw = file.read_bytes(); body = raw.decode("utf-8-sig", errors="strict")
    if "\x00" in body or digest(raw) != receipt["raw_sha256"] or len(body.split()) > 200:
        raise ContractError("excerpt hash mismatch, NUL, or more than 200 words")
    source = {"source_id": receipt["source_id"], "url": "web-search-excerpt:" + receipt["source_id"], "original_url": url,
              "source_type": "wiki", "title": receipt["title"], "language": "en", "selector": {"tag": "body"}, "interval_seconds": 3,
              "declared_version": "Search index excerpt; date label " + receipt["index_date_label"] + "; page/build version unverified",
              "acquisition": {"kind": "web_search_excerpt", "method": receipt["method"]},
              "policy": {"allow_fetch": False, "allow_import": True, "reviewed_at": receipt["retrieved_at"], "terms_url": license_url,
                         "notes": receipt["license_statement"], "uses": uses}}
    metadata = {"acquisition_kind": "web_search_excerpt", "receipt": receipt, "imported_at": utc_now(),
                "extractor_version": "operator-selected-search-excerpt-v1", "original_url": url, "requested_url": None,
                "canonical_url": url, "canonical_basis": "Search-result attribution; not a retrieved canonical page",
                "source_updated_at": None, "source_updated_basis": "Unknown; index date label is not a verified page update",
                "body_locator": {"format": "search_index_excerpt", "line_count": len(body.splitlines())},
                "full_page_acquired": False, "collector_called_llm": False, "http_requests": 0}
    store.register_source(source)
    result = store.save_snapshot(source, raw, body, metadata)
    store.event(source["source_id"], "web_excerpt_import", {**result, "http_requests": 0, "full_page_acquired": False})
    return {**result, "acquisition_kind": "web_search_excerpt", "http_requests": 0, "full_page_acquired": False}
