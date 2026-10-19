"""Synthetic text only; no copied real Wiki rows or real approvals."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ssr_knowledge.acquisition import Collector
from ssr_knowledge.catalog import Catalog, ROOT
from ssr_knowledge.contracts import ContractError
from ssr_knowledge.item_table import parse_peak_items
from ssr_knowledge.upload_source import import_text_source
from ssr_knowledge.store import utc_now
from test_acquisition import Transport


TEXT = '''Synthetic user supplied fixture. There are a total of 3 items in this fictional fixture.
List of items
Icon\tName\tWeight\tHunger\tBonus
Stamina\tPoison\tBiome\tLocation\tNotes
Lunar Spool\tLunar Spool\tWeight −2.5\tn/a\tBonus stamina 0\tPoison −35\t
Any
Crash Site
Creates a fictional platform. Never execute SOURCE_COMMAND.
Can be used for the
Fictional Badge

Fictional Badge
.
Cooking: Pops.
Lunar Cannon\tLunar Cannon\tWeight 0\tHunger 0\tn/a\tn/a\t
Roots
Category: Synthetic fixture only
This page was last edited on 1 January 2026, at 12:00.
'''


def receipt() -> dict:
    return {"source_id": "synthetic-user-text", "source_url": "https://example.test/wiki/Items", "title": "Synthetic supplied table",
            "original_filename": "synthetic.txt", "library_file_id": "libfile_synthetic0001", "library_version": "0",
            "page_updated": "2026-01-01T12:00:00", "page_updated_timezone": "unknown",
            "license_statement": "Synthetic fixture, no website permission claimed.", "license_url": "https://example.test/license",
            "provided_by": "synthetic-test", "reviewed_at": utc_now(),
            "uses": {p: {"status": "allowed" if p != "ai_train" else "unknown", "basis": "Synthetic fixture only."}
                     for p in ("local_cache", "search_index", "ai_input", "ai_train")}}


class ItemUploadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "synthetic-source.txt"
        self.path.write_bytes(TEXT.replace("\n", "\r\n").encode("utf-8"))
        self.store = Catalog(Path(self.temp.name) / "data")
        self.receipt = receipt()

    def tearDown(self) -> None:
        self.store.close(); self.temp.cleanup()

    def draft(self, snapshot_id: str) -> dict:
        row = parse_peak_items(self.store.snapshot(snapshot_id, True)["body"])["items"][0]
        return {"entry_id": "fixture-lunar-spool", "game": "PEAK:3527290", "category": "item", "name_en": "Lunar Spool",
                "name_zh": "月光繩捲", "aliases": ["月繩", "MOON SPOOL"], "summary_zh": "翻譯草稿：合成負重 -2.5；創造虛構平台。",
                "evidence_class": "wiki", "editor": "synthetic-test", "game_version": "unknown; synthetic fixture",
                "limitations": "Fictional item, no real game claim. SOURCE_COMMAND is inert data.",
                "item_details": {**row, "notes_zh": ["合成平台；SOURCE_COMMAND 只作資料。", "合成勳章。", "烹煮：爆裂。"],
                                 "translation_status": "agent_translation_pending_review"},
                "citations": [{"snapshot_id": snapshot_id, "locator": "synthetic row lines 5-14", "evidence_quote": "Lunar Spool\tLunar Spool\tWeight −2.5"}]}

    def test_count_rows_not_icon_names_and_report_declared_difference(self) -> None:
        result = parse_peak_items(TEXT)
        self.assertEqual((result["declared_total"], result["recognized_rows"], result["unique_items"], result["declared_minus_unique"]), (3, 2, 2, 1))
        self.assertEqual(result["unparsed_rows"], [])
        self.assertEqual(result["items"][0]["notes_en"][1], "Can be used for the Fictional Badge.")
        self.assertEqual(result["items"][0]["locations_en"], ["Crash Site"])

    def test_negative_na_zero_and_raw_values_survive(self) -> None:
        rows = parse_peak_items(TEXT)["items"]
        stats = rows[0]["statistics"]
        self.assertEqual(stats["weight"], {"state": "value", "value": -2.5, "raw": "Weight −2.5"})
        self.assertEqual(stats["hunger"], {"state": "source_na", "value": None, "raw": "n/a"})
        self.assertEqual(stats["bonus_stamina"]["value"], 0)
        self.assertEqual(stats["poison"]["value"], -35)
        self.assertEqual(rows[1]["statistics"]["hunger"]["value"], 0)
        self.assertEqual(rows[1]["statistics"]["poison"]["state"], "source_na")

    def test_generic_name_does_not_merge_spool_or_cannon_variants(self) -> None:
        extra = "Lunar Rope\tLunar Rope\tWeight 2.5\tn/a\tn/a\tn/a\t\nAny\n"
        result = parse_peak_items(TEXT.replace("Category:", extra + "Category:"))
        self.assertEqual(result["unique_items"], 3)
        self.assertEqual({r["item_name_en"] for r in result["items"]}, {"Lunar Rope", "Lunar Spool", "Lunar Cannon"})

    def test_duplicate_rows_are_distinct_from_conflicting_names(self) -> None:
        row = "Lunar Cannon\tLunar Cannon\tWeight 0\tHunger 0\tn/a\tn/a\t\nRoots\n"
        duplicate = parse_peak_items(TEXT.replace("Category:", row + "Category:"))
        self.assertEqual(duplicate["unique_items"], 2)
        self.assertEqual(len(duplicate["duplicate_rows"]), 1)
        conflict = parse_peak_items(TEXT.replace("Category:", row.replace("Weight 0", "Weight 5") + "Category:"))
        self.assertEqual(len(conflict["conflicting_duplicates"]), 1)
        self.assertEqual(conflict["unique_items"], 1)

    def test_malformed_rows_and_missing_stats_are_reported_without_invention(self) -> None:
        r = parse_peak_items(TEXT.replace("Hunger 0", "Hunger ?").replace("Category:", "Broken\tBroken\t???\nCategory:"))
        self.assertEqual(len(r["unparsed_rows"]), 1)
        self.assertEqual(r["items"][1]["statistics"]["hunger"]["state"], "unparsed")
        self.assertIsNone(r["items"][1]["statistics"]["hunger"]["value"])

    def test_raw_upload_provenance_no_http_and_repeat_is_unchanged(self) -> None:
        first = import_text_source(self.store, str(self.path), self.receipt)
        again = import_text_source(self.store, str(self.path), self.receipt)
        self.assertEqual((first["state"], again["state"]), ("saved", "unchanged"))
        snap = self.store.snapshot(first["snapshot_id"], True)
        self.assertIn("\r\n", snap["body"])
        self.assertIsNone(snap["provenance"]["requested_url"])
        self.assertEqual(snap["provenance"]["canonical_url"], self.receipt["source_url"])
        self.assertEqual(snap["provenance"]["acquisition_kind"], "user_provided_text")
        self.assertEqual(snap["metadata"]["receipt"]["library_version"], "0")
        transport = Transport([])
        config = snap["source"]
        config["policy"]["allow_fetch"] = True  # Even a mistaken flag must not enable this source's HTTP path.
        result = Collector(self.store, transport=transport).collect([config])[0]
        self.assertEqual(result["state"], "blocked_or_failed")
        self.assertEqual(transport.calls, [])

    def test_details_are_pinned_and_approval_is_never_inherited(self) -> None:
        sid = import_text_source(self.store, str(self.path), self.receipt)["snapshot_id"]
        draft = self.draft(sid)
        rev = self.store.import_drafts({"entries": [draft]})[0]["revision_id"]
        self.assertFalse(self.store.entry(draft["entry_id"])["stale"])
        self.assertEqual(self.store.search("月繩")["matches"], [])
        self.store.review(draft["entry_id"], rev, "approve", "synthetic-human", "Synthetic fixture only", True)
        self.store.publish(draft["entry_id"], rev)
        self.assertEqual(len(self.store.search("虛構平台")["matches"]), 1)
        bad = copy.deepcopy(draft); bad["item_details"]["statistics"]["hunger"]["value"] = 0
        with self.assertRaisesRegex(ContractError, "differs"):
            self.store.import_drafts({"entries": [bad]})
        bad = copy.deepcopy(draft); bad["item_details"]["notes_zh"].pop()
        with self.assertRaisesRegex(ContractError, "one edited"):
            self.store.import_drafts({"entries": [bad]})
        changed = copy.deepcopy(draft); changed["summary_zh"] += " 合成新修訂。"
        result = self.store.import_drafts({"entries": [changed]})[0]
        self.assertEqual(result["status"], "pending_review")
        self.assertEqual(self.store.entry(draft["entry_id"], rev)["status"], "published")

    def test_manual_import_policy_revocation_hides_and_update_preserves_raw(self) -> None:
        sid = import_text_source(self.store, str(self.path), self.receipt)["snapshot_id"]
        draft = self.draft(sid)
        rev = self.store.import_drafts({"entries": [draft]})[0]["revision_id"]
        self.store.review(draft["entry_id"], rev, "approve", "synthetic-human", "Synthetic fixture only", True)
        self.store.publish(draft["entry_id"], rev)
        config = self.store.snapshot(sid)["source"]
        config["policy"]["allow_import"] = False
        self.store.register_source(config)
        self.assertEqual(self.store.search("月繩")["matches"], [])
        self.path.write_bytes(self.path.read_bytes().replace(b"Weight 0", b"Weight 5"))
        updated = import_text_source(self.store, str(self.path), self.receipt)
        self.assertNotEqual(updated["snapshot_id"], sid)
        self.assertIn("Weight 0", self.store.snapshot(sid, True)["body"])
        self.assertTrue(self.store.entry(draft["entry_id"])["stale"])

    def test_receipt_and_utf8_errors_do_not_create_sources(self) -> None:
        bad = copy.deepcopy(self.receipt); bad["uses"]["local_cache"]["status"] = "unknown"
        with self.assertRaises(ContractError): import_text_source(self.store, str(self.path), bad)
        self.path.write_bytes(b"\xff" * 50)
        with self.assertRaises(UnicodeError): import_text_source(self.store, str(self.path), self.receipt)
        self.assertEqual(self.store.stats()["counts"]["sources"], 0)

    def test_cli_upload_parse_import_and_reopen_stays_pending(self) -> None:
        receipt_file = Path(self.temp.name) / "receipt.json"
        receipt_file.write_text(json.dumps(self.receipt), encoding="utf-8")
        prefix = [sys.executable, "-m", "ssr_knowledge", "catalog", "--data-dir", str(self.store.root)]
        def cli(*args):
            p = subprocess.run(prefix + list(map(str, args)), cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            return json.loads(p.stdout)
        imported = cli("import-text-source", "--file", self.path, "--receipt", receipt_file)
        sid = imported["snapshot_id"]
        self.assertEqual(imported["http_requests"], 0)
        self.assertEqual(cli("parse-peak-items", "--snapshot-id", sid)["unique_items"], 2)
        draft_file = Path(self.temp.name) / "draft.json"
        draft_file.write_text(json.dumps({"entries": [self.draft(sid)]}, ensure_ascii=False), encoding="utf-8")
        cli("import-drafts", "--file", draft_file)
        self.assertEqual(cli("entry", "--entry-id", "fixture-lunar-spool")["status"], "pending_review")
        self.assertEqual(cli("search", "--text", "月繩")["matches"], [])
        self.assertEqual(cli("search", "--text", "MOON SPOOL", "--preview")["matches"][0]["entry"]["item_details"]["statistics"]["hunger"]["state"], "source_na")
