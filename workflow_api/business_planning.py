"""Read-only, owner-scoped business evidence for workflow proposals.

Retrieval is not a policy approval, join grant or rule interpreter. Provider step
references are validated; provenance is constructed only from saved documents.
"""
from copy import deepcopy
from hashlib import sha256
import json

from .business_compiler import canonical, check_snapshot
from .business_ontology import identity, MODULES
from .business_policies import checked
from .kg_retrieval import terms
from .service import ApiFailure

VERSION = 'simpson-business-planning-v1'
MAX_REFERENCES = 36
MAX_CHARACTERS = 70000
ALIASES = {
    'engines': 'engine product model serial invoice',
    'complaints': 'complaint ticket claim customer service',
    'warranty': 'warranty coverage eligibility eligible exclusion',
    'inspection': 'inspection investigation diagnostic diagnosis',
    'failure': 'failure cause symptom mechanism diagnosis',
    'replacement': 'replacement replace dispatch return logistics',
    'quality': 'quality investigation test examination',
    'capa': 'capa corrective preventive containment',
    'effectivity': 'cutin cut-in engineering change incorporation',
    'monitoring': 'monitoring reliability recurrence exposure rate effectiveness',
    'organization': 'organization oem department account',
    'evidence': 'provenance evidence citation document',
}


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def retrieve(store, auth, objective, version_id=None):
    """No initialization, source DB calls, provider calls or writes."""
    result = dict(retrieval_version=VERSION, state='not_configured', version_id=None,
                  revision=None, definition_sha256=None, references=[], matched_modules=[],
                  truncated=False, limits=dict(max_references=MAX_REFERENCES, max_characters=MAX_CHARACTERS))
    try:
        scope = identity(auth)
    except ApiFailure as exc:
        if exc.status != 403:
            raise
        result['state'] = 'not_authorized'
        return result
    with store.transaction(write=False) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", ('business_ontology_versions',)).fetchone():
            return result
        row = db.execute("SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? ORDER BY CAST(json_extract(document,'$.revision') AS INTEGER) DESC LIMIT 1", scope).fetchone()
        if not row:
            return result
        if version_id:
            row=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?',(*scope,version_id)).fetchone()
            if not row:raise ApiFailure('BUSINESS_VERSION_NOT_FOUND','Pinned ontology not found.',404)
        snapshot = json.loads(row[0])
        policy_rows = db.execute('SELECT v.document FROM business_policy_versions v JOIN business_policy_heads h ON v.workspace=h.workspace AND v.owner=h.owner AND v.policy_key=h.policy_key AND v.revision=h.revision WHERE v.workspace=? AND v.owner=? ORDER BY v.policy_key LIMIT 40', scope).fetchall() if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", ('business_policy_heads',)).fetchone() else []
    if version_id:
        policy_rows=[(json.dumps(p),) for p in snapshot.get('knowledge',{}).get('manifest',{}).get('policy_snapshots',[])]
    result.update(state='no_match', version_id=snapshot['version_id'], revision=snapshot['revision'], definition_sha256=digest(snapshot))
    if not snapshot.get('concepts'):
        result['state'] = 'no_definitions'
        return result
    check_snapshot(snapshot)
    query = terms(objective)
    module_scores = {mid: len(query & terms(ALIASES.get(mid, '') + ' ' + label)) for mid, label, _, _ in MODULES}
    def score(item):
        return 5 * len(query & terms(item['label'] + ' ' + item['id'])) + len(query & terms(item['definition']))
    # Concept labels support organization-specific terms without an alias dictionary.
    for item in snapshot['concepts']:
        module_scores[item['module_id']] += len(query & terms(item['label']))
    matched = [m for m in sorted(module_scores, key=lambda m: (-module_scores[m], m)) if module_scores[m] > 0][:3]
    if not matched:
        return result
    result['matched_modules'] = matched
    sources = {s['source_id']: s for s in snapshot['sources']}
    def cite(item, kind):
        value = {k: deepcopy(v) for k, v in item.items() if k not in ('evidence', 'confidence', 'status', 'executable')}
        value.update(ref=kind + ':' + item['id'], kind=kind)
        value['evidence'] = [dict(source_id=e['source_id'], quote=e['quote'],
                                  source_sha256=sources[e['source_id']]['sha256'],
                                  source_kind=sources[e['source_id']]['kind'],
                                  title=sources[e['source_id']]['title']) for e in item['evidence']]
        return value
    candidates = []
    selected = sorted([c for c in snapshot['concepts'] if c['module_id'] in matched], key=lambda c: (-score(c), c['id']))[:18]
    concept_ids = {c['id'] for c in selected}
    candidates.extend(cite(c, 'concept') for c in selected)
    candidates.extend(cite(r, 'relationship') for r in sorted(snapshot['relationships'], key=lambda r: (-score(r), r['id'])) if r['source'] in concept_ids and r['target'] in concept_ids)
    candidates.extend(cite(r, 'rule') for r in sorted(snapshot['rules'], key=lambda r: (-score(r), r['id'])) if r['module_id'] in matched)
    # Prioritize rules over less relevant concepts/relationships within the bound.
    candidates.sort(key=lambda c: (0 if c['kind'] == 'rule' else 1, -score(c), c['ref']))
    if 'warranty' in matched:
        policies = []
        for raw, in policy_rows:
            p = checked(json.loads(raw))
            source = p['source']
            policies.append(dict(ref='policy:' + p['policy_id'], kind='policy', id=p['policy_id'],
                label=p['title'], definition='Source-cited warranty interpretation; not verified policy.', module_id='warranty',
                policy_key=p['policy_key'], revision=p['revision'], sha256=p['sha256'],
                interpretation_basis=p.get('interpretation_basis', 'policy_statement'),
                implementation_reference=p.get('implementation_reference'),
                clauses=p['clauses'], missing_clauses=p['missing_clauses'],
                evidence=[dict(source_id=source['source_id'], source_sha256=source['sha256'],
                    source_kind=source['kind'], title=source['title'], quote=cell['quote'])
                    for cell in p['clauses'].values() if cell['quote']][:8]))
        candidates = policies + candidates
    for item in candidates:
        if len(result['references']) >= MAX_REFERENCES or len(canonical({**result, 'references': result['references'] + [item]})) > MAX_CHARACTERS:
            result['truncated'] = True
            continue
        result['references'].append(item)
    result['state'] = 'matched' if result['references'] else 'no_match'
    result['retrieval_sha256'] = digest(result)
    return result


