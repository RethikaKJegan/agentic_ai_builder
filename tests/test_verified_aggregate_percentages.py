from copy import deepcopy
from types import SimpleNamespace
import pytest
from runtime.aggregate_math import percentages
from tests.test_workflow_query_integration import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query)
from tests.test_connected_action_plans import compile_run,stored
from tests.test_data_queries import plan

SUBJECT={'workspace_id':'one','subject_id':'alice'}

def evidence(count,filtered=False,qid=None):
 q=plan();q.update(metrics=[dict(label='count',op='count',expression='')],filters=[dict(field_id='pg_lines_price',op='gte',value=0)] if filtered else [])
 return dict(state='completed',capability_id='tool.workflow_data_query',verified_receipt=True,
  output=dict(query_id=qid or ('subset' if filtered else 'total'),metadata_revision='revision',scope=dict(workspace_id='one',owner_id='alice'),
   coverage=dict(complete_scan=True,aggregate_complete=True,has_more=False,returned_rows=1,total_result_rows=1),
   result=dict(executed_plan=q,rows=[{'count':count}],matched_rows=count,total_result_rows=1,limited=False)))


def test_exact_reported_counts_yield_percentage_and_provenance():
 n,d=evidence(1588,True),evidence(5810);before=deepcopy([n,d]);out=percentages([n,d],SUBJECT)
 assert len(out)==1 and out[0]['percentage']=='27.33'
 assert out[0]['numerator']=='1588' and out[0]['denominator']=='5810'
 assert out[0]['numerator_query_id']=='subset' and out[0]['denominator_query_id']=='total'
 assert before==[n,d]


@pytest.mark.parametrize('change',['scope','revision','dataset','incomplete','sample','group','join','metric','count_mismatch','unverified','not_subset','larger_subset'])
def test_incompatible_incomplete_and_unverified_counts_do_not_derive(change):
 n,d=evidence(1588,True),evidence(5810);o=n['output'];r=o['result'];p=r['executed_plan']
 if change=='scope':o['scope']['owner_id']='bob'
 elif change=='revision':o['metadata_revision']='other'
 elif change=='dataset':p['base_dataset_id']='different'
 elif change=='incomplete':o['coverage']['aggregate_complete']=False
 elif change=='sample':r['limited']=True
 elif change=='group':p['group_by']=['status']
 elif change=='join':p['joins']=[{'target_dataset_id':'other'}]
 elif change=='metric':p['metrics'][0]['expression']='price'
 elif change=='count_mismatch':r['rows'][0]['count']=1587
 elif change=='unverified':n['verified_receipt']=False
 elif change=='not_subset':d['output']['result']['executed_plan']['filters']=[dict(field_id='other',op='eq',value=1)]
 else:r.update(rows=[{'count':6000}],matched_rows=6000)
 assert percentages([n,d],SUBJECT)==[]


def test_zero_denominator_is_undefined_and_zero_numerator_is_zero_percent():
 assert percentages([evidence(0,True),evidence(0)],SUBJECT)[0]['percentage'] is None
 assert percentages([evidence(0,True),evidence(10)],SUBJECT)[0]['percentage']=='0.00'


def test_complete_filtered_denominator_and_large_integer_counts():
 n,d=evidence(1,True),evidence(3)
 assert percentages([n,d],SUBJECT)[0]['percentage']=='33.33'
 n['output']['result'].update(rows=[{'count':10**20}],matched_rows=10**20)
 d['output']['result'].update(rows=[{'count':10**21}],matched_rows=10**21)
 assert percentages([n,d],SUBJECT)[0]['percentage']=='10.00'


def test_report_and_spreadsheet_content_receive_deterministic_math(automation,queries):
 from runtime.action_plans import params
 f=automation;_,_,_,body=setup_query(f,queries);doc,w,rid=compile_run(f,body)
 with f.general.store.transaction(write=False) as db:run=f.runtime.load(db,rid,f.x.a)
 report=next(a for a in w['metadata']['connected_action_plan']['actions'] if a['action_id']=='analysis')
 report['depends_on']=['numerator','denominator'];report['bindings']=[dict(kind='output',action_id='numerator',path=[],target=['data'])]
 # Content runtime obtains trusted actual dependency outputs, not source row math.
 run.setdefault('action_instances',{}).update(numerator=evidence(1588,True),denominator=evidence(5810))
 node=next(n for n in w['nodes'] if n['node_id']=='analysis')
 result=params(w,node,run)
 assert result['data']['verified_aggregate_math'][0]['percentage']=='27.33'
 assert 'verified_aggregate_math' in result['instructions']
 assert not f.http.sent and f.http.write_count==0
