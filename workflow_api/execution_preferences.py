"""Versioned execution preferences in the existing scoped workspace settings store."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

BEHAVIOURS={'formalTone':False,'conciseResponses':False,'clarifyUncertainty':False,'requireSupportingEvidence':False,'preferredLanguage':'Auto','screenAbusiveLanguage':False,'avoidHostileResponses':False,'strictOutputFormat':False}
LANGUAGES=('Auto','English','Hindi','Tamil','Telugu','Spanish','French','German')
PACKS=[
 dict(id='mk_gr_pii',version=1,name='PII protection pack',controls=['email_masking','us_ssn_masking','schema_output_validation'],limitations=['Masks email and US SSN patterns in supported generated output strings. Source quotations, references, identifiers and control/tool arguments are preserved. Other personal information is not detected. This pack does not redact model inputs or rewrite source records or exact approvals.']),
 dict(id='mk_gr_injection',version=1,name='Prompt-injection shield',controls=['instruction_override_screening'],limitations=['Screens known instruction-override patterns at model boundaries. Cannot detect every prompt injection. Direct tools retain their existing schemas, permissions and exact approvals.']),
]
CONTROLS={c for p in PACKS for c in p['controls']}

def key(auth,workflow_id=None,version=None,agent_id=None):
    return 'exec_'+hashlib.sha256(json.dumps([None if workflow_id else auth['subject']['subject_id'],workflow_id,version,agent_id]).encode()).hexdigest()[:48]

def authorize(auth,write=False):
    from .service import ApiFailure
    if auth.get('decision')!='allow' or ('workflow.edit' if write else 'workflow.view') not in auth.get('permissions',[]) or (write and 'workspace:write' not in auth.get('scopes',[])):
        raise ApiFailure('OPERATION_NOT_AUTHORIZED','Authorized workspace access is required.',403)

def load(db,auth,workflow_id=None,version=None,agent_id=None):
    row=db.execute('SELECT value FROM workspace_settings WHERE workspace=? AND key=?',(auth['subject']['workspace_id'],key(auth,workflow_id,version,agent_id))).fetchone()
    value=json.loads(row[0]) if row else dict(version=1,revision=0,behaviours={},packs=[],display=dict(timezone='UTC',date_format='locale'),updated_at=None)
    value['behaviours']={**deepcopy(BEHAVIOURS),**value['behaviours']}
    return value

def target(store,db,auth,workflow_id,version,agent_id,write=False):
    from .service import ApiFailure
    if workflow_id and (not isinstance(workflow_id,str) or type(version)is not int or version<1):raise ApiFailure('SETTING_INVALID','Select an exact workflow revision.',400)
    if agent_id is not None and not isinstance(agent_id,str):raise ApiFailure('SETTING_INVALID','Use a registered agent identifier.',400)
    if not workflow_id:
        if agent_id or version:raise ApiFailure('SETTING_INVALID','Select a saved workflow revision before selecting an agent.',400)
        return
    workflow=store.get(db,auth['subject']['workspace_id'],workflow_id,version)
    if workflow is None:raise ApiFailure('WORKFLOW_NOT_FOUND','Workflow revision is unavailable in this workspace.',404)
    if write and workflow['status']!='draft':raise ApiFailure('REVISION_IMMUTABLE','Apply protections to an editable draft, then validate and approve it.',409)
    if agent_id and agent_id not in {a['agent_id'] for a in workflow['agents']}:raise ApiFailure('AGENT_NOT_FOUND','Agent is unavailable in this workflow.',404)

def read(store,auth,workflow_id=None,version=None,agent_id=None):
    from .service import ApiFailure
    authorize(auth)
    with store.transaction(write=False) as db:
        if workflow_id and version is None:
            workflow=store.get(db,auth['subject']['workspace_id'],workflow_id)
            if not workflow:raise ApiFailure('WORKFLOW_NOT_FOUND','Workflow is unavailable in this workspace.',404)
            version=workflow['version']
        target(store,db,auth,workflow_id,version,agent_id)
        return dict(settings=load(db,auth,workflow_id,version,agent_id),packs=deepcopy(PACKS),coverage=dict(model_inputs=False,model_input_screening=True,model_outputs=True,delegated_model_tasks=True,direct_tool_payload_redaction=False,planning_input_screening=True),scope=dict(workspace_id=auth['subject']['workspace_id'],subject_id=auth['subject']['subject_id'],workflow_id=workflow_id,workflow_version=version,agent_id=agent_id))

def save(store,auth,body):
    from .service import ApiFailure
    from registry.safety import reject_secrets
    authorize(auth,True);reject_secrets(body)
    if not isinstance(body,dict) or set(body)-{'workflow_id','workflow_version','agent_id','expected_revision','behaviours','packs','display','current_revision'}:
        raise ApiFailure('SETTING_INVALID','Use supported execution preference fields.',400)
    wid,version,aid=body.get('workflow_id'),body.get('workflow_version'),body.get('agent_id')
    if wid and (not isinstance(wid,str) or type(version)is not int or version<1):raise ApiFailure('SETTING_INVALID','Select an exact saved workflow version.',400)
    with store.transaction() as db:
        target(store,db,auth,wid,version,aid,True)
        if 'current_revision' in body:
            if body['current_revision'] is not True or not wid:raise ApiFailure('SETTING_INVALID','Use an authorized current workflow.',400)
            head=store.get(db,auth['subject']['workspace_id'],wid)
            if not head or head['version']!=version:raise ApiFailure('REVISION_CONFLICT','The workflow changed. Select it again to load its current editable revision.',409)
        if wid:
            exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_runs'").fetchone()
            if exists and db.execute("SELECT 1 FROM runtime_runs WHERE workspace=? AND workflow_id=? AND version=? LIMIT 1",(auth['subject']['workspace_id'],wid,version)).fetchone():
                raise ApiFailure('REVISION_IMMUTABLE','Create an editable revision; a workflow with execution history cannot be changed.',409)
        current=load(db,auth,wid,version,aid)
        if type(body.get('expected_revision'))is not int or body.get('expected_revision')!=current['revision']:raise ApiFailure('SETTING_CONFLICT','Preferences changed. Reload before saving.',409)
        if 'behaviours' in body:
            values=body['behaviours']
            if not isinstance(values,dict) or set(values)-set(BEHAVIOURS) or any((v not in LANGUAGES if k=='preferredLanguage' else type(v)is not bool) for k,v in values.items()):raise ApiFailure('SETTING_INVALID','Use supported behavior switches and a supported language.',400)
            current['behaviours'].update(values)
            current.setdefault('behaviour_overrides',{}).update(values)
        if 'packs' in body:
            if not wid:raise ApiFailure('SETTING_INVALID','Guardrail packs require an exact workflow/agent scope.',400)
            if not isinstance(body['packs'],list) or len(body['packs'])>len(PACKS):raise ApiFailure('SETTING_INVALID','Use a bounded guardrail selection.',400)
            selected=[];seen=set()
            for selection in body['packs']:
                if not isinstance(selection,dict) or set(selection)!={'id','version','controls'}:raise ApiFailure('SETTING_INVALID','Select an explicit supported pack subset and version.',400)
                pack=next((p for p in PACKS if p['id']==selection['id'] and p['version']==selection['version']),None)
                controls=selection['controls']
                if not pack or pack['id'] in seen or not isinstance(controls,list) or not controls or any(not isinstance(c,str) for c in controls) or not set(controls)<=set(pack['controls']):raise ApiFailure('GUARDRAIL_UNAVAILABLE','Unsupported or duplicate protections cannot be activated.',422)
                seen.add(pack['id']);selected.append(dict(id=pack['id'],version=pack['version'],controls=sorted(set(controls)),effective_controls=sorted(set(controls)),status='Applied',limitations=pack['limitations']))
            current['packs']=selected
        if 'display' in body:
            display=body['display']
            if not isinstance(display,dict) or set(display)-{'timezone','date_format'}:raise ApiFailure('SETTING_INVALID','Use supported display preferences.',400)
            if 'timezone' in display:
                try:ZoneInfo(display['timezone'])
                except (ZoneInfoNotFoundError,ValueError,TypeError):raise ApiFailure('SETTING_INVALID','Use a valid IANA display timezone.',400) from None
            if display.get('date_format','locale') not in {'locale','iso','day-first','month-first'}:raise ApiFailure('SETTING_INVALID','Use a supported date format.',400)
            current['display'].update(display)
        if wid:store_event=dict(workflow_id=wid,workflow_version=version,agent_id=aid,packs=[dict(id=p['id'],version=p['version'],controls=p['controls']) for p in current['packs']])
        else:store_event=dict(workflow_id=None,behaviour_keys=sorted(body.get('behaviours',{})))
        # Append to the existing scoped immutable mutation journal.
        from uuid import uuid4
        record=dict(event_type='execution.preferences_updated',actor=auth['subject']['subject_id'],at=datetime.now(timezone.utc).isoformat(),**store_event)
        db.execute('INSERT INTO mutations VALUES (?,?,?,?,?)',(auth['subject']['workspace_id'],auth['subject']['subject_id'],'preferences_audit_'+uuid4().hex,hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest(),json.dumps(record)))
        current.update(revision=current['revision']+1,updated_at=datetime.now(timezone.utc).isoformat(),reviewed_by=auth['subject']['subject_id'])
        db.execute('INSERT INTO workspace_settings VALUES(?,?,?,?) ON CONFLICT(workspace,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',
            (auth['subject']['workspace_id'],key(auth,wid,version,aid),json.dumps(current),current['updated_at']))
    return read(store,auth,wid,version,aid)

def snapshot(db,auth,workflow):
    base=load(db,auth);specific=load(db,auth,workflow['workflow_id'],workflow['version'])
    if specific['revision']:
        effective=deepcopy(specific)
        effective['behaviours']={**base['behaviours'],**specific.get('behaviour_overrides',{})}
        base=effective
    agents={}
    for agent in workflow['agents']:
        item=load(db,auth,workflow['workflow_id'],workflow['version'],agent['agent_id'])
        if item['revision']:
            item['behaviours']={**base['behaviours'],**item.get('behaviour_overrides',{})}
            # Agent-specific selections add protection; they cannot remove a workflow pack.
            merged={p['id']:deepcopy(p) for p in base['packs']}
            for pack in item['packs']:
                if pack['id'] in merged:
                    prior=merged[pack['id']]
                    pack=deepcopy(pack)
                    pack['controls']=sorted(set(prior['controls'])|set(pack['controls']))
                    pack['effective_controls']=sorted(set(prior['effective_controls'])|set(pack['effective_controls']))
                merged[pack['id']]=pack
            item['packs']=list(merged.values())
        agents[agent['agent_id']]=item if item['revision'] else base
    value=dict(version=1,scope=deepcopy(auth['subject']),workflow_id=workflow['workflow_id'],workflow_version=workflow['version'],agents=agents)
    value['sha256']=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    return value
