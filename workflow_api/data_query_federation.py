"""Exact bounded aggregate states and trusted cross-connection coordination.

Only PostgreSQL fact prefixes and complete bounded dimension reads are optimized.
No SQL or pipeline supplied by the model/client is accepted here.
"""
from __future__ import annotations

import ast
import time
from decimal import Decimal, localcontext

from .data_query_engine import MAX_BYTES, MAX_ROWS, fail, filtered, join_rows
from .data_query_pushdown import (
    NUMERIC, TEXT, BOOL, DATE, PostgresCompiler, check_deadline,
    execute_postgres, execute_mongo, postgres_snapshot,
)
from .google_connections import now
from .data_query_control import checkpoint


def supported_fields(needed, datasets):
    for did, fields in needed.items():
        engine = datasets[did]['connection']['engine']
        if engine not in ('postgresql', 'mongodb'):
            return False
        allowed = NUMERIC | TEXT | BOOL | (DATE if engine == 'postgresql' else set())
        if any(len(f['types']) != 1 or f['types'][0] not in allowed for f in fields):
            return False
    return True


def federation_spec(plan, needed, datasets, expressions, joins):
    """Return a partition only when algebra and connection ordering are proven."""
    if not joins or not plan['metrics'] or not supported_fields(needed, datasets):
        return None
    if any(isinstance(n, ast.Div) for tree in expressions.values() for n in ast.walk(tree)):
        return None
    base = plan['base_dataset_id']
    connection = datasets[base]['connection']
    if connection['engine'] != 'postgresql':
        return None
    prefix, local, remote = [base], [], []
    for join in joins:
        target = join[0]
        same = datasets[target]['connection']['connection_id'] == connection['connection_id']
        if same:
            if remote:
                return None
            prefix.append(target)
            local.append(join)
        else:
            remote.append(join)
    if not remote:
        return None
    prefix_fields = {f['field_id'] for d in prefix for f in needed[d]}
    if any(n.id not in prefix_fields for tree in expressions.values() for n in ast.walk(tree) if isinstance(n, ast.Name)):
        return None
    frontier = sorted({a for _, pairs, _ in remote for a, _ in pairs if a in prefix_fields})
    if not frontier:
        return None
    return dict(prefix=prefix, local=local, remote=remote, frontier=frontier, fields=prefix_fields)


def state_plan(plan, group_by, reserved=()):
    """Use internal labels independent of user labels and field identifiers."""
    occupied = set(group_by) | set(reserved) | {m['label'] for m in plan['metrics']}
    prefix = 'phase5_'
    while any(name.startswith(prefix) for name in occupied):
        prefix += 'x_'
    weight = prefix + 'rows'
    metrics = [dict(label=weight, op='count', expression='')]
    specs = []
    for i, metric in enumerate(plan['metrics']):
        value, count = prefix + str(i) + '_value', prefix + str(i) + '_count'
        metrics.append(dict(label=value, op='sum' if metric['op'] == 'avg' else metric['op'], expression=metric['expression']))
        if metric['op'] in ('sum', 'avg', 'min', 'max'):
            metrics.append(dict(label=count, op='count', expression=metric['expression']))
        specs.append((metric, value, count))
    return {**plan, 'fields': [], 'group_by': group_by, 'metrics': metrics,
            'order_by': [], 'limit': MAX_ROWS + 1}, specs, weight


def partial_expressions(specs, expressions):
    output = {}
    for metric, value, count in specs:
        tree = expressions.get(metric['label'])
        if tree is not None:
            output[value] = tree
            if metric['op'] in ('sum', 'avg', 'min', 'max'):
                output[count] = tree
    return output


def merge_states(rows, plan, specs, weight, deadline):
    groups = {}
    matched = 0
    for row in rows:
        check_deadline(deadline)
        if not filtered(row, plan['filters']):
            continue
        matched += int(row[weight])
        k = tuple((type(row.get(f)).__name__, row.get(f)) for f in plan['group_by'])
        if k not in groups:
            groups[k] = ({f: row.get(f) for f in plan['group_by']}, [[None, 0] for _ in specs])
        _, states = groups[k]
        for state, (metric, value_key, count_key) in zip(states, specs):
            value = row[value_key]
            count = int(row[value_key]) if metric['op'] == 'count' else int(row[count_key])
            if metric['op'] == 'count':
                state[1] += count
            elif count:
                with localcontext() as ctx:
                    ctx.prec = 38
                    if state[0] is None:
                        state[0] = value
                    elif metric['op'] in ('sum', 'avg'):
                        state[0] += value
                    elif metric['op'] == 'min':
                        state[0] = min(state[0], value)
                    else:
                        state[0] = max(state[0], value)
                state[1] += count
    if not groups and not plan['group_by']:
        groups[()] = ({}, [[None, 0] for _ in specs])
    output = []
    for record, states in groups.values():
        check_deadline(deadline)
        for (metric, _, _), (value, count) in zip(specs, states):
            with localcontext() as ctx:
                ctx.prec = 38
                record[metric['label']] = count if metric['op'] == 'count' else (
                    None if not count else value / Decimal(count) if metric['op'] == 'avg' else value)
        output.append(record)
    for sort in reversed(plan['order_by']):
        try:
            output.sort(key=lambda r: (r[sort['column']] is None, r[sort['column']]), reverse=sort['direction'] == 'desc')
        except TypeError:
            fail('Sort column contains incompatible types.', 'DATA_QUERY_TYPE', 422)
    check_deadline(deadline)
    return output[:plan['limit']], len(output), matched


