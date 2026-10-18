"""Metadata retrieval tests: no external databases, model calls or Google writes."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator
from tests.test_data_relationships import manager, built, auth as base_auth, dataset
from workflow_api.data_sources import DataSources
from workflow_api.data_queries import DataQueries
from workflow_api.database_workflows import DatabaseWorkflows, bind_generated
from workflow_api.service import ApiFailure
from workflow_api.kg_retrieval import terms


def authority(owner='alice'):
    return {**base_auth(owner), 'roles':['admin'], 'scopes':['workspace:read'], 'permissions':['tools.read','tools.assign','workflow.plan']}


@pytest.fixture
def coordinator(manager):
    with manager.store.transaction() as db:
        for cid,raw in db.execute('SELECT connection_id,document FROM data_source_connections').fetchall():
            doc=json.loads(raw);doc['engine']='postgresql' if cid=='pg' else 'mongodb'
            db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(doc),cid))
    built(manager)
    sources=DataSources(manager.store,{})
    ops=SimpleNamespace(manager=sources,store=manager.store,policy=lambda:{'targets':[]})
    service=SimpleNamespace(registry=SimpleNamespace(list_tools=lambda auth:{'data':{'items':[]}}))
    return DatabaseWorkflows(service,ops,DataQueries(sources),lambda workspace,owner:authority(owner) if workspace=='one' else None)


def test_exact_source_and_confirmed_concepts_not_generic_customer_references(coordinator):
    c=coordinator;p,catalog=c.retrieval.retrieve(authority(),'List orders with employee IDs')
    assert not p['requires_selection']
    assert p['source_ids']==['pg_orders']
    assert len(catalog['sources'])==1
    assert any('dataset name' in reason for source in p['candidates'] for reason in source['reasons'])
    assert terms('customerID customers categories')=={'customer','id','category'}
    view=c.manager.relationships.detailed.get(authority())
    c.manager.relationships.detailed.edit(authority(),'pg_orders',dict(revision=view['graph']['revision'],entity_name='Purchase',role='represents',status='confirmed'))
    p,_=c.retrieval.retrieve(authority(),'Review purchases')
    assert p['source_ids']==['pg_orders']
    assert any('confirmed concept' in r for candidate in p['candidates'] for r in candidate['reasons'])


def test_ambiguity_requires_explicit_owned_selection(coordinator):
    c=coordinator;p,_=c.retrieval.retrieve(authority(),'List customers')
    assert p['requires_selection']
    explicit={'revision':p['revision'],'source_ids':['mongo_customers']}
    p,catalog=c.retrieval.retrieve(authority(),'List customers',explicit)
    assert not p['requires_selection'] and [s['dataset_id'] for s in catalog['sources']]==['mongo_customers']
    with pytest.raises(ApiFailure) as e:c.retrieval.retrieve(authority(),'List customers',dict(revision=p['revision'],source_ids=['foreign_table']))
    assert e.value.status==403
    context=c.enrich(authority(),{},'List customers')
    assert not context['knowledge_graph_retrieval']['requires_selection']
    assert {'mongo_customers','pg_customers'} <= {source['dataset_id'] for source in context['database_catalog']['sources']}


def test_stale_preview_disconnect_index_update_and_no_metadata_cross_owner(coordinator):
    c=coordinator;p,_=c.retrieval.retrieve(authority(),'List orders')
    graph=c.manager.relationships.get(authority())['graph']
    c.manager.relationships.edit(authority(),'annotation','pg_orders',dict(revision=graph['revision'],description='Warranty claims'))
    with pytest.raises(ApiFailure) as e:c.retrieval.retrieve(authority(),'List orders',dict(revision=p['revision'],source_ids=['pg_orders']))
    assert e.value.code=='KG_RETRIEVAL_STALE'
    fresh,_=c.retrieval.retrieve(authority(),'Find warranty claims')
    assert fresh['source_ids']==['pg_orders'] and fresh['revision']!=p['revision']
    other,_=c.retrieval.retrieve(authority('bob'),'List orders')
    assert other['coverage']['datasets']==0 and other['candidates']==[]
    with c.store.transaction() as db:
        raw=db.execute("SELECT document FROM data_source_connections WHERE connection_id='pg'").fetchone()[0]
        doc=json.loads(raw);doc['connection_status']='disconnected'
        db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='pg'",(json.dumps(doc),))
    p,_=c.retrieval.retrieve(authority(),'List orders')
    assert all(s['connection_id']!='pg' for s in p['candidates'])


def test_large_catalog_bounded_context_and_unchanged_cache(coordinator):
    c=coordinator
    with c.store.transaction() as db:
        raw=db.execute("SELECT document FROM data_source_snapshots WHERE connection_id='pg' AND revision=1").fetchone()[0]
        snap=json.loads(raw)
        snap['datasets'] += [dataset('pg','inventory'+str(i),[('stock',['integer'])],'northwind') for i in range(150)]
        snap['datasets'].append(dataset('pg','warranties',[('claimCode',['text'])],'northwind'))
        db.execute("UPDATE data_source_snapshots SET document=? WHERE connection_id='pg' AND revision=1",(json.dumps(snap),))
    c.manager.relationships.request(authority());c.manager.relationships.tick()
    p,cat=c.retrieval.retrieve(authority(),'List warranties by claim code')
    assert p['coverage']['datasets']==154 and p['source_ids']==['pg_warranties']
    assert len(cat['sources'])==1 and len(json.dumps(cat))<15000
    scope=dict(sources=[{key:source[key] for key in ('connection_id','dataset_id','label','engine','context_hash')} for source in cat['sources']], graph_hash=cat['graph_hash'])
    _,current=c.scope(authority(),{'metadata':{'database_scope':scope}})
    assert len(current['sources'])==1  # Execution freshness does not reload a model-wide catalog.
    p2,_=c.retrieval.retrieve(authority(),'List warranties by claim code')
    assert p2['indexed_at']==p['indexed_at']
    context=c.enrich(authority(),{'database_catalog':{'sources':['injected']},'knowledge_graph_retrieval':{'revision':'fake'}},'List warranties')
    assert [s['dataset_id'] for s in context['database_catalog']['sources']]==['pg_warranties']
    assert context['knowledge_graph_retrieval']['revision']==p['revision']


def test_technical_path_expansion_never_suggested_edges(coordinator):
    c=coordinator;p,cat=c.retrieval.retrieve(authority(),'List orders with customers',None)
    assert all(e['status'] in {'accepted','declared'} for e in p['relationships'])
    assert all(e['source_dataset_id']!='mongo_customers' and e['target_dataset_id']!='mongo_customers' for e in p['relationships'])
    assert any('no declared/accepted path' in w for w in p['warnings'])
    assert len(cat['sources'])<=4


def test_agent_task_context_and_out_of_scope_rejection(coordinator):
    c=coordinator;cat=c.catalog(authority())
    ids=[s['dataset_id'] for s in cat['sources']]
    w={'tools':[{'tool_id':'database_read_query'}], 'nodes':[],
       'metadata':{'database_source_ids':ids,'agent_database_source_ids':{'sales':[ids[0]],'accounts':[ids[1]]}},
       'agents':[{'agent_id':a,'capabilities':['database.read_query'],'instructions':'Read current records.'} for a in ('sales','accounts')]}
    bind_generated(w,{'database_catalog':cat})
    assert len(w['metadata']['agent_database_sources']['sales'])==1
    assert ids[1] not in w['agents'][0]['instructions']
    bad=deepcopy(w);bad['metadata'].update(database_source_ids=ids,agent_database_source_ids={'sales':['outside']})
    with pytest.raises(ValueError):bind_generated(bad,{'database_catalog':cat})


def test_no_match_does_not_invent_sources_and_safe_input(coordinator):
    p,cat=coordinator.retrieval.retrieve(authority(),'Analyse zebras')
    assert not p['source_ids'] and not cat['sources'] and p['warnings']
    for bad in ('',None,{},'x'*12001):
        with pytest.raises(ApiFailure):coordinator.retrieval.retrieve(authority(),bad)
    with pytest.raises(ApiFailure):coordinator.preview(authority(),{'objective':'orders','catalog':{}})


def test_preview_contract_confirmed_predicates_and_no_semantic_join_grant(coordinator):
    from pathlib import Path
    c=coordinator;view=c.manager.relationships.ontology.get(authority())
    edge=next(e for e in view['relationships'] if e['technical_status']=='declared')
    c.manager.relationships.ontology.edit(authority(),edge['relationship_id'],dict(revision=view['revision'],predicate='fulfills warranty',reversed=False,status='confirmed'))
    p,cat=c.retrieval.retrieve(authority(),'Show warranty')
    schema=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/knowledge-retrieval-v2.schema.json').read_text())
    Draft202012Validator.check_schema(schema);Draft202012Validator(schema).validate(p)
    assert cat['sources'] and cat['business_relationships'][0]['predicate']=='fulfills warranty'
    assert all(e['status'] in {'declared','accepted'} for e in cat['relationships'])
    with pytest.raises(ApiFailure) as error:c.enrich(authority(),{'knowledge_graph_revision':'outdated'},'Analyse zebras')
    assert error.value.status==409


def test_preview_http_is_session_protected_and_only_indexes_metadata(coordinator):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    from workflow_api.service import WorkflowService
    c=coordinator;service=WorkflowService(c.store)
    app=create_app(service,dev_auth=True,roles=['admin'],start_workers=False,planning_worker_enabled=False)
    service.registry._policy.workspace_id='one'
    app.state.workflow_auth=authority()
    with TestClient(app) as client:
        assert client.post('/knowledge-graph/preview',json={'objective':'List orders'}).status_code==401
        response=client.get('/session');cookie=response.cookies['builder_dev_session']
        client.cookies.set('builder_dev_session',cookie,path='/')
        result=client.post('/knowledge-graph/preview',json={'objective':'List orders'})
        assert result.status_code==200,result.text
        assert result.headers['cache-control']=='no-store'
        assert result.json()['data']['source_ids']==['pg_orders']
        assert client.post('/knowledge-graph/preview',json={'objective':'List orders'},headers={'origin':'https://untrusted.test'}).status_code==403
        assert client.post('/knowledge-graph/preview',json={'objective':'List orders','injected':{}}).status_code==400


def test_intermediate_paths_are_added_once_and_unaccepted_paths_are_excluded(coordinator,monkeypatch):
    c=coordinator;original=c.catalog(authority());base=original['sources'][0]
    sources=[]
    for name in ['alpha','beta','gamma','delta']:
        sources.append({**base,'dataset_id':name,'label':'Demo / '+name,'fields':[{'field_id':name+'_id','name':name+'ID','types':['integer']}]})
    def edge(name,left,right,status='accepted'):
        return dict(relationship_id=name,source_dataset_id=left,target_dataset_id=right,status=status,field_pairs=[dict(source_field_id=left+'_id',target_field_id=right+'_id')])
    catalog={**original,'sources':sources,'relationships':[edge('ab','alpha','beta'),edge('bg','beta','gamma'),edge('ad','alpha','delta','proposed')], 'business_mappings':[]}
    monkeypatch.setattr(c,'catalog',lambda *a,**kw:catalog)
    p,selected=c.retrieval.retrieve(authority(),'List alpha and gamma')
    assert set(p['source_ids'])=={'alpha','beta','gamma'}
    assert len({s['dataset_id'] for s in p['candidates']})==len(p['candidates'])
    assert any('intermediate' in r for s in p['candidates'] if s['dataset_id']=='beta' for r in s['reasons'])
    p,_=c.retrieval.retrieve(authority(),'List alpha and delta')
    assert p['relationships']==[] and any('no declared/accepted path' in w for w in p['warnings'])


def test_workflow_pins_semantic_meaning_and_rejects_changed_review(coordinator):
    from workflow_api.database_workflows import bind_generated
    c=coordinator;view=c.manager.semantic.get(authority());edge=next(e for e in view['relationships'] if e['technical_status']=='declared')
    c.manager.semantic.review(authority(),edge['relationship_id'],dict(revision=view['revision'],predicate='fulfills warranty',reversed=False,status='confirmed'))
    preview,catalog=c.retrieval.retrieve(authority(),'List warranty')
    assert preview['semantic_relationships']
    ids=[s['dataset_id'] for s in catalog['sources']]
    workflow={'tools':[{'tool_id':'database_read_query'}],'nodes':[],'agents':[{'agent_id':'reader','instructions':'Read data.','capabilities':['database.read_query']}], 'metadata':{'database_source_ids':ids}}
    bind_generated(workflow,{'database_catalog':catalog,'knowledge_graph_retrieval':preview})
    assert workflow['metadata']['semantic_kg_scope'][0]['predicate']=='fulfills warranty'
    c.scope(authority(),workflow)
    view=c.manager.semantic.get(authority())
    c.manager.semantic.review(authority(),edge['relationship_id'],dict(revision=view['revision'],predicate='records warranty',reversed=False,status='confirmed'))
    with pytest.raises(ApiFailure) as error:c.scope(authority(),workflow)
    assert error.value.code=='KG_WORKFLOW_STALE'


def test_automatic_planning_passes_bounded_candidates_and_pins_actual_choice(coordinator):
    c=coordinator
    context=c.enrich(authority(),{},'List customers')
    catalog=context['database_catalog']
    assert 1 < len(catalog['sources']) <= 16
    assert not context['knowledge_graph_retrieval']['requires_selection']
    workflow={'tools':[{'tool_id':'database_read_query'}], 'nodes':[],
              'agents':[{'agent_id':'reader','capabilities':['database.read_query'],'instructions':'Read selected data.'}],
              'metadata':{'database_source_ids':['mongo_customers']}}
    bind_generated(workflow,context)
    pinned=workflow['metadata']['knowledge_graph_retrieval']
    assert pinned['source_ids']==['mongo_customers']
    assert [item['dataset_id'] for item in pinned['candidates'] if item['selected']]==['mongo_customers']
    assert len(workflow['metadata']['database_scope']['sources'])==1
    assert pinned['relationships']==[]
    assert pinned['semantic_relationships']==[]
    forged=deepcopy(workflow);forged['metadata']['database_source_ids']=['outside']
    with pytest.raises(ValueError):bind_generated(forged,context)


def test_automatic_candidate_budget_does_not_expand_execution_budget(coordinator):
    c=coordinator
    with c.store.transaction() as db:
        raw=db.execute("SELECT document FROM data_source_snapshots WHERE connection_id='pg' AND revision=1").fetchone()[0]
        snap=json.loads(raw)
        snap['datasets'] += [dataset('pg','inventory'+str(i),[('stock',['integer'])],'northwind') for i in range(30)]
        db.execute("UPDATE data_source_snapshots SET document=? WHERE connection_id='pg' AND revision=1",(json.dumps(snap),))
    c.manager.relationships.request(authority());c.manager.relationships.tick()
    context=c.enrich(authority(),{},'Review inventory stock')
    assert not context['knowledge_graph_retrieval']['requires_selection']
    assert len(context['database_catalog']['sources'])<=16
    ids=[source['dataset_id'] for source in context['database_catalog']['sources']]
    workflow={'tools':[{'tool_id':'database_read_query'}],'nodes':[],'agents':[], 'metadata':{'database_source_ids':ids[:5]}}
    with pytest.raises(ValueError):bind_generated(workflow,context)


def test_enabled_registered_research_and_sheet_setup_reach_planner(coordinator):
    from runtime.supplier_search import SEARCH, PAGE
    from connector_extension.catalog import CATALOG
    c=coordinator
    enabled=[deepcopy(SEARCH),deepcopy(PAGE),deepcopy(CATALOG['extension_sheets_create'])]
    for tool in enabled:tool['availability']='enabled'
    disabled=deepcopy(CATALOG['extension_sheets_add_tabs']);disabled['availability']='disabled'
    absent=deepcopy(CATALOG['extension_calendar_list']);absent['availability']='enabled'
    tools=[*enabled,disabled,absent]
    c.service.runtime_runner=SimpleNamespace(connectors={tool['tool_id']:object() for tool in [*enabled,disabled]})
    c.service.registry.list_tools=lambda auth:{'data':{'items':[{'tool_id':tool['tool_id'],'definition':tool} for tool in tools]}}
    context=c.enrich(authority(),{'workflow_google_tools':[{'tool_id':'forged'}]},'List orders')
    assert {tool['tool_id'] for tool in context['workflow_google_tools']}=={tool['tool_id'] for tool in enabled}
    assert next(tool for tool in context['workflow_google_tools'] if tool['tool_id']=='extension_sheets_create')['approval_required'] is True
    assert {tool['tool_id'] for tool in c.preview_tools(authority(),True)}=={tool['tool_id'] for tool in enabled}


@pytest.mark.parametrize('status',['queued','running','failed'])
def test_retrieval_cache_tracks_profile_availability(coordinator,status):
    c=coordinator
    preview,_=c.retrieval.retrieve(authority(),'List orders')
    assert 'pg_orders' in preview['source_ids']
    with c.store.transaction() as db:
        doc=json.loads(db.execute("SELECT document FROM data_source_connections WHERE connection_id='pg'").fetchone()[0])
        doc['profiling_status']=status
        db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='pg'",(json.dumps(doc),))
    preview,_=c.retrieval.retrieve(authority(),'List orders')
    assert all(source['connection_id']!='pg' for source in preview['candidates'])
    with c.store.transaction() as db:
        doc['profiling_status']='ready'
        db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='pg'",(json.dumps(doc),))
    preview,_=c.retrieval.retrieve(authority(),'List orders')
    assert 'pg_orders' in preview['source_ids']


@pytest.mark.parametrize('change,code',[
    ('disconnect','DATABASE_WORKFLOW_SOURCE_UNAVAILABLE'),
    ('queued','DATABASE_WORKFLOW_SOURCE_PROFILING'),
    ('delete','DATABASE_WORKFLOW_SOURCE_MISSING'),
])
def test_workflow_preflight_explains_lifecycle_before_semantic_scope(coordinator,change,code):
    c=coordinator
    _,catalog=c.retrieval.retrieve(authority(),'List orders')
    scope={'sources':[{k:s[k] for k in ('connection_id','dataset_id','label','engine','context_hash')} for s in catalog['sources']], 'graph_hash':catalog['graph_hash']}
    workflow={'metadata':{'database_scope':scope,'semantic_kg_scope':{'invalid':'must not mask lifecycle failure'}}}
    with c.store.transaction() as db:
        if change=='delete':db.execute("DELETE FROM data_source_connections WHERE connection_id='pg'")
        else:
            doc=json.loads(db.execute("SELECT document FROM data_source_connections WHERE connection_id='pg'").fetchone()[0])
            if change=='disconnect':doc['connection_status']='disconnected'
            else:doc['profiling_status']=change
            db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='pg'",(json.dumps(doc),))
    with pytest.raises(ApiFailure) as failure:c.scope(authority(),workflow)
    assert failure.value.code==code
