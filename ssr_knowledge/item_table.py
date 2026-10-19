"""Deterministic parser for user-supplied PEAK Items copied text; never fetches URLs."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .catalog import digest, normalize
from .contracts import ContractError

PARSER_VERSION = "peak-items-pasted-v1"
STATS = {"weight": "Weight", "hunger": "Hunger", "bonus_stamina": "Bonus stamina", "poison": "Poison"}
BIOMES = {"Any", "Airport", "Shore", "Tropics", "Roots", "Mesa", "Alpine", "Caldera", "The Kiln", "Peak", "Gloom", "The Citadel"}
LOCATIONS = {"Tomb", "Crash Site", "Campfires", "Campfire", "Photobooth", "On ground", "In Luggage", "Scout Statue", "Stone Scout"}
ROW = re.compile(r"^([^\t]+)\t\1\tWeight\s+([−-]?\d+(?:\.\d+)?)(?:\t|$)")
STATUS_LABELS = ("Bonus stamina", "Invincibility", "Drowsy", "Poison", "Heat", "Cold", "Injury", "Spores", "Thorns", "Curse", "Petrify", "Stamina", "Weight")


def statistic(raw: str, label: str) -> dict[str, Any]:
    raw = raw.strip()
    if raw.lower() == "n/a":
        return {"state": "source_na", "value": None, "raw": raw}
    if not raw:
        return {"state": "missing", "value": None, "raw": raw}
    match = re.fullmatch(re.escape(label) + r"\s+([−-]?\d+(?:\.\d+)?)", raw)
    if not match:
        return {"state": "unparsed", "value": None, "raw": raw}
    number = float(match[1].replace("−", "-"))
    return {"state": "value", "value": int(number) if number.is_integer() else number, "raw": raw}


def clean_notes(lines: list[str]) -> list[str]:
    """Only remove known copied icon labels and duplicated adjacent badge text."""
    parts: list[str] = []
    last_input = None
    for line in lines:
        line = " ".join(line.split())
        if not line or line == last_input:
            continue
        last_input = line
        for label in STATUS_LABELS:
            line = re.sub(r"\b" + re.escape(label) + r"\s+" + re.escape(label) + r"\b", label, line)
        # Badge links were pasted on their own lines twice; attach them to the
        # surrounding sentence without treating them as additional item rows.
        if parts and (line.endswith("Badge") or line == "."):
            parts[-1] += ("" if line == "." else " ") + line
        else:
            parts.append(line)
    return parts


def parse_peak_items(body: str) -> dict[str, Any]:
    lines = body.splitlines()
    declared = re.search(r"There are a total of (\d+) items", body)
    table = next((i for i, line in enumerate(lines) if line.startswith("Icon\tName\tWeight\tHunger\tBonus")), None)
    if table is None:
        raise ContractError("PEAK copied Items table header not found")
    end = next((i for i in range(table + 1, len(lines)) if lines[i].startswith("Category:")), len(lines))
    # Every tabular row is a boundary, including malformed rows. Its following
    # description stays quarantined until the next row, never on the prior item.
    boundaries = [i for i in range(table + 1, end) if "\t" in lines[i]
                  and not lines[i].startswith("Stamina\tPoison\tBiome\tLocation\tNotes")]
    if not any(ROW.match(lines[i]) for i in boundaries):
        raise ContractError("no recognizable PEAK item rows")
    rows: list[dict[str, Any]] = []
    unparsed = []
    for n, start in enumerate(boundaries):
        stop = boundaries[n + 1] if n + 1 < len(boundaries) else end
        if not ROW.match(lines[start]):
            unparsed.append({"line": start + 1, "text": lines[start], "reason": "unrecognized tabular row"})
            continue
        cells = lines[start].split("\t")
        while cells and cells[-1] == "":
            cells.pop()
        if len(cells) != 6:
            unparsed.append({"line": start + 1, "text": lines[start], "reason": "expected icon/name and four statistic cells"})
            continue
        stats = {key: statistic(raw, label) for (key, label), raw in zip(STATS.items(), cells[2:])}
        trailing = [l.strip() for l in lines[start + 1:stop] if l.strip()]
        biomes, locations, notes = [], [], []
        in_notes = False
        for line in trailing:
            if not in_notes and line in BIOMES and not locations:
                biomes.append(line)
            elif not in_notes and (line in LOCATIONS or line == "Peak" and locations):
                locations.append(line)
            else:
                in_notes = True
                notes.append(line)
        cleaned = clean_notes(notes)
        acquisition = [line for line in cleaned if re.search(r"^(?:Source:|Found |Obtained |Can only be found )|\bchance to (?:spawn|appear)\b", line)]
        restrictions = [line for line in cleaned if re.search(r"\b(?:Cannot|cannot|Does not spawn|Limited to|Takes \d|Lasts for|Can be used \d|while actively held|except |only )", line)]
        cooking = [line for line in cleaned if line.startswith("Cooking:") or "cook" in line.lower()]
        issues = [f"{key}:{v['state']}" for key, v in stats.items() if v["state"] in {"missing", "unparsed"}]
        if not biomes:
            issues.append("biome_missing")
        if not locations and not acquisition:
            issues.append("acquisition_unspecified")
        if not cleaned:
            issues.append("notes_unspecified")
        if any(re.search(r"\b(Poison|Heat|Cold|Drowsy|Injury|Spores|Curse|Petrify)\b", s) and not re.search(r"\d", s) and re.search(r"^(Removes|Heals|Inflicts)", s) for s in cleaned):
            issues.append("status_amount_unspecified")
        if any("Cooking:" in s and "Poison" in s for s in cleaned) and stats["poison"]["state"] == "source_na":
            issues.append("cooking_mentions_poison_but_column_na; verify_not_infer")
        if any("Randomizes" in s for s in cleaned) and any(v["state"] == "value" and v["value"] == 0 for k, v in stats.items() if k != "weight"):
            issues.append("zero_column_with_random_effect_notes; verify_scope")
        if any("see the full page" in s for s in cleaned):
            issues.append("details_deferred_to_unprovided_item_page")
        rows.append({"schema_version": 1, "parser_version": PARSER_VERSION, "item_name_en": cells[1],
            "row_start_line": start + 1, "row_end_line": stop, "statistics": stats,
            "biomes_en": biomes, "locations_en": locations, "notes_en": cleaned,
            "acquisition_en": acquisition, "restrictions_en": restrictions, "cooking_en": cooking,
            "source_row_sha256": digest("\n".join(lines[start:stop])), "issues": issues})
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(normalize(row["item_name_en"]), []).append(row)
    unique, duplicates, conflicts = [], [], []
    for values in grouped.values():
        if len(values) == 1:
            unique.append(values[0]); continue
        comparable = [{k: v for k, v in r.items() if k not in {"row_start_line", "row_end_line", "source_row_sha256"}} for r in values]
        if all(v == comparable[0] for v in comparable):
            unique.append(values[0]); duplicates.extend(r["row_start_line"] for r in values[1:])
        else:
            conflicts.append({"name_en": values[0]["item_name_en"], "lines": [r["row_start_line"] for r in values]})
    counts = {key: dict(Counter(row["statistics"][key]["state"] for row in unique)) for key in STATS}
    missing = {field: sum(not row[field] for row in unique) for field in ("biomes_en", "locations_en", "notes_en", "acquisition_en", "restrictions_en", "cooking_en")}
    return {"parser_version": PARSER_VERSION, "declared_total": int(declared[1]) if declared else None,
            "recognized_rows": len(rows), "unique_items": len(unique), "duplicate_rows": duplicates,
            "conflicting_duplicates": conflicts, "unparsed_rows": unparsed,
            "declared_minus_unique": int(declared[1]) - len(unique) if declared else None,
            "statistic_states": counts, "missing_fields": missing, "items": unique}


def validate_item_details(details: Any, name_en: str, source_body: str) -> bool:
    """Pin every parsed field to a row; translated notes are separately edited data."""
    if not isinstance(details, dict) or details.get("translation_status") != "agent_translation_pending_review":
        raise ContractError("item_details needs an explicit translation status")
    notes_zh = details.get("notes_zh")
    if not isinstance(notes_zh, list) or any(not isinstance(s, str) or not s.strip() or len(s) > 4000 for s in notes_zh):
        raise ContractError("notes_zh must contain nonempty edited translations")
    if "Icon\tName\tWeight\tHunger\tBonus" not in source_body:
        return False
    parsed = parse_peak_items(source_body)
    row = next((r for r in parsed["items"] if r["item_name_en"] == name_en), None)
    if row is None:
        return False
    if {k: v for k, v in details.items() if k not in {"notes_zh", "translation_status"}} != row:
        raise ContractError("item_details differs from the pinned parsed source row")
    if len(notes_zh) != len(row["notes_en"]):
        raise ContractError("each source note requires one edited Traditional Chinese translation")
    return True
