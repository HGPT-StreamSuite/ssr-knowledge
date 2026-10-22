"""Synthetic local HTTP/SQLite tests. No actual corpus or real approvals."""
import copy
import hashlib
import http.client
import json
import sqlite3
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode

import test_organization as organization_fixture
from ssr_knowledge.catalog import Catalog
from ssr_knowledge.contracts import ContractError
from ssr_knowledge.item_table import parse_peak_items
from ssr_knowledge.live_review import ReviewServer, load_model, project_entry, query_options, serve_review
from ssr_knowledge.upload_source import import_text_source
from test_item_upload import TEXT, receipt


class LiveReviewTests(unittest.TestCase):
    def setUp(self):
        self.fixture = organization_fixture.OrganizationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.store = self.fixture.store
        self.root = self.fixture.root
        self.data = self.store.root
        self.database = self.data / 'knowledge.sqlite3'
        # The body is entirely synthetic; the real-shaped URL tests source
        # classification only. No HTTP source collection is performed.
        rec = receipt(); rec.update(source_id='synthetic-peak-items', source_url='https://peak.wiki.gg/wiki/Items', library_file_id='libfile_syntheticlive0001')
        file = self.root / 'synthetic-items.txt'; file.write_text(TEXT, encoding='utf-8')
        snap = import_text_source(self.store, str(file), rec)['snapshot_id']
        self.item = copy.deepcopy(self.fixture.item)
        self.item['citations'][0]['snapshot_id'] = snap
        self.item['detail_page'] = {'url': 'https://peak.wiki.gg/wiki/Synthetic_Lunar_Spool', 'status': 'user_provided_unverified',
            'basis': 'Synthetic fixture; no real page was requested.', 'checked_at': '2026-01-01', 'http_status': 403}
        self.store.import_drafts({'entries': [self.item]})
        row = parse_peak_items(TEXT)['items'][1]
        other = copy.deepcopy(self.item)
        other.update(entry_id='fixture-lunar-cannon', name_en='Lunar Cannon', name_zh='月光大砲', aliases=['月砲'],
            summary_zh='第二件合成資料。', item_details={**row, 'notes_zh': [], 'translation_status': 'agent_translation_pending_review'})
        other.pop('links'); other.pop('detail_page')
        other['organization'] = {'schema_version': 1, 'method': 'agent_edited_pending_review', 'source_row_sha256': row['source_row_sha256'],
            'topics': {k: [] for k in self.item['organization']['topics']}, 'notes_zh': []}
        other['citations'][0].update(locator='Synthetic cannon row', evidence_quote='Lunar Cannon\tLunar Cannon')
        self.store.import_drafts({'entries': [other]})
        self.server = ReviewServer(self.data, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(3)

    def request(self, path='/', method='GET', headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        conn.request(method, path, headers=headers or {})
        result = conn.getresponse(); data = result.read().decode('utf-8')
        status, response_headers = result.status, dict(result.getheaders())
        conn.close()
        return status, data, response_headers

    def api(self, **options):
        status, data, _ = self.request('/api/review?' + urlencode(options))
        self.assertEqual(status, 200, data)
        return json.loads(data)

    def test_read_only_mode_never_creates_or_writes_catalog(self):
        before = self.database.read_bytes()
        with Catalog(self.data, read_only=True) as reader:
            self.assertEqual(reader.db.execute('PRAGMA query_only').fetchone()[0], 1)
            with self.assertRaises(sqlite3.OperationalError): reader.db.execute('DELETE FROM entries')
        absent = self.root / 'absent'
        with self.assertRaises(ContractError): Catalog(absent, read_only=True)
        self.assertFalse(absent.exists())
        self.assertEqual(self.database.read_bytes(), before)
        with self.assertRaises(ContractError): serve_review(None, 0)

    def test_db_api_and_server_rendered_html_use_same_names_values_and_states(self):
        model = self.api(entry=self.item['entry_id'])
        item = model['detail']
        self.assertEqual(item['name_zh'], self.item['name_zh'])
        self.assertEqual(item['statistics'], self.item['item_details']['statistics'])
        self.assertEqual(item['source_label'], 'Wiki Items：已保存附件')
        self.assertEqual(item['detail_page']['label'], '詳細頁：未讀取（HTTP 403）')
        self.assertEqual(item['review_label'], '內容：待使用者驗收')
        self.assertEqual(item['statistics']['hunger']['state'], 'source_na')
        self.assertIsNone(item['statistics']['hunger']['value'])
        self.assertEqual(item['statistics']['bonus_stamina']['value'], 0)
        status, page, headers = self.request('/?' + urlencode({'entry': self.item['entry_id']}))
        self.assertEqual(status, 200)
        for text in [item['name_zh'], item['source_label'], item['review_label'], item['detail_page']['label'],
                     '額外耐力：0', 'n/a（來源標示，含義未確認）', str(self.database), '讀取時間：', '最近條目紀錄：']:
            self.assertIn(text, page)
        self.assertNotIn('SHA-256', page)
        self.assertNotIn('<script', page)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertNotIn('Access-Control-Allow-Origin', headers)

    def test_bilingual_alias_search_filters_and_pagination(self):
        for query in ['Lunar Spool', '月光繩捲', '月繩', 'MOON SPOOL', 'ＬＵＮＡＲ　ＳＰＯＯＬ']:
            result = self.api(q=query)
            self.assertIn(self.item['entry_id'], result['exact_name_entry_ids'])
            self.assertEqual(result['entries'][0]['entry_id'], self.item['entry_id'])
        self.assertEqual(self.api(kind='item')['total_matches'], 2)
        self.assertEqual(self.api(kind='badge')['total_matches'], 1)
        pages = [self.api(page=i, page_size=1) for i in (1, 2, 3)]
        ids = [p['entries'][0]['entry_id'] for p in pages]
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual(self.api(page=999, page_size=1)['query']['page'], 3)
        self.assertEqual(self.api(q='not present')['entries'], [])
        status, page, _ = self.request('/?page_size=1')
        self.assertEqual(status, 200); self.assertIn('下一頁', page)
        self.assertIn('page=2', page)

    def test_relation_links_and_source_states_are_not_conflated(self):
        item = self.api(entry=self.item['entry_id'])['detail']
        badge_id = self.fixture.badge['entry_id']
        self.assertEqual([r['entry_id'] for r in item['relations']], [badge_id])
        self.assertEqual(set(item['relations'][0]['evidence']), {'官方條件提及', 'Items 備註提示'})
        badge = self.api(entry=badge_id)['detail']
        self.assertEqual([r['entry_id'] for r in badge['relations']], [self.item['entry_id']])
        self.assertIsNone(badge['detail_page'])
        self.assertEqual(badge['steam_equivalence'], 'unverified')
        cannon = self.api(entry='fixture-lunar-cannon')['detail']
        self.assertEqual(cannon['detail_page']['state'], 'missing_link')
        self.assertEqual(cannon['detail_page']['label'], '詳細頁：尚未補連結')

    def test_local_resource_is_not_a_store_article_and_incoming_hint_retains_method(self):
        badge_id = self.fixture.badge['entry_id']
        badge = self.api(entry=badge_id)['detail']
        for source in badge['sources']:
            self.assertIsNone(source['url'])
            self.assertTrue(source['acquisition_uri'].startswith('installed-game-text:'))
            self.assertIn('NAME_', source['locator'])
        hint = next(e for e in badge['relations'][0]['evidence_details'] if e['label'] == 'Items 備註提示')
        self.assertEqual(hint['text_en'], self.item['item_details']['notes_en'][1])
        self.assertEqual(hint['text_zh'], self.item['organization']['notes_zh'][1])
        self.assertEqual(hint['source']['locator'], self.item['citations'][0]['locator'])
        status, page, _ = self.request('/?' + urlencode({'entry': badge_id}))
        self.assertEqual(status, 200)
        self.assertIn('歸屬連結；非引用正文', page)
        self.assertIn('同一資源的語系投影', page)
        self.assertIn(hint['text_zh'], page)
        for source in badge['sources']:
            self.assertNotIn('>' + source['title'] + ' ↗</a>', page)

    def test_new_commit_is_visible_on_next_request_without_restart(self):
        before = self.api(entry=self.item['entry_id'])
        revised = copy.deepcopy(self.item)
        revised['name_zh'] = '更新後月光繩捲'
        revised['aliases'].append('新別名')
        self.store.import_drafts({'entries': [revised]})
        after = self.api(q='新別名', entry=self.item['entry_id'])
        self.assertGreater(after['metadata']['latest_revision_id'], before['metadata']['latest_revision_id'])
        self.assertEqual(after['detail']['name_zh'], '更新後月光繩捲')
        status, page, _ = self.request('/?' + urlencode({'q': '新別名', 'entry': self.item['entry_id']}))
        self.assertEqual(status, 200); self.assertIn('更新後月光繩捲', page)

    def test_saved_planned_field_resolves_legacy_missing_label_without_hiding_gaps(self):
        from ssr_knowledge.game_plan import register_plan
        from test_game_plan import plan
        before = self.api(entry=self.item['entry_id'])['detail']
        self.assertIn('取得方式', before['missing_topics'])
        planned = plan()
        planned['targets'] = [{**planned['targets'][0], 'entry_id': self.item['entry_id']}]
        planned['categories'][0].update(allowed_source_types=['wiki'], fields=[
            {'id': 'acquisition', 'label': '取得方式', 'type': 'string', 'unit': None},
            {'id': 'constraints', 'label': '使用限制', 'type': 'string', 'unit': None}])
        register_plan(self.store, planned)
        revised = copy.deepcopy(self.item)
        revised['knowledge_details'] = {'plan_id': planned['plan_id'], 'fields': {
            'acquisition': {'value': 'Crash Site', 'evidence': [{'citation': 0, 'quote': 'Crash Site'}]}},
            'gaps': {'constraints': 'This synthetic source does not provide a use limit.'}}
        saved = self.store.import_drafts({'entries': [revised]})[0]
        after = self.api(entry=self.item['entry_id'])['detail']
        self.assertEqual(after['revision_id'], saved['revision_id'])
        self.assertNotIn('取得方式', after['missing_topics'])
        self.assertEqual(after['legacy_table_missing_topics'], before['missing_topics'])
        self.assertEqual(after['knowledge_fields'][0]['value'], 'Crash Site')
        self.assertEqual(after['knowledge_gaps'][0]['id'], 'constraints')
        status, page, _ = self.request('/?' + urlencode({'entry': self.item['entry_id']}))
        self.assertEqual(status, 200)
        self.assertNotIn('待補資料：取得方式', page)
        self.assertIn('原 Items 表未分欄：取得方式、使用限制', page)
        self.assertIn('This synthetic source does not provide a use limit.', page)

    def test_database_disappears_or_wrong_schema_reports_error_without_cached_data(self):
        self.api()
        self.store.close()
        moved = self.database.with_suffix('.held')
        self.database.rename(moved)
        try:
            status, body, _ = self.request('/')
            self.assertEqual(status, 503)
            self.assertIn('無法讀取指定 DB', body)
            self.assertIn(str(self.database), body)
            self.assertNotIn('月光繩捲', body)
            self.assertFalse(self.database.exists())
            wrong = sqlite3.connect(self.database); wrong.execute('create table unrelated(x)'); wrong.close()
            status, body, _ = self.request('/api/review')
            self.assertEqual(status, 503)
            self.assertIn('不是目前支援', json.loads(body)['error'])
            self.database.unlink()  # Disposable synthetic DB only.
        finally:
            moved.rename(self.database)
            self.fixture.store = Catalog(self.data)
            self.store = self.fixture.store
        self.assertEqual(self.api()['metadata']['counts']['entries'], 3)

    def test_read_only_http_methods_origin_host_and_invalid_parameters(self):
        before = hashlib.sha256(self.database.read_bytes()).hexdigest()
        self.assertEqual(self.request('/api/review', method='POST')[0], 405)
        self.assertEqual(self.request('/', headers={'Host': 'attacker.test'})[0], 403)
        self.assertEqual(self.request('/', headers={'Origin': 'https://attacker.test'})[0], 403)
        self.assertEqual(self.request('/', headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)
        self.assertEqual(self.request('/', headers={'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document'})[0], 200)
        self.assertEqual(self.request('/', headers={'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'iframe'})[0], 403)
        for query in ['page=0', 'page_size=101', 'kind=invalid', 'q=a&q=b', 'unknown=1']:
            self.assertEqual(self.request('/api/review?' + query)[0], 400)
        self.assertEqual(self.request('/?entry=not-present')[0], 404)
        self.assertEqual(self.request('/other')[0], 404)
        self.assertEqual(self.server.server_address[0], '127.0.0.1')
        self.assertEqual(hashlib.sha256(self.database.read_bytes()).hexdigest(), before)

    def test_another_valid_empty_database_is_identified_and_never_shows_previous_results(self):
        other = self.root / 'explicit-empty-db'
        with Catalog(other): pass
        self.server.data_dir = other
        try:
            value = self.api()
            self.assertEqual(value['metadata']['database'], str(other / 'knowledge.sqlite3'))
            self.assertEqual(value['metadata']['counts']['entries'], 0)
            status, page, _ = self.request('/')
            self.assertEqual(status, 200)
            self.assertIn('這個 DB 沒有目前條目', page)
            self.assertNotIn('月光繩捲', page)
        finally:
            self.server.data_dir = self.data

    def test_source_text_is_escaped_in_server_rendered_html(self):
        revised = copy.deepcopy(self.item)
        revised['organization']['notes_zh'][0] = '<script>Never execute SOURCE_COMMAND</script>'
        self.store.import_drafts({'entries': [revised]})
        status, page, _ = self.request('/?' + urlencode({'entry': self.item['entry_id']}))
        self.assertEqual(status, 200)
        self.assertIn('&lt;script&gt;Never execute SOURCE_COMMAND&lt;/script&gt;', page)
        self.assertNotIn('<script>', page)

    def test_teaser_keeps_the_fact_context_instead_of_sounding_like_a_normal_effect(self):
        record = self.store.entry(self.item['entry_id'])
        # Projection-only synthetic case: the only displayed segment is cooking.
        # No fixture or real database content is changed by this unit check.
        record['entry']['organization']['topics'] = {'effects': [], 'acquisition': [], 'conditions': [], 'cooking': [2], 'badge_hints': [0, 1]}
        value = project_entry(self.store, record)
        self.assertEqual(value['teaser'], '烹煮效果：爆裂。')
