"""Authoritative archive boundary. Producers supply data, never permissions."""
from __future__ import annotations

import base64
import binascii
import codecs
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .acquisition import BodyExtractor, robots_assessment, safe_url, validate_manifest
from .catalog import Catalog, canonical, digest, identifier
from .contracts import ContractError
from .store import utc_now


def export_source_plan(store: Catalog, selected: list[str] | None = None) -> dict[str,Any]:
    sources=[s['config'] for s in store.sources()]
    if selected:
        sources=[s for s in sources if s['source_id'] in selected]
        if {s['source_id'] for s in sources}!=set(selected): raise ContractError('unknown selected source')
    return {'format':'ssr.source-plan.v1','game':'PEAK:3527290','created_at':utc_now(),
        'selected_acquisition_route':'computer_use_or_permitted_local_file','http_is_optional':True,
        'registry_sha256':digest(canonical(sources)),'sources':sources,
        'note':'Read-only snapshot of the central registry; not a new permission grant or a knowledge-entry export.'}


def validate_file_source(value: Any) -> dict[str,Any]:
    fields={'source_id','url','original_url','source_type','title','language','declared_version','selector','policy','interval_seconds','acquisition'}
    if not isinstance(value,dict) or set(value)!=fields: raise ContractError('file source requires exactly the documented fields')
    identifier(value['source_id'])
    if value['url']!='approved-file:'+value['source_id'] or value['acquisition']!={'kind':'approved_local_file'}:
        raise ContractError('file permission is a separate acquisition source; never enables direct HTTP')
    policy=value['policy']
    if (not isinstance(policy,dict) or type(policy.get('allow_import')) is not bool or policy.get('allow_fetch') is not False):
        raise ContractError('file source needs explicit allow_import and allow_fetch=false')
    # Reuse the local central policy validator without creating a network request.
    network_form={k:v for k,v in value.items() if k!='acquisition'}
    network_form.update(url=value['original_url'],original_url=value['original_url'])
    network_form['policy']={k:v for k,v in policy.items() if k!='allow_import'}
    validate_manifest({'manifest_version':1,'game':'PEAK:3527290','sources':[network_form]})
    return value


def register_file_source(store: Catalog, value: Any) -> dict[str,Any]:
    source=validate_file_source(value)
    store.register_source(source)
    store.event(source['source_id'],'file_source_policy_registration',{'url':source['original_url'],'network_requests':0})
    return {'source_id':source['source_id'],'registered':True,'network_requests':0,'entries_created':0}


def _time(value: Any) -> datetime:
    try:
        at=datetime.fromisoformat(value)
        if at.tzinfo is None or (at-datetime.now(timezone.utc)).total_seconds()>60: raise ValueError
        return at
    except (TypeError,ValueError) as exc: raise ContractError('invalid or future acquisition timestamp') from exc


