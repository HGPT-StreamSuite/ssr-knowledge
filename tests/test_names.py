"""Fictional names only; game-localization verification is never inferred."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ssr_knowledge.catalog import Catalog, ROOT
from ssr_knowledge.contracts import ContractError
from ssr_knowledge.names import name_records
from test_catalog import seed, source


def annotated(draft):
    value = copy.deepcopy(draft)
    labels = [("english", value["name_en"], "en", "source_name", 0),
              ("chinese", value["name_zh"], "zh-TW", "provisional_translation", None),
              *(("alias", a, "en" if a.isascii() else "zh-TW", "provisional_alias", None) for a in value["aliases"])]
    value["names"] = {"schema_version": 1, "target_locale": "zh-TW", "records": [
        {"text": text, "locale": locale, "role": role, "status": status, "citation": citation,
         "basis": "Synthetic source/editorial label, not a real PEAK translation."}
        for role, text, locale, status, citation in labels]}
    return value


class NameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Catalog(Path(self.temp.name) / "data")
        self.config, self.draft = seed(self.store)

    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def save(self, draft=None):
        return self.store.import_drafts({"entries": [draft or self.draft]})[0]["revision_id"]

    def test_name_variations_find_same_id_without_migrating_legacy_rows(self):
        self.save()
        for query in ("LUNAR ROPE", "  lunar\t rope  ", "LunarRope", "Ｌｕｎａｒ　Ｒｏｐｅ", "月 光 繩", "moonrope"):
            with self.subTest(query=query):
                result = self.store.search(query, preview=True, names_only=True)
                self.assertEqual(result["name_resolution"], {"status": "unique", "entry_ids": [self.draft["entry_id"]]})
                self.assertEqual(result["matches"][0]["name_matches"][0]["status"], "unverified_legacy")
                self.assertEqual(result["matches"][0]["match_type"], "exact_name")
        self.assertEqual(self.store.search("藍色落腳", preview=True, names_only=True)["matches"], [])
        self.assertEqual(len(self.store.search("藍色落腳", preview=True)["matches"]), 1)

    def test_ambiguity_is_preserved_even_when_display_limit_is_one(self):
        self.save()
        other = copy.deepcopy(self.draft); other["entry_id"] = "fixture-other-rope"
        self.save(other)
        result = self.store.search("月繩", preview=True, names_only=True, limit=1)
        self.assertEqual(result["name_resolution"]["status"], "ambiguous")
        self.assertEqual(set(result["name_resolution"]["entry_ids"]), {self.draft["entry_id"], other["entry_id"]})
        self.assertEqual((result["total_matches"], len(result["matches"]), result["truncated"]), (2, 1, True))
        formal = self.store.search("月繩", names_only=True)
        self.assertEqual(formal["name_resolution"], {"status": "unresolved", "entry_ids": []})

    def test_generic_spool_and_cannon_are_distinct_not_prefix_resolved(self):
        for suffix in ("", " Spool", " Cannon"):
            d = copy.deepcopy(self.draft); d["entry_id"] += suffix.lower().replace(" ", "-")
            d["name_en"] += suffix; d["aliases"] = [d["name_en"]]
            self.save(d)
        for suffix in ("", "Spool", "Cannon"):
            result = self.store.search("lunarrope" + suffix, preview=True, names_only=True)
            self.assertEqual(len(result["matches"]), 1)
            self.assertEqual(result["matches"][0]["entry"]["name_en"], "Lunar Rope" + (" " + suffix if suffix else ""))
        self.assertEqual(self.store.search("Lunar-Rope", preview=True, names_only=True)["matches"], [])

    def test_structured_names_pin_source_keep_locale_and_update_pending(self):
        old = self.save()
        self.store.review(self.draft["entry_id"], old, "approve", "synthetic-human", "Fixture only", True)
        self.store.publish(self.draft["entry_id"], old)
        d = annotated(self.draft)
        d["aliases"].append("月光绳")
        d["names"]["records"].append({"text": "月光绳", "locale": "zh-CN", "role": "alias", "status": "provisional_alias", "citation": None, "basis": "Explicit synthetic Simplified Chinese alias; not converted or official."})
        new = self.save(d)
        self.assertNotEqual(old, new)
        self.assertEqual(self.store.entry(d["entry_id"])["status"], "pending_review")
        self.assertEqual(self.store.entry(d["entry_id"], old)["status"], "published")
        self.assertEqual(self.store.search("月光绳", names_only=True)["matches"], [])
        result = self.store.search("月光绳", preview=True, names_only=True)
        self.assertEqual(result["matches"][0]["name_matches"][0]["locale"], "zh-CN")
        repeat = self.store.import_drafts({"entries": [d]})[0]
        self.assertEqual((repeat["state"], repeat["revision_id"]), ("unchanged", new))
        bad = annotated(self.draft); bad["names"]["records"][0]["text"] = "Invented name"
        with self.assertRaisesRegex(ContractError, "match display"):
            self.save(bad)
        bad = annotated(self.draft); bad["names"]["records"][1]["locale"] = "zh-CN"
        with self.assertRaisesRegex(ContractError, "locale differs"):
            self.save(bad)

    def test_marketing_cannot_be_promoted_to_game_ui_or_other_locale(self):
        config = source(); config.update(source_id="fixture-marketing", url="https://example.test/marketing", language="zh-TW")
        self.store.register_source(config)
        body = "合成宣傳詞：月光攀登繩；僅供測試。"
        sid = self.store.save_snapshot(config, body.encode(), body, {"name_evidence": {"kind": "official_marketing", "locale": "zh-TW"}})["snapshot_id"]
        d = annotated(self.draft); d["aliases"].append("月光攀登繩")
        d["citations"].append({"snapshot_id": sid, "locator": "synthetic marketing", "evidence_quote": "月光攀登繩"})
        d["names"]["records"].append({"text": "月光攀登繩", "locale": "zh-TW", "role": "alias", "status": "official_marketing_alias", "citation": 1, "basis": "Synthetic marketing only, game UI unverified."})
        self.save(d)
        record = d["names"]["records"][-1]
        for field, value in (("status", "game_ui_verified"), ("locale", "zh-CN"), ("citation", 0)):
            bad = copy.deepcopy(d); bad["names"]["records"][-1][field] = value
            with self.subTest(field=field), self.assertRaises(ContractError): self.save(bad)
        self.assertEqual(record["status"], "official_marketing_alias")

    def test_game_ui_label_needs_explicit_scope_exact_quote_and_official_source(self):
        d = annotated(self.draft); record = d["names"]["records"][0]
        record["status"] = "game_ui_verified"
        with self.assertRaisesRegex(ContractError, "evidence scope"):
            self.save(d)
        body = "Synthetic game UI: Lunar Rope"
        sid = self.store.save_snapshot(self.config, body.encode(), body, {"name_evidence": {"kind": "game_ui", "locale": "en"}})["snapshot_id"]
        d["citations"][0] = {"snapshot_id": sid, "locator": "synthetic UI only", "evidence_quote": "Lunar Rope"}
        self.save(d)
        other = source(); other.update(source_id="fixture-community", url="https://example.test/community", source_type="wiki")
        self.store.register_source(other)
        sid2 = self.store.save_snapshot(other, body.encode(), body, {"name_evidence": {"kind": "game_ui", "locale": "en"}})["snapshot_id"]
        bad = copy.deepcopy(d); bad["evidence_class"] = "wiki"; bad["citations"][0]["snapshot_id"] = sid2
        with self.assertRaisesRegex(ContractError, "evidence scope"):
            self.save(bad)

    def test_names_only_keeps_published_source_and_rejection_boundaries(self):
        revision = self.save(annotated(self.draft))
        self.store.review(self.draft["entry_id"], revision, "reject", "synthetic-human", "Fixture rejection", True)
        self.assertEqual(self.store.search("LunarRope", names_only=True)["matches"], [])
        self.assertEqual(self.store.search("LunarRope", preview=True, names_only=True)["matches"][0]["status"], "rejected")
        changed = annotated(self.draft); changed["limitations"] += " New synthetic revision after rejection."
        revision = self.save(changed)
        self.store.review(self.draft["entry_id"], revision, "approve", "synthetic-human", "Fixture approval", True)
        self.store.publish(self.draft["entry_id"], revision)
        formal = self.store.search("LunarRope", names_only=True)
        self.assertEqual(formal["name_resolution"]["status"], "unique")
        self.assertNotIn("evidence_quote", formal["matches"][0]["entry"]["citations"][0])
        self.store.event(self.config["source_id"], "collection_result", {"robots_assessment": {"content_signals": {"search": ["no"]}}})
        self.assertEqual(self.store.search("LunarRope", names_only=True)["name_resolution"]["entry_ids"], [])
        self.assertEqual(self.store.search("LunarRope", preview=True, names_only=True)["name_resolution"]["status"], "unique")
        self.config["policy"]["uses"]["search_index"]["status"] = "prohibited"
        self.store.register_source(self.config)
        formal = self.store.search("LunarRope", names_only=True)
        self.assertEqual(formal["name_resolution"]["entry_ids"], [])

    def test_cli_reopen_reports_names_and_ambiguity_without_publication(self):
        self.save(annotated(self.draft))
        command = [sys.executable, "-m", "ssr_knowledge", "catalog", "--data-dir", str(self.store.root),
                   "search", "--text", " lunar rope ", "--names-only", "--preview"]
        p = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result["name_resolution"]["status"], "unique")
        self.assertEqual(result["matches"][0]["name_matches"][0]["status"], "source_name")
        self.assertEqual(result["matches"][0]["entry"]["names"]["target_locale"], "zh-TW")
