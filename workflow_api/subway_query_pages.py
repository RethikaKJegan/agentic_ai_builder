"""Private bounded spill state and display pages for complete source queries."""
from decimal import Decimal, localcontext
import json
import pickle
import sqlite3
import tempfile
from pathlib import Path


def typed_key(value):
    """Stable numeric equivalence without rounding group identities."""
    if value is None:
        return ('', '')
    kind, item = value
    if kind == 'number':
        with localcontext() as context:
            context.prec = max(context.prec, len(item.as_tuple().digits))
            item = str(item.normalize() if item else Decimal(0))
    elif hasattr(item, 'isoformat'):
        item = item.isoformat()
    return kind, item


class GroupStore:
    """Spill at the memory threshold; never deserialize external pickle data.

    Serialized values are created here from already validated native scalars and
    our own aggregate state, in a fresh private temporary directory per query.
    """
    def __init__(self, checkpoint, memory_groups=10000, max_bytes=256 * 1024 * 1024, directory=None):
        self.checkpoint = checkpoint
        self.memory_groups, self.max_bytes, self.parent = memory_groups, max_bytes, directory
        self.memory, self.db, self.temporary = {}, None, None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        try:
            if self.db is not None:
                self.db.close()
        finally:
            if self.temporary is not None:
                self.temporary.cleanup()

    def identity(self, group):
        return json.dumps([typed_key(value) for value in group], ensure_ascii=False, separators=(',', ':'))

    def sql(self, command, parameters=()):
        try:
            return self.db.execute(command, parameters)
        except sqlite3.OperationalError as error:
            if getattr(error, 'sqlite_errorcode', None) == sqlite3.SQLITE_FULL:
                from .subway_queries import fail
                fail('Aggregate temporary-storage budget exhausted; no partial result returned.', 'SUBWAY_QUERY_LIMIT')
            raise

    def spill(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='subway-query-', dir=self.parent)
        self.db = sqlite3.connect(Path(self.temporary.name) / 'groups.sqlite3')
        self.db.execute('PRAGMA page_size=4096')
        self.db.execute('PRAGMA max_page_count=' + str(max(1, self.max_bytes // 4096)))
        self.db.execute('PRAGMA cache_size=-4096')
        self.db.execute('PRAGMA journal_mode=OFF')
        self.db.execute('PRAGMA synchronous=OFF')
        self.db.execute('PRAGMA temp_store=FILE')
        def compare(a, b):
            a, b = json.loads(a), json.loads(b)
            for value in (a, b):
                if value[0] == 'number':
                    value[1] = Decimal(value[1])
            return (a > b) - (a < b)
        self.db.create_collation('scalar_order', compare)
        self.sql('CREATE TABLE groups (identity TEXT PRIMARY KEY, sequence INTEGER UNIQUE, state BLOB, s0 TEXT COLLATE scalar_order, s1 TEXT COLLATE scalar_order, s2 TEXT COLLATE scalar_order)')
        for sequence, (group, state) in enumerate(self.memory.items()):
            self.checkpoint()
            self.sql('INSERT INTO groups(identity,sequence,state) VALUES (?,?,?)', (self.identity(group), sequence, pickle.dumps(state)))
        self.memory.clear()

    def __len__(self):
        return len(self.memory) if self.db is None else self.sql('SELECT COUNT(*) FROM groups').fetchone()[0]

    def get(self, group):
        if self.db is None:
            return self.memory.get(group)
        row = self.sql('SELECT state FROM groups WHERE identity=?', (self.identity(group),)).fetchone()
        return pickle.loads(row[0]) if row else None

    def put(self, group, state):
        if self.db is None and group not in self.memory and len(self.memory) >= self.memory_groups:
            self.spill()
        if self.db is None:
            self.memory[group] = state
        else:
            self.sql('INSERT INTO groups(identity,sequence,state) VALUES (?,(SELECT COALESCE(MAX(sequence)+1,0) FROM groups),?) ON CONFLICT(identity) DO UPDATE SET state=excluded.state', (self.identity(group), pickle.dumps(state)))

    def page(self, finalize, order, offset, limit, key):
        if self.db is None:
            rows = [finalize(group) for group in self.memory.values()]
            for item in reversed(order):
                rows.sort(key=lambda row: (row[item['column']] is not None, row[item['column']]), reverse=item['direction'] == 'desc')
            return rows[offset:offset + limit]
        for sequence, state in self.sql('SELECT sequence,state FROM groups ORDER BY sequence'):
            self.checkpoint()
            row = finalize(pickle.loads(state))
            sorting = [json.dumps(typed_key(key(row[item['column']]))) for item in order]
            sorting += [json.dumps(('', ''))] * (3 - len(sorting))
            self.sql('UPDATE groups SET state=?,s0=?,s1=?,s2=? WHERE sequence=?', (pickle.dumps(row), *sorting, sequence))
        sorting = ','.join('s' + str(i) + (' DESC' if item['direction'] == 'desc' else ' ASC') for i, item in enumerate(order))
        ordering = (sorting + ',' if sorting else '') + 'sequence ASC'
        # Application-owned column names/directions only; client strings are not SQL.
        self.checkpoint()
        rows = self.sql('SELECT state FROM groups ORDER BY ' + ordering + ' LIMIT ? OFFSET ?', (limit, offset))
        page = [pickle.loads(row[0]) for row in rows]
        self.checkpoint()
        return page


def bounded_page(result, max_bytes=100000):
    """Bound display bytes after complete computation, never source population."""
    from .business_compiler import canonical
    from .subway_queries import fail
    coverage = result['coverage']
    rows = result['rows']
    def apply(count):
        result['rows'] = rows[:count]
        coverage['returned_rows'] = count
        coverage['has_more'] = coverage['offset'] + count < coverage['total_result_rows']
        coverage['next_offset'] = coverage['offset'] + count if coverage['has_more'] else None
        return len(canonical(result).encode()) <= max_bytes
    if apply(len(rows)):
        return result
    coverage['display_limited_by'] = 'response_bytes'
    low, high, fitting = 1, len(rows) - 1, 0
    while low <= high:
        middle = (low + high) // 2
        if apply(middle):
            fitting = middle
            low = middle + 1
        else:
            high = middle - 1
    if not fitting or not apply(fitting):
        fail('A result row and its required metadata exceed the response budget; choose fewer display fields. No partial row returned.', 'SUBWAY_QUERY_LIMIT')
    return result
