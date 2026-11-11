from copy import deepcopy
import json
import pytest
from runtime.report_tables import context,normalize,validate
from runtime.crew import content_response_schema
from tests.test_workflow_query_integration import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query)
from tests.test_connected_action_plans import compile_run,stored,complete,decide,advance


def empty_instance():
 return dict(state='completed',verified_receipt=True,capability_id='tool.workflow_data_query',output=dict(query_id='verified_query',
  result=dict(matched_rows=0,total_result_rows=0,rows=[],limited=False),coverage=dict(complete_scan=True,aggregate_complete=True,has_more=False,returned_rows=0,total_result_rows=0)))


def test_empty_tables_render_explicit_report_status_without_group_metrics():
 out=dict(tabs=[dict(title='Status breakdown',headers=['Status','Count','Average'],rows=[])])
 normalize(out,dict(verified_empty=True,contracts=[{'type':'array'}]))
 assert out['tabs'][0]['headers']==['Report status','Details']
 assert out['tabs'][0]['rows'][0][0]=='No matching records'
 assert all(not isinstance(v,(int,float)) for v in out['tabs'][0]['rows'][0])
 before=deepcopy(out);normalize(out,dict(verified_empty=True,contracts=[{'type':'array'}]));assert out==before


@pytest.mark.parametrize('kind',['nonempty','incomplete','unverified','mixed'])
def test_nonempty_incomplete_or_unverified_sources_are_not_zero_filled(kind):
 q=empty_instance()
 if kind=='nonempty':q['output']['result'].update(matched_rows=1,rows=[{'x':1}])
 elif kind=='incomplete':q['output']['coverage']['aggregate_complete']=False
 elif kind=='unverified':q['verified_receipt']=False
 other=deepcopy(q)
 if kind=='mixed':other['output']['result']['matched_rows']=2
 plan={'actions':[dict(action_id='publish',capability_id='sheet',bindings=[dict(kind='output',action_id='report',path=['tabs'],target=['tabs'])])]}
 a=dict(action_id='report',depends_on=['q','other'] if kind=='mixed' else ['q'])
 c=context(plan,a,dict(q=q,other=other),dict(sheet=dict(kind='tool',input_schema=dict(properties={'tabs':{'type':'array'}}))))
 assert not c['verified_empty']
 out={'tabs':[{'title':'Data','headers':['x'],'rows':[]}]};before=deepcopy(out);normalize(out,c);assert out==before


def test_zero_query_can_publish_sheet_and_send_no_matches_report(automation,queries):
 from runtime.crew import CrewExecutor
 from runtime.model import BoundedLLM
 from tests.test_data_queries import plan
 f=automation;q=plan();q.update(fields=[],metrics=[dict(label='count',op='count',expression='')],group_by=['pg_lines_categoryID'],filters=[dict(field_id='pg_lines_price',op='gt',value=1000)])
 jobs,_,_,body=setup_query(f,queries,typed_query=q)
 captured=[]
 def factory(definition):
  def transport(messages,cap,timeout):
   raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip();inputs,_=json.JSONDecoder().raw_decode(raw)
   if set(definition['output_schema']['properties'])=={'query'}:return json.dumps({'query':q}),1,10
   captured.append(inputs);out=dict(source_references=inputs['source_references'],assumptions=[])
   if 'artifact_url' in inputs:out.update(subject='No matches report',body='No matching records. '+inputs['artifact_url'])
   else:out.update(title='No matches report',summary='No matching records.',tabs=[dict(title='Groups',headers=['Group','Count'],rows=[])])
   return json.dumps(out),1,10
  return BoundedLLM(definition,transport,lambda messages:100,0,0)
 f.runner.agents=CrewExecutor(f.adapter,factory)
 doc,w,rid=compile_run(f,body)
 assert f.runner.advance(rid,f.x.a)['status']=='running'
 assert jobs.tick();f.now+=2
 result=complete(f,w,rid);snapshot=stored(f,rid)
 assert result['status']=='completed',snapshot
 assert captured[0]['data']['report_table_context']['verified_empty']
 tabs=snapshot['outputs']['analysis']['tabs']
 assert tabs[0]['headers']==['Report status','Details'] and tabs[0]['rows'][0][0]=='No matching records'
 assert f.http.write_count==1 and len(f.http.sent)==1
 assert snapshot['action_instances']['send']['verified_receipt']
 assert not list(__import__('jsonschema').Draft202012Validator(doc['contracts']['tool.extension_sheets_create_report']['input_schema']['properties']['tabs']).iter_errors(tabs))


def test_nonempty_generated_table_errors_are_caught_before_tool_dispatch(automation,queries):
 from runtime.action_plans import params,validate_content
 f=automation;_,_,_,body=setup_query(f,queries);doc,w,rid=compile_run(f,body)
 with f.general.store.transaction(write=False) as db:run=f.runtime.load(db,rid,f.x.a)
 action=next(a for a in w['metadata']['connected_action_plan']['actions'] if a['action_id']=='analysis')
 action['depends_on']=['read'];run['action_instances']={'read':empty_instance()};run['action_instances']['read']['output']['result']['matched_rows']=1
 node=next(n for n in w['nodes'] if n['node_id']=='analysis');inputs=params(w,node,run)
 output=dict(source_references=['read'],assumptions=[],tabs=[dict(title='Result',headers=['Count'],rows=[])])
 with pytest.raises(Exception) as error:validate_content(w,node,output,inputs)
 assert error.value.code=='AGENT_OUTPUT_INVALID' and error.value.validation_field=='tabs'
 assert not f.http.sent and not f.http.write_count


def test_content_transport_uses_downstream_table_limits_and_keeps_canonical_schema():
 from workflow_api.action_plans import CONTENT_OUTPUT,CONTENT_INPUT
 from connector_extension.catalog import CATALOG
 contract=CATALOG['extension_sheets_create_report']['input_schema']['properties']['tabs']
 definition=dict(input_schema=CONTENT_INPUT,output_schema=deepcopy(CONTENT_OUTPUT))
 before=deepcopy(definition)
 inputs=dict(data={'report_table_context':{'contracts':[contract],'verified_empty':True}},instructions='',source_references=['query'])
 response=content_response_schema(definition,inputs)
 assert response['properties']['tabs']['items']['properties']['rows']['minItems']==1
 assert response['properties']['tabs']['items']['properties']['rows']['maxItems']==250
 assert definition==before
 assert 'uniqueItems' not in json.dumps(response)
