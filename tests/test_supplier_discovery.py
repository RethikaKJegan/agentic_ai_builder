"""Evidence-backed discovery and shortlist review through the native runtime."""
from copy import deepcopy
import hashlib
import json
import socket
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tests import test_integrated_procurement as native
from connector_extension.procurement.store import ProcurementError
from runtime.supplier_search import public_url,Text,SupplierSearchConnector,SEARCH,fetch_public_page
from runtime.service import RuntimeFailure
from workflow_api.procurement_observability import project_communication


class DiscoveryTests(unittest.TestCase):
    start=native.IntegratedTests.start
    call=native.IntegratedTests.call
    urlopen=native.IntegratedTests.urlopen
    approve=native.IntegratedTests.approve
    advance=native.IntegratedTests.advance
    def setUp(self):
        native.IntegratedTests.setUp(self)
        raw=deepcopy(native.PLAN);raw.pop('project_id');raw.update(supplier_mode='discover',search_region='wt-wt',vendors=None)
        raw['requirements']['columns'].update(delivery_location=None,delivery_deadline=None)
        self.sdk.responses.create=lambda **kw:SimpleNamespace(output_text=json.dumps(raw),status='completed')
        self.text='Example supplier offers pipes, valves, pumps and helmets. Contact sales@supplier.example for quotations.'
        self.page={'url':'https://supplier.example/products','text':self.text,'emails':['sales@supplier.example'],
                   'content_sha256':hashlib.sha256(self.text.encode()).hexdigest()}
        original=SupplierSearchConnector.execute
        def execute(connector,grant,inputs,effect_id,deadline):
            if connector.definition['tool_id']=='supplier_web_search':
                return {'results':[{'url':self.page['url'],'title':'Example supplier','snippet':'Products'}]}
            return deepcopy(self.page)
        p=patch.object(SupplierSearchConnector,'execute',execute);p.start();self.addCleanup(p.stop)
    def model_factory(self,definition):
        if definition['role']!='Supplier verification specialist':return native.IntegratedTests.model_factory(self,definition)
        from runtime.model import BoundedLLM
        def provider(messages,cap,timeout):
            return json.dumps({'candidates':[
                {'name':'Example Supplier','email':'sales@supplier.example','url':self.page['url'],
                 'evidence_quote':'offers pipes, valves, pumps and helmets','assessment':'Website offers these products; delivery availability needs a quote.'},
                {'name':'Unknown Contact','email':'invented@example.com','url':self.page['url'],
                 'evidence_quote':'Example supplier','assessment':'Contact not supported by the page.'},
                {'name':'Fabricated','email':'fake@example.com','url':self.page['url'],'evidence_quote':'Not on the page','assessment':'Unsupported'}]}),100,100
        return BoundedLLM(definition,provider,lambda messages:1000,0,0)
    def prepare(self):
        return native.IntegratedTests.prepare(self)
    def select(self,state,ids=None):
        chosen=ids if ids is not None else [c['candidate_id'] for c in state['candidates'] if c['email']]
        return self.procurement.review_suppliers(self.plan['project_id'],{'decision':'approved','candidate_ids':chosen,
            'expected_digest':state['shortlist_digest']},self.auth)
    def test_discovery_review_then_rfq_delivery_and_unified_trace(self):
        before=deepcopy(self.http.books);state=self.prepare()
        self.assertEqual(state['phase'],'SHORTLIST_REVIEW');self.assertEqual(self.http.sent,[]);self.assertEqual(self.http.write_count,0)
        self.assertEqual(len(state['candidates']),2)
        known=next(c for c in state['candidates'] if c['email'])
        self.assertEqual(set(known['categories']),{'Piping','Equipment','Safety'})
        missing=next(c for c in state['candidates'] if not c['email'])
        with self.assertRaises(ProcurementError):self.select(state,[missing['candidate_id']])
        state=self.select(state)
        self.assertEqual(state['record_counts']['vendor'],1);self.assertEqual(state['record_counts']['rfq'],3)
        for _ in range(30):
            if state['phase']=='RFQS_SENT':break
            self.assertNotEqual(state['phase'],'STOPPED',state['issues'])
            self.approve(state);state=self.advance()
        self.assertEqual(state['phase'],'RFQS_SENT');self.assertEqual(len(self.http.sent),3)
        self.assertEqual({m['To'] for m in self.http.sent},{'sales@supplier.example'})
        self.assertEqual(self.http.books['requirements_book'],before['requirements_book'])
        evidence=[r for r in state['records'] if r['record_type']=='evidence' and r['data']['provider']=='operator']
        self.assertTrue(evidence);self.assertTrue(all(e['data']['source_kind']=='OPERATOR_CONFIRMATION' for e in evidence))
        graph=project_communication(self.service,self.procurement,self.ref['workflow_id'],1,self.auth)
        self.assertGreater(len(graph['actions']),10)
        self.assertTrue(any(a['key'].startswith('research_') for a in graph['actions']))
        self.assertTrue(any(e['event_type']=='agent.spawned' for a in graph['actions'] for e in a['events']))
        self.start();self.advance();self.assertEqual(len(self.http.sent),3)
    def test_stale_and_unauthorized_shortlist_rejected(self):
        state=self.prepare()
        payload={'decision':'approved','candidate_ids':[],'expected_digest':'stale'}
        with self.assertRaises(ProcurementError):self.procurement.review_suppliers(self.plan['project_id'],payload,self.auth)
        auth=deepcopy(self.auth);auth['roles']=['builder'];auth['permissions']=[p for p in auth['permissions'] if p!='workflow.approve']
        with self.assertRaises(RuntimeFailure):self.procurement.review_suppliers(self.plan['project_id'],payload,auth)
        self.assertEqual(self.http.sent,[])
    def test_rejected_shortlist_blocks_all_outreach(self):
        state=self.prepare()
        result=self.procurement.review_suppliers(self.plan['project_id'],{'decision':'rejected','candidate_ids':[],
            'expected_digest':state['shortlist_digest']},self.auth)
        self.assertEqual(result['phase'],'STOPPED');self.assertEqual(self.http.write_count,0)
    def test_changed_requirements_after_review_fail_closed(self):
        state=self.prepare();self.http.books['requirements_book']['sheets'][0]['business_rows'][0][3]=999
        result=self.select(state)
        self.assertEqual(result['phase'],'STOPPED');self.assertEqual(self.http.sent,[])

    def test_failed_search_and_pages_do_not_stop_other_sections(self):
        execute=SupplierSearchConnector.execute
        searches=[];pages=[]
        def intermittent(connector,grant,inputs,effect_id,deadline):
            if connector.definition['tool_id']=='supplier_web_search':
                searches.append(inputs['query'])
                if 'pump' in inputs['query'].lower():
                    raise RuntimeFailure('SEARCH_UNAVAILABLE','Provider unavailable',503)
            else:
                pages.append(inputs['url'])
                if len(pages)==1:raise RuntimeFailure('PAGE_HTTP_403','Website rejected request',502)
            return execute(connector,grant,inputs,effect_id,deadline)
        with patch.object(SupplierSearchConnector,'execute',intermittent):state=self.prepare()
        self.assertEqual(state['phase'],'SHORTLIST_REVIEW',state['issues'])
        self.assertEqual(set(state['rejected_pages']),{'research_0_page_0','research_1','research_1_fallback'})
        self.assertTrue(any('helmets' in query.lower() for query in searches))
        self.assertTrue(any(c['email'] for c in state['candidates']))
        self.assertEqual(state['actions']['research_1']['state'],'failed')
        self.assertEqual(self.http.sent,[])
        self.assertEqual(self.http.write_count,0)

    def test_research_authorization_failure_stops_without_fallback(self):
        searches=[]
        def denied(connector,grant,inputs,effect_id,deadline):
            searches.append(inputs)
            raise RuntimeFailure('CONNECTOR_NOT_AUTHORIZED','Authorization revoked',403)
        with patch.object(SupplierSearchConnector,'execute',denied):state=self.prepare()
        self.assertEqual(state['phase'],'STOPPED')
        self.assertEqual(len(searches),1)
        self.assertEqual(state['rejected_pages'],[])
        self.assertEqual(self.http.sent,[])

    def test_explicit_automatic_mode_completes_without_action_approvals(self):
        self.env['BUILDER_PROCUREMENT_AUTOMATIC']='1';self.start()
        raw=deepcopy(native.PLAN);raw.pop('project_id');raw.update(supplier_mode='discover',search_region='wt-wt',vendors=None,action_mode='automatic')
        raw['requirements']['columns'].update(delivery_location=None,delivery_deadline=None)
        self.sdk.responses.create=lambda **kw:SimpleNamespace(output_text=json.dumps(raw),status='completed')
        state=self.prepare()
        for _ in range(5):
            if state['phase']=='RFQS_SENT':break
            state=self.advance()
        self.assertEqual(state['phase'],'RFQS_SENT',state['issues']);self.assertEqual(len(self.http.sent),3)
        self.assertTrue(all(not a.get('approvals') for a in state['actions'].values()))
        graph=project_communication(self.service,self.procurement,self.ref['workflow_id'],1,self.auth)
        self.assertEqual(graph['root_run']['status'],'completed')
        self.advance();self.assertEqual(len(self.http.sent),3)


