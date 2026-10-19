"""Synthetic UnityFS/CSV data only; no real game resources or names."""
import copy
import io
import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path

from ssr_knowledge.catalog import Catalog, digest
from ssr_knowledge.contracts import ContractError
from ssr_knowledge.game_extraction import import_game_text, extract_installed_text
from ssr_knowledge.game_localization import parse_game_csv, pair_game_names, pair_saved_game_names
from ssr_knowledge.unity_stream import BoundedUnityFS, BundleWindow
from ssr_knowledge.acquisition import Collector
from ssr_knowledge.store import utc_now
from test_acquisition import Transport
from test_catalog import seed
from test_names import annotated

CSV = "CURRENT_LANGUAGE,English,简体中文,繁體中文,ENDLINE\r\nNAME_LUNAR ROPE,LUNAR ROPE,月光绳索,月光繩索,ENDLINE\r\nNAME_LUNAR ROPE SPOOL,LUNAR ROPE SPOOL,月光绳卷,月光繩捲,ENDLINE\r\nNAME_LUNAR ROPE CANNON,LUNAR ROPE CANNON,月光绳炮,月光繩炮,ENDLINE\r\nSCROLL,LUNAR ROPE,滚动,捲動,ENDLINE\r\n"

def receipt(raw):
    parsed = parse_game_csv(raw.decode())
    return {"schema_version": 1, "game": "PEAK:3527290", "game_version": "synthetic-v1", "steam_build_id": "123", "extracted_at": utc_now(),
            "raw_sha256": digest(raw), "bundle_sha256_before": "a" * 64, "bundle_sha256_after": "a" * 64,
            "header": parsed["header"], "columns": parsed["columns"], "asset": "resources.assets", "text_asset_name": "Localized_Text", "path_id": 7}

