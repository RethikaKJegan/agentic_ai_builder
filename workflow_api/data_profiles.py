"""Shared bounded database statistics; sampled records are never persisted."""
from collections import Counter
import hashlib
import json
import math

SAMPLE_ROWS = 100


def token(value):
    # bool, integer, decimal and text never share a key by implicit coercion.
    if value is None or isinstance(value, (dict, list, tuple)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return hashlib.sha256(json.dumps([type(value).__name__, str(value)], ensure_ascii=True).encode()).hexdigest()


MISSING = object()


def lookup(row, name):
    if name in row:return row[name]
    parts=name.replace('[]','.*').split('.')
    def walk(value,index):
        if index==len(parts):return value
        if parts[index]=='*':
            if not isinstance(value,list):return MISSING
            found=[walk(v,index+1) for v in value]
            return [v for v in found if v is not MISSING] if found else MISSING
        if not isinstance(value,dict) or parts[index] not in value:return MISSING
        return walk(value[parts[index]],index+1)
    return walk(row,0)


def summarize(rows, fields):
    result = {}
    for field in fields:
        name = field['name']
        values = [lookup(row,name) for row in rows]
        values = [value for value in values if value is not MISSING]
        hashes = [token(v) for v in values if v is not None]
        supported = [v for v in hashes if v is not None]
        counts = Counter(supported)
        numeric = [v for v in values if type(v) in (int, float) and math.isfinite(v)]
        anomalies = 0
        if len(numeric) >= 4:
            ordered = sorted(numeric)
            q1, q3 = ordered[len(ordered)//4], ordered[(3*len(ordered))//4]
            anomalies = sum(v < q1-1.5*(q3-q1) or v > q3+1.5*(q3-q1) for v in numeric)
        n, present = len(rows), len(values)
        result[field['field_id']] = dict(basis='bounded_sample', sample_size=n, present=present,
            missing=n-present, nulls=sum(v is None for v in values),
            null_rate=sum(v is None for v in values)/present if present else None,
            distinct=len(counts), comparable=len(supported),
            uniqueness=len(counts)/len(supported) if supported else None,
            distribution=[dict(value_hash=k, count=v) for k,v in counts.most_common(10)],
            key_hashes=sorted(counts), unsupported_values=len(hashes)-len(supported),
            anomalies=dict(method='sample_iqr', count=anomalies) if len(numeric)>=4 else None)
    return result


def overlap(left, right):
    """Directional sample coverage is not population referential integrity."""
    a, b = set(left.get('key_hashes', [])), set(right.get('key_hashes', []))
    return dict(basis='bounded_sample', overlap=len(a & b), source_distinct=len(a),
                target_distinct=len(b), referential_consistency=len(a & b)/len(a) if a else None,
                population_verified=False)


def composite(rows, fields):
    keys = []
    for row in rows:
        parts = [token(row.get(name)) for name in fields]
        if all(parts):
            keys.append(hashlib.sha256(json.dumps(parts).encode()).hexdigest())
    return dict(basis='bounded_sample', sample_size=len(rows), comparable=len(keys), key_hashes=sorted(set(keys)))
