from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ssr_knowledge.contracts import ContractError, read_json, validate
from ssr_knowledge.store import LocalKnowledgeStore
from ssr_knowledge.workflows import (
    prepare_gap_supplement,
    prepare_gap_research,
    prepare_prebuild,
    query_published,
    review_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


class KnowledgeWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_root = ROOT / ".test-temp"
        cls.temp_root.mkdir(exist_ok=True)

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir=self.temp_root)
        self.store = LocalKnowledgeStore(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_prebuild_candidate_requires_human_approval_before_publish(self) -> None:
        source = read_json(FIXTURES / "prebuild-source.json")
        candidate = prepare_prebuild(source, self.store)
        self.assertEqual(candidate["origin"], "prebuild")
        self.assertEqual(candidate["status"], "pending_review")
        with self.assertRaisesRegex(ContractError, "approved candidate"):
            self.store.publish(candidate["candidate_id"], "v0.1.0")

        reviewed = review_candidate(candidate["candidate_id"], "approve", "human", "reviewed", self.store)
        self.assertEqual(reviewed["status"], "approved")
        published = self.store.publish(candidate["candidate_id"], "v0.1.0")
        self.assertEqual(published["version"], "v0.1.0")
        self.assertEqual(published["publication_status"], "published")
        self.assertEqual(len(published["records_sha256"]), 64)
        result = query_published("v0.1.0", "game_item", "\u661f\u7802", self.store)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(set(result), {"status", "materials", "sources"})
        self.assertEqual(result["materials"][0]["record_id"], "fixture-item-stardust")
        self.assertTrue(result["sources"][0]["locator"].startswith("fixture://"))

    def test_gap_supplement_is_a_separate_candidate_and_requires_review(self) -> None:
        gaps = read_json(FIXTURES / "gap-export.json")
        records = read_json(FIXTURES / "gap-records.json")
        packet = prepare_gap_research(gaps, records, self.store)
        self.assertEqual(packet["status"], "complete")
        self.assertEqual(packet["gaps"][0]["run_id"], gaps["gaps"][0]["run_id"])
        self.assertEqual(packet["records"][0]["gap_id"], gaps["gaps"][0]["gap_id"])
        self.assertTrue(self.store.research_path(packet["research_id"]).exists())
        self.assertFalse(self.store.candidate_dir.exists())

        reloaded_store = LocalKnowledgeStore(self.temp.name)
        candidate = prepare_gap_supplement(packet["research_id"], reloaded_store)
        self.assertEqual(candidate["origin"], "gap_supplement")
        self.assertEqual(candidate["status"], "pending_review")
        self.assertEqual(candidate["research_id"], packet["research_id"])
        self.assertEqual(candidate["records"][0]["gap_id"], gaps["gaps"][0]["gap_id"])

        incomplete = {"records": []}
        with self.assertRaisesRegex(ContractError, "cover each imported gap"):
            prepare_gap_research(gaps, incomplete, self.store)

        review_candidate(candidate["candidate_id"], "approve", "human", "source checked", self.store)
        self.store.publish(candidate["candidate_id"], "v0.2.0")
        result = query_published("v0.2.0", "game_item", "\u661f\u7802", self.store)
        self.assertEqual(result["status"], "ok")

    def test_local_schemas_validate_all_fixtures_and_tool_settings_are_static(self) -> None:
        validate(read_json(FIXTURES / "prebuild-source.json"), "prebuild-source.schema.json")
        validate(read_json(FIXTURES / "gap-export.json"), "gap-export.schema.json")
        validate(read_json(FIXTURES / "gap-records.json"), "supplement-records.schema.json")
        validate(read_json(FIXTURES / "research-packet.json"), "research-packet.schema.json")
        tools = read_json(FIXTURES / "tool-config.json")
        validate(tools, "tool-config.schema.json")
        self.assertEqual(tools["mode"], "documented_not_connected")
        self.assertFalse(tools["network_enabled"])
        self.assertTrue(all(item["state"] == "documented_not_connected" for item in tools["tools"]))
        self.assertEqual(
            {tool["adapter_kind"] for tool in tools["tools"]},
            {"source", "http_api", "mcp", "manual_import"},
        )

        saved = self.store.save_tool_config(tools)
        reloaded_store = LocalKnowledgeStore(self.temp.name)
        self.assertEqual(reloaded_store.load_tool_config("v1.0.0"), saved)
        with self.assertRaisesRegex(ContractError, "already exists"):
            self.store.save_tool_config(tools)

        invalid = json.loads(json.dumps(read_json(FIXTURES / "gap-export.json")))
        invalid["gaps"][0].pop("message_id")
        with self.assertRaisesRegex(ContractError, "message_id: required"):
            validate(invalid, "gap-export.schema.json")

    def test_rejected_candidate_cannot_be_published_and_versions_are_immutable(self) -> None:
        candidate = prepare_prebuild(read_json(FIXTURES / "prebuild-source.json"), self.store)
        review_candidate(candidate["candidate_id"], "reject", "human", "source needs checking", self.store)
        with self.assertRaisesRegex(ContractError, "approved candidate"):
            self.store.publish(candidate["candidate_id"], "v0.1.0")

        approved = prepare_prebuild(read_json(FIXTURES / "prebuild-source.json"), self.store)
        review_candidate(approved["candidate_id"], "approve", "human", "ok", self.store)
        self.store.publish(approved["candidate_id"], "v0.1.0")
        second = prepare_prebuild(read_json(FIXTURES / "prebuild-source.json"), self.store)
        review_candidate(second["candidate_id"], "approve", "human", "ok", self.store)
        with self.assertRaisesRegex(ContractError, "already exists"):
            self.store.publish(second["candidate_id"], "v0.1.0")

    def test_published_records_digest_rejects_tampering(self) -> None:
        candidate = prepare_prebuild(read_json(FIXTURES / "prebuild-source.json"), self.store)
        review_candidate(candidate["candidate_id"], "approve", "human", "ok", self.store)
        self.store.publish(candidate["candidate_id"], "v0.3.0")
        bundle_path = self.store.published_dir / "v0.3.0.json"
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        bundle["records"][0]["summary"] += " altered"
        bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")

        with self.assertRaisesRegex(ContractError, "digest mismatch"):
            self.store.read_published("v0.3.0")

    def test_blank_research_evidence_is_rejected(self) -> None:
        gaps = read_json(FIXTURES / "gap-export.json")
        records = read_json(FIXTURES / "gap-records.json")
        records["records"][0]["summary"] = "  "

        with self.assertRaisesRegex(ContractError, "summary must not be empty"):
            prepare_gap_research(gaps, records, self.store)


if __name__ == "__main__":
    unittest.main()
