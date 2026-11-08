"""Build/check this repo's own interface contracts; no DB, network or installs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ssr_knowledge.acceptance_native import FORMAT, MAX_BYTES, OPERATIONS, SCENARIOS, SCHEMAS
from ssr_knowledge.cli import build_parser


def exact(properties):
    return {"type": "object", "required": list(properties), "properties": properties, "additionalProperties": False}


def products():
    def source_schema(name): return json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))
    payloads = {
        "validate": exact({"schema": {"type": "string", "enum": sorted(SCHEMAS)}, "value": {}}),
        "prebuild_preview": exact({"source": source_schema("prebuild-source.schema.json")}),
        "gap_supplement_preview": exact({"gaps": source_schema("gap-export.schema.json"), "records": source_schema("supplement-records.schema.json")}),
        "catalog_check": exact({"scenario": {"type": "string", "enum": sorted(SCENARIOS)}, "query": {"type": "string", "minLength": 1, "maxLength": 200}}),
    }
    request = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": FORMAT,
               "oneOf": [exact({"format": {"type": "string", "enum": [FORMAT]}, "operation": {"type": "string", "enum": [operation]}, "input": payloads[operation]}) for operation in sorted(OPERATIONS)],
               "x-native-profile": {"max_utf8_bytes": MAX_BYTES, "max_depth": 32, "max_nodes": 5000,
                                    "synthetic_records": "1..10; fixture- ID, fictional source_type, fixture:// locator; further native nonempty/referential checks apply",
                                    "query": "nonblank 1..200 Unicode characters", "strict_json": "reject nonfinite constants"}}
    response = exact({
        "format": {"type": "string", "enum": ["ssr.knowledge.acceptance.response.v1"]},
        "synthetic_only": {"type": "boolean", "enum": [True]},
        "network_used": {"type": "boolean", "enum": [False]}, "llm_used": {"type": "boolean", "enum": [False]},
        "production_data_used": {"type": "boolean", "enum": [False]},
        "status": {"type": "string", "enum": ["ok", "rejected", "error"]},
        "operation": {"type": "string", "enum": sorted(OPERATIONS)}, "data": {"type": "object"},
        "errors": {"type": "array", "items": {"type": "string"}},
        "temporary_state_created": {"type": "boolean"}, "temporary_state_removed": {"type": "boolean"},
        "before": {"type": "object"}, "after": {"type": "object"},
        "error_type": {"type": "string"}, "errno": {"type": ["integer", "null"]},
    })
    response["required"] = ["format", "synthetic_only", "network_used", "llm_used", "production_data_used", "status"]
    response.update({"$schema": request["$schema"], "title": "ssr.knowledge.acceptance.response.v1",
                     "x-status-semantics": "ok means request executed; data may still be schema_invalid, no_data or rejected. No browser acceptance implied."})
    parser = build_parser()
    commands = next(action.choices for action in parser._actions if isinstance(action, argparse._SubParsersAction))
    catalog = next(action.choices for action in commands["catalog"]._actions if isinstance(action, argparse._SubParsersAction))
    runtime = [*sorted((ROOT / "ssr_knowledge").glob("*.py")), *sorted((ROOT / "contracts").glob("*.schema.json")), ROOT / "fixtures" / "collection-example-source.synthetic.json"]
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    manifest = {"format": "ssr.knowledge.interfaces.v1", "producer": "ssr-knowledge/" + version,
                "responsibility": "Independent offline preparation and PEAK catalog; no chat/LLM, no identity inference, no complete shared-Record export",
                "cli_commands": sorted(commands), "catalog_actions": sorted(catalog),
                "native": {"entry": ["python", "-B", "-X", "utf8", "-m", "ssr_knowledge", "acceptance-native"],
                           "library": ["ssr_knowledge.acceptance_native.handle_request", "ssr_knowledge.acceptance_native.handle_json"],
                           "request_format": FORMAT, "response_format": "ssr.knowledge.acceptance.response.v1",
                           "operations": sorted(OPERATIONS), "exit_codes": {"0": "processed; inspect native data status", "1": "rejected/native error", "2": "argparse rejects unsupported CLI arguments; stderr, no response envelope"},
                           "max_utf8_bytes": MAX_BYTES, "web_transport_connected": False},
                "legacy_outputs": {"prebuild": "contracts/candidate.schema.json", "research": "contracts/research-packet.schema.json", "publish": "contracts/published-bundle.schema.json",
                                   "errors": {"exit_1": {"status": "error", "error": "diagnostic string"}, "exit_2": "argparse usage on stderr; not a JSON envelope"},
                                   "catalog_search": ["scope", "query", "status", "matches", "total_matches", "truncated", "name_resolution", "names_only"],
                                   "catalog_match": ["revision_id", "status", "stale", "entry", "sources", "payload_sha256", "match_type"]},
                "upstream": {"provider": "ssr-collector-peak", "protocols": ["ssr.source-plan.v1", "ssr.collection.v1", "ssr.game-plan.v1"], "binding": "exact source_id/config_sha256/URL/raw/body hashes; no permission grant in bundle"},
                "downstream": {"consumer": "ssr-chat/CatalogKnowledgeReader", "entry": "catalog search --text=NAME --names-only --limit 2", "required_permission": "snapshot_usage.ai_input and current_usage.ai_input both allowed; search_index alone insufficient", "synthetic_receipt_ai_input": "unknown; not allowed for model input"},
                "shared_record_bridge": {"connected": False, "consumer": "hgpt-game-store / hgpt-ssr-game-search 1.0.1", "missing_authoritative_fields": ["schema_version", "source_event_id", "event_time", "received_at", "scope", "actor_account_id", "record_kind", "quality_flags", "source_refs", "access_scope"], "rule": "Do not rename Evidence/catalog entry into a full Record or infer source ACL/scope/version. Coordinator decision required."},
                "runtime_source_sha256": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in runtime}}
    return {"acceptance-native.request.schema.json": request, "acceptance-native.response.schema.json": response, "manifest.json": manifest}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--check", action="store_true"); args = parser.parse_args()
    directory = ROOT / "interfaces"
    failures = []
    for name, value in products().items():
        text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"; path = directory / name
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text: failures.append(name)
        else:
            directory.mkdir(exist_ok=True); path.write_text(text, encoding="utf-8")
    print("FAIL: stale interface inventory: " + ", ".join(failures) if failures else "PASS: interface inventory matches actual CLI/library/runtime")
    return bool(failures)


if __name__ == "__main__": raise SystemExit(main())
