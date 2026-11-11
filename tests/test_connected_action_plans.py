"""Connected-plan acceptance through actual Registry, CrewAI, graph and Google adapters."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from tests.test_business_composition import (composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,approve,install_external)
from workflow_api.action_plans import CONTENT_OUTPUT
from workflow_api.action_bindings import validate_plan
from workflow_api.business_composition import BusinessComposition,verify_composition
from workflow_api.business_cases import BusinessCases
from runtime import RuntimeService
from runtime.graph import GraphRunner
from runtime.service import RuntimeFailure
from runtime.crew import CrewExecutor
from runtime.model import BoundedLLM
from connector_extension.catalog import CATALOG
from connector_extension.mail import MailConnector
from connector_extension.calendar import CalendarConnector
from connector_extension.google import GoogleAPI
from connector_extension.common import EffectJournal,ArtifactStore
from connector_extension.sheet_creation import SheetResourceStore
from connector_extension.sheet_report import ReportSheetsSetup
from tests.test_inventory_report_runtime import GoogleProvider


def bind(kind,target,key=None,action=None,path=()):
    return dict(kind=kind,target=target.split('.'),path=list(path),**({'key':key} if key is not None else {'action_id':action}))


def action(aid,cid,bindings,deps=(),refs=(),optional=False,when=None):
    model=cid=='content.prepare'
    write=cid.startswith('tool.') and any(x in cid for x in ('send','create','draft','reply','update','cancel'))
    return dict(action_id=aid,capability_id=cid,depends_on=list(deps),bindings=bindings,instructions='Prepare source-backed findings or content.',
        evidence_references=list(refs),required_approvals=['exact_payload'] if write else [],budget=dict(max_llm_calls=1 if model else 0,max_tool_calls=0 if model else 1,max_retries=0,timeout_seconds=60),optional=optional,when=when)


def proposal(preflight):
    read=action('read','business.read.complaints',[bind('context','preparation_id','preparation_id'),bind('literal','task','task')])
    analysis=action('analysis','content.prepare',[bind('output','data',action='read')],['read'],['read'])
    sheet=action('sheet','tool.extension_sheets_create_report',[bind('literal','project_id','project'),bind('literal','creation_key','creation'),bind('literal','title','title'),bind('generated','tabs',action='analysis',path=['tabs'])],['analysis'])
    email=action('email','content.prepare',[bind('generated','data',action='analysis'),bind('receipt','artifact_url',action='sheet',path=['spreadsheet_url'])],['analysis','sheet'],['analysis','sheet'])
    send=action('send','tool.extension_mail_send',[bind('literal','to','recipient'),bind('generated','subject',action='email',path=['subject']),bind('generated','body',action='email',path=['body'])],['email'])
    return dict(actions=[read,analysis,sheet,email,send],completion_criteria=['send'],missing_inputs=[])


@pytest.fixture
def connected(composition,tmp_path):
    f=composition
    for name in ('effects','sheets','artifacts'):(tmp_path/name).mkdir()
    f.http=GoogleProvider();api=GoogleAPI(lambda *_:'controlled',f.http);journal=EffectJournal(tmp_path/'effects')
    for tid in ['extension_sheets_create_report','extension_mail_send','extension_calendar_create']:
        tool,_=install_external(f,tid)
        policy=deepcopy(f.registry._policy);policy.version+=1;scope=set(tool['permission_scopes'])|set(tool['authentication']['scopes'])
        policy.credential_references['cred_extension_'+tool['provider_id']]=dict(provider_id=tool['provider_id'],scopes=list(scope))
        assert f.registry.update_policy(policy,f.x.a)['status']==200
        assert f.registry.register_tool(tool,f.x.a,'cred_extension_'+tool['provider_id'])['status']==200
    f.connectors['extension_sheets_create_report']=ReportSheetsSetup(CATALOG['extension_sheets_create_report'],api,journal,SheetResourceStore(tmp_path/'sheets'))
    f.connectors['extension_mail_send']=MailConnector(CATALOG['extension_mail_send'],api,journal,ArtifactStore(tmp_path/'artifacts'),'owner@example.com',['engineer@example.com'])
    f.connectors['extension_calendar_create']=CalendarConnector(CATALOG['extension_calendar_create'],api,journal,['primary'])
    f.adapter.auto_resolve_planner=True
    f.prepared=f.general.business_preparation.prepare(f.x.a,dict(objective='Compare complaint C123 with its linked inspection.'))
    f.request=dict(objective='Investigate complaint C123, create a Google Sheet of findings and email the assigned engineer with its link.',request_key='connected_plan_001',preparation_id=f.prepared['preflight_id'],client_id='simpson',
        user_values=dict(task='complaints',project='complaint_report',creation='findings_v1',title='Complaint findings',recipient='engineer@example.com'),action_plan=proposal(f.prepared))
    f.calls=[]
    def factory(definition):
        def provider(messages,cap,timeout):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip();inputs,_=json.JSONDecoder().raw_decode(raw)
            f.calls.append(deepcopy(inputs));output=dict(source_references=inputs['source_references'],assumptions=[])
            if 'artifact_url' in inputs:output.update(subject='Complaint findings',body='Please review '+inputs['artifact_url'])
            else:output.update(title='Complaint findings',summary='Reported cooling water leak; diagnosis remains unverified.',findings=['Cooling water leak'],tabs=[dict(title='Findings',headers=['Finding','Provenance'],rows=[['Cooling water leak','Source-reported complaint']])])
            return json.dumps(output),1,10
        return BoundedLLM(definition,provider,lambda messages:100,0,0)
    f.runtime=RuntimeService(f.general);f.runner=GraphRunner(f.runtime,agents=CrewExecutor(f.adapter,factory),connectors=f.connectors);f.general.runtime_runner=f.runner
    return f


def compile_run(f,request=None):
    doc=f.c.prepare_actions(f.x.a,request or f.request);w=f.c.workflow(f.x.a,doc['composition_id'])
    review=f.adapter.approve_pending(w,f.x.a);assert review['ready'],json.dumps(review,indent=2)
    w=approve(f,w)
    created=f.runtime.create_run(dict(request_id='action_run',operation='execute_workflow',idempotency_key='action_run_'+doc['composition_id'],payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.x.a)
    return doc,w,created['run_id']


def advance(f,rid):return f.runner.advance(rid,f.x.a)


def decide(f,w,run):
    return f.runner.decide(dict(request_id='approve_action',operation='decide_approval',idempotency_key='decision_'+run['approvals'][-1]['approval_id'],payload=dict(approval_id=run['approvals'][-1]['approval_id'],workflow_id=w['workflow_id'],workflow_version=1,decision='approved')),f.x.a)


def stored(f,rid):
    with f.general.store.transaction(write=False) as db:return deepcopy(f.runtime.load(db,rid,f.x.a))


def complete(f,w,rid):
    for _ in range(10):
        run=advance(f,rid)
        if run['status']!='paused_for_approval':return run
        decide(f,w,run)
    raise AssertionError('Unexpected approval loop')


def test_prompt_to_actual_crewai_sheet_verified_url_email_and_restart(connected,tmp_path):
    f=connected;contexts=[]
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda goal,ctx:(contexts.append(deepcopy(ctx)) or proposal(f.prepared)))
    request=deepcopy(f.request);request.pop('action_plan')
    doc,w,rid=compile_run(f,request)
    assert contexts[0]['capabilities']['tool.extension_mail_send']['supported_operation']=='mail.send'
    first=advance(f,rid);assert first['status']=='paused_for_approval',stored(f,rid)
    assert not f.http.sent and f.http.write_count==0
    decide(f,w,first);second=advance(f,rid);assert second['status']=='paused_for_approval',stored(f,rid)
    assert f.http.write_count==1 and not f.http.sent
    before=stored(f,rid);sheet=before['action_instances']['sheet']['output']
    assert sheet['spreadsheet_url'] in before['action_instances']['email']['output']['body']
    # Reconstruct composition/runtime/runner; persist output bindings, approvals and receipts across restart.
    f.c=BusinessComposition(f.general,f.general.business_preparation,f.connectors,model_id='offline-test-model');f.general.business_composition=f.c
    f.runtime=RuntimeService(f.general);f.runner=GraphRunner(f.runtime,agents=f.runner.agents,connectors=f.connectors);f.general.runtime_runner=f.runner
    decide(f,w,second);result=advance(f,rid)
    assert result['status']=='completed',stored(f,rid)
    final=stored(f,rid);assert len(f.http.sent)==1 and f.http.write_count==1
    assert sheet['spreadsheet_url'] in f.http.sent[0].get_body(preferencelist=('plain',)).get_content()
    assert final['action_instances']['email']['provenance_type']=='INFERRED'
    assert final['action_instances']['send']['verified_receipt'] and final['action_instances']['send']['approval_references']
    assert advance(f,rid)['status']=='completed' and len(f.http.sent)==1
    assert f.c.prepare_actions(f.x.a,request)['composition_id']==doc['composition_id']
    trace=dict(plan=doc['action_plan'],run=final,events=f.runtime.events(rid,f.x.a)['items'],qualification='Actual CrewAI/Registry/Google adapters; controlled model and HTTP transports; no live effects.')
    (tmp_path/'connected-action-trace.json').write_text(json.dumps(trace,indent=2)+'\n')


@pytest.mark.parametrize('mutation,code',[
    ('cycle','ACTION_DEPENDENCY_INVALID'),('unknown','ACTION_CAPABILITY_UNKNOWN'),('unknown_dependency','ACTION_DEPENDENCY_INVALID'),
    ('path','ACTION_BINDING_INVALID'),('type','ACTION_BINDING_INVALID'),('authority','ACTION_AUTHORITY_DENIED'),('approval','ACTION_APPROVAL_REQUIRED'),
    ('budget','ACTION_BINDING_INVALID'),('duplicate','ACTION_BINDING_INVALID')])
def test_rejects_invalid_plans_before_effects(connected,mutation,code):
    f=connected;req=deepcopy(f.request);a=req['action_plan']['actions']
    if mutation=='cycle':a[0]['depends_on']=['send']
    if mutation=='unknown':a[0]['capability_id']='invented.send'
    if mutation=='unknown_dependency':a[1]['depends_on']=['absent']
    if mutation=='path':a[-1]['bindings'][1]['path']=['invented']
    if mutation=='type':a[-1]['bindings'][1]['path']=['tabs']
    if mutation=='authority':a[-1]['bindings'][0]=bind('generated','to',action='email',path=['body'])
    if mutation=='approval':a[-1]['required_approvals']=[]
    if mutation=='budget':req['constraints']=dict(max_actions=1,max_seconds=300,max_llm_calls=32,max_tool_calls=16)
    if mutation=='duplicate':a[-1]['action_id']='sheet'
    with pytest.raises(RuntimeFailure) as error:f.c.prepare_actions(f.x.a,req)
    assert error.value.code==code
    assert not f.http.sent and not f.http.write_count


def test_repeated_gmail_capability_has_separate_approvals_inputs_and_receipts(connected):
    f=connected;request=deepcopy(f.request);second=deepcopy(request['action_plan']['actions'][-1]);second['action_id']='send_second'
    request['user_values']['second_body']='Independent explicit follow-up.';second['bindings'][-1]=bind('literal','body','second_body')
    request['action_plan']['actions'].append(second);request['action_plan']['completion_criteria'].append('send_second')
    doc,w,rid=compile_run(f,request);result=complete(f,w,rid);assert result['status']=='completed',stored(f,rid)
    final=stored(f,rid);one,two=[final['action_instances'][k] for k in ('send','send_second')]
    assert len(f.http.sent)==2 and one['resolved_inputs']['body']!=two['resolved_inputs']['body']
    assert one['output']['rfc_message_id']!=two['output']['rfc_message_id']
    assert one['approval_references']!=two['approval_references']
    assert len([t for t in doc['tasks'] if t['capability_id']=='tool.extension_mail_send'])==2


def test_unauthorized_recipient_never_reaches_mail_provider(connected):
    f=connected;request=deepcopy(f.request);request['user_values']['recipient']='intruder@example.com'
    _,w,rid=compile_run(f,request);result=complete(f,w,rid)
    assert result['status'] in ('failed','blocked') and not f.http.sent
    assert stored(f,rid)['error_code']=='DESTINATION_NOT_AUTHORIZED'


def test_payload_change_invalidates_exact_action_approval(connected):
    f=connected;_,w,rid=compile_run(f);first=advance(f,rid);decide(f,w,first);second=advance(f,rid)
    assert second['status']=='paused_for_approval'
    decide(f,w,second)
    # Corrupt persisted generated content after approval to exercise the last-moment digest check.
    with f.general.store.transaction() as db:
        run=f.runtime.load(db,rid,f.x.a);run['action_instances']['email']['output']['body']='Changed approved payload'
        f.runtime.save(db,run)
    result=advance(f,rid);assert result['status']=='blocked' and not f.http.sent
    assert stored(f,rid)['error_code']=='APPROVAL_ACTION_MISMATCH'


@pytest.mark.parametrize('receipt',['missing_id','wrong_url','failed'])
def test_invalid_creation_receipt_blocks_downstream_content_and_send(connected,receipt):
    f=connected;original=f.connectors['extension_sheets_create_report']
    class Broken:
        timeout=30;external_write=True;retry_safe=False
        def reservation(self,grant):return {'tool_calls':1,'estimated_cost_usd':0}
        def invoke(self,grant,inputs,effect):
            output=dict(spreadsheet_id='real_id',spreadsheet_url='https://docs.google.com/spreadsheets/d/real_id',title='Findings',reused=False,written_rows=1,report_sha256='a'*64)
            if receipt=='missing_id':output.pop('spreadsheet_id')
            if receipt=='wrong_url':output['spreadsheet_url']='https://evil.example/sheet'
            if receipt=='failed':output['status']='failed'
            return output
    f.connectors['extension_sheets_create_report']=Broken()
    _,w,rid=compile_run(f);run=complete(f,w,rid)
    assert run['status'] in ('failed','blocked') and not f.http.sent
    assert stored(f,rid)['action_instances']['email']['state']=='pending'


def test_permission_revocation_blocks_dispatch(connected):
    f=connected;_,w,rid=compile_run(f);first=advance(f,rid);decide(f,w,first)
    denied=deepcopy(f.x.a);denied['permissions'].remove('data.write')
    result=f.runner.advance(rid,denied)
    assert result['status']=='blocked' and f.http.write_count==0 and not f.http.sent


def test_optional_calendar_action_and_validated_times(connected):
    f=connected;request=deepcopy(f.request)
    request['user_values'].update(calendar='primary',start={'dateTime':'2027-01-04T10:00:00+05:30','timeZone':'Asia/Kolkata'},end={'dateTime':'2027-01-04T11:00:00+05:30','timeZone':'Asia/Kolkata'})
    event=action('calendar','tool.extension_calendar_create',[bind('literal','calendar_id','calendar'),bind('generated','event.summary',action='email',path=['subject']),bind('generated','event.description',action='email',path=['body']),bind('literal','event.start','start'),bind('literal','event.end','end')],['email'])
    request['action_plan']['actions'].append(event);request['action_plan']['completion_criteria'].append('calendar')
    _,w,rid=compile_run(f,request);assert complete(f,w,rid)['status']=='completed',stored(f,rid)
    assert len(f.http.events)==1 and f.http.events[0]['start']==request['user_values']['start']
    assert stored(f,rid)['action_instances']['calendar']['output']['event_id']


def test_generated_time_cannot_authorize_calendar_input(connected):
    f=connected;request=deepcopy(f.request)
    request['action_plan']['actions'].append(action('calendar','tool.extension_calendar_create',[bind('literal','calendar_id','calendar'),bind('generated','event',action='email')],['email']))
    request['user_values']['calendar']='primary'
    with pytest.raises(RuntimeFailure) as error:f.c.prepare_actions(f.x.a,request)
    assert error.value.code=='ACTION_AUTHORITY_DENIED'


def test_scope_and_control_metadata_cannot_be_rebound(connected):
    f=connected;doc=f.c.prepare_actions(f.x.a,f.request);w=f.c.workflow(f.x.a,doc['composition_id'])
    for key in ('workspace_id','subject_id'):
        other=deepcopy(f.x.a);other['subject'][key]='foreign'
        with pytest.raises(Exception):f.c.get(other,doc['composition_id'])
    w['metadata']['connected_action_plan']['scope']['client_id']='another_client'
    with f.general.store.transaction(write=False) as db:
        with pytest.raises(Exception):verify_composition(db,f.x.a,w)


def test_partial_failure_preserves_completed_actions_and_refuses_uncertain_replay(connected):
    f=connected
    original=f.connectors['extension_mail_send']
    class Uncertain:
        external_write=True;retry_safe=False;timeout=30
        def reservation(self,grant):return {'tool_calls':1,'estimated_cost_usd':0}
        def invoke(self,*args):raise OSError('transport lost after submission')
    f.connectors['extension_mail_send']=Uncertain()
    _,w,rid=compile_run(f);result=complete(f,w,rid)
    assert result['status']=='blocked'
    final=stored(f,rid);assert final['action_instances']['sheet']['state']=='completed'
    assert final['action_instances']['send']['external_effect_status']=='requires_reconciliation'
    assert advance(f,rid)['status']=='blocked' and f.http.write_count==1
    # The existing recovery boundary must refuse uncertain writes, rather than replaying them.
    with f.general.store.transaction() as db:
        run=f.runtime.load(db,rid,f.x.a);run['lease_until']=0;f.runtime.save(db,run)
    with pytest.raises(RuntimeFailure) as denied:f.runtime.recovery.resume(rid,f.x.a)
    assert denied.value.code=='RECOVERY_RECONCILIATION_REQUIRED'
    assert f.http.write_count==1 and not f.http.sent


def test_missing_inputs_and_expression_paths_never_execute(connected):
    f=connected
    for change in ('missing','expression'):
        request=deepcopy(f.request)
        if change=='missing':request['user_values'].pop('recipient')
        else:request['action_plan']['actions'][-1]['bindings'][0]['path']=['__class__']
        with pytest.raises(RuntimeFailure):f.c.prepare_actions(f.x.a,request)
    assert f.http.write_count==0 and not f.http.sent


def test_real_provider_forwards_memory_and_registered_action_catalogue():
    from planner.provider import OpenAIStructuredOutputProvider
    calls=[]
    client=SimpleNamespace(responses=SimpleNamespace(create=lambda **kw:(calls.append(kw) or SimpleNamespace(status='completed',output_text='{"actions":[],"completion_criteria":[],"missing_inputs":["recipient"]}'))))
    p=OpenAIStructuredOutputProvider(client=client)
    result=p.plan_actions('Prepare a message',{'capabilities':{'content.prepare':{}},'binding_context':{},'verified_experience_recommendations':[{'capability_id':'content.prepare'}]})
    payload=json.loads(calls[0]['input'][1]['content'])
    assert result['missing_inputs']==['recipient'] and payload['verified_experience_recommendations']
    assert payload['action_schema']['properties']['capability_id']['enum']==['content.prepare']
    assert not calls[0]['store'] and calls[0]['max_output_tokens']==16000


def test_action_plan_case_attachment_cas_persistence_and_existing_execution(connected,tmp_path):
    from tests.test_business_cases import stage,process
    f=connected;cases=BusinessCases(f.general);f.general.business_cases=cases
    caps=['business.read.complaints','content.prepare','tool.extension_sheets_create_report','tool.extension_mail_send']
    definition=process(stage(required_inputs={},required_capabilities=caps,allowed_tools=['business_retrieve_evidence','extension_sheets_create_report','extension_mail_send'],side_effect_classification='write',
        output_schema={'type':'object','required':['message_id'],'properties':{'message_id':{'type':'string'}}},output_bindings={'message_id':{'source':'receipt','path':'send.message_id'}},timeout_policy=dict(seconds=300,action='block')))
    cases.publish(f.x.a,definition)
    case=cases.create(f.x.a,dict(request_key='connected_case_001',process_definition_id=definition['process_definition_id'],process_definition_version=1,original_user_goal=f.request['objective'],business_request=dict(inputs=dict(identifiers=dict(complaint_id='C123')))))
    case=cases.command(f.x.a,case['case_id'],'prepare',dict(request_key='connected_case_prepare',expected_revision=case['revision']))
    req=deepcopy(f.request);req.pop('preparation_id');req['client_id']=case['client_id']
    attach=dict(request_key='connected_case_attach',expected_revision=case['revision'],stage_instance_id='first',plan_request=req)
    case=cases.attach_action_plan(f.x.a,case['case_id'],attach)
    assert cases.attach_action_plan(f.x.a,case['case_id'],attach)==case
    with pytest.raises(Exception):cases.attach_action_plan(f.x.a,case['case_id'],{**attach,'request_key':'changed_attach_key'})
    w=f.c.workflow(f.x.a,case['stages']['first']['composition_id']);assert f.adapter.approve_pending(w,f.x.a)['ready'];approve(f,w)
    case=cases.command(f.x.a,case['case_id'],'start',dict(request_key='connected_case_start',expected_revision=case['revision']))
    for attempt in range(4):
        stage_state=case['stages']['first']
        if stage_state['run_id']:
            run=f.runtime.public(stored(f,stage_state['run_id']))
            if run['status']=='paused_for_approval':decide(f,w,run)
        if case['case_status'] in ('COMPLETED','COMPLETED_PROVISIONALLY'):break
        case=cases.command(f.x.a,case['case_id'],'advance',dict(request_key='connected_case_advance_'+str(attempt),expected_revision=case['revision']))
    assert case['case_status'] in ('COMPLETED','COMPLETED_PROVISIONALLY'),case['stages']['first']
    assert case['stages']['first']['outputs']['message_id']['provenance_type']=='ACTUAL'
    reopened=BusinessCases(f.general).get(f.x.a,case['case_id'])
    assert reopened['stages']['first']['action_instances']['send']['verified_receipt']
    assert len(f.http.sent)==1 and f.http.write_count==1
    trace={'case':case,'composition':f.c.get(f.x.a,case['stages']['first']['composition_id']),'run':stored(f,case['stages']['first']['run_id'])}
    (tmp_path/'connected-case-trace.json').write_text(json.dumps(trace,indent=2)+'\n')


def test_research_search_to_public_fetch_preserves_actual_provenance(connected,monkeypatch):
    from runtime.supplier_search import SEARCH,PAGE,SupplierSearchConnector
    from workflow_api.public_research import definitions
    import hashlib
    f=connected
    for definition in definitions():
        tool=deepcopy(definition);assert tool['availability']=='enabled'
        policy=deepcopy(f.registry._policy);policy.version+=1;policy.approved_providers.add(tool['provider_id']);policy.agent_permissions.update(tool['permission_scopes']);policy.remaining_quota[tool['tool_id']]=20
        for a in (f.x.a,f.x.current):a['permissions']=sorted(set(a['permissions'])|set(tool['permission_scopes']));a['scopes']=sorted(set(a['scopes'])|set(tool['permission_scopes']))
        assert f.registry.update_policy(policy,f.x.a)['status']==200
        assert f.registry.register_tool(tool,f.x.a)['status']==200
        f.connectors[tool['tool_id']]=SupplierSearchConnector(tool)
    seen=[]
    def execute(connector,grant,inputs,effect,deadline):
        seen.append(deepcopy(inputs))
        if 'query' in inputs:return {'results':[{'title':'Complaint context','url':'https://public.example/report','snippet':'Public reference'}]}
        return dict(url=inputs['url'],text='Untrusted source text; review as evidence.',content_sha256=hashlib.sha256(b'controlled public source').hexdigest(),emails=[])
    monkeypatch.setattr(SupplierSearchConnector,'execute',execute)
    request=dict(objective='Research public context and fetch the first permitted result.',request_key='research_actions_001',client_id='simpson',user_values={'query':'public complaint','region':'in-en','count':1},
        action_plan=dict(actions=[action('search','tool.supplier_web_search',[bind('literal','query','query'),bind('literal','region','region'),bind('literal','max_results','count')]),
            action('fetch','tool.supplier_read_page',[bind('receipt','url',action='search',path=['results',0,'url'])],['search'])],completion_criteria=['fetch'],missing_inputs=[]))
    _,w,rid=compile_run(f,request);assert advance(f,rid)['status']=='completed',stored(f,rid)
    item=stored(f,rid)['action_instances']['fetch']
    assert item['verified_receipt'] and item['provenance_type']=='ACTUAL' and item['output']['content_sha256']
    assert seen[1]['url']==item['output']['url']=='https://public.example/report'


def test_optional_action_skips_without_provider_effect(connected):
    f=connected;req=deepcopy(f.request);req['user_values']['include_followup']=False
    optional=deepcopy(req['action_plan']['actions'][-1]);optional.update(action_id='followup',optional=True,when=dict(binding=bind('literal','enabled','include_followup'),equals=True))
    req['action_plan']['actions'].append(optional)
    _,w,rid=compile_run(f,req);assert complete(f,w,rid)['status']=='completed',stored(f,rid)
    assert stored(f,rid)['node_states']['followup']=='skipped' and len(f.http.sent)==1


def test_explicit_safe_read_recovery_preserves_completed_action_checkpoint(connected):
    f=connected;original=f.connectors['business_retrieve_evidence'];calls=[]
    class FlakyRead:
        external_write=False;retry_safe=False;timeout=1
        def bind_context(self,w,run,actor,node):self.inner=original.bind_context(w,run,actor,node);return self
        def reservation(self,grant):return {'tool_calls':1,'estimated_cost_usd':0}
        def invoke(self,grant,inputs,effect):
            calls.append(effect)
            if len(calls)==2:raise RuntimeFailure('CONNECTOR_TIMEOUT','Controlled pre-effect read timeout')
            return self.inner.invoke(grant,inputs,effect)
    f.connectors['business_retrieve_evidence']=FlakyRead()
    req=deepcopy(f.request);req['action_plan']['actions']=[deepcopy(req['action_plan']['actions'][0])]
    req['action_plan']['actions'][0]['action_id']='read_one'
    second=deepcopy(req['action_plan']['actions'][0]);second.update(action_id='read_two',depends_on=['read_one']);second['budget'].update(max_retries=1,max_tool_calls=2)
    req['action_plan']['actions'].append(second);req['action_plan']['completion_criteria']=['read_two']
    req['constraints']=dict(max_actions=4,max_seconds=300,max_llm_calls=0,max_tool_calls=3,max_retries=1)
    _,w,rid=compile_run(f,req);assert advance(f,rid)['status']=='failed'
    checkpoint=deepcopy(stored(f,rid)['task_checkpoints']['read_one'])
    with f.general.store.transaction() as db:
        run=f.runtime.load(db,rid,f.x.a);run['lease_until']=0;f.runtime.save(db,run)
    f.runtime.recovery.resume(rid,f.x.a)
    assert advance(f,rid)['status']=='completed',stored(f,rid)
    assert stored(f,rid)['task_checkpoints']['read_one']==checkpoint
    assert calls.count(rid+':read_one')==1 and calls.count(rid+':read_two')==2
    assert stored(f,rid)['recovery_history'][0]['affected_tasks']==['read_two']


def test_existing_general_plan_operation_supports_connected_mode(connected):
    f=connected;context=deepcopy(f.request);objective=context.pop('objective');key=context.pop('request_key');context['planning_mode']='connected_actions'
    result=f.general.handle(dict(request_id='connected_api',operation='plan_workflow',idempotency_key=key,payload=dict(objective=objective,context=context)),f.x.a)
    assert result['status']==200,result
    assert result['data']['plan']['schema_version']=='orchestration-plan-v1'
    assert result['data']['workflow']['metadata']['connected_action_plan']['plan_id']==result['data']['plan']['plan_id']
    from workflow_api.composition_presentation import CompositionPresentation
    assert CompositionPresentation(f.c).view(f.x.a,result['data']['composition_id'])['tasks']


def test_missing_registered_permission_excluded_before_model_selection(connected):
    f=connected;denied=deepcopy(f.x.a);denied['permissions'].remove('communication.send');f.x.current['permissions'].remove('communication.send')
    with pytest.raises(RuntimeFailure) as error:f.c.prepare_actions(denied,f.request)
    assert error.value.code=='ACTION_CAPABILITY_UNKNOWN' and not f.http.sent


def test_empty_and_failed_provider_plans_are_rejected(connected):
    f=connected
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda *args:{'actions':[],'completion_criteria':[],'missing_inputs':['recipient']})
    request=deepcopy(f.request);request.pop('action_plan')
    with pytest.raises(RuntimeFailure):f.c.prepare_actions(f.x.a,request)
    assert not f.http.sent and f.http.write_count==0


def test_action_plan_http_uses_existing_session_origin_and_scope_controls(tmp_path):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    app=create_app(database=tmp_path/'action-api.sqlite',dev_auth=True,roles=['admin'],runtime_enabled=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app);base='/business-ontology/v1/action-plans'
    assert client.post(base,json={}).status_code==401
    assert client.get(base+'/composition_missing').status_code==401
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    assert client.post(base,json={},headers={'origin':'https://untrusted.example'}).status_code==403
    assert client.post(base,json={}).status_code==422
    assert client.get(base+'/composition_missing').status_code==404


def test_registered_connected_tool_coverage_reuses_existing_adapters():
    from workflow_api.capability_contracts import catalogue
    from runtime.supplier_search import SEARCH,PAGE
    records=[{'tool_id':d['tool_id'],'definition':d} for d in [*CATALOG.values(),SEARCH,PAGE]]
    caps=catalogue(None,records)
    for tid in ('extension_mail_search','extension_mail_message','extension_mail_thread','extension_mail_attachment','extension_mail_profile','extension_mail_draft','extension_mail_send','extension_mail_reply',
                'google_sheets_read_rows','google_sheets_upsert_record','extension_sheets_create','extension_sheets_create_report',
                'extension_calendar_discover','extension_calendar_list','extension_calendar_create','extension_calendar_update','extension_calendar_cancel','extension_web_search','supplier_read_page'):
        assert 'tool.'+tid in caps,tid


def test_specialist_cannot_invent_mapped_evidence_references():
    from runtime.action_plans import verify
    workflow={'metadata':{'connected_action_plan':{'actions':[{'action_id':'compare','capability_id':'business.compare'}]}}}
    output={'summary':'Claim','findings':[{'kind':'observation','statement':'Invented fact','references':[{'record_id':'not_supplied','mapping_id':'mapping:absent'}]}],'missing_information':[]}
    with pytest.raises(RuntimeFailure):verify(workflow,{'node_id':'compare','kind':'agent'},output,{'context':{'evidence':{'records':[]}}})


def test_unanchored_case_read_requires_clarification_before_compilation(connected):
    f=connected
    prepared=f.general.business_preparation.prepare(f.x.a,dict(objective='Compare complaints with linked inspections.'))
    req=dict(objective='List up to 10 complaints with linked inspection records, newest first.',request_key='unanchored_read_001',
        preparation_id=prepared['preflight_id'],user_values={'task':'complaints'},action_plan=dict(actions=[
            action('read','business.read.complaints',[bind('context','preparation_id','preparation_id'),bind('literal','task','task')])],completion_criteria=['read'],missing_inputs=[]))
    f.x.reader.calls.clear()
    with pytest.raises(RuntimeFailure) as error:
        f.c.prepare_actions(f.x.a,req)
    assert error.value.code=='ACTION_INPUT_REQUIRED'
    assert 'complaint_id' in error.value.required_inputs
    assert not f.x.reader.calls
    with f.x.f.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM business_compositions').fetchone()[0]==0


def test_explicit_case_identifier_reprepares_unanchored_read(connected):
    f=connected
    prepared=f.general.business_preparation.prepare(f.x.a,dict(objective='Compare complaints with linked inspections.'))
    req=dict(objective='Show the selected complaint and its inspection.',request_key='anchored_read_input_001',
        preparation_id=prepared['preflight_id'],user_values={'task':'complaints','complaint_id':'C123'},action_plan=dict(actions=[
            action('read','business.read.complaints',[bind('context','preparation_id','preparation_id'),bind('literal','task','task')])],completion_criteria=['read'],missing_inputs=[]))
    doc=f.c.prepare_actions(f.x.a,req)
    current=f.general.business_preparation.checked(f.x.a,doc['preparation_id'])
    assert current['inputs']['identifiers']=={'complaint_id':'C123'}
    assert current['preflight_id']!=prepared['preflight_id']
    assert f.general.business_preparation.get(f.x.a,prepared['preflight_id'])['inputs']['identifiers']=={}


@pytest.mark.parametrize('body',[
    'Report: https://docs.google.com/spreadsheets/d/approved_book/edit.',
    '[Report](https://docs.google.com/spreadsheets/d/approved_book/edit)',
])
def test_verified_content_accepts_provided_link_in_prose(body):
    from runtime.action_plans import verify
    workflow={'metadata':{'connected_action_plan':{'actions':[{'action_id':'content','capability_id':'content.prepare'}]}}}
    verify(workflow,{'node_id':'content','kind':'agent'},{'body':body,'source_references':[]},
        {'source_references':[],'artifact_url':'https://docs.google.com/spreadsheets/d/approved_book/edit'})


def test_unprovided_content_url_gets_only_one_pure_model_correction():
    from runtime.action_plans import validate_content
    from shared.llm_feedback import correct_once
    workflow={'metadata':{'connected_action_plan':{'actions':[{'action_id':'content','capability_id':'content.prepare'}]}}}
    node={'node_id':'content','kind':'agent'};calls=[]
    def invoke(feedback):
        calls.append(feedback)
        output={'body':'https://unprovided.example/link','source_references':[]}
        validate_content(workflow,node,output,{'source_references':[]})
        return output
    corrections=[]
    with pytest.raises(RuntimeFailure) as error:correct_once(invoke,lambda item:corrections.append(item))
    assert error.value.code=='ACTION_CONTENT_UNVERIFIED'
    assert len(calls)==2 and len(corrections)==1
    assert 'unprovided.example' not in str(corrections)


@pytest.mark.parametrize('call_allowance',[1,2])
def test_corrected_email_content_preserves_created_sheet_and_send(connected,call_allowance):
    f=connected;original=f.runner.agents
    class Adapter:
        external_write=False
        def reservation(self,*args):return {'llm_calls':1,'tokens':100,'estimated_cost_usd':0}
        def invoke(self,binding,inputs,reference):
            output=original.invoke(binding,inputs,reference)
            if inputs.get('artifact_url') and not binding.get('_validation_feedback'):
                output['body']='Review https://unprovided.example/link'
            return output
    f.runner.agents=Adapter()
    request=deepcopy(f.request)
    next(a for a in request['action_plan']['actions'] if a['action_id']=='email')['budget']['max_llm_calls']=call_allowance
    _,workflow,rid=compile_run(f,request)
    result=complete(f,workflow,rid)
    if call_allowance==1:
        assert result['status']=='failed' and stored(f,rid)['error_code']=='ACTION_CONTENT_UNVERIFIED'
        assert f.http.write_count==1 and not f.http.sent
        return
    assert result['status']=='completed',stored(f,rid).get('error_code')
    assert f.http.write_count==1 and len(f.http.sent)==1
    events=f.runtime.events(rid,f.x.a)['items']
    assert any(e['event_type']=='agent.correction' and e['details']['validation_feedback'][0]['code']=='ACTION_CONTENT_UNVERIFIED' for e in events)


def test_generated_unconditional_completion_flag_is_normalized_before_review(connected):
    f=connected;draft=proposal(f.prepared);draft['actions'][-1]['optional']=True
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda *_:deepcopy(draft))
    request=deepcopy(f.request);request.pop('action_plan')
    doc=f.c.prepare_actions(f.x.a,request)
    assert doc['composition_id']
    assert draft['actions'][-1]['optional'] is True  # Never mutate provider input.
    send=doc['action_plan']['actions'][-1]
    assert send['optional'] is False and send['when'] is None
    assert send['required_approvals']==['exact_payload'] and doc['action_plan']['completion_criteria']==['send']
    assert not f.http.sent and f.http.write_count==0


def test_explicit_unconditional_optional_completion_still_rejected(connected):
    f=connected;request=deepcopy(f.request)
    request['action_plan']['actions'][-1]['optional']=True
    with pytest.raises(RuntimeFailure) as error:f.c.prepare_actions(f.x.a,request)
    assert error.value.code=='ACTION_BINDING_INVALID'
    assert error.value.binding_issue['action_ids']==['send']
    assert not f.http.sent and f.http.write_count==0


def test_generated_real_condition_gets_bounded_precise_correction(connected):
    f=connected;corrected=proposal(f.prepared)
    corrected.update(actions=corrected['actions'][:2],completion_criteria=['analysis'])
    draft=deepcopy(corrected)
    draft['actions'][-1].update(optional=True,when=dict(binding=bind('literal','enabled','include_analysis'),equals=True))
    contexts=[]
    def selector(goal,context):
        contexts.append(deepcopy(context))
        return deepcopy(draft if len(contexts)==1 else corrected)
    f.general.planner.provider=SimpleNamespace(plan_actions=selector)
    request=deepcopy(f.request);request.pop('action_plan');request['automatic_inputs']=True
    assert f.c.prepare_actions(f.x.a,request)['composition_id']
    assert len(contexts)==2
    issue=contexts[1]['validation_feedback']['binding_issue']
    assert issue['field']=='completion_criteria' and issue['action_ids']==['analysis']
    assert contexts[1]['validation_feedback']['invalid_proposal']['actions'][-1]['when'] is not None
    assert not f.http.sent and f.http.write_count==0


def test_generated_optional_flag_does_not_hide_missing_recipient(connected):
    f=connected;draft=proposal(f.prepared);draft['actions'][-1]['optional']=True
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda *_:deepcopy(draft))
    request=deepcopy(f.request);request.pop('action_plan');request['user_values'].pop('recipient')
    with pytest.raises(RuntimeFailure) as error:f.c.prepare_actions(f.x.a,request)
    assert error.value.code=='ACTION_INPUT_REQUIRED'
    assert 'recipient' in error.value.required_inputs
    assert not f.http.sent and f.http.write_count==0


def test_repeated_conditional_completion_stops_after_one_correction(connected):
    f=connected;draft=proposal(f.prepared)
    draft.update(actions=draft['actions'][:2],completion_criteria=['analysis'])
    draft['actions'][-1].update(optional=True,when=dict(binding=bind('literal','enabled','include_analysis'),equals=True))
    calls=[]
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda *args:(calls.append(1) or deepcopy(draft)))
    request=deepcopy(f.request);request.pop('action_plan');request['automatic_inputs']=True
    with pytest.raises(RuntimeFailure) as error:f.c.prepare_actions(f.x.a,request)
    assert error.value.code=='ACTION_BINDING_INVALID' and len(calls)==2
    assert draft['actions'][-1]['optional'] is True and draft['actions'][-1]['when'] is not None
    assert not f.http.sent and f.http.write_count==0


def test_ontology_usage_pin_and_verified_read_survive_saved_plan_and_run(connected):
    f=connected
    doc,w,rid=compile_run(f)
    pin=doc['binding_context']['validated_context']['ontology_usage']
    assert pin['version_id']==f.prepared['version_id']
    assert pin['scope']==dict(workspace_id='one',owner_id='alice')
    assert w['metadata']['action_binding_context']['validated_context']['ontology_usage']==pin
    assert f.c.get(f.x.a,doc['composition_id'])['binding_context']['validated_context']['ontology_usage']==pin
    run=complete(f,w,rid)
    assert run['status']=='completed'
    saved=stored(f,rid);instances=saved['action_instances']
    assert instances['read']['ontology_usage']
    assert {u['version_id'] for u in instances['read']['ontology_usage']}=={pin['version_id']}
    assert instances['analysis']['ontology_usage']
    assert instances['send']['ontology_usage']==[]
    from workflow_api.composition_presentation import CompositionPresentation
    public=CompositionPresentation(f.c).view(f.x.a,doc['composition_id'],rid)
    assert public['run']['action_instances']['read']['ontology_usage']==instances['read']['ontology_usage']
