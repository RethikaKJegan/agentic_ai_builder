"""Operator acceptance in an isolated application copy; company tools are read-only.

Default: preparation without model calls. --live-model explicitly invokes the
configured OpenAI planner/CrewAI with mapped complaint/inspection evidence.
No workers, Google effects, live registry writes or live application writes.
"""
from pathlib import Path
import argparse
import json
import os
import sqlite3
import sys
import tempfile
from urllib.parse import urlparse
from unittest.mock import patch
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def check(database,complaint,live_model=False,include_related_evidence=False):
    if not database.is_file():raise ValueError('The source application database does not exist.')
    check_root=ROOT/'.local/dynamic-investigation-checks';check_root.mkdir(parents=True,exist_ok=True)
    directory=Path(tempfile.mkdtemp(prefix='check-',dir=check_root));os.chmod(directory,0o700)
    destination=directory/'isolated.sqlite3'
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(destination) as target:source.backup(target)
    os.chmod(destination,0o600)
    # The copy must never dispatch pre-existing jobs.
    with sqlite3.connect(destination) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='business_investigation_jobs'").fetchone():db.execute('DELETE FROM business_investigation_jobs')
    from workflow_api.live_providers import environment,create_configured_app,operator_auth,registry_configuration
    env=environment();host=urlparse(env.get('OPENAI_BASE_URL','https://api.openai.com/v1')).hostname
    if host!='api.openai.com':raise ValueError('Review authorization for the configured model endpoint before this acceptance check.')
    env.update(BUILDER_ENVIRONMENT='test',BUILDER_DEV_AUTH='1',BUILDER_PROCESS_ROLE='api',BUILDER_UI_ORIGINS='http://127.0.0.1:3199')
    from workflow_api.business_knowledge_model import canonical
    with patch('workflow_api.live_providers.REGISTRY',directory/'registry.json'):
        app=create_configured_app(env,database=destination)
    service=app.state.workflow_service;auth=operator_auth(registry_configuration(env))
    objective=f'Compare complaint {complaint} with its linked inspection. Prepare a source-backed report identifying agreements, discrepancies and missing inspection evidence. Do not assess warranty or perform operational actions.'
    allowed={'business.read.complaints','business.read.inspection','business.compare','business.report'}
    if include_related_evidence:
        objective=f'Investigate complaint {complaint}. Compare its linked inspection, review replacement evidence distinguishing technical recommendations from commercial authorization, check warranty readiness without inventing policies or eligibility, and prepare a source-backed report with missing evidence. Do not send emails, schedule meetings or modify records.'
        allowed|={'business.read.warranty','business.assess_warranty','business.read.replacement','business.review_replacement'}
    if live_model:
        from fastapi.testclient import TestClient
        client=TestClient(app,base_url='http://127.0.0.1:3199') # No lifespan: workers remain stopped.
        session=client.get('/session');session.raise_for_status()
        client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
        key='pilot_'+uuid4().hex
        response=client.post('/business-ontology/v1/investigations/jobs',json=dict(kind='compose',request_key=key,payload=dict(objective=objective,request_key=key,planning_mode='model',business_request={'inputs':{'identifiers':{'complaint_id':complaint}}},recovery_max_retries=1)))
        response.raise_for_status();job=response.json()['data'];app.state.investigation_jobs.tick()
        job=client.get('/business-ontology/v1/investigations/jobs/'+job['job_id']).json()['data']
        if job['state']!='succeeded':raise ValueError('Planning failed: '+json.dumps(job.get('error')))
        cid=job['composition_id'];doc=service.business_composition.get(auth,cid)
    else:
        doc=service.business_composition.prepare(auth,dict(objective=objective,request_key='pilot_'+uuid4().hex,planning_mode='offline',business_request={'inputs':{'identifiers':{'complaint_id':complaint}}}))
        cid=doc['composition_id']
    if doc['state']!='ready':raise ValueError('Preparation gaps: '+json.dumps(doc['gaps']))
    capabilities={t['capability_id'] for t in doc['tasks']}
    if not capabilities<=allowed or not {'business.read.complaints','business.read.inspection','business.compare'}<=capabilities:raise ValueError('Plan falls outside the bounded comparison check.')
    workflow=service.business_composition.workflow(auth,cid)
    if workflow['execution_policy']['allow_external_writes'] or {t['tool_id'] for t in workflow['tools']}!={'business_retrieve_evidence'}:raise ValueError('Only mapped read-only business tools are permitted.')
    receipt=dict(directory=str(directory),mode='configured_model' if live_model else 'offline_preparation',complaint_id=complaint,composition_id=cid,planning=doc['planning'],capabilities=sorted(capabilities),company_write_tools=0,application_database_isolated=True)
    if live_model:
        def operation(op,payload):
            request=dict(request_id='pilot_'+uuid4().hex,operation=op,idempotency_key='pilot_'+uuid4().hex,payload=payload)
            result=service.handle(request,auth)
            if result['status']>=400:raise ValueError('Lifecycle failed: '+json.dumps(result['data'].get('error')))
            return result['data']
        ref=dict(workflow_id=workflow['workflow_id'],workflow_version=1)
        operation('validate_workflow',ref);operation('approve_workflow',{**ref,'action':'approve'})
        created=operation('execute_workflow',{**ref,'inputs':{}})['run']
        run=service.runtime_runner.advance(created['run_id'],auth)
        snapshot=app.state.composition_presentation.view(auth,cid,run['run_id'])
        (directory/'view.json').write_text(canonical(snapshot));os.chmod(directory/'view.json',0o600)
        receipt.update(run_id=run['run_id'],status=run['status'],usage=snapshot['run']['usage'],completed_tasks=sum(t['state']=='completed' for t in snapshot['tasks']),evidence_tasks=sum(bool(t['result'] and t['result']['records']) for t in snapshot['tasks']),failure=snapshot['run']['error_code'])
    (directory/'receipt.json').write_text(json.dumps(receipt,indent=2));os.chmod(directory/'receipt.json',0o600)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--database',type=Path,required=True);parser.add_argument('--complaint',default='A-2022-12-013');parser.add_argument('--live-model',action='store_true');parser.add_argument('--include-related-evidence',action='store_true');args=parser.parse_args()
    try:
        receipt=check(args.database,args.complaint,args.live_model,args.include_related_evidence);print(json.dumps(receipt,indent=2));sys.exit(0 if receipt.get('status','completed')=='completed' else 1)
    except Exception as exc:
        print(json.dumps(dict(error=getattr(exc,'code','ACCEPTANCE_CHECK_FAILED'),message=str(exc) if isinstance(exc,ValueError) else 'Inspect the isolated check and current provider/source configuration.')));sys.exit(1)
