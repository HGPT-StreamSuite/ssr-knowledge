"""Additive catalog commands; existing offline file workflows are unchanged."""
from __future__ import annotations

import argparse
from typing import Any

from .acquisition import Collector, robots_assessment, validate_manifest
from .catalog import Catalog
from .contracts import read_json
from .item_table import parse_peak_items
from .upload_source import import_text_source
from .name_reference import import_name_reference
from .community_names import match_community_names
from .game_extraction import extract_installed_text, import_game_text
from .game_localization import pair_saved_game_names
from .collection_handoff import export_source_plan, ingest_collection, register_file_source


def add_catalog_parser(commands: Any) -> None:
    parser = commands.add_parser("catalog", help="private PEAK source collection, drafts and independent search")
    parser.add_argument("--data-dir", help="outside every Git checkout; or SSR_KNOWLEDGE_DATA_DIR")
    actions = parser.add_subparsers(dest="action", required=True)
    plan = actions.add_parser('export-source-plan', help='read-only export of central sources; no knowledge entries or new permissions')
    plan.add_argument('--source-id', action='append')
    local = actions.add_parser('register-file-source', help='register explicit local-file policy centrally; never enables website crawling')
    local.add_argument('--file', required=True)
    ingest = actions.add_parser('ingest-collection', help='validate data-only collection packet; --apply explicitly archives raw/body, never knowledge entries')
    ingest.add_argument('--file', required=True)
    ingest.add_argument('--apply', action='store_true')
    extract = actions.add_parser("extract-game-names", help="read one official installed TextAsset with a bounded cache; never launches/rewrites the game")
    extract.add_argument("--game-dir", required=True)
    extract.add_argument("--output-dir", required=True)
    game = actions.add_parser("import-game-text", help="save extracted official item-name projections and original text privately")
    game.add_argument("--file", required=True)
    game.add_argument("--receipt", required=True)
    pair = actions.add_parser("pair-game-names", help="pair official item keys/locales with exact Wiki English names; no fuzzy matches")
    pair.add_argument("--en-snapshot-id", required=True)
    pair.add_argument("--zh-snapshot-id", required=True)
    pair.add_argument("--items-snapshot-id", required=True)
    badges = actions.add_parser("badge-drafts", help="project exact names/conditions from already saved official CSV; no fetch, extraction or approval")
    badges.add_argument("--en-snapshot-id", required=True)
    badges.add_argument("--zh-snapshot-id", required=True)
    upload = actions.add_parser("import-text-source", help="save explicitly supplied UTF-8 text and provenance; no HTTP")
    upload.add_argument("--file", required=True)
    upload.add_argument("--receipt", required=True)
    reference = actions.add_parser("import-name-reference", help="import reviewed pinned connector text or a bounded web excerpt, without HTTP")
    reference.add_argument("--file", required=True)
    reference.add_argument("--receipt", required=True)
    excerpt = actions.add_parser("import-web-excerpt", help="save bounded operator-selected search excerpts and provenance; no HTTP fetch or automatic discovery")
    excerpt.add_argument("--file", required=True)
    excerpt.add_argument("--receipt", required=True)
    actions.add_parser("discover-details", help="inventory saved explicit URLs and exact saved HTML links; no network or guessed slugs")
    batch = actions.add_parser("research-batch", help="resumable reviewed detail-page batch; successful substantive extraction becomes pending English candidates")
    batch.add_argument("--plan", required=True)
    batch.add_argument("--max-jobs", type=int, default=2)
    batch.add_argument("--refresh", action="store_true", help="revisit completed jobs; manual blocks remain stopped")
    batch.add_argument("--retry-blocked", action="store_true", help="explicitly reconsider blocked jobs after access/terms review")
    community = actions.add_parser("match-community-names", help="exact casefold English matches; community mod names are not game UI verification")
    community.add_argument("--snapshot-id", required=True)
    community.add_argument("--items-snapshot-id", required=True)
    parse = actions.add_parser("parse-peak-items", help="parse a pinned copied Items table; no translation, review or network")
    parse.add_argument("--snapshot-id", required=True)
    collect = actions.add_parser("collect", help="collect only reviewed exact source URLs")
    collect.add_argument("--manifest", required=True)
    collect.add_argument("--source-id", help="collect just one manifest source")
    collect.add_argument("--purpose", choices=("local_cache", "search_index", "ai_input"), default="local_cache",
                         help="terms must allow local caching and this purpose; never calls an LLM")
    register = actions.add_parser("register-sources", help="save reviewed source policies without any network requests")
    register.add_argument("--manifest", required=True)
    status = actions.add_parser("source-status", help="current purpose review plus re-evaluation of saved robots; no network")
    status.add_argument("--source-id", required=True)
    status.add_argument("--purpose", choices=("local_cache", "search_index", "ai_input", "ai_train"), default="local_cache")
    actions.add_parser("sources", help="source metadata and pinned snapshots, without body")
    snapshot = actions.add_parser("snapshot", help="inspect a private source snapshot")
    snapshot.add_argument("--snapshot-id", required=True)
    snapshot.add_argument("--body", action="store_true", help="include private extracted text for review")
    diff = actions.add_parser("snapshot-diff", help="compare pinned versions without changing any entries or reviews")
    diff.add_argument("--before", required=True)
    diff.add_argument("--after", required=True)
    diff.add_argument("--body", action="store_true", help="include bounded private unified body diff")
    drafts = actions.add_parser("import-drafts", help="validate and store operator/agent-edited summaries; does not generate or approve them")
    drafts.add_argument("--file", required=True)
    entry = actions.add_parser("entry", help="inspect a private draft or a historical revision")
    entry.add_argument("--entry-id", required=True)
    entry.add_argument("--revision", type=int)
    relations = actions.add_parser("relations", help="private incoming/outgoing current item-badge relations")
    relations.add_argument("--entry-id", required=True)
    render = actions.add_parser("render-review", help="write a private readable HTML preview from saved DB entries")
    render.add_argument("--output", required=True)
    serve = actions.add_parser("serve-review", help="live read-only SQLite review on 127.0.0.1 only; explicit data directory required")
    serve.add_argument("--port", type=int, default=8765)
    review = actions.add_parser("review-entry", help="human review of an explicit current revision")
    review.add_argument("--entry-id", required=True)
    review.add_argument("--revision", type=int, required=True)
    review.add_argument("--decision", choices=("approve", "reject"), required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--note", required=True)
    review.add_argument("--human-reviewed", action="store_true")
    publish = actions.add_parser("publish-entry", help="publish an approved revision to catalog search")
    publish.add_argument("--entry-id", required=True)
    publish.add_argument("--revision", type=int, required=True)
    search = actions.add_parser("search", help="search only published entries; --preview explicitly shows review material")
    search.add_argument("--text", required=True)
    search.add_argument("--preview", action="store_true")
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--names-only", action="store_true", help="exact bilingual name/alias after case, width and whitespace normalization; return all ambiguous IDs")
    events = actions.add_parser("events", help="private collection/review audit; may include robots text")
    events.add_argument("--limit", type=int, default=100)
    actions.add_parser("stats")


def run_catalog(args: argparse.Namespace) -> tuple[Any, int]:
    if args.action == "extract-game-names":
        return extract_installed_text(args.game_dir, args.output_dir), 0
    if args.action == "serve-review":
        from .live_review import serve_review
        serve_review(args.data_dir, args.port)
        return {"state": "stopped"}, 0
    if args.action in {'export-source-plan','register-file-source','ingest-collection'} and not args.data_dir:
        raise ValueError('collection handoff requires an explicit --data-dir')
    read_only = args.action == 'export-source-plan' or args.action == 'ingest-collection' and not args.apply
    with Catalog(args.data_dir, read_only=read_only) as store:
        if args.action == 'export-source-plan':
            return export_source_plan(store, args.source_id), 0
        if args.action == 'register-file-source':
            return register_file_source(store, read_json(args.file)), 0
        if args.action == 'ingest-collection':
            return ingest_collection(store, args.file, apply=args.apply), 0
        if args.action == "badge-drafts":
            from .organization import badge_drafts
            return badge_drafts(store, args.en_snapshot_id, args.zh_snapshot_id), 0
        if args.action == "import-game-text":
            return import_game_text(store, args.file, read_json(args.receipt)), 0
        if args.action == "pair-game-names":
            items = parse_peak_items(store.snapshot(args.items_snapshot_id, True)["body"])
            return pair_saved_game_names(store.snapshot(args.en_snapshot_id, True), store.snapshot(args.zh_snapshot_id, True),
                                         [r["item_name_en"] for r in items["items"]]), 0
        if args.action == "import-text-source":
            return import_text_source(store, args.file, read_json(args.receipt)), 0
        if args.action == "import-name-reference":
            return import_name_reference(store, args.file, read_json(args.receipt)), 0
        if args.action == "import-web-excerpt":
            from .web_excerpt import import_web_excerpt
            return import_web_excerpt(store, args.file, read_json(args.receipt)), 0
        if args.action == "discover-details":
            from .research import discover
            return discover(store), 0
        if args.action == "research-batch":
            from .research import run_batch
            result = run_batch(store, read_json(args.plan), max_jobs=args.max_jobs, refresh=args.refresh, retry_blocked=args.retry_blocked)
            return result, 2 if any(r["state"] in {"manual_required", "retry_wait"} for r in result["results"]) else 0
        if args.action == "match-community-names":
            reference = store.snapshot(args.snapshot_id, True)
            if reference["metadata"].get("name_evidence", {}).get("kind") != "community_mod":
                raise ValueError("snapshot is not a community mod name reference")
            items = parse_peak_items(store.snapshot(args.items_snapshot_id, True)["body"])
            result = match_community_names(reference["body"], [row["item_name_en"] for row in items["items"]])
            return result, 2 if result["unparsed_rows"] else 0
        if args.action == "parse-peak-items":
            result = parse_peak_items(store.snapshot(args.snapshot_id, True)["body"])
            return result, 2 if result["unparsed_rows"] or result["conflicting_duplicates"] else 0
        if args.action in {"collect", "register-sources"}:
            sources = validate_manifest(read_json(args.manifest))
            if args.action == "register-sources":
                for source in sources:
                    store.register_source(source)
                store.event(None, "source_policy_registration", {"source_ids": [s["source_id"] for s in sources], "network_requests": 0})
                return {"registered": [s["source_id"] for s in sources], "network_requests": 0}, 0
            if args.source_id:
                sources = [s for s in sources if s["source_id"] == args.source_id]
                if not sources:
                    raise ValueError("source-id not present in manifest")
            results = Collector(store).collect(sources, args.purpose)
            return {"results": results}, 2 if any(r["state"] == "blocked_or_failed" for r in results) else 0
        if args.action == "sources":
            return {"sources": store.sources()}, 0
        if args.action == "source-status":
            source = next((s for s in store.sources() if s["config"]["source_id"] == args.source_id), None)
            if source is None:
                raise ValueError("source not found")
            saved = next((e for e in store.history(1000) if e["source_id"] == args.source_id and "robots_text" in e["details"]), None)
            return {"source": source, "purpose": args.purpose, "network_requests": 0,
                    "saved_robots": None if saved is None else {
                        "observed_at": saved["at"], "robots_sha256": saved["details"].get("robots_sha256"),
                        "reassessment": robots_assessment(saved["details"]["robots_text"], source["config"]["url"], args.purpose)},
                    "note": "Saved robots are historical access evidence, not a license or proof of current access; no target requested or LLM called."}, 0
        if args.action == "snapshot":
            return store.snapshot(args.snapshot_id, args.body), 0
        if args.action == "snapshot-diff":
            return store.compare_snapshots(args.before, args.after, args.body), 0
        if args.action == "import-drafts":
            return {"results": store.import_drafts(read_json(args.file))}, 0
        if args.action == "entry":
            return store.entry(args.entry_id, args.revision), 0
        if args.action == "relations":
            return store.relations(args.entry_id), 0
        if args.action == "render-review":
            from .review_page import render_review
            return render_review(store, args.output), 0
        if args.action == "review-entry":
            return store.review(args.entry_id, args.revision, args.decision, args.reviewer, args.note, args.human_reviewed), 0
        if args.action == "publish-entry":
            return store.publish(args.entry_id, args.revision), 0
        if args.action == "search":
            return store.search(args.text, preview=args.preview, limit=args.limit, names_only=args.names_only), 0
        if args.action == "events":
            if not 1 <= args.limit <= 1000:
                raise ValueError("events limit must be 1 to 1000")
            return {"events": store.history(args.limit)}, 0
        return store.stats(), 0
