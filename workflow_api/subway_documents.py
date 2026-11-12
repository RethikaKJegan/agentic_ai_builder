"""Passages from existing owned source text; metadata never proves content."""
from hashlib import sha256
import re
from jsonschema import Draft202012Validator
from .service import ApiFailure

INPUT = dict(type='object', additionalProperties=False, required=['query'], properties=dict(
    query=dict(type='string', minLength=1, maxLength=2000)))
OUTPUT = dict(type='object', additionalProperties=False, required=['scope','ontology_version','records','completeness','limitations'], properties=dict(
    scope=dict(type='object'), ontology_version=dict(type='string'), records=dict(type='array', maxItems=8, items=dict(type='object')),
    completeness=dict(type='string', enum=['complete','incomplete']), limitations=dict(type='array', items=dict(type='string'))))


def definition():
    from .subway_queries import definition as query_definition
    result = query_definition()
    result.update(tool_id='subway_documents', capability='subway.documents', timeout_seconds=30,
        input_schema=INPUT, output_schema=OUTPUT,
        description='Retrieve bounded passages from actual saved Subway ontology source text and owned documents. '
            'Search using the objective or evidence gap. Returns exact offsets, hashes and version. '
            'Code describes implementation, not approved company policy. No external downloads, OCR, '
            'invented attachment bytes, fuzzy entity identity or business-record writes.')
    return result


class SubwayDocuments:
    external_write = False
    timeout = 30

    def __init__(self, queries, auth=None, pin=None):
        self.queries, self.auth, self.pin = queries, auth, pin

    def reservation(self, grant):
        return dict(tool_calls=1, llm_calls=0, tokens=0, estimated_cost_usd=0)

    def bind_context(self, workflow, run, auth, node):
        from .subway_queries import SubwayQueryConnector
        bound = SubwayQueryConnector(self.queries).bind_context(workflow, run, auth, node)
        return SubwayDocuments(self.queries, bound.auth, bound.pin)

    def invoke(self, grant, inputs, effect_id):
        if not self.auth or grant.get('tool_id') != 'subway_documents' or list(Draft202012Validator(INPUT).iter_errors(inputs)):
            raise ApiFailure('SUBWAY_DOCUMENT_DENIED', 'Use an authorized bound document request.', 403)
        self.queries.authorize(self.auth)
        packages = self.queries.app.state.client_packages
        if packages.get(self.auth, self.pin['package_id'], self.pin['revision'])['sha256'] != self.pin['package_sha256']:
            raise ApiFailure('SUBWAY_DOCUMENT_STALE', 'The reviewed document scope changed.', 409)
        from .business_documents import BusinessDocuments
        from .subway_evidence_resolution import load
        scope = (self.auth['subject']['workspace_id'], self.auth['subject']['subject_id'])
        snapshot = self.queries.version
        sources = {s['source_id']:s for s in snapshot['sources']}
        resolved = load(scope, snapshot)
        if resolved:
            sources.update(resolved['sources'])
        with self.queries.store.transaction(write=False) as db:
            for source in BusinessDocuments.rows(db, scope):
                sources[source['source_id']] = source
        terms = set(re.findall(r'[a-z0-9]{3,}', inputs['query'].lower()))
        selected = []
        for sid, source in sources.items():
            text = source.get('text')
            if not isinstance(text,str) or not text or sha256(text.encode()).hexdigest() != source.get('sha256'):
                continue
            score = len(terms & set(re.findall(r'[a-z0-9]{3,}', text.lower())))
            if score:
                selected.append((score, sid, source))
        records = []; remaining = 12000
        for _, sid, source in sorted(selected, key=lambda x:(-x[0],x[1]))[:8]:
            text = source['text']
            positions = [m.start() for term in terms for m in re.finditer(re.escape(term), text.lower())]
            start = max(0, min(positions, default=0)-160)
            excerpt = text[start:start+min(2000,remaining)]
            if not excerpt:
                break
            remaining -= len(excerpt)
            records.append(dict(record_id=sid, source_id=sid, title=source['title'], source_kind=source['kind'],
                source_sha256=source['sha256'], version_id=snapshot['version_id'], text=excerpt,
                location=dict(character_start=start, character_end=start+len(excerpt)),
                excerpt_sha256=sha256(excerpt.encode()).hexdigest(), content_available=True,
                scope=dict(workspace_id=scope[0],owner_id=scope[1]),
                qualification='Actual saved source text. No inferred entity match, approved policy, precedence or causal conclusion.'))
        return dict(scope=dict(workspace_id=scope[0],owner_id=scope[1]), ontology_version=snapshot['version_id'],
            records=records, completeness='complete' if records else 'incomplete',
            limitations=['Bounded passages; unindexed bytes and external attachments are unavailable. '
                'Text alone does not establish complete business records or approved policy.'])
