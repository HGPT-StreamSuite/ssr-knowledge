"""Pinned editorial organization, game badge definitions and private relations.

This module reads already saved evidence only. It neither fetches sources nor
approves content. Editorial groupings and translations remain review material.
"""
from __future__ import annotations

import csv
import io
import re
from typing import Any
from urllib.parse import urlsplit

from .catalog import identifier, required_text
from .contracts import ContractError

TOPICS = ("effects", "acquisition", "conditions", "cooking", "badge_hints")


def cached_badges(raw: bytes) -> list[dict[str, Any]]:
    """Pair exact NAME_/DESC_ suffixes and explicitly named locale columns."""
    if not 1 <= len(raw) <= 2_000_000:
        raise ContractError("bounded cached localization required")
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
    if not rows or any(rows[0].count(x) != 1 for x in ("English", "繁體中文", "ENDLINE")):
        raise ContractError("badge locale columns must be explicit and unique")
    en, tw = rows[0].index("English"), rows[0].index("繁體中文")
    by_key: dict[str, tuple[int, list[str]]] = {}
    conflicts = set()
    for number, row in enumerate(rows[1:], 2):
        if len(row) != len(rows[0]) or row[-1] != "ENDLINE":
            raise ContractError("malformed cached badge CSV row")
        if row[0] in by_key and any(by_key[row[0]][1][i] != row[i] for i in (en, tw)):
            conflicts.add(row[0])
        by_key.setdefault(row[0], (number, row))
    result = []
    for key, (number, row) in by_key.items():
        if not key.startswith("NAME_") or not row[en].endswith(" BADGE"):
            continue
        desc_key = "DESC_" + key[5:]
        if key in conflicts or desc_key in conflicts:
            raise ContractError("conflicting cached badge localization key")
        if desc_key not in by_key:
            raise ContractError("badge description missing for exact game key")
        desc_number, desc = by_key[desc_key]
        if not all((row[en], row[tw], desc[en], desc[tw])):
            raise ContractError("badge name/condition locale is blank")
        result.append({"game_key": key, "description_key": desc_key,
                       "name_en": row[en], "name_zh": row[tw],
                       "condition_en": desc[en], "condition_zh": desc[tw],
                       "name_csv_record": number, "condition_csv_record": desc_number})
    return result


def badge_drafts(store: Any, english_id: str, traditional_id: str) -> dict[str, Any]:
    """Project existing official CSV into pending definitions, with no inference."""
    en, tw = store.snapshot(english_id, True), store.snapshot(traditional_id, True)
    if (en["source"]["language"] != "en" or tw["source"]["language"] != "zh-TW"
            or en["raw_sha256"] != tw["raw_sha256"]):
        raise ContractError("badge locales must come from the same saved extraction")
    raw = store.db.execute("SELECT raw FROM snapshots WHERE snapshot_id=?", (english_id,)).fetchone()[0]
    entries = []
    for row in cached_badges(raw):
        names = []
        for text, locale, role, index in ((row["name_en"], "en", "english", 0), (row["name_zh"], "zh-TW", "chinese", 1), (row["name_en"], "en", "alias", 0)):
            names.append({"text": text, "locale": locale, "role": role, "status": "game_ui_verified", "citation": index,
                          "game_key": row["game_key"], "basis": "Exact key and explicit locale in already saved official game text."})
        value = {"entry_id": "peak-badge-" + re.sub(r"[^a-z0-9]+", "-", row["game_key"][5:].casefold()).strip("-"),
                 "game": "PEAK:3527290", "category": "achievement", "name_en": row["name_en"], "name_zh": row["name_zh"],
                 "aliases": [row["name_en"]], "summary_zh": row["condition_zh"], "evidence_class": "official",
                 "editor": "Deterministic projection of cached official localization; not human approved or gameplay tested.",
                 "game_version": en["source"]["declared_version"],
                 "limitations": "遊戲徽章定義，非玩家進度；條件為官方顯示文字，未由程式判定實際解鎖邏輯或與 Steam 成就等同。",
                 "names": {"schema_version": 1, "target_locale": "zh-TW", "records": names,
                           "preferred": {"en": row["name_en"], "zh-TW": row["name_zh"]}},
                 "citations": [{"snapshot_id": sid, "locator": row["game_key"] + "; " + row["description_key"] + "; cached Localized_Text CSV " + locale,
                                "evidence_quote": row["name_en"] if locale == "en" else row["name_zh"]}
                               for sid, locale in ((english_id, "en"), (traditional_id, "zh-TW"))],
                 "badge_details": {"schema_version": 1, "kind": "game_badge", "game_key": row["game_key"], "description_key": row["description_key"],
                                   "condition_en": row["condition_en"], "condition_zh": row["condition_zh"], "condition_status": "game_ui_text",
                                   "steam_equivalence": "unverified", "english_citation": 0, "traditional_citation": 1}}
        store._validate_draft(value)
        entries.append(value)
    return {"entries": entries}


