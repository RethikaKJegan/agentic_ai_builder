"""Restricted scalar computation. No SQL, scripts or model text are evaluated."""
from __future__ import annotations

import ast
import datetime
import math
from decimal import Decimal, InvalidOperation, localcontext
from .service import ApiFailure
from .data_query_control import checkpoint

MAX_ROWS = 5000
MAX_BYTES = 2_000_000


def fail(message, code='DATA_QUERY_INVALID', status=400):
    raise ApiFailure(code, message, status)


def scalar(value):
    if value is None or type(value) in (str, bool, int):
        if isinstance(value, str) and len(value.encode()) > 16000:
            fail('A field value exceeds the supported size.', 'DATA_QUERY_LIMIT', 422)
        return value
    if isinstance(value, float) and math.isfinite(value):
        return Decimal(str(value))
    if isinstance(value, Decimal) and value.is_finite():
        return value
    if isinstance(value, datetime.datetime):
        if value.tzinfo is not None: value = value.astimezone(datetime.timezone.utc)
        return value.isoformat()
    if isinstance(value, datetime.date): return value.isoformat()
    # Mongo Decimal128 is converted explicitly; arrays, objects and ObjectIds are not guessed.
    if type(value).__module__ == 'bson.decimal128':
        return scalar(value.to_decimal())
    fail('A selected field contains unsupported or non-finite values. Select scalar fields.', 'DATA_QUERY_TYPE', 422)


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        fail('An arithmetic expression encountered a nonnumeric value.', 'DATA_QUERY_TYPE', 422)
    return Decimal(value)


def expression(text, field_ids):
    if not text or len(text) > 1000:
        fail('Supply an arithmetic expression for this metric.')
    try:
        tree = ast.parse(text, mode='eval')
    except (SyntaxError, ValueError, RecursionError):
        fail('Metric expressions support field IDs, numeric constants and + - * / only.')
    nodes = list(ast.walk(tree))
    if len(nodes) > 100:
        fail('Metric expression is too complex.')
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.Constant,
               ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd)
    fields = set()
    for node in nodes:
        if not isinstance(node, allowed):
            fail('Metric expressions support field IDs, numeric constants and + - * / only.')
        if isinstance(node, ast.Name):
            if node.id not in field_ids: fail('Metric references an unavailable field.')
            fields.add(node.id)
        if isinstance(node, ast.Constant) and (type(node.value) not in (int, float) or not Decimal(str(node.value)).is_finite() or abs(Decimal(str(node.value))) > Decimal('1e30')):
            fail('Metric constants must be finite numbers.')
    return tree.body, fields


def calculate(node, row):
    if isinstance(node, ast.Name):
        value = row.get(node.id)
        return None if value is None else number(value)
    if isinstance(node, ast.Constant): return Decimal(str(node.value))
    if isinstance(node, ast.UnaryOp):
        value = calculate(node.operand, row)
        return None if value is None else -value if isinstance(node.op, ast.USub) else value
    left, right = calculate(node.left, row), calculate(node.right, row)
    if left is None or right is None: return None
    try:
        with localcontext() as ctx:
            ctx.prec = 38
            if isinstance(node.op, ast.Add): value = left + right
            elif isinstance(node.op, ast.Sub): value = left - right
            elif isinstance(node.op, ast.Mult): value = left * right
            else: value = left / right
        if not value.is_finite() or abs(value) > Decimal('1e30'):
            fail('Arithmetic result exceeds supported precision.', 'DATA_QUERY_TYPE', 422)
        return value
    except (ArithmeticError, InvalidOperation):
        fail('Arithmetic failed, including possible division by zero.', 'DATA_QUERY_TYPE', 422)


def key(row, fields):
    values = tuple(row.get(f) for f in fields)
    if any(v is None for v in values): return None
    # Boolean/integer and text/integer keys must never silently compare equal.
    return tuple(('number' if type(v) is int or isinstance(v, Decimal) else type(v).__name__, v) for v in values)


def join_rows(left, right, pairs):
    index = {}
    for row in right:
        checkpoint()
        k = key(row, [b for _, b in pairs])
        if k is None: fail('Join target contains null keys; a complete unique target is required.', 'DATA_QUERY_JOIN_INVALID', 422)
        if k in index: fail('Join target keys are duplicated. Joining could inflate totals.', 'DATA_QUERY_JOIN_INVALID', 422)
        index[k] = row
    result = []
    for row in left:
        checkpoint()
        k = key(row, [a for a, _ in pairs])
        if k is None or k not in index:
            fail('Join source contains null or unmatched keys. No incomplete total was returned.', 'DATA_QUERY_JOIN_INVALID', 422)
        result.append({**row, **index[k]})
    return result, dict(source_rows=len(left), target_rows=len(right), matched_rows=len(result), target_unique=True)


def filtered(row, filters):
    checkpoint()
    for item in filters:
        a, b, op = row.get(item['field_id']), item['value'], item['op']
        if op == 'is_null': good = a is None
        elif op == 'not_null': good = a is not None
        elif a is None or b is None: good = False
        else:
            if type(b) in (float, int): b = Decimal(str(b))
            if (isinstance(a, (int, Decimal)) and not isinstance(a, bool)) != isinstance(b, Decimal) or isinstance(a, bool) != isinstance(b, bool):
                fail('Filter value type does not match the source field.', 'DATA_QUERY_TYPE', 422)
            try:
                if op == 'eq': good = a == b
                elif op == 'ne': good = a != b
                elif op == 'gt': good = a > b
                elif op == 'gte': good = a >= b
                elif op == 'lt': good = a < b
                else: good = a <= b
            except TypeError: fail('Filter values are not comparable.', 'DATA_QUERY_TYPE', 422)
        if not good: return False
    return True


def compute(rows, plan, expressions):
    rows = [r for r in rows if filtered(r, plan['filters'])]
    matched = len(rows)
    if plan['metrics']:
        groups = {}
        for row in rows:
            k = tuple((type(row.get(f)).__name__, row.get(f)) for f in plan['group_by'])
            groups.setdefault(k, []).append(row)
        if not plan['group_by'] and not rows: groups[()] = []
        output = []
        for group in groups.values():
            checkpoint()
            record = {f: group[0].get(f) for f in plan['group_by']}
            for metric in plan['metrics']:
                expr = expressions.get(metric['label'])
                values = [calculate(expr, r) for r in group] if expr else []
                values = [v for v in values if v is not None]
                op = metric['op']
                if op == 'count': value = len(values) if expr else len(group)
                elif not values: value = None
                elif op in ('sum', 'avg'):
                    with localcontext() as ctx:
                        ctx.prec = 38
                        value = sum(values, Decimal(0))
                        if op == 'avg': value /= len(values)
                elif op == 'min': value = min(values)
                else: value = max(values)
                record[metric['label']] = value
            output.append(record)
    else:
        output = [{f: r.get(f) for f in plan['fields']} for r in rows]
    for sort in reversed(plan['order_by']):
        try: output.sort(key=lambda r:(r.get(sort['column']) is None, r.get(sort['column'])), reverse=sort['direction']=='desc')
        except TypeError: fail('Sort column contains incompatible types.', 'DATA_QUERY_TYPE', 422)
    return output[:plan['limit']], len(output), matched