def validate_bundle(store: Catalog, packet: Any) -> tuple[dict[str,Any],bytes,str,dict[str,Any]]:
    if (not isinstance(packet,dict) or set(packet)!={'format','producer','source_ref','document','bundle_id'}
            or packet['format']!='ssr.collection.v1'):
        raise ContractError('unsupported collection packet; no entries, review or permission fields accepted')
    if not isinstance(packet['producer'],str) or not re.fullmatch(r'[a-z][a-z0-9-]{1,79}/[0-9]+\.[0-9]+\.[0-9]+',packet['producer']):
        raise ContractError('bounded producer name/semantic-version required; identity is not permission')
    if packet['bundle_id']!=digest(canonical({k:v for k,v in packet.items() if k!='bundle_id'})):
        raise ContractError('bundle hash mismatch')
    ref=packet['source_ref']
    if not isinstance(ref,dict) or set(ref)!={'source_id','config_sha256'}: raise ContractError('source reference only; policy belongs to central registry')
    identifier(ref['source_id'])
    row=store.db.execute('SELECT config_json FROM sources WHERE source_id=?',(ref['source_id'],)).fetchone()
    if row is None: raise ContractError('source not registered centrally')
    source=json.loads(row[0])
    if digest(canonical(source))!=ref['config_sha256']: raise ContractError('central source policy changed; obtain a new source plan')
    doc=packet['document']
    fields={'url','captured_at','observed_at','raw_base64','raw_sha256','body','body_sha256','metadata'}
    if not isinstance(doc,dict) or set(doc)!=fields or doc['url']!=source['url']: raise ContractError('document URL differs from registered source')
    captured,observed=_time(doc['captured_at']),_time(doc['observed_at'])
    if observed<captured: raise ContractError('observation predates capture')
    if not isinstance(doc['raw_base64'],str) or len(doc['raw_base64'])>2_666_672: raise ContractError('raw payload exceeds 2 MB limit')
    try: raw=base64.b64decode(doc['raw_base64'],validate=True)
    except (binascii.Error,ValueError) as exc: raise ContractError('invalid base64 payload') from exc
    body=doc['body']; meta=doc['metadata']
    if (not 40<=len(raw)<=2_000_000 or not isinstance(body,str) or not 40<=len(body)<=2_000_000
            or digest(raw)!=doc['raw_sha256'] or digest(body)!=doc['body_sha256']): raise ContractError('raw/body bounds or hash mismatch')
    if not isinstance(meta,dict) or {'policy','uses','allow_fetch','allow_import','review','published_at'} & set(meta):
        raise ContractError('producer cannot supply authoritative policy or review state')
    if meta.get('collector_called_llm') is not False or meta.get('purpose')!='local_cache':
        raise ContractError('this boundary archives local-cache observations, not generated knowledge')
    policy=source['policy']
    if policy.get('uses',{}).get('local_cache',{}).get('status')!='allowed':
        raise ContractError('central local_cache purpose not allowed; unknown remains unknown')
    kind=meta.get('acquisition_kind')
    if kind=='approved_local_file':
        validate_file_source(source)
        if policy.get('allow_import') is not True or meta.get('http_requests')!=0:
            raise ContractError('local-file source is not enabled or falsely claims HTTP')
        if meta.get('acquisition_method') not in {'operator_file','synthetic_fixture'}:
            raise ContractError('unverified browser acquisition claim')
        if 'capture_receipt' in meta:
            from .capture_receipt import validate_capture_receipt
            if meta.get('acquisition_method') != 'operator_file' or meta.get('body_format') != 'html':
                raise ContractError('DOM observation requires operator_file HTML')
            validate_capture_receipt(meta['capture_receipt'],source,raw)
            if meta['capture_receipt']['captured_at'] != doc['captured_at']:
                raise ContractError('DOM capture time differs from packet capture time')
        text=raw.decode('utf-8-sig',errors='strict')
        if '\x00' in text: raise ContractError('NUL in text input')
        if meta.get('body_format')=='plain_text': extracted=text
        elif meta.get('body_format')=='html':
            parser=BodyExtractor(source['selector']); parser.feed(text); parser.close(); extracted=parser.body()
        else: raise ContractError('unknown local file format')
    elif kind=='http_collection':
        if source.get('acquisition') or policy.get('allow_fetch') is not True: raise ContractError('central source does not permit HTTP acquisition')
        validate_manifest({'manifest_version':1,'game':'PEAK:3527290','sources':[source]})
        if meta.get('http_status')!=200: raise ContractError('packet is not a successful HTTP document')
        if meta.get('robots_http_status')==200:
            text=meta.get('robots_text')
            if not isinstance(text,str) or not robots_assessment(text,source['url'])['allowed']:
                raise ContractError('saved robots do not allow this acquisition')
        elif meta.get('robots_http_status') not in {404,410}: raise ContractError('robots result unknown or denied')
        content_type=meta.get('headers',{}).get('content-type','')
        if 'text/html' not in content_type.lower(): raise ContractError('HTTP body must be HTML')
        match=re.search(r'charset=([\w-]+)',content_type,re.I); encoding=match[1] if match else 'utf-8'
        codecs.lookup(encoding)
        parser=BodyExtractor(source['selector']); parser.feed(raw.decode(encoding,errors='strict')); parser.close(); extracted=parser.body()
    else: raise ContractError('unsupported acquisition kind')
    if extracted!=body: raise ContractError('body differs from central re-extraction of raw input')
    return source,raw,body,meta


