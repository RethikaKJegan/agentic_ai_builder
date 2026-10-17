"""Explicit approval submission; canonical v1 workflow states remain unchanged."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json,re


def submit(service,request,auth):
    from .service import ApiFailure
    from registry.safety import reject_secrets
    service.authorize(auth,'validate_workflow')
    reject_secrets(request)
    payload=request.get('payload',{});key=request.get('idempotency_key');reference=request.get('request_id')
    if (request.get('operation')!='submit_workflow_for_approval' or not isinstance(payload,dict) or
            set(payload)!={'workflow_id','workflow_version'} or not isinstance(payload['workflow_id'],str) or
            type(payload['workflow_version']) is not int or not isinstance(key,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{8,128}',key) or
            not isinstance(reference,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}',reference)):
        raise ApiFailure('INVALID_REQUEST','Use an exact workflow revision and a safe retry key.',400)
    workspace,subject=auth['subject']['workspace_id'],auth['subject']['subject_id']
    fingerprint=hashlib.sha256(json.dumps({'operation':request['operation'],'payload':payload},sort_keys=True).encode()).hexdigest()
    with service.store.transaction() as db:
        old=db.execute('SELECT fingerprint,response FROM mutations WHERE workspace=? AND subject=? AND key=?',(workspace,subject,key)).fetchone()
        if old:
            if old[0]!=fingerprint:raise ApiFailure('IDEMPOTENCY_KEY_REUSED','This retry key belongs to another action.',409)
            return json.loads(old[1])
        workflow=service.store.get(db,workspace,payload['workflow_id'])
        if not workflow or workflow['version']!=payload['workflow_version']:raise ApiFailure('REVISION_CONFLICT','Reload the current revision before submitting.',409)
        if workflow['status']!='validated':raise ApiFailure('INVALID_TRANSITION','Validate this revision before submitting for approval.',409)
        review=service.registry_adapter.review(workflow,auth)
        if not review['ready']:raise ApiFailure('ASSIGNMENT_REVALIDATION_FAILED','Resolve Registry review blockers before submitting.',403)
        workflow=deepcopy(workflow)
        workflow['metadata']['approval_submission']={'workflow_version':workflow['version'],'submitted_by':subject,
            'submitted_at':datetime.fromtimestamp(service.lifecycle.clock(),timezone.utc).isoformat()}
        service.store.put(db,workspace,workflow)
        result=service.envelope(reference,200,service.document_data(workflow,auth))
        db.execute('INSERT INTO mutations VALUES (?,?,?,?,?)',(workspace,subject,key,fingerprint,json.dumps(result)))
        return result
