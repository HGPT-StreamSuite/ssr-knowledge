"""Parse text labels from an uninstalled community mod; never execute its content."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .contracts import ContractError


def match_community_names(body: str, english_names: list[str]) -> dict[str, Any]:
    # Only casefold and trim at the ends: typos, punctuation, internal spaces and
    # qualifiers remain distinct. This is stricter than interactive name lookup.
    keys = [name.strip().casefold() for name in english_names]
    if len(keys) != len(set(keys)):
        raise ContractError("reference item names are ambiguous after casefold")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unparsed = []
    rows = []
    for number, line in enumerate(body.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "=" not in line:
            unparsed.append({"line": number, "text": line, "reason": "expected key=value"}); continue
        key, value = (part.strip() for part in line.split("=", 1))
        if not key or not value or len(key) > 200 or len(value) > 200:
            unparsed.append({"line": number, "text": line, "reason": "empty/overlong label"}); continue
        row = {"line": number, "key": key, "value": value, "raw": line}
        rows.append(row); grouped[key.casefold()].append(row)
    matched, missing = [], []
    for name, key in zip(english_names, keys):
        if key not in grouped:
            missing.append(name); continue
        values = list(dict.fromkeys(row["value"] for row in grouped[key]))
        matched.append({"name_en": name, "aliases": values, "conflicting_values": len(values) > 1, "rows": grouped[key]})
    conflicts = [{"key_casefold": key, "values": list(dict.fromkeys(row["value"] for row in values)), "rows": values}
                 for key, values in grouped.items() if len({row["value"] for row in values}) > 1]
    return {"parser_version": "community-labels-exact-v1", "key_value_rows": len(rows), "unique_casefold_keys": len(grouped),
            "duplicate_pairs": len(rows) - len({(r["key"].casefold(), r["value"]) for r in rows}),
            "source_conflicts": conflicts, "matched_items": len(matched), "unmatched_items": len(missing),
            "unmatched_names": missing, "unmatched_source_keys": [k for k in grouped if k not in set(keys)],
            "matched_conflicts": [row["name_en"] for row in matched if row["conflicting_values"]],
            "unparsed_rows": unparsed, "matches": matched}
