"""Synthetic evidence and DB behavior; never real-game or human acceptance."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ssr_knowledge.catalog import Catalog
from ssr_knowledge.contracts import ContractError
from ssr_knowledge.game_plan import coverage, register_plan, validate_plan
from ssr_knowledge.live_review import load_model, query_options
from ssr_knowledge.live_review_html import render_page
from test_catalog import BODY, seed


def plan():
    return {'format':'ssr.game-plan.v1','plan_id':'synthetic-plan-v1','game':'PEAK:3527290',
        'analysis':{'core_loop':'Fictional climbing','structure':'Question-driven fixture','basis_url':'https://example.test',
            'basis_sections':['fixture'],'version_policy':'Synthetic only','exclusions':['No real content'],'questions':['How?']},
        'categories':[{'id':category,'label':category,'rationale':'Synthetic question',
            'allowed_source_types':['official'], 'fields':[{'id':'rule','label':'規則','type':'string','unit':None},
                {'id':'count','label':'數量','type':'integer','unit':'人'}]} for category in ['item','mechanic','update']],
        'relation_types':[{'id':'uses_mechanic','label':'使用機制','from_categories':['item'],'to_categories':['mechanic']}],
        'targets':[{'entry_id':id,'category':category,'name':id,'question':'Synthetic question?','priority':1,
            'source_url':'https://example.test','source_locator':'fixture','gap_reason':''}
            for id,category in [('fixture-lunar-rope','item'),('fixture-rule','mechanic'),('fixture-update','update')]]}


class GamePlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)/'data'
        self.store = Catalog(self.data); self.addCleanup(self.store.close)
        self.source, self.draft = seed(self.store)
        self.plan = plan()
        register_plan(self.store, self.plan)
        self.draft['knowledge_details'] = {'plan_id':self.plan['plan_id'],
            'fields':{'rule':{'value':'Testable blue platform','evidence':[{'citation':0,'quote':'It makes a blue landing platform.'}]}},
            'gaps':{'count':'Source does not state a number.'}}

    def other(self):
        other = copy.deepcopy(self.draft)
        other.pop('knowledge_links', None)
        other.update(entry_id='fixture-rule', category='mechanic', name_en='Fixture rule',name_zh='合成規則')
        return other

    def links(self):
        self.draft['knowledge_links']=[{'kind':'uses_mechanic','target_entry_id':'fixture-rule',
            'citation':0,'evidence_text':'It makes a blue landing platform.'}]

    def test_plan_immutable_and_no_knowledge_side_effect(self):
        self.assertEqual(register_plan(self.store,self.plan)['state'],'unchanged')
        changed=copy.deepcopy(self.plan); changed['analysis']['core_loop']='Changed'
        with self.assertRaisesRegex(ContractError,'immutable'): register_plan(self.store,changed)
        self.assertEqual(coverage(self.store)[0]['saved_targets'],0)
        self.assertEqual(self.store.stats()['counts']['entries'],0)

    def test_typed_fields_gaps_and_evidence_reject_before_write(self):
        cases=[]
        bad=copy.deepcopy(self.draft);bad['knowledge_details']['plan_id']='missing-plan';cases.append(bad)
        bad=copy.deepcopy(self.draft);bad['knowledge_details']['gaps']={};cases.append(bad)
        bad=copy.deepcopy(self.draft);bad['knowledge_details']['fields']['rule']['evidence'][0]['quote']='invented';cases.append(bad)
        bad=copy.deepcopy(self.draft);bad['knowledge_details']['fields']['count']={'value':True,'evidence':[{'citation':0,'quote':BODY}]};bad['knowledge_details']['gaps']={};cases.append(bad)
        bad=copy.deepcopy(self.draft);bad['knowledge_details']['fields']['rule']['evidence'][0]['citation']=-1;cases.append(bad)
        for bad in cases:
            with self.subTest(bad=bad), self.assertRaises(ContractError): self.store.import_drafts({'entries':[bad]})
        self.assertEqual(self.store.stats()['counts']['entries'],0)

    def test_forward_relation_atomic_batch_and_query(self):
        self.links()
        results=self.store.import_drafts({'entries':[self.draft,self.other()]})
        self.assertEqual(len(results),2)
        self.assertEqual(self.store.relations('fixture-rule')['relations'][0]['direction'],'incoming')
        self.assertEqual(self.store.relations('fixture-rule')['relations'][0]['evidence_state'],'planned_editorial_claim')
        self.assertEqual(self.store.search('Testable blue',preview=True)['total_matches'],2)
        self.assertEqual(self.store.search('Testable blue')['total_matches'],0)
        self.assertEqual(coverage(self.store)[0]['saved_targets'],2)

    def test_invalid_target_rolls_back_entire_batch(self):
        self.links(); other=self.other();other['knowledge_details']['fields']['rule']['evidence'][0]['quote']='invalid'
        with self.assertRaises(ContractError):self.store.import_drafts({'entries':[self.draft,other]})
        self.assertEqual(self.store.stats()['counts']['entries'],0)
        self.assertEqual(self.store.stats()['counts']['entry_relations'],0)

    def test_dangling_reversed_and_self_links_rejected(self):
        self.links()
        with self.assertRaises(ContractError):self.store.import_drafts({'entries':[self.draft]})
        other=self.other();other['category']='item'
        with self.assertRaises(ContractError):self.store.import_drafts({'entries':[self.draft,other]})
        self.draft['knowledge_links'][0]['target_entry_id']=self.draft['entry_id']
        with self.assertRaises(ContractError):self.store.import_drafts({'entries':[self.draft]})

    def test_official_updates_cannot_use_wiki(self):
        bad=copy.deepcopy(self.plan);bad['categories'][2]['allowed_source_types']=['wiki']
        with self.assertRaisesRegex(ContractError,'official'):validate_plan(bad)
        wiki=copy.deepcopy(self.source);wiki.update(source_id='wiki-fixture',url='https://example.test/wiki',source_type='wiki')
        self.store.register_source(wiki);snap=self.store.save_snapshot(wiki,BODY.encode(),BODY,{'fixture_only':True})
        draft=copy.deepcopy(self.draft);draft.update(entry_id='fixture-update',category='update',evidence_class='wiki')
        draft['citations'][0]['snapshot_id']=snap['snapshot_id']
        with self.assertRaisesRegex(ContractError,'source class'):self.store.import_drafts({'entries':[draft]})

    def test_target_cannot_silently_break_existing_incoming_relations(self):
        self.links(); self.store.import_drafts({'entries':[self.draft,self.other()]})
        new_plan=copy.deepcopy(self.plan);new_plan['plan_id']='synthetic-plan-v2'
        register_plan(self.store,new_plan)
        other=self.other();other['knowledge_details']['plan_id']=new_plan['plan_id']
        with self.assertRaisesRegex(ContractError,'mismatch'):self.store.import_drafts({'entries':[other]})
        self.assertEqual(self.store.entry('fixture-rule')['entry']['knowledge_details']['plan_id'],self.plan['plan_id'])

    def test_current_revision_and_read_only_ui_show_actual_db_fields(self):
        self.links();self.store.import_drafts({'entries':[self.draft,self.other()]})
        self.assertEqual(load_model(self.data,query_options('category=mechanic'))['total_matches'],1)
        old=load_model(self.data,query_options('entry=fixture-lunar-rope'))
        self.draft['knowledge_details']['fields']['rule']['value']='<script>Changed pending text</script>'
        new=self.store.import_drafts({'entries':[self.draft]})[0]
        before=hashlib.sha256((self.data/'knowledge.sqlite3').read_bytes()).hexdigest()
        model=load_model(self.data,query_options('entry=fixture-lunar-rope'))
        self.assertNotEqual(old['detail']['revision_id'],model['detail']['revision_id'])
        self.assertEqual(model['detail']['revision_id'],new['revision_id'])
        self.assertEqual(model['detail']['knowledge_fields'][0]['value'],self.draft['knowledge_details']['fields']['rule']['value'])
        html=render_page(model)
        self.assertIn('&lt;script&gt;Changed pending text&lt;/script&gt;',html)
        self.assertIn('本條目 → 使用機制',html)
        self.assertIn('明確缺漏',html)
        self.assertEqual(before,hashlib.sha256((self.data/'knowledge.sqlite3').read_bytes()).hexdigest())
        read=subprocess.run([sys.executable,'-m','ssr_knowledge','catalog','--data-dir',str(self.data),'entry','--entry-id','fixture-lunar-rope'],capture_output=True,encoding='utf-8',check=True)
        self.assertEqual(json.loads(read.stdout)['revision_id'],new['revision_id'])

    def test_reading_legacy_db_does_not_add_plan_table(self):
        data=Path(self.temp.name)/'legacy'
        with Catalog(data):pass
        before=(data/'knowledge.sqlite3').read_bytes()
        model=load_model(data,query_options(''))
        self.assertEqual(model['plans'],[])
        self.assertEqual(before,(data/'knowledge.sqlite3').read_bytes())

    def test_idempotence_and_old_revision_do_not_revert_head(self):
        original=copy.deepcopy(self.draft)
        first=self.store.import_drafts({'entries':[original]})[0]
        self.draft['knowledge_details']['fields']['rule']['value']='Revised blue platform'
        second=self.store.import_drafts({'entries':[self.draft]})[0]
        again=self.store.import_drafts({'entries':[original]})[0]
        self.assertEqual(again['revision_id'],first['revision_id'])
        self.assertEqual(self.store.entry(original['entry_id'])['revision_id'],second['revision_id'])
        self.assertEqual(coverage(self.store)[0]['targets'][0]['revision_id'],second['revision_id'])


if __name__=='__main__':unittest.main()