def validate_organization(entry: dict[str, Any]) -> None:
    if "organization" in entry:
        value = entry["organization"]
        fields = {"schema_version", "method", "source_row_sha256", "topics", "notes_zh"}
        if ("item_details" not in entry or not isinstance(value, dict) or set(value) != fields
                or value["schema_version"] != 1 or value["method"] != "agent_edited_pending_review"):
            raise ContractError("organization needs pinned item notes and pending editorial method")
        detail = entry["item_details"]
        if value["source_row_sha256"] != detail["source_row_sha256"]:
            raise ContractError("organization row differs from pinned item")
        if not isinstance(value["topics"], dict) or set(value["topics"]) != set(TOPICS):
            raise ContractError("organization needs the documented topics")
        indices = []
        for topic in TOPICS:
            values = value["topics"][topic]
            if not isinstance(values, list) or any(type(i) is not int for i in values):
                raise ContractError("topic indices must be integer arrays")
            indices.extend(values)
        if sorted(indices) != list(range(len(detail["notes_en"]))):
            raise ContractError("each pinned note must be assigned exactly once")
        if not isinstance(value["notes_zh"], list) or len(value["notes_zh"]) != len(detail["notes_en"]):
            raise ContractError("organized translations must cover every pinned note")
        for text in value["notes_zh"]:
            required_text(text, "organized note", 800)
    if "detail_page" in entry:
        value = entry["detail_page"]
        if (entry["category"] != "item" or not isinstance(value, dict)
                or set(value) != {"url", "status", "basis", "checked_at", "http_status"}
                or value["status"] not in {"user_provided_unverified", "verified"}):
            raise ContractError("invalid detail page metadata")
        url = urlsplit(required_text(value["url"], "detail URL", 1000))
        if (url.scheme != "https" or url.hostname != "peak.wiki.gg" or url.username or url.password
                or url.port not in (None, 443) or not url.path.startswith("/wiki/") or url.query or url.fragment):
            raise ContractError("detail page must be a bounded exact PEAK Wiki URL")
        required_text(value["basis"], "detail URL basis", 800)
        required_text(value["checked_at"], "detail check time", 100)
        if type(value["http_status"]) is not int or not 100 <= value["http_status"] <= 599:
            raise ContractError("detail check needs observed HTTP status")
        if value["status"] == "verified" and value["http_status"] != 200:
            raise ContractError("blocked detail page cannot be verified")


def validate_badge(entry: dict[str, Any], snapshots: dict[str, dict[str, Any]], raw_lookup: Any) -> None:
    if "badge_details" not in entry:
        return
    badge = entry["badge_details"]
    fields = {"schema_version", "kind", "game_key", "description_key", "condition_en", "condition_zh",
              "condition_status", "steam_equivalence", "english_citation", "traditional_citation"}
    if (entry["category"] != "achievement" or not isinstance(badge, dict) or set(badge) != fields
            or badge["schema_version"] != 1 or badge["kind"] != "game_badge"
            or badge["condition_status"] != "game_ui_text" or badge["steam_equivalence"] != "unverified"):
        raise ContractError("badge definition is game text, not Steam equivalence or player progress")
    pinned = []
    for field, locale in (("english_citation", "en"), ("traditional_citation", "zh-TW")):
        index = badge[field]
        if type(index) is not int or not 0 <= index < len(entry["citations"]):
            raise ContractError("badge citation index invalid")
        snap = snapshots[entry["citations"][index]["snapshot_id"]]
        if (snap["source"]["source_type"] != "official" or snap["source"]["language"] != locale
                or snap["source"].get("acquisition", {}).get("kind") != "installed_game_text"):
            raise ContractError("badge needs official cached English and Traditional sources")
        pinned.append(snap)
    if pinned[0]["raw_sha256"] != pinned[1]["raw_sha256"]:
        raise ContractError("badge locale versions differ")
    rows = [b for b in cached_badges(raw_lookup(pinned[0]["snapshot_id"])) if b["game_key"] == badge["game_key"]]
    if len(rows) != 1:
        raise ContractError("badge key not present in cached official CSV")
    row = rows[0]
    if any(badge[k] != row[k] for k in ("description_key", "condition_en", "condition_zh")) or any(entry[k] != row[k] for k in ("name_en", "name_zh")):
        raise ContractError("badge text differs from pinned game key/locale")


def validate_links(entry: dict[str, Any], lookup: Any, snapshots: dict[str, dict[str, Any]]) -> None:
    links = entry.get("links", [])
    if not isinstance(links, list) or len(links) > 30:
        raise ContractError("bounded links array required")
    seen = set()
    for link in links:
        if (not isinstance(link, dict) or set(link) != {"target_entry_id", "kind", "citation", "note_index", "evidence_text"}
                or link["kind"] not in {"badge_hint", "condition_mentions_item"}):
            raise ContractError("invalid entry relation")
        target_id = identifier(link["target_entry_id"])
        target = lookup(target_id)
        if target_id == entry["entry_id"] or (link["kind"], target_id) in seen:
            raise ContractError("self/duplicate entry relation")
        seen.add((link["kind"], target_id))
        index = link["citation"]
        if type(index) is not int or not 0 <= index < len(entry["citations"]):
            raise ContractError("relation citation index invalid")
        required_text(link["evidence_text"], "relation evidence", 800)
        if link["kind"] == "badge_hint":
            from .item_table import validate_item_details
            i = link["note_index"]
            detail = entry.get("item_details", {})
            if (entry["category"] != "item" or target.get("badge_details", {}).get("kind") != "game_badge"
                    or type(i) is not int or not 0 <= i < len(detail.get("notes_en", []))
                    or link["evidence_text"] != detail["notes_en"][i]
                    or not re.search(r"(?<!\w)" + re.escape(target["name_en"]) + r"(?!\w)", link["evidence_text"], re.IGNORECASE)
                    or not validate_item_details(detail, entry["name_en"], snapshots[entry["citations"][index]["snapshot_id"]]["body"])):
                raise ContractError("badge hint differs from literal pinned item note")
        else:
            badge = entry.get("badge_details", {})
            label = re.sub(r"[^a-z0-9]", "", target["name_en"].casefold())
            observed = re.sub(r"[^a-z0-9]", "", link["evidence_text"].casefold())
            if (not badge or target["category"] != "item" or link["note_index"] is not None
                    or index != badge["english_citation"] or link["evidence_text"] not in badge["condition_en"]
                    or observed not in {label, label + "s"}):
                raise ContractError("condition relation differs from official badge condition")
