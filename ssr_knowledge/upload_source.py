"""Import a user-provided text file with explicit provenance; no network calls."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .acquisition import safe_url
from .catalog import Catalog, USAGE_PURPOSES, identifier, required_text
from .contracts import ContractError
from .store import utc_now


def import_text_source(store: Catalog, path: str, receipt: Any) -> dict[str, Any]:
    fields = {"source_id", "source_url", "title", "original_filename", "library_file_id", "library_version",
              "page_updated", "page_updated_timezone", "license_statement", "license_url", "provided_by", "reviewed_at", "uses"}
    if not isinstance(receipt, dict) or set(receipt) != fields:
        raise ContractError("upload receipt must contain exactly the documented provenance fields")
    identifier(receipt["source_id"])
    source_url, license_url = safe_url(receipt["source_url"]), safe_url(receipt["license_url"])
    for key in fields - {"uses", "source_id", "source_url", "license_url"}:
        required_text(receipt[key], key, 2000)
    if not re.fullmatch(r"libfile_[A-Za-z0-9]+", receipt["library_file_id"]):
        raise ContractError("stable Library file ID required for this user-upload route")
    try:
        reviewed = datetime.fromisoformat(receipt["reviewed_at"])
        if reviewed.tzinfo is None:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise ContractError("reviewed_at needs an explicit timezone") from exc
    uses = receipt["uses"]
    if not isinstance(uses, dict) or set(uses) != USAGE_PURPOSES:
        raise ContractError("upload uses must separately record all four purposes")
    for use in uses.values():
        if not isinstance(use, dict) or set(use) != {"status", "basis"} or use["status"] not in {"allowed", "prohibited", "unknown"}:
            raise ContractError("invalid upload purpose review")
        required_text(use["basis"], "purpose basis")
    if uses["local_cache"]["status"] != "allowed":
        raise ContractError("local_cache must be reviewed allowed before importing an upload")
    p = Path(path)
    if not p.is_file() or not 40 <= p.stat().st_size <= 2_000_000:
        raise ContractError("upload must be a 40-byte to 2-MB local text file")
    raw = p.read_bytes()
    body = raw.decode("utf-8-sig", errors="strict")
    if "\x00" in body:
        raise ContractError("upload contains NUL bytes, expected UTF-8 text")
    source = {"source_id": receipt["source_id"], "url": "library-file:" + receipt["library_file_id"],
              "original_url": source_url, "source_type": "wiki", "title": receipt["title"], "language": "en",
              "declared_version": "user-provided page text; last edited " + receipt["page_updated"] + "; game build unknown",
              "selector": {"tag": "body"}, "interval_seconds": 3,
              "acquisition": {"kind": "user_provided_text", "library_file_id": receipt["library_file_id"],
                              "library_version": receipt["library_version"], "original_filename": receipt["original_filename"]},
              "policy": {"allow_fetch": False, "allow_import": True, "reviewed_at": receipt["reviewed_at"],
                         "terms_url": license_url, "notes": "User-supplied text import only; does not grant or enable website crawling. " + receipt["license_statement"],
                         "uses": uses}}
    metadata = {"acquisition_kind": "user_provided_text", "receipt": receipt, "imported_at": utc_now(),
                "extractor_version": "utf8-upload-v1", "original_url": source_url, "requested_url": None,
                "canonical_url": source_url, "canonical_basis": "user-provided attribution URL; not fetched or independently verified",
                "source_updated_at": receipt["page_updated"], "source_updated_basis": "copied page footer; timezone " + receipt["page_updated_timezone"],
                "body_locator": {"format": "user_provided_plain_text", "line_count": len(body.splitlines())},
                "license_statement": receipt["license_statement"], "license_url": license_url,
                "collector_called_llm": False, "http_requests": 0}
    store.register_source(source)
    result = store.save_snapshot(source, raw, body, metadata)
    store.event(source["source_id"], "user_text_import", {**result, "canonical_url": source_url,
                "library_file_id": receipt["library_file_id"], "http_requests": 0})
    return {**result, "acquisition_kind": "user_provided_text", "source_url": source_url, "http_requests": 0}
