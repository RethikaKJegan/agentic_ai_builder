"""Bounded, read-only Atlas and Supabase metadata discovery.

Adapted from Praxi's profiling/catalog approach; no runtime imports from Praxi.
Only cloud provider hostnames are accepted, and credentials never enter metadata.
"""
from __future__ import annotations

import hashlib
import json
from itertools import islice
import ipaddress
import socket
import time
from contextlib import contextmanager
from urllib.parse import parse_qs, unquote, urlsplit

from .service import ApiFailure

MAX_DATASETS = 100
MAX_FIELDS = 1000
MAX_DEPTH = 6
SAMPLE_DOCUMENTS = 25
PROFILE_SECONDS = 60


def invalid(message):
    raise ApiFailure('DATA_SOURCE_INPUT_INVALID', message, 400)


def configuration(body):
    if not isinstance(body, dict) or set(body) - {'name', 'engine', 'uri', 'database', 'schemas', 'description', 'mode'}:
        invalid('Supply a connection name, supported engine and cloud database settings only.')
    name = body.get('name', '')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100 or any(ord(c) < 32 for c in name):
        invalid('Enter a connection name between 1 and 100 characters.')
    engine, uri = body.get('engine'), body.get('uri')
    if engine not in {'mongodb', 'postgresql'} or not isinstance(uri, str) or len(uri) > 8192:
        invalid('Choose MongoDB Atlas or Supabase PostgreSQL and supply a connection URI.')
    try:
        parsed = urlsplit(uri)
        host, port = parsed.hostname or '', parsed.port
        if parsed.fragment or any(ord(c) < 32 for c in uri):
            raise ValueError()
        query = parse_qs(parsed.query, strict_parsing=True)
        if any(len(v) != 1 for v in query.values()):
            raise ValueError()
    except ValueError:
        invalid('The connection URI is invalid. Percent-encode special characters in credentials.')
    if not parsed.username or not parsed.password:
        invalid('Supply the database username and password in the connection URI.')
    database = body.get('database') or unquote(parsed.path.lstrip('/'))
    if not isinstance(database, str) or not database or len(database) > 100 or any(c in database for c in '/\\\x00'):
        invalid('Select one database to profile.')
    description = body.get('description', '')
    if not isinstance(description, str) or len(description) > 500:
        invalid('The business description must be at most 500 characters.')
    schemas = body.get('schemas', ['public'])
    if not isinstance(schemas, list) or not 1 <= len(schemas) <= 10 or any(not isinstance(s, str) or not s or len(s) > 63 or '\x00' in s for s in schemas):
        invalid('Choose between 1 and 10 schema names.')
    if engine == 'mongodb':
        if parsed.scheme != 'mongodb+srv' or not host.endswith('.mongodb.net') or port:
            invalid('Use an Atlas mongodb+srv URI ending in .mongodb.net.')
        permitted = {'retryWrites', 'w', 'appName', 'authSource', 'readPreference'}
        if set(query) - permitted:
            invalid('Unsupported Atlas URI options. TLS and timeouts are managed by the server.')
        if query.get('authSource', ['admin'])[0] not in {'admin', database}:
            invalid('Atlas authentication source must be admin or the selected database.')
        mode = 'srv'
    else:
        if parsed.scheme not in {'postgres', 'postgresql'} or not (host.endswith('.supabase.co') or host.endswith('.pooler.supabase.com')):
            invalid('Use a Supabase database or pooler PostgreSQL hostname.')
        if port not in {None, 5432, 6543} or set(query) - {'sslmode'} or query.get('sslmode', ['verify-full'])[0] not in {'require', 'verify-ca', 'verify-full'}:
            invalid('Use port 5432 or 6543 with SSL enabled. Other URI options are not supported.')
        mode = body.get('mode', 'direct')
        if mode not in {'direct', 'session', 'transaction'}:
            invalid('Choose direct, session pooler or transaction pooler mode.')
        if mode == 'direct' and (host.endswith('.pooler.supabase.com') or port not in {None,5432}):
            invalid('For a pooler endpoint choose session or transaction pooler mode.')
        if mode in {'session','transaction'} and (not host.endswith('.pooler.supabase.com') or (port or 5432) != (6543 if mode == 'transaction' else 5432)):
            invalid('Use the Supabase pooler hostname with port 5432 for session mode or 6543 for transaction mode.')
    return dict(name=name.strip(), engine=engine, uri=uri, database=database, schemas=list(dict.fromkeys(schemas)), description=description, mode=mode, host=host)


