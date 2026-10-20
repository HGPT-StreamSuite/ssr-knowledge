"""Bounded resumable detail-page research. Extracts English candidates, not facts."""
from __future__ import annotations

import copy
import json
import re
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit

from .acquisition import Collector, safe_url, validate_manifest
from .catalog import Catalog, canonical, digest, normalize
from .contracts import ContractError

PARSER_VERSION = "wiki-detail-rules-v1"
PATTERNS = {
    "location": r"\b(?:found|located|entrance|inside)\b.*\b(?:tomb|mesa|biome|location)\b",
    "effects": r"\b(?:grants?|prevents?)\b.*\b(?:invincibility|stamina|damage|status)\b",
    "steps": r"\b(?:throw\w*|sacrific\w*)\b.*\b(?:lava|kiln|cauldron)\b",
    "constraints": r"\b(?:cannot be cooked|weight\s*\d|except knockback)\b",
    "tips": r"\bbackpack\b.*\b(?:farther|further|throw\w*)\b|\bthrow\w*\b.*\bbackpack\b",
    "recipients": r"\b(?:all|every)\s+(?:living\s+)?players?\b.*\b(?:badge|earn\w*|unlock\w*)\b",
    "reward": r"\b(?:reward|unlocks?|grants?)\b.*\b(?:beanie|cosmetic|hat)\b",
}


