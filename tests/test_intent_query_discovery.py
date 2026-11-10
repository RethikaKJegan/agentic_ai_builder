"""Existing ontology retrieval feeds bounded query metadata, never business rows."""
from copy import deepcopy
import json
import pytest
from tests.test_kg_retrieval import coordinator, manager, authority, dataset
from workflow_api.service import ApiFailure

EXACT = 'Find complaints with operating hours between 0 and 100, inclusive. Generate a workflow to query all matching records, calculate the count, minimum, maximum and average operating hours, and prepare an evidence-backed report. Show result completeness and any limitations. Do not send emails, create spreadsheets or perform external writes.'

@pytest.mark.parametrize('entity,measure,goal',[
    ('complaints','operating_hours',EXACT),
    ('purchase_orders','total_amount','Analyse purchase orders with total amount between 0 and 100 and report count and average.'),
])
def test_oversized_catalogue_filters_before_bound_and_saves_plan(coordinator,entity,measure,goal):
    c=coordinator;q=c.queries;q.retrieval=c.retrieval
    with c.store.transaction() as db:
        raw=db.execute("SELECT document FROM data_source_snapshots WHERE connection_id='pg' AND revision=1").fetchone()[0]
        snap=json.loads(raw)
        snap['datasets'] += [dataset('pg','unrelated'+str(i),[(f'attribute{j}',['integer']) for j in range(12)],'northwind') for i in range(95)]
        snap['datasets'].append(dataset('pg',entity,[(measure,['integer']),('id',['integer'])],'northwind'))
        db.execute("UPDATE data_source_snapshots SET document=? WHERE connection_id='pg' AND revision=1",(json.dumps(snap),))
    c.manager.relationships.request(authority());c.manager.relationships.tick()
    full,_=q._catalogue(authority(),q.context(authority()),enforce_limit=False)
    assert len(json.dumps(full).encode())>120000
    with pytest.raises(ApiFailure) as error:q.catalogue(authority())
    assert error.value.code=='DATA_QUERY_LIMIT'
    catalog=q.catalogue(authority(),goal)
    assert 'pg_'+entity in {d['dataset_id'] for d in catalog['datasets']}
    assert all(not d['name'].startswith('unrelated') for d in catalog['datasets'])
    assert len(json.dumps(catalog).encode())<120000
    assert catalog['discovery']['revision'] and catalog['context_hash']
    p=dict(base_dataset_id='pg_'+entity,joins=[],fields=[],filters=[dict(field_id=f'pg_{entity}_{measure}',op='gte',value=0),dict(field_id=f'pg_{entity}_{measure}',op='lte',value=100)],group_by=[],metrics=[dict(label=op,op=op,expression='' if op=='count' else f'pg_{entity}_{measure}') for op in ('count','min','max','avg')],order_by=[],limit=100,explanation='Inclusive range over the complete source.',clarification='')
    saved=q.save_typed_plan(authority(),goal,p,context_hash=catalog['context_hash'])
    assert saved['plan']==p
    with pytest.raises(ApiFailure):q.catalogue(authority('bob'),goal)


def test_reviewed_relationships_survive_selection(coordinator):
    q=coordinator.queries;q.retrieval=coordinator.retrieval
    catalog=q.catalogue(authority(),'Orders and customers employee IDs')
    ids={d['dataset_id'] for d in catalog['datasets']}
    assert {'pg_orders','pg_customers'}<=ids
    assert any(e['source_dataset_id']=='pg_orders' and e['target_dataset_id']=='pg_customers' for e in catalog['relationships'])
    assert all({e['source_dataset_id'],e['target_dataset_id']}<=ids for e in catalog['relationships'])


def test_no_matching_mapping_is_actionable(coordinator):
    q=coordinator.queries;q.retrieval=coordinator.retrieval
    with pytest.raises(ApiFailure) as error:q.catalogue(authority(),'Analyse zebras')
    assert error.value.code=='DATA_QUERY_MAPPING_REQUIRED'


def test_confirmed_business_synonym_is_reused(coordinator):
    c=coordinator;q=c.queries;q.retrieval=c.retrieval
    view=c.manager.relationships.detailed.get(authority())
    c.manager.relationships.detailed.edit(authority(),'pg_orders',dict(revision=view['graph']['revision'],entity_name='Procurement',role='represents',status='confirmed'))
    catalog=q.catalogue(authority(),'Summarize procurement')
    assert [d['dataset_id'] for d in catalog['datasets']]==['pg_orders']
    assert catalog['confirmed_business_mappings'][0]['entity_name']=='Procurement'


def test_relevant_wide_scalar_schema_is_not_truncated(coordinator):
    c=coordinator;q=c.queries;q.retrieval=c.retrieval
    with c.store.transaction() as db:
        raw=db.execute("SELECT document FROM data_source_snapshots WHERE connection_id='pg' AND revision=1").fetchone()[0]
        snap=json.loads(raw)
        snap['datasets'].append(dataset('pg','warranties',[(f'attribute{j}',['integer']) for j in range(950)],'northwind'))
        db.execute("UPDATE data_source_snapshots SET document=? WHERE connection_id='pg' AND revision=1",(json.dumps(snap),))
    c.manager.relationships.request(authority());c.manager.relationships.tick()
    with pytest.raises(ApiFailure) as error:q.catalogue(authority(),'List warranties')
    assert error.value.code=='KG_RETRIEVAL_LIMIT'
