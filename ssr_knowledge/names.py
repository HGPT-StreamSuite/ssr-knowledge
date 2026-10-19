"""Literal bilingual labels; evidence status never follows from a translation."""
from __future__ import annotations

import unicodedata
from typing import Any

from .contracts import ContractError

STATUSES = {"source_name", "provisional_translation", "provisional_alias", "official_marketing_alias", "community_mod_alias", "game_ui_verified"}
LOCALES = {"en", "zh-TW", "zh-CN", "und"}


def name_key(text: str) -> str:
    """Case/width/whitespace only; keep punctuation, words and variants distinct."""
    return "".join(unicodedata.normalize("NFKC", text).casefold().split())


def name_records(entry: dict[str, Any]) -> list[dict[str, Any]]:
    if "names" in entry:
        return entry["names"]["records"]
    # Legacy display labels have no implicit official status or regional locale.
    return [{"text": text, "locale": "en" if role == "english" else "und", "role": role,
             "status": "unverified_legacy", "citation": None, "basis": "Legacy label; no structured name evidence."}
            for role, text in [("english", entry["name_en"]), ("chinese", entry["name_zh"]),
                               *(("alias", a) for a in entry["aliases"])]]


def validate_names(entry: dict[str, Any], snapshots: dict[str, dict[str, Any]]) -> None:
    if "names" not in entry:
        return
    value = entry["names"]
    if not isinstance(value, dict) or set(value) != {"schema_version", "target_locale", "records"}:
        raise ContractError("names needs schema_version, target_locale, records")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1 or not isinstance(value["target_locale"], str) or value["target_locale"] not in {"zh-TW", "zh-CN"}:
        raise ContractError("names needs an explicit zh-TW or zh-CN target locale")
    records = value["records"]
    if not isinstance(records, list) or not 2 <= len(records) <= 100:
        raise ContractError("names must describe both display names and every alias; maximum 100 evidence records")
    if any(not isinstance(r, dict) or set(r) != {"text", "locale", "role", "status", "citation", "basis"}
           or any(not isinstance(r[k], str) for k in ("text", "locale", "role", "status", "basis")) for r in records):
        raise ContractError("invalid name record fields")
    if {r.get("text") for r in records[2:] if isinstance(r, dict)} != set(entry["aliases"]):
        raise ContractError("name records must cover every alias without adding unrelated labels")
    for index, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != {"text", "locale", "role", "status", "citation", "basis"}:
            raise ContractError("invalid name record fields")
        role, text = (("english", entry["name_en"]) if index == 0 else ("chinese", entry["name_zh"]) if index == 1 else ("alias", record["text"]))
        if record["text"] != text or record["role"] != role:
            raise ContractError("name records must match display names and aliases in order")
        if record["locale"] not in LOCALES or record["status"] not in STATUSES:
            raise ContractError("invalid name locale or evidence status")
        if role == "english" and record["locale"] != "en" or role == "chinese" and record["locale"] != value["target_locale"]:
            raise ContractError("display name locale differs from its role/target")
        if not isinstance(record["basis"], str) or not record["basis"].strip() or len(record["basis"]) > 1000:
            raise ContractError("each name needs a bounded evidence/translation basis")
        status, citation = record["status"], record["citation"]
        if status in {"official_marketing_alias", "community_mod_alias"} and role != "alias":
            raise ContractError("marketing/community terms are aliases, not verified display names")
        if status in {"provisional_translation", "provisional_alias"}:
            if citation is not None:
                raise ContractError("provisional names use an editorial basis, not a verified name citation")
            continue
        if type(citation) is not int or not 0 <= citation < len(entry["citations"]):
            raise ContractError("attested names require a pinned citation index")
        reference = entry["citations"][citation]
        snapshot = snapshots[reference["snapshot_id"]]
        if text not in reference["evidence_quote"] or text not in snapshot["body"]:
            raise ContractError("attested name is absent from its pinned quote/body")
        if status in {"official_marketing_alias", "game_ui_verified"}:
            evidence = snapshot["metadata"].get("name_evidence", {})
            kind = "official_marketing" if status == "official_marketing_alias" else "game_ui"
            if (not isinstance(evidence, dict) or snapshot["source"]["source_type"] != "official" or snapshot["source"].get("language") != record["locale"]
                    or evidence.get("kind") != kind or evidence.get("locale") != record["locale"]):
                raise ContractError("official names require matching source, locale and evidence scope; marketing is not game UI")
        if status == "community_mod_alias":
            evidence = snapshot["metadata"].get("name_evidence", {})
            if (not isinstance(evidence, dict) or snapshot["source"]["source_type"] not in {"wiki", "third_party_analysis"}
                    or snapshot["source"].get("language") != record["locale"]
                    or evidence.get("kind") != "community_mod" or evidence.get("locale") != record["locale"]):
                raise ContractError("community mod aliases require matching nonofficial source/locale/scope")