def bind(workflow, context):
    """Require real action-step links; discard any provider-authored provenance."""
    metadata = workflow.setdefault('metadata', {})
    metadata.pop('business_ontology', None)
    view = context.get('business_ontology_retrieval') if isinstance(context, dict) else None
    bindings = metadata.pop('business_ontology_step_bindings', [])
    if not isinstance(view, dict):
        return
    trace = deepcopy(view)
    trace['contributions'] = []
    if view['state'] == 'matched':
        refs = {r['ref']: r for r in view['references']}
        nodes = {n['node_id']: n for n in workflow.get('nodes', [])}
        def invalid(reason, index=None):
            from planner.errors import PlannerFailure
            raise PlannerFailure('BUSINESS_ONTOLOGY_BINDING_INVALID',
                'Link proposed action steps to the supplied Business Ontology references.',
                field='metadata.business_ontology_step_bindings', retryable=True,
                details={'binding_issue': reason, 'binding_index': index})
        if not isinstance(bindings, list) or not 1 <= len(bindings) <= 80:
            invalid('Supply a nonempty list of step bindings, at most 80.')
        agents = {a['agent_id']: a for a in workflow.get('agents', [])}
        normalizations = []
        seen = set()
        for index, original in enumerate(bindings):
            if not isinstance(original, dict) or set(original) != {'node_id', 'refs', 'application'}:
                invalid('Each binding needs exactly node_id, refs and application.', index)
            b = deepcopy(original)
            if not isinstance(b['node_id'], str):
                invalid('node_id must be an actual action node identifier.', index)
            # Some proposals use a registered-in-the-proposal agent identity in
            # place of its node. Resolve only a unique actual executable node.
            if b['node_id'] not in nodes and b['node_id'] in agents:
                agent_id = b['node_id']
                targets = [n for n in nodes.values() if n.get('agent_id') == agent_id]
                if len(targets) == 1:
                    b['node_id'] = targets[0]['node_id']
                    normalizations.append(dict(binding_index=index, field='node_id', reason='unique_agent_action_node', supplied=agent_id, resolved=b['node_id']))
            if b['node_id'] not in nodes or nodes[b['node_id']]['kind'] not in ('agent', 'tool', 'condition', 'transform'):
                invalid('node_id must name an existing agent, tool, condition or transform node; not a specialist without its own graph node.', index)
            if not isinstance(b['refs'], list) or not 1 <= len(b['refs']) <= 12 or any(not isinstance(r, str) for r in b['refs']):
                invalid('refs must contain one to twelve exact retrieved ref strings.', index)
            for position, supplied in enumerate(b['refs']):
                if supplied in refs:
                    continue
                matches = [r['ref'] for r in view['references'] if r['id'] == supplied]
                if len(matches) != 1:
                    invalid('A reference is not an exact retrieved ref or unambiguous retrieved definition ID.', index)
                b['refs'][position] = matches[0]
                normalizations.append(dict(binding_index=index, field='refs', reason='unique_saved_definition_id', supplied=supplied, resolved=matches[0]))
            b['refs'] = list(dict.fromkeys(b['refs']))
            if not isinstance(b['application'], str) or not 12 <= len(b['application'].strip()) <= 1000:
                invalid('application must explain the step contribution in 12 to 1000 characters.', index)
            if b['node_id'] in seen:
                existing = next(c for c in trace['contributions'] if c['node_id'] == b['node_id'])
                merged = list(dict.fromkeys([*existing['refs'], *b['refs']]))
                application = existing['application'] + '\n' + b['application'].strip()
                if len(merged) > 12 or len(application) > 1000:
                    invalid('Combine repeated step bindings within twelve references and 1000 explanation characters.', index)
                existing.update(refs=merged, application=application)
                normalizations.append(dict(binding_index=index, field='node_id', reason='merged_same_action_node', supplied=b['node_id'], resolved=b['node_id']))
            else:
                seen.add(b['node_id'])
                trace['contributions'].append(dict(node_id=b['node_id'], node_name=nodes[b['node_id']]['label'],
                    refs=deepcopy(b['refs']), application=b['application'].strip()))
        if normalizations:
            trace['binding_normalizations'] = normalizations
        trace['state'] = 'incorporated'
    trace['trace_sha256'] = digest(trace)
    metadata['business_ontology'] = trace


