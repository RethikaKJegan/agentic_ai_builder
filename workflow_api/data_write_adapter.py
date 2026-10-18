"""Exact-key, scalar CRUD with native transactions and no transaction-body retry."""
import datetime as dt
import json
import math
import re
from decimal import Decimal
from uuid import UUID

from .data_relationships import fingerprint
from .service import ApiFailure


class RolledBack(Exception):
    def __init__(self, code='DATA_WRITE_ROLLED_BACK'):
        self.code = code


class UncertainWrite(Exception):
    pass


def fail(message, code='DATA_WRITE_INVALID', status=400):
    raise ApiFailure(code, message, status)


def value_for(field, value):
    types = set(field['types']) - {'null'}
    if len(types) != 1:
        fail('Mixed or unknown field types cannot be written.')
    kind = next(iter(types))
    if value is None:
        return None
    if kind in {'string', 'text', 'character varying', 'character'}:
        if not isinstance(value, str) or len(value) > 4096:
            fail('Text fields require strings of at most 4096 characters.')
        return value
    if kind in {'integer', 'smallint', 'bigint'}:
        if type(value) is not int or abs(value) > 9007199254740991:
            fail('Integer input must be an exact JSON integer within the safe range.')
        return value
    if kind in {'number', 'numeric', 'decimal', 'Decimal128'}:
        if type(value) not in (str, int) or not re.fullmatch(r'-?\d{1,30}(?:\.\d{1,18})?', str(value)):
            fail('Exact decimal input requires a bounded decimal string or integer.')
        return Decimal(str(value))
    if kind == 'boolean' and type(value) is bool:
        return value
    if kind == 'ObjectId' and isinstance(value, str) and re.fullmatch(r'[a-fA-F0-9]{24}', value):
        from bson import ObjectId
        return ObjectId(value)
    if kind == 'uuid' and isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            pass
    if kind in {'date', 'datetime', 'timestamp', 'timestamp with time zone', 'timestamp without time zone'} and isinstance(value, str):
        try:
            if kind == 'date':
                return dt.date.fromisoformat(value)
            if 'T' not in value:
                fail('Timestamp input requires an ISO timestamp with time.')
            parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
            if kind == 'timestamp without time zone':
                if parsed.tzinfo is not None:
                    fail('This timestamp requires a local value without a time zone.')
            elif parsed.tzinfo is None:
                fail('This timestamp requires an explicit time zone.')
            return parsed
        except ValueError:
            pass
    fail('Unsupported scalar field type or invalid value. Refresh metadata and review the target.')


def pack(record, engine):
    if record is None:
        return None
    from bson import ObjectId
    from bson.decimal128 import Decimal128

    def scalar(value):
        if isinstance(value, Decimal128):
            value = value.to_decimal()
        if value is None or type(value) in (str, bool):
            return value
        if isinstance(value, int):
            return value if abs(value) <= 9007199254740991 else {'$integer': str(value)}
        if isinstance(value, Decimal) and value.is_finite():
            return {'$decimal': str(value)}
        if isinstance(value, ObjectId):
            return {'$objectid': str(value)}
        if isinstance(value, UUID):
            return {'$uuid': str(value)}
        if isinstance(value, dt.datetime):
            if engine == 'mongodb' and value.tzinfo is None:
                value = value.replace(tzinfo=dt.timezone.utc)
            return {'$timestamp': value.isoformat()}
        if isinstance(value, dt.date):
            return {'$date': value.isoformat()}
        if type(value) is float and math.isfinite(value):
            return {'$float': value.hex()}
        fail('Point operations require scalar records; nested, binary or unsupported values are outside this scope.')
    encoded = {key: scalar(value) for key, value in record.items()}
    if len(json.dumps(encoded).encode()) > 65536:
        fail('The point record exceeds the 64 KB operation snapshot limit.', 'DATA_WRITE_LIMIT', 422)
    return encoded


def public_record(record):
    if record is None:
        return None
    return {key: (float.fromhex(value['$float']) if '$float' in value else next(iter(value.values())))
            if isinstance(value, dict) else value for key, value in record.items()}


