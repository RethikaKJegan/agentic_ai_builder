"""Automatic checks on Run. Workflow and exact-action approval remain human."""
from copy import deepcopy
import hashlib,json,re
from .service import ApiFailure
from runtime.service import digest


def child(request,operation,payload,suffix):
    key='run_'+hashlib.sha256((request['idempotency_key']+suffix).encode()).hexdigest()[:48]
    return dict(request_id=request['request_id'],operation=operation,idempotency_key=key,payload=payload)


def checked(service,request,auth):
    ref={k:request['payload'][k] for k in ('workflow_id','workflow_version')}
    with service.store.transaction(write=False) as db:
        document=service.store.get(db,auth['subject']['workspace_id'],ref['workflow_id'],ref['workflow_version'])
    if not document:raise ApiFailure('WORKFLOW_NOT_FOUND','The workflow revision was not found.',404)
    if document['status'] in ('draft','validated'):
        response=service.handle(child(request,'validate_workflow',ref,'_checks'),auth)
        if response['status']>=400:
            error=response['data']['error'];raise ApiFailure(error['error_code'],error['message'],response['status'],field=error.get('field'),details=error.get('details'))
        # API documents may project a separate display title. Execution and
        # retained intent fingerprints must always use the canonical revision.
        with service.store.transaction(write=False) as db:
            document=service.store.get(db,auth['subject']['workspace_id'],ref['workflow_id'],ref['workflow_version'])
        if not document:raise ApiFailure('WORKFLOW_NOT_FOUND','The workflow revision was not found.',404)
        report=document.get('metadata',{}).get('validation_report',{})
        from .readiness import fingerprint as workflow_fingerprint
        if report.get('workflow_fingerprint')!=workflow_fingerprint(document):
            raise ApiFailure('REVISION_CONFLICT','The workflow changed during Run checks. Run the current revision.',409)
    else:
        from .readiness import assess
        with service.store.transaction(write=False) as db:report=assess(service,document,auth,db,semantic=True)
    if not report.get('ready'):
        raise ApiFailure('WORKFLOW_READINESS_FAILED','Run cannot start until these setup issues are resolved.',409,details={'issues':[i for i in report.get('issues',[]) if i['blocking']]})
    return document