def public_addresses(host, port):
    try:
        addresses = list(dict.fromkeys(row[4][0] for row in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)))
        if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
            raise ValueError()
        return addresses
    except (socket.gaierror, ValueError):
        raise ApiFailure('DATA_SOURCE_NETWORK_BLOCKED', 'The cloud hostname must resolve to public addresses. Check the endpoint and server network access.', 400) from None


def validate_target(config):
    parsed = urlsplit(config['uri'])
    if config['engine'] == 'postgresql':
        return public_addresses(config['host'], parsed.port or 5432)
    import dns.resolver
    try:
        answers = dns.resolver.resolve('_mongodb._tcp.' + config['host'], 'SRV', lifetime=5)
        targets = [(str(r.target).rstrip('.'), r.port) for r in answers]
        if not targets or len(targets) > 20 or any(not h.endswith('.mongodb.net') for h, _ in targets):
            raise ValueError()
    except Exception:
        raise ApiFailure('DATA_SOURCE_DNS_FAILED', 'Atlas SRV discovery failed. Check the cluster URI and DNS access.', 400) from None
    for host, port in targets:
        public_addresses(host, port)
    return []


def stable_id(connection_id, *parts):
    return 'meta_' + hashlib.sha256(('\x00'.join([connection_id, *parts])).encode()).hexdigest()[:32]


def type_name(value):
    if value is None: return 'null'
    if isinstance(value, bool): return 'boolean'
    if isinstance(value, int): return 'integer'
    if isinstance(value, float): return 'number'
    if isinstance(value, str): return 'string'
    if isinstance(value, dict): return 'object'
    if isinstance(value, list): return 'array'
    return type(value).__name__


def observed_fields(documents, connection_id, dataset_id):
    fields, partial = {}, False
    for document in documents:
        seen = set()
        def walk(value, prefix='', depth=0):
            nonlocal partial
            if not isinstance(value, dict): return
            for key, item in value.items():
                path = prefix + str(key)
                if len(fields) >= MAX_FIELDS and path not in fields:
                    partial = True
                    continue
                if len(path) > 512:
                    partial = True
                    continue
                entry = fields.setdefault(path, {'field_id': stable_id(connection_id, dataset_id, path), 'name': path, 'types': set(), 'present_in_samples': 0, 'discovery_method': 'sampled'})
                entry['types'].add(type_name(item))
                if path not in seen:
                    entry['present_in_samples'] += 1
                    seen.add(path)
                if isinstance(item, (dict, list)):
                    if depth >= MAX_DEPTH:
                        partial = True
                        continue
                    if isinstance(item, dict): walk(item, path + '.', depth + 1)
                    else:
                        if len(item) > 10: partial = True
                        for child in item[:10]: walk(child, path + '[].', depth + 1)
        walk(document)
    return [dict(v, types=sorted(v['types'])) for _, v in sorted(fields.items())], partial


