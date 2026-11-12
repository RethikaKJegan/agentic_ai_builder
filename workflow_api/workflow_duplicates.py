"""Independent draft copies; execution history and automation grants stay with the source."""
from copy import deepcopy
import json
from .business_knowledge_model import canonical, digest
from .google_connections import now
from .investigation_graph import fail
from .workflow_display import display_title


def request_key(auth, body):
    if 'workflow.edit' not in auth.get('permissions', []):
        fail('Workflow edit access is required.', 'INVESTIGATION_DENIED', 403)
    if 'workspace:write' not in auth.get('scopes', []):
        fail('Workspace write access is required.', 'INVESTIGATION_DENIED', 403)
    if not isinstance(body, dict) or set(body) != {'request_key'} or not isinstance(body['request_key'], str) or not 8 <= len(body['request_key']) <= 128:
        fail('Supply a duplicate request key.')
    return 'duplicate_' + digest(body['request_key'])[:32]


def composition_copy(presentation, auth, cid, body):
    composition = presentation.composition
    doc = composition.get(auth, cid)
    key = request_key(auth, body)
    scope = (doc['scope']['workspace'], doc['scope']['owner'])
    wid = 'cw_'+cid.removeprefix('composition_')
    with composition.store.transaction(write=False) as db:
        meta = db.execute('SELECT display_name,deleted_at FROM business_investigation_metadata WHERE workspace=? AND owner=? AND workflow_id=?', (*scope,wid)).fetchone()
        deleted = db.execute('SELECT 1 FROM lifecycle_tombstones WHERE workspace=? AND workflow_id=?', (scope[0],wid)).fetchone()
    if deleted or (meta and meta[1]):fail('Workflow was deleted.', 'WORKFLOW_DELETED', 410)
    source = dict(workflow_id=wid,display_name=meta[0] if meta and meta[0] else display_title(doc))
    fingerprint = digest(['duplicate', cid])
    with composition.store.transaction(write=False) as db:
        old = db.execute('SELECT fingerprint,document FROM business_compositions WHERE workspace=? AND owner=? AND request_key=?', (*scope, key)).fetchone()
    if old:
        if old[0] != fingerprint: fail('Duplicate key was reused.', 'CAPABILITY_CONFLICT', 409)
        saved = json.loads(old[1])
        return dict(workflow_id='cw_'+saved['composition_id'].removeprefix('composition_'), composition_id=saved['composition_id'])
    suffix = digest([scope, key, cid])[:24]
    new_cid = 'composition_' + suffix
    mapping = {cid: new_cid, source['workflow_id']: 'cw_'+suffix}
    for config in doc['configurations']:
        old_id = config['definition']['agent_id']
        mapping[old_id] = 'ca_'+digest([new_cid, old_id])[:24]
    if doc.get('master'):
        mapping[doc['master']['agent_id']] = 'cm_'+suffix
    def remap(value):
        if isinstance(value, dict): return {mapping.get(k, k): remap(v) for k, v in value.items()}
        if isinstance(value, list): return [remap(v) for v in value]
        return mapping.get(value, value) if isinstance(value, str) else value
    copied = remap(deepcopy(doc))
    copied.pop('sha256')
    copied['objective'] = doc['objective']
    copied.pop('lifecycle_context', None)
    copied['created_at'] = now()
    copied['display_name'] = (source['display_name'][:153] + ' (copy)')
    if copied.get('action_plan'):
        plan = copied['action_plan']
        plan['goal'] = doc['action_plan']['goal']
        plan['plan_id'] = 'plan_'+suffix
        plan['revision'] = 1
        plan['schema_version'] = 'orchestration-plan-v1'
        for field in ('previous_revision', 'revision_reason', 'triggering_observations'):
            plan.pop(field, None)
        plan['fingerprint'] = digest({k:v for k,v in plan.items() if k!='fingerprint'})
        from .action_bindings import validate_plan
        validate_plan(plan, copied['contracts'], copied['binding_context'], plan['scope'])
    for config in copied['configurations']:
        composition.register(config['definition'], auth)
    if copied.get('master'): composition.register(copied['master'], auth)
    copied['sha256'] = digest(copied)
    if copied['state'] == 'ready':
        from planner.validation import validate_workflow
        from .action_plans import compile_workflow as actions
        from .business_composition import compile_workflow as tasks
        validate_workflow((actions if copied.get('action_plan') else tasks)(copied))
    with composition.store.transaction() as db:
        db.execute('INSERT INTO business_compositions VALUES (?,?,?,?,?,?) ON CONFLICT(workspace,owner,request_key) DO NOTHING', (*scope,new_cid,key,fingerprint,canonical(copied)))
        saved = db.execute('SELECT fingerprint FROM business_compositions WHERE workspace=? AND owner=? AND request_key=?', (*scope,key)).fetchone()
        if saved[0] != fingerprint:fail('Duplicate key was reused.', 'CAPABILITY_CONFLICT', 409)
    return dict(workflow_id='cw_'+suffix, composition_id=new_cid)


def investigation_copy(service, auth, wid, body):
    auth, scope = service.authorize(auth)
    key = request_key(auth, body)
    plan = service.get_plan(auth, wid)
    fingerprint = digest(['duplicate', wid])
    with service.store.transaction() as db:
        old = db.execute('SELECT fingerprint,document FROM business_investigation_plans WHERE workspace=? AND owner=? AND request_key=?', (*scope,key)).fetchone()
        if old:
            if old[0] != fingerprint: fail('Duplicate key was reused.', 'INVESTIGATION_CONFLICT', 409)
            return dict(workflow_id=json.loads(old[1])['workflow_id'])
        meta = db.execute('SELECT display_name FROM business_investigation_metadata WHERE workspace=? AND owner=? AND workflow_id=?', (*scope,wid)).fetchone()
        copied = deepcopy(plan)
        copied.pop('plan_sha256')
        copied.update(workflow_id='investigation_'+digest([scope,key,wid])[:24], revision=1, created_at=now(), display_name=((meta[0] if meta and meta[0] else display_title(plan))[:153]+' (copy)'))
        copied['plan_sha256'] = digest(copied)
        service.check_plan(auth, copied)
        db.execute('INSERT INTO business_investigation_plans VALUES (?,?,?,?,?,?)', (*scope,copied['workflow_id'],key,fingerprint,canonical(copied)))
    return dict(workflow_id=copied['workflow_id'])
