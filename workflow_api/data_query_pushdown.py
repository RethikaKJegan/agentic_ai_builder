"""Trusted physical plans; model output is never used as database source text.

The exact arithmetic envelope (25 significant digits per node, <=1M inputs)
fits both Python's 38-digit arithmetic and BSON's 34-digit Decimal128 sums.
Division deliberately uses the existing bounded application executor.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import datetime
import json
import time
from decimal import Decimal

from .data_query_engine import MAX_BYTES, fail, scalar
from .google_connections import now
from .data_query_control import checkpoint, track_postgres

SERVER_ROWS = 1_000_000
SERVER_BYTES = 64_000_000
NUMERIC = {'smallint', 'integer', 'bigint', 'numeric', 'decimal', 'int', 'long'}
TEXT = {'text', 'character varying', 'varchar', 'string'}
BOOL = {'boolean', 'bool'}
DATE = {'date', 'timestamp without time zone', 'timestamp with time zone'}


def physical_plan(plan, needed, datasets, expressions, joins=None):
    engines = {datasets[d]['connection']['engine'] for d in needed}
    connections = {datasets[d]['connection']['connection_id'] for d in needed}
    reason = ''
    from .data_query_federation import federation_spec
    if len(connections) > 1 and federation_spec(plan, needed, datasets, expressions, joins):
        return dict(strategy='federated',
                    reason='PostgreSQL aggregates complete facts; bounded dimensions and complete join key domains are checked before exact aggregate merging. Dimensions and intermediates must each fit 5,000 rows and transfers together fit 2 MB.',
                    operations=['complete dimension reads', 'complete source and join checks', 'PostgreSQL partial aggregation', 'strict cross-source joins', 'weighted aggregate merge', 'global sorting and limit'],
                    max_source_rows=SERVER_ROWS, snapshot='independent source snapshots; no shared cross-database snapshot')
    if len(connections) != 1:
        reason = 'This cross-connection shape cannot use proven PostgreSQL partial aggregation; it uses complete bounded application reads.'
    elif any(
        isinstance(n, ast.Div) for tree in expressions.values() for n in ast.walk(tree)
    ):
        reason = 'Per-row division retains the application decimal arithmetic semantics.'
    elif any(len(f['types']) != 1 or f['types'][0] not in NUMERIC | TEXT | BOOL | DATE
             for fields in needed.values() for f in fields):
        reason = 'One or more field types require application scalar validation.'
    elif engines == {'mongodb'} and (plan['joins'] or any(
        f['types'][0] in DATE for fields in needed.values() for f in fields
    ) or any('.' in m['label'] or m['label'].startswith('$') or m['label'].startswith(('n_', '__')) for m in plan['metrics'])):
        reason = 'MongoDB joins and date fields require the bounded application executor.'
    if not needed or reason:
        return dict(strategy='application', reason=reason or 'Clarification has no executable operations.',
                    operations=['bounded reads', 'strict joins', 'application computation'], max_source_rows=5000,
                    snapshot='independent reads')
    engine = next(iter(engines))
    operations = ['projection', 'complete source checks']
    if plan['joins']: operations.append('strict joins')
    if plan['filters']: operations.append('filters')
    if plan['metrics']: operations.append('aggregation')
    if any(m['op'] == 'avg' for m in plan['metrics']): operations.append('exact sum/count average finalization; at most 5,000 groups')
    if plan['order_by']: operations.append('sorting')
    operations.append('result limit')
    return dict(strategy=engine, reason='Validated operations compile to a read-only database query. Numeric operands and intermediates require magnitude at most 1e16 and at most eight fractional digits.',
                operations=operations,
                max_source_rows=SERVER_ROWS,
                snapshot='read-only repeatable read' if engine == 'postgresql' else 'single-statement snapshot')


def check_deadline(deadline):
    checkpoint()
    if time.monotonic() > deadline:
        fail('Data query deadline exceeded. No partial answer returned.', 'DATA_QUERY_TIMEOUT', 504)


def bounded_rows(rows, columns, deadline):
    """Wire size is checked incrementally, before accumulating another result."""
    from .data_queries import wire
    output, size = [], 0
    for values in rows:
        check_deadline(deadline)
        record = {key: scalar(value) for key, value in zip(columns, values)}
        size += len(json.dumps(wire(record), ensure_ascii=False).encode())
        if size > MAX_BYTES:
            fail('Query result exceeds 2 MB. No partial answer returned.', 'DATA_QUERY_LIMIT', 422)
        output.append(record)
    return output, size


class PostgresCompiler:
    def __init__(self, plan, needed, datasets, joins, expressions):
        from psycopg import sql
        self.q = lambda name: sql.Identifier(name).as_string()
        self.literal = lambda value: sql.Literal(value).as_string()
        self.plan, self.params, self.guards, self.needed = plan, [], [], needed
        self.datasets = datasets
        self.fields = {f['field_id']: f for fields in needed.values() for f in fields}
        self.sources = {}
        ctes = []
        for i, (did, fields) in enumerate(needed.items()):
            source = 's' + str(i)
            self.sources[did] = source
            selected = []
            for f in fields:
                value = self.q(f['name'])
                if f['types'][0] in {'numeric', 'decimal'}: value = '(' + value + ')::numeric'
                if f['types'][0] in TEXT: value += ' COLLATE "C"'
                selected.append(value + ' AS ' + self.q(f['field_id']))
            d = datasets[did]
            ctes.append(source + ' AS NOT MATERIALIZED (SELECT ' + ', '.join(selected) + ' FROM ' +
                        self.q(d['schema']) + '.' + self.q(d['name']) + ' LIMIT ' + str(SERVER_ROWS + 1) + ')')
        current = self.sources[plan['base_dataset_id']]
        self.join_steps = []
        for i, (target, pairs, rid) in enumerate(joins):
            right = self.sources[target]
            on = ' AND '.join('l.' + self.q(a) + '=r.' + self.q(b) for a, b in pairs)
            joined = 'j' + str(i)
            self.join_steps.append((current, right, pairs, rid, on))
            ctes.append(joined + ' AS MATERIALIZED (SELECT l.*, r.* FROM ' + current + ' l JOIN ' + right + ' r ON ' + on + ')')
            current = joined
        self.prefix = 'WITH ' + ', '.join(ctes) + ' '
        self.current = current
        conditions = []
        for item in plan['filters']:
            field = self.q(item['field_id'])
            op, value = item['op'], item['value']
            if op in ('is_null', 'not_null'):
                conditions.append(field + (' IS NULL' if op == 'is_null' else ' IS NOT NULL'))
                continue
            native = self.fields[item['field_id']]['types'][0]
            valid = (type(value) in (int, float) if native in NUMERIC else
                     type(value) is bool if native in BOOL else isinstance(value, str))
            if not valid: fail('Filter value type does not match the source field.', 'DATA_QUERY_TYPE', 422)
            if native == 'date': value = datetime.date.fromisoformat(value)
            elif native in DATE: value = datetime.datetime.fromisoformat(value)
            elif native in NUMERIC: value = Decimal(str(value))
            conditions.append(field + ' ' + {'eq':'=', 'ne':'<>', 'gt':'>', 'gte':'>=', 'lt':'<', 'lte':'<='}[op] + ' %s')
            self.params.append(value)
        self.filtered = 'SELECT * FROM ' + current + (' WHERE ' + ' AND '.join(conditions) if conditions else '')
        outputs = [self.q(f) for f in (plan['group_by'] if plan['metrics'] else plan['fields'])]
        for metric in plan['metrics']:
            value = self.expr(expressions[metric['label']]) if metric['label'] in expressions else '*'
            outputs.append(metric['op'].upper() + '(' + value + ') AS ' + self.q(metric['label']))
        self.output = 'SELECT ' + ', '.join(outputs) + ' FROM (' + self.filtered + ') filtered'
        if plan['group_by']: self.output += ' GROUP BY ' + ', '.join(self.q(f) for f in plan['group_by'])
        self.columns = (plan['group_by'] + [m['label'] for m in plan['metrics']]) if plan['metrics'] else plan['fields']
        self.order = ', '.join(self.q(s['column']) + (' DESC NULLS FIRST' if s['direction'] == 'desc' else ' ASC NULLS LAST') for s in plan['order_by'])

    def expr(self, node):
        if isinstance(node, ast.Name): value = '(' + self.q(node.id) + ')::numeric'
        elif isinstance(node, ast.Constant): value = self.literal(Decimal(str(node.value)))
        elif isinstance(node, ast.UnaryOp): value = '(' + ('-' if isinstance(node.op, ast.USub) else '+') + self.expr(node.operand) + ')'
        else:
            value = '(' + self.expr(node.left) + {ast.Add:'+', ast.Sub:'-', ast.Mult:'*'}[type(node.op)] + self.expr(node.right) + ')'
        self.guards.append(self.numeric_guard(value))
        return value

    @staticmethod
    def numeric_guard(value):
        return '(' + value + ' IS NOT NULL AND (' + value + "::text IN ('NaN','Infinity','-Infinity') OR abs(" + value + ') > 1e16 OR round(' + value + ',8) <> ' + value + '))'

    def execute(self, conn, deadline):
        checks, counts = [], {}
        with conn.cursor() as cur:
            def fetch(query, params=()):
                check_deadline(deadline)
                remaining = max(1, min(10000, int((deadline - time.monotonic()) * 1000)))
                cur.execute("SELECT set_config('statement_timeout', %s, true)", (str(remaining),))
                cur.execute(self.prefix + query, params)
                return cur.fetchone()
            # All checks precede filtering, preserving Phase 3 whole-source semantics.
            source_bytes = 0
            for did, source in self.sources.items():
                checkpoint('Checking complete PostgreSQL sources')
                dataset = self.datasets[did]
                cur.execute('SELECT a.attname, format_type(a.atttypid, NULL) FROM pg_attribute a '
                            'JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace '
                            'WHERE n.nspname=%s AND c.relname=%s AND a.attnum>0 AND NOT a.attisdropped '
                            'AND a.attname=ANY(%s)',
                            (dataset['schema'], dataset['name'], [f['name'] for f in self.needed[did]]))
                actual_types = dict(cur.fetchall())
                aliases = {'decimal':'numeric', 'varchar':'character varying', 'int':'integer', 'bool':'boolean'}
                if any(actual_types.get(f['name']) != aliases.get(f['types'][0], f['types'][0]) for f in self.needed[did]):
                    fail('Source field types changed. Refresh metadata and create a new plan.', 'DATA_QUERY_STALE', 409)
                count = fetch('SELECT count(*) FROM (SELECT 1 FROM ' + source + ' LIMIT ' + str(SERVER_ROWS + 1) + ') bounded')[0]
                if count > SERVER_ROWS: fail('A source exceeds the one-million-row database budget. No partial answer returned.', 'DATA_QUERY_LIMIT', 422)
                counts[did] = count
                source_bytes += fetch('SELECT coalesce(sum(pg_column_size(s)),0) FROM ' + source + ' s')[0]
                if source_bytes > SERVER_BYTES:
                    fail('Projected source data exceeds the 64 MB database working-set budget. No partial answer returned.', 'DATA_QUERY_LIMIT', 422)
                guards = []
                for fid, f in self.fields.items():
                    if f not in self.needed[did]: continue
                    value = self.q(fid)
                    if f['types'][0] in NUMERIC: guards.append(self.numeric_guard(value))
                    elif f['types'][0] in TEXT: guards.append('octet_length(' + value + ') > 16000')
                    elif f['types'][0] in DATE:
                        guards.append('(' + value + " < '0001-01-01' OR " + value + " >= '10000-01-01')")
                if guards and fetch('SELECT EXISTS(SELECT 1 FROM ' + source + ' WHERE ' + ' OR '.join(guards) + ')')[0]:
                    fail('Source values exceed the exact pushdown numeric or scalar envelope. No partial answer returned.', 'DATA_QUERY_TYPE', 422)
            for left, right, pairs, rid, on in self.join_steps:
                checkpoint('Validating complete PostgreSQL joins')
                keys = ', '.join(self.q(b) for _, b in pairs)
                nulls = ' OR '.join(self.q(b) + ' IS NULL' for _, b in pairs)
                if fetch('SELECT EXISTS(SELECT 1 FROM ' + right + ' GROUP BY ' + keys + ' HAVING count(*) > 1 OR ' + nulls + ')')[0]:
                    fail('Join target keys must be unique and non-null.', 'DATA_QUERY_JOIN_INVALID', 422)
                if fetch('SELECT EXISTS(SELECT 1 FROM ' + left + ' l WHERE NOT EXISTS(SELECT 1 FROM ' + right + ' r WHERE ' + on + '))')[0]:
                    fail('Join source contains null or unmatched keys. No incomplete total returned.', 'DATA_QUERY_JOIN_INVALID', 422)
                source_count = fetch('SELECT count(*) FROM ' + left)[0]
                target_count = fetch('SELECT count(*) FROM ' + right)[0]
                checks.append(dict(relationship_id=rid, source_rows=source_count, target_rows=target_count, matched_rows=source_count, target_unique=True, checked_at=now()))
            checkpoint('Calculating PostgreSQL result')
            if self.guards and fetch('SELECT EXISTS(SELECT 1 FROM (' + self.filtered + ') filtered WHERE ' + ' OR '.join(self.guards) + ')', self.params)[0]:
                fail('Arithmetic exceeds the exact pushdown envelope. No partial answer returned.', 'DATA_QUERY_TYPE', 422)
            matched = fetch('SELECT count(*) FROM (' + self.filtered + ') filtered', self.params)[0]
            total = fetch('SELECT count(*) FROM (' + self.output + ') output', self.params)[0]
            query = self.output + (' ORDER BY ' + self.order if self.order else '') + ' LIMIT ' + str(self.plan['limit'])
            check_deadline(deadline)
            with conn.cursor(name='data_pushdown_result') as result_cursor:
                result_cursor.execute(self.prefix + query, self.params)
                def values():
                    while True:
                        batch = result_cursor.fetchmany(25)
                        if not batch: break
                        yield from batch
                rows, size = bounded_rows(values(), self.columns, deadline)
        return rows, total, matched, counts, checks, size

@contextmanager
def postgres_snapshot(manager, config):
    with manager.adapter.connection(config) as conn:
        # Health reads must finish before opening the validation/result snapshot.
        conn.rollback()
        from psycopg import IsolationLevel
        conn.isolation_level = IsolationLevel.REPEATABLE_READ
        conn.read_only = True
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '10s'")
            cur.execute("SET LOCAL lock_timeout = '3s'")
            cur.execute("SET LOCAL idle_in_transaction_session_timeout = '45s'")
            cur.execute("SET LOCAL work_mem = '8MB'")
            cur.execute("SET LOCAL timezone = 'UTC'")
        with track_postgres(conn):
            yield conn


def execute_postgres(manager, config, plan, needed, datasets, joins, expressions, deadline):
    compiler = PostgresCompiler(plan, needed, datasets, joins, expressions)
    with postgres_snapshot(manager, config) as conn:
        return compiler.execute(conn, deadline)


class MongoCompiler:
    def __init__(self, plan, fields, expressions):
        from bson.decimal128 import Decimal128
        self.decimal = lambda value: {'$literal': Decimal128(str(value))}
        self.fields = {f['field_id']: f for f in fields}
        self.guards = []
        self.columns = (plan['group_by'] + [m['label'] for m in plan['metrics']]) if plan['metrics'] else plan['fields']
        checks, projection = [], {'_id': 0}
        for fid, f in self.fields.items():
            value, native = '$' + f['name'], f['types'][0]
            kind = {'$type': value}
            missing = {'$in': [kind, ['missing', 'null']]}
            allowed = (['decimal'] if native in {'numeric', 'decimal'} else ['int', 'long']) if native in NUMERIC else ['bool'] if native in BOOL else ['string']
            checks.append({'$not': [{'$or': [missing, {'$in': [kind, allowed]}]}]})
            if native in NUMERIC:
                projection[fid] = self.convert(value) if native in {'numeric', 'decimal'} else {'$ifNull': [value, None]}
                checks.append(self.numeric_guard(self.convert(value)))
            else:
                projection[fid] = {'$ifNull': [value, None]}
                if native in TEXT:
                    checks.append({'$cond': [{'$eq': [kind, 'string']}, {'$gt': [{'$strLenBytes': value}, 16000]}, False]})
        conditions = []
        for item in plan['filters']:
            value = '$' + item['field_id']
            op, constant = item['op'], item['value']
            if op in ('is_null', 'not_null'):
                conditions.append({'$eq' if op == 'is_null' else '$ne': [value, None]})
            else:
                native = self.fields[item['field_id']]['types'][0]
                valid = (type(constant) in (int, float) if native in NUMERIC else type(constant) is bool if native in BOOL else isinstance(constant, str))
                if not valid: fail('Filter value type does not match the source field.', 'DATA_QUERY_TYPE', 422)
                rhs = self.decimal(constant) if native in NUMERIC else {'$literal': constant}
                conditions.append({'$and': [{'$ne': [value, None]}, {'$' + op: [value, rhs]}]})
        filtered = [{'$project': projection}]
        if conditions: filtered.append({'$match': {'$expr': {'$and': conditions}}})
        result = []
        if plan['metrics']:
            group = {'_id': {f: '$' + f for f in plan['group_by']} if plan['group_by'] else None}
            for metric in plan['metrics']:
                expr = self.expr(expressions[metric['label']]) if metric['label'] in expressions else None
                op = metric['op']
                if op == 'count': group[metric['label']] = {'$sum': {'$cond': [{'$ne': [expr, None]}, 1, 0]} if expr else 1}
                else:
                    group[metric['label']] = {'$' + op: expr}
                    group['n_' + metric['label']] = {'$sum': {'$cond': [{'$ne': [expr, None]}, 1, 0]}}
            result.append({'$group': group})
            projected = {'_id': 0, **{f: '$_id.' + f for f in plan['group_by']}}
            for metric in plan['metrics']:
                label = metric['label']
                projected[label] = '$' + label if metric['op'] == 'count' else {'$cond': [{'$eq': ['$n_' + label, 0]}, None, '$' + label]}
            result.append({'$project': projected})
        else: result.append({'$project': {'_id': 0, **{f: 1 for f in plan['fields']}}})
        result.append({'$setWindowFields': {'output': {'__total': {'$count': {}, 'window': {'documents': ['unbounded', 'unbounded']}}}}})
        # Mongo's native null ordering is opposite the application ordering.
        if plan['order_by']:
            result.append({'$set': {'__null' + str(i): {'$eq': ['$' + s['column'], None]} for i, s in enumerate(plan['order_by'])}})
            ordering = {}
            for i, s in enumerate(plan['order_by']):
                direction = -1 if s['direction'] == 'desc' else 1
                ordering['__null' + str(i)] = direction
                ordering[s['column']] = direction
            result.append({'$sort': ordering})
        result.append({'$limit': plan['limit']})
        self.pipeline = [{'$limit': SERVER_ROWS + 1}, {'$facet': {
            'source': [{'$group': {'_id': None, 'count': {'$sum': 1}, 'invalid': {'$max': {'$cond': [{'$or': checks}, 1, 0]}}}}],
            'matched': filtered + [{'$count': 'count'}],
            'arithmetic': filtered + ([{'$match': {'$expr': {'$or': self.guards}}}, {'$limit': 1}, {'$project': {'_id': 0, 'invalid': {'$literal': True}}}] if self.guards else [{'$limit': 0}]),
            'rows': filtered + result,
        }}]
        # $limit:0 is invalid in aggregation; a constant-false match is explicit.
        if not self.guards: self.pipeline[1]['$facet']['arithmetic'] = [{'$match': {'$expr': {'$literal': False}}}]
        self.plan = plan

    @staticmethod
    def convert(value):
        return {'$convert': {'input': value, 'to': 'decimal', 'onError': None, 'onNull': None}}

    def numeric_guard(self, value):
        # Stringifying first handles non-finite Decimal128 without arithmetic on it.
        return {'$cond': [{'$in': [{'$toString': value}, ['NaN', 'Infinity', '-Infinity']]}, True,
                          {'$or': [{'$gt': [{'$abs': value}, self.decimal('1e16')]}, {'$ne': [{'$round': [value, 8]}, value]}]}]}

    def expr(self, node):
        if isinstance(node, ast.Name): value = self.convert('$' + node.id)
        elif isinstance(node, ast.Constant): value = self.decimal(node.value)
        elif isinstance(node, ast.UnaryOp):
            operand = self.expr(node.operand)
            value = {'$multiply': [self.decimal(-1), operand]} if isinstance(node.op, ast.USub) else operand
        else:
            value = {{ast.Add:'$add', ast.Sub:'$subtract', ast.Mult:'$multiply'}[type(node.op)]: [self.expr(node.left), self.expr(node.right)]}
        self.guards.append(self.numeric_guard(value))
        return value

    def execute(self, collection, deadline):
        from pymongo import timeout
        from pymongo.read_concern import ReadConcern
        checkpoint('Reading and checking MongoDB snapshot')
        check_deadline(deadline)
        with timeout(max(.001, min(12, deadline - time.monotonic()))):
            cursor = collection.with_options(read_concern=ReadConcern('snapshot')).aggregate(
                self.pipeline, allowDiskUse=False, maxTimeMS=max(1, min(10000, int((deadline-time.monotonic())*1000))),
                collation={'locale': 'simple'}, batchSize=1)
            try: result = next(cursor)
            finally: cursor.close()
        source = result['source'][0] if result['source'] else {'count': 0, 'invalid': 0}
        if source['count'] > SERVER_ROWS: fail('A source exceeds the one-million-row database budget. No partial answer returned.', 'DATA_QUERY_LIMIT', 422)
        if source['invalid'] or result['arithmetic']: fail('Source or arithmetic exceeds supported scalar types or the exact decimal envelope. No partial answer returned.', 'DATA_QUERY_TYPE', 422)
        matched = result['matched'][0]['count'] if result['matched'] else 0
        values = result['rows']
        total = values[0]['__total'] if values else 0
        if not values and self.plan['metrics'] and not self.plan['group_by']:
            values = [{m['label']: 0 if m['op'] == 'count' else None for m in self.plan['metrics']}]
            total = 1
        rows, size = bounded_rows(([r.get(c) for c in self.columns] for r in values), self.columns, deadline)
        return rows, total, matched, source['count'], size


def execute_mongo(manager, config, plan, needed, datasets, joins, expressions, deadline):
    did = next(iter(needed))
    compiler = MongoCompiler(plan, needed[did], expressions)
    with manager.adapter.connection(config) as conn:
        rows, total, matched, count, size = compiler.execute(conn[config['database']][datasets[did]['name']], deadline)
    return rows, total, matched, {did: count}, [], size