class PageTests(unittest.TestCase):
    def test_network_failure_has_recoverable_page_error(self):
        connection=SimpleNamespace(request=lambda *a,**k:None,
            getresponse=lambda:(_ for _ in ()).throw(TimeoutError()),close=lambda:None)
        with patch('runtime.supplier_search.public_url',return_value=(
                __import__('urllib.parse',fromlist=['urlsplit']).urlsplit('https://supplier.example'),'8.8.8.8')),\
             patch('runtime.supplier_search.http.client.HTTPSConnection',return_value=connection):
            with self.assertRaises(RuntimeFailure) as failure:fetch_public_page('https://supplier.example',10)
        self.assertEqual(failure.exception.code,'PAGE_UNAVAILABLE')

    def test_large_html_and_public_redirect_are_read_with_footer_contacts(self):
        class Response:
            def __init__(self,status,body=b'',location=None):self.status,self.body,self.location=status,body,location
            def getheader(self,key,default=None):return self.location if key=='Location' else 'text/html' if key=='Content-Type' else default
            def read(self,size):return self.body[:size]
        responses=iter([Response(301,location='/products'),Response(200,
            ('<script>'+'x'*300000+'</script><p>Pumps and valves</p><a href="/contact">Contact</a><footer>sales@example.com</footer>').encode())])
        class Connection:
            def request(self,*args,**kwargs):pass
            def getresponse(self):return next(responses)
            def close(self):pass
        with patch('runtime.supplier_search.public_url',side_effect=lambda url:(__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(url),'8.8.8.8')),\
             patch('runtime.supplier_search.http.client.HTTPSConnection',return_value=Connection()):
            result=fetch_public_page('https://supplier.example/',15)
        self.assertEqual(result['url'],'https://supplier.example/products')
        self.assertEqual(result['emails'],['sales@example.com']);self.assertEqual(result['contact_urls'],['https://supplier.example/contact'])
        self.assertNotIn('x'*100,result['text'])
    def test_redirect_to_private_host_is_rechecked(self):
        class Response:
            status=302
            def getheader(self,key,default=None):return 'https://127.0.0.1/'
        connection=SimpleNamespace(request=lambda *a,**k:None,getresponse=lambda:Response(),close=lambda:None)
        def checked(url):
            if '127.0.0.1' in url:raise RuntimeFailure('PUBLIC_PAGE_REQUIRED','Private',400)
            return __import__('urllib.parse',fromlist=['urlsplit']).urlsplit(url),'8.8.8.8'
        with patch('runtime.supplier_search.public_url',side_effect=checked),patch('runtime.supplier_search.http.client.HTTPSConnection',return_value=connection) as http:
            with self.assertRaises(RuntimeFailure):fetch_public_page('https://supplier.example/',15)
        self.assertEqual(http.call_count,1)
    def test_search_uses_bounded_backend_fallback(self):
        calls=[]
        class Fake:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def text(self,*args,**kwargs):
                calls.append(kwargs['backend'])
                if len(calls)==1:raise RuntimeError('temporary provider failure')
                return [{'title':'Supplier','href':'https://supplier.example','body':'Products'}]
        SupplierSearchConnector.next_search=0
        with patch('ddgs.DDGS',return_value=Fake()),patch('runtime.supplier_search.time.sleep'):
            result=SupplierSearchConnector(SEARCH).execute(None,{'query':'pump suppliers','region':'in-en','max_results':3},'test',__import__('time').monotonic()+20)
        self.assertEqual(calls,['auto','bing']);self.assertEqual(len(result['results']),1)
    def test_private_and_mixed_dns_are_rejected(self):
        for addresses in [['127.0.0.1'],['8.8.8.8','10.0.0.1']]:
            with patch('socket.getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443)) for ip in addresses]):
                with self.assertRaises(RuntimeFailure):public_url('https://supplier.example/')
    def test_no_credentials_non_https_or_custom_ports(self):
        for url in ['http://example.com','https://user:pass@example.com','https://example.com:8443']:
            with self.assertRaises(RuntimeFailure):public_url(url)
    def test_html_scripts_are_not_evidence_and_mailto_is_preserved(self):
        parser=Text();parser.feed('<script>invented@example.com</script><p>Products</p><a href="mailto:sales@example.com">Contact</a>')
        self.assertNotIn('invented@example.com',' '.join(parser.parts));self.assertIn('sales@example.com',parser.parts)
    def test_ddgs_results_are_bounded_and_duplicate_urls_removed(self):
        fake=SimpleNamespace(__enter__=lambda s:s)
        class Fake:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def text(self,*args,**kwargs):return [{'title':'Supplier','href':'https://supplier.example','body':'Products'}]*4
        with patch('ddgs.DDGS',return_value=Fake()):
            result=SupplierSearchConnector(SEARCH).execute(None,{'query':'equipment suppliers','region':'wt-wt','max_results':3},'test',__import__('time').monotonic()+10)
        self.assertEqual(len(result['results']),1)
