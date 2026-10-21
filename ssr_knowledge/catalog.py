"""Private SQLite catalog. Source text is data; it is never executable input."""
from __future__ import annotations

import hashlib
import difflib
import json
import os
import shutil
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

from .contracts import ContractError
from .store import ID_PATTERN, utc_now

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TYPES = {"official", "wiki", "third_party_analysis", "player_test"}
CATEGORIES = {"introduction", "review", "mode", "character", "mechanic", "item", "status", "guide", "lore", "location", "creature", "achievement", "update", "support"}
USAGE_PURPOSES = {"local_cache", "search_index", "ai_input", "ai_train"}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def required_text(value: Any, label: str, maximum: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ContractError(f"{label}: nonempty string up to {maximum} characters required")
    return value


def identifier(value: Any) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise ContractError("invalid identifier")
    return value


def _robots_search_denied(metadata: dict[str, Any], url: str) -> bool:
    """Only an observed explicit search=no denies search; missing signals stay unknown.

    Reassess saved text for legacy snapshots with no structured assessment. This
    is an offline parse of the actual fixed UA, not a new fetch or license check.
    """
    assessment = metadata.get("robots_assessment", {})
    if isinstance(metadata.get("robots_text"), str):
        from .acquisition import robots_assessment  # Runtime import avoids the collector/catalog cycle.
        assessment = robots_assessment(metadata["robots_text"], url, "search_index")
    if not isinstance(assessment, dict):
        return False
    signals = assessment.get("content_signals", {})
    values = signals.get("search", []) if isinstance(signals, dict) else []
    explicit_no = isinstance(values, list) and any(isinstance(v, str) and v.strip().lower() == "no" for v in values)
    usage = assessment.get("usage_signals", {})
    return explicit_no or (isinstance(usage, dict) and usage.get("search_index") == "prohibited")


def _source_usable(source: dict[str, Any]) -> bool:
    if source.get("acquisition", {}).get("kind") in {"user_provided_text", "local_name_reference", "installed_game_text", "web_search_excerpt", "approved_local_file"}:
        return source["policy"].get("allow_import") is True
    return source["policy"]["allow_fetch"] is True


def resolve_data_dir(value: str | Path | None = None) -> Path:
    default = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SSRKnowledge" / "data"
    path = Path(value or os.environ.get("SSR_KNOWLEDGE_DATA_DIR", str(default))).expanduser().resolve()
    if path == ROOT or ROOT in path.parents:
        raise ContractError("catalog data directory must be outside the Git checkout")
    # Also protect any other checkout, including linked worktrees with a .git file.
    if any((parent / ".git").exists() for parent in (path, *path.parents)):
        raise ContractError("catalog data directory must be outside every Git checkout")
    return path


class Catalog:
    """One local writer at a time; no server, FTS extension or model required."""

    def __init__(self, data_dir: str | Path | None = None, *, read_only: bool = False) -> None:
        self.root = resolve_data_dir(data_dir)
        if read_only:
            database = self.root / "knowledge.sqlite3"
            if not database.is_file():
                raise ContractError("指定的 knowledge.sqlite3 不存在；不建立或替換資料庫")
            self.db = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5)
            self.db.row_factory = sqlite3.Row
            try:
                self.db.execute("PRAGMA query_only = ON")
                version = self.db.execute("PRAGMA user_version").fetchone()[0]
                tables = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if version != 1 or not {"entries", "entry_revisions", "sources", "snapshots", "citations", "entry_relations"} <= tables:
                    raise ContractError("指定檔案不是目前支援的 knowledge catalog；不使用其他資料庫")
            except Exception:
                self.close()
                raise
            return
        existing = self.root
        while not existing.exists():
            existing = existing.parent
        self.free_bytes = shutil.disk_usage(existing).free
        if self.free_bytes < 50 * 1024 * 1024:
            raise ContractError("at least 50 MiB free space required for the catalog")
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "knowledge.sqlite3", timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            self.close()
            raise ContractError("unsupported catalog schema version")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL,
                config_json TEXT NOT NULL, latest_snapshot TEXT
            );
            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources,
                fetched_at TEXT NOT NULL, raw BLOB NOT NULL, raw_sha256 TEXT NOT NULL,
                body TEXT NOT NULL, body_sha256 TEXT NOT NULL, metadata_json TEXT NOT NULL,
                config_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY, at TEXT NOT NULL, source_id TEXT,
                event TEXT NOT NULL, details_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS throttles (origin TEXT PRIMARY KEY, next_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS entries (entry_id TEXT PRIMARY KEY, current_revision INTEGER);
            CREATE TABLE IF NOT EXISTS entry_revisions (
                revision_id INTEGER PRIMARY KEY, entry_id TEXT NOT NULL REFERENCES entries,
                payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
                search_text TEXT NOT NULL, created_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending_review','approved','rejected','published')),
                review_json TEXT, published_at TEXT, UNIQUE(entry_id, payload_sha256)
            );
            CREATE TABLE IF NOT EXISTS citations (
                revision_id INTEGER NOT NULL REFERENCES entry_revisions,
                snapshot_id TEXT NOT NULL REFERENCES snapshots, PRIMARY KEY(revision_id,snapshot_id)
            );
            CREATE INDEX IF NOT EXISTS citations_snapshot ON citations(snapshot_id);
            CREATE TABLE IF NOT EXISTS entry_relations (
                revision_id INTEGER NOT NULL REFERENCES entry_revisions,
                target_entry_id TEXT NOT NULL REFERENCES entries,
                kind TEXT NOT NULL, citation_index INTEGER NOT NULL,
                note_index INTEGER, evidence_text TEXT NOT NULL,
                PRIMARY KEY(revision_id,target_entry_id,kind)
            );
            CREATE INDEX IF NOT EXISTS relations_target ON entry_relations(target_entry_id);
            PRAGMA user_version = 1;
        """)

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> Catalog:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def event(self, source_id: str | None, event: str, details: dict[str, Any]) -> dict[str, Any]:
        result = {"at": utc_now(), "source_id": source_id, "event": event, **details}
        with self.db:
            self.db.execute("INSERT INTO events(at,source_id,event,details_json) VALUES(?,?,?,?)",
                            (result["at"], source_id, event, canonical(details)))
        return result

    def register_source(self, source: dict[str, Any]) -> None:
        existing = self.db.execute("SELECT url FROM sources WHERE source_id=?", (source["source_id"],)).fetchone()
        if existing and existing["url"] != source["url"]:
            raise ContractError("source_id URL cannot change; use a new source_id")
        try:
            with self.db:
                self.db.execute("""INSERT INTO sources(source_id,url,config_json) VALUES(?,?,?)
                    ON CONFLICT(source_id) DO UPDATE SET config_json=excluded.config_json""",
                    (source["source_id"], source["url"], canonical(source)))
        except sqlite3.IntegrityError as exc:
            raise ContractError("URL already registered with another source_id") from exc

    def save_snapshot(self, source: dict[str, Any], raw: bytes, body: str,
                      metadata: dict[str, Any]) -> dict[str, Any]:
        """Called by the collector; raw bytes and extracted text stay inside SQLite."""
        required_text(body, "extracted body", 2_000_000)
        config = canonical(source)
        raw_hash, body_hash = digest(raw), digest(body)
        sid = digest(source["url"] + "\0" + raw_hash + "\0" + digest(config))
        old = self.db.execute("SELECT latest_snapshot FROM sources WHERE source_id=?", (source["source_id"],)).fetchone()
        if old is None:
            raise ContractError("source not registered")
        with self.db:
            self.db.execute("""INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?,?,?,?,?,?)""",
                            (sid, source["source_id"], utc_now(), raw, raw_hash, body, body_hash,
                             canonical(metadata), config))
            self.db.execute("UPDATE sources SET latest_snapshot=? WHERE source_id=?", (sid, source["source_id"]))
        return {"source_id": source["source_id"], "snapshot_id": sid,
                "state": "unchanged" if old["latest_snapshot"] == sid else "saved",
                "raw_sha256": raw_hash, "body_sha256": body_hash,
                "raw_bytes": len(raw), "body_characters": len(body)}

    def snapshot(self, snapshot_id: str, include_body: bool = False) -> dict[str, Any]:
        row = self.db.execute("SELECT * FROM snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
        if row is None:
            raise ContractError("snapshot not found")
        if digest(row["raw"]) != row["raw_sha256"] or digest(row["body"]) != row["body_sha256"]:
            raise ContractError("snapshot integrity mismatch")
        source = json.loads(row["config_json"])
        result = {key: row[key] for key in ("snapshot_id", "source_id", "fetched_at", "raw_sha256", "body_sha256")}
        result.update({"source": source, "metadata": json.loads(row["metadata_json"]),
                       "raw_bytes": len(row["raw"]), "body_characters": len(row["body"])})
        meta = result["metadata"]
        current = self.db.execute("SELECT config_json FROM sources WHERE source_id=?", (row["source_id"],)).fetchone()
        current_source = json.loads(current[0])
        unknown = {p: {"status": "unknown", "basis": "no purpose-specific review recorded"} for p in sorted(USAGE_PURPOSES)}
        result["provenance"] = {
            "original_url": source.get("original_url", source["url"]), "requested_url": meta.get("requested_url", source["url"]),
            "canonical_url": meta.get("canonical_url", source["url"]),
            "canonical_basis": meta.get("canonical_basis", "normalized request URL; page canonical unknown"),
            "body_locator": meta.get("body_locator", source["selector"]), "acquired_at": row["fetched_at"],
            "source_updated_at": meta.get("source_updated_at", meta.get("headers", {}).get("last-modified")),
            "source_updated_basis": meta.get("source_updated_basis", "legacy HTTP Last-Modified" if meta.get("headers", {}).get("last-modified") else "unknown"),
            "declared_version": source["declared_version"], "page_version": meta.get("page_dates", {}).get("mw:revisionId") or "unknown",
            "snapshot_usage": source["policy"].get("uses", unknown),
            "current_usage": current_source["policy"].get("uses", unknown),
            "collector_called_llm": False, "url_is_not_proof_of_llm_reading": True,
            "acquisition_kind": meta.get("acquisition_kind", "http_collection"),
        }
        if include_body:
            result["body"] = row["body"]
        return result

    def compare_snapshots(self, before: str, after: str, include_body: bool = False) -> dict[str, Any]:
        left, right = self.snapshot(before, include_body), self.snapshot(after, include_body)
        if left["source_id"] != right["source_id"]:
            raise ContractError("snapshot comparison requires the same source_id")
        result = {"source_id": left["source_id"], "before": left, "after": right,
                  "raw_changed": left["raw_sha256"] != right["raw_sha256"],
                  "body_changed": left["body_sha256"] != right["body_sha256"],
                  "config_changed": left["source"] != right["source"],
                  "entry_revisions_created": 0, "review_state_changed": False}
        if include_body:
            diff = list(difflib.unified_diff(left.pop("body").splitlines(), right.pop("body").splitlines(),
                                           fromfile=before, tofile=after, lineterm=""))
            text = "\n".join(diff[:200])
            result["private_body_diff"] = text[:50000]
            result["diff_truncated"] = len(diff) > 200 or len(text) > 50000
        return result

    def sources(self) -> list[dict[str, Any]]:
        result = []
        for row in self.db.execute("SELECT * FROM sources ORDER BY source_id"):
            result.append({"config": json.loads(row["config_json"]),
                           "latest": self.snapshot(row["latest_snapshot"]) if row["latest_snapshot"] else None})
        return result

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        return [{"event_id": row["event_id"], "at": row["at"], "source_id": row["source_id"],
                 "event": row["event"], "details": json.loads(row["details_json"])}
                for row in self.db.execute("SELECT * FROM events ORDER BY event_id DESC LIMIT ?", (limit,))]

    def _validate_draft(self, value: Any, lookup: Any = None) -> dict[str, Any]:
        fields = {"entry_id", "game", "category", "name_en", "name_zh", "aliases", "summary_zh",
                  "evidence_class", "citations", "editor", "game_version", "limitations"}
        if not isinstance(value, dict) or not fields <= set(value) or set(value) - fields - {"taxonomy", "item_details", "names", "organization", "badge_details", "links", "detail_page", "guide_details", "research_extracts", "knowledge_details", "knowledge_links"}:
            raise ContractError("draft must contain exactly the documented fields")
        identifier(value["entry_id"])
        if value["game"] != "PEAK:3527290" or value["category"] not in CATEGORIES:
            raise ContractError("only PEAK:3527290 and documented categories are supported in this batch")
        if value["evidence_class"] not in SOURCE_TYPES:
            raise ContractError("invalid evidence_class")
        if "taxonomy" in value:
            tax = value["taxonomy"]
            if not isinstance(tax, dict) or set(tax) != {"mapping_version", "source_path", "subtype"}:
                raise ContractError("taxonomy needs mapping_version, source_path, subtype")
            if tax["mapping_version"] != "peak-v1" or not isinstance(tax["source_path"], list) or not 1 <= len(tax["source_path"]) <= 10:
                raise ContractError("invalid taxonomy mapping version or source_path")
            for part in [tax["subtype"], *tax["source_path"]]:
                required_text(part, "taxonomy text", 200)
        for field in ("name_en", "name_zh", "summary_zh", "editor", "game_version", "limitations"):
            required_text(value[field], field)
        if not isinstance(value["aliases"], list) or not 1 <= len(value["aliases"]) <= 30:
            raise ContractError("at least one alias required; maximum 30")
        for alias in value["aliases"]:
            required_text(alias, "alias", 200)
        if not isinstance(value["citations"], list) or not 1 <= len(value["citations"]) <= 20:
            raise ContractError("one to twenty pinned citations required")
        details_pinned = "item_details" not in value
        if not details_pinned and value["category"] != "item":
            raise ContractError("item_details only belongs to item entries")
        name_snapshots = {}
        for citation in value["citations"]:
            if not isinstance(citation, dict) or set(citation) != {"snapshot_id", "locator", "evidence_quote"}:
                raise ContractError("citation needs snapshot_id, locator, evidence_quote")
            required_text(citation["locator"], "citation locator", 500)
            # Short private anchors only. The program verifies location, not factual entailment.
            quote = required_text(citation["evidence_quote"], "evidence quote", 300)
            snap = self.snapshot(citation["snapshot_id"], include_body=True)
            name_snapshots[citation["snapshot_id"]] = snap
            if quote not in snap["body"]:
                raise ContractError("evidence_quote is not present in the pinned extracted body")
            if value["evidence_class"] == "official" and snap["source"]["source_type"] != "official":
                raise ContractError("official claims require official citations")
            if value["evidence_class"] == "player_test" and snap["source"]["source_type"] != "player_test":
                raise ContractError("player_test requires a player-test source, not an inferred test")
            if "item_details" in value:
                from .item_table import validate_item_details
                details_pinned = validate_item_details(value["item_details"], value["name_en"], snap["body"]) or details_pinned
        if not details_pinned:
            raise ContractError("item_details is not pinned to any cited source row")
        from .names import validate_names
        validate_names(value, name_snapshots)
        from .organization import validate_organization, validate_badge, validate_links
        validate_organization(value)
        validate_badge(value, name_snapshots, lambda sid: self.db.execute("SELECT raw FROM snapshots WHERE snapshot_id=?", (sid,)).fetchone()[0])
        lookup = lookup or (lambda eid: self.entry(eid)["entry"])
        validate_links(value, lookup, name_snapshots)
        from .game_plan import validate_details, validate_relations
        validate_details(self, value, name_snapshots)
        validate_relations(self, value, lookup, name_snapshots)
        from .guide_details import validate_guide
        validate_guide(value, name_snapshots)
        from .research import validate_extracts
        validate_extracts(value, name_snapshots)
        return value

    def import_drafts(self, drafts: Any) -> list[dict[str, Any]]:
        if not isinstance(drafts, dict) or set(drafts) != {"entries"} or not isinstance(drafts["entries"], list):
            raise ContractError("draft bundle must be an object containing entries array")
        if not 1 <= len(drafts["entries"]) <= 100:
            raise ContractError("import one to one hundred drafts at a time")
        ids = [identifier(item.get("entry_id")) if isinstance(item, dict) else identifier(None) for item in drafts["entries"]]
        if len(ids) != len(set(ids)):
            raise ContractError("entry_id must be unique within an import")
        batch = dict(zip(ids, drafts["entries"]))
        def lookup(eid: str) -> dict:
            if eid in batch:
                historical = self.db.execute('SELECT 1 FROM entry_revisions WHERE entry_id=? AND payload_sha256=?',
                                             (eid, digest(canonical(batch[eid])))).fetchone()
                if not historical:
                    return batch[eid]
            # A duplicate historical payload does not replace the current head.
            return self.entry(eid)["entry"]
        results = []
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            # Validate all targets before any row is inserted. This supports
            # forward links in one atomic batch without leaving placeholder rows.
            values = [self._validate_draft(item, lookup) for item in drafts["entries"]]
            from .game_plan import validate_relations
            checked = set()
            for eid in ids:
                for row in self.db.execute('''SELECT r.entry_id FROM entry_relations l
                    JOIN entry_revisions r USING(revision_id) JOIN entries e ON e.current_revision=r.revision_id
                    WHERE l.target_entry_id=? AND l.kind LIKE 'planned:%' ''', (eid,)):
                    if row[0] not in checked:
                        origin = lookup(row[0])
                        snapshots = {c['snapshot_id']: self.snapshot(c['snapshot_id'], True) for c in origin['citations']}
                        validate_relations(self, origin, lookup, snapshots)
                        checked.add(row[0])
            self.db.executemany("INSERT OR IGNORE INTO entries(entry_id) VALUES(?)", [(eid,) for eid in ids])
            for value in values:
                payload = canonical(value)
                old = self.db.execute("SELECT revision_id,status FROM entry_revisions WHERE entry_id=? AND payload_sha256=?",
                                      (value["entry_id"], digest(payload))).fetchone()
                if old:
                    results.append({"entry_id": value["entry_id"], "revision_id": old["revision_id"],
                                    "state": "unchanged", "status": old["status"]})
                    continue
                self.db.execute("INSERT OR IGNORE INTO entries(entry_id) VALUES(?)", (value["entry_id"],))
                search = normalize(" ".join([value["name_en"], value["name_zh"], *value["aliases"], value["summary_zh"]]))
                if "item_details" in value:
                    detail = value["item_details"]
                    search += " " + normalize(" ".join(detail["notes_en"] + detail["notes_zh"] + detail["biomes_en"] + detail["locations_en"]))
                if "badge_details" in value:
                    search += " " + normalize(value["badge_details"]["condition_en"] + " " + value["badge_details"]["condition_zh"])
                from .guide_details import guide_search_text
                search += " " + normalize(guide_search_text(value))
                from .game_plan import search_text
                search += " " + normalize(search_text(value))
                search += " " + normalize(" ".join(b["text_en"] for extract in value.get("research_extracts", []) for b in extract["blocks"]))
                cur = self.db.execute("""INSERT INTO entry_revisions(entry_id,payload_json,payload_sha256,search_text,created_at,status)
                    VALUES(?,?,?,?,?,'pending_review')""", (value["entry_id"], payload, digest(payload), search, utc_now()))
                revision = cur.lastrowid
                self.db.execute("UPDATE entries SET current_revision=? WHERE entry_id=?", (revision, value["entry_id"]))
                self.db.executemany("INSERT OR IGNORE INTO citations VALUES(?,?)",
                                    [(revision, c["snapshot_id"]) for c in value["citations"]])
                self.db.executemany("INSERT INTO entry_relations VALUES(?,?,?,?,?,?)",
                                    [(revision, link["target_entry_id"], link["kind"], link["citation"], link["note_index"], link["evidence_text"])
                                     for link in value.get("links", [])])
                self.db.executemany("INSERT INTO entry_relations VALUES(?,?,?,?,?,?)",
                                    [(revision, link["target_entry_id"], "planned:" + link["kind"], link["citation"], None, link["evidence_text"])
                                     for link in value.get("knowledge_links", [])])
                results.append({"entry_id": value["entry_id"], "revision_id": revision,
                                "state": "saved", "status": "pending_review"})
            self.db.execute("INSERT INTO events(at,event,details_json) VALUES(?, 'draft_import', ?)",
                            (utc_now(), canonical({"results": results})))
        return results

    def _stale(self, revision: int) -> bool:
        rows = self.db.execute("""SELECT s.latest_snapshot,s.config_json AS current_config,
            p.snapshot_id,p.config_json AS pinned_config FROM citations c
            JOIN snapshots p USING(snapshot_id) JOIN sources s USING(source_id) WHERE c.revision_id=?""", (revision,)).fetchall()
        return not rows or any(row["latest_snapshot"] != row["snapshot_id"] or
                               row["current_config"] != row["pinned_config"] or
                               not _source_usable(json.loads(row["current_config"])) for row in rows)

    def entry(self, entry_id: str, revision_id: int | None = None) -> dict[str, Any]:
        if revision_id is None:
            row = self.db.execute("""SELECT r.* FROM entries e JOIN entry_revisions r
                ON r.revision_id=e.current_revision WHERE e.entry_id=?""", (entry_id,)).fetchone()
        else:
            row = self.db.execute("SELECT * FROM entry_revisions WHERE entry_id=? AND revision_id=?", (entry_id, revision_id)).fetchone()
        if row is None:
            raise ContractError("entry revision not found")
        if digest(row["payload_json"]) != row["payload_sha256"]:
            raise ContractError("entry integrity mismatch")
        payload = json.loads(row["payload_json"])
        from .names import display_names
        return {"revision_id": row["revision_id"], "status": row["status"], "created_at": row["created_at"],
                "published_at": row["published_at"], "payload_sha256": row["payload_sha256"],
                "review": json.loads(row["review_json"]) if row["review_json"] else None,
                "stale": self._stale(row["revision_id"]), "entry": payload, "display_names": display_names(payload),
                "sources": [self.snapshot(c["snapshot_id"]) for c in payload["citations"]]}

    def review(self, entry_id: str, revision: int, decision: str, reviewer: str,
               note: str, attested: bool) -> dict[str, Any]:
        required_text(reviewer, "reviewer", 200)
        required_text(note, "review note")
        if not attested:
            raise ContractError("explicit --human-reviewed attestation is required")
        if decision not in {"approve", "reject"}:
            raise ContractError("decision must be approve or reject")
        item = self.entry(entry_id)
        if item["revision_id"] != revision or item["status"] != "pending_review":
            raise ContractError("review must target the current pending revision")
        if decision == "approve" and item["stale"]:
            raise ContractError("stale source evidence; recollect/revise before approval")
        review = {"decision": decision, "reviewer": reviewer, "note": note, "at": utc_now()}
        with self.db:
            self.db.execute("UPDATE entry_revisions SET status=?,review_json=? WHERE revision_id=?",
                            ("approved" if decision == "approve" else "rejected", canonical(review), revision))
            self.db.execute("INSERT INTO events(at,event,details_json) VALUES(?,'entry_review',?)",
                            (utc_now(), canonical({"entry_id": entry_id, "revision_id": revision, **review})))
        return self.entry(entry_id)

    def publish(self, entry_id: str, revision: int) -> dict[str, Any]:
        item = self.entry(entry_id)
        if item["revision_id"] != revision or item["status"] != "approved" or item["stale"]:
            raise ContractError("only the current approved revision with current evidence can be published")
        with self.db:
            self.db.execute("UPDATE entry_revisions SET status='published',published_at=? WHERE revision_id=?", (utc_now(), revision))
            self.db.execute("INSERT INTO events(at,event,details_json) VALUES(?,'entry_publish',?)",
                            (utc_now(), canonical({"entry_id": entry_id, "revision_id": revision})))
        return self.entry(entry_id)

    def relations(self, entry_id: str) -> dict[str, Any]:
        """Private current-revision graph; never used by published search."""
        self.entry(entry_id)
        rows = self.db.execute("""SELECT r.entry_id AS source_entry_id, l.* FROM entry_relations l
            JOIN entry_revisions r USING(revision_id) JOIN entries e ON e.current_revision=r.revision_id
            WHERE r.entry_id=? OR l.target_entry_id=? ORDER BY r.entry_id,l.target_entry_id,l.kind""", (entry_id, entry_id))
        result = []
        for row in rows:
            value = dict(row)
            other = row["target_entry_id"] if row["source_entry_id"] == entry_id else row["source_entry_id"]
            target = self.entry(other)
            value.update({"direction": "outgoing" if row["source_entry_id"] == entry_id else "incoming",
                          "related_entry_id": other, "related_names": target["display_names"], "related_status": target["status"],
                          "evidence_state": "planned_editorial_claim" if row["kind"].startswith("planned:") else "partial_item_hint" if row["kind"] == "badge_hint" else "official_condition_mention"})
            result.append(value)
        return {"scope": "review_preview", "entry_id": entry_id, "relations": result}

    def search(self, text: str, *, preview: bool = False, limit: int = 20, names_only: bool = False) -> dict[str, Any]:
        required_text(text, "search text", 200)
        if not 1 <= limit <= 100:
            raise ContractError("search limit must be between 1 and 100")
        needle = normalize(text)
        from .names import name_key, name_records
        compact = name_key(text)
        # Small corpus: inspect separate labels rather than concatenate names or
        # rewrite stored indexes. Legacy rows immediately gain the same lookup.
        rows = self.db.execute("""SELECT r.entry_id,r.revision_id,r.payload_json,r.search_text FROM entries e
            JOIN entry_revisions r ON r.revision_id=e.current_revision
            WHERE (? OR r.status='published') ORDER BY r.entry_id""", (preview,))
        matches = []
        exact_ids = []
        observed_denials: dict[str, bool] = {}
        for row in rows:
            labels = name_records(json.loads(row["payload_json"]))
            exact_names = [n for n in labels if name_key(n["text"]) == compact]
            if not exact_names and (names_only or needle not in row["search_text"]):
                continue
            item = self.entry(row["entry_id"], row["revision_id"])
            if not preview and item["stale"]:
                continue
            if not preview and any(s["provenance"]["current_usage"]["search_index"]["status"] != "allowed" for s in item["sources"]):
                continue
            if not preview:
                restricted = False
                for source in item["sources"]:
                    sid, url = source["source_id"], source["source"]["url"]
                    if sid not in observed_denials:
                        observed_denials[sid] = False
                        # A repeated fetch may deduplicate identical raw bytes/config,
                        # while its newly observed robots signals differ. Keep that
                        # successful observation effective without rewriting a snapshot.
                        for observation in self.db.execute("SELECT details_json FROM events WHERE source_id=? AND event='collection_result' ORDER BY event_id DESC", (sid,)):
                            details = json.loads(observation[0])
                            if "robots_assessment" in details or isinstance(details.get("robots_text"), str) or details.get("robots_http_status") in {404, 410}:
                                observed_denials[sid] = _robots_search_denied(details, url)
                                break
                    if _robots_search_denied(source["metadata"], url) or observed_denials[sid]:
                        restricted = True
                        break
                # Mixed-source summaries cannot be safely split automatically. Exclude
                # the whole entry if any citation restricts search; preview stays private.
                if restricted:
                    continue
            # Formal results never return private evidence quotes or raw source body.
            item["entry"] = dict(item["entry"])
            if not preview:
                # A published source must not reveal identifiers/evidence from a
                # linked pending/rejected/stale target. Inspect the graph privately.
                item["entry"].pop("links", None)
                item["entry"].pop("knowledge_links", None)
                # Private anchors are for review, not published search output.
                if "knowledge_details" in item["entry"]:
                    detail = item["entry"]["knowledge_details"]
                    item["entry"]["knowledge_details"] = {**detail, "fields": {k: {"value": v["value"]} for k, v in detail["fields"].items()}}
            item["entry"]["citations"] = [{k: v for k, v in c.items() if k != "evidence_quote"}
                                          for c in item["entry"]["citations"]]
            item["name_matches"] = exact_names
            item["match_type"] = "exact_name" if exact_names else "full_text"
            if exact_names:
                exact_ids.append(row["entry_id"])
            matches.append(item)
        matches.sort(key=lambda item: (item["match_type"] != "exact_name", item["entry"]["entry_id"]))
        return {"scope": "review_preview" if preview else "published", "query": text,
                "status": "ok" if matches else "no_data", "matches": matches[:limit],
                "total_matches": len(matches), "truncated": len(matches) > limit,
                "name_resolution": {"status": "ambiguous" if len(exact_ids) > 1 else "unique" if exact_ids else "unresolved",
                                    "entry_ids": exact_ids}, "names_only": names_only}

    def stats(self) -> dict[str, Any]:
        counts = {table: self.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                  for table in ("sources", "snapshots", "entries", "entry_revisions", "events", "entry_relations")}
        states = {row["status"]: row["n"] for row in self.db.execute("""SELECT r.status,count(*) AS n
            FROM entries e JOIN entry_revisions r ON r.revision_id=e.current_revision GROUP BY r.status""")}
        return {"data_dir": str(self.root), "database": str(self.root / "knowledge.sqlite3"),
                "schema_version": 1, "free_bytes": shutil.disk_usage(self.root).free,
                "counts": counts, "current_states": states}
