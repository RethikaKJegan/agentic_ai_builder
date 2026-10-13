"""Offline native Phase 2-to-3 lifecycle with bounded master/specialists."""
from copy import deepcopy
import base64
from datetime import datetime,timezone
import json
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlparse
import test_procurement_phase2 as phase2

POLICY={'enabled':True,'buyer_email':'receiver@example.com','manager_email':'manager@example.com',
        'acceptance_hours':24,'reminder_hours':24,'allow_delivery_reschedule':False}

class Providers(phase2.Phase2Providers):
    def __init__(self):super().__init__();self.calendar_updates=[]
    def request(self,method,url,headers,body=None,timeout=30):
        path=urlparse(url).path
        if '/calendar/v3/' in path and method=='PATCH':
            self.calendar_updates.append(deepcopy(body));return {'id':path.rsplit('/',1)[-1],'status':'confirmed'}
        if '/messages/' in path and method=='GET':
            mid=path.rsplit('/',1)[-1]
            return next(m for messages in self.replies.values() for m in messages if m['id']==mid)
        out=super().request(method,url,headers,body,timeout)
        if path.endswith('/messages/send') and body.get('threadId'):out['threadId']=body['threadId']
        return out

class Phase3Tests(unittest.TestCase):
    start=phase2.Phase2Tests.start
    call=phase2.Phase2Tests.call
    prepare=phase2.Phase2Tests.prepare
    advance=phase2.Phase2Tests.advance
    urlopen=phase2.Phase2Tests.urlopen
    replies=phase2.Phase2Tests.replies
    def setUp(self):
        phase2.Phase2Tests.setUp(self);self.http=Providers();self.ful_outputs={};self.message_number=0;self.start()
    def model_factory(self,definition):
        if not definition.get('role','').startswith('Fulfilment'):return phase2.Phase2Tests.model_factory(self,definition)
        from runtime.model import BoundedLLM
        def provider(messages,cap,timeout):
            if definition['role']=='Fulfilment master':
                content=next(m['content'] for m in messages if 'Return only a JSON object.\n' in m['content'])
                ctx,_=json.JSONDecoder().raw_decode(content.split('Return only a JSON object.\n',1)[1].lstrip())
                if not ctx['results']:
                    output={'action':'delegate','reason':'Review update.','continuation':{},'tasks':[
                        {'agent_id':a['agent_id'],'inputs':ctx['request'],'reason':a['goal']} for a in ctx['available_agents']]}
                else:output={'action':'finish','reason':'Both reviews returned.','output':next(r['result'] for r in ctx['results'] if 'event_kind' in r['result'])}
            elif definition['role']=='Fulfilment review specialist':output={'summary':'Reviewed supplied evidence.'}
            else:
                content=' '.join(m['content'] for m in messages);marker=next(k for k in self.ful_outputs if k in content);output=self.ful_outputs[marker]
            return json.dumps(output),100,100
        return BoundedLLM(definition,provider,lambda messages:1000,0,0)
    def packet(self,po,kind,role='SUPPLIER'):
        self.message_number+=1;marker='FUL_UPDATE_'+str(self.message_number)+'_END'
        items=[] if kind=='ACCEPTED' else [{'item_id':i['item_id'],'quantity':i['ordered_quantity'],'unit':i['unit']} for i in po['items']]
        output={'event_kind':kind,'items':items,'quantity_mode':'cumulative','tracking_reference':'TRACK-'+po['po_id'] if kind=='DISPATCHED' else None,
            'expected_delivery_date':None,'receipt_confirmed':role=='BUYER','acceptance_confirmed':role=='BUYER',
            'resolution_confirmed':role=='BUYER','note':kind+' explicitly reported.'}
        text=marker+'\n'+po['po_number']+'\n'+json.dumps(output);output['evidence']=[text];self.ful_outputs[marker]=output
        job=self.procurement.job('local-workspace',self.plan['project_id'])
        vendor=self.procurement.store.get('local-workspace',self.plan['project_id'],po['vendor_id'])['data']['email']
        thread=job['buyer_threads'][po['po_id']][0] if role=='BUYER' else po['gmail_thread_ids'][0]
        sender=POLICY['buyer_email'] if role=='BUYER' else vendor
        message={'id':'ful_reply_'+str(self.message_number),'threadId':thread,'internalDate':str(int(datetime.now(timezone.utc).timestamp()*1000)),
            'payload':{'mimeType':'text/plain','headers':[{'name':'From','value':sender},{'name':'Subject','value':'Re: PO '+po['po_number']},
                {'name':'Message-ID','value':'<ful'+str(self.message_number)+'@example.com>'}],
                'body':{'data':base64.urlsafe_b64encode(text.encode()).decode()}}}
        self.http.replies.setdefault(thread,[]).append(message)
        spoof=deepcopy(message);spoof['id']='spoof_'+message['id'];spoof['payload']['headers'][0]['value']='stranger@example.com'
        self.http.replies[thread].append(spoof)
    def cycle(self):
        self.poll_clock+=31
        with patch('workflow_api.procurement_fulfilment.time.time',return_value=self.poll_clock):return self.advance()
    def test_existing_pos_fulfilment_to_buyer_closure(self):
        state=self.prepare();self.replies(state);state=self.advance()
        self.assertEqual(state['phase'],'PO_RELEASED',state['issues']);before=len(self.http.sent)
        payload={'settings':POLICY,'expected_revision':0,'workflow_id':self.ref['workflow_id'],'workflow_version':1}
        response=self.client.post('/procurement/projects/'+self.plan['project_id']+'/fulfilment-activate',json={
            'request_id':'req_phase3','operation':'procurement_fulfilment_activate','idempotency_key':'phase3_activation_1','payload':payload})
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(len(self.http.sent),before)
        self.poll_clock=time.time();state=response.json()['data']
        invalid=deepcopy(payload);invalid['settings']['buyer_email']='b@example.com'
        with self.assertRaises(Exception):self.procurement.activate_fulfilment(self.plan['project_id'],invalid,self.auth)
        for kind in ('ACCEPTED','PACKED','DISPATCHED','DELIVERED'):
            for po in state['orders']:self.packet(po,kind)
            state=self.cycle();self.assertNotEqual(state['phase'],'STOPPED',state['issues'])
            self.assertTrue(all(po['status']==kind for po in state['orders']),state['orders'])
        self.assertEqual(state['phase'],'FULFILMENT');self.assertTrue(all(po['status']!='CLOSED' for po in state['orders']))
        # Polling the same messages with evolved PO snapshots must reuse exact
        # extraction/notification children instead of failing fingerprint checks.
        count=len(self.http.sent);self.start();state=self.cycle();self.assertEqual(len(self.http.sent),count)
        for po in state['orders']:self.packet(po,'BUYER_RECEIPT_CONFIRMED','BUYER')
        state=self.cycle();self.assertEqual(state['phase'],'COMPLETED',state['issues'])
        self.assertTrue(all(po['status']=='CLOSED' for po in state['orders']));self.assertEqual(len(state['activity']),15)
        self.assertTrue(all(r['data']['status']=='RESOLVED' for r in state['records'] if r['record_type']=='boq_item'))
        closures=[m for m in self.http.sent if 'Order closed:' in m['Subject']]
        self.assertEqual(len(closures),3);self.assertEqual({m['To'] for m in closures},{POLICY['manager_email']})
        self.assertEqual(len(self.http.calendar),4);self.assertTrue(self.http.calendar_updates)
        activity=next(t for t in self.http.books['created_1']['sheets'] if t['properties']['title']=='Activity')
        self.assertEqual(len(activity['business_rows']),15)
        count=len(self.http.sent);updates=len(self.http.calendar_updates);self.start();state=self.cycle()
        self.assertEqual(state['phase'],'COMPLETED');self.assertEqual(len(self.http.sent),count);self.assertEqual(len(self.http.calendar_updates),updates)