class WikiMarkup(HTMLParser):
    """Only read links and table cells. No evaluation or secondary requests."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.rows: list[list[str]] = []
        self.href: str | None = None
        self.link_parts: list[str] = []
        self.cells: list[str] | None = None
        self.cell: list[str] | None = None
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"script", "style", "nav", "form"}: self.hidden += 1
        if self.hidden: return
        if tag == "a" and values.get("href"):
            self.href, self.link_parts = values["href"], []
        if tag == "tr": self.cells = []
        if tag in {"td", "th"} and self.cells is not None: self.cell = []

    def handle_endtag(self, tag: str) -> None:
        if self.hidden:
            if tag in {"script", "style", "nav", "form"}: self.hidden -= 1
            return
        if tag == "a" and self.href is not None:
            self.links.append((self.href, " ".join("".join(self.link_parts).split())))
            self.href = None
        if tag in {"td", "th"} and self.cell is not None and self.cells is not None:
            self.cells.append(" ".join("".join(self.cell).split())); self.cell = None
        if tag == "tr" and self.cells is not None:
            self.rows.append(self.cells); self.cells = None

    def handle_data(self, data: str) -> None:
        if self.hidden: return
        if self.href is not None: self.link_parts.append(data)
        if self.cell is not None: self.cell.append(data)


def coverage(blocks: list[dict[str, str]]) -> dict[str, Any]:
    topics = sorted({b["topic"] for b in blocks})
    unique = {b["text_en"] for b in blocks}
    substantive = len(topics) >= 2 and len(unique) >= 2 and sum(map(len, unique)) >= 100
    return {"substantive": substantive, "topics": topics,
            "missing": sorted({"location", "effects", "steps", "constraints", "recipients", "reward"} - set(topics)),
            "meaning": "literal English extraction only; no translation, factual reconciliation or unlock validation"}


def parse_detail(html: str, body: str, name: str, adapter: str) -> dict[str, Any]:
    markup = WikiMarkup(); markup.feed(html); markup.close()
    lines = body.splitlines()
    if adapter == "wiki_badge":
        matching = [row for row in markup.rows if any(normalize(c) == normalize(name) for c in row[:3])]
        if len(matching) != 1:
            raise ContractError("incomplete badge parsing: require exactly one target table row")
        target = normalize(" ".join(matching[0]))
        lines = [line for line in lines if normalize(line) in target]
    elif adapter == "wiki_item":
        title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        if not title or normalize(name) not in normalize(re.sub(r"<[^>]+>", "", title[1])):
            raise ContractError("incomplete item parsing: target identity not present in page title")
    else:
        raise ContractError("unknown detail adapter")
    blocks = []
    for line in lines:
        # Long or fragmented paragraphs are gaps, never silently truncated quotes.
        if not 20 <= len(line) <= 300 or re.match(r"(?:Can be used for|Part of|Required for) ", line):
            continue
        for topic, pattern in PATTERNS.items():
            if re.search(pattern, line, re.I):
                block = {"topic": topic, "text_en": line}
                if block not in blocks: blocks.append(block)
    if len(blocks) > 30: raise ContractError("incomplete parsing: more than 30 matched blocks; refine scope")
    result = {"parser_version": PARSER_VERSION, "adapter": adapter, "target_name": name,
              "translation_status": "pending_translation_and_human_review", "blocks": blocks, "coverage": coverage(blocks)}
    if not result["coverage"]["substantive"]:
        raise ContractError("incomplete parsing: only a title, hint, or insufficient supported topics")
    return result


def validate_extracts(entry: dict[str, Any], snapshots: dict[str, dict[str, Any]]) -> None:
    values = entry.get("research_extracts", [])
    if not isinstance(values, list) or len(values) > 5:
        raise ContractError("at most five separately attributed research extracts")
    seen = set()
    for value in values:
        fields = {"parser_version", "adapter", "target_name", "translation_status", "blocks", "coverage", "citation"}
        if (not isinstance(value, dict) or set(value) != fields or value["parser_version"] != PARSER_VERSION
                or value["adapter"] not in {"wiki_item", "wiki_badge"} or value["target_name"] != entry["name_en"]
                or value["translation_status"] != "pending_translation_and_human_review"):
            raise ContractError("invalid research extraction provenance or method")
        index = value["citation"]
        if type(index) is not int or not 0 <= index < len(entry["citations"]): raise ContractError("invalid research citation")
        snap = snapshots[entry["citations"][index]["snapshot_id"]]
        if snap["source"]["source_type"] != "wiki" or snap["source"].get("acquisition", {}).get("kind"):
            raise ContractError("automatic extraction needs directly collected Wiki HTML, never a search excerpt")
        if snap["source_id"] in seen: raise ContractError("duplicate extraction source")
        seen.add(snap["source_id"])
        if not isinstance(value["blocks"], list) or not 1 <= len(value["blocks"]) <= 30:
            raise ContractError("bounded extraction blocks required")
        for block in value["blocks"]:
            if (not isinstance(block, dict) or set(block) != {"topic", "text_en"} or block["topic"] not in PATTERNS
                    or not isinstance(block["text_en"], str) or not 20 <= len(block["text_en"]) <= 300
                    or block["text_en"] not in snap["body"]):
                raise ContractError("research block is not pinned to exact extracted body")
        if value["coverage"] != coverage(value["blocks"]) or not value["coverage"]["substantive"]:
            raise ContractError("research coverage differs or is only a title/hint")


def discover(store: Catalog) -> dict[str, Any]:
    """Find saved detail URLs and matching anchor text; never guess slugs or fetch."""
    entries = [json.loads(r[0]) for r in store.db.execute("SELECT r.payload_json FROM entries e JOIN entry_revisions r ON r.revision_id=e.current_revision")]
    by_name = {normalize(e["name_en"]): e for e in entries}
    candidates = []
    for entry in entries:
        if entry.get("detail_page"):
            candidates.append({"entry_id": entry["entry_id"], "url": entry["detail_page"]["url"], "basis": "saved explicit detail_page", "fetch_allowed": False})
    for row in store.db.execute("SELECT snapshot_id,raw,config_json FROM snapshots"):
        cfg = json.loads(row["config_json"])
        if cfg["source_type"] != "wiki" or cfg.get("acquisition", {}).get("kind"): continue
        try: html = row["raw"].decode("utf-8", errors="strict")
        except UnicodeError: continue
        parser = WikiMarkup(); parser.feed(html); parser.close()
        for href, label in parser.links:
            entry = by_name.get(normalize(label))
            if not entry: continue
            try: url = safe_url(urljoin(cfg["url"], href).split("#", 1)[0])
            except ContractError: continue
            parsed = urlsplit(url)
            if (parsed.hostname != urlsplit(cfg["url"]).hostname or not parsed.path.startswith("/wiki/")
                    or ":" in parsed.path[len("/wiki/"):] or parsed.query): continue
            candidates.append({"entry_id": entry["entry_id"], "url": url, "basis": "exact saved HTML anchor", "snapshot_id": row["snapshot_id"], "fetch_allowed": False})
    unique = {(c["entry_id"], c["url"]): c for c in candidates}
    inventory = []
    for e in entries:
        org = e.get("organization", {})
        inventory.append({"entry_id": e["entry_id"], "category": e["category"], "name_en": e["name_en"],
                          "has_detailed_item_row": "item_details" in e, "has_editorial_guide": "guide_details" in e,
                          "has_automatic_extract": bool(e.get("research_extracts")),
                          "official_condition_only": "badge_details" in e and "guide_details" not in e and not e.get("research_extracts"),
                          "missing_item_topics": [k for k, v in org.get("topics", {}).items() if not v],
                          "name_or_hint_only_item": e["category"] == "item" and not any(not n.startswith(("Can be used for ", "Part of ", "Required for ")) for n in e.get("item_details", {}).get("notes_en", []))})
    return {"network_requests": 0, "candidates": sorted(unique.values(), key=lambda c: (c["entry_id"], c["url"])),
            "note": "Discovered links require an explicit reviewed manifest; not an access or coverage grant.", "inventory": inventory}


def ensure_jobs(store: Catalog) -> None:
    store.db.executescript("""CREATE TABLE IF NOT EXISTS research_jobs (
        job_key TEXT PRIMARY KEY, config_json TEXT NOT NULL, state TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0, next_at REAL, lease_until REAL, result_json TEXT);
        CREATE TABLE IF NOT EXISTS research_attempts (
        attempt_id INTEGER PRIMARY KEY, job_key TEXT NOT NULL, started_at REAL NOT NULL,
        completed_at REAL, result_json TEXT);""")


def save_candidate(store: Catalog, task: dict[str, Any], source: dict[str, Any], result: dict[str, Any],
                   parsed: dict[str, Any], before: str | None) -> dict[str, Any]:
    draft = copy.deepcopy(store.entry(task["entry_id"])["entry"])
    refs = draft["citations"]
    previous = draft.get("research_extracts", [])
    old_extract = next((e for e in previous if store.snapshot(refs[e["citation"]]["snapshot_id"])["source_id"] == source["source_id"]), None)
    index = old_extract["citation"] if old_extract else next((i for i, c in enumerate(refs) if c["snapshot_id"] == result["snapshot_id"]), len(refs))
    others = [e for e in previous if store.snapshot(refs[e["citation"]]["snapshot_id"])["source_id"] != source["source_id"]]
    citation = {"snapshot_id": result["snapshot_id"], "locator": "Deterministic scoped Wiki detail blocks; English pending translation", "evidence_quote": parsed["blocks"][0]["text_en"]}
    if index == len(refs): refs.append(citation)
    else: refs[index] = citation
    draft["research_extracts"] = [*others, {**parsed, "citation": index}]
    draft["evidence_class"] = "wiki"
    # Preserve names, official conditions and existing editorial text. Separate
    # sources remain unreconciled alternatives. No review status is carried over.
    saved = store.import_drafts({"entries": [draft]})[0]
    return {"state": "candidate_saved" if saved["state"] == "saved" else "unchanged", "draft": saved, "coverage": parsed["coverage"],
            "reconciliation": "unreconciled source variants; do not merge claims" if others or draft.get("guide_details") else "single-source extraction, not fact checked",
            "snapshot_diff": store.compare_snapshots(before, result["snapshot_id"]) if before and before != result["snapshot_id"] else None}


def run_batch(store: Catalog, plan: Any, *, max_jobs: int = 2, refresh: bool = False, retry_blocked: bool = False,
              transport: Any = None, sleep: Any = time.sleep, clock: Any = time.time) -> dict[str, Any]:
    if not isinstance(plan, dict) or set(plan) != {"manifest", "tasks"}: raise ContractError("research plan needs manifest and tasks")
    sources = {s["source_id"]: s for s in validate_manifest(plan["manifest"])}
    tasks = plan["tasks"]
    if type(max_jobs) is not int or not 1 <= max_jobs <= 10 or not isinstance(tasks, list) or not 1 <= len(tasks) <= 1000:
        raise ContractError("one to 1000 planned tasks; run only one to ten at a time")
    configs = []
    for task in tasks:
        if (not isinstance(task, dict) or set(task) != {"entry_id", "source_id", "adapter"}
                or task["source_id"] not in sources or task["adapter"] not in {"wiki_item", "wiki_badge"}):
            raise ContractError("task requires exact entry, reviewed source and supported adapter")
        entry = store.entry(task["entry_id"])["entry"]
        if sources[task["source_id"]]["source_type"] != "wiki" or (task["adapter"] == "wiki_item") != (entry["category"] == "item"):
            raise ContractError("task source/category mismatch")
        if task["adapter"] == "wiki_badge" and (entry["category"] != "achievement" or "badge_details" not in entry):
            raise ContractError("badge adapter needs a separately verified game badge definition")
        configs.append({"task": task, "source": sources[task["source_id"]], "target_name": entry["name_en"]})
    if len({canonical(c["task"]) for c in configs}) != len(configs): raise ContractError("duplicate research task")
    ensure_jobs(store)
    results = []
    for config in configs:
        key = digest(canonical(config))
        with store.db:
            store.db.execute("INSERT OR IGNORE INTO research_jobs(job_key,config_json,state) VALUES(?,?,'queued')", (key, canonical(config)))
        if len(results) >= max_jobs: continue
        with store.db:
            store.db.execute("BEGIN IMMEDIATE")
            job = store.db.execute("SELECT * FROM research_jobs WHERE job_key=?", (key,)).fetchone()
            eligible = (job["state"] == "queued" or job["state"] == "retry_wait" and (job["next_at"] or 0) <= clock()
                        or job["state"] == "running" and (job["lease_until"] or 0) <= clock()
                        or refresh and job["state"] in {"candidate_saved", "unchanged"}
                        or retry_blocked and job["state"] == "manual_required")
            if not eligible: continue
            store.db.execute("UPDATE research_jobs SET state='running',attempts=attempts+1,lease_until=? WHERE job_key=?", (clock() + 300, key))
            attempt = store.db.execute("INSERT INTO research_attempts(job_key,started_at) VALUES(?,?)", (key, clock())).lastrowid
        task, source = config["task"], config["source"]
        old = store.db.execute("SELECT latest_snapshot FROM sources WHERE source_id=?", (source["source_id"],)).fetchone()
        before = old[0] if old else None
        parsed: dict[str, Any] = {}
        def check(_: Any, html: str, body: str) -> None:
            parsed.update(parse_detail(html, body, config["target_name"], task["adapter"]))
        collector = Collector(store, transport=transport, sleep=sleep, clock=clock, body_check=check)
        result = collector.collect([source], purpose="local_cache")[0]
        output: dict[str, Any] = {"job_key": key, "entry_id": task["entry_id"], "source_url": source["url"], "collection": result,
                                  "direct_fetch_success": result["state"] != "blocked_or_failed", "previous_snapshot_id": before}
        state, next_at = "manual_required", None
        if result["state"] == "blocked_or_failed":
            if result["retryable"] and job["attempts"] < 2:
                state, next_at = "retry_wait", max(result.get("next_attempt_at") or 0, clock() + 60)
            output.update(state=state, pending_action="wait until retry time" if state == "retry_wait" else "review terms/access or supply a properly attributed file; no bypass")
            if result["retryable"] and job["attempts"] >= 2:
                output["retry_budget_exhausted"] = True
        else:
            try:
                candidate = save_candidate(store, task, source, result, parsed, before)
                state = candidate["state"]
                output.update(candidate)
            except (ContractError, ValueError) as exc:
                output.update(state=state, failure_kind="candidate_validation", error=str(exc),
                              pending_action="Collected source retained; existing entry unchanged. Review schema or evidence conflict.")
        latest = store.db.execute("SELECT latest_snapshot FROM sources WHERE source_id=?", (source["source_id"],)).fetchone()
        output["latest_good_snapshot_preserved"] = result["state"] != "blocked_or_failed" or (latest[0] if latest else None) == before
        with store.db:
            store.db.execute("UPDATE research_jobs SET state=?,next_at=?,lease_until=NULL,result_json=? WHERE job_key=?", (state, next_at, canonical(output), key))
            store.db.execute("UPDATE research_attempts SET completed_at=?,result_json=? WHERE attempt_id=?", (clock(), canonical(output), attempt))
        results.append(output)
    counts = {r[0]: r[1] for r in store.db.execute("SELECT state,count(*) FROM research_jobs GROUP BY state")}
    return {"max_jobs": max_jobs, "processed": len(results), "results": results, "queue_counts": counts,
            "batch_fetch_and_parse_viable": bool(results) and all(r["state"] in {"candidate_saved", "unchanged"} and r["direct_fetch_success"] for r in results),
            "full_database_expansion_granted_by_this_result": False,
            "note": "This bounded batch never grants access or approves knowledge. Check real fetch/coverage before any wider batch."}
