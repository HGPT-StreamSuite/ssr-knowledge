"""Entirely synthetic transport and knowledge; no real site or real approvals."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ssr_knowledge.acquisition import BodyExtractor, Collector, Response
from ssr_knowledge.catalog import Catalog, digest
from ssr_knowledge.contracts import ContractError
from ssr_knowledge.guide_details import REQUIRED_TOPICS
from ssr_knowledge.research import discover, parse_detail, run_batch
from ssr_knowledge.store import utc_now
from ssr_knowledge.web_excerpt import import_web_excerpt
from test_acquisition import FakeClock, Transport, ok, robots
from test_catalog import seed, source

HTML = b'''<html><head><title>Lunar Rope - Synthetic Wiki</title></head><body><main>
<h1>Lunar Rope</h1><p>Found exclusively inside the Tomb. This is fictional test data.</p>
<p>Grants Invincibility from any damage while actively held in this synthetic fixture.</p>
<p>Can be thrown into the lava of The Kiln to receive the fictional test badge.</p>
<p>Weight 40. This fictional item cannot be cooked.</p>
<script>RUN_SOURCE_COMMAND</script></main></body></html>'''


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Catalog(self.root / 'data')
        _, self.draft = seed(self.store)
        self.store.import_drafts({'entries': [self.draft]})
        self.clock = FakeClock()
        cfg = source(); cfg.update(source_id='synthetic-detail', url='https://example.test/wiki/Lunar_Rope', source_type='wiki')
        self.plan = {'manifest': {'manifest_version': 1, 'game': 'PEAK:3527290', 'sources': [cfg]},
                     'tasks': [{'entry_id': self.draft['entry_id'], 'source_id': cfg['source_id'], 'adapter': 'wiki_item'}]}

    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def run_plan(self, responses, **options):
        transport = Transport(responses)
        result = run_batch(self.store, self.plan, transport=transport, sleep=self.clock.sleep, clock=self.clock.time, **options)
        return result, transport

    def test_automatic_fetch_parse_pending_reopen_dedup_and_source_update(self):
        result, transport = self.run_plan([robots(), ok(HTML)])
        self.assertEqual(result['results'][0]['state'], 'candidate_saved')
        self.assertEqual(len(transport.calls), 2)
        record = self.store.entry(self.draft['entry_id'])
        revision = record['revision_id']
        self.assertEqual(record['status'], 'pending_review')
        self.assertEqual(record['entry']['summary_zh'], self.draft['summary_zh'])
        extract = record['entry']['research_extracts'][0]
        self.assertTrue(extract['coverage']['substantive'])
        self.assertEqual(extract['translation_status'], 'pending_translation_and_human_review')
        self.assertNotIn('RUN_SOURCE_COMMAND', json.dumps(extract))
        self.assertEqual(self.store.search('actively held')['matches'], [])
        self.assertEqual(len(self.store.search('actively held', preview=True)['matches']), 1)
        self.store.close(); self.store = Catalog(self.root / 'data')
        resumed, no_calls = self.run_plan([])
        self.assertEqual((resumed['processed'], no_calls.calls), (0, []))
        duplicate, _ = self.run_plan([robots(), ok(HTML)], refresh=True)
        self.assertEqual(duplicate['results'][0]['state'], 'unchanged')
        self.assertEqual(self.store.entry(self.draft['entry_id'])['revision_id'], revision)
        updated, _ = self.run_plan([robots(), ok(HTML.replace(b'any damage', b'some fictional damage'))], refresh=True)
        self.assertEqual(updated['results'][0]['state'], 'candidate_saved')
        self.assertIsNotNone(updated['results'][0]['snapshot_diff'])
        current = self.store.entry(self.draft['entry_id'])
        self.assertGreater(current['revision_id'], revision)
        self.assertFalse(current['stale'])
        self.assertEqual(len(current['entry']['citations']), 2)
        self.assertEqual(self.store.entry(self.draft['entry_id'], revision)['status'], 'pending_review')

    def test_failure_does_not_replace_good_snapshot_entry_or_retry_manual_block(self):
        self.run_plan([robots(), ok(HTML)])
        before = self.store.entry(self.draft['entry_id'])
        old = self.store.sources()[-1]['latest']['snapshot_id']
        for response, expected in [(Response(403, {}, b''), 'forbidden')]:
            result, _ = self.run_plan([robots(), response], refresh=True)
            self.assertEqual(result['results'][0]['collection']['failure_kind'], expected)
            self.assertTrue(result['results'][0]['latest_good_snapshot_preserved'])
        self.assertEqual(self.store.entry(self.draft['entry_id'])['revision_id'], before['revision_id'])
        self.assertEqual(self.store.sources()[-1]['latest']['snapshot_id'], old)
        result, transport = self.run_plan([])
        self.assertEqual((result['processed'], transport.calls), (0, []))

    def test_title_only_or_partial_parser_is_quarantined_before_latest_snapshot(self):
        self.run_plan([robots(), ok(HTML)])
        before = self.store.entry(self.draft['entry_id'])['revision_id']
        for body in [b'<h1>Lunar Rope</h1><p>Can be used for Fictional Badge. Nothing else in this synthetic page.</p>',
                     b'<h1>Lunar Rope</h1><p>Found exclusively inside the Tomb. A single fragment is insufficient.</p>']:
            page = b'<html><title>Lunar Rope</title><main>' + body + b'</main></html>'
            result, _ = self.run_plan([robots(), ok(page)], refresh=True, retry_blocked=True)
            item = result['results'][0]
            self.assertEqual(item['collection']['failure_kind'], 'parse_incomplete')
            self.assertTrue(item['latest_good_snapshot_preserved'])
            self.assertEqual(self.store.entry(self.draft['entry_id'])['revision_id'], before)
            evidence = next(e for e in self.store.history() if e['event'] == 'collection_result')['details']['quarantine']
            self.assertEqual(Path(evidence['raw_path']).read_bytes(), page)

    def test_exception_categories_have_bounded_retries_and_no_false_empty_success(self):
        cases = [
            ([robots(b'User-agent: *\nDisallow: /')], 'robots_disallowed', 1),
            ([Response(403, {}, b'')], 'robots_unavailable', 1),
            ([robots(), Response(401, {}, b'')], 'auth_required', 2),
            ([robots(), Response(302, {'location': 'https://example.test/login'}, b'')], 'redirect_blocked', 2),
            ([robots(), ok(b'<title>Just a moment</title><main>Challenge fixture only. Never bypass it.</main>')], 'challenge', 2),
            ([robots(), ok(b'<title>Lunar Rope</title><main><input type="password">Login required synthetic document.</main>')], 'auth_required', 2),
            ([robots(), Response(429, {'retry-after': '120'}, b'')], 'rate_limited', 2),
            ([TimeoutError(), TimeoutError(), TimeoutError()], 'transient_network', 3),
        ]
        for index, (responses, kind, calls) in enumerate(cases):
            with self.subTest(kind=kind), Catalog(self.root / ('case-' + str(index))) as store:
                _, draft = seed(store); store.import_drafts({'entries': [draft]})
                clock = FakeClock(); transport = Transport(responses)
                result = run_batch(store, self.plan, transport=transport, sleep=clock.sleep, clock=clock.time)['results'][0]
                self.assertEqual(result['collection']['failure_kind'], kind)
                self.assertEqual(len(transport.calls), calls)
                self.assertFalse(result['direct_fetch_success'])
                self.assertTrue(result['latest_good_snapshot_preserved'])
                self.assertEqual(store.entry(draft['entry_id'])['revision_id'], 1)

    def test_retry_after_survives_reopen_and_job_retry_budget(self):
        result, transport = self.run_plan([robots(), Response(429, {'retry-after': '120'}, b'')])
        self.assertEqual(result['results'][0]['state'], 'retry_wait')
        self.store.close(); self.store = Catalog(self.root / 'data')
        result, no_calls = self.run_plan([])
        self.assertEqual((result['processed'], no_calls.calls), (0, []))
        for n in (2, 3):
            self.clock.now += 121
            result, _ = self.run_plan([robots(), Response(429, {'retry-after': '120'}, b'')])
        self.assertEqual(result['results'][0]['state'], 'manual_required')
        self.assertTrue(result['results'][0]['retry_budget_exhausted'])
        result, _ = self.run_plan([])
        self.assertEqual(result['processed'], 0)

    def test_terms_unknown_makes_zero_requests_and_returns_manual_action(self):
        self.plan['manifest']['sources'][0]['policy']['uses']['local_cache']['status'] = 'unknown'
        result, transport = self.run_plan([])
        self.assertEqual(transport.calls, [])
        self.assertEqual(result['results'][0]['collection']['failure_kind'], 'terms_unreviewed')
        self.assertEqual(result['results'][0]['state'], 'manual_required')

    def test_source_url_identity_conflict_becomes_auditable_manual_job_without_io(self):
        cfg = self.plan['manifest']['sources'][0]
        self.store.register_source(cfg)
        cfg['source_id'] = 'synthetic-colliding-id'
        self.plan['tasks'][0]['source_id'] = cfg['source_id']
        result, transport = self.run_plan([])
        self.assertEqual(transport.calls, [])
        self.assertEqual(result['results'][0]['collection']['failure_kind'], 'source_conflict')
        self.assertEqual(result['results'][0]['state'], 'manual_required')
        self.assertTrue(result['results'][0]['latest_good_snapshot_preserved'])

    def test_candidate_validation_failure_finishes_job_without_overwriting_entry(self):
        revision = self.store.entry(self.draft['entry_id'])['revision_id']
        with patch.object(self.store, 'import_drafts', side_effect=ContractError('Synthetic schema conflict')):
            result, _ = self.run_plan([robots(), ok(HTML)])
        item = result['results'][0]
        self.assertTrue(item['direct_fetch_success'])
        self.assertEqual(item['state'], 'manual_required')
        self.assertEqual(item['failure_kind'], 'candidate_validation')
        self.assertEqual(self.store.entry(self.draft['entry_id'])['revision_id'], revision)
        self.assertEqual(self.store.db.execute('select count(*) from research_attempts where completed_at is null').fetchone()[0], 0)

    def test_running_lease_can_be_resumed_after_crash_and_batch_is_bounded(self):
        self.run_plan([robots(), ok(HTML)])
        self.store.db.execute("UPDATE research_jobs SET state='running',lease_until=?", (self.clock.now + 300,)); self.store.db.commit()
        result, _ = self.run_plan([]); self.assertEqual(result['processed'], 0)
        self.clock.now += 301
        result, _ = self.run_plan([robots(), ok(HTML)]); self.assertEqual(result['results'][0]['state'], 'unchanged')
        with self.assertRaises(ContractError): self.run_plan([], max_jobs=11)

    def test_one_job_budget_persists_the_rest_for_next_run(self):
        other = copy.deepcopy(self.draft); other['entry_id'] = 'fixture-other-rope'
        self.store.import_drafts({'entries': [other]})
        self.plan['tasks'].append({**self.plan['tasks'][0], 'entry_id': other['entry_id']})
        first, transport = self.run_plan([robots(), ok(HTML)], max_jobs=1)
        self.assertEqual(first['processed'], 1)
        self.assertEqual(first['queue_counts'], {'candidate_saved': 1, 'queued': 1})
        self.assertEqual(len(transport.calls), 2)
        second, _ = self.run_plan([robots(), ok(HTML)], max_jobs=1)
        self.assertEqual(second['processed'], 1)
        self.assertEqual(second['results'][0]['entry_id'], other['entry_id'])

    def test_positive_badge_row_extract_keeps_official_condition_separate(self):
        import test_organization as fixtures
        fixture = fixtures.OrganizationTests(); fixture.setUp()
        try:
            badge = copy.deepcopy(fixture.badge)
            self.store.import_drafts({'entries': [self.draft]})
            cfg = source(); cfg.update(source_id='synthetic-badges-page', url='https://example.test/wiki/Badges', source_type='wiki')
            plan = {'manifest': {'manifest_version': 1, 'game': 'PEAK:3527290', 'sources': [cfg]},
                    'tasks': [{'entry_id': badge['entry_id'], 'source_id': cfg['source_id'], 'adapter': 'wiki_badge'}]}
            html = b'<title>Synthetic Badges</title><main><table><tr><td>FICTIONAL BADGE</td><td><p>Found exclusively inside the Tomb. Synthetic location only.</p><p>Can be thrown into the lava of The Kiln to receive a fictional badge.</p></td></tr><tr><td>OTHER BADGE</td><td>All living players earn this other badge.</td></tr></table></main>'
            transport = Transport([robots(), ok(html)])
            result = run_batch(fixture.store, plan, transport=transport, sleep=self.clock.sleep, clock=self.clock.time)
            self.assertEqual(result['results'][0]['state'], 'candidate_saved')
            current = fixture.store.entry(badge['entry_id'])
            self.assertEqual(current['entry']['badge_details'], badge['badge_details'])
            self.assertEqual(current['entry']['names'], badge['names'])
            self.assertNotIn('living players', json.dumps(current['entry']['research_extracts']))
            self.assertEqual(current['status'], 'pending_review')
        finally:
            fixture.tearDown()

    def test_search_excerpt_import_is_bounded_deduped_and_never_automatic_fetch_proof(self):
        parser = BodyExtractor({'tag': 'main'}); parser.feed(HTML.decode()); body = parser.body()
        file = self.root / 'index-excerpt.txt'; file.write_text(body, encoding='utf-8')
        receipt = {'source_id': 'synthetic-index-excerpt', 'source_url': 'https://example.test/wiki/Lunar_Rope',
            'title': 'Synthetic index excerpt; not real website evidence', 'retrieved_at': utc_now(), 'index_date_label': 'unverified synthetic date',
            'raw_sha256': digest(file.read_bytes()), 'queries': ['synthetic query only'], 'direct_fetch_status': 403,
            'license_statement': 'Synthetic fixture authored for testing only.', 'license_url': 'https://example.test/license',
            'method': 'web_search_index_excerpt', 'uses': {p: {'status': 'allowed' if p == 'local_cache' else 'unknown', 'basis': 'Synthetic only.'} for p in ('local_cache','search_index','ai_input','ai_train')}}
        first = import_web_excerpt(self.store, str(file), receipt)
        second = import_web_excerpt(self.store, str(file), receipt)
        self.assertEqual((first['snapshot_id'], second['state']), (second['snapshot_id'], 'unchanged'))
        self.assertFalse(first['full_page_acquired']); self.assertEqual(first['http_requests'], 0)
        snap = self.store.snapshot(first['snapshot_id'], True)
        transport = Transport([])
        self.assertEqual(Collector(self.store, transport=transport).collect([snap['source']])[0]['state'], 'blocked_or_failed')
        self.assertEqual(transport.calls, [])
        draft = copy.deepcopy(self.draft); draft['evidence_class'] = 'wiki'
        draft['citations'].append({'snapshot_id': first['snapshot_id'], 'locator': 'Synthetic index', 'evidence_quote': body.splitlines()[1]})
        draft['research_extracts'] = [{**parse_detail(HTML.decode(), body, draft['name_en'], 'wiki_item'), 'citation': 1}]
        with self.assertRaisesRegex(ContractError, 'directly collected'):
            self.store.import_drafts({'entries': [draft]})
        for change in ({'direct_fetch_status': 200}, {'raw_sha256': '0'*64}, {'method': 'direct_http'}):
            bad = {**receipt, **change}
            with self.subTest(change=change), self.assertRaises(ContractError): import_web_excerpt(self.store, str(file), bad)
        file.write_text('word ' * 201, encoding='utf-8')
        with self.assertRaises(ContractError): import_web_excerpt(self.store, str(file), {**receipt, 'raw_sha256': digest(file.read_bytes())})

    def test_different_sources_remain_unreconciled_and_never_inherit_approval(self):
        self.store.review(self.draft['entry_id'], 1, 'approve', 'synthetic-human', 'Simulation only.', True)
        self.store.publish(self.draft['entry_id'], 1)
        self.assertEqual(len(self.store.search('月繩')['matches']), 1)
        self.run_plan([robots(), ok(HTML)])
        first = self.store.entry(self.draft['entry_id'])
        self.assertEqual(first['status'], 'pending_review')
        self.assertEqual(self.store.search('月繩')['matches'], [])
        cfg = self.plan['manifest']['sources'][0]
        cfg.update(source_id='synthetic-other-detail', url='https://example.test/wiki/Alternative_Rope')
        self.plan['tasks'][0]['source_id'] = cfg['source_id']
        result, _ = self.run_plan([robots(), ok(HTML.replace(b'any damage', b'no fictional damage'))])
        self.assertEqual(len(self.store.entry(self.draft['entry_id'])['entry']['research_extracts']), 2)
        self.assertIn('unreconciled', result['results'][0]['reconciliation'])

    def test_discovery_follows_only_saved_exact_name_anchors_and_never_fetches(self):
        cfg = self.plan['manifest']['sources'][0]
        raw = b'<main><a href="/wiki/Lunar_Rope">Lunar Rope</a><a href="https://other.test/wiki/No">Lunar Rope</a><a href="/wiki/File:Trap">Lunar Rope</a><a href="/wiki/Guessed">Other name</a></main>'
        self.store.register_source(cfg); self.store.save_snapshot(cfg, raw, 'Synthetic saved link page, not a real network fetch.', {})
        result = discover(self.store)
        self.assertEqual(result['network_requests'], 0)
        self.assertEqual([c['url'] for c in result['candidates']], ['https://example.test/wiki/Lunar_Rope'])
        self.assertFalse(result['candidates'][0]['fetch_allowed'])

    def test_badge_parser_cannot_borrow_another_badges_conditions(self):
        html = '<table><tr><td>Target Badge</td><td>Offer a sacrifice.</td></tr><tr><td>Other Badge</td><td>Throw an idol into the lava of The Kiln. All living players earn this badge.</td></tr></table>'
        body = 'Target Badge Offer a sacrifice.\nOther Badge Throw an idol into the lava of The Kiln. All living players earn this badge.'
        with self.assertRaisesRegex(ContractError, 'incomplete'):
            parse_detail(html, body, 'Target Badge', 'wiki_badge')

    def test_guide_claims_require_exact_quotes_correct_class_and_explicit_gaps(self):
        cfg = copy.deepcopy(self.plan['manifest']['sources'][0]); self.store.register_source(cfg)
        body = 'A fictional thing found inside the Tomb. This is not real game data.'
        snap = self.store.save_snapshot(cfg, body.encode(), body, {})['snapshot_id']
        draft = copy.deepcopy(self.draft); draft['evidence_class'] = 'wiki'
        draft['citations'].append({'snapshot_id': snap, 'locator': 'Synthetic paragraph', 'evidence_quote': body})
        draft['guide_details'] = {'schema_version': 1, 'method': 'agent_edited_pending_review',
            'claims': [{'topic': 'location', 'text_zh': '虛構測試位置。', 'source_class': 'wiki', 'evidence': [{'citation': 1, 'quote': body}]}],
            'gaps': [{'topic': t, 'reason': '合成測試缺資料。'} for t in sorted(REQUIRED_TOPICS - {'location'})]}
        self.store.import_drafts({'entries': [draft]})
        self.assertEqual(self.store.search('虛構測試位置')['matches'], [])
        self.assertEqual(len(self.store.search('虛構測試位置', preview=True)['matches']), 1)
        for change in ('missing_gap', 'invented_quote', 'wrong_class', 'official_compilation'):
            bad = copy.deepcopy(draft)
            if change == 'missing_gap': bad['guide_details']['gaps'] = []
            if change == 'invented_quote': bad['guide_details']['claims'][0]['evidence'][0]['quote'] = 'Not in source'
            if change == 'wrong_class': bad['guide_details']['claims'][0]['source_class'] = 'player_test'
            if change == 'official_compilation': bad['evidence_class'] = 'official'
            with self.subTest(change=change), self.assertRaises(ContractError): self.store.import_drafts({'entries': [bad]})