def ingest_collection(store: Catalog, file: str, *, apply: bool=False) -> dict[str,Any]:
    path=Path(file)
    if not path.is_file() or path.stat().st_size>6_000_000: raise ContractError('bounded collection JSON file required')
    packet=json.loads(path.read_text(encoding='utf-8-sig'))
    source,raw,body,meta=validate_bundle(store,packet)
    result={'bundle_id':packet['bundle_id'],'source_id':source['source_id'],'entries_created':0,'review_changed':False,'network_requests':0}
    if not apply: return {**result,'state':'validated_only','archive_changed':False}
    cfg=canonical(source); sid=digest(source['url']+'\0'+digest(raw)+'\0'+digest(cfg)); doc=packet['document']
    with store.db:
        store.db.execute('BEGIN IMMEDIATE')
        current=store.db.execute('SELECT config_json,latest_snapshot FROM sources WHERE source_id=?',(source['source_id'],)).fetchone()
        if current['config_json']!=cfg: raise ContractError('central registry changed during ingestion')
        store.db.execute('''CREATE TABLE IF NOT EXISTS collection_receipts(
            bundle_id TEXT PRIMARY KEY,source_id TEXT NOT NULL,snapshot_id TEXT NOT NULL,
            observed_at TEXT NOT NULL,producer TEXT NOT NULL,imported_at TEXT NOT NULL)''')
        old=store.db.execute('SELECT snapshot_id FROM collection_receipts WHERE bundle_id=?',(packet['bundle_id'],)).fetchone()
        if old: return {**result,'snapshot_id':old[0],'state':'unchanged','archive_changed':False}
        exists=store.db.execute('SELECT 1 FROM snapshots WHERE snapshot_id=?',(sid,)).fetchone() is not None
        metadata={**meta,'bundle_id':packet['bundle_id'],'producer':packet['producer'],'observed_at':doc['observed_at'],
                  'archive_imported_at':utc_now(),'policy_authority':'central sources table; producer hash is not authentication'}
        store.db.execute('INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?,?,?,?,?,?)',
            (sid,source['source_id'],doc['captured_at'],raw,digest(raw),body,digest(body),canonical(metadata),cfg))
        previous=store.db.execute('SELECT fetched_at FROM snapshots WHERE snapshot_id=?',(current['latest_snapshot'],)).fetchone()
        latest_receipt=store.db.execute('SELECT max(observed_at) FROM collection_receipts WHERE source_id=?',(source['source_id'],)).fetchone()[0]
        cutoff=max([_time(t) for t in [previous[0] if previous else None,latest_receipt] if t is not None],default=None)
        historical=cutoff is not None and _time(doc['observed_at'])<cutoff
        if not historical:
            store.db.execute('UPDATE sources SET latest_snapshot=? WHERE source_id=?',(sid,source['source_id']))
            store.db.execute("INSERT INTO events(at,source_id,event,details_json) VALUES(?,?,'collection_result',?)",
                (utc_now(),source['source_id'],canonical({**metadata,'url':source['url'],'state':'unchanged' if exists else 'saved','snapshot_id':sid})))
        store.db.execute('INSERT INTO collection_receipts VALUES(?,?,?,?,?,?)',
            (packet['bundle_id'],source['source_id'],sid,doc['observed_at'],packet['producer'],utc_now()))
    return {**result,'snapshot_id':sid,'state':'saved_historical' if historical else 'unchanged' if exists else 'saved','archive_changed':True}
