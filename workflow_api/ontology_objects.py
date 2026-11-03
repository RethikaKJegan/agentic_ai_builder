"""Approved-definition projection over existing read-only connector services."""
import json
import re
import threading
import time

from .data_relationships import fingerprint
from .data_write_adapter import pack, public_record, value_for
from .google_connections import GoogleConnections, now
from .service import ApiFailure


def fail(message, code='ONTOLOGY_OBJECT_INVALID', status=422):
    raise ApiFailure(code, message, status)


def safe_field(field):
    name = field['name']
    normalized = re.sub('[^a-z0-9]', '', name.lower())
    return (not any(c in name for c in '.[$\x00') and
            not any(word in normalized for word in ('password', 'passwd', 'secret', 'token', 'credential', 'privatekey', 'apikey', 'authhash', 'salt')) and
            len(set(field['types'])-{'null'}) == 1 and
            next(iter(set(field['types'])-{'null'}), '') in {
                'string', 'text', 'character varying', 'character', 'integer', 'smallint', 'bigint',
                'number', 'numeric', 'decimal', 'Decimal128', 'boolean', 'ObjectId', 'uuid',
                'date', 'datetime', 'timestamp', 'timestamp with time zone', 'timestamp without time zone'})


class OntologyObjects:
    def __init__(self, foundation, reader, resolve=None):
        self.foundation, self.manager = foundation, foundation.manager
        self.reader, self.resolve = reader, resolve
        self.lock, self.active = threading.Lock(), set()

    def authority(self, auth):
        scope = GoogleConnections.identity(auth)
        current = self.resolve(*scope) if self.resolve else auth
        if not current or current.get('subject') != auth['subject']:
            fail('Current object access is unavailable.', 'ONTOLOGY_OBJECT_DENIED', 403)
        GoogleConnections.identity(current)
        if 'workspace:read' not in current.get('scopes', []):
            fail('Source record read scope is required.', 'ONTOLOGY_OBJECT_DENIED', 403)
        return current

    def binding(self, auth, version_id, concept_id):
        auth = self.authority(auth)
        version = self.foundation.version(auth, version_id)
        if version['stale']:
            fail('Source evidence changed. Revalidate the ontology before browsing records.', 'ONTOLOGY_OBJECT_STALE', 409)
        records = {r['id']: r for r in version['records']}
        concept = records.get(concept_id)
        if not concept or concept['kind'] != 'concept':
            fail('Approved concept unavailable.', 'ONTOLOGY_OBJECT_NOT_FOUND', 404)
        with self.manager.store.transaction(write=False) as db:
            current, refs, _ = self.foundation.state(db, GoogleConnections.identity(auth))
            datasets = [refs[r] for r in concept['source_refs'] if r in refs and refs[r]['kind'] == 'dataset']
            if len(datasets) != 1:
                fail('This concept has no single verified source identity. Record browsing is unavailable.', 'ONTOLOGY_OBJECT_UNSUPPORTED', 422)
            source = datasets[0]
            secret, connection = self.manager.owned(db, auth, source['connection_id'])
        self.manager.configured()
        if not secret or connection['connection_status'] != 'connected':
            fail('Source unavailable.', 'ONTOLOGY_OBJECT_NOT_FOUND', 404)
        dataset = source['metadata']
        all_fields = {f['name']: f for f in dataset['fields']}
        if connection['engine'] == 'mongodb':
            keys = ['_id'] if '_id' in all_fields else []
        else:
            keys = next((c['columns'] for c in dataset.get('constraints', []) if c['kind'] == 'primary_key'), [])
        if not keys or not all(name in all_fields and safe_field(all_fields[name]) for name in keys):
            fail('A supported native primary key is required to browse this concept.', 'ONTOLOGY_OBJECT_UNSUPPORTED')
        attributes = [r for r in records.values() if r['kind'] == 'attribute' and r['properties'].get('source') == concept_id]
        selected = set(keys)
        for attribute in attributes:
            for ref in attribute['source_refs']:
                if ref in refs and refs[ref]['kind'] == 'field' and refs[ref]['dataset_id'] == dataset['dataset_id']:
                    field = refs[ref]['metadata']
                    if safe_field(field):
                        selected.add(field['name'])
        if len(selected) > 64:
            fail('This concept exceeds the 64-field projection limit.', 'ONTOLOGY_OBJECT_LIMIT')
        current = {r['id']: r for r in current}
        # A corrected draft cannot continue using its prior published meaning.
        for r in [concept, *attributes]:
            live = current.get(r['id'])
            if not live or live['status'] != 'approved' or live['stale'] or live['revision'] != r['revision']:
                fail('This definition changed. Reload the approved ontology.', 'ONTOLOGY_OBJECT_STALE', 409)
        fields = [all_fields[name] for name in sorted(selected)]
        config = json.loads(self.manager.cipher.decrypt(secret.encode()))
        return dict(version_id=version_id, concept=concept, records=records, current=current, refs=refs,
                    dataset=dataset, fields=fields, keys=keys, config=config, connection=connection,
                    stamp=fingerprint([GoogleConnections.identity(auth), version_id, concept_id, fields, keys,
                                       connection['generation'], connection['metadata_revision'], fingerprint(secret)]))

    def read(self, auth, binding, filters, offset, limit, deadline):
        fields = {f['name']: f for f in binding['fields']}
        if not set(filters) <= set(fields) or any(v is None for v in filters.values()):
            fail('Choose a permitted scalar search field with a non-null value.')
        for name, value in filters.items():
            value_for(fields[name], value)
        self.authority(auth)
        rows = self.reader.objects(binding['config'], binding['dataset'], binding['fields'], binding['keys'], filters, offset, limit, deadline)
        # Reauthorize after I/O; cache and prior permissions are not grants.
        after = self.binding(auth, binding['version_id'], binding['concept']['id'])
        if after['stamp'] != binding['stamp']:
            fail('Source evidence changed during retrieval. Reload and retry.', 'ONTOLOGY_OBJECT_STALE', 409)
        if len(rows) > limit:
            fail('Source exceeded the bounded read limit.', 'ONTOLOGY_OBJECT_LIMIT')
        if any(not set(row) <= set(fields) for row in rows):
            fail('Unexpected source projection.', 'ONTOLOGY_OBJECT_STALE', 409)
        return rows

    def object(self, binding, raw):
        keys = binding['keys']
        if any(raw.get(k) is None for k in keys):
            fail('Source returned a missing native identity.', 'ONTOLOGY_OBJECT_IDENTITY', 409)
        encoded = public_record(pack(raw, binding['config']['engine']))
        # Validate actual source types before exposing a stale/mixed value.
        for field in binding['fields']:
            name = field['name']
            if name in encoded:
                if type(encoded[name]) is float and (set(field['types'])-{'null'}) <= {'number', 'numeric', 'decimal', 'Decimal128'}:
                    continue  # pack already rejects non-finite floating values.
                value_for(field, encoded[name])
        key = {name: encoded[name] for name in keys}
        values = [dict(name=f['name'], field_id=f['field_id'], types=f['types'], value=encoded.get(f['name']),
                       state='not_returned' if f['name'] not in raw else 'not_recorded' if raw[f['name']] is None else 'value') for f in binding['fields']]
        preferred = ('ticketNumber', 'ticketNo', 'complaintNumber', 'name', 'companyName', 'engineSerialNumber', 'engineNo', 'email')
        label = next((str(encoded[n]) for n in preferred if encoded.get(n) is not None), ' · '.join(str(v) for v in key.values()))
        return dict(object_id='obj_'+fingerprint([binding['connection']['connection_id'], binding['dataset']['dataset_id'], key]),
                    concept_id=binding['concept']['id'], label=label, key=key, fields=values)

    def relationships(self, binding):
        concept_id = binding['concept']['id']
        result = []
        for r in binding['records'].values():
            p = r['properties']
            if r['kind'] != 'relationship' or concept_id not in (p.get('source'), p.get('target')):
                continue
            current = binding['current'].get(r['id'])
            candidate = bool(re.search('candidate|possible|may ', r['label']+' '+p.get('predicate', ''), re.I))
            result.append(dict(relationship_id=r['id'], label=r['label'], definition=r['definition'],
                target_concept_id=p['target'] if p['source'] == concept_id else p['source'],
                classification='candidate' if candidate else 'source_reference',
                supported=bool(p.get('field_pairs')) and bool(current) and current['status'] == 'approved' and not current['stale'] and current['revision'] == r['revision']))
        return result

    def response(self, binding, rows, cursor=None, **extra):
        objects = [self.object(binding, row) for row in rows]
        if len({r['object_id'] for r in objects}) != len(objects):
            fail('Source identity is not unique.', 'ONTOLOGY_OBJECT_IDENTITY', 409)
        result = dict(api_version=1, version_id=binding['version_id'], concept_id=binding['concept']['id'],
            concept_label=binding['concept']['label'], connection_id=binding['connection']['connection_id'],
            source_name=binding['connection'].get('name', ''), dataset_id=binding['dataset']['dataset_id'],
            dataset_name=binding['dataset']['name'], metadata_revision=binding['connection']['metadata_revision'],
            retrieved_at=now(), objects=objects, relationships=self.relationships(binding),
            search_fields=[dict(name=f['name'], types=f['types']) for f in binding['fields']], next_cursor=cursor,
            warnings=['Live source reads are not an immutable historical snapshot. Page membership may change between requests.',
                      'Only approved, bound scalar fields are shown; credentials and unsupported fields are excluded.'], **extra)
        if len(json.dumps(result).encode()) > 2_000_000:
            fail('Object result exceeds 2 MB.', 'ONTOLOGY_OBJECT_LIMIT')
        return result

    def run(self, auth, body, expand=False):
        scope = GoogleConnections.identity(self.authority(auth))
        with self.lock:
            if scope in self.active or len(self.active) >= 4:
                fail('An object read is already running. Wait and retry.', 'ONTOLOGY_OBJECT_BUSY', 429)
            self.active.add(scope)
        try:
            return self.expand(auth, body) if expand else self.explore(auth, body)
        finally:
            with self.lock:
                self.active.discard(scope)

    def explore(self, auth, body):
        if not isinstance(body, dict) or set(body)-{'version_id', 'concept_id', 'key', 'filter', 'cursor', 'limit'} or not all(isinstance(body.get(k), str) and 0 < len(body[k]) <= 256 for k in ('version_id', 'concept_id')):
            fail('Choose an approved version and concept.')
        limit = body.get('limit', 25)
        if type(limit) is not int or not 1 <= limit <= 100:
            fail('Choose a page size from 1 to 100.')
        binding = self.binding(auth, body['version_id'], body['concept_id'])
        filters = body.get('filter', {})
        if not isinstance(filters, dict) or len(filters) > 1:
            fail('Search uses one exact scalar field.')
        if 'key' in body:
            if not isinstance(body['key'], dict) or set(body['key']) != set(binding['keys']) or filters or body.get('cursor'):
                fail('Supply the exact native key without search or continuation.')
            filters, limit = body['key'], 1
        offset = 0
        marker = fingerprint([binding['stamp'], filters, limit])
        if body.get('cursor'):
            try:
                value = json.loads(self.manager.cipher.decrypt(body['cursor'].encode(), ttl=600))
                if value['marker'] != marker or type(value['offset']) is not int or not 0 < value['offset'] <= 5000:
                    raise ValueError()
                offset = value['offset']
            except Exception:
                fail('Continuation expired or scope changed. Restart the search.', 'ONTOLOGY_OBJECT_CURSOR', 409)
        page_limit = min(limit, 5000-offset)
        rows = self.read(auth, binding, filters, offset, page_limit+1, time.monotonic()+20)
        if 'key' in body and len(rows) > 1:
            fail('Native key matched multiple records.', 'ONTOLOGY_OBJECT_IDENTITY', 409)
        more = len(rows) > page_limit
        boundary = more and offset+page_limit >= 5000
        cursor = self.manager.cipher.encrypt(json.dumps(dict(marker=marker, offset=offset+page_limit)).encode()).decode() if more and not boundary else None
        result = self.response(binding, rows[:page_limit], cursor, truncated=boundary)
        if boundary:
            result['warnings'].append('Browsing reached the 5,000-record boundary. Narrow the search; no further page is available.')
        return result

    def expand(self, auth, body):
        required = {'version_id', 'concept_id', 'key', 'relationship_id'}
        if not isinstance(body, dict) or set(body) != required or not all(isinstance(body.get(k), str) and 0 < len(body[k]) <= 256 for k in required-{'key'}):
            fail('Choose an object and one connected relationship.')
        binding = self.binding(auth, body['version_id'], body['concept_id'])
        relationships = self.relationships(binding)
        relation = next((r for r in relationships if r['relationship_id'] == body['relationship_id']), None)
        if not relation or not relation['supported']:
            fail('This relationship has no current supported field binding.', 'ONTOLOGY_OBJECT_UNSUPPORTED')
        if not isinstance(body['key'], dict) or set(body['key']) != set(binding['keys']):
            fail('Supply the exact native source key.')
        deadline = time.monotonic()+25
        roots = self.read(auth, binding, body['key'], 0, 2, deadline)
        if len(roots) != 1:
            fail('Source object is missing or ambiguous. Reload records.', 'ONTOLOGY_OBJECT_IDENTITY', 409)
        target = self.binding(auth, body['version_id'], relation['target_concept_id'])
        edge = binding['records'][body['relationship_id']]
        reverse = edge['properties']['target'] == body['concept_id']
        side, other = ('target_field_id', 'source_field_id') if reverse else ('source_field_id', 'target_field_id')
        filters = {}
        for pair in edge['properties']['field_pairs']:
            left, right = binding['refs'].get(pair[side]), target['refs'].get(pair[other])
            if not left or not right or left['dataset_id'] != binding['dataset']['dataset_id'] or right['dataset_id'] != target['dataset']['dataset_id']:
                fail('Relationship field binding is incompatible.', 'ONTOLOGY_OBJECT_UNSUPPORTED')
            a, b = left['metadata'], right['metadata']
            if a['name'] not in {f['name'] for f in binding['fields']} or b['name'] not in {f['name'] for f in target['fields']}:
                fail('Linking fields are not in the permitted projection.', 'ONTOLOGY_OBJECT_UNSUPPORTED')
            if (set(a['types'])-{'null'}) != (set(b['types'])-{'null'}):
                fail('Link types differ. No implicit coercion is permitted.', 'ONTOLOGY_OBJECT_UNSUPPORTED')
            value = public_record(pack({a['name']: roots[0].get(a['name'])}, binding['config']['engine']))[a['name']]
            if value is None:
                return self.response(target, [], classification=relation['classification'], relationship_label=relation['label'], link_state='not_recorded', truncated=False)
            filters[b['name']] = value
        rows = self.read(auth, target, filters, 0, 26, deadline)
        after = self.binding(auth, body['version_id'], body['concept_id'])
        if after['stamp'] != binding['stamp'] or not next((r['supported'] for r in self.relationships(after) if r['relationship_id'] == body['relationship_id']), False):
            fail('Relationship changed during retrieval.', 'ONTOLOGY_OBJECT_STALE', 409)
        result = self.response(target, rows[:25], classification=relation['classification'], relationship_label=relation['label'],
            link_state='candidate' if relation['classification'] == 'candidate' else 'resolved' if rows else 'not_found', truncated=len(rows)>25)
        result['warnings'].append('Matching source references do not prove current ownership or real-world physical identity. Expansion grants no technical join authority.')
        if len(rows)>25:
            result['warnings'].append('More than 25 related records exist. Open this concept and narrow an exact search for further results.')
        return result
