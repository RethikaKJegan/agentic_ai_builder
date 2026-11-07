"""Complete evidence reads, exact aggregates, scoped joins and failure boundaries."""
from copy import deepcopy
from contextlib import contextmanager
from decimal import Decimal
from types import SimpleNamespace
import json
from pathlib import Path
import pytest
from tests.test_subway_coverage_audit import installed,AUTH
from workflow_api.business_ontology import BusinessOntology
from workflow_api.subway_queries import SubwayQueries,reference_key,key
from workflow_api.service import ApiFailure

ROOT=Path(__file__).resolve().parents[1];V=json.loads((ROOT/'ontology/subway/business-ontology-v4.json').read_text())
class Cursor:
 def __init__(self,rows):self.rows=deepcopy(rows)
 def batch_size(self,n):return self
 def max_time_ms(self,n):return self
 def sort(self,columns):
  assert columns
  for column,direction in reversed(columns):self.rows.sort(key=lambda r:(r.get(column) is not None,r.get(column)),reverse=direction<0)
  return self
 def __iter__(self):return iter(self.rows)
 def close(self):pass
class Collection:
 def __init__(self,rows):self.rows=rows
 def find(self,query,projection):assert query=={};return Cursor(self.rows)
class Database:
 def __init__(self,rows):self.rows=rows
 def __getitem__(self,name):return Collection(self.rows.get(name,[]))
class MemoryAdapter:
 def __init__(self,rows):self.rows=rows
 @contextmanager
 def connection(self,config):yield {name:Database(rows) for name,rows in self.rows.items()}

@pytest.fixture
def engine(installed):
 store,packages,sources,service=installed
 with store.transaction() as db:
  db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',('client-subway','subway-client',V['version_id'],json.dumps(V)))
  for role in ['central','finance']:
   cid='dbconn_subway_'+role;row=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=1',(cid,)).fetchone();md=json.loads(row[0])
   for d in md['datasets']:
    for f in d['fields']:f['field_id']=role+'_'+d['name']+'_'+f['name']
   db.execute('UPDATE data_source_snapshots SET document=? WHERE connection_id=? AND revision=1',(json.dumps(md),cid))
 rows={'subway_finance':{'purchaseorders':[{'_id':i,'poNumber':'PO'+str(i),'status':'APPROVED' if i%2 else 'PENDING','totalAmount':Decimal(str(i))+Decimal('.01'),'company':1 if i%3 else 999} for i in range(1,101)],'companies':[{'_id':1,'name':'Company One'}]},'subway_central':{'apps':[{'_id':1,'properties':'5'},{'_id':2,'properties':None},{'_id':3,'properties':999}],'appproperties':[{'_id':5,'archive':False}]}}
 sources.manager.adapter=MemoryAdapter(rows)
 app=SimpleNamespace(state=SimpleNamespace(workflow_service=service,business_sources=sources,business_ontology=BusinessOntology(store)))
 q=SubwayQueries(app,AUTH);return q,rows

def plan(q,label='finance.purchaseorders',**extra):
 c=q.catalog(AUTH);did=next(did for did,d in c['datasets'].items() if d['label']==label)
 return dict(base_dataset_id=did,joins=[],fields=[],filters=[],group_by=[],metrics=[dict(label='records',op='count',field_id='')],order_by=[],offset=0,limit=10,**extra) if not extra else {**plan(q,label),**extra}
def field(q,label,name):return next(f['field_id'] for d in q.catalog(AUTH)['datasets'].values() if d['label']==label for f in d['fields'] if f['name']==name)

def test_aggregate_counts_all_rows_not_initial_sample(engine):
 q,_=engine;r=q.execute(AUTH,plan(q));assert r['rows']==[{'records':100}]
 assert r['coverage']['complete_scan'] and r['coverage']['matched_records']==100 and r['sources'][0]['scanned_records']==100


def test_filtered_record_beyond_first_25_is_retrieved(engine):
 q,_=engine;fid=field(q,'finance.purchaseorders','poNumber')
 r=q.execute(AUTH,plan(q,fields=[fid],metrics=[],filters=[dict(field_id=fid,op='eq',value='PO99')]))
 assert r['rows']==[{fid:'PO99'}] and r['coverage']['matched_records']==1 and r['sources'][0]['scanned_records']==100


