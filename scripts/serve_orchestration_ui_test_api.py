"""Loopback-only Phase 4 acceptance server: real backend, controlled transports, temporary stores.

No production launch path imports this module. Scenario controls exist only on this server.
"""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"tests"))

if __name__=='__main__':
    os.environ.update(CREWAI_TESTING='true',CREWAI_TRACING_ENABLED='false',CREWAI_DISABLE_TELEMETRY='true')
    import crewai
    import pytest
    import uvicorn
    from tests.test_business_ontology import foundation
    from tests.test_business_generation import generation
    from tests.test_business_reference import reference
    from tests.test_business_knowledge import knowledge
    from tests.test_business_retrieval import retrieval
    from tests.test_business_investigations import investigation
    from tests.test_business_composition import composition
    from tests.test_connected_action_plans import connected,proposal,action,bind,stored
    from tests.test_google_connections import setup as google_setup
    from tests.test_durable_automation import automation,reply,drain,trace
    from tests.test_adaptive_orchestration import Evaluator,decision
    from tests.test_business_cases import process,stage
    from workflow_api.automation import DurableAutomation
    from workflow_api.scheduler import TriggerScheduler
    from workflow_api.business_preparation import BusinessEvidenceConnector
    with TemporaryDirectory(prefix='orchestration-ui-') as directory,pytest.MonkeyPatch.context() as monkeypatch:
        tmp=Path(directory);os.environ['BUILDER_DATABASE_URL']=str(tmp/'unused-default.sqlite')
        from workflow_api.main import create_app
        base=composition.__wrapped__(investigation.__wrapped__(retrieval.__wrapped__(knowledge.__wrapped__(reference.__wrapped__(generation.__wrapped__(foundation.__wrapped__(tmp)),monkeypatch)),tmp)))
        f=automation.__wrapped__(connected.__wrapped__(base,tmp),google_setup.__wrapped__(tmp))
        preparation=f.general.business_preparation;google=f.general.google_tools
        f.registry._policy.workspace_id='local-workspace'
        app=create_app(service=f.general,dev_auth=True,roles=['admin','approver'],runtime_enabled=True,start_workers=False,planning_worker_enabled=False,environment_name='test',ui_origins='http://127.0.0.1:3247',google_oauth_config={**google.manager.env,'BUILDER_DATA_SOURCE_KEY_FILE':str(tmp/'key')})
        f.x.a['permissions']=sorted(set(f.x.a['permissions'])|{'workflow.validate','workflow.publish'})
        app.state.workflow_auth.clear();app.state.workflow_auth.update(deepcopy(f.x.a));f.registry._policy.workspace_id='one'
        f.general.business_preparation=preparation;app.state.business_composition.preparation=preparation
        app.state.business_composition.connectors=f.connectors;f.c=app.state.business_composition
        f.general.google_tools=google;f.general.bind_google_connector=google.bind
        f.connectors['business_retrieve_evidence']=BusinessEvidenceConnector(preparation)
        f.general.runtime_runner.connectors=f.connectors
        f.cases=app.state.business_cases;f.cases.clock=lambda:f.now
        f.auto=app.state.automation;f.auto.clock=lambda:f.now
        f.general.worker_authenticate=lambda w,o:deepcopy(f.x.a) if (w,o)==('one','alice') else None
        scenario={'kind':'reply','asked':False,'revised':False}
        evaluator=Evaluator()
        def plan_actions(goal,ctx):
            p=proposal(f.prepared)
            if scenario['kind']=='reply':
                p['actions'] += [action('reply_read','tool.extension_mail_thread',[bind('receipt','thread_id',action='send',path=['thread_id'])],['send']),action('reply_analysis','content.prepare',[bind('output','data',action='reply_read')],['reply_read'],['reply_read'])]
                p['completion_criteria']=['reply_analysis']
            return p
        evaluator.plan_actions=plan_actions
        def assess(ctx):
            if scenario['kind']=='reply' and 'send' in ctx['completed_actions'] and not scenario['asked']:
                scenario['asked']=True
                return decision(ctx,'wait_for_event',['reply_read'],event={'event_type':'mail.reply','expected_source':'gmail','schema':{'type':'object','required':['finding'],'additionalProperties':False,'properties':{'finding':{'type':'string'}}},'deadline_seconds':86400})
            if scenario['kind']=='gather' and 'read' in ctx['completed_actions'] and not scenario['revised']:
                scenario['revised']=True
                p=dict(actions=deepcopy(ctx['plan']['actions']),completion_criteria=ctx['plan']['completion_criteria'],missing_inputs=[])
                p['actions'].insert(1,action('more_evidence','business.read.inspection',[bind('context','preparation_id','preparation_id'),bind('literal','task','inspection_task')],['read']))
                p['actions'][2]['depends_on'].append('more_evidence')
                return decision(ctx,'gather_context',['read'],p)
        evaluator.custom=assess;f.general.planner.provider=evaluator
        definition=process(stage(required_inputs={},required_capabilities=['business.read.complaints','content.prepare','tool.extension_sheets_create_report','tool.extension_mail_send'],allowed_tools=list(f.connectors),side_effect_classification='write',output_schema={'type':'object'},output_bindings={},timeout_policy={'seconds':600,'action':'block'}))
        definition['description']='Controlled browser acceptance process, not installed company policy.'
        f.cases.publish(f.x.a,definition)
        @app.post('/__test/scenario/{kind}')
        def configure(kind:str):
            assert kind in ('reply','missing','gather','daily')
            scenario.update(kind=kind,asked=False,revised=False)
            c=f.cases.create(f.x.a,dict(request_key='ui_case_'+uuid4().hex,process_definition_id=definition['process_definition_id'],process_definition_version=1,original_user_goal=f.request['objective'],google_connection_id=f.connection,business_request={'inputs':{'identifiers':{'complaint_id':'C123'}}}))
            c=f.cases.command(f.x.a,c['case_id'],'prepare',dict(request_key='ui_prepare_'+uuid4().hex,expected_revision=c['revision']))
            return dict(case_id=c['case_id'],connection_id=f.connection,values=f.request['user_values'])
        @app.post('/__test/reply')
        def deliver():
            sub=next(r for r in f.auto.listing(f.x.a,'subscription')['items'] if r['state']=='active')
            f.now+=3*86400;f.messages=[reply(f,sub)]
            f.auto=DurableAutomation(f.general,clock=lambda:f.now)
            f.auto.tick(f.general.worker_authenticate);drain(f)
            return {'sent':len(f.http.sent),'sheets':f.http.write_count}
        @app.post('/__test/occurrence')
        def occurrence():
            s=next(r for r in f.auto.listing(f.x.a,'schedule')['items'] if r['state']=='active')
            f.x.reader.rows['tickets'][0]['complaintRecord']['natureOfCustomerComplaint']='Current source '+str(f.now)
            f.now=s['due'];f.auto.tick(f.general.worker_authenticate);drain(f)
            return {'occurrences':f.auto.listing(f.x.a,'occurrence')['items']}
        @app.post('/__test/tick')
        def tick():
            TriggerScheduler(f.general,f.general.worker_authenticate).tick()
            # Standalone action runs use the existing runner, as the real runtime worker would.
            with f.general.store.transaction(write=False) as db:ids=[json.loads(row[0])['run_id'] for row in db.execute('SELECT document FROM runtime_runs').fetchall()]
            for rid in ids:
                r=stored(f,rid)
                if not r.get('adaptive_control') and r['status'] in ('queued','running'):f.runner.advance(rid,f.x.a)
            return {'sent':len(f.http.sent),'sheets':f.http.write_count}
        @app.post('/__test/revoke-account')
        def revoke_account():
            f.manager.disconnect(f.x.a,f.connection)
            return {'revoked':True}
        @app.post('/__test/uncertain')
        def uncertain():
            original=f.http.request
            def ambiguous(method,url,headers,body=None,timeout=30):
                if url.endswith('/messages/send'):
                    original(method,url,headers,body,timeout)
                    raise TimeoutError('Controlled ambiguous transport; no live provider.')
                return original(method,url,headers,body,timeout)
            f.http.request=ambiguous
            return {'configured':True}
        @app.post('/__test/restart-worker')
        def restart_worker():
            from runtime import RuntimeService
            from runtime.graph import GraphRunner
            f.runtime=RuntimeService(f.general);f.runtime.clock=lambda:f.now
            f.runner=GraphRunner(f.runtime,agents=f.runner.agents,connectors=f.connectors)
            f.general.runtime_runner=f.runner
            f.auto=DurableAutomation(f.general,clock=lambda:f.now)
            return {'restarted':True,'sent':len(f.http.sent),'sheets':f.http.write_count}
        @app.post('/__test/state')
        @app.get('/__test/state')
        def state():
            return {'sent':len(f.http.sent),'sheets':f.http.write_count,'connection_id':f.connection}
        uvicorn.run(app,host='127.0.0.1',port=8028,log_level='warning')
