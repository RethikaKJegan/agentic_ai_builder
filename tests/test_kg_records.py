"""Record KG nodes come only from validated real reads; no fabricated instances."""
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator
from tests.test_data_queries import queries,auth
from tests.test_database_workflows import harness,operations,engines
from workflow_api.kg_records import KnowledgeRecords
from workflow_api.service import ApiFailure


def linked(queries):
    graph=queries.manager.relationships.get(auth())['graph'];edge=graph['relationships'][0]
    queries.manager.relationships.edit(auth(),'review',edge['relationship_id'],dict(revision=graph['revision'],status='accepted'))
    semantic=queries.manager.semantic;view=semantic.get(auth());edge=view['relationships'][0]
    view=semantic.review(auth(),edge['relationship_id'],dict(revision=view['revision'],predicate='categorizes',reversed=edge['source_dataset_id']!='mongo_categories',status='confirmed'))
    return semantic,view,edge


def body(view,edge):
    return dict(revision=view['revision'],dataset_id='mongo_categories',identity_field_id='mongo_categories_categoryID',identity_value=1,label_field_id='mongo_categories_name',relationship_id=edge['relationship_id'],neighbor_identity_field_id='pg_lines_qty',neighbor_label_field_id='pg_lines_qty',limit=5)


def test_observed_nodes_edges_direction_query_evidence_and_contract(queries):
    semantic,view,edge=linked(queries)
    result=KnowledgeRecords(semantic,queries).explore(auth(),body(view,edge))
    assert len(result['nodes'])==3 and len(result['edges'])==2
    root=next(n for n in result['nodes'] if n['dataset_id']=='mongo_categories')
    assert root['label']=='Food'
    assert {n['identity_value'] for n in result['nodes'] if n['dataset_id']=='pg_lines'}=={2,4}
    assert all(e['source_node_id']==root['node_id'] and e['predicate']=='categorizes' for e in result['edges'])
    assert len(result['query_traces'])==4 and result['sources']
    schema=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/kg-records-v1.schema.json').read_text())
    Draft202012Validator(schema).validate(result)
    with queries.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM data_query_plans').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM kg_semantic_proposals').fetchone()[0]==0


def test_truncation_missing_record_stale_and_unaccepted_links(queries):
    semantic,view,edge=linked(queries);explorer=KnowledgeRecords(semantic,queries)
    result=explorer.explore(auth(),{**body(view,edge),'limit':1})
    assert result['limited'] and len(result['edges'])==1
    result=explorer.explore(auth(),{**body(view,edge),'identity_value':999})
    assert result['nodes']==[] and result['edges']==[]
    with pytest.raises(ApiFailure):explorer.explore(auth(),{**body(view,edge),'revision':'old'})
    graph=queries.manager.relationships.get(auth())['graph']
    queries.manager.relationships.edit(auth(),'review',edge['technical_relationship_id'],dict(revision=graph['revision'],status='proposed'))
    view=semantic.get(auth())
    with pytest.raises(ApiFailure,match='independently declared or accepted'):explorer.explore(auth(),body(view,edge))


def test_duplicate_identity_invalid_source_and_no_invented_fields(queries):
    semantic,view,edge=linked(queries);explorer=KnowledgeRecords(semantic,queries)
    queries.reader.rows['mongo_categories'].append(dict(mongo_categories_categoryID=1,mongo_categories_name='Duplicate'))
    with pytest.raises(ApiFailure,match='multiple records'):explorer.explore(auth(),body(view,edge))
    for change in [dict(identity_field_id='foreign'),dict(dataset_id='other_owner'),dict(identity_value='1'),dict(limit=11),dict(limit=True)]:
        with pytest.raises(ApiFailure):explorer.explore(auth(),{**body(view,edge),**change})


def test_neighbor_identity_checked_against_complete_matching_data(queries):
    semantic,view,edge=linked(queries)
    queries.reader.rows['pg_lines'].append(dict(pg_lines_categoryID=2,pg_lines_qty=2,pg_lines_price=1,pg_lines_discount=0))
    with pytest.raises(ApiFailure,match='not unique'):KnowledgeRecords(semantic,queries).explore(auth(),body(view,edge))


@pytest.mark.parametrize('engine',['pg','mongo'])
def test_native_record_nodes_use_actual_postgres_and_mongo_records(harness,engine):
    h=harness;manager=h['operations'].manager
    with manager.store.transaction() as db:
        for cid,revision,raw in db.execute('SELECT connection_id,revision,document FROM data_source_snapshots').fetchall():
            snapshot=json.loads(raw);snapshot.setdefault('coverage','declared' if cid=='pg' else 'sampled');snapshot.setdefault('warnings',[])
            db.execute('UPDATE data_source_snapshots SET document=? WHERE connection_id=? AND revision=?',(json.dumps(snapshot),cid,revision))
    manager.relationships.request(h['auth']);manager.relationships.tick()
    view=manager.semantic.get(h['auth']);target=next(t for t in h['operations'].testing['targets'] if t['connection_id']==engine)
    context=h['coordinator'].queries.context(h['auth']);fields=[f for f in context[2].values() if f['dataset_id']==target['dataset_id']]
    identity=next(f['field_id'] for f in fields if f['name']==target['identity_fields'][0]);label=next(f['field_id'] for f in fields if f['name']=='name')
    result=KnowledgeRecords(manager.semantic,h['coordinator'].queries).explore(h['auth'],dict(revision=view['revision'],dataset_id=target['dataset_id'],identity_field_id=identity,identity_value='seed',label_field_id=label,relationship_id='',neighbor_identity_field_id='',neighbor_label_field_id='',limit=5))
    assert result['nodes'][0]['label']=='Seed' and result['nodes'][0]['identity_value']=='seed'
    assert len(result['nodes'])==1 and result['edges']==[] and result['sources'][0]['dataset_id']==target['dataset_id']
