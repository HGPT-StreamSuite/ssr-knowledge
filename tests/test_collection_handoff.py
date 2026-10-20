"""Synthetic packets and policies only; no collector-repo import or real sources."""
import base64
import copy
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

from ssr_knowledge.catalog import Catalog,canonical,digest
from ssr_knowledge.collection_handoff import export_source_plan,ingest_collection,register_file_source
from ssr_knowledge.contracts import ContractError
from ssr_knowledge.store import utc_now
from test_catalog import source,seed,BODY

TEXT='Synthetic fictional Lunar Rope. SOURCE_COMMAND is inert text and no real PEAK material is used.'


def file_source():
    cfg=source(); cfg.update(source_id='synthetic-export',url='approved-file:synthetic-export',
        original_url='https://example.test/authorized-export',acquisition={'kind':'approved_local_file'})
    cfg['policy'].update(allow_fetch=False,allow_import=True)
    return cfg


def packet(cfg,text=TEXT,at=None):
    raw=text.encode('utf-8'); at=at or utc_now()
    value={'format':'ssr.collection.v1','producer':'ssr-collector-peak/0.1.0',
        'source_ref':{'source_id':cfg['source_id'],'config_sha256':digest(canonical(cfg))},
        'document':{'url':cfg['url'],'captured_at':at,'observed_at':at,'raw_base64':base64.b64encode(raw).decode(),
            'raw_sha256':digest(raw),'body':text,'body_sha256':digest(text),'metadata':{
                'acquisition_kind':'approved_local_file','acquisition_method':'synthetic_fixture','body_format':'plain_text',
                'http_requests':0,'purpose':'local_cache','collector_called_llm':False}}}
    return rehash(value)


