"""Bounded aggregate-only discovery for the separate Simpson Business Ontology.

No application service is instantiated and no source records/values are exported.
Run explicitly; importing this module performs no I/O.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from itertools import islice
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCOPE = ('local-workspace', 'local-builder')
MAX_TIME_MS = 3000
SAMPLE_LIMIT = 100
SOURCES = {
    'dbconn_897964ed8cd9de2073f5497b50b80361': ('db1', {
        'oemnames': ['_id', 'name'],
        'oems': ['_id', 'oemNameId'],
        'enginedetails': ['_id', 'oem', 'engineSerialNumber', 'engineModel', 'listNo', 'organizationName', 'invoiceDate', 'buildDate'],
        'tickets': ['_id', 'oem', 'oemOrg', 'engineNo', 'engineModal', 'createdAt', 'complaintRecord.dateOfSale', 'complaintRecord.hmr', 'complaintRecord.unitMachineStatus', 'hmr', 'underWarranty', 'invoiceDate', 'serviceEngineer', 'jointInspectionReport', 'defectCode', 'actionCode', 'assignedApprover', 'engineReplacementStatus', 'engineReplacementApprovedDate', 'cutInNumber', 'cutIn', 'cutInDetails'],
        'jointinspectionreports': ['_id', 'ticketId', 'oem', 'dateOfSale', 'dateOfFailure', 'hoursCovered', 'status', 'potentialCause', 'defectCode', 'serviceMaintenanceRecord', 'photos', 'documents'],
        'enginereplacements': ['_id', 'ticket', 'mode', 'engineType', 'engineSLNo'],
        'partreplacements': ['_id', 'ticket', 'part', 'mode', 'scope', 'partReplacementCost'],
        'floatengines': ['_id', 'ticketId', 'oem', 'replacementEngineNumber', 'status', 'engineReplacementApprovalDate'],
        'focs': ['_id', 'ticket', 'oem', 'hoursOfFailure', 'failureDate', 'focStatus', 'focReleaseRequest.warrantyClaimNo'],
        'workorders': ['_id', 'complaintReferenceNumber', 'fieldWarrantyReferenceNumber', 'oem', 'oemOrg', 'fieldWarrantyEngineInwardDate', 'hoursCovered'],
        'internalcutins': ['_id', 'plant', 'listNo', 'engineCutInNumber', 'cutInDate', 'oem', 'defectCode', 'engineModel'],
        'servicebulletins': ['_id', 'oem', 'engineModel', 'listNumbers', 'plantDetails', 'defectCode', 'approvalStatus'],
        'serviceinformations': ['_id', 'oem', 'engineModel', 'listNumbers', 'plantDetails', 'defectCode', 'approvalStatus'],
    }),
    'dbconn_1abe80b38381eaf39b4fff79b924410a': ('db2', {
        'claims': ['_id', 'oem', 'claimReferenceNumber', 'claimNumber', 'engineSerialNumber', 'machineSaleDate', 'dateOfFailure', 'hoursCovered', 'status', 'reason', 'simpsonPartNumber'],
        'claimsftps': ['_id', 'oem', 'claimReference', 'claimId', 'engineSerialNumber', 'machineSaleDate', 'failureDate', 'simpsonInvoiceDate', 'failureHours', 'status', 'defectCode', 'plant', 'partValue'],
        'failedengineanalyses': ['_id', 'engineSerialNumber', 'defect', 'oem', 'engineModel', 'listNo', 'beforeImprovement', 'afterImprovement', 'cutInEsn', 'cutInEffectiveDate', 'qualityApprover', 'status', 'attachments'],
        'failedpartanalyses': ['_id', 'partNumber', 'defect', 'oem', 'engineModel', 'cutInEsn', 'cutInEffectiveDate', 'qualityApprover', 'status'],
        'icacapas': ['_id', 'defect', 'oem', 'engineModel', 'listNo', 'beforeImprovement', 'afterImprovement', 'cutInEsn', 'cutInEffectiveDate', 'attachments'],
        'products': ['_id', 'engineModel', 'oem', 'listData'],
        'floatengineftps': ['_id', 'serialNumber', 'model', 'listNumber', 'plant', 'oem', 'stock', 'status', 'amount'],
        'jirlogs': ['_id', 'jirId', 'ticketId', 'operationType', 'createdAt'],
    }),
}
REFERENCES = [
    ('tickets', 'oem', 'oems'),
    ('tickets', 'oemOrg', 'oemnames'),
    ('jointinspectionreports', 'ticketId', 'tickets'),
    ('enginereplacements', 'ticket', 'tickets'),
    ('floatengines', 'ticketId', 'tickets'),
    ('focs', 'ticket', 'tickets'),
]


def safe_failure(exc):
    code = getattr(exc, 'code', None)
    return {'error_type': type(exc).__name__, 'code': code if isinstance(code, int) else None}


def field_pipeline(fields):
    # Group all allowlisted fields in one bounded scan; no stored values leave DB.
    return [
        {'$limit': SAMPLE_LIMIT},
        {'$project': {'_id': 0, 'field_types': [
            {'field': {'$literal': f}, 'bson_type': {'$type': '$' + f}}
            for f in fields
        ]}},
        {'$unwind': '$field_types'},
        {'$group': {'_id': {'field': '$field_types.field', 'bson_type': '$field_types.bson_type'}, 'count': {'$sum': 1}}},
    ]


def profile(collection, fields):
    try:
        rows = list(collection.aggregate(field_pipeline(fields), maxTimeMS=MAX_TIME_MS, allowDiskUse=False))
    except Exception as exc:
        return {'status': 'unavailable', **safe_failure(exc)}
    counts = {f: {} for f in fields}
    for row in rows:
        field, kind = row['_id']['field'], row['_id']['bson_type']
        if field not in counts or not isinstance(kind, str) or not isinstance(row['count'], int):
            raise ValueError('Invalid aggregate shape')
        counts[field][kind] = row['count']
    sizes = {sum(c.values()) for c in counts.values()}
    if len(sizes) != 1 or max(sizes, default=0) > SAMPLE_LIMIT:
        raise ValueError('Invalid sample counts')
    size = next(iter(sizes), 0)
    return {'status': 'sampled' if size else 'empty_collection', 'sample_size': size,
            'fields': [{'field': f, 'bson_type_counts': c,
                        'status': 'empty_collection' if not size else
                        'not_observed_in_bounded_sample' if c.get('missing', 0) == size else
                        'observed_only_null' if c.get('missing', 0) + c.get('null', 0) == size else 'observed_value'}
                       for f, c in counts.items()]}


def reference_pipeline(field, target):
    return [
        {'$limit': SAMPLE_LIMIT},
        {'$project': {'_id': 0, 'ref': '$' + field, 'ref_type': {'$type': '$' + field}}},
        {'$lookup': {'from': target, 'localField': 'ref', 'foreignField': '_id', 'as': 'matches'}},
        {'$project': {'state': {'$switch': {'branches': [
            {'case': {'$in': ['$ref_type', ['missing', 'null']]}, 'then': 'missing_or_null'},
            {'case': {'$eq': [{'$size': '$matches'}, 1]}, 'then': 'single_target'},
            {'case': {'$gt': [{'$size': '$matches'}, 1]}, 'then': 'multiple_targets'},
        ], 'default': 'unresolved'}}}},
        {'$group': {'_id': '$state', 'count': {'$sum': 1}}},
    ]


def reference_profile(collection, field, target):
    try:
        rows = list(collection.aggregate(reference_pipeline(field, target), maxTimeMS=MAX_TIME_MS, allowDiskUse=False))
        allowed = {'missing_or_null', 'single_target', 'multiple_targets', 'unresolved'}
        if any(r['_id'] not in allowed or not isinstance(r['count'], int) for r in rows):
            raise ValueError('Invalid reference aggregate')
        counts = {r['_id']: r['count'] for r in rows}
        if sum(counts.values()) > SAMPLE_LIMIT:
            raise ValueError('Invalid reference sample count')
        return {'status': 'sampled' if rows else 'empty_collection', 'sample_size': sum(counts.values()), 'counts': counts}
    except Exception as exc:
        return {'status': 'unavailable', **safe_failure(exc)}


def connection_rows(path):
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        rows = db.execute('SELECT connection_id,secret,document FROM data_source_connections WHERE workspace=? AND owner=?', SCOPE).fetchall()
    return {cid: (secret, raw) for cid, secret, raw in rows if cid in SOURCES}


def fingerprints(rows):
    return {cid: hashlib.sha256((secret + raw).encode()).hexdigest() for cid, (secret, raw) in rows.items()}


def verify(store):
    from cryptography.fernet import Fernet
    from scripts.integration_config import load_env
    from workflow_api.data_source_adapters import CloudAdapters

    env = {**load_env(), **os.environ}
    keyfile = env.get('BUILDER_DATA_SOURCE_KEY_FILE') or env.get('BUILDER_GOOGLE_KEY_FILE')
    if not keyfile:
        raise ValueError('Connector key configuration unavailable')
    keypath = Path(keyfile)
    cipher = Fernet((keypath if keypath.is_absolute() else ROOT / keypath).read_bytes().strip())
    before = connection_rows(store)
    if set(before) != set(SOURCES):
        raise ValueError('Both scoped Simpson connections are required')
    outcomes = []
    for cid, (label, targets) in SOURCES.items():
        secret, raw = before[cid]
        document = json.loads(raw)
        result = {'source': label, 'collections': {}, 'direct_references': []}
        outcomes.append(result)
        try:
            if document.get('connection_status') != 'connected' or 'simpson' not in document.get('name', '').lower():
                raise ValueError('Expected connected Simpson source')
            config = json.loads(cipher.decrypt(secret.encode()))
            if config.get('engine') != 'mongodb':
                raise ValueError('Expected MongoDB source')
            with CloudAdapters(env).connection(config) as client:
                db = client[config['database']]
                discovered = list(islice(db.list_collections(nameOnly=True, maxTimeMS=MAX_TIME_MS), 101))
                if len(discovered) > 100:
                    raise ValueError('Collection discovery bound exceeded')
                names = {i['name'] for i in discovered}
                result['connection_status'] = 'read_succeeded'
                for name, fields in targets.items():
                    result['collections'][name] = profile(db[name], fields) if name in names else {'status': 'collection_not_visible'}
                for source, field, target in REFERENCES if label == 'db1' else []:
                    outcome = reference_profile(db[source], field, target) if {source, target} <= names else {'status': 'collection_not_visible'}
                    result['direct_references'].append({'collection': source, 'field': field, 'target': target, **outcome})
        except Exception as exc:
            result['connection_status'] = 'unavailable'
            result.update(safe_failure(exc))
            for name in targets:
                result['collections'].setdefault(name, {'status': 'unavailable', **safe_failure(exc)})
    after = connection_rows(store)
    report = {
        'schema_version': 1, 'checked_at': datetime.now(timezone.utc).isoformat(),
        'method': 'bounded_server_side_type_and_direct_reference_aggregates',
        'limits': {'documents_per_collection_or_reference': SAMPLE_LIMIT, 'max_time_ms_per_operation': MAX_TIME_MS},
        'sampling': 'first_up_to_100_unsorted_documents_not_random_or_population_evidence',
        'source_records_exported': 0, 'source_values_exported': 0, 'source_writes': 0,
        'ontology_mutations': 0, 'model_calls': 0,
        'connection_configuration_unchanged_during_probe': fingerprints(before) == fingerprints(after),
        'cross_database_associations_verified': False, 'business_policy_verified': False,
        'sources': outcomes,
    }
    report['status_counts'] = dict(Counter(c['status'] for s in outcomes for c in s['collections'].values()))
    report['complete'] = (report['connection_configuration_unchanged_during_probe'] and
                          all(s['connection_status'] == 'read_succeeded' for s in outcomes) and
                          all(c['status'] not in {'unavailable', 'collection_not_visible'} for s in outcomes for c in s['collections'].values()) and
                          all(r['status'] not in {'unavailable', 'collection_not_visible'} for s in outcomes for r in s['direct_references']))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, default=ROOT / '.local/workflows.sqlite3')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Exclusive creation preserves earlier evidence on repeated runs.
    with args.output.open('x') as handle:
        try:
            report = verify(args.store)
        except Exception as exc:
            report = {'complete': False, 'status': 'unavailable', **safe_failure(exc)}
        handle.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'complete': report['complete'], 'status_counts': report.get('status_counts', {}), 'output': str(args.output)}))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    sys.exit(main())
