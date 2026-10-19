"""Official installed-game text pairing; source rows stay private and inert."""
from __future__ import annotations

import csv
import io
from collections import defaultdict
from typing import Any

from .contracts import ContractError


def parse_game_csv(body: str) -> dict[str, Any]:
    if "\x00" in body or len(body.encode("utf-8")) > 2_000_000:
        raise ContractError("game localization exceeds 2 MB")
    try:
        rows = list(csv.reader(io.StringIO(body.lstrip("\ufeff"), newline=""), strict=True))
    except csv.Error as exc:
        raise ContractError("invalid game localization CSV") from exc
    if not rows or not rows[0] or rows[0][0] != "CURRENT_LANGUAGE":
        raise ContractError("expected explicit game localization header")
    header = rows[0]
    labels = {"en": "English", "zh-TW": "繁體中文", "zh-CN": "简体中文"}
    if any(header.count(label) != 1 for label in labels.values()) or header[-1] != "ENDLINE":
        raise ContractError("English/Traditional/Simplified columns must each be unique")
    columns = {locale: header.index(label) for locale, label in labels.items()}
    if len(set(columns.values())) != 3:
        raise ContractError("locale columns must be separate")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for number, row in enumerate(rows[1:], 2):
        if len(row) != len(header) or row[-1] != "ENDLINE":
            raise ContractError(f"invalid CSV width/end marker at record {number}")
        if not row[0].startswith("NAME_"):
            continue
        record = {"key": row[0], "en": row[columns["en"]], "zh-TW": row[columns["zh-TW"]],
                  "zh-CN": row[columns["zh-CN"]], "csv_record": number}
        if any(not record[k].strip() or len(record[k]) > 200 for k in ("key", "en")):
            raise ContractError("empty/overlong game item key/name")
        grouped[record["key"]].append(record)
    conflicts = {key: values for key, values in grouped.items()
                 if len({(r["en"], r["zh-TW"], r["zh-CN"]) for r in values}) > 1}
    items = [{**values[0], "csv_records": [r["csv_record"] for r in values]} for key, values in grouped.items() if key not in conflicts]
    return {"parser_version": "peak-game-localization-v1", "header": header, "columns": columns,
            "csv_records": len(rows) - 1, "name_records": sum(map(len, grouped.values())),
            "items": items, "conflicting_keys": conflicts}


def pair_game_names(parsed: dict[str, Any], names: list[str]) -> dict[str, Any]:
    by_english: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in parsed["items"]:
        by_english[item["en"].strip().casefold()].append(item)
    matches, unresolved = [], []
    for name in names:
        found = by_english.get(name.strip().casefold(), [])
        if len(found) == 1 and found[0]["zh-TW"].strip():
            matches.append({"name_en": name, **found[0]})
        else:
            conflicts = [key for key, rows in parsed["conflicting_keys"].items() if any(r["en"].strip().casefold() == name.strip().casefold() for r in rows)]
            reason = "conflicting_game_key" if conflicts else "no_exact_english_name_in_NAME_namespace" if not found else "ambiguous_game_keys" if len(found) > 1 else "traditional_chinese_value_missing"
            unresolved.append({"name_en": name, "reason": reason, "candidate_keys": conflicts or [r["key"] for r in found]})
    return {"parser_version": parsed["parser_version"], "columns": parsed["columns"], "matched_items": len(matches),
            "unmatched_items": len(unresolved), "matches": matches, "unresolved": unresolved, "conflicting_keys": parsed["conflicting_keys"]}


def validate_game_record(canonical_name: str, record: dict[str, Any], snapshot: dict[str, Any]) -> None:
    """Prevent selecting another key or the Simplified column by changing a label."""
    if snapshot["source"].get("acquisition", {}).get("kind") != "installed_game_text":
        return
    key = record.get("game_key")
    import json
    rows = json.loads(snapshot["body"])["items"]
    found = [row for row in rows if row["key"] == key]
    if (len(found) != 1 or found[0]["en"].strip().casefold() != canonical_name.strip().casefold()
            or found[0]["text"] != record["text"] or snapshot["source"]["language"] != record["locale"]):
        raise ContractError("game name/key/locale differs from pinned item pairing")


def pair_saved_game_names(english: dict[str, Any], traditional: dict[str, Any], names: list[str]) -> dict[str, Any]:
    import json
    if (english["source"].get("acquisition", {}).get("kind") != "installed_game_text"
            or traditional["source"].get("acquisition", {}).get("kind") != "installed_game_text"
            or english["source"]["language"] != "en" or traditional["source"]["language"] != "zh-TW"
            or english["raw_sha256"] != traditional["raw_sha256"]):
        raise ContractError("paired locales must come from the same installed extraction")
    en_body, tw_body = json.loads(english["body"]), json.loads(traditional["body"])
    en = en_body["items"]
    tw = {r["key"]: r for r in tw_body["items"]}
    en_receipt, tw_receipt = english["metadata"]["receipt"], traditional["metadata"]["receipt"]
    if (en_body["locale"] != "en" or tw_body["locale"] != "zh-TW" or {r["key"] for r in en} != set(tw)
            or any(en_receipt[k] != tw_receipt[k] for k in ("game_version", "steam_build_id", "bundle_sha256_before", "columns"))):
        raise ContractError("locale extraction versions/columns/keys differ")
    rows = []
    for row in en:
        if row["key"] not in tw or tw[row["key"]]["en"] != row["en"]:
            raise ContractError("locale projections disagree on stable game key")
        rows.append({"key": row["key"], "en": row["en"], "zh-TW": tw[row["key"]]["text"], "csv_records": row["csv_records"]})
    return pair_game_names({"parser_version": "peak-game-localization-v1", "columns": english["metadata"]["receipt"]["columns"],
                            "items": rows, "conflicting_keys": en_body["conflicting_keys"]}, names)