class WriteAdapter:
    def __init__(self, cloud):
        self.cloud = cloud

    @staticmethod
    def fields(dataset):
        fields = {f['name']: f for f in dataset['fields']}
        if not fields or len(fields) > 64:
            fail('Point operations support datasets with 1–64 discovered fields.')
        if any('.' in name or name.startswith('$') or '\x00' in name for name in fields):
            fail('Nested or operator-like field paths are not supported by point operations.')
        return fields

    def inputs(self, dataset, target, step):
        fields = self.fields(dataset)
        identity = step['identity']
        if set(identity) != set(target['identity_fields']) or any(value is None for value in identity.values()):
            fail('Supply every permitted identity field, with non-null values.')
        names = set(step.get('values', {})) | set(step.get('unset_fields', []))
        if not names <= set(target['writable_fields']) or names & set(identity):
            fail('Only explicitly writable, non-identity fields may be changed.', 'DATA_WRITE_FIELD_DENIED', 403)
        if not set(identity) | names <= set(fields):
            fail('An operation references fields outside the discovered catalog.')
        if set(step.get('values', {})) & set(step.get('unset_fields', [])):
            fail('A field cannot be set and removed in the same operation.')
        if step['action'] == 'delete' and names:
            fail('Delete requests contain only explicit identities.')
        if step['action'] == 'create' and step.get('unset_fields'):
            fail('Create requests cannot remove fields.')
        if step['action'] == 'update' and not names:
            fail('Choose at least one permitted field to update.')
        if dataset.get('schema') is not None and step.get('unset_fields'):
            fail('PostgreSQL columns cannot be removed by record operations.')
        return ({name: value_for(fields[name], value) for name, value in identity.items()},
                {name: value_for(fields[name], value) for name, value in step.get('values', {}).items()})

    def validate_record(self, dataset, target, raw, identity):
        if raw is None:
            return None
        if not set(raw) <= set(self.fields(dataset)):
            fail('The record has undiscovered fields. Refresh metadata before writing.', 'DATA_WRITE_STALE', 409)
        if any(raw.get(name) != value for name, value in identity.items()):
            fail('The database matched a different identity representation.', 'DATA_WRITE_CONFLICT', 409)
        encoded = pack(raw, 'mongodb' if dataset.get('schema') is None else 'postgresql')
        for name, value in public_record(encoded).items():
            value_for(self.fields(dataset)[name], value)
        return encoded

    def check_result(self, dataset, after, values, removed):
        actual = public_record(after)
        fields = self.fields(dataset)
        for name, wanted in values.items():
            expected = wanted.to_decimal() if hasattr(wanted, 'to_decimal') else wanted
            if name not in actual or value_for(fields[name], actual[name]) != expected:
                fail('The database coerced or omitted a requested value. The transaction was rolled back.', 'DATA_WRITE_COERCION', 409)
        if any(name in actual for name in removed):
            fail('The database did not remove the requested field.', 'DATA_WRITE_CONFLICT', 409)

    @staticmethod
    def check_table(conn, dataset, target, action):
        names = [f['name'] for f in dataset['fields']]
        with conn.cursor() as cur:
            cur.execute('SELECT c.oid,c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relname=%s', (dataset['schema'], dataset['name']))
            table = cur.fetchone()
            if not table or table[1] != 'r':
                fail('Only ordinary PostgreSQL tables support point operations.')
            oid = table[0]
            cur.execute('SELECT column_name,data_type,is_generated,is_identity FROM information_schema.columns WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position', (dataset['schema'], dataset['name']))
            columns = cur.fetchall()
            expected = {f['name']: f['types'][0] for f in dataset['fields']}
            if set(names) != {c[0] for c in columns} or any(expected[c[0]] != c[1] for c in columns):
                fail('The PostgreSQL structure changed; refresh metadata.', 'DATA_WRITE_STALE', 409)
            if action != 'read' and any(c[2] != 'NEVER' or c[3] == 'YES' for c in columns):
                fail('Generated or identity-generated columns require a separate write policy implementation.')
            cur.execute('SELECT a.attname FROM pg_index i JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(num,ord) ON true JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.num WHERE i.indrelid=%s AND i.indisprimary ORDER BY k.ord', (oid,))
            actual_key = [r[0] for r in cur.fetchall()]
            declared_key = next((c.get('columns', []) for c in dataset.get('constraints', []) if c.get('kind') == 'primary_key'), [])
            if actual_key != target['identity_fields'] or actual_key != declared_key:
                fail('The configured identity must match the complete current PostgreSQL primary key.')
            if action != 'read':
                cur.execute('SELECT EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid=%s AND NOT tgisinternal) OR EXISTS(SELECT 1 FROM pg_inherits WHERE inhrelid=%s OR inhparent=%s)', (oid, oid, oid))
                if cur.fetchone()[0]:
                    fail('User triggers, inheritance and partition routing are outside controlled point-write scope.')
            if action == 'delete':
                cur.execute("SELECT EXISTS(SELECT 1 FROM pg_constraint WHERE confrelid=%s AND contype='f' AND confdeltype IN ('c','n','d'))", (oid,))
                if cur.fetchone()[0]:
                    fail('Cascading or referential-action deletes require a separate recovery implementation.')

    def pg_read(self, conn, dataset, target, identity, action, lock=False):
        from psycopg import sql
        self.check_table(conn, dataset, target, action)
        names = [f['name'] for f in dataset['fields']]
        condition = sql.SQL(' AND ').join(sql.SQL('{} IS NOT DISTINCT FROM %s').format(sql.Identifier(name)) for name in identity)
        query = sql.SQL('SELECT {} FROM {}.{} WHERE {} LIMIT 2{}').format(
            sql.SQL(',').join(map(sql.Identifier, names)), sql.Identifier(dataset['schema']),
            sql.Identifier(dataset['name']), condition, sql.SQL(' FOR UPDATE' if lock else ''))
        with conn.cursor() as cur:
            cur.execute(query, list(identity.values()))
            rows = cur.fetchall()
        if len(rows) > 1:
            fail('The record identity is not unique.', 'DATA_WRITE_CONFLICT', 409)
        return self.validate_record(dataset, target, dict(zip(names, rows[0])) if rows else None, identity)

    def read(self, config, dataset, target, step):
        identity, _ = self.inputs(dataset, target, step)
        with self.cloud.connection(config) as conn:
            if config['engine'] == 'postgresql':
                return self.pg_read(conn, dataset, target, identity, step['action'])
            if target['identity_fields'] != ['_id']:
                fail('MongoDB point operations require the unique _id identity.')
            return self.validate_record(dataset, target, conn[config['database']][dataset['name']].find_one(identity, max_time_ms=10000), identity)

    @staticmethod
    def expected(current, before, action):
        if fingerprint(current) != fingerprint(before) or (action == 'create') != (current is None):
            fail('The record changed or its expected existence no longer matches. Prepare a fresh operation.', 'DATA_WRITE_CONFLICT', 409)

    def mutate(self, config, dataset, target, step, before, guard):
        identity, values = self.inputs(dataset, target, step)
        committing = committed = False
        result = None
        try:
            with self.cloud.connection(config) as conn:
                if config['engine'] == 'postgresql':
                    from psycopg import IsolationLevel, sql
                    conn.rollback()
                    conn.read_only = False
                    conn.isolation_level = IsolationLevel.SERIALIZABLE
                    conn.execute("SET LOCAL statement_timeout='10s'")
                    conn.execute("SET LOCAL lock_timeout='3s'")
                    guard()
                    # Hold the table's write lock before inspecting triggers,
                    # constraints and types so concurrent DDL cannot change the
                    # accepted write semantics between inspection and mutation.
                    conn.execute(sql.SQL('LOCK TABLE {}.{} IN ROW EXCLUSIVE MODE').format(
                        sql.Identifier(dataset['schema']), sql.Identifier(dataset['name'])))
                    current = self.pg_read(conn, dataset, target, identity, step['action'], lock=True)
                    self.expected(current, before, step['action'])
                    if step['action'] == 'delete' and not set(current or {}) <= set(target['identity_fields'] + target['writable_fields']):
                        fail('Deletion recovery requires all record fields to be permitted.')
                    table = sql.SQL('{}.{}').format(sql.Identifier(dataset['schema']), sql.Identifier(dataset['name']))
                    condition = sql.SQL(' AND ').join(sql.SQL('{} IS NOT DISTINCT FROM %s').format(sql.Identifier(name)) for name in identity)
                    returning = sql.SQL(' RETURNING {}').format(sql.SQL(',').join(map(sql.Identifier, identity)))
                    if step['action'] == 'create':
                        data = {**identity, **values}
                        query = sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(table, sql.SQL(',').join(map(sql.Identifier, data)), sql.SQL(',').join(sql.Placeholder() for _ in data))
                        params = list(data.values())
                    elif step['action'] == 'update':
                        query = sql.SQL('UPDATE {} SET {} WHERE {}').format(table, sql.SQL(',').join(sql.SQL('{}=%s').format(sql.Identifier(name)) for name in values), condition)
                        params = [*values.values(), *identity.values()]
                    else:
                        query = sql.SQL('DELETE FROM {} WHERE {}').format(table, condition)
                        params = list(identity.values())
                    with conn.cursor() as cur:
                        cur.execute(query + returning, params)
                        if len(cur.fetchall()) != 1:
                            fail('The operation did not affect its one expected target.', 'DATA_WRITE_CONFLICT', 409)
                    after = None if step['action'] == 'delete' else self.pg_read(conn, dataset, target, identity, 'read', lock=True)
                    if after is not None:
                        self.check_result(dataset, after, values, step['unset_fields'])
                    result = dict(after=after, matched_records=0 if current is None else 1,
                                  affected_records=int(fingerprint(current) != fingerprint(after)))
                    guard()
                    committing = True
                    conn.commit()
                    committed = True
                else:
                    from bson.decimal128 import Decimal128
                    from pymongo import timeout
                    from pymongo.read_concern import ReadConcern
                    from pymongo.write_concern import WriteConcern
                    if target['identity_fields'] != ['_id']:
                        fail('MongoDB point operations require the unique _id identity.')
                    values = {name: Decimal128(value) if isinstance(value, Decimal) else value for name, value in values.items()}
                    collection = conn[config['database']][dataset['name']]
                    with timeout(30), conn.start_session() as session:
                        session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern(w='majority', wtimeout=10000), max_commit_time_ms=10000)
                        try:
                            guard()
                            current = self.validate_record(dataset, target, collection.find_one(identity, session=session, max_time_ms=10000), identity)
                            self.expected(current, before, step['action'])
                            if step['action'] == 'delete' and not set(current or {}) <= set(target['identity_fields'] + target['writable_fields']):
                                fail('Deletion recovery requires all record fields to be permitted.')
                            if step['action'] == 'create':
                                collection.insert_one({**identity, **values}, session=session)
                            elif step['action'] == 'update':
                                change = {}
                                if values:
                                    change['$set'] = values
                                if step['unset_fields']:
                                    change['$unset'] = {name: '' for name in step['unset_fields']}
                                if collection.update_one(identity, change, session=session).matched_count != 1:
                                    fail('The expected document is unavailable.', 'DATA_WRITE_CONFLICT', 409)
                            elif collection.delete_one(identity, session=session).deleted_count != 1:
                                fail('The expected document is unavailable.', 'DATA_WRITE_CONFLICT', 409)
                            after = None if step['action'] == 'delete' else self.validate_record(dataset, target, collection.find_one(identity, session=session), identity)
                            if after is not None:
                                self.check_result(dataset, after, values, step['unset_fields'])
                            result = dict(after=after, matched_records=0 if current is None else 1,
                                          affected_records=int(fingerprint(current) != fingerprint(after)))
                            guard()
                            committing = True
                            session.commit_transaction()
                            committed = True
                        except Exception:
                            if not committing:
                                try:
                                    session.abort_transaction()
                                except Exception:
                                    pass
                            raise
            return result
        except Exception as exc:
            if committed:
                return result
            # Server-reported integrity/serialization errors establish rollback;
            # a lost commit acknowledgement never authorizes a body retry.
            definite_commit_failure = (getattr(exc, 'sqlstate', None) or '')[:2] in {'23', '40'}
            if committing and not definite_commit_failure:
                raise UncertainWrite() from None
            raise RolledBack(exc.code if isinstance(exc, ApiFailure) else 'DATA_WRITE_ROLLED_BACK') from None