def rehash(value):
    value['bundle_id']=digest(canonical({k:v for k,v in value.items() if k!='bundle_id'})); return value


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.data=self.root/'archive'; self.store=Catalog(self.data); self.cfg=file_source()
        register_file_source(self.store,self.cfg)
        self.bundle=self.root/'packet.json'

    def tearDown(self): self.store.close(); self.temp.cleanup()

    def write(self,value):
        self.bundle.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8'); return str(self.bundle)

    def test_readonly_source_export_and_default_validation_do_not_write(self):
        before=(self.data/'knowledge.sqlite3').read_bytes()
        plan=export_source_plan(self.store)
        self.assertEqual(plan['format'],'ssr.source-plan.v1')
        self.assertEqual(plan['sources'],[self.cfg])
        self.assertNotIn('entries',plan)
        value=packet(self.cfg); self.write(value)
        command=[sys.executable,'-m','ssr_knowledge','catalog','--data-dir',str(self.data)]
        for args in [['export-source-plan'],['ingest-collection','--file',str(self.bundle)]]:
            result=subprocess.run([*command,*args],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual((self.data/'knowledge.sqlite3').read_bytes(),before)
        self.assertEqual(self.store.db.execute("select count(*) from sqlite_master where name='collection_receipts'").fetchone()[0],0)

    def test_archive_only_dedup_new_process_readback_and_no_knowledge(self):
        first=ingest_collection(self.store,self.write(packet(self.cfg)),apply=True)
        self.assertEqual(first['state'],'saved')
        second=ingest_collection(self.store,str(self.bundle),apply=True)
        self.assertEqual(second['state'],'unchanged')
        self.assertEqual(self.store.stats()['counts']['entries'],0)
        self.assertEqual(self.store.stats()['counts']['entry_revisions'],0)
        self.assertEqual(self.store.search('Synthetic')['matches'],[])
        with Catalog(self.data,read_only=True) as reader:
            snap=reader.snapshot(first['snapshot_id'],True)
            self.assertEqual(snap['body'],TEXT)
            self.assertEqual(snap['metadata']['acquisition_kind'],'approved_local_file')
            self.assertEqual(reader.db.execute('select count(*) from collection_receipts').fetchone()[0],1)

    def test_permission_policy_or_review_cannot_be_supplied_by_packet(self):
        for mode in ['policy','body','raw','review','source','hash','method']:
            value=packet(self.cfg)
            if mode=='policy': value['document']['metadata']['policy']={'allow_fetch':True}
            if mode=='body': value['document']['body']+=' invented'; value['document']['body_sha256']=digest(value['document']['body'])
            if mode=='raw': value['document']['raw_base64']='!invalid'
            if mode=='review': value['approved']=True
            if mode=='source': value['source_ref']['source_id']='unknown-source'
            if mode=='hash': value['source_ref']['config_sha256']='0'*64
            if mode=='method': value['document']['metadata']['acquisition_method']='browser_fetch_succeeded'
            rehash(value)
            with self.subTest(mode=mode),self.assertRaises(ContractError):
                ingest_collection(self.store,self.write(value),apply=True)
        self.assertEqual(self.store.db.execute('select count(*) from snapshots').fetchone()[0],0)

    def test_unknown_prohibited_and_revoked_purposes_remain_blocked(self):
        for status in ['unknown','prohibited']:
            cfg=copy.deepcopy(self.cfg); cfg['policy']['uses']['local_cache']['status']=status
            register_file_source(self.store,cfg)
            with self.subTest(status=status),self.assertRaises(ContractError):
                ingest_collection(self.store,self.write(packet(cfg)),apply=True)
        register_file_source(self.store,self.cfg); original=packet(self.cfg)
        ingest_collection(self.store,self.write(original),apply=True)
        changed=copy.deepcopy(self.cfg); changed['policy']['allow_import']=False
        register_file_source(self.store,changed)
        with self.assertRaises(ContractError): ingest_collection(self.store,self.write(original),apply=True)
        with self.assertRaises(ContractError): ingest_collection(self.store,self.write(packet(changed)),apply=True)

    def test_old_bundle_does_not_roll_back_latest_snapshot(self):
        first=packet(self.cfg,at=(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat())
        one=ingest_collection(self.store,self.write(first),apply=True)
        second=packet(self.cfg,TEXT+' A second synthetic revision.',at=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat())
        two=ingest_collection(self.store,self.write(second),apply=True)
        self.assertNotEqual(one['snapshot_id'],two['snapshot_id'])
        ingest_collection(self.store,self.write(first),apply=True)
        self.assertEqual(self.store.sources()[0]['latest']['snapshot_id'],two['snapshot_id'])

    def test_archive_transaction_rollback_has_no_partial_document(self):
        self.store.db.executescript('''CREATE TABLE collection_receipts(bundle_id TEXT PRIMARY KEY,source_id TEXT,snapshot_id TEXT,observed_at TEXT,producer TEXT,imported_at TEXT);
            CREATE TRIGGER synthetic_reject_receipt BEFORE INSERT ON collection_receipts BEGIN SELECT RAISE(ABORT,'fixture abort'); END;''')
        with self.assertRaises(sqlite3.IntegrityError):
            ingest_collection(self.store,self.write(packet(self.cfg)),apply=True)
        self.assertEqual(self.store.db.execute('select count(*) from snapshots').fetchone()[0],0)
        self.assertIsNone(self.store.sources()[0]['latest'])

    def test_http_is_optional_and_search_no_remains_enforced(self):
        cfg,draft=seed(self.store)
        text=BODY+' Updated synthetic evidence.'; raw=('<main>'+text+'</main>').encode()
        value=packet(cfg,text)
        value['document'].update(raw_base64=base64.b64encode(raw).decode(),raw_sha256=digest(raw))
        value['document']['metadata']={'acquisition_kind':'http_collection','purpose':'local_cache','collector_called_llm':False,
            'http_status':200,'robots_http_status':200,'robots_text':'User-agent: *\nAllow: /\nContent-Signal: search=no\n',
            'headers':{'content-type':'text/html; charset=utf-8'}}
        result=ingest_collection(self.store,self.write(rehash(value)),apply=True)
        draft['citations'][0]['snapshot_id']=result['snapshot_id']
        revision=self.store.import_drafts({'entries':[draft]})[0]['revision_id']
        self.store.review(draft['entry_id'],revision,'approve','synthetic-human','Fixture simulation only.',True)
        self.store.publish(draft['entry_id'],revision)
        self.assertEqual(self.store.search('Lunar Rope')['matches'],[])