class CloudAdapters:
    def __init__(self, env):
        self.env = env

    @contextmanager
    def connection(self, config):
        addresses = validate_target(config)
        if config['engine'] == 'mongodb':
            from pymongo import MongoClient, timeout
            with timeout(PROFILE_SECONDS):
                with MongoClient(config['uri'], tls=True, tlsAllowInvalidCertificates=False, tlsAllowInvalidHostnames=False,
                                 connectTimeoutMS=8000, serverSelectionTimeoutMS=8000, socketTimeoutMS=10000,
                                 maxPoolSize=2, retryReads=False) as client:
                    client[config['database']].command('ping')
                    yield client
        else:
            import psycopg
            parsed = urlsplit(config['uri'])
            # Pin libpq to the already checked IPs; retain host for certificate verification.
            hosts = ','.join([config['host']] * len(addresses))
            with psycopg.connect(host=hosts, hostaddr=','.join(addresses), port=parsed.port or 5432,
                                  dbname=config['database'], user=unquote(parsed.username), password=unquote(parsed.password),
                                  sslmode='verify-full', sslrootcert=self.env.get('BUILDER_DATA_SOURCE_CA_FILE', '/etc/ssl/certs/ca-certificates.crt'),
                                  connect_timeout=8, prepare_threshold=None) as conn:
                conn.read_only = True
                with conn.cursor() as cur:
                    cur.execute("SELECT set_config('statement_timeout', '10000', true)")
                    cur.execute("SELECT set_config('lock_timeout', '3000', true)")
                    cur.execute('SELECT 1')
                yield conn

    def test(self, config):
        with self.connection(config) as conn:
            if config['engine'] == 'mongodb':
                # Verify collection discovery authority, not merely connectivity.
                next(iter(conn[config['database']].list_collections(nameOnly=True, maxTimeMS=8000)), None)
            else:
                with conn.cursor() as cur:
                    cur.execute('SELECT schema_name FROM information_schema.schemata WHERE schema_name = ANY(%s)', (config['schemas'],))
                    if set(r[0] for r in cur.fetchall()) != set(config['schemas']):
                        raise ApiFailure('DATA_SOURCE_ACCESS_DENIED', 'One or more selected schemas are inaccessible or do not exist.', 400)

    def profile(self, config, connection_id):
        with self.connection(config) as conn:
            if config['engine'] == 'mongodb':
                return self.mongo(conn[config['database']], config, connection_id)
            return self.postgres(conn, config, connection_id)

    @staticmethod
    def mongo(db, config, cid):
        datasets, warnings = [], []
        deadline = time.monotonic() + PROFILE_SECONDS
        infos = list(islice(db.list_collections(maxTimeMS=8000), MAX_DATASETS + 1))
        if len(infos) > MAX_DATASETS: warnings.append('Dataset limit reached; only the first 100 collections are profiled.')
        for info in sorted(infos, key=lambda x: x['name'])[:MAX_DATASETS]:
            if time.monotonic() >= deadline:
                warnings.append('Profiling time limit reached.'); break
            name = info['name']
            did = stable_id(cid, config['database'], name)
            docs = list(db[name].find({}, limit=SAMPLE_DOCUMENTS).max_time_ms(8000))
            fields, partial = observed_fields(docs, cid, did)
            if partial: warnings.append('Field, array or nesting coverage limited for ' + name)
            indexes = []
            for index in ([] if info.get('type') == 'view' else db[name].list_indexes()):
                indexes.append({'name': index['name'], 'columns': [{'name': k, 'direction': str(v)} for k,v in index['key'].items()], 'unique': bool(index.get('unique', False))})
                if len(indexes) >= 100:
                    warnings.append('Index coverage limited for ' + name); break
            validator = info.get('options', {}).get('validator')
            datasets.append(dict(dataset_id=did, name=name, database=config['database'], schema=None,
                                 kind=info.get('type', 'collection'), fields=fields, indexes=indexes, constraints=[],
                                 sample_count=len(docs), discovery_method='sampled', has_validation_rules=bool(validator),
                                 validation_schema_json=json.dumps(validator.get('$jsonSchema', {}), default=str) if isinstance(validator, dict) else '{}'))
        return dict(datasets=datasets, warnings=warnings, coverage='partial' if warnings else 'sampled', limits={'datasets':MAX_DATASETS,'documents_per_collection':SAMPLE_DOCUMENTS,'field_depth':MAX_DEPTH})

    @staticmethod
    def postgres(conn, config, cid):
        datasets, warnings = [], []
        deadline = time.monotonic() + PROFILE_SECONDS
        with conn.cursor() as cur:
            cur.execute('SELECT table_schema, table_name, table_type FROM information_schema.tables WHERE table_schema = ANY(%s) ORDER BY table_schema,table_name LIMIT %s', (config['schemas'], MAX_DATASETS+1))
            tables = cur.fetchall()
            if len(tables) > MAX_DATASETS: warnings.append('Dataset limit reached; only the first 100 tables/views are profiled.')
            for schema, name, kind in tables[:MAX_DATASETS]:
                if time.monotonic() >= deadline:
                    warnings.append('Profiling time limit reached.'); break
                did = stable_id(cid, config['database'], schema, name)
                cur.execute('SELECT column_name,data_type,udt_name,is_nullable,column_default FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position LIMIT %s', (schema,name,MAX_FIELDS+1))
                columns = cur.fetchall()
                if len(columns) > MAX_FIELDS: warnings.append('Field coverage limited for ' + schema + '.' + name)
                fields = [dict(field_id=stable_id(cid,did,n),name=n,types=[t],native_type=u,nullable=nullable=='YES',default_expression=default,discovery_method='declared') for n,t,u,nullable,default in columns[:MAX_FIELDS]]
                # pg_constraint preserves composite-key column order and the precise referenced relation.
                cur.execute('''SELECT c.conname,c.contype,pg_get_constraintdef(c.oid),
                    ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(num,ord) JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.num ORDER BY k.ord),
                    rn.nspname,rt.relname,
                    ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY k(num,ord) JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=k.num ORDER BY k.ord)
                    FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace
                    LEFT JOIN pg_class rt ON rt.oid=c.confrelid LEFT JOIN pg_namespace rn ON rn.oid=rt.relnamespace
                    WHERE n.nspname=%s AND t.relname=%s ORDER BY c.conname LIMIT 101''', (schema,name))
                rows = cur.fetchall()
                constraints = [dict(name=n,kind={'p':'primary_key','f':'foreign_key','u':'unique','c':'check','x':'exclusion'}.get(k,k),definition=d,columns=cols,referenced_schema=rs,referenced_table=rt,referenced_columns=rc,discovery_method='declared') for n,k,d,cols,rs,rt,rc in rows[:100]]
                cur.execute('SELECT indexname,indexdef FROM pg_indexes WHERE schemaname=%s AND tablename=%s ORDER BY indexname LIMIT 101', (schema,name))
                index_rows=cur.fetchall()
                if len(rows)>100 or len(index_rows)>100: warnings.append('Constraint/index coverage limited for ' + schema + '.' + name)
                indexes=[dict(name=n,definition=d) for n,d in index_rows[:100]]
                datasets.append(dict(dataset_id=did,name=name,database=config['database'],schema=schema,kind='view' if 'VIEW' in kind else 'table',fields=fields,indexes=indexes,constraints=constraints,sample_count=0,discovery_method='declared'))
        return dict(datasets=datasets,warnings=warnings,coverage='partial' if warnings else 'declared',limits={'datasets':MAX_DATASETS,'fields_per_dataset':MAX_FIELDS})


def safe_failure(exc):
    if isinstance(exc, ApiFailure): return exc
    name = type(exc).__name__
    state = getattr(exc, 'sqlstate', '') or ''
    if isinstance(exc, ImportError):
        return ApiFailure('DATA_SOURCE_DRIVER_MISSING', 'Install requirements-data-sources.txt in the backend and worker environment.', 503)
    if state.startswith('28') or name == 'OperationFailure' and getattr(exc,'code',None) in {13,18}:
        return ApiFailure('DATA_SOURCE_ACCESS_DENIED', 'Database authentication or discovery access was denied. Check the database user and permissions.', 400)
    return ApiFailure('DATA_SOURCE_CONNECTION_FAILED', 'The database operation failed. Check cloud network access, credentials, endpoint and TLS trust. No new metadata was activated.', 400)
