"""Immutable game plans and evidence-bound editorial fields. No acquisition."""
from __future__ import annotations

import json
import math
from datetime import date
from typing import Any

from .catalog import CATEGORIES, SOURCE_TYPES, canonical, digest, identifier, required_text
from .contracts import ContractError
from .store import utc_now


def object_fields(value: Any, fields: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise ContractError(f'{label}: exactly the documented fields required')


def bounded_list(value: Any, label: str, maximum: int = 40) -> list:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise ContractError(f'{label}: bounded nonempty array required')
    return value


def unique_records(values: Any, label: str, key: str = 'id', maximum: int = 40) -> dict:
    records = bounded_list(values, label, maximum)
    ids = [identifier(v.get(key)) if isinstance(v, dict) else identifier(None) for v in records]
    if len(ids) != len(set(ids)):
        raise ContractError(f'{label}: duplicate identifier')
    return dict(zip(ids, records))


def validate_plan(plan: Any) -> dict:
    object_fields(plan, {'format','plan_id','game','analysis','categories','relation_types','targets'}, 'game plan')
    if plan['format'] != 'ssr.game-plan.v1' or plan['game'] != 'PEAK:3527290':
        raise ContractError('unsupported game plan format/game')
    identifier(plan['plan_id'])
    analysis = plan['analysis']
    object_fields(analysis, {'core_loop','structure','basis_url','basis_sections','version_policy','exclusions','questions'}, 'analysis')
    for key in ('core_loop','structure','basis_url','version_policy'):
        required_text(analysis[key], key)
    for key in ('basis_sections','exclusions','questions'):
        for text in bounded_list(analysis[key], key):
            required_text(text, key)
    categories = unique_records(plan['categories'], 'categories')
    if not set(categories) <= CATEGORIES:
        raise ContractError('unsupported planned category')
    for category in categories.values():
        object_fields(category, {'id','label','rationale','allowed_source_types','fields'}, 'category')
        for key in ('label','rationale'):
            required_text(category[key], key)
        sources = bounded_list(category['allowed_source_types'], 'source types', 4)
        if not all(isinstance(s, str) and s in SOURCE_TYPES for s in sources):
            raise ContractError('invalid source types')
        if category['id'] == 'update' and sources != ['official']:
            raise ContractError('official updates require official sources')
        for field in unique_records(category['fields'], 'fields').values():
            object_fields(field, {'id','label','type','unit'}, 'field definition')
            required_text(field['label'], 'field label', 200)
            if field['type'] not in {'string','strings','integer','number','boolean','date'}:
                raise ContractError('unsupported field type')
            if field['unit'] is not None:
                required_text(field['unit'], 'unit', 80)
    for relation in unique_records(plan['relation_types'], 'relation types').values():
        object_fields(relation, {'id','label','from_categories','to_categories'}, 'relation type')
        required_text(relation['label'], 'relation label', 200)
        for key in ('from_categories','to_categories'):
            values = bounded_list(relation[key], key)
            if not all(isinstance(v, str) and v in categories for v in values):
                raise ContractError('relation category outside plan')
    for target in unique_records(plan['targets'], 'targets', 'entry_id', 100).values():
        object_fields(target, {'entry_id','category','name','question','priority','source_url','source_locator','gap_reason'}, 'target')
        if target['category'] not in categories or type(target['priority']) is not int or not 1 <= target['priority'] <= 3:
            raise ContractError('invalid target category/priority')
        for key in ('name','question','source_url','source_locator'):
            required_text(target[key], key)
        if not isinstance(target['gap_reason'], str) or len(target['gap_reason']) > 4000:
            raise ContractError('invalid target gap')
    return plan


def register_plan(store: Any, plan: Any) -> dict:
    validate_plan(plan)
    payload = canonical(plan)
    with store.db:
        store.db.execute('''CREATE TABLE IF NOT EXISTS game_plans (
            plan_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL, created_at TEXT NOT NULL)''')
        old = store.db.execute('SELECT payload_sha256 FROM game_plans WHERE plan_id=?', (plan['plan_id'],)).fetchone()
        if old and old[0] != digest(payload):
            raise ContractError('game plan is immutable; use a new plan_id for changes')
        store.db.execute('INSERT OR IGNORE INTO game_plans VALUES(?,?,?,?)', (plan['plan_id'], payload, digest(payload), utc_now()))
    return {'plan_id': plan['plan_id'], 'sha256': digest(payload), 'state': 'unchanged' if old else 'saved', 'entries_created': 0}


def plans(store: Any) -> list[dict]:
    if not store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='game_plans'").fetchone():
        return []  # Legacy read-only DB remains unchanged.
    result = []
    for row in store.db.execute('SELECT * FROM game_plans ORDER BY plan_id'):
        if digest(row['payload_json']) != row['payload_sha256']:
            raise ContractError('game plan integrity mismatch')
        result.append(validate_plan(json.loads(row['payload_json'])))
    return result


def get_plan(store: Any, plan_id: str) -> dict:
    identifier(plan_id)
    for plan in plans(store):
        if plan['plan_id'] == plan_id:
            return plan
    raise ContractError('register game plan before importing structured knowledge')


def validate_value(value: Any, kind: str) -> None:
    if kind in {'string','date'}:
        required_text(value, 'field value')
        if kind == 'date':
            try:
                if len(value) != 10 or date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            except ValueError as exc:
                raise ContractError('date must be YYYY-MM-DD') from exc
    elif kind == 'strings':
        for text in bounded_list(value, 'field values', 30):
            required_text(text, 'field value')
    elif kind == 'boolean':
        if type(value) is not bool:
            raise ContractError('boolean field required')
    elif kind == 'integer':
        if type(value) is not int or abs(value) > 10**12:
            raise ContractError('bounded integer field required')
    elif kind == 'number' and (type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 10**12):
        raise ContractError('bounded finite number field required')


def validate_evidence(entry: dict, evidence: Any, snapshots: dict, allowed: list) -> None:
    object_fields(evidence, {'citation','quote'}, 'field evidence')
    index = evidence['citation']
    if type(index) is not int or not 0 <= index < len(entry['citations']):
        raise ContractError('field citation out of range')
    snap = snapshots[entry['citations'][index]['snapshot_id']]
    quote = required_text(evidence['quote'], 'field quote', 300)
    if quote not in snap['body'] or snap['source']['source_type'] not in allowed:
        raise ContractError('field evidence differs from pinned text/source class')


def validate_details(store: Any, entry: dict, snapshots: dict) -> None:
    details = entry.get('knowledge_details')
    if details is None:
        if entry['category'] in {'introduction','mode','character','review'} or any(
                t['entry_id'] == entry['entry_id'] for p in plans(store) for t in p['targets']):
            raise ContractError('planned/new category entries require knowledge details')
        return
    object_fields(details, {'plan_id','fields','gaps'}, 'knowledge details')
    plan = get_plan(store, details['plan_id'])
    targets = {t['entry_id']: t for t in plan['targets']}
    if entry['entry_id'] not in targets or targets[entry['entry_id']]['category'] != entry['category']:
        raise ContractError('entry/category does not match planned target')
    category = next(c for c in plan['categories'] if c['id'] == entry['category'])
    fields = {f['id']: f for f in category['fields']}
    values, gaps = details['fields'], details['gaps']
    if (not isinstance(values, dict) or not values or not isinstance(gaps, dict)
            or set(values) & set(gaps) or set(values) | set(gaps) != set(fields)):
        raise ContractError('every planned field needs a value or an explicit gap, never both')
    if entry['evidence_class'] not in category['allowed_source_types']:
        raise ContractError('category source class not allowed')
    for key, field in values.items():
        object_fields(field, {'value','evidence'}, 'knowledge field')
        validate_value(field['value'], fields[key]['type'])
        for evidence in bounded_list(field['evidence'], 'field evidence', 4):
            validate_evidence(entry, evidence, snapshots, category['allowed_source_types'])
    for gap in gaps.values():
        required_text(gap, 'field gap', 800)


def validate_relations(store: Any, entry: dict, lookup: Any, snapshots: dict) -> None:
    links = entry.get('knowledge_links', [])
    if not isinstance(links, list) or len(links) > 30:
        raise ContractError('bounded knowledge links required')
    if not links:
        return
    details = entry.get('knowledge_details')
    if not details:
        raise ContractError('planned relations require knowledge details')
    plan = get_plan(store, details['plan_id'])
    types = {r['id']: r for r in plan['relation_types']}
    category = next(c for c in plan['categories'] if c['id'] == entry['category'])
    seen = set()
    for link in links:
        object_fields(link, {'target_entry_id','kind','citation','evidence_text'}, 'knowledge link')
        identifier(link['target_entry_id'])
        key = (link['kind'], link['target_entry_id'])
        if link['kind'] not in types or key in seen or link['target_entry_id'] == entry['entry_id']:
            raise ContractError('unknown/self/duplicate knowledge relation')
        seen.add(key)
        target, spec = lookup(link['target_entry_id']), types[link['kind']]
        target_details = target.get('knowledge_details')
        if (not isinstance(target_details, dict) or target_details.get('plan_id') != details['plan_id']
                or entry['category'] not in spec['from_categories'] or target.get('category') not in spec['to_categories']):
            raise ContractError('knowledge relation direction/category/plan mismatch')
        validate_evidence(entry, {'citation': link['citation'], 'quote': link['evidence_text']}, snapshots, category['allowed_source_types'])
        # Literal provenance is verified here. Semantic entailment is reviewed by
        # the human; no keyword matcher upgrades this claim to official/game-tested.


def search_text(entry: dict) -> str:
    return ' '.join(str(field['value']) for field in entry.get('knowledge_details', {}).get('fields', {}).values())


def coverage(store: Any) -> list[dict]:
    results = []
    for plan in plans(store):
        targets = []
        for target in plan['targets']:
            row = store.db.execute('SELECT current_revision FROM entries WHERE entry_id=?', (target['entry_id'],)).fetchone()
            record = store.entry(target['entry_id']) if row and row[0] else None
            details = record['entry'].get('knowledge_details', {}) if record else {}
            matches = details.get('plan_id') == plan['plan_id']
            targets.append({**target, 'state': 'knowledge_saved' if matches else 'planned',
                'revision_id': record['revision_id'] if matches else None,
                'review_status': record['status'] if matches else None,
                'stale': record['stale'] if matches else None,
                'field_count': len(details.get('fields', {})) if matches else 0,
                'gaps': details.get('gaps', {}) if matches else {}})
        results.append({'plan_id': plan['plan_id'], 'analysis': plan['analysis'], 'categories': plan['categories'],
            'targets': targets, 'saved_targets': sum(t['state'] == 'knowledge_saved' for t in targets),
            'target_count': len(targets), 'note': 'Knowledge saved is not human acceptance or publication.'})
    return results
