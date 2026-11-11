"""Exact metadata association and persisted runtime usage, without live providers."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from workflow_api.workflow_knowledge import capture,completed_usage
from runtime.action_plans import completed


def fixture():
    mappings=[dict(id='mapping:case',concept_id='concept:case',source_role='operations',collection='cases',field_path='description'),
              dict(id='mapping:value',concept_id='concept:value',source_role='operations',collection='cases',field_path='value')]
    scope=dict(workspace_id='tenant',owner_id='owner')
    catalog=dict(context_hash='metadata',datasets=[dict(dataset_id='cases',fields=[dict(field_id='f_description'),dict(field_id='f_value')])],relationships=[])
    pin=dict(version_id='ontology_v1',scope=scope,mappings=[{**m,'field_id':f,'dataset_id':'cases'} for m,f in zip(mappings,['f_description','f_value'])])
    query=dict(fields=['f_description'],group_by=[],filters=[],metrics=[],joins=[])
    action=dict(action_id='read',capability_id='tool.workflow_data_query',depends_on=[],evidence_references=[],required_approvals=[])
    context=dict(validated_context=dict(data_query_catalog=catalog,ontology_usage=pin))
    workflow=dict(metadata=dict(connected_action_plan=dict(plan_id='p',actions=[action]),action_binding_context=context,connected_contracts={action['capability_id']:{}}))
    run=dict(workspace_id='tenant',subject_id='owner',action_instances={'read':dict(resolved_inputs=dict(query=query))})
    output=dict(query_id='query_saved',metadata_revision='metadata',scope=scope,result=dict(rows=[],matched_rows=0))
    return mappings,workflow,action,run,output


def test_completed_query_persists_exact_usage_even_with_zero_rows():
    _,w,a,r,out=fixture();completed(w,dict(node_id='read',kind='tool'),r,out)
    restored=json.loads(json.dumps(r))
    assert restored['action_instances']['read']['ontology_usage']==[dict(version_id='ontology_v1',concept_id='concept:case',mapping_id='mapping:case',reason='Verified query used this mapped source field.',field_id='f_description',query_id='query_saved')]
    assert restored['action_instances']['read']['output']==out


@pytest.mark.parametrize('kind',['filter','group','metric','join'])
def test_query_operands_establish_only_exact_mapped_fields(kind):
    _,w,a,r,out=fixture();query=r['action_instances']['read']['resolved_inputs']['query'];query['fields']=[]
    if kind=='filter':query['filters']=[dict(field_id='f_value')]
    if kind=='group':query['group_by']=['f_value']
    if kind=='metric':query['metrics']=[dict(expression='f_value * 2')]
    if kind=='join':
        query['joins']=[dict(relationship_id='edge')]
        w['metadata']['action_binding_context']['validated_context']['data_query_catalog']['relationships']=[dict(relationship_id='edge',field_pairs=[dict(source_field_id='f_value',target_field_id='unknown')])]
    completed(w,dict(node_id='read',kind='tool'),r,out)
    assert [u['concept_id'] for u in r['action_instances']['read']['ontology_usage']]==['concept:value']


@pytest.mark.parametrize('change',['foreign_scope','foreign_receipt','stale_metadata','failed','synthetic','unverified','missing_pin'])
def test_ineligible_evidence_never_establishes_usage(change):
    _,w,a,r,out=fixture();completed(w,dict(node_id='read',kind='tool'),r,out);item=r['action_instances']['read']
    if change=='foreign_scope':r['subject_id']='other'
    if change=='foreign_receipt':item['output']['scope']={'workspace_id':'other','owner_id':'owner'}
    if change=='stale_metadata':item['output']['metadata_revision']='new'
    if change=='failed':item['state']='failed'
    if change=='synthetic':item['provenance_type']='SYNTHETIC'
    if change=='unverified':item['verified_receipt']=False
    if change=='missing_pin':w['metadata']['action_binding_context']['validated_context'].pop('ontology_usage')
    assert completed_usage(w,a,r)==[]


def test_report_consumes_recorded_usage_but_delivery_does_not():
    _,w,a,r,out=fixture();completed(w,dict(node_id='read',kind='tool'),r,out)
    report=dict(action_id='report',capability_id='content.prepare',depends_on=['read'])
    r['action_instances']['report']=dict(state='completed',output={},provenance_type='INFERRED',input_provenance=[dict(binding_kind='output',source_reference=dict(action_id='read'))])
    usage=completed_usage(w,report,r);assert usage[0]['upstream_action_id']=='read'
    assert usage[0]['query_id']=='query_saved'
    delivery={**report,'capability_id':'tool.extension_mail_send'}
    assert completed_usage(w,delivery,r)==[]
    r['action_instances']['report']['input_provenance']=[]
    assert completed_usage(w,report,r)==[]


def test_capture_uses_owned_version_source_connection_and_exact_path():
    mappings,w,_,_,_=fixture();seen=[]
    snapshot=dict(workspace=dict(sources={'operations':'bound_source'}),knowledge=dict(source_mappings=mappings))
    ontology=SimpleNamespace(version=lambda auth,version:(seen.append((auth,version)) or deepcopy(snapshot)))
    datasets={'cases':dict(name='cases',connection=dict(connection_id='bound_source')),
              'other':dict(name='cases',connection=dict(connection_id='other_source'))}
    fields={'f_description':dict(name='description',dataset_id='cases'),'f_value':dict(name='value',dataset_id='other')}
    service=SimpleNamespace(ontology=ontology)
    composition=SimpleNamespace(preparation=SimpleNamespace(service=service),service=SimpleNamespace(workflow_queries=SimpleNamespace(queries=SimpleNamespace(context=lambda auth:({},datasets,fields,{})))))
    auth=dict(subject=dict(workspace_id='tenant',subject_id='owner'))
    pin=capture(composition,auth,w['metadata']['action_binding_context'],'ontology_v1')
    assert seen==[(auth,'ontology_v1')]
    assert pin['mappings'][0]['field_id']=='f_description'
    assert 'field_id' not in pin['mappings'][1]
    fields['duplicate']=dict(name='description',dataset_id='cases')
    w['metadata']['action_binding_context']['validated_context']['data_query_catalog']['datasets'][0]['fields'].append(dict(field_id='duplicate'))
    assert 'field_id' not in capture(composition,auth,w['metadata']['action_binding_context'],'ontology_v1')['mappings'][0]


def test_explicit_imported_collection_mapping_is_generic_and_requires_bound_source():
    from workflow_api.workflow_knowledge import source_mappings
    snapshot=dict(version_id='generic_v1',workspace=dict(sources={'research':'source_owned'}),concepts=[dict(id='lab:batch',properties=[dict(name='result.value')],dump_mapping=dict(role='research',connection_id='source_owned',collection='batches'))])
    mappings=source_mappings(snapshot)
    assert len(mappings)==1 and mappings[0]['concept_id']=='lab:batch'
    assert mappings[0]['field_path']=='result.value'
    assert source_mappings(deepcopy(snapshot))==mappings
    snapshot['concepts'][0]['dump_mapping']['connection_id']='foreign_source'
    assert source_mappings(snapshot)==[]
