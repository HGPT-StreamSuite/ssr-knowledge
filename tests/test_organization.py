"""Synthetic editorial notes and badges only; approvals are test simulations."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ssr_knowledge.catalog import Catalog
from ssr_knowledge.contracts import ContractError
from ssr_knowledge.game_extraction import import_game_text
from ssr_knowledge.organization import TOPICS, badge_drafts, cached_badges
from ssr_knowledge.review_page import render_review
from ssr_knowledge.upload_source import import_text_source
from test_game_names import receipt as game_receipt
import test_item_upload as item_fixture
from test_item_upload import TEXT, receipt

CSV = 'CURRENT_LANGUAGE,English,简体中文,繁體中文,ENDLINE\r\nNAME_FICTIONAL,FICTIONAL BADGE,虚构徽章,虛構徽章,ENDLINE\r\nDESC_FICTIONAL,Use Lunar Spool.,使用月光绳卷。,使用月光繩捲。,ENDLINE\r\n'


class OrganizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Catalog(self.root / 'data')
        text = self.root / 'items.txt'; text.write_text(TEXT, encoding='utf-8')
        snap = import_text_source(self.store, str(text), receipt())['snapshot_id']
        self.item = item_fixture.ItemUploadTests.draft(SimpleNamespace(store=self.store), snap)
        self.item['organization'] = {'schema_version': 1, 'method': 'agent_edited_pending_review',
            'source_row_sha256': self.item['item_details']['source_row_sha256'],
            'topics': {'effects': [0], 'acquisition': [], 'conditions': [], 'cooking': [2], 'badge_hints': [1]},
            'notes_zh': self.item['item_details']['notes_zh'][:]}
        self.store.import_drafts({'entries': [self.item]})
        game = self.root / 'game.csv'; game.write_bytes(CSV.encode())
        saved = import_game_text(self.store, str(game), game_receipt(game.read_bytes()))['results']
        self.en, self.tw = saved['en']['snapshot_id'], saved['zh-TW']['snapshot_id']
        self.badge = badge_drafts(self.store, self.en, self.tw)['entries'][0]
        self.badge['links'] = [{'target_entry_id': self.item['entry_id'], 'kind': 'condition_mentions_item',
                               'citation': 0, 'note_index': None, 'evidence_text': 'Lunar Spool'}]
        self.store.import_drafts({'entries': [self.badge]})
        self.item['links'] = [{'target_entry_id': self.badge['entry_id'], 'kind': 'badge_hint', 'citation': 0,
                              'note_index': 1, 'evidence_text': self.item['item_details']['notes_en'][1]}]

    def tearDown(self):
        self.store.close(); self.temp.cleanup()

    def test_organization_covers_pinned_notes_without_rewriting_na_or_zero(self):
        before = copy.deepcopy(self.item['item_details'])
        self.store.import_drafts({'entries': [self.item]})
        after = self.store.entry(self.item['entry_id'])['entry']
        self.assertEqual(after['item_details'], before)
        self.assertEqual(after['item_details']['statistics']['hunger']['state'], 'source_na')
        self.assertEqual(after['item_details']['statistics']['bonus_stamina']['value'], 0)
        for mode in ('missing', 'duplicate', 'out_of_range', 'row', 'extra'):
            bad = copy.deepcopy(self.item)
            if mode == 'missing': bad['organization']['topics']['effects'] = []
            if mode == 'duplicate': bad['organization']['topics']['conditions'] = [0]
            if mode == 'out_of_range': bad['organization']['topics']['effects'] = [99]
            if mode == 'row': bad['organization']['source_row_sha256'] = '0' * 64
            if mode == 'extra': bad['organization']['notes_zh'].append('invented')
            with self.subTest(mode=mode), self.assertRaises(ContractError): self.store.import_drafts({'entries': [bad]})

    def test_badge_conditions_are_pinned_to_exact_key_and_traditional_column(self):
        for change in ({'condition_zh': '使用月光绳卷。'}, {'condition_en': 'Invented unlock rule'},
                       {'description_key': 'DESC_OTHER'}, {'steam_equivalence': 'confirmed'}, {'player_progress': 1}):
            bad = copy.deepcopy(self.badge); bad['badge_details'].update(change)
            with self.subTest(change=change), self.assertRaises(ContractError): self.store.import_drafts({'entries': [bad]})
        self.assertEqual(len(cached_badges(CSV.encode())), 1)
        # Another locale's duplicate spelling cannot override the selected TW
        # column. Unrelated action keys also do not define badge identities.
        repeated = CSV + 'DESC_FICTIONAL,Use Lunar Spool.,简中不同,使用月光繩捲。,ENDLINE\r\n'
        self.assertEqual(len(cached_badges(repeated.encode())), 1)
        for raw in (CSV.replace('DESC_FICTIONAL', 'DESC_OTHER'), CSV + 'NAME_FICTIONAL,OTHER BADGE,甲,乙,ENDLINE\r\n'):
            with self.assertRaises(ContractError): cached_badges(raw.encode())

    def test_links_require_literal_evidence_and_known_matching_categories(self):
        for field, value in (('target_entry_id', 'absent'), ('note_index', 0), ('citation', 99), ('evidence_text', 'fabricated')):
            bad = copy.deepcopy(self.item); bad['links'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ContractError): self.store.import_drafts({'entries': [bad]})
        bad = copy.deepcopy(self.badge); bad['links'][0]['evidence_text'] = 'Use'
        with self.assertRaises(ContractError): self.store.import_drafts({'entries': [bad]})

    def test_relation_dedup_current_revision_and_reopen(self):
        saved = self.store.import_drafts({'entries': [self.item]})[0]
        again = self.store.import_drafts({'entries': [self.item]})[0]
        self.assertEqual((saved['revision_id'], again['revision_id'], again['state']), (saved['revision_id'], saved['revision_id'], 'unchanged'))
        self.assertEqual(len(self.store.relations(self.badge['entry_id'])['relations']), 2)
        self.store.close(); self.store = Catalog(self.root / 'data')
        self.assertEqual(len(self.store.relations(self.badge['entry_id'])['relations']), 2)
        newer = copy.deepcopy(self.item); newer['links'] = []
        self.store.import_drafts({'entries': [newer]})
        self.assertEqual(len(self.store.relations(self.badge['entry_id'])['relations']), 1)
        self.assertEqual(self.store.db.execute('select count(*) from entry_relations').fetchone()[0], 2)

    def test_published_search_does_not_reveal_linked_pending_or_rejected_id(self):
        rev = self.store.import_drafts({'entries': [self.item]})[0]['revision_id']
        self.store.review(self.item['entry_id'], rev, 'approve', 'synthetic-human', 'Fixture simulation only', True)
        self.store.publish(self.item['entry_id'], rev)
        for rejected in (False, True):
            if rejected:
                badge = self.store.entry(self.badge['entry_id'])
                self.store.review(self.badge['entry_id'], badge['revision_id'], 'reject', 'synthetic-human', 'Fixture rejection', True)
            formal = self.store.search('Lunar Spool')
            self.assertEqual(formal['total_matches'], 1)
            self.assertNotIn('links', formal['matches'][0]['entry'])
            self.assertNotIn(self.badge['entry_id'], json.dumps(formal))
            self.assertEqual(self.store.search('虛構徽章')['total_matches'], 0)

    def test_content_first_preview_keeps_audit_fields_out_and_source_text_inert(self):
        self.store.import_drafts({'entries': [self.item]})
        result = render_review(self.store, str(self.root / 'review.html'))
        text = (self.root / 'review.html').read_text(encoding='utf-8')
        self.assertEqual((result['items'], result['game_badges']), (1, 1))
        self.assertIn('待補資料：取得方式、使用限制', text)
        self.assertIn('虛構徽章', text)
        for forbidden in ('SHA-256', self.item['entry_id'], self.item['item_details']['source_row_sha256'], '字面規則', '不能推定'):
            self.assertNotIn(forbidden, text)
        self.assertIn('SOURCE_COMMAND', text)
        self.assertIn('來源標示 n/a（含義未確認）', text)
        self.assertIn('額外耐力：0', text)
        bad = copy.deepcopy(self.item)
        bad['detail_page'] = {'url': 'javascript:alert(1)', 'status': 'verified', 'basis': 'bad', 'checked_at': 'now', 'http_status': 200}
        with self.assertRaises(ContractError): self.store.import_drafts({'entries': [bad]})