def test_filtered_grouped_sum_and_average_are_complete_and_exact(engine):
 q,_=engine;amount=field(q,'finance.purchaseorders','totalAmount');status=field(q,'finance.purchaseorders','status')
 r=q.execute(AUTH,plan(q,filters=[dict(field_id=status,op='eq',value='APPROVED')],group_by=[status],metrics=[dict(label='amount',op='sum',field_id=amount),dict(label='average',op='avg',field_id=amount),dict(label='records',op='count',field_id='')]))
 assert r['rows']==[{status:'APPROVED','amount':'2500.50','average':'50.01','records':50}]
 assert r['coverage']['aggregate_complete'] and r['coverage']['matched_records']==50


def test_detail_limit_is_pagination_not_evidence_sample(engine):
 q,_=engine;fid=field(q,'finance.purchaseorders','poNumber');r=q.execute(AUTH,plan(q,fields=[fid],metrics=[],offset=95,limit=2))
 assert r['rows']==[{fid:'PO96'},{fid:'PO97'}] and r['coverage']['matched_records']==100 and r['coverage']['has_more']


def test_left_join_preserves_orphans_and_reports_exact_coverage(engine):
 q,_=engine;c=q.catalog(AUTH);base=plan(q)['base_dataset_id'];edge=next(r for r in c['relationships'].values() if r['source_dataset_id']==base and c['datasets'][r['target_dataset_id']]['label']=='finance.companies')
 name=field(q,'finance.companies','name');r=q.execute(AUTH,plan(q,joins=[edge['relationship_id']],group_by=[name]))
 assert sum(row['records'] for row in r['rows'])==100
 assert r['join_checks'][0]['matched_rows']==67 and r['join_checks'][0]['unmatched_reference_rows']==33
 assert next(row for row in r['rows'] if row[name] is None)['records']==33


def test_schema_backed_numeric_reference_resolves_real_string_id(engine):
 q,_=engine;c=q.catalog(AUTH);query=plan(q,'central.apps');edge=next(r for r in c['relationships'].values() if r['source_dataset_id']==query['base_dataset_id'] and c['datasets'][r['target_dataset_id']]['label']=='central.appproperties')
 assert edge['reference_conversion']=='schema_integer_reference'
 r=q.execute(AUTH,{**query,'joins':[edge['relationship_id']]})
 check=r['join_checks'][0];assert check['matched_rows']==1 and check['normalized_reference_rows']==1 and check['missing_reference_rows']==1 and check['unmatched_reference_rows']==1
 assert reference_key('5','native')!=key(5) and reference_key('5','schema_integer_reference')==key(5)
 assert reference_key('5a','schema_integer_reference')!=key(5)


@pytest.mark.parametrize('change',[{'base_dataset_id':'another-client'},{'fields':['foreign-field'],'metrics':[]},{'joins':['foreign-link']}])
def test_unowned_sources_fields_and_links_are_rejected(engine,change):
 q,_=engine
 with pytest.raises(ApiFailure):q.execute(AUTH,{**plan(q),**change})


def test_other_tenant_denied_before_source_read(engine):
 q,_=engine;auth=deepcopy(AUTH);auth['subject']['workspace_id']='client-simpsons'
 with pytest.raises(ApiFailure):q.execute(auth,plan(q))


def test_operator_injection_and_non_numeric_sum_fail_closed(engine):
 q,rows=engine;fid=field(q,'finance.purchaseorders','totalAmount')
 with pytest.raises(ApiFailure):q.execute(AUTH,plan(q,filters=[dict(field_id=fid,op='eq',value={'$gt':0})]))
 rows['subway_finance']['purchaseorders'][-1]['totalAmount']='unknown'
 with pytest.raises(ApiFailure,match='nonnumeric'):q.execute(AUTH,plan(q,metrics=[dict(label='total',op='sum',field_id=fid)]))


def test_duplicate_target_keys_cannot_multiply_totals(engine):
 q,rows=engine;rows['subway_finance']['companies'].append({'_id':1,'name':'Duplicate'})
 c=q.catalog(AUTH);edge=next(r for r in c['relationships'].values() if r['source_dataset_id']==plan(q)['base_dataset_id'] and c['datasets'][r['target_dataset_id']]['label']=='finance.companies')
 with pytest.raises(ApiFailure,match='unique'):q.execute(AUTH,plan(q,joins=[edge['relationship_id']]))


