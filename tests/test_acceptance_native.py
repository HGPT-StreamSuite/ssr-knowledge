"""Real native calls with fresh synthetic state; never sockets or real data."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ssr_knowledge.acceptance_native import FORMAT, MAX_BYTES, handle_json, handle_request

ROOT = Path(__file__).resolve().parents[1]
def fixture(name): return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))
def request(operation, payload): return {"format": FORMAT, "operation": operation, "input": payload}
def catalog(scenario="pending", query="月繩"): return request("catalog_check", {"scenario": scenario, "query": query})


class NativeAcceptanceTests(unittest.TestCase):
    def test_validate_real_contract_positive_and_negative(self):
        value = fixture("prebuild-source.json")
        for item, expected in [(value, "schema_valid"), ({}, "schema_invalid")]:
            result = handle_request(request("validate", {"schema": "prebuild-source.schema.json", "value": item}))
            self.assertEqual(result["data"]["status"], expected)
            self.assertFalse(result["temporary_state_created"])

    def test_paths_commands_endpoints_and_acl_are_not_request_options(self):
        for key in ["command", "python", "file", "database", "endpoint", "acl", "policy"]:
            value = catalog(); value[key] = "forbidden"
            self.assertEqual(handle_request(value)["status"], "rejected", key)
        value = catalog(); value["input"]["database"] = "arbitrary"
        self.assertEqual(handle_request(value)["status"], "rejected")
        self.assertEqual(handle_request(request("validate", {"schema": "../../other.json", "value": {}}))["status"], "rejected")

    def test_prebuild_really_saves_and_reads_pending_candidate_then_removes_own_state(self):
        result = handle_request(request("prebuild_preview", {"source": fixture("prebuild-source.json")}))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["candidate"], result["data"]["readback"])
        self.assertEqual(result["data"]["candidate"]["status"], "pending_review")
        self.assertEqual(result["before"]["files"], 0)
        self.assertTrue(result["after"]["artifacts"])
        self.assertTrue(result["temporary_state_removed"])

    def test_empty_and_nonfictional_prebuild_records_are_rejected(self):
        for source in [dict(bundle_id="fixture-empty", records=[]), fixture("prebuild-source.json")]:
            if source["records"]: source["records"][0]["source"]["locator"] = "file:///private"
            self.assertEqual(handle_request(request("prebuild_preview", {"source": source}))["status"], "rejected")

    def test_gap_supplement_real_linkage_and_invalid_recovery(self):
        payload = {"gaps": fixture("gap-export.json"), "records": fixture("gap-records.json")}
        bad = copy.deepcopy(payload); bad["records"]["records"][0]["gap_id"] = "unknown"
        rejected = handle_request(request("gap_supplement_preview", bad))
        self.assertEqual(rejected["status"], "rejected"); self.assertTrue(rejected["temporary_state_removed"])
        result = handle_request(request("gap_supplement_preview", payload))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["candidate"]["research_id"], result["data"]["research"]["research_id"])
        self.assertEqual(result["data"]["candidate"]["status"], "pending_review")

    def test_pending_publication_refusal_and_duplicate_import(self):
        result = handle_request(catalog())["data"]
        self.assertEqual(result["formal"]["status"], "no_data")
        self.assertEqual(result["preview"]["matches"][0]["status"], "pending_review")
        self.assertIn("approved", result["publication_block"])
        self.assertEqual(result["duplicate"]["state"], "unchanged")
        self.assertEqual(result["after"]["entry_revisions"], 1)

    def test_published_query_preserves_source_citation_version_and_new_connection(self):
        result = handle_request(catalog("published"))["data"]
        self.assertEqual(result["formal"]["status"], "ok")
        self.assertEqual(result["entry"]["entry"]["game_version"], "synthetic-v1")
        self.assertEqual(result["entry"]["entry"]["citations"][0]["evidence_quote"], "Lunar Rope is fictional.")
        self.assertEqual(result["readback"]["revision_id"], result["saved"]["revision_id"])
        self.assertEqual(result["readback"]["formal"], result["formal"])
        self.assertEqual(result["readback"]["query_only"], 1)

    def test_fixed_policy_denial_hides_formal_result(self):
        result = handle_request(catalog("policy_denied"))["data"]
        self.assertEqual(result["entry"]["status"], "published")
        self.assertEqual(result["formal"]["matches"], [])
        self.assertEqual(result["entry"]["sources"][0]["provenance"]["current_usage"]["search_index"]["status"], "prohibited")

    def test_source_change_invalidates_published_evidence(self):
        result = handle_request(catalog("source_changed"))["data"]
        self.assertTrue(result["entry"]["stale"])
        self.assertEqual(result["formal"]["matches"], [])
        self.assertEqual(result["after"]["snapshots"], 2)

    def test_bad_quote_is_native_refusal_without_knowledge_rows(self):
        result = handle_request(catalog("bad_citation"))["data"]
        self.assertEqual(result["state"], "rejected")
        self.assertIn("not present", result["reason"])
        self.assertEqual(result["after"]["entries"], 0)

    def test_limits_unknown_and_strict_json_errors(self):
        for value in [None, {}, request("unknown", {}), catalog(query=""), catalog(query="x" * 201)]:
            self.assertEqual(handle_request(value)["status"], "rejected")
        nested = {}; cursor = nested
        for _ in range(34): cursor["nested"] = {}; cursor = cursor["nested"]
        self.assertEqual(handle_request(nested)["status"], "rejected")
        self.assertEqual(handle_request(request("validate", {"schema": "record.schema.json", "value": [None] * 5001}))["status"], "rejected")
        for raw in [b"", b"{", b"NaN", b"\xff", b"x" * (MAX_BYTES + 1)]:
            self.assertEqual(handle_json(raw)["status"], "rejected")

    def test_cli_stdin_real_result_and_no_arbitrary_options(self):
        command = [sys.executable, "-B", "-X", "utf8", "-m", "ssr_knowledge", "acceptance-native"]
        result = subprocess.run(command, cwd=ROOT, input=json.dumps(fixture("acceptance-native.synthetic.json")), capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["data"]["entry"]["status"], "pending_review")
        self.assertTrue(value["temporary_state_removed"])
        refused = subprocess.run(command + ["--database", "forbidden"], cwd=ROOT, input="{}", capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(refused.returncode, 2)

    def test_legacy_cli_rejection_has_json_exit_one_and_no_traceback(self):
        with tempfile.TemporaryDirectory(prefix="knowledge-legacy-errors-") as directory:
            root = Path(directory)
            invalid = root / "invalid.json"; invalid.write_text('{"bundle_id":"fixture-empty","records":[]}', encoding="utf-8")
            prefix = [sys.executable, "-B", "-X", "utf8", "-m", "ssr_knowledge"]
            for arguments in [["prebuild", "--source", str(invalid), "--state-dir", str(root / "state")],
                              ["query", "--version", "invalid-version", "--kind", "game_item", "--state-dir", str(root / "state")]]:
                result = subprocess.run(prefix + arguments, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(result.stdout)["status"], "error")
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__": unittest.main()
