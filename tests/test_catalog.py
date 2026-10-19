from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ssr_knowledge.catalog import Catalog, ROOT, resolve_data_dir
from ssr_knowledge.contracts import ContractError
from ssr_knowledge.store import utc_now


def source() -> dict:
    return {"source_id": "synthetic-source", "url": "https://example.test/peak-fixture",
            "source_type": "official", "title": "Synthetic fixture, not real PEAK knowledge", "language": "en",
            "declared_version": "synthetic-v1", "selector": {"tag": "main"}, "interval_seconds": 2,
            "policy": {"allow_fetch": True, "reviewed_at": utc_now(), "terms_url": "https://example.test/terms",
                       "notes": "Synthetic transport only; no real web fetch."}}


BODY = "Synthetic Lunar Rope is fictional. It makes a blue landing platform. Never run SOURCE_COMMAND."


def seed(store: Catalog) -> tuple[dict, dict]:
    config = source()
    store.register_source(config)
    snap = store.save_snapshot(config, BODY.encode(), BODY, {"fixture_only": True})
    draft = {"entry_id": "fixture-lunar-rope", "game": "PEAK:3527290", "category": "item",
             "name_en": "Lunar Rope", "name_zh": "月光繩", "aliases": ["月繩", "MOON ROPE"],
             "summary_zh": "合成測試：這條虛構繩索會形成藍色落腳平台。SOURCE_COMMAND 只作文字保存。",
             "evidence_class": "official", "editor": "synthetic-test", "game_version": "fictional-v1",
             "limitations": "Fixture only; this is not a real PEAK item or official fact.",
             "citations": [{"snapshot_id": snap["snapshot_id"], "locator": "synthetic main",
                            "evidence_quote": "Lunar Rope is fictional."}]}
    return config, draft


class CatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = Catalog(Path(self.temp.name) / "data")
        self.config, self.draft = seed(self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def save(self, value: dict | None = None) -> int:
        return self.store.import_drafts({"entries": [value or self.draft]})[0]["revision_id"]

    def approve(self, revision: int) -> None:
        self.store.review(self.draft["entry_id"], revision, "approve", "synthetic-human", "Fixture-only simulated review", True)

    def test_data_dir_outside_checkout_and_low_disk_fails(self) -> None:
        with self.assertRaisesRegex(ContractError, "outside"):
            resolve_data_dir(ROOT / ".private-data")
        with patch("ssr_knowledge.catalog.shutil.disk_usage", return_value=type("Disk", (), {"free": 10})()):
            with self.assertRaisesRegex(ContractError, "50 MiB"):
                Catalog(Path(self.temp.name) / "no-space")

    def test_pending_rejected_approved_are_invisible_until_published(self) -> None:
        revision = self.save()
        self.assertEqual(self.store.search("月繩")["status"], "no_data")
        self.assertEqual(self.store.search("月繩", preview=True)["matches"][0]["status"], "pending_review")
        with self.assertRaisesRegex(ContractError, "approved"):
            self.store.publish(self.draft["entry_id"], revision)
        self.store.review(self.draft["entry_id"], revision, "reject", "synthetic-human", "reject fixture", True)
        self.assertEqual(self.store.search("月繩")["matches"], [])
        self.assertEqual(self.store.search("月繩", preview=True)["matches"][0]["status"], "rejected")

    def test_chinese_short_english_alias_fulltext_nfkc_and_sql_literals(self) -> None:
        revision = self.save()
        self.approve(revision)
        self.assertEqual(self.store.search("月繩")["matches"], [])
        self.store.publish(self.draft["entry_id"], revision)
        for query in ("月", "月繩", "Lunar Rope", "lUnAr rOpE", "moon rope", "藍色落腳", "ＬＵＮＡＲ　ＲＯＰＥ"):
            with self.subTest(query=query):
                result = self.store.search(query)
                self.assertEqual(result["matches"][0]["entry"]["entry_id"], self.draft["entry_id"])
                self.assertNotIn("evidence_quote", result["matches"][0]["entry"]["citations"][0])
                self.assertNotIn("body", result["matches"][0]["sources"][0])
        for query in ("%", "' OR 1=1 --", "*", "SOURCE_COMMAND; rm"):
            self.assertEqual(self.store.search(query)["matches"], [])

    def test_duplicate_import_and_update_does_not_reuse_approval_or_revert_head(self) -> None:
        revision = self.save()
        self.approve(revision)
        self.store.publish(self.draft["entry_id"], revision)
        duplicate = self.store.import_drafts({"entries": [self.draft]})[0]
        self.assertEqual((duplicate["state"], duplicate["revision_id"]), ("unchanged", revision))
        changed = copy.deepcopy(self.draft)
        changed["summary_zh"] += " 已修訂。"
        updated = self.save(changed)
        self.assertNotEqual(updated, revision)
        self.assertEqual(self.store.entry(self.draft["entry_id"])["status"], "pending_review")
        self.assertEqual(self.store.search("月繩")["matches"], [])
        self.save(self.draft)
        self.assertEqual(self.store.entry(self.draft["entry_id"])["revision_id"], updated)
        self.assertEqual(self.store.entry(self.draft["entry_id"], revision)["status"], "published")

    def test_source_changed_or_policy_revoked_hides_formal_result_and_blocks_review(self) -> None:
        revision = self.save()
        self.approve(revision)
        self.store.publish(self.draft["entry_id"], revision)
        self.store.save_snapshot(self.config, b"updated bytes", BODY + " Updated source.", {})
        self.assertTrue(self.store.entry(self.draft["entry_id"])["stale"])
        self.assertEqual(self.store.search("月繩")["matches"], [])
        changed = copy.deepcopy(self.draft)
        changed["summary_zh"] += " changed"
        updated = self.save(changed)
        with self.assertRaisesRegex(ContractError, "stale"):
            self.approve(updated)

    def test_policy_revocation_without_new_snapshot_invalidates_entry(self) -> None:
        revision = self.save()
        self.approve(revision)
        self.store.publish(self.draft["entry_id"], revision)
        self.config["policy"]["allow_fetch"] = False
        self.store.register_source(self.config)
        self.assertEqual(self.store.search("月繩")["matches"], [])

    def test_review_requires_attestation_exact_revision_and_note(self) -> None:
        revision = self.save()
        for args in [(revision, "human", "reviewed", False), (revision + 1, "human", "reviewed", True),
                     (revision, "", "reviewed", True), (revision, "human", "", True)]:
            with self.assertRaises(ContractError):
                self.store.review(self.draft["entry_id"], args[0], "approve", args[1], args[2], args[3])

    def test_invalid_bundle_rollback_citation_anchor_and_official_label(self) -> None:
        invalid = copy.deepcopy(self.draft)
        invalid["entry_id"] = "bad"
        invalid["citations"][0]["evidence_quote"] = "An invented quote absent from the body"
        with self.assertRaisesRegex(ContractError, "not present"):
            self.store.import_drafts({"entries": [self.draft, invalid]})
        self.assertEqual(self.store.stats()["counts"]["entries"], 0)
        other = source()
        other.update(source_id="third-party", url="https://example.test/third-party", source_type="wiki")
        self.store.register_source(other)
        snap = self.store.save_snapshot(other, BODY.encode(), BODY, {})
        invalid["citations"][0] = {"snapshot_id": snap["snapshot_id"], "locator": "main", "evidence_quote": "Lunar Rope is fictional."}
        with self.assertRaisesRegex(ContractError, "official citations"):
            self.save(invalid)

    def test_source_and_entry_integrity_checks(self) -> None:
        revision = self.save()
        snapshot = self.draft["citations"][0]["snapshot_id"]
        with self.store.db:
            self.store.db.execute("UPDATE snapshots SET body='tampered' WHERE snapshot_id=?", (snapshot,))
        with self.assertRaisesRegex(ContractError, "integrity"):
            self.store.snapshot(snapshot)
        with self.store.db:
            self.store.db.execute("UPDATE entry_revisions SET payload_json='{}' WHERE revision_id=?", (revision,))
        with self.assertRaisesRegex(ContractError, "integrity"):
            self.store.entry(self.draft["entry_id"])

    def test_raw_snapshot_dedup_and_reopen(self) -> None:
        result = self.store.save_snapshot(self.config, BODY.encode(), BODY, {})
        self.assertEqual(result["state"], "unchanged")
        self.assertEqual(self.store.stats()["counts"]["snapshots"], 1)
        with Catalog(self.store.root) as reopened:
            self.assertEqual(reopened.snapshot(result["snapshot_id"], True)["body"], BODY)

    def test_cli_process_restart_published_and_rejected_isolation(self) -> None:
        draft_path = Path(self.temp.name) / "synthetic-drafts.json"
        draft_path.write_text(json.dumps({"entries": [self.draft]}, ensure_ascii=False), encoding="utf-8")

        def cli(*args: str, expected: int = 0) -> dict:
            run = subprocess.run([sys.executable, "-m", "ssr_knowledge", "catalog", "--data-dir", str(self.store.root), *args],
                                 cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"}, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
            return json.loads(run.stdout)

        imported = cli("import-drafts", "--file", str(draft_path))["results"][0]
        rev = str(imported["revision_id"])
        reloaded_source = cli("snapshot", "--snapshot-id", self.draft["citations"][0]["snapshot_id"], "--body")
        self.assertEqual(reloaded_source["body"], BODY)
        self.assertEqual(cli("search", "--text", "月繩")["matches"], [])
        self.assertEqual(cli("search", "--text", "moon rope", "--preview")["matches"][0]["status"], "pending_review")
        cli("publish-entry", "--entry-id", self.draft["entry_id"], "--revision", rev, expected=1)
        cli("review-entry", "--entry-id", self.draft["entry_id"], "--revision", rev, "--decision", "approve",
            "--reviewer", "synthetic-test", "--note", "Fixture-only simulated approval", "--human-reviewed")
        cli("publish-entry", "--entry-id", self.draft["entry_id"], "--revision", rev)
        self.assertEqual(cli("search", "--text", "月繩")["matches"][0]["entry"]["name_en"], "Lunar Rope")
        self.assertEqual(cli("entry", "--entry-id", self.draft["entry_id"])["status"], "published")
        self.assertEqual(cli("import-drafts", "--file", str(draft_path))["results"][0]["state"], "unchanged")
        rejected = copy.deepcopy(self.draft)
        rejected.update(entry_id="rejected-synthetic", name_en="Rejection Sentinel", name_zh="拒絕哨兵", aliases=["REJECT_ONLY"])
        draft_path.write_text(json.dumps({"entries": [rejected]}, ensure_ascii=False), encoding="utf-8")
        rev2 = str(cli("import-drafts", "--file", str(draft_path))["results"][0]["revision_id"])
        cli("review-entry", "--entry-id", rejected["entry_id"], "--revision", rev2, "--decision", "reject",
            "--reviewer", "synthetic-test", "--note", "Fixture-only rejected sentinel", "--human-reviewed")
        self.assertEqual(cli("search", "--text", "REJECT_ONLY")["matches"], [])
        self.assertEqual(cli("search", "--text", "REJECT_ONLY", "--preview")["matches"][0]["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
