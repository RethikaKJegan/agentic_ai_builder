"""Account connections with workflow-selected Calendar, Mail and search resources."""
import base64
from email import message_from_bytes
from email.policy import default
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse
from connector_extension.app import create_extension_app, STATE_ROOT
from connector_extension.calendar import CalendarConnector
from connector_extension.catalog import CATALOG, GOOGLE
from connector_extension.common import ArtifactStore, EffectJournal
from connector_extension.examples import connector_workflow
from connector_extension.google import GoogleAPI
from connector_extension.mail import MailConnector
from connector_extension.search import SearchConnector
from connector_extension.authorize_google import required_scopes
from connector_extension.tests.test_connectors import FakeTransport, grant
from runtime.service import RuntimeFailure


def calendar_page():
    return {'items':[{'id':'owner@example.com','summary':'Personal','timeZone':'Asia/Kolkata','accessRole':'owner','primary':True},
                     {'id':'team_calendar','summary':'Team','timeZone':'Europe/London','accessRole':'writer'}], 'nextPageToken':'next'}


class GeneralizedFeatureTests(unittest.TestCase):
    def setUp(self):
        STATE_ROOT.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=STATE_ROOT);self.root=Path(self.temp.name)
        self.journal=EffectJournal(self.root);self.artifacts=ArtifactStore(self.root)
        self.event={'summary':'Deadline','start':{'date':'2026-11-01'},'end':{'date':'2026-11-02'}}
    def tearDown(self):self.temp.cleanup()
    def api(self,transport):return GoogleAPI(lambda scopes,timeout:'offline',transport)
    def mail(self,action,transport,recipients=None):
        return MailConnector(CATALOG['extension_mail_'+action],self.api(transport),self.journal,self.artifacts,recipients=recipients)

    def test_connected_groups_need_no_resource_presets(self):
        app=create_extension_app({'enabled_providers':['google_sheets','google_calendar','gmail','brave_search']},self.root,
            transport=FakeTransport(),token_supplier=lambda scopes,timeout:'offline',search_key='offline')
        items=app.state.workflow_service.registry.list_tools(app.state.extension_auth)['data']['items']
        self.assertEqual(len(items),19)
        existing=[item for item in items if item['tool_id'] not in {'extension_sheets_create','extension_sheets_add_tabs'}]
        self.assertTrue(all(item['definition']['availability']=='enabled' for item in existing))
        self.assertEqual(len(app.state.workflow_service.runtime_runner.connectors),17)
        self.assertIn(GOOGLE+'calendar.calendarlist.readonly',required_scopes(['google_calendar']))

    def test_calendar_discovery_returns_real_account_resources_and_pagination(self):
        transport=FakeTransport(calendar_page())
        connector=CalendarConnector(CATALOG['extension_calendar_discover'],self.api(transport))
        result=connector.invoke(grant('extension_calendar_discover'),{'limit':5,'page_token':'previous'},'discover')
        self.assertEqual([item['name'] for item in result['calendars']],['Personal','Team'])
        self.assertEqual(result['calendars'][1]['time_zone'],'Europe/London');self.assertEqual(result['next_page_token'],'next')
        self.assertIn('/users/me/calendarList?',transport.calls[0]['url'])
        self.assertEqual(parse_qs(urlparse(transport.calls[0]['url']).query)['pageToken'],['previous'])

    def test_calendar_discovery_respects_optional_primary_alias_ceiling(self):
        transport=FakeTransport(calendar_page())
        connector=CalendarConnector(CATALOG['extension_calendar_discover'],self.api(transport),calendars=['primary'])
        result=connector.invoke(grant('extension_calendar_discover'),{},'discover')
        self.assertEqual(len(result['calendars']),1);self.assertEqual(result['calendars'][0]['calendar_id'],'primary')

    def test_calendar_operations_select_different_calendars_without_reconfiguration(self):
        transport=FakeTransport({'id':'event_1'},{'id':'event_2'},{'items':[]})
        connector=CalendarConnector(CATALOG['extension_calendar_create'],self.api(transport),self.journal)
        for identifier in ['owner@example.com','team_calendar']:
            connector.invoke(grant('extension_calendar_create'),{'calendar_id':identifier,'event':self.event},identifier)
        reader=CalendarConnector(CATALOG['extension_calendar_list'],self.api(transport))
        reader.invoke(grant('extension_calendar_list'),{},'default_read')
        self.assertIn('owner%40example.com/events',transport.calls[0]['url'])
        self.assertIn('team_calendar/events',transport.calls[1]['url']);self.assertIn('/primary/events',transport.calls[2]['url'])

    def test_mail_profile_and_sender_follow_connected_account(self):
        transport=FakeTransport({'emailAddress':'connected@example.com'},{'emailAddress':'connected@example.com'},
                                {'id':'mail_1','threadId':'thread_1'},{'emailAddress':'connected@example.com'},{'id':'mail_2'})
        result=self.mail('profile',transport).invoke(grant('extension_mail_profile'),{},'profile')
        self.assertEqual(result['email_address'],'connected@example.com')
        connector=self.mail('send',transport)
        for number,recipient in enumerate(['first@example.com','second@example.org'],1):
            connector.invoke(grant('extension_mail_send'),{'to':recipient,'subject':'Request','body':'Please respond.'},'send_'+str(number))
        sent=[call for call in transport.calls if call['method']=='POST']
        self.assertEqual(len(sent),2)
        for call,recipient in zip(sent,['first@example.com','second@example.org']):
            message=message_from_bytes(base64.urlsafe_b64decode(call['body']['raw']),policy=default)
            self.assertEqual(message['From'],'connected@example.com');self.assertEqual(message['To'],recipient)

    def test_any_reviewed_reply_uses_actual_thread_sender(self):
        original={'id':'new_message','threadId':'new_thread','payload':{'headers':[
            {'name':'From','value':'different@example.org'},{'name':'Subject','value':'Any topic'},
            {'name':'Message-ID','value':'<message@example.org>'}]}}
        transport=FakeTransport(original,{'emailAddress':'connected@example.com'},{'id':'reply_1','threadId':'new_thread'})
        result=self.mail('reply',transport).invoke(grant('extension_mail_reply'),{'message_id':'new_message','body':'Thanks.'},'reply')
        self.assertEqual(result['thread_id'],'new_thread')
        message=message_from_bytes(base64.urlsafe_b64decode(transport.calls[-1]['body']['raw']),policy=default)
        self.assertEqual(message['To'],'different@example.org');self.assertEqual(message['In-Reply-To'],'<message@example.org>')

    def test_optional_recipient_ceiling_and_malformed_addresses_still_deny(self):
        transport=FakeTransport();connector=self.mail('send',transport,['allowed@example.com'])
        for recipient in ['other@example.com','evil@example.com\r\nBcc: hidden@example.com']:
            with self.assertRaises(RuntimeFailure):connector.invoke(grant('extension_mail_send'),{'to':recipient,'subject':'Hello','body':'Message'},'bad')
        self.assertFalse(transport.calls)

    def test_identity_access_failure_does_not_submit_mail(self):
        transport=FakeTransport(RuntimeFailure('GOOGLE_SCOPE_REQUIRED','Consent missing',403))
        with self.assertRaises(RuntimeFailure):self.mail('send',transport).invoke(grant('extension_mail_send'),
            {'to':'any@example.com','subject':'Hello','body':'Message'},'denied')
        self.assertEqual(len(transport.calls),1);self.assertEqual(transport.calls[0]['method'],'GET')

    def test_search_topics_filters_and_pagination_are_per_invocation(self):
        transport=FakeTransport({'web':{'results':[{'title':'One','url':'https://example.com/one'}]},'query':{'more_results_available':True}},
                                {'web':{'results':[{'title':'Two','url':'https://example.org/two'}]}})
        connector=SearchConnector(CATALOG['extension_web_search'],transport,lambda reference:'offline')
        first=connector.invoke(grant('extension_web_search'),{'query':'solar equipment','country':'in','language':'en','freshness':'pw','page':2},'first')
        second=connector.invoke(grant('extension_web_search'),{'query':'restaurant supplies','freshness':'2026-01-01to2026-02-01'},'second')
        query=parse_qs(urlparse(transport.calls[0]['url']).query)
        self.assertEqual(query['country'],['IN']);self.assertEqual(query['search_lang'],['en']);self.assertEqual(query['offset'],['2'])
        self.assertEqual(first['next_page'],3);self.assertIsNone(second['has_more'])
        self.assertNotEqual(first['results'][0]['url'],second['results'][0]['url'])
        with self.assertRaises(RuntimeFailure):connector.invoke(grant('extension_web_search'),{'query':'test','freshness':'2026-02-30to2026-03-01'},'bad')
        self.assertEqual(len(transport.calls),2)

    def test_calendar_planning_uses_discovered_names_without_server_ids(self):
        class Provider:
            contexts=[]
            def generate(self,objective,context):
                self.contexts.append(context)
                return connector_workflow('extension_calendar_list',{'calendar_id':'team_calendar'},'calendar_plan')
        provider=Provider();transport=FakeTransport(calendar_page())
        app=create_extension_app({'enabled_providers':['google_calendar','gmail']},self.root,transport=transport,
            token_supplier=lambda scopes,timeout:'offline',planner_provider=provider)
        result=app.state.workflow_service.handle({'request_id':'req_test','operation':'plan_workflow','idempotency_key':'calendar_planning',
            'payload':{'objective':'Read events in my Team calendar'}},app.state.extension_auth)
        self.assertEqual(result['status'],200,result)
        self.assertEqual(provider.contexts[0]['discovered_calendars']['calendars'][1]['calendar_id'],'team_calendar')
        self.assertEqual(provider.contexts[0]['mail_sender_mode'],'connected_account')

    def test_generalized_writes_still_need_action_approval_in_real_runtime(self):
        transport=FakeTransport({'id':'event_1'},{'emailAddress':'connected@example.com'},{'id':'mail_1'},
                                {'id':'event_2'},{'emailAddress':'connected@example.com'},{'id':'mail_2'})
        app=create_extension_app({'enabled_providers':['google_calendar','gmail']},self.root,transport=transport,
            token_supplier=lambda scopes,timeout:'offline')
        service,auth=app.state.workflow_service,app.state.extension_auth
        cases=[('extension_calendar_create',{'calendar_id':'calendar_one','event':self.event}),
               ('extension_mail_send',{'to':'first@example.com','subject':'First','body':'Hello'}),
               ('extension_calendar_create',{'calendar_id':'calendar_two','event':self.event}),
               ('extension_mail_send',{'to':'second@example.org','subject':'Second','body':'Hello'})]
        for index,(tool,inputs) in enumerate(cases):
            identity='general_case_'+str(index);workflow=connector_workflow(tool,inputs,identity)
            ref={'workflow_id':identity,'workflow_version':1}
            def handle(operation,payload,key):
                result=service.handle({'request_id':'req_test','operation':operation,'idempotency_key':key+str(index),'payload':payload},auth)
                self.assertEqual(result['status'],200,result);return result['data']
            handle('save_workflow_version',{**ref,'base_version':0,'workflow':workflow},'save_general')
            handle('validate_workflow',ref,'validate_general');handle('approve_workflow',{**ref,'action':'approve'},'approve_general')
            before=len(transport.calls)
            run=handle('execute_workflow',{**ref,'inputs':{}},'execute_general')['run']
            self.assertEqual(run['status'],'paused_for_approval');self.assertEqual(len(transport.calls),before)
            handle('decide_approval',{**ref,'approval_id':run['approvals'][0]['approval_id'],'decision':'approved'},'decide_general')
            self.assertEqual(service.runtime_runner.runtime.get_run(run['run_id'],auth)['status'],'completed')
        self.assertEqual(len(transport.calls),6)

    def test_reviewing_another_workflow_preserves_prior_exact_grants(self):
        app=create_extension_app({'enabled_providers':['google_calendar','gmail']},self.root,transport=FakeTransport(),
            token_supplier=lambda scopes,timeout:'offline')
        service,auth=app.state.workflow_service,app.state.extension_auth
        references=[]
        for index,(tool,inputs) in enumerate([
            ('extension_calendar_create',{'calendar_id':'first_calendar','event':self.event}),
            ('extension_mail_send',{'to':'first@example.com','subject':'First','body':'Hello'}),
            ('extension_calendar_create',{'calendar_id':'second_calendar','event':self.event}),
            ('extension_mail_send',{'to':'second@example.org','subject':'Second','body':'Hello'})]):
            workflow=connector_workflow(tool,inputs,'independent_'+str(index))
            ref={'workflow_id':workflow['workflow_id'],'workflow_version':1};references.append(ref)
            for operation,payload,key in [('save_workflow_version',{**ref,'base_version':0,'workflow':workflow},'save'),
                ('validate_workflow',ref,'validate'),('approve_workflow',{**ref,'action':'approve'},'approve')]:
                result=service.handle({'request_id':'req_test','operation':operation,'idempotency_key':key+'_independent_'+str(index),
                                      'payload':payload},auth)
                self.assertEqual(result['status'],200,result)
        viewer={**auth,'roles':['viewer'],'permissions':['runs.view']}
        self.assertEqual(service.registry.update_approval_evidence({},viewer)['status'],403)
        for index,ref in enumerate(references):
            result=service.handle({'request_id':'req_test','operation':'execute_workflow','idempotency_key':'independent_execute_'+str(index),
                                  'payload':{**ref,'inputs':{}}},auth)
            self.assertEqual(result['status'],200,result);self.assertEqual(result['data']['run']['status'],'paused_for_approval')

        self.assertEqual(service.registry.update_approval_evidence({},auth)['status'],200)
        with service.store.transaction() as db:
            document=service.store.get(db,'local-workspace',references[0]['workflow_id'],1)
        self.assertFalse(service.registry_adapter.review(document,auth)['ready'])
