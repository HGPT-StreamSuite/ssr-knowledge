"""Additive catalog commands; existing offline file workflows are unchanged."""
from __future__ import annotations

import argparse
from typing import Any

from .acquisition import Collector, validate_manifest
from .catalog import Catalog
from .contracts import read_json


def add_catalog_parser(commands: Any) -> None:
    parser = commands.add_parser("catalog", help="private PEAK source collection, drafts and independent search")
    parser.add_argument("--data-dir", help="outside every Git checkout; or SSR_KNOWLEDGE_DATA_DIR")
    actions = parser.add_subparsers(dest="action", required=True)
    collect = actions.add_parser("collect", help="collect only reviewed exact source URLs")
    collect.add_argument("--manifest", required=True)
    collect.add_argument("--source-id", help="collect just one manifest source")
    actions.add_parser("sources", help="source metadata and pinned snapshots, without body")
    snapshot = actions.add_parser("snapshot", help="inspect a private source snapshot")
    snapshot.add_argument("--snapshot-id", required=True)
    snapshot.add_argument("--body", action="store_true", help="include private extracted text for review")
    drafts = actions.add_parser("import-drafts", help="validate and store operator/agent-edited summaries; does not generate or approve them")
    drafts.add_argument("--file", required=True)
    entry = actions.add_parser("entry", help="inspect a private draft or a historical revision")
    entry.add_argument("--entry-id", required=True)
    entry.add_argument("--revision", type=int)
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
    events = actions.add_parser("events", help="private collection/review audit; may include robots text")
    events.add_argument("--limit", type=int, default=100)
    actions.add_parser("stats")


def run_catalog(args: argparse.Namespace) -> tuple[Any, int]:
    with Catalog(args.data_dir) as store:
        if args.action == "collect":
            sources = validate_manifest(read_json(args.manifest))
            if args.source_id:
                sources = [s for s in sources if s["source_id"] == args.source_id]
                if not sources:
                    raise ValueError("source-id not present in manifest")
            results = Collector(store).collect(sources)
            return {"results": results}, 2 if any(r["state"] == "blocked_or_failed" for r in results) else 0
        if args.action == "sources":
            return {"sources": store.sources()}, 0
        if args.action == "snapshot":
            return store.snapshot(args.snapshot_id, args.body), 0
        if args.action == "import-drafts":
            return {"results": store.import_drafts(read_json(args.file))}, 0
        if args.action == "entry":
            return store.entry(args.entry_id, args.revision), 0
        if args.action == "review-entry":
            return store.review(args.entry_id, args.revision, args.decision, args.reviewer, args.note, args.human_reviewed), 0
        if args.action == "publish-entry":
            return store.publish(args.entry_id, args.revision), 0
        if args.action == "search":
            return store.search(args.text, preview=args.preview, limit=args.limit), 0
        if args.action == "events":
            if not 1 <= args.limit <= 1000:
                raise ValueError("events limit must be 1 to 1000")
            return {"events": store.history(args.limit)}, 0
        return store.stats(), 0