def bundle_bytes(data=b"synthetic names only", flags=0x240, mode=0):
    if mode:
        import lz4.block
        compressed = lz4.block.compress(data, store_size=False)
    else: compressed = data
    index = b"\0" * 16 + struct.pack(">I", 1) + struct.pack(">IIH", len(data), len(compressed), mode)
    index += struct.pack(">IQQI", 1, 0, len(data), 4) + b"synthetic.assets\0"
    prefix = b"UnityFS\0" + struct.pack(">I", 8) + b"5.x.x\0" + b"6000.0.synthetic\0"
    header_len = ((len(prefix) + 20 + 15) // 16) * 16
    start = ((header_len + len(index) + 15) // 16) * 16
    header = prefix + struct.pack(">QIII", start + len(compressed), len(index), len(index), flags)
    return header.ljust(header_len, b"\0") + index + b"\0" * (start - header_len - len(index)) + compressed

@unittest.skipUnless(importlib.util.find_spec("UnityPy"), "optional extraction group required; core catalog remains dependency-free")
class GameNameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.store = Catalog(self.root / "data")
        self.file = self.root / "synthetic.csv"; self.file.write_bytes(CSV.encode())
        self.receipt = receipt(self.file.read_bytes())
        self.saved = import_game_text(self.store, str(self.file), self.receipt)["results"]

    def tearDown(self): self.store.close(); self.temp.cleanup()

    def official_draft(self):
        _, base = seed(self.store); d = annotated(base)
        en_index = len(d["citations"])
        d["citations"].append({"snapshot_id": self.saved["en"]["snapshot_id"], "locator": "synthetic NAME_LUNAR ROPE English column", "evidence_quote": "LUNAR ROPE"})
        tw_index = len(d["citations"])
        d["citations"].append({"snapshot_id": self.saved["zh-TW"]["snapshot_id"], "locator": "synthetic Traditional column, not Simplified", "evidence_quote": "月光繩索"})
        d["name_zh"] = "月光繩索"
        d["names"]["records"][1] = {"text": "月光繩索", "locale": "zh-TW", "role": "chinese", "status": "game_ui_verified", "citation": tw_index, "game_key": "NAME_LUNAR ROPE", "basis": "Synthetic official text, not real game data."}
        for text, locale, status, cite in [("LUNAR ROPE", "en", "game_ui_verified", en_index), ("月光繩", "zh-TW", "provisional_alias", None)]:
            d["aliases"].append(text)
            record = {"text": text, "locale": locale, "role": "alias", "status": status, "citation": cite, "basis": "Synthetic preferred/old provisional label."}
            if cite is not None: record["game_key"] = "NAME_LUNAR ROPE"
            d["names"]["records"].append(record)
        d["names"]["preferred"] = {"en": "LUNAR ROPE", "zh-TW": "月光繩索"}
        return d

    def test_column_labels_not_positions_and_no_simplified_substitution(self):
        parsed = parse_game_csv(CSV)
        self.assertEqual(parsed["columns"], {"en": 1, "zh-TW": 3, "zh-CN": 2})
        row = pair_game_names(parsed, ["Lunar Rope"])["matches"][0]
        self.assertEqual((row["zh-TW"], row["zh-CN"]), ("月光繩索", "月光绳索"))
        bad = copy.deepcopy(self.receipt); bad["columns"]["zh-TW"] = 2
        with self.assertRaisesRegex(ContractError, "column"):
            import_game_text(self.store, str(self.file), bad)
        for body in (CSV.replace("繁體中文", "简体中文"), CSV.replace("ENDLINE\r\nNAME_", "BROKEN\r\nNAME_", 1), CSV.replace("月光繩索,ENDLINE", "月光繩索,extra,ENDLINE")):
            with self.subTest(body=body[:40]), self.assertRaises(ContractError): parse_game_csv(body)

    def test_namespace_duplicate_conflicts_and_no_fuzzy_variant_mapping(self):
        identical = CSV + "NAME_LUNAR ROPE,LUNAR ROPE,月光绳索,月光繩索,ENDLINE\r\n"
        parsed = parse_game_csv(identical)
        self.assertEqual(len(parsed["items"]), 3)
        self.assertEqual(parsed["items"][0]["csv_records"], [2, 6])
        result = pair_game_names(parsed, ["Lunar Rope", "Lunar Rope (Poisonous)", "Lunar-Rope"])
        self.assertEqual((result["matched_items"], result["unmatched_items"]), (1, 2))
        conflict = parse_game_csv(CSV + "NAME_LUNAR ROPE,LUNAR ROPE,别名,不同名稱,ENDLINE\r\n")
        result = pair_game_names(conflict, ["Lunar Rope"])
        self.assertEqual(result["unresolved"][0]["reason"], "conflicting_game_key")

    def test_projection_import_repeat_no_http_and_same_extraction_pairing(self):
        repeat = import_game_text(self.store, str(self.file), self.receipt)
        self.assertTrue(all(r["state"] == "unchanged" for r in repeat["results"].values()))
        later = copy.deepcopy(self.receipt); later["extracted_at"] = "2026-10-20T00:00:00+00:00"
        self.assertTrue(all(r["state"] == "unchanged" for r in import_game_text(self.store, str(self.file), later)["results"].values()))
        en, tw = (self.store.snapshot(self.saved[l]["snapshot_id"], True) for l in ("en", "zh-TW"))
        result = pair_saved_game_names(en, tw, ["Lunar Rope", "Lunar Rope Spool", "Lunar Rope Cannon"])
        self.assertEqual(result["matched_items"], 3)
        bad = copy.deepcopy(tw); bad["source"]["language"] = "zh-CN"
        with self.assertRaises(ContractError): pair_saved_game_names(en, bad, ["Lunar Rope"])
        bad = copy.deepcopy(tw); bad["metadata"]["receipt"]["steam_build_id"] = "999"
        with self.assertRaises(ContractError): pair_saved_game_names(en, bad, ["Lunar Rope"])
        config = en["source"]; config["policy"]["allow_fetch"] = True; transport = Transport([])
        self.assertEqual(Collector(self.store, transport=transport).collect([config])[0]["state"], "blocked_or_failed")
        self.assertEqual(transport.calls, [])

    def test_preferred_official_names_keep_canonical_id_and_old_translation_alias(self):
        d = self.official_draft(); rev = self.store.import_drafts({"entries": [d]})[0]["revision_id"]
        item = self.store.entry(d["entry_id"])
        self.assertEqual(item["entry"]["name_en"], "Lunar Rope")
        self.assertEqual(item["display_names"]["en"], {"text": "LUNAR ROPE", "status": "game_ui_verified"})
        self.assertEqual(item["display_names"]["zh-TW"]["text"], "月光繩索")
        for query in ("Lunar Rope", "LUNARROPE", "月光繩索", "月光繩", "月繩"):
            result = self.store.search(query, preview=True, names_only=True)
            self.assertEqual(result["name_resolution"]["entry_ids"], [d["entry_id"]])
            self.assertEqual(self.store.search(query, names_only=True)["matches"], [])
        self.store.review(d["entry_id"], rev, "approve", "synthetic-human", "Fixture only", True); self.store.publish(d["entry_id"], rev)
        changed = copy.deepcopy(d); changed["limitations"] += " New synthetic revision."
        self.assertEqual(self.store.import_drafts({"entries": [changed]})[0]["status"], "pending_review")
        self.assertEqual(self.store.entry(d["entry_id"], rev)["status"], "published")

    def test_wrong_game_key_or_simplified_value_cannot_be_verified(self):
        d = self.official_draft()
        for key, value in (("game_key", "NAME_LUNAR ROPE SPOOL"), ("text", "月光绳索")):
            bad = copy.deepcopy(d); bad["names"]["records"][1][key] = value
            if key == "text": bad["name_zh"] = value
            with self.subTest(key=key), self.assertRaises(ContractError): self.store.import_drafts({"entries": [bad]})
        bad = copy.deepcopy(d); bad["names"]["preferred"]["en"] = "MOON ROPE"
        with self.assertRaisesRegex(ContractError, "unique verified"):
            self.store.import_drafts({"entries": [bad]})

    def test_official_alias_collision_reports_ambiguity_without_selecting_one(self):
        d = self.official_draft(); other = copy.deepcopy(d); other["entry_id"] = "fixture-alternate-entity"
        self.store.import_drafts({"entries": [d, other]})
        result = self.store.search("月光繩索", preview=True, names_only=True, limit=1)
        self.assertEqual(result["name_resolution"]["status"], "ambiguous")
        self.assertEqual(len(result["name_resolution"]["entry_ids"]), 2)
        self.assertEqual(self.store.search("月光繩索", names_only=True)["name_resolution"]["entry_ids"], [])

    def test_stream_cache_bounds_seeks_lz4_and_encryption_stops(self):
        for mode in (0, 2):
            file = self.root / (str(mode) + ".unity3d"); file.write_bytes(bundle_bytes(mode=mode))
            bundle = BoundedUnityFS(file)
            try:
                window = BundleWindow(bundle, bundle.nodes[0]); self.assertEqual(window.read(9), b"synthetic")
                window.seek(-4, 2); self.assertEqual(window.read(4), b"only")
                with self.assertRaises(ValueError): window.read()
                with self.assertRaises(ValueError): bundle.read(0, 17*1024*1024)
                with self.assertRaises(ValueError): window.seek(-1)
                self.assertLessEqual(bundle.max_cache, 32*1024*1024)
            finally: bundle.file.close()
        for flags in (0x640, 0x1240, 0x8240):
            file = self.root / 'bad.unity3d'; file.write_bytes(bundle_bytes(flags=flags))
            with self.assertRaisesRegex(ValueError, "encrypted/unknown"): BoundedUnityFS(file)

    def test_extractor_refuses_non_game_path_without_running_any_program(self):
        with self.assertRaisesRegex(ContractError, "installation"):
            extract_installed_text(str(self.root / "not-a-game"), str(self.root / "out"))