def bounded_intermediate(result):
    if result[1] > MAX_ROWS:
        fail('A dimension or aggregate intermediate exceeds 5,000 rows. No partial answer returned.', 'DATA_QUERY_LIMIT', 422)
    return result


def execute_average(manager, config, plan, needed, datasets, joins, expressions, deadline):
    partial, specs, weight = state_plan(plan, plan['group_by'], (f['field_id'] for fs in needed.values() for f in fs))
    exprs = partial_expressions(specs, expressions)
    executor = execute_postgres if datasets[plan['base_dataset_id']]['connection']['engine'] == 'postgresql' else execute_mongo
    raw = bounded_intermediate(executor(manager, config, partial, needed, datasets, joins, exprs, deadline))
    rows, total, matched = merge_states(raw[0], {**plan, 'filters': []}, specs, weight, deadline)
    return rows, total, matched, raw[3], raw[4], raw[5], len(raw[0])


def execute_federated(manager, configs, plan, needed, datasets, joins, expressions, deadline, fresh):
    spec = federation_spec(plan, needed, datasets, expressions, joins)
    if spec is None:
        fail('The federated plan is no longer supported. Create a fresh plan.', 'DATA_QUERY_STALE', 409)
    counts, checks, fragments, dimensions = {}, [], [], {}
    transferred_rows, transferred_bytes = 0, 0

    def account(result, ids, engine, snapshot, purpose, started, clock):
        nonlocal transferred_rows, transferred_bytes
        bounded_intermediate(result)
        transferred_rows += len(result[0])
        transferred_bytes += result[5]
        if transferred_bytes > MAX_BYTES:
            fail('Combined intermediate transfers exceed 2 MB. No partial answer returned.', 'DATA_QUERY_LIMIT', 422)
        counts.update(result[3])
        fragments.append(dict(dataset_ids=ids, engine=engine, purpose=purpose, snapshot=snapshot,
                              started_at=started, finished_at=now(), duration_ms=round((time.monotonic()-clock)*1000),
                              source_rows=sum(result[3].values()), transferred_rows=len(result[0]), transferred_bytes=result[5]))
        checkpoint('Completed '+purpose, fragment=fragments[-1])
        fresh()
        return result[0]

    # Complete dimension snapshots are reused for BOTH validation and final merging.
    for target, _, _ in spec['remote']:
        fresh()
        started, clock = now(), time.monotonic()
        engine = datasets[target]['connection']['engine']
        projection = {**plan, 'base_dataset_id': target, 'joins': [], 'metrics': [], 'filters': [],
                      'group_by': [], 'fields': [f['field_id'] for f in needed[target]], 'order_by': [], 'limit': MAX_ROWS+1}
        executor = execute_postgres if engine == 'postgresql' else execute_mongo
        result = executor(manager, configs[target], projection, {target: needed[target]}, datasets, [], {}, deadline)
        snapshot = 'read-only repeatable read' if engine == 'postgresql' else 'single-statement snapshot'
        dimensions[target] = account(result, [target], engine, snapshot, 'complete dimension', started, clock)

    prefix_needed = {d: needed[d] for d in spec['prefix']}
    # Include frontier keys even when not output, so cross-source joining commutes
    # with early aggregation. Include prefix output keys to preserve final groups.
    grouping = sorted(set(spec['frontier']) | (set(plan['group_by']) & spec['fields']))
    partial, specs, weight = state_plan(plan, grouping, (f['field_id'] for fs in needed.values() for f in fs))
    partial['joins'] = plan['joins'][:len(spec['local'])]
    partial['filters'] = [f for f in plan['filters'] if f['field_id'] in spec['fields']]
    exprs = partial_expressions(specs, expressions)
    domain = {**partial, 'filters': [], 'group_by': spec['frontier'],
              'metrics': [dict(label=weight, op='count', expression='')]}
    fresh()
    with postgres_snapshot(manager, configs[plan['base_dataset_id']]) as conn:
        started, clock = now(), time.monotonic()
        domain_result = PostgresCompiler(domain, prefix_needed, datasets, spec['local'], {}).execute(conn, deadline)
        domain_rows = account(domain_result, spec['prefix'], 'postgresql', 'read-only repeatable read', 'complete join key domain', started, clock)
        checks.extend(domain_result[4])
        # Strict checks operate on complete keys before ANY local/dimension filters.
        for target, pairs, rid in spec['remote']:
            check_deadline(deadline)
            source_count = sum(int(r[weight]) for r in domain_rows)
            domain_rows, check = join_rows(domain_rows, dimensions[target], pairs)
            checks.append(dict(relationship_id=rid, source_rows=source_count, matched_rows=source_count,
                               target_rows=check['target_rows'], target_unique=True, checked_at=now()))
        started, clock = now(), time.monotonic()
        result = PostgresCompiler(partial, prefix_needed, datasets, spec['local'], exprs).execute(conn, deadline)
        partial_rows = account(result, spec['prefix'], 'postgresql', 'read-only repeatable read', 'partial aggregates', started, clock)
    for target, pairs, _ in spec['remote']:
        check_deadline(deadline)
        partial_rows, _ = join_rows(partial_rows, dimensions[target], pairs)
    merge_plan = {**plan, 'filters': [f for f in plan['filters'] if f['field_id'] not in spec['fields']]}
    checkpoint('Merging complete weighted aggregates')
    rows, total, matched = merge_states(partial_rows, merge_plan, specs, weight, deadline)
    fresh()
    return rows, total, matched, counts, checks, transferred_bytes, transferred_rows, fragments
