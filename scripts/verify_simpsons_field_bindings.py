"""Read-only, bounded technical checks of the Simpsons draft's unresolved fields.

No source documents, credentials or identifier values are exported. This is
technical evidence, never business approval or permission to publish a draft.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from itertools import islice
import os
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from cryptography.fernet import Fernet
from scripts.integration_config import load_env
from workflow_api.data_source_adapters import CloudAdapters

MAX_TIME_MS=3000
SAMPLE_LIMIT=25
SCOPE=('local-workspace','local-builder')


def failure(exc):
    # Driver messages can contain endpoints or values. Retain only safe codes.
    return dict(error_type=type(exc).__name__,code=getattr(exc,'code',None))


def probe_collection(collection,fields,info):
    schema=info.get('options',{}).get('validator',{}).get('$jsonSchema',{})
    declarations=schema.get('properties',{})
    try:
        has_records=bool(list(collection.aggregate([
            {'$limit':1},{'$project':{'_id':0,'has_record':{'$literal':True}}}
        ],maxTimeMS=MAX_TIME_MS)))
    except Exception as exc:
        return [dict(field=f,status='unavailable',**failure(exc)) for f in fields]
    results=[]
    for field in fields:
        declaration=declarations.get(field,{})
        declared=field in declarations
        result=dict(field=field,collection_has_records=has_records,
            json_schema_declared=declared,declared_bson_type=declaration.get('bsonType'),
            declared_required=field in schema.get('required',[]),
            observed_bson_types=[],matching_sample_count=0,
            business_policy_approved=False,reference_target_verified=False)
        if not has_records:
            result['status']='schema_declared_empty_collection' if declared else 'empty_collection_no_schema_declaration'
        else:
            try:
                # $exists searches for this exact field, rather than reusing the
                # first 25 documents. Limit precedes grouping. No values leave DB.
                rows=list(collection.aggregate([
                    {'$match':{field:{'$exists':True}}},
                    {'$limit':SAMPLE_LIMIT},
                    {'$project':{'_id':0,'bson_type':{'$type':'$'+field}}},
                    {'$group':{'_id':'$bson_type','count':{'$sum':1}}}
                ],maxTimeMS=MAX_TIME_MS,allowDiskUse=False))
                result['observed_bson_types']=sorted(row['_id'] for row in rows)
                result['matching_sample_count']=sum(row['count'] for row in rows)
                result['status']='observed_field' if rows else 'schema_declared_not_observed' if declared else 'not_observed_in_completed_probe'
            except Exception as exc:
                result.update(status='unavailable',**failure(exc))
        results.append(result)
    return results


def verify():
    root=ROOT/'docs/ontology-review/simpsons'
    gaps=json.loads((root/'draft/validation.json').read_text())['mapping_gaps']
    target=root/'field-verification.json'
    if target.exists():raise ValueError('Preserve existing evidence; use a versioned report for a subsequent check.')
    source=ROOT/'.local/ontology-foundation/simpsons-check.sqlite3'
    env={**load_env(),**os.environ}
    keyfile=env.get('BUILDER_DATA_SOURCE_KEY_FILE') or env.get('BUILDER_GOOGLE_KEY_FILE')
    if not keyfile:raise ValueError('Existing connector key configuration is unavailable.')
    keypath=Path(keyfile)
    cipher=Fernet((keypath if keypath.is_absolute() else ROOT/keypath).read_bytes().strip())
    grouped={};configs={}
    with sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True) as db:
        for secret,raw in db.execute('SELECT secret,document FROM data_source_connections WHERE workspace=? AND owner=?',SCOPE):
            connection=json.loads(raw)
            if 'simpson' not in connection.get('name','').lower() or connection.get('connection_status')!='connected':continue
            snapshot=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(connection['connection_id'],connection['metadata_revision'])).fetchone()
            if not snapshot:raise ValueError('Saved connection metadata unavailable.')
            datasets={d['name'] for d in json.loads(snapshot[0])['datasets']}
            targets={g['collection'] for g in gaps}&datasets
            if not targets:continue
            cid=connection['connection_id']
            configs[cid]=json.loads(cipher.decrypt(secret.encode()))
            grouped[cid]=dict(connection_name=connection['name'],collections=sorted(targets))
    counts=Counter(c for group in grouped.values() for c in group['collections'])
    if any(counts[g['collection']]!=1 for g in gaps):raise ValueError('Each collection must resolve to exactly one authorized saved source.')
    outcomes=[]
    for cid,group in grouped.items():
        try:
            with CloudAdapters(env).connection(configs[cid]) as client:
                db=client[configs[cid]['database']]
                # Reuse the connector's bounded metadata discovery: Atlas may
                # reject listCollections name-$in filters on this deployment.
                discovered=list(islice(db.list_collections(maxTimeMS=MAX_TIME_MS),101))
                if len(discovered)>100:raise ValueError('Collection discovery exceeds its metadata bound.')
                infos={i['name']:i for i in discovered if i['name'] in group['collections']}
                for name in group['collections']:
                    fields=[g['field'] for g in gaps if g['collection']==name]
                    if name not in infos:
                        probes=[dict(field=f,status='collection_not_visible',business_policy_approved=False) for f in fields]
                    else:probes=probe_collection(db[name],fields,infos[name])
                    outcomes.extend(dict(collection=name,connection_name=group['connection_name'],**p) for p in probes)
        except Exception as exc:
            already={(x['collection'],x['field']) for x in outcomes}
            outcomes.extend(dict(collection=g['collection'],field=g['field'],connection_name=group['connection_name'],status='unavailable',business_policy_approved=False,**failure(exc))
                for g in gaps if g['collection'] in group['collections'] and (g['collection'],g['field']) not in already)
    report=dict(checked_at=datetime.now(timezone.utc).isoformat(),method='read_only_targeted_field_presence_and_server_side_bson_type',
        limits=dict(max_time_ms_per_operation=MAX_TIME_MS,matching_documents_per_field=SAMPLE_LIMIT,connector_deadline_seconds=60),
        basis='point_in_time_bounded_probe_not_a_population_integrity_check',business_policy_approved=False,
        source_documents_exported=0,source_writes=0,ontology_mutations=0,reference_targets_checked=False,
        ontology_published=False,credentials_exported=False,status_counts=dict(Counter(p['status'] for p in outcomes)),fields=outcomes)
    if len(outcomes)!=len(gaps):raise AssertionError('Every unresolved field must have an explicit outcome.')
    target.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report


if __name__=='__main__':
    try:print(json.dumps(verify(),indent=2))
    except Exception as exc:
        print(json.dumps(dict(status='verification_unavailable',**failure(exc))))
        sys.exit(1)
