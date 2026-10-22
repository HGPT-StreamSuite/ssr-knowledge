"""Field-level evidence for pending editorial guidance; never gameplay approval."""
from __future__ import annotations

from typing import Any

from .catalog import required_text
from .contracts import ContractError

TOPICS = {"location": "取得地點", "prerequisites": "前置需求", "steps": "操作步驟", "recipients": "獲得對象",
          "reward": "獎勵", "constraints": "限制", "effects": "持握效果", "tips": "玩家用法"}
REQUIRED_TOPICS = {"location", "prerequisites", "steps", "recipients", "reward", "constraints"}


def validate_guide(entry: dict[str, Any], snapshots: dict[str, dict[str, Any]]) -> None:
    guide = entry.get("guide_details")
    if guide is None:
        return
    if (not isinstance(guide, dict) or set(guide) != {"schema_version", "method", "claims", "gaps"}
            or guide["schema_version"] != 1 or guide["method"] != "agent_edited_pending_review"
            or entry["category"] not in {"item", "achievement", "guide"}):
        raise ContractError("guide_details needs pending editorial method and documented fields")
    if not isinstance(guide["claims"], list) or not 1 <= len(guide["claims"]) <= 30:
        raise ContractError("one to thirty sourced guide claims required")
    covered = set()
    for claim in guide["claims"]:
        if (not isinstance(claim, dict) or set(claim) != {"topic", "text_zh", "source_class", "evidence"}
                or claim["topic"] not in TOPICS or claim["source_class"] not in {"wiki", "third_party_analysis", "player_test"}):
            raise ContractError("guide claims must distinguish community evidence from official displayed text")
        covered.add(claim["topic"])
        required_text(claim["text_zh"], "guide text", 800)
        if not isinstance(claim["evidence"], list) or not 1 <= len(claim["evidence"]) <= 4:
            raise ContractError("each guide claim needs one to four exact private anchors")
        for evidence in claim["evidence"]:
            if not isinstance(evidence, dict) or set(evidence) != {"citation", "quote"}:
                raise ContractError("guide evidence needs citation and exact quote")
            index = evidence["citation"]
            if type(index) is not int or not 0 <= index < len(entry["citations"]):
                raise ContractError("guide citation index out of range")
            snap = snapshots[entry["citations"][index]["snapshot_id"]]
            quote = required_text(evidence["quote"], "guide quote", 300)
            if quote not in snap["body"] or snap["source"]["source_type"] != claim["source_class"]:
                raise ContractError("guide quote/class differs from pinned source")
    if not isinstance(guide["gaps"], list) or len(guide["gaps"]) > 15:
        raise ContractError("bounded explicit guide gaps required")
    for gap in guide["gaps"]:
        if not isinstance(gap, dict) or set(gap) != {"topic", "reason"} or gap["topic"] not in TOPICS:
            raise ContractError("guide gap requires documented topic and reason")
        required_text(gap["reason"], "gap reason", 800)
        covered.add(gap["topic"])
    if not REQUIRED_TOPICS <= covered:
        raise ContractError("location, prerequisites, steps, recipients, reward and constraints must be sourced or explicitly missing")


def guide_search_text(entry: dict[str, Any]) -> str:
    return " ".join(text for claim in entry.get("guide_details", {}).get("claims", [])
                    for text in [claim["text_zh"], *(e["quote"] for e in claim["evidence"])])
