from copy import deepcopy
import pytest
from runtime.aggregate_math import percentages
from workflow_api.business_knowledge_model import digest
from runtime.subway_percentages import evidence
SUBJECT=dict(workspace_id='owned',subject_id='user')


def pair():
    queries={};instances=[]
    for aid,filtered,rows in [('subset',True,[{'currency':1,'count':2}]),('all',False,[{'currency':1,'count':4},{'currency':3,'count':2}])]:
        query=dict(base_dataset_id='source',group_by=['currency'],metrics=[dict(label='count',op='count',field_id='')],fields=[],joins=[],filters=[dict(field_id='value',op='gte',value=10)] if filtered else [],offset=0,limit=500,order_by=[])
        queries[aid]=query
        output=dict(query_id=aid,query_sha256=digest(query),ontology_version='pinned',scope=dict(workspace_id='owned',owner_id='user'),rows=rows,sources=[dict(dataset_id='source',metadata_revision=1,generation=1)],coverage=dict(complete_scan=True,aggregate_complete=True,filtered_on_entire_source=True,has_more=False,offset=0,returned_rows=len(rows),total_result_rows=len(rows),matched_records=sum(r['count'] for r in rows)))
        instances.append(dict(action_id=aid,state='completed',capability_id='tool.subway_query',verified_receipt=True,output=output))
    return instances,queries


def derive(instances,queries,basis='overall_population'):
    return percentages(instances,SUBJECT,subway_context=dict(interpretation=dict(percentage_basis=basis)),queries=queries)


def test_declared_global_and_group_denominators_and_zero_groups():
    instances,queries=pair();before=deepcopy((instances,queries))
    global_values=derive(instances,queries)
    assert [(v['numerator'],v['denominator'],v['percentage']) for v in global_values]==[('2','6','33.33'),('0','6','0.00')]
    grouped=derive(instances,queries,'within_group')
    assert [(v['numerator'],v['denominator'],v['percentage']) for v in grouped]==[('2','4','50.00'),('0','2','0.00')]
    assert global_values[0]['numerator_query_id']=='subset' and global_values[0]['denominator_query_id']=='all'
    assert (instances,queries)==before and derive(instances,queries,'none')==[]


@pytest.mark.parametrize('bad',['unverified','scope','hash','revision','generation','incomplete','limited','offset','metric','count','duplicate','join','filters','missing_group','larger_count'])
def test_incompatible_evidence_never_produces_percentages(bad):
    instances,queries=pair();n=instances[0];o=n['output'];c=o['coverage']
    if bad=='unverified':n['verified_receipt']=False
    elif bad=='scope':o['scope']['owner_id']='other'
    elif bad=='hash':o['query_sha256']='wrong'
    elif bad=='revision':o['sources'][0]['metadata_revision']=2
    elif bad=='generation':o['sources'][0]['generation']=2
    elif bad=='incomplete':c['complete_scan']=False
    elif bad=='limited':c['has_more']=True
    elif bad=='offset':c['offset']=1
    elif bad=='metric':queries['subset']['metrics'][0]['field_id']='value';o['query_sha256']=digest(queries['subset'])
    elif bad=='count':c['matched_records']=3
    elif bad=='duplicate':o['rows']*=2;c.update(returned_rows=2,total_result_rows=2,matched_records=4)
    elif bad=='join':queries['subset']['joins']=['edge'];o['query_sha256']=digest(queries['subset'])
    elif bad=='filters':queries['subset']['filters']=[];o['query_sha256']=digest(queries['subset'])
    elif bad=='missing_group':o['rows'][0]['currency']=99
    else:o['rows'][0]['count']=5;c['matched_records']=5
    assert derive(instances,queries)==[]


def test_undefined_zero_denominator_is_preserved():
    instances,queries=pair()
    for instance in instances:
        for row in instance['output']['rows']:row['count']=0
        instance['output']['coverage']['matched_records']=0
    assert all(v['percentage'] is None and v['status']=='undefined_zero_denominator' for v in derive(instances,queries))
