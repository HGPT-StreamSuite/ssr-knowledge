"""Synthetic connector/name files; no mod is installed or executed."""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ssr_knowledge.acquisition import Collector
from ssr_knowledge.catalog import Catalog, ROOT, digest
from ssr_knowledge.community_names import match_community_names
from ssr_knowledge.contracts import ContractError
from ssr_knowledge.name_reference import import_name_reference
from ssr_knowledge.store import utc_now
from ssr_knowledge.upload_source import import_text_source
from test_acquisition import Transport
from test_item_upload import TEXT, receipt as upload_receipt
from test_names import annotated
from test_catalog import seed


MOD = "# Synthetic labels only\nLunar Spool=月光繩捲\nLUNAR SPOOL=月光繩捲\nLunar Cannon=月光繩炮\nScroll=卷軸\nSCROLL=捲動\njackpack=噴射背包\nENERGY EELIXIR=虛構飲品\n"


def receipt(raw):
    return {"source_id": "synthetic-community", "source_url": "https://example.test/blob/" + "a" * 40 + "/Item.txt",
            "title": "Synthetic mod name file", "locale": "zh-TW", "evidence_kind": "community_mod", "acquisition_method": "github_connector",
            "version": "synthetic-v1; not a real PEAK version", "upstream_commit": "a" * 40,
            "upstream_blob_sha": hashlib.sha1(("blob " + str(len(raw)) + "\0").encode() + raw).hexdigest(), "raw_sha256": digest(raw),
            "license_statement": "Synthetic fixture only; no third-party data.", "license_url": "https://example.test/LICENSE", "reviewed_at": utc_now(),
            "uses": {p: {"status": "allowed" if p in {"local_cache", "search_index"} else "unknown", "basis": "Synthetic fixture only."}
                     for p in ("local_cache", "search_index", "ai_input", "ai_train")}}


class NameReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.store = Catalog(self.root / "data")
        self.file = self.root / "mod.txt"; self.file.write_bytes(MOD.encode())
        self.receipt = receipt(self.file.read_bytes())

    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def test_exact_match_preserves_conflicts_duplicates_and_rejects_typo_guesses(self):
        parsed = match_community_names(MOD, ["Lunar Spool", "Lunar Cannon", "Scroll", "Jetpack", "Energy Elixir"])
        self.assertEqual((parsed["key_value_rows"], parsed["unique_casefold_keys"], parsed["duplicate_pairs"]), (7, 5, 1))
        self.assertEqual((parsed["matched_items"], parsed["unmatched_names"]), (3, ["Jetpack", "Energy Elixir"]))
        self.assertEqual(parsed["matched_conflicts"], ["Scroll"])
        self.assertEqual(parsed["matches"][2]["aliases"], ["卷軸", "捲動"])
        self.assertEqual(len(parsed["matches"][0]["rows"]), 2)
        with self.assertRaisesRegex(ContractError, "ambiguous"):
            match_community_names(MOD, ["Scroll", "SCROLL"])
        malformed = match_community_names(MOD + "bad row\n=empty\n", ["Scroll"])
        self.assertEqual(len(malformed["unparsed_rows"]), 2)

    def test_reference_import_exact_bytes_sha_license_repeat_and_no_http(self):
        first = import_name_reference(self.store, str(self.file), self.receipt)
        repeated = import_name_reference(self.store, str(self.file), self.receipt)
        self.assertEqual((first["state"], repeated["state"]), ("saved", "unchanged"))
        snapshot = self.store.snapshot(first["snapshot_id"], True)
        self.assertEqual(snapshot["body"].encode(), self.file.read_bytes())
        self.assertEqual(snapshot["metadata"]["receipt"]["upstream_commit"], "a" * 40)
        self.assertEqual(snapshot["metadata"]["name_evidence"], {"kind": "community_mod", "locale": "zh-TW"})
        self.assertIsNone(snapshot["provenance"]["requested_url"])
        config = snapshot["source"]; config["policy"]["allow_fetch"] = True
        transport = Transport([])
        self.assertEqual(Collector(self.store, transport=transport).collect([config])[0]["state"], "blocked_or_failed")
        self.assertEqual(transport.calls, [])
        bad = copy.deepcopy(self.receipt); bad["upstream_blob_sha"] = "b" * 40
        with self.assertRaisesRegex(ContractError, "blob SHA"):
            import_name_reference(self.store, str(self.file), bad)
        bad = copy.deepcopy(self.receipt); bad["evidence_kind"] = "game_ui"
        with self.assertRaisesRegex(ContractError, "not game UI"):
            import_name_reference(self.store, str(self.file), bad)

    def test_community_alias_can_overlap_other_names_without_official_promotion(self):
        _, draft = seed(self.store)
        data = MOD + "Lunar Rope=月光繩\n"
        self.file.write_bytes(data.encode()); r = receipt(self.file.read_bytes())
        sid = import_name_reference(self.store, str(self.file), r)["snapshot_id"]
        d = annotated(draft); d["evidence_class"] = "wiki"; d["aliases"].append("月光繩")
        d["citations"].append({"snapshot_id": sid, "locator": "synthetic line", "evidence_quote": "Lunar Rope=月光繩"})
        d["names"]["records"].append({"text": "月光繩", "locale": "zh-TW", "role": "alias", "status": "community_mod_alias", "citation": 1, "basis": "Synthetic mod name; no game UI verification."})
        self.store.import_drafts({"entries": [d]})
        matches = self.store.search("月光繩", preview=True, names_only=True)["matches"][0]["name_matches"]
        self.assertEqual({m["status"] for m in matches}, {"provisional_translation", "community_mod_alias"})
        for status in ("game_ui_verified", "official_marketing_alias"):
            bad = copy.deepcopy(d); bad["names"]["records"][-1]["status"] = status
            with self.assertRaisesRegex(ContractError, "evidence scope"):
                self.store.import_drafts({"entries": [bad]})

    def test_cli_reference_import_and_fixed_snapshot_matching_reopen(self):
        self.file.write_bytes(MOD.encode())
        rpath = self.root / "receipt.json"; rpath.write_text(json.dumps(self.receipt), encoding="utf-8")
        upload = self.root / "items.txt"; upload.write_text(TEXT, encoding="utf-8")
        items = import_text_source(self.store, str(upload), upload_receipt())["snapshot_id"]
        prefix = [sys.executable, "-m", "ssr_knowledge", "catalog", "--data-dir", str(self.store.root)]
        def cli(*args):
            p = subprocess.run(prefix + list(map(str, args)), cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self.assertEqual(p.returncode, 0, p.stderr)
            return json.loads(p.stdout)
        imported = cli("import-name-reference", "--file", self.file, "--receipt", rpath)
        report = cli("match-community-names", "--snapshot-id", imported["snapshot_id"], "--items-snapshot-id", items)
        self.assertEqual((report["matched_items"], report["unmatched_items"]), (2, 0))
