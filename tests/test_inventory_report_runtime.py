"""Complete native runtime with real journals and offline DB/web/Google transports."""
from copy import deepcopy
import base64
from email import message_from_bytes
import json
from urllib.parse import urlparse
import pytest
from connector_extension.tests.test_sheet_report import ReportProvider
from tests.test_inventory_report_planner import PROMPT, proposal, record, source_catalog
from workflow_api.inventory_report_planner import compile_inventory_report
from workflow_api.database_workflows import bind_generated


class GoogleProvider(ReportProvider):
    def __init__(self):super().__init__();self.sent=[];self.events=[]
    def request(self,method,url,headers,body=None,timeout=30):
        path=urlparse(url).path
        if path.endswith('/profile'):return {'emailAddress':'owner@example.com'}
        if path.endswith('/messages/send'):
            self.sent.append(message_from_bytes(base64.urlsafe_b64decode(body['raw']+'==')))
            return {'id':'sent_report','threadId':'report_thread'}
        if '/calendar/v3/' in path and method=='POST':
            self.events.append(deepcopy(body));return {'id':body['id'],'status':'confirmed'}
        return super().request(method,url,headers,body,timeout)


class ReadProvider:
    retry_safe=False;external_write=False;timeout=1
    def __init__(self,result,calls):self.result,self.calls=result,calls
    def reservation(self,grant):return {'tool_calls':1,'estimated_cost_usd':0}
    def invoke(self,grant,inputs,invocation):
        self.calls.append((grant['tool_id'],deepcopy(inputs)));return deepcopy(self.result)


class OfflineAgents:
    retry_safe=False;external_write=False
    def reservation(self,agent):return {'llm_calls':1,'tokens':10,'estimated_cost_usd':0}
    def invoke_decision(self,agent,context,invocation,schema):
        if context['pending_tasks']:return {'action':'wait','reason':'Wait for actual evidence.'}
        if not context['results']:
            return {'action':'delegate','reason':'Retrieve both evidence types.','tasks':[
                {'agent_id':a['agent_id'],'inputs':{},'reason':'Read assigned sources.'} for a in context['available_agents']]}
        results={r['agent_id']:r['result'] for r in context['results']}
        risk=next(v for k,v in results.items() if 'supply_risk' in k)
        return {'action':'finish','reason':'Use actual returned evidence.','output':risk}
    def invoke_tool_decision(self,agent,context,invocation,schema):
        if 'inventory_reader' in agent['agent_id']:
            if not context['tool_results']:
                plan={'base_dataset_id':'products','joins':[],'fields':[],'filters':[], 'group_by':[],
                      'metrics':[],'order_by':[],'limit':500,'explanation':'Read fixture inventory','clarification':''}
                return {'action':'tool','reason':'Read actual fixture rows.','tool_id':'database_read_query','inputs':{'plan':plan}}
            result=context['tool_results'][0]['output']
            return {'action':'finish','reason':'Use returned rows.','output':{'records':result['rows'],'limited':result['limited']}}
        if not context['tool_results']:
            return {'action':'tool','reason':'Retrieve public fixture sources.','tool_id':'supplier_web_search',
                    'inputs':{'query':'food wholesale supply risks','region':'wt-wt','max_results':3}}
        result=context['tool_results'][0]['output']['results']
        return {'action':'finish','reason':'Cite retrieved evidence.','output':{'external_risks':[
            {'finding':r['snippet'],'source_url':r['url']} for r in result]}}


@pytest.mark.parametrize('reject_at',[None,0,1,2])
def test_native_report_sequence_requires_each_approval_and_uses_actual_url(reject_at):
    from tests.test_integrated_procurement import IntegratedTests
    case=IntegratedTests(methodName='test_native_prompt_to_approved_sends_and_tracking');case.setUp()
    try:
        config=json.loads((case.path/'config.json').read_text());config['enabled_providers'].append('google_calendar')
        (case.path/'config.json').write_text(json.dumps(config));case.http=GoogleProvider();case.start()
        s=case.service;runner=s.runtime_runner;calls=[]
        stock=[record('covered',on_order=10),record('urgent',stock=1),record('less_urgent',stock=8)]
        query={'columns':[],'rows':stock,'total_result_rows':3,'limited':False,'sources':[], 'join_checks':[],'execution':{},'warnings':[]}
        runner.connectors['database_read_query']=ReadProvider(query,calls)
        runner.connectors['supplier_web_search']=ReadProvider({'results':[{'title':'Public fixture','url':'https://example.org/supply','snippet':'External fixture finding'}]},calls)
        runner.agents=OfflineAgents()
        tools=s.registry.list_tools(case.auth)['data']['items'];defs=[t['definition'] for t in tools]
        catalog=source_catalog()
        context={'google_connection_id':'gc_'+'a'*32,'database_catalog':catalog,'database_workflow_tools':defs,'workflow_google_tools':defs}
        w=compile_inventory_report(proposal(),PROMPT,context);w['workflow_id']='offline_report_sequence'
        bind_generated(w,context)
        # Existing DB scope/query guards have their own real-storage tests. This
        # fixture substitutes only the external dataset lookup and query result.
        s.database_workflows.scope=lambda actor,workflow,requested=():(workflow['metadata']['database_scope'],catalog)
        s.database_workflows.queries.context=lambda actor:({}, {}, {}, {})
        s.database_workflows.queries.validate=lambda plan,ctx:({'products':set(),'categories':set(),'suppliers':set()},None,None)
        ref={'workflow_id':w['workflow_id'],'workflow_version':1}
        case.call('save_workflow_version',{**ref,'base_version':0,'workflow':w})
        case.call('validate_workflow',ref);case.call('approve_workflow',{**ref,'action':'approve'})
        case.call('approve_workflow',{**ref,'action':'publish'})
        run=case.call('execute_workflow',{**ref,'inputs':{}})['run']
        for stage in range(3):
            assert run['status']=='paused_for_approval',json.dumps({'run':run,'events':runner.runtime.events(run['run_id'],case.auth)['items'][-5:]})
            assert len(case.http.books)==(0 if stage==0 else 1)
            assert len(case.http.sent)==(1 if stage==2 else 0)
            assert case.http.events==[]
            approval=next(a for a in run['approvals'] if a['status']=='pending')
            case.call('decide_approval',{**ref,'approval_id':approval['approval_id'],
                'decision':'rejected' if stage==reject_at else 'approved'})
            run=runner.runtime.get_run(run['run_id'],case.auth)
            if stage==reject_at:
                assert run['status']=='rejected';return
        assert run['status']=='completed',json.dumps(run)
        assert {c[0] for c in calls}=={'database_read_query','supplier_web_search'}
        assert len(case.http.books)==len(case.http.sent)==len(case.http.events)==1
        message=case.http.sent[0];event=case.http.events[0]
        assert message['To']=='owner@example.com'
        assert 'https://docs.google.com/spreadsheets/d/created_1/edit' in message.get_payload(decode=True).decode()
        assert 'https://docs.google.com/spreadsheets/d/created_1/edit' in event['description']
        assert event['start']['dateTime']=='2026-10-19T15:30:00+05:30'
        assert event['end']['dateTime']=='2026-10-19T16:00:00+05:30'
        inventory=case.http.books['created_1']['sheets'][0]['business_rows']
        assert len(inventory)==3 and inventory[0][0]=='urgent' and inventory[0][8]==9
    finally:case.doCleanups()