def record(store, auth, workflow):
    """Keep server-owned generation proof independently of browser draft edits."""
    trace = workflow.get('metadata', {}).get('business_ontology')
    if not trace:
        return
    scope = auth['subject']['workspace_id'], auth['subject']['subject_id']
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS business_planning_provenance (workspace TEXT NOT NULL, owner TEXT NOT NULL, trace_sha256 TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,trace_sha256))')
        db.execute('INSERT INTO business_planning_provenance VALUES (?,?,?,?) ON CONFLICT DO NOTHING', (*scope, trace['trace_sha256'], canonical(trace)))


def verify_saved(db, auth, workflow):
    trace = workflow.get('metadata', {}).get('business_ontology')
    if trace is None:
        return
    if not isinstance(trace, dict) or not isinstance(trace.get('trace_sha256'), str):
        raise ApiFailure('BUSINESS_ONTOLOGY_TRACE_INVALID', 'Use the original server-recorded ontology contribution evidence.', 422)
    exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", ('business_planning_provenance',)).fetchone()
    row = db.execute('SELECT document FROM business_planning_provenance WHERE workspace=? AND owner=? AND trace_sha256=?',
        (auth['subject']['workspace_id'], auth['subject']['subject_id'], trace['trace_sha256'])).fetchone() if exists else None
    if not row or canonical(trace) != canonical(json.loads(row[0])):
        raise ApiFailure('BUSINESS_ONTOLOGY_TRACE_INVALID', 'Ontology contribution evidence does not match this owner’s recorded generation. Regenerate or remove the historical trace.', 422)
