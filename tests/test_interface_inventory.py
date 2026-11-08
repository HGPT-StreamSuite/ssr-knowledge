"""Version-bound interface examples and actual receipts; no cross-repo imports."""
import hashlib
import json
from pathlib import Path
import unittest

from ssr_knowledge.acceptance_native import FORMAT, OPERATIONS, SCHEMAS, SCENARIOS
from ssr_knowledge.contracts import _validate

ROOT = Path(__file__).resolve().parents[1]
def read(path): return json.loads(path.read_text(encoding="utf-8"))


class InterfaceInventoryTests(unittest.TestCase):
    def test_inventory_matches_cli_and_runtime_without_writing(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        from build_interface_inventory import products
        for name, expected in products().items():
            self.assertEqual(read(ROOT / "interfaces" / name), expected)

    def test_fixed_request_contract_covers_only_native_operations(self):
        schema = read(ROOT / "interfaces" / "acceptance-native.request.schema.json")
        branches = {item["properties"]["operation"]["enum"][0]: item for item in schema["oneOf"]}
        self.assertEqual(set(branches), OPERATIONS)
        self.assertEqual(set(branches["validate"]["properties"]["input"]["properties"]["schema"]["enum"]), SCHEMAS)
        self.assertEqual(set(branches["catalog_check"]["properties"]["input"]["properties"]["scenario"]["enum"]), SCENARIOS)
        sample = read(ROOT / "fixtures" / "acceptance-native.synthetic.json")
        self.assertEqual(sample["format"], FORMAT)
        self.assertEqual(_validate(sample, branches[sample["operation"]], "$"), [])
        sample["database"] = "forbidden"
        self.assertTrue(_validate(sample, branches[sample["operation"]], "$"))

    def test_actual_receipts_bind_bytes_runtime_and_response_contract(self):
        manifest = read(ROOT / "interfaces" / "manifest.json")
        schema = read(ROOT / "interfaces" / "acceptance-native.response.schema.json")
        receipts = list((ROOT / "interfaces" / "receipts").glob("*.json"))
        self.assertEqual(len(receipts), 3)
        for path in receipts:
            receipt = read(path)
            self.assertEqual(receipt["runtime_source_sha256"], manifest["runtime_source_sha256"])
            self.assertEqual(hashlib.sha256(receipt["request_utf8"].encode()).hexdigest(), receipt["input_sha256"])
            self.assertEqual(json.loads(receipt["request_utf8"]), receipt["request"])
            self.assertEqual(_validate(receipt["response"], schema, "$"), [])
            self.assertEqual(receipt["exit_code"], 0)
            self.assertTrue(receipt["response"]["temporary_state_removed"])

    def test_published_receipt_is_not_an_ai_permission_grant(self):
        result = read(ROOT / "interfaces" / "receipts" / "published.json")["response"]["data"]
        self.assertEqual(result["formal"]["scope"], "published")
        self.assertEqual(result["formal"]["status"], "ok")
        for source in result["entry"]["sources"]:
            for scope in ("snapshot_usage", "current_usage"):
                self.assertEqual(source["provenance"][scope]["ai_input"]["status"], "unknown")

    def test_catalog_payload_is_not_silently_claimed_to_be_shared_record(self):
        manifest = read(ROOT / "interfaces" / "manifest.json")
        self.assertFalse(manifest["shared_record_bridge"]["connected"])
        result = read(ROOT / "interfaces" / "receipts" / "published.json")["response"]["data"]
        self.assertNotIn("access_scope", result["entry"]["entry"])
        self.assertFalse(manifest["native"]["web_transport_connected"])
