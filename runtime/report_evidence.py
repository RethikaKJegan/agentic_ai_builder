"""Lossless model-transport projection; durable evidence remains canonical."""
from copy import deepcopy
import json


def compact(data):
    """Intern repeated large values; never sample or omit rule outcomes.

    Replacement paths identify actual references so source objects resembling
    reference markers round-trip without ambiguity.
    """
    tables = []
    def tabulate(value, path):
        if isinstance(value, list) and len(value) >= 4 and all(isinstance(item, dict) for item in value):
            columns = list(value[0])
            if columns and all(set(item) == set(columns) for item in value):
                tables.append(path)
                return {'$columns': columns, '$rows': [[tabulate(item[key], [*path, '$rows', n, j]) for j, key in enumerate(columns)] for n, item in enumerate(value)]}
        if isinstance(value, dict):return {key: tabulate(item, [*path, key]) for key, item in value.items()}
        if isinstance(value, list):return [tabulate(item, [*path, n]) for n, item in enumerate(value)]
        return deepcopy(value)
    original = data
    data = tabulate(data, [])
    counts = {}

    def encoded(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

    def collect(value):
        text = encoded(value)
        if len(text) >= 120:
            counts[text] = counts.get(text, 0) + 1
        if isinstance(value, dict):
            for item in value.values():collect(item)
        elif isinstance(value, list):
            for item in value:collect(item)

    collect(data)
    tokens = {text: f'v{n}' for n, (text, count) in enumerate(counts.items()) if count > 1}
    if not tokens and not tables:return deepcopy(original)
    dictionary = {}
    paths = []

    def project(value, path):
        token = tokens.get(encoded(value))
        if token is not None:
            dictionary[token] = deepcopy(value)
            paths.append(path)
            return {'$shared_ref': token}
        if isinstance(value, dict):return {key: project(item, [*path, key]) for key, item in value.items()}
        if isinstance(value, list):return [project(item, [*path, n]) for n, item in enumerate(value)]
        return deepcopy(value)

    projected = project(data, [])
    packet = {'transport': 'shared_evidence_v1', 'data': projected,
              'evidence_dictionary': dictionary, 'reference_paths': paths, 'table_paths': tables}
    return packet if len(encoded(packet)) < len(encoded(original)) else deepcopy(original)


def expand(packet):
    """Verify exact round-trip equivalence, including reference-looking input."""
    if not isinstance(packet, dict) or packet.get('transport') != 'shared_evidence_v1':return deepcopy(packet)
    data = deepcopy(packet['data'])
    for path in packet['reference_paths']:
        parent = data
        for key in path[:-1]:parent = parent[key]
        ref = parent[path[-1]] if path else data
        original = deepcopy(packet['evidence_dictionary'][ref['$shared_ref']])
        if path:parent[path[-1]] = original
        else:data = original
    # Nested table paths use packed coordinates, so restore deepest first.
    for path in sorted(packet.get('table_paths', []), key=len, reverse=True):
        parent = data
        for key in path[:-1]:parent = parent[key]
        table = parent[path[-1]] if path else data
        rows = [dict(zip(table['$columns'], row)) for row in table['$rows']]
        if path:parent[path[-1]] = rows
        else:data = rows
    return data