def test_query_source_change_blocks_result(engine,monkeypatch):
 q,_=engine;original=q.catalog;calls=[]
 def catalog(auth,*args):
  c=original(auth,*args);calls.append(1)
  if len(calls)>1:c['stamps']['dbconn_subway_central']['generation']+=1
  return c
 query=plan(q);monkeypatch.setattr(q,'catalog',catalog)
 with pytest.raises(ApiFailure,match='changed'):q.execute(AUTH,query)


def test_query_planning_retains_typed_schema_through_runtime(engine):
 from runtime.action_plans import params,verify
 from runtime.crew import capability_context
 from runtime.model_protocol import closed_payload
 from workflow_api.subway_queries import planning_contract,PLAN_OUTPUT
 from tests.test_connected_action_plans import action,bind
 q,_=engine;c=planning_contract();query=plan(q)
 a=action('plan','subway.plan_query',[bind('context','task_id','task'),bind('context','context','catalog')]);a['budget'].update(max_llm_calls=1,max_tool_calls=0)
 node=dict(node_id='plan',kind='agent',agent_id='planner')
 workflow=dict(agents=[dict(agent_id='planner',input_schema=c['input_schema'])],metadata=dict(connected_action_plan=dict(actions=[a],constraints={}),action_binding_context=dict(validated_context=dict(task='plan',catalog=dict(subway_query_catalog=q.catalog(AUTH,'Count purchase orders'))))))
 payload=params(workflow,node,{'action_instances':{}})
 assert capability_context(payload) is None and 'subway_query_catalog' in payload['context']
 output={'query':query};verify(workflow,node,output,payload);assert output=={'query':query}
 assert closed_payload(PLAN_OUTPUT)


def test_earliest_and_latest_dates_use_all_source_records(engine):
 from datetime import datetime
 q,rows=engine;dates=[datetime(2025,1,1),datetime(2026,10,30)]
 for i,r in enumerate(rows['subway_finance']['purchaseorders']):r['poDate']=dates[i%2]
 f=field(q,'finance.purchaseorders','poDate')
 r=q.execute(AUTH,plan(q,metrics=[dict(label='earliest',op='min',field_id=f),dict(label='latest',op='max',field_id=f)]))
 assert r['rows']==[{'earliest':dates[0].isoformat(),'latest':dates[1].isoformat()}]


def test_empty_aggregates_and_immutable_execution_receipts(engine):
 q,_=engine;f=field(q,'finance.purchaseorders','_id');amount=field(q,'finance.purchaseorders','totalAmount')
 query=plan(q,filters=[dict(field_id=f,op='eq',value=999999)],metrics=[dict(label='count',op='count',field_id=''),dict(label='total',op='sum',field_id=amount)])
 first=q.execute(AUTH,query);second=q.execute(AUTH,query)
 assert first['rows']==[{'count':0,'total':None}]
 assert first['query_id']!=second['query_id']
 with q.store.transaction(write=False) as db:
  assert db.execute('SELECT count(*) FROM subway_query_receipts').fetchone()[0]==2


def test_mixed_currency_total_cannot_be_reported_as_one_amount(engine):
 q,rows=engine
 for i,r in enumerate(rows['subway_finance']['purchaseorders']):r['currency']=1 if i%2 else 3
 amount=field(q,'finance.purchaseorders','totalAmount');currency=field(q,'finance.purchaseorders','currency')
 with pytest.raises(ApiFailure,match='currency'):q.execute(AUTH,plan(q,metrics=[dict(label='amount',op='sum',field_id=amount)]))
 r=q.execute(AUTH,plan(q,metrics=[dict(label='amount',op='sum',field_id=amount)],group_by=[currency]))
 assert len(r['rows'])==2 and r['coverage']['matched_records']==100


def test_common_po_wording_selects_actual_purchase_order_source(engine):
 q,_=engine;catalog=q.catalog(AUTH,'What is the total value of all POs?')
 assert catalog['sources'][0]['label']=='finance.purchaseorders'
