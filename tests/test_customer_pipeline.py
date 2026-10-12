"""Simple prompt -> discovery -> published dynamic agents -> automatic emails/replies."""
from copy import deepcopy
from email.message import EmailMessage
from io import BytesIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlparse

from runtime.model import BoundedLLM
from runtime.sheet_records import table_range
from tests.test_sheet_records import authored_workflow
from tests.test_slack_gmail import FakeSMTP
from workflow_api.live_providers import create_configured_app

ROOT = Path(__file__).resolve().parents[1]


class CustomerPipelineTests(unittest.TestCase):
    def test_restaurant_and_manufacturing_with_three_supporting_tables(self):
        for domain in ('restaurant','manufacturing'):
            with self.subTest(domain=domain):
                self.check_pipeline(domain)

    def check_pipeline(self, domain):
        source = 'Customer requests'
        tabs = ['Inspection records','Processing records','Delivery records']
        spreadsheet = 'test_sheet_123456789012345'
        tables = {source:[['Record','Contact Email','Reference','Concern','Customer'],['old','old@example.com','old-ref','Old case','Old']],
                  **{tab:[['Reference','Notes'],['REF1', f'Actual evidence from {tab}']] for tab in tabs}}
        workflow = authored_workflow((source,tabs[0],'Record','Reference','lookup'),spreadsheet)
        workflow['workflow_id'] = 'automatic-' + domain
        workflow['error_policy'].update(max_retries=0, on_runtime_error='stop')
        template = workflow['agents'][1]
        lookups = []
        for i in range(3):
            agent = deepcopy(template)
            agent.update(agent_id=f'lookup_{i}',role=f'lookup_{i}')
            lookups.append(agent)
        sender = workflow['agents'][-1]
        sender.update(agent_id='sender', role='Deterministic customer sender', capabilities=['send_email'],permissions=['communication.send'])
        sender['limits']['max_tool_calls'] = 1
        workflow['agents'] = [workflow['agents'][0],*lookups,workflow['agents'][2],sender]
        workflow['tools'] = [{'tool_id':'google_sheets_read_rows','capability':'read_spreadsheet'},
                             {'tool_id':'smtp_send_email','capability':'send_email'}]
        workflow['nodes'] = workflow['nodes'][:2] + [
            {'node_id':'send','kind':'tool','label':'Send customer email','agent_id':'sender','tool_id':'smtp_send_email',
             'configuration':{'input_mapping':{'to':'inputs.row["Contact Email"]','subject':'outputs.master.draft_fields.subject','body':'outputs.master.draft_fields.body'}}},
            {'node_id':'done','kind':'output','label':'Complete'}]
        workflow['edges'] = [{'edge_id':str(i),'source':a,'target':b} for i,(a,b) in enumerate([('incoming','master'),('master','send'),('send','done')])]
        workflow['metadata'].pop('sheet_write_targets')
        workflow['metadata']['email_recipient_policy']={'mode':'source_row','field':'Contact Email'}
        workflow['metadata']['customer_automation']={'mode':'automatic','manager_email':'owner@example.com',
            'case_fields':{'identity':'Record','reference':'Reference','complaint':'Concern','name':'Customer'},'close_on_customer_confirmation':True}
        workflow['metadata']['sheet_read_targets']=[{'spreadsheet_id':spreadsheet,'range':f"'{tab}'!A1:B100"} for tab in tabs]
        poll=workflow['metadata']['trigger_templates'][0]['poll_input']
        poll.update(range=f"'{source}'!A1:E100",required_fields=['Record','Contact Email','Reference','Concern'])
        requests,planning,model_calls=[],[],[]
        def http(request, timeout):
            requests.append(request)
            self.assertEqual(request.get_method(),'GET')
            parsed=urlparse(request.full_url)
            if '/values/' not in parsed.path:
                return BytesIO(json.dumps({'properties':{'title':domain},'sheets':[{'properties':{
                    'title':tab,'gridProperties':{'rowCount':100,'columnCount':26}}} for tab in tables]}).encode())
            cell_range=unquote(parsed.path.split('/values/',1)[1])
            tab,left,top,right,bottom=table_range(cell_range)
            name=tab[1:-1].replace("''", "'")
            return BytesIO(json.dumps({'values':[r[left-1:right] for r in tables[name][top-1:bottom]]}).encode())
        def plan(**kwargs):
            planning.append(json.loads(kwargs['input'][1]['content']))
            return SimpleNamespace(output_text=json.dumps(workflow))
        def factory(definition):
            def provider(messages,cap,timeout):
                raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
                context,_=json.JSONDecoder().raw_decode(raw)
                role=definition['role']; model_calls.append(role)
                if role=='supervisor':
                    results=context['results']
                    available = {a['role']: a['agent_id'] for a in context['available_agents']}
                    if not results:
                        output={'action':'delegate','reason':'Check the published supporting tables.','tasks':[
                            {'agent_id':available[f'lookup_{i}'],'inputs':{'spreadsheet_id':spreadsheet,'range':f"'{tab}'!A1:B100",'reference':'REF1'},
                             'reason':'Find actual supporting evidence.'} for i,tab in enumerate(tabs)]}
                    elif len(results)==3:
                        output={'action':'delegate','reason':'Compose a cumulative evidence-based response.','tasks':[
                            {'agent_id':available['draft_specialist'],'inputs':{'reports':[r['result'] for r in results]},'reason':'Draft from all reports.'}]}
                    else:
                        output={'action':'finish','reason':'Return the checked draft.','output':results[-1]['result']}
                elif role.startswith('lookup_'):
                    if not context['tool_results']:
                        output={'action':'tool','reason':'Read the configured supporting table.','tool_id':'google_sheets_read_rows',
                            'inputs':{k:context['request'][k] for k in ('spreadsheet_id','range')}}
                    else:
                        output={'action':'finish','reason':'Report actual matched evidence.','output':{'findings':context['tool_results'][0]['output']['rows'][1][1]}}
                else:
                    body='; '.join(r['findings'] for r in context['reports'])
                    output={'draft_fields':{'findings':body,'subject':'Case update','body':body,'status':'Awaiting reply'},'status_fields':{'status':'Awaiting reply'}}
                return json.dumps(output),20,20
            return BoundedLLM(definition,provider,lambda messages:100,.0000002,.0000012)
        with tempfile.TemporaryDirectory(dir=ROOT / '.local') as directory:
            path=Path(directory);(path/'token.json').write_text('{}')
            env={'OPENAI_API_KEY':'test-only','OPENAI_MODEL':'gpt-5.6-luna','GMAIL_SMTP_USER':'owner@example.com',
                 'GMAIL_SMTP_PASSWORD':'test-only','GOOGLE_TOKEN_FILE':str(path/'token.json'),
                 'BUILDER_EMAIL_RECIPIENTS':'owner@example.com','BUILDER_EMAIL_DIRECT_SEND':'1','BUILDER_REPLY_MONITOR':'1'}
            client=SimpleNamespace(responses=SimpleNamespace(create=plan))
            with patch('workflow_api.live_providers.REGISTRY',path/'registry.json'), patch('runtime.connectors._google_credentials',return_value=SimpleNamespace(token='test-only')), patch('runtime.connectors.urlopen',side_effect=http):
                app=create_configured_app(env,path/'workflows.sqlite3',client=client,model_factory=factory)
                service=app.state.workflow_service;auth=app.state.live_operator_auth
                service.runtime_runner.connectors['smtp_send_email'].transport=FakeSMTP
                service.reply_cases.smtp_factory=FakeSMTP;FakeSMTP.messages=[]
                def call(operation,payload,key):
                    key = 'pipeline_' + key
                    response=service.handle({'request_id':key,'operation':operation,'idempotency_key':key,'payload':payload},auth)
                    self.assertEqual(response['status'],200,response)
                    return response['data']
                objective=f'Automatically handle {domain} customer complaints using https://docs.google.com/spreadsheets/d/{spreadsheet}/edit. Email customers, monitor replies, escalate to owner@example.com, and close only on their confirmation. Keep Sheets read-only.'
                planned=call('plan_workflow',{'objective':objective,'context':{'generation_mode':'hierarchy','execution_input_mode':'automatic'}},'plan')['workflow']
                self.assertEqual(len(planning[0]['context']['discovered_spreadsheets'][0]['tables']),4)
                self.assertNotIn('old@example.com',json.dumps(planning[0]['context']['discovered_spreadsheets']))
                self.assertNotIn('sample_rows',json.dumps(planned['metadata']['sheet_catalog']))
                ref={'workflow_id':planned['workflow_id'],'workflow_version':1}
                call('save_workflow_version',{**ref,'base_version':0,'workflow':planned},'save')
                call('validate_workflow',ref,'validate');call('approve_workflow',{**ref,'action':'approve'},'review')
                call('approve_workflow',{**ref,'action':'publish'},'publish')
                service.lifecycle.activate({'request_id':'activate','idempotency_key':'activate','payload':{**ref,'triggers':[]}},auth)
                scheduler=app.state.live_workers[0];scheduler.tick()
                tables[source].append(['NEW1','customer@example.com','REF1','The issue needs investigation.','Customer'])
                scheduler.last_polled.clear();self.assertEqual(scheduler.tick()['dispatched'],1)
                with service.store.transaction() as db:
                    run=json.loads(db.execute('SELECT document FROM runtime_runs').fetchone()[0])
                self.assertEqual(run['status'],'completed',run)
                self.assertEqual(run['approvals'],[])
                self.assertEqual(len(FakeSMTP.messages),1)
                self.assertEqual(FakeSMTP.messages[0]['To'],'customer@example.com')
                self.assertTrue(all(f'Actual evidence from {tab}' in FakeSMTP.messages[0].get_content() for tab in tabs))
                self.assertTrue({'lookup_0','lookup_1','lookup_2','draft_specialist','supervisor'} <= set(model_calls))
                class Replies:
                    def create(inner,**kwargs):
                        payload=json.loads(kwargs['input'][1]['content'])
                        if not payload['read_results']:
                            return SimpleNamespace(output_text=json.dumps({'action':'read','read_requests':[{
                                'spreadsheet_id':spreadsheet,'range':f"'{tabs[0]}'!A1:B100",'match_column':'Reference','source_column':'Reference'}]}))
                        resolved=payload['customer_reply']=='The issue is resolved.'
                        return SimpleNamespace(output_text=json.dumps({'action':'finish','decision':'resolution_confirmed' if resolved else 'manager_review',
                            'reason':'Reviewed customer response and fresh evidence.','customer_followup':'Thank you for the update.',
                            'resolution_evidence':payload['customer_reply'] if resolved else ''}))
                service.reply_cases.model=SimpleNamespace(responses=Replies())
                service.reply_cases.sync_sent_runs(auth['subject']['workspace_id'])
                def reply(body,uid,reference):
                    m=EmailMessage();m['From']='customer@example.com';m['To']='owner@example.com';m['Message-ID']=f'<reply-{uid}@example.com>'
                    m['In-Reply-To']=reference;m.set_content(body)
                    self.assertTrue(service.reply_cases.accept_message(auth['subject']['workspace_id'],'owner@example.com','1',uid,m.as_bytes()))
                    service.reply_cases.process_pending(auth['subject']['workspace_id'])
                reply('Please ask the manager to review this.','10',run['outputs']['send']['message_id'])
                self.assertEqual([m['To'] for m in FakeSMTP.messages],['customer@example.com','customer@example.com','owner@example.com'])
                reply('The issue is resolved.','11',FakeSMTP.messages[1]['Message-ID'])
                self.assertEqual(service.reply_cases.list_cases(auth['subject']['workspace_id'])[0]['status'],'Closed')
                self.assertEqual(len(FakeSMTP.messages),5)
                self.assertEqual(tables[source][-1][-2],'The issue needs investigation.')
                self.assertTrue(all(request.get_method()=='GET' for request in requests))


if __name__=='__main__':
    unittest.main()
