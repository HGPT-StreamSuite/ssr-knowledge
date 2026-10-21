"""Loopback-only, read-only review of the current SQLite catalog. No cache."""
from __future__ import annotations

import json
import math
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .catalog import CATEGORIES, Catalog, digest, identifier, normalize, resolve_data_dir
from .contracts import ContractError
from .names import display_names, name_key, name_records
from .review_page import LABELS, short_note

REVIEW_LABELS = {"pending_review": "內容：待使用者驗收", "approved": "內容：已核准", "rejected": "內容：已拒絕", "published": "內容：已發布"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def entry_kind(payload: dict[str, Any]) -> str:
    return "item" if payload["category"] == "item" else "badge" if payload.get("badge_details", {}).get("kind") == "game_badge" else "other"


def project_source(value: dict[str, Any], citation: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg, meta = value["source"], value["metadata"]
    kind = cfg.get("acquisition", {}).get("kind", meta.get("acquisition_kind", "saved_source"))
    local = kind == "installed_game_text"
    receipt = meta.get("receipt", {})
    browser_receipt = meta.get('capture_receipt', {})
    return {"title": cfg["title"], "type": cfg["source_type"], "language": cfg.get("language"),
            "source_id": value['source_id'], "snapshot_id": value['snapshot_id'],
            "license_statement": browser_receipt.get('license_statement'), "license_links": browser_receipt.get('license_links', []),
            "url": None if local else value["provenance"]["original_url"],
            "attribution_url": value["provenance"]["original_url"] if local else None,
            "acquisition_uri": cfg["url"], "acquisition_kind": kind,
            "resource": {k: receipt[k] for k in ("asset", "text_asset_name", "path_id", "game_version", "steam_build_id") if k in receipt} if local else None,
            "locator": citation["locator"] if citation else None, "evidence_quote": citation["evidence_quote"] if citation else None,
            "saved_at": value["fetched_at"], "source_updated_at": meta.get("source_updated_at"), "version": cfg.get("declared_version")}


def project_entry(store: Catalog, record: dict[str, Any], *, detailed: bool = False) -> dict[str, Any]:
    payload = record["entry"]
    names = display_names(payload)
    sources = [project_source(s, c) for s, c in zip(record["sources"], payload["citations"])]
    items_sources = [s for s in sources if s["type"] == "wiki" and urlsplit(s["url"] or "").hostname == "peak.wiki.gg" and urlsplit(s["url"] or "").path.rstrip("/") == "/wiki/Items"]
    wiki_label = ("Wiki Items：已保存附件" if any(s["acquisition_kind"] == "user_provided_text" for s in items_sources)
                  else "Wiki Items：已保存引用" if items_sources else "來源：已有保存引用")
    detail = payload.get("detail_page")
    if detail is None:
        detail_status = {"state": "missing_link", "label": "詳細頁：尚未補連結", "url": None, "http_status": None}
    elif detail["status"] == "verified":
        detail_status = {"state": "verified", "label": "詳細頁：已有核對紀錄", "url": detail["url"], "http_status": detail["http_status"]}
    else:
        code = detail.get("http_status")
        label = "詳細頁：未讀取（HTTP " + str(code) + "）" if isinstance(code, int) and code >= 400 else "詳細頁：連結已保存，讀頁尚未確認"
        detail_status = {"state": "unread", "label": label, "url": detail["url"], "http_status": code}
    preferred = names.get("zh-TW", {})
    name_label = "官方中英名稱（資源文字）" if preferred.get("status") == "game_ui_verified" else "中文暫譯" if preferred.get("status") == "provisional_translation" else "既有名稱"
    sections = []
    missing = []
    org = payload.get("organization")
    if org:
        for topic, label in LABELS.items():
            notes = [short_note(org["notes_zh"][i], topic) for i in org["topics"][topic]]
            if notes:
                sections.append({"label": label, "notes": notes})
            else:
                missing.append(label)
        methods = [org["notes_zh"][i] for i in org["topics"]["badge_hints"]
                   if not payload["item_details"]["notes_en"][i].startswith(("Can be used for ", "Part of ", "Required for "))]
        if methods:
            sections.append({"label": "徽章用法", "notes": methods})
    elif "badge_details" in payload:
        sections.append({"label": "條件（官方顯示文字）", "notes": [payload["badge_details"]["condition_zh"]]})
    else:
        sections.append({"label": "已保存摘要", "notes": [payload["summary_zh"]]})
    guide = payload.get("guide_details")
    from .guide_details import TOPICS
    guide_claims = [{"topic": c["topic"], "label": TOPICS[c["topic"]], "text_zh": c["text_zh"], "source_class": c["source_class"],
                     "evidence": [{"quote": e["quote"], "source": sources[e["citation"]]} for e in c["evidence"]]} for c in guide["claims"]] if guide else []
    guide_gaps = [{**g, "label": TOPICS[g["topic"]]} for g in guide["gaps"]] if guide else []
    extracts = [{"translation_status": e["translation_status"], "coverage": e["coverage"], "missing_labels": [TOPICS.get(t, t) for t in e["coverage"]["missing"]], "source": sources[e["citation"]],
                 "blocks": [{**b, "label": TOPICS[b["topic"]]} for b in e["blocks"]]} for e in payload.get("research_extracts", [])]
    result = {"entry_id": payload["entry_id"], "revision_id": record["revision_id"], "kind": entry_kind(payload), "category": payload["category"],
              "name_zh": preferred.get("text", payload["name_zh"]), "name_en": names.get("en", {}).get("text", payload["name_en"]),
              "name_label": name_label, "review_status": record["status"], "review_label": REVIEW_LABELS[record["status"]],
              "stale": record["stale"], "wiki_items_present": bool(items_sources), "source_label": wiki_label,
              "detail_page": detail_status if payload["category"] == "item" else None, "sections": sections, "missing_topics": missing,
              "guide_claims": guide_claims, "guide_gaps": guide_gaps, "research_extracts": extracts,
              "teaser": next((("" if s["label"] in {"用途與效果", "已保存摘要"} else s["label"] + "：") + s["notes"][0] for s in sections if s["notes"]), "")}
    result.update(knowledge_fields=[], knowledge_gaps=[], plan_id=None, category_label=payload['category'])
    knowledge = payload.get('knowledge_details')
    if knowledge:
        # Legacy organization describes the original Items table only. A field
        # saved later in the same revision must not still be called missing.
        saved_topics = {'purpose': 'effects', 'acquisition': 'acquisition',
                        'constraints': 'conditions', 'cooking': 'cooking'}
        provided_labels = {LABELS[saved_topics[key]] for key in knowledge['fields'] if key in saved_topics}
        result['missing_topics'] = [label for label in result['missing_topics'] if label not in provided_labels]
        from .game_plan import get_plan
        plan = get_plan(store, knowledge['plan_id'])
        category = next(c for c in plan['categories'] if c['id'] == payload['category'])
        result.update(plan_id=plan['plan_id'], category_label=category['label'])
        for field in category['fields']:
            key = field['id']
            if key in knowledge['fields']:
                saved = knowledge['fields'][key]
                result['knowledge_fields'].append({**field, 'value': saved['value'],
                    'evidence': [{'quote': e['quote'], 'source': sources[e['citation']]} for e in saved['evidence']]})
            else:
                result['knowledge_gaps'].append({'id': key, 'label': field['label'], 'reason': knowledge['gaps'][key]})
    if detailed:
        related = {}
        for link in store.relations(payload["entry_id"])["relations"]:
            eid = link["related_entry_id"]
            target = store.entry(eid)["entry"]
            other = related.setdefault(eid, {"entry_id": eid, "name_zh": link["related_names"].get("zh-TW", {}).get("text", target["name_zh"]),
                                             "name_en": link["related_names"].get("en", {}).get("text", ""), "evidence": [], "evidence_details": []})
            label = "Items 備註提示" if link["kind"] == "badge_hint" else "官方條件提及"
            if link['kind'].startswith('planned:'):
                from .game_plan import get_plan
                origin_payload = store.entry(link['source_entry_id'], link['revision_id'])['entry']
                origin_plan = get_plan(store, origin_payload['knowledge_details']['plan_id'])
                definition = next(r for r in origin_plan['relation_types'] if r['id'] == link['kind'].removeprefix('planned:'))
                label = ('本條目 → ' if link['direction'] == 'outgoing' else '本條目 ← ') + definition['label'] + '（待審證據）'
            if label not in other["evidence"]:
                other["evidence"].append(label)
            origin = store.entry(link["source_entry_id"], link["revision_id"])
            index = link["citation_index"]
            note = link["note_index"]
            translation = origin["entry"].get("organization", {}).get("notes_zh", [])
            other["evidence_details"].append({"label": label, "text_en": link["evidence_text"],
                "text_zh": translation[note] if isinstance(note, int) and note < len(translation) else None,
                "source": project_source(origin["sources"][index], origin["entry"]["citations"][index])})
        result.update({"aliases": payload["aliases"], "sources": sources, "relations": list(related.values()),
                       "limitations": payload['limitations'],
                       "game_version": payload["game_version"], "saved_at": record["created_at"],
                       "statistics": payload.get("item_details", {}).get("statistics", {}),
                       "notes_en": payload.get("item_details", {}).get("notes_en", []),
                       "biomes_en": payload.get("item_details", {}).get("biomes_en", []),
                       "locations_en": payload.get("item_details", {}).get("locations_en", []),
                       "condition_en": payload.get("badge_details", {}).get("condition_en"),
                       "steam_equivalence": payload.get("badge_details", {}).get("steam_equivalence")})
    return result


def query_options(query: str) -> dict[str, Any]:
    values = parse_qs(query, keep_blank_values=True)
    if set(values) - {"q", "kind", "category", "page", "page_size", "entry"} or any(len(v) != 1 for v in values.values()):
        raise ValueError("查詢參數不支援或重複")
    q, kind, entry = (values.get(k, [default])[0] for k, default in (("q", ""), ("kind", "all"), ("entry", "")))
    if len(q) > 200 or kind not in {"all", "item", "badge", "other"}:
        raise ValueError("搜尋最多 200 字；分類必須為全部、道具、徽章或其他")
    category = values.get('category', ['all'])[0]
    if category not in CATEGORIES | {'all'}:
        raise ValueError('不支援的知識分類')
    try:
        page, size = int(values.get("page", ["1"])[0]), int(values.get("page_size", ["20"])[0])
    except ValueError as exc:
        raise ValueError("頁碼與每頁筆數必須為整數") from exc
    if not 1 <= page <= 1_000_000 or not 1 <= size <= 100:
        raise ValueError("頁碼或每頁筆數超出範圍")
    if entry:
        identifier(entry)
    return {"q": q, "kind": kind, "category": category, "page": page, "page_size": size, "entry_id": entry or None}


def load_model(data_dir: Path, options: dict[str, Any]) -> dict[str, Any]:
    """One new read-only connection and one consistent transaction per request."""
    with Catalog(data_dir, read_only=True) as store:
        store.db.execute("BEGIN")
        rows = list(store.db.execute("SELECT r.* FROM entries e JOIN entry_revisions r ON e.current_revision=r.revision_id"))
        counts = {"entries": len(rows), "items": 0, "organized_items": 0, "game_badges": 0, "other": 0}
        states: dict[str, int] = {}
        candidates = []
        q, compact = normalize(options["q"]), name_key(options["q"])
        for row in rows:
            if digest(row["payload_json"]) != row["payload_sha256"]:
                raise ContractError("條目內容完整性檢查失敗")
            payload = json.loads(row["payload_json"])
            kind = entry_kind(payload)
            counts[{"item": "items", "badge": "game_badges", "other": "other"}[kind]] += 1
            counts["organized_items"] += "organization" in payload
            states[row["status"]] = states.get(row["status"], 0) + 1
            if options["kind"] != "all" and kind != options["kind"]:
                continue
            if options.get('category', 'all') != 'all' and payload['category'] != options['category']:
                continue
            exact = bool(q) and any(name_key(n["text"]) == compact for n in name_records(payload))
            if q and not exact and q not in row["search_text"]:
                continue
            candidates.append((not exact, normalize(payload["name_en"]), payload["entry_id"], row["revision_id"]))
        candidates.sort()
        pages = max(1, math.ceil(len(candidates) / options["page_size"]))
        page = min(options["page"], pages)
        offset = (page - 1) * options["page_size"]
        entries = [] if options["entry_id"] else [project_entry(store, store.entry(eid, revision)) for _, _, eid, revision in candidates[offset:offset + options["page_size"]]]
        if options["entry_id"] and not any(r["entry_id"] == options["entry_id"] for r in rows):
            raise LookupError("指定條目不存在於目前 DB")
        detail = project_entry(store, store.entry(options["entry_id"]), detailed=True) if options["entry_id"] else None
        database = store.root / "knowledge.sqlite3"
        latest = store.db.execute("SELECT max(revision_id),max(created_at) FROM entry_revisions").fetchone()
        metadata = {"database": str(database), "read_at": now(), "database_file_modified_at": datetime.fromtimestamp(database.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
                    "latest_revision_id": latest[0], "latest_revision_recorded_at": latest[1], "schema_version": 1, "read_only": True,
                    "counts": counts, "review_states": states,
                    "revision_count": store.db.execute("SELECT count(*) FROM entry_revisions").fetchone()[0],
                    "relation_count": store.db.execute("SELECT count(*) FROM entry_relations").fetchone()[0]}
        from .game_plan import coverage
        return {"metadata": metadata, "plans": coverage(store), "view": "detail" if detail else "list", "query": {**options, "page": page}, "total_matches": len(candidates), "pages": pages,
                "exact_name_entry_ids": [eid for nonexact, _, eid, _ in candidates if not nonexact], "entries": entries, "detail": detail}


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, data_dir: Path, port: int):
        self.data_dir = resolve_data_dir(data_dir)
        super().__init__(("127.0.0.1", port), ReviewHandler)
        self.origin = "http://127.0.0.1:" + str(self.server_port)


class ReviewHandler(BaseHTTPRequestHandler):
    server: ReviewServer

    def log_message(self, *_: Any) -> None:
        pass  # Query strings can contain private text; no access log.

    def send_body(self, status: int, value: Any, *, json_result: bool = False) -> None:
        data = (json.dumps(value, ensure_ascii=False, allow_nan=False) if json_result else value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8" if json_result else "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(data)

    def error(self, status: int, message: str, *, api: bool = False) -> None:
        from .live_review_html import render_error
        value = {"error": message, "database": str(self.server.data_dir / "knowledge.sqlite3"), "read_at": now(), "read_only": True}
        self.send_body(status, value if api else render_error(value), json_result=api)

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        api = parsed.path == "/api/review"
        # A user may follow a normal link/bookmark from another origin. Permit
        # top-level document navigation without Origin, but reject cross-site
        # fetches, images and iframes. Host/Origin checks still prevent rebinding.
        top_navigation = self.headers.get("Sec-Fetch-Mode") == "navigate" and self.headers.get("Sec-Fetch-Dest") == "document" and not self.headers.get("Origin")
        if self.headers.get("Host") != self.server.origin.removeprefix("http://") or self.headers.get("Origin", self.server.origin) != self.server.origin or (self.headers.get("Sec-Fetch-Site") == "cross-site" and not top_navigation):
            self.error(403, "此唯讀入口只接受相同 loopback 位址的請求", api=api)
            return
        if len(self.path) > 4096:
            self.error(414, "查詢網址過長", api=api)
            return
        if parsed.path not in {"/", "/api/review"}:
            self.error(404, "找不到此頁面", api=api)
            return
        try:
            options = query_options(parsed.query)
        except (ValueError, ContractError) as exc:
            self.error(400, str(exc), api=api)
            return
        try:
            model = load_model(self.server.data_dir, options)
        except LookupError as exc:
            self.error(404, str(exc), api=api)
            return
        except (OSError, sqlite3.Error, ContractError, KeyError, TypeError, ValueError) as exc:
            self.error(503, "無法讀取指定 DB：" + str(exc), api=api)
            return
        from .live_review_html import render_page
        self.send_body(200, model if api else render_page(model), json_result=api)

    def do_POST(self) -> None:
        self.error(405, "此入口只讀；不提供匯入、批准或修改操作", api=urlsplit(self.path).path == "/api/review")

    do_PUT = do_DELETE = do_PATCH = do_POST


def serve_review(data_dir: str | None, port: int = 8765) -> None:
    selected = data_dir or os.environ.get("SSR_KNOWLEDGE_DATA_DIR")
    if not selected:
        raise ContractError("請用 --data-dir 或 SSR_KNOWLEDGE_DATA_DIR 明確指定現有 DB 資料夾")
    if not 1 <= port <= 65535:
        raise ContractError("port 必須介於 1 與 65535")
    with ReviewServer(Path(selected), port) as server:
        print("本機唯讀驗收入口：" + server.origin + "/", flush=True)
        print("指定 DB：" + str(server.data_dir / "knowledge.sqlite3"), flush=True)
        print("每次查詢重新讀取 SQLite；Ctrl+C 停止。", flush=True)
        try:
            server.serve_forever(poll_interval=0.25)
        except KeyboardInterrupt:
            pass
