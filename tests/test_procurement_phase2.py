"""Focused native Phase 2 smoke test; all model and Google responses are offline."""
from copy import deepcopy
import base64
from datetime import datetime,timezone
import json
from types import SimpleNamespace
import unittest
from urllib.parse import urlparse
import test_integrated_procurement as native
from connector_extension.tests.test_procurement_slice import PLAN, CONFIG
from workflow_api.procurement_quotes import quote_issues


SETTINGS={'enabled':True,'calendar_id':'primary','reminder_minutes':60,
          'purchasing_limit':'100000','allow_single_offer':True}

class Phase2Providers(native.ProcurementProviders):
    def __init__(self):super().__init__();self.replies={};self.calendar=[]
    def request(self,method,url,headers,body=None,timeout=30):
        path=urlparse(url).path
        if '/calendar/v3/' in path and method=='POST':
            self.calendar.append(deepcopy(body));return {'id':body['id'],'status':'confirmed'}
        if '/threads/' in path and method=='GET':
            thread=path.rsplit('/',1)[-1]
            return {'id':thread,'messages':self.replies.get(thread,[])}
        return super().request(method,url,headers,body,timeout)

class Phase2Tests(unittest.TestCase):
    # Reuse setup helpers, without importing/rerunning the Phase 1 test suite.
    start=native.IntegratedTests.start
    call=native.IntegratedTests.call
    prepare=native.IntegratedTests.prepare
    advance=native.IntegratedTests.advance
    urlopen=native.IntegratedTests.urlopen

    def setUp(self):
        native.IntegratedTests.setUp(self)
        self.http=Phase2Providers();self.env['BUILDER_PROCUREMENT_AUTOMATIC']='1'
        config=deepcopy(CONFIG);config['enabled_providers'].append('google_calendar')
        (self.path/'config.json').write_text(json.dumps(config))
        raw=deepcopy(PLAN);raw.pop('project_id')
        raw.update(action_mode='automatic',supplier_mode='supplied',search_region='wt-wt',phase2=SETTINGS)
        self.sdk=SimpleNamespace(responses=SimpleNamespace(create=lambda **kw:SimpleNamespace(output_text=json.dumps(raw),status='completed')))
        self.quote_outputs={};self.start()

    def model_factory(self,definition):
        if definition.get('role')!='Quotation extraction specialist':return native.IntegratedTests.model_factory(self,definition)
        from runtime.model import BoundedLLM
        def provider(messages,cap,timeout):
            content=' '.join(m['content'] for m in messages)
            match=next(key for key in self.quote_outputs if key in content)
            return json.dumps(self.quote_outputs[match]),100,100
        return BoundedLLM(definition,provider,lambda messages:1000,0,0)

    def replies(self,state):
        records={r['record_id']:r for r in state['records']}
        for n,rfq in enumerate(r for r in state['records'] if r['record_type']=='rfq'):
            d=rfq['data'];marker='VENDOR_QUOTE_'+str(n)
            unit_price='9' if d['vendor_id']=='vendor_a' else '10'
            shipping='100' if d['vendor_id']=='vendor_a' else '0'
            lines=[{'item_id':i,'quantity':records[i]['data']['quantity'],'unit':records[i]['data']['unit'],
                    'unit_price':unit_price,'line_total':str(int(records[i]['data']['quantity'])*int(unit_price))} for i in d['scope_item_ids']]
            subtotal=sum(int(i['line_total']) for i in lines)
            output={'is_quotation':True,'items':lines,'financials':{'currency':'INR','subtotal':str(subtotal),
                'discount':'0','tax':'0','shipping':shipping,'other_charges':'0','total_delivered_cost':str(subtotal+int(shipping))},
                'delivery_date':'2099-12-01','valid_until':'2099-12-31','payment_terms':'30 days',
                'compliance_statement':'All items meet the requested specifications.'}
            text=marker+'\nRFQ '+rfq['record_id']+'\n'+json.dumps(output)
            output['evidence']=[text];self.quote_outputs[marker]=output
            thread=d['gmail_thread_ids'][0]
            message={'id':'reply_'+str(n),'threadId':thread,'internalDate':str(int(datetime.now(timezone.utc).timestamp()*1000)),
                     'payload':{'mimeType':'text/plain','headers':[{'name':'From','value':d['recipient']},
                          {'name':'Subject','value':'Re: RFQ '+rfq['record_id']},{'name':'Message-ID','value':'<reply'+str(n)+'@example.com>'}],
                          'body':{'data':base64.urlsafe_b64encode(text.encode()).decode()}}}
            # Incorrect sender in the correct thread must not be processed.
            spoof=deepcopy(message);spoof['id']='spoof_'+str(n);spoof['payload']['headers'][0]['value']='other@example.com'
            self.http.replies[thread]=[spoof,message]

    def test_native_quotes_to_po_and_restart_deduplication(self):
        state=self.prepare();self.assertEqual(state['phase'],'RFQS_SENT',state['issues'])
        self.replies(state);state=self.advance()
        self.assertEqual(state['phase'],'PO_RELEASED',state['issues'])
        self.assertEqual(state['record_counts']['quotation'],4)
        self.assertEqual(state['record_counts']['purchase_order'],3)
        piping=next(r for r in state['records'] if r['record_type']=='award' and len(r['data']['scope_item_ids'])==2)
        self.assertEqual(piping['data']['vendor_id'],'vendor_b') # Price 10 with no freight beats 9 plus freight.
        self.assertEqual(len(self.http.sent),10) # Four RFQs, three awards, three POs.
        self.assertEqual(len(self.http.calendar),4)
        self.assertTrue(all(a['state']=='completed' for a in state['actions'].values()))
        book=self.http.books['created_1'];tables={s['properties']['title']:s for s in book['sheets']}
        self.assertEqual(len(tables['Quotations']['business_rows']),4)
        self.assertEqual(len(tables['Orders']['business_rows']),3)
        self.assertTrue(all(r['data']['status']=='ORDERED' for r in state['records'] if r['record_type']=='boq_item'))
        self.start();state=self.advance()
        self.assertEqual(state['phase'],'PO_RELEASED');self.assertEqual(len(self.http.sent),10);self.assertEqual(len(self.http.calendar),4)
        # Existing publication authority is specific to the stored amount.
        altered=deepcopy(piping);altered['data']['total']['amount']='1'
        approval=next(r for r in state['records'] if r['record_id']==piping['data']['approval_id'])
        self.assertFalse(self.procurement.purchase_authority(approval,altered,'award_order'))
        self.assertFalse(self.procurement.check_budget('local-workspace',self.plan['project_id'],piping,'1'))

    def test_missing_or_unsupported_charges_are_not_zero(self):
        self.quote_outputs={}
        state=self.prepare();self.replies(state)
        output=next(iter(self.quote_outputs.values()));items=[r for r in state['records'] if r['record_id'] in {i['item_id'] for i in output['items']}]
        output['financials']['shipping']=None
        self.assertIn('MISSING_OR_INVALID_shipping',quote_issues(output,output['evidence'][0],items,'INR'))
        output['financials']['shipping']='987654'
        self.assertIn('UNSUPPORTED_shipping',quote_issues(output,output['evidence'][0],items,'INR'))

if __name__=='__main__':unittest.main()
