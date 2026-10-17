from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .contracts import read_json, validate
from .store import LocalKnowledgeStore
from .workflows import prepare_gap_supplement, prepare_prebuild, query_published, review_candidate


ROOT = Path(__file__).resolve().parents[1]


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ssr-knowledge")
    commands = parser.add_subparsers(dest="command", required=True)

    prebuild = commands.add_parser("prebuild", help="prepare a reviewed candidate from a local source bundle")
    prebuild.add_argument("--source", required=True)
    prebuild.add_argument("--state-dir", default=".local-state")

    supplement = commands.add_parser("supplement", help="import question gaps and researched sourced records")
    supplement.add_argument("--gaps", required=True)
    supplement.add_argument("--records", required=True)
    supplement.add_argument("--state-dir", default=".local-state")

    review = commands.add_parser("review", help="record a human candidate review")
    review.add_argument("--candidate-id", required=True)
    review.add_argument("--decision", choices=("approve", "reject"), required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--note", default="")
    review.add_argument("--state-dir", default=".local-state")

    publish = commands.add_parser("publish", help="publish an approved candidate as an immutable version")
    publish.add_argument("--candidate-id", required=True)
    publish.add_argument("--version", required=True)
    publish.add_argument("--state-dir", default=".local-state")

    query = commands.add_parser("query", help="read one explicit published version")
    query.add_argument("--version", required=True)
    query.add_argument("--kind", choices=("person", "game_info", "game_guide", "game_item"), required=True)
    query.add_argument("--text", default="")
    query.add_argument("--state-dir", default=".local-state")

    tools = commands.add_parser("tools", help="inspect fixed local tool-preparation settings")
    tools.add_argument("--config", default=str(ROOT / "fixtures" / "tool-config.json"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = LocalKnowledgeStore(getattr(args, "state_dir", ".local-state"))
    if args.command == "prebuild":
        result = prepare_prebuild(read_json(args.source), store)
    elif args.command == "supplement":
        result = prepare_gap_supplement(read_json(args.gaps), read_json(args.records), store)
    elif args.command == "review":
        result = review_candidate(args.candidate_id, args.decision, args.reviewer, args.note, store)
    elif args.command == "publish":
        result = store.publish(args.candidate_id, args.version)
    elif args.command == "query":
        result = query_published(args.version, args.kind, args.text, store)
    else:
        result = read_json(args.config)
        validate(result, "tool-config.schema.json")
    _print(result)


if __name__ == "__main__":
    main()
