"""Synthetic full-workflow regressions; no real pages, permissions or reviews."""
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
from test_acquisition import FakeClock, Transport, ok, robots
from test_catalog import BODY, seed, source


class SearchEligibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = Catalog(Path(self.temp.name) / "synthetic-data")
        _, self.template = seed(self.store)
        self.clock = FakeClock()

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def collect_draft(self, slug: str, signals: str | None = None, text: str | None = None) -> tuple[dict, dict, dict]:
        config = source()
        config.update(source_id="synthetic-" + slug, url="https://example.test/" + slug)
        rules = text or "User-agent: *\nAllow: /\n" + ("Content-Signal: " + signals if signals else "")
        transport = Transport([robots(rules.encode()), ok()])
        result = Collector(self.store, transport=transport, clock=self.clock.time, sleep=self.clock.sleep).collect([config], "local_cache")[0]
        self.assertEqual(result["state"], "saved")
        self.assertEqual(transport.calls, ["https://example.test/robots.txt", config["url"]])
        draft = copy.deepcopy(self.template)
        draft.update(entry_id="fixture-" + slug, summary_zh="合成限制哨兵：PRIVATE_FRAGMENT_" + slug)
        draft["citations"] = [{"snapshot_id": result["snapshot_id"], "locator": "synthetic main",
                               "evidence_quote": "Synthetic fictional rope makes a blue platform."}]
        return config, draft, result

    def publish_fixture(self, draft: dict) -> int:
        rev = self.store.import_drafts({"entries": [draft]})[0]["revision_id"]
        self.store.review(draft["entry_id"], rev, "approve", "synthetic-human", "Synthetic fixture only", True)
        self.store.publish(draft["entry_id"], rev)
        self.assertEqual(self.store.entry(draft["entry_id"])["status"], "published")
        return rev

    def test_local_cache_search_no_stays_out_after_approval_and_publishing(self) -> None:
        _, draft, snapshot = self.collect_draft("denied", "search=no")
        self.assertEqual(self.store.snapshot(snapshot["snapshot_id"])["metadata"]["robots_assessment"]["usage_signals"]["search_index"], "prohibited")
        revision = self.publish_fixture(draft)
        for query in ("月", "月光繩", "Lunar Rope", "MOON ROPE", "PRIVATE_FRAGMENT_denied"):
            result = self.store.search(query)
            self.assertEqual(result["matches"], [])
            self.assertNotIn("PRIVATE_FRAGMENT_denied", json.dumps(result["matches"], ensure_ascii=False))
        self.assertEqual(self.store.search("月光繩", preview=True)["matches"][0]["status"], "published")
        self.assertEqual(self.store.entry(draft["entry_id"], revision)["status"], "published")

    def test_missing_unknown_and_unrelated_signals_do_not_become_search_denials(self) -> None:
        cases = [None, "search=unknown", "search=maybe", "ai-input=no,ai-train=no,use=reference", "search=yes,ai-train=no"]
        for n, signals in enumerate(cases):
            with self.subTest(signals=signals):
                _, draft, _ = self.collect_draft("unknown-" + str(n), signals)
                self.publish_fixture(draft)
                self.assertIn(draft["entry_id"], [m["entry"]["entry_id"] for m in self.store.search("月光繩")["matches"]])

    def test_conflicting_search_signal_with_explicit_no_still_denies(self) -> None:
        _, draft, snap = self.collect_draft("conflict", "search=yes,search=no")
        self.assertEqual(self.store.snapshot(snap["snapshot_id"])["metadata"]["robots_assessment"]["usage_signals"]["search_index"], "unknown")
        self.publish_fixture(draft)
        self.assertEqual(self.store.search("月光繩")["matches"], [])

    def test_mixed_citations_exclude_entire_entry_in_either_order_without_fragments(self) -> None:
        _, allowed, _ = self.collect_draft("allowed", "search=yes")
        _, denied, _ = self.collect_draft("restricted", "search=no")
        self.publish_fixture(allowed)
        for n, citations in enumerate((allowed["citations"] + denied["citations"], denied["citations"] + allowed["citations"])):
            mixed = copy.deepcopy(allowed)
            mixed.update(entry_id="fixture-mixed-" + str(n), summary_zh="合成混合來源 PRIVATE_RESTRICTED_COMPOSITE", citations=citations)
            self.publish_fixture(mixed)
        formal = self.store.search("月光繩")
        self.assertEqual([r["entry"]["entry_id"] for r in formal["matches"]], [allowed["entry_id"]])
        for secret in ("PRIVATE_RESTRICTED_COMPOSITE", "synthetic-restricted", "fixture-mixed"):
            self.assertNotIn(secret, json.dumps(formal, ensure_ascii=False))
        self.assertEqual(self.store.search("PRIVATE_RESTRICTED_COMPOSITE")["matches"], [])
        self.assertEqual(len(self.store.search("PRIVATE_RESTRICTED_COMPOSITE", preview=True)["matches"]), 2)

    def test_actual_ua_and_legacy_saved_robots_are_interpreted_without_network(self) -> None:
        _, allowed, _ = self.collect_draft("actual-ua", text="User-agent: *\nAllow: /\nUser-agent: GPTBot\nContent-Signal: search=no\nDisallow: /")
        self.publish_fixture(allowed)
        self.assertEqual(len(self.store.search("月光繩")["matches"]), 1)
        config = source()
        config.update(source_id="legacy-search-no", url="https://example.test/legacy")
        self.store.register_source(config)
        snap = self.store.save_snapshot(config, BODY.encode(), BODY, {"robots_text": "User-agent: *\nAllow: /\nContent-Signal: search=no"})
        legacy = copy.deepcopy(self.template)
        legacy["entry_id"] = "fixture-legacy-search-no"
        legacy["citations"][0]["snapshot_id"] = snap["snapshot_id"]
        self.publish_fixture(legacy)
        self.assertEqual([r["entry"]["entry_id"] for r in self.store.search("月光繩")["matches"]], [allowed["entry_id"]])

    def test_deduplicated_body_still_honors_newly_observed_search_no(self) -> None:
        config, draft, before = self.collect_draft("reobserved")
        revision = self.publish_fixture(draft)
        self.assertEqual(len(self.store.search("月光繩")["matches"]), 1)
        transport = Transport([robots(b"User-agent: *\nAllow: /\nContent-Signal: search=no"), ok()])
        result = Collector(self.store, transport=transport, clock=self.clock.time, sleep=self.clock.sleep).collect([config], "local_cache")[0]
        self.assertEqual(result["state"], "unchanged")
        self.assertEqual(result["snapshot_id"], before["snapshot_id"])
        self.assertEqual(self.store.search("月光繩")["matches"], [])
        self.assertEqual(self.store.entry(draft["entry_id"], revision)["status"], "published")

    def test_cli_reopen_after_local_cache_review_publish_has_no_restricted_result(self) -> None:
        _, draft, _ = self.collect_draft("cli-denied", "search=no")
        path = Path(self.temp.name) / "synthetic-draft.json"
        path.write_text(json.dumps({"entries": [draft]}, ensure_ascii=False), encoding="utf-8")
        prefix = [sys.executable, "-m", "ssr_knowledge", "catalog", "--data-dir", str(self.store.root)]

        def cli(*args: str) -> dict:
            p = subprocess.run(prefix + list(args), cwd=ROOT, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            return json.loads(p.stdout)

        revision = str(cli("import-drafts", "--file", str(path))["results"][0]["revision_id"])
        cli("review-entry", "--entry-id", draft["entry_id"], "--revision", revision, "--decision", "approve",
            "--reviewer", "synthetic-human", "--note", "Synthetic fixture only", "--human-reviewed")
        cli("publish-entry", "--entry-id", draft["entry_id"], "--revision", revision)
        self.assertEqual(cli("entry", "--entry-id", draft["entry_id"])["status"], "published")
        self.assertEqual(cli("search", "--text", "月光繩")["matches"], [])
        self.assertEqual(cli("search", "--text", "月光繩", "--preview")["matches"][0]["status"], "published")


if __name__ == "__main__":
    unittest.main()
