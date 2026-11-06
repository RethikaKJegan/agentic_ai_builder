"""Restore selected archive collections to the dedicated authenticated Subway MongoDB."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import secrets
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from bson import BSON, json_util
from bson.codec_options import CodecOptions
from bson.errors import InvalidBSON
from pymongo import MongoClient
from scripts.subway_archive_analysis import records

EXCLUDED = {'tokens','clientsecrets','users','otps','apilogs','auditlogs','mails','backuplogs',
    'notifications','userproperties','useridcounters','storeupdatetrackers','counters','mastercodeidcounters'}
SECRET_FIELD = re.compile(r'password|passhash|secret|token|api.?key|posistkey|private.?key|otp', re.I)


def restore(directory, restart_partial=False):
    directory = Path(directory).resolve(); manifest_path = directory / 'mongo-access.json'
    if (directory / 'restore-receipt.json').exists(): raise ValueError('A restore receipt already exists; do not overwrite this snapshot.')
    if manifest_path.exists(): access = json.loads(manifest_path.read_text())
    else:
        access = dict(port=27028, admin_user='subway_restore_operator', admin_password=secrets.token_urlsafe(40),
                      reader_user='subway_source_reader', reader_password=secrets.token_urlsafe(40))
        manifest_path.write_text(json.dumps(access)); os.chmod(manifest_path, 0o600)
        with MongoClient('mongodb://127.0.0.1:27028', serverSelectionTimeoutMS=5000) as bootstrap:
            bootstrap.admin.command('createUser', access['admin_user'], pwd=access['admin_password'], roles=['root'])
    uri = f'mongodb://{quote(access["admin_user"])}:{quote(access["admin_password"])}@127.0.0.1:27028/?authSource=admin'
    receipt = dict(databases={}, excluded_collections=[], removed_secret_field_occurrences={}, utf8_repaired_records={}, original_archives_changed=False)
    removed = Counter()
    def sanitized(value):
        if isinstance(value, list): return [sanitized(v) for v in value]
        if isinstance(value, dict):
            result = {}
            for k,v in value.items():
                if SECRET_FIELD.search(k): removed[k] += 1
                else: result[k] = sanitized(v)
            return result
        return value
    grants = []
    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        for role, dbname in [('central','subway_central'),('finance','subway_finance')]:
            report = json.loads((directory / role / 'analysis.json').read_text())
            db = client[dbname]
            expected_names = {p['collection'] for p in report['collections'] if p['collection'] not in EXCLUDED}
            if set(db.list_collection_names()) - expected_names: raise ValueError('Unexpected collection in restore destination.')
            counts = {}
            for profile in report['collections']:
                name = profile['collection']
                if name in EXCLUDED:
                    receipt['excluded_collections'].append(role + '.' + name); continue
                path = next((directory / role / 'extracted').rglob(name + '.bson'))
                existing = name in db.list_collection_names()
                if not existing: db.create_collection(name)
                existing_count = db[name].count_documents({})
                if existing_count not in (0, profile['record_count']):
                    if not restart_partial: raise ValueError('A partial collection needs explicit reconciliation.')
                    db.drop_collection(name); db.create_collection(name); existing_count = 0
                batch = []; count = 0
                for raw in (() if existing_count else records(path)):
                    try: document = BSON(raw).decode()
                    except InvalidBSON:
                        document = BSON(raw).decode(codec_options=CodecOptions(unicode_decode_error_handler='replace'))
                        key = role + '.' + name
                        receipt['utf8_repaired_records'][key] = receipt['utf8_repaired_records'].get(key, 0) + 1
                    batch.append(sanitized(document))
                    if len(batch) >= 200:
                        db[name].insert_many(batch, ordered=True); count += len(batch); batch = []
                if batch: db[name].insert_many(batch, ordered=True); count += len(batch)
                if existing_count: count = existing_count
                if count != profile['record_count'] or db[name].count_documents({}) != count:
                    raise ValueError('Restored record counts do not match the archive.')
                for index in json_util.loads(json.dumps(profile['metadata'])).get('indexes', []):
                    if index.get('name') == '_id_': continue
                    # Preserve key/uniqueness metadata, never expiry policies that would delete snapshot rows.
                    keys = list(index['key'].items())
                    if index['key'].get('_fts') == 'text':
                        keys = [(k, 'text') for k in index.get('weights', {})] + [(k,v) for k,v in keys if k not in {'_fts','_ftsx'}]
                    if any(SECRET_FIELD.search(k) for k,_ in keys): continue
                    options = {k:index[k] for k in ['name','unique','sparse','partialFilterExpression','collation','weights','default_language','language_override'] if k in index}
                    db[name].create_index(keys, **options)
                counts[name] = count
                grants.append(dict(resource=dict(db=dbname, collection=name), actions=['find','listIndexes','collStats']))
                print(json.dumps(dict(database=dbname, collection=name, records=count)), flush=True)
            grants.append(dict(resource=dict(db=dbname, collection=''), actions=['listCollections','dbStats']))
            receipt['databases'][dbname] = dict(archive_sha256=report['archive_sha256'], collections=counts)
        client.admin.command('createRole', 'subway_archive_reader', privileges=grants, roles=[])
        client.admin.command('createUser', access['reader_user'], pwd=access['reader_password'],
                             roles=[dict(role='subway_archive_reader', db='admin')])
    receipt['removed_secret_field_occurrences'] = dict(removed)
    (directory / 'restore-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--restart-partial',action='store_true');a=p.parse_args()
    os.umask(0o077);restore(a.directory,a.restart_partial)