def start(service,request,auth):
    service.authorize(auth,'execute_workflow')
    payload=request['payload'];key=request.get('idempotency_key')
    if not isinstance(payload,dict) or not isinstance(payload.get('workflow_id'),str) or type(payload.get('workflow_version')) is not int:
        raise ApiFailure('INVALID_REQUEST','Use an exact saved workflow revision.',400)
    if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',key):raise ApiFailure('INVALID_IDEMPOTENCY_KEY','Use a retry key of 8–128 safe characters.',400)
    if set(payload)-{'workflow_id','workflow_version','inputs'}:raise ApiFailure('INVALID_REQUEST','Unsupported execution input.',400)
    with service.store.transaction(write=False) as db:
        document=service.store.get(db,auth['subject']['workspace_id'],payload.get('workflow_id'),payload.get('workflow_version'))
        if document:
            from runtime.service import RuntimeFailure
            try:service.runtime_runner.runtime.validate_inputs(document,payload.get('inputs',{}))
            except RuntimeFailure as exc:
                if exc.code!='INVALID_INPUT':raise
                inputs=payload.get('inputs',{})
                missing=[f['name'] for f in document['inputs'] if f['required'] and
                    (not isinstance(inputs,dict) or f['name'] not in inputs)]
                message=('Supply required workflow inputs: '+', '.join(missing)+'.') if missing else 'Correct the supplied input names and types to match the workflow fields.'
                raise ApiFailure('INVALID_INPUT',message,400,field='inputs.'+missing[0] if missing else 'inputs') from None
    document=checked(service,request,auth)
    if document['status']=='validated':
        from .review_actions import submit
        ref={k:payload[k] for k in ('workflow_id','workflow_version')}
        submit(service,child(request,'submit_workflow_for_approval',ref,'_review'),auth)
        # Intent authority is stored in the server-only mutation journal, not
        # supplied roles, an approval flag, or client workflow metadata.
        scope=auth['subject'];intent_key='run_wait_'+hashlib.sha256(key.encode()).hexdigest()[:48]
        from .readiness import fingerprint as workflow_fingerprint
        intent=dict(request=deepcopy(request),workflow_id=ref['workflow_id'],workflow_version=ref['workflow_version'],owner=scope['subject_id'],workflow_fingerprint=workflow_fingerprint(document))
        fingerprint=digest(payload)
        with service.store.transaction() as db:
            old=db.execute('SELECT fingerprint FROM mutations WHERE workspace=? AND subject=? AND key=?',(scope['workspace_id'],scope['subject_id'],intent_key)).fetchone()
            if old and old[0]!=fingerprint:raise ApiFailure('IDEMPOTENCY_KEY_REUSED','The Run retry key belongs to different inputs.',409)
            prior=db.execute("SELECT response FROM mutations WHERE workspace=? AND subject=? AND key LIKE 'run_wait_%' AND json_extract(response,'$.workflow_id')=? AND json_extract(response,'$.workflow_version')=? ORDER BY rowid LIMIT 1",(scope['workspace_id'],scope['subject_id'],ref['workflow_id'],ref['workflow_version'])).fetchone()
            if prior:
                previous=json.loads(prior[0])
                if previous.get('workflow_fingerprint')!=intent['workflow_fingerprint'] or digest(previous['request']['payload'])!=fingerprint:
                    raise ApiFailure('RUN_ALREADY_REQUESTED','A Run request for this revision already awaits review. Keep its inputs or create a reviewed revision.',409)
                # All clicks before review share one execution intent, including
                # retries after a very fast run has already finished.
                intent['request']=previous['request']
            db.execute('INSERT INTO mutations VALUES (?,?,?,?,?) ON CONFLICT(workspace,subject,key) DO NOTHING',(scope['workspace_id'],scope['subject_id'],intent_key,fingerprint,json.dumps(intent)))
        raise ApiFailure('WORKFLOW_APPROVAL_REQUIRED','Awaiting approval. An authorized reviewer must approve this workflow before the retained Run request can execute.',409,details={'state':'awaiting_approval',**ref})
    scope=auth['subject'];intent_key='run_wait_'+hashlib.sha256(key.encode()).hexdigest()[:48]
    with service.store.transaction(write=False) as db:
        prior=db.execute('SELECT fingerprint,response FROM mutations WHERE workspace=? AND subject=? AND key=?',(scope['workspace_id'],scope['subject_id'],intent_key)).fetchone()
    if prior:
        if prior[0]!=digest(payload):raise ApiFailure('IDEMPOTENCY_KEY_REUSED','The Run retry key belongs to different inputs.',409)
        intent=json.loads(prior[1])
        from .readiness import fingerprint as workflow_fingerprint
        if intent.get('workflow_fingerprint')!=workflow_fingerprint(document):raise ApiFailure('REVISION_CONFLICT','The reviewed workflow differs from the requested Run. Review and submit a fresh Run request.',409)
        request=intent['request']
    return service.runtime_runner.runtime.create_run(request,auth,expected_digest=digest(document),coalesce=True)


def resume_pending(service,workflow_id,version,approver):
    """Called only AFTER the existing human workflow approval commits."""
    service.authorize(approver,'approve_workflow')
    workspace=approver['subject']['workspace_id'];resolver=getattr(service,'worker_authenticate',None)
    if not resolver:return []
    with service.store.transaction(write=False) as db:
        document=service.store.get(db,workspace,workflow_id,version)
        if not document or document['status'] not in ('approved','published'):return []
        rows=db.execute("SELECT subject,key,response FROM mutations WHERE workspace=? AND key LIKE 'run_wait_%'",(workspace,)).fetchall()
    from .readiness import fingerprint as workflow_fingerprint
    from runtime.service import RuntimeFailure
    results=[]
    for owner,intent_key,raw in rows:
        intent=json.loads(raw)
        if intent.get('run_id'):continue
        if intent.get('workflow_id')!=workflow_id or intent.get('workflow_version')!=version:continue
        if intent.get('workflow_fingerprint')!=workflow_fingerprint(document):continue
        try:
            auth=resolver(workspace,owner)
            if not auth or auth.get('subject')!={'workspace_id':workspace,'subject_id':owner}:continue
            request=intent['request'];service.authorize(auth,'execute_workflow')
            # Runtime keeps the unchanged approved-only revision/Registry boundary.
            run=service.runtime_runner.runtime.create_run(request,auth,expected_digest=digest(document),coalesce=True)
            intent['run_id']=run['run_id']
            with service.store.transaction() as db:
                db.execute('UPDATE mutations SET response=? WHERE workspace=? AND subject=? AND key=?',(json.dumps(intent),workspace,owner,intent_key))
            results.append(run)
        except (ApiFailure,RuntimeFailure):
            # Approval stays committed; a revoked or conflicting execution intent
            # remains blocked and can be retried explicitly through Run.
            continue
    return results
