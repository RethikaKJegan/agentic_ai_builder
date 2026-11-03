"""Phase 2: independently specified records, no remote model or company writes."""
from copy import deepcopy
from datetime import datetime,timezone
import json
from types import SimpleNamespace
from unittest.mock import patch,Mock
import pytest
from cryptography.fernet import Fernet
from bson import ObjectId
from tests.test_business_knowledge import knowledge
from tests.test_business_reference import reference
from tests.test_business_generation import generation
from tests.test_business_ontology import foundation,auth
from workflow_api.business_retrieval import BusinessRetrieval
from workflow_api.business_resolution import ConceptIndex,interpret,resolve,closure
from workflow_api.business_knowledge_model import digest
from workflow_api.business_intent import IntentInterpreter
from workflow_api.data_sources import DataSources
from workflow_api.service import ApiFailure


class Reader:
    def __init__(self):
        self.calls=[];self.hook=None
        self.rows={
          'tickets':[
            {'_id':'C123','engineNo':'E123','hmr':99,'complaintRecord':{'hmr':'1000','natureOfCustomerComplaint':'Cooling water leak','investigationDetailsByOem':'Reported hose leak'},'status':'OPENED','createdAt':datetime(2026,1,2,tzinfo=timezone.utc)},
            {'_id':'C999','engineNo':'E999','complaintRecord':{'hmr':'9','natureOfCustomerComplaint':'Oil leak'},'status':'CLOSED'},
            {'_id':'C124','engineNo':'E124','complaintRecord':{'hmr':'bad','natureOfCustomerComplaint':'Cooling warning'},'status':'OPENED'},
          ],
          'jointinspectionreports':[
            {'_id':'J1','ticketId':'C123','status':'PUBLISHED','potentialCause':'Hose connection','complaint':'Cooling water leak','defect':'Loose hose'},
            {'_id':'J9','ticketId':'C999','status':'DRAFTED'},
            {'_id':'Jorphan','ticketId':'missing','status':'PUBLISHED'},
          ],
          'enginedetails':[{'_id':'I1','engineSerialNumber':'E123','invoiceDate':datetime(2025,12,1,tzinfo=timezone.utc)}],
          'failedengineanalyses':[{'_id':'Q1','engineSerialNumber':'E123','status':'PENDING','defect':'Unconfirmed water leak'}],
          'enginereplacements':[{'_id':'R1','ticket':'C123','mode':'WARRANTY'}],
          'partreplacements':[], 'floatengines':[],
        }
    def objects(self,config,dataset,fields,keys,filters,offset,limit,deadline):
        from workflow_api.business_graph import at
        from workflow_api.data_write_adapter import value_for
        self.calls.append(dict(collection=dataset['name'],fields=[f['name'] for f in fields],filters=deepcopy(filters),limit=limit,database=config['database']))
        if self.hook:self.hook()
        types={f['name']:f for f in fields}
        native={k:value_for(types[k],v) for k,v in filters.items()}
        return deepcopy([r for r in self.rows.get(dataset['name'],[]) if all(type(at(r,k)) is type(v) and at(r,k)==v for k,v in native.items())][offset:offset+limit])


@pytest.fixture
def retrieval(knowledge,tmp_path):
    f,_,a,old,result=knowledge
    key=tmp_path/'key';key.write_bytes(Fernet.generate_key())
    manager=DataSources(f.store,{'BUILDER_DATA_SOURCE_KEY_FILE':str(key)})
    snapshot=f.version(a,result['version_id']);k=snapshot['knowledge']
    groups={}
    for m in k['source_mappings']:
        if m['id'] in ('mapping:engine_build_date','mapping:invoice_model'):continue
        groups.setdefault((m['source_role'],m['collection']),{})[m['field_path']]=dict(name=m['field_path'],types=[next(t for t in m['stored_datatypes'] if t in ('string','integer','number','date','datetime','ObjectId','boolean'))])
    for rule in k['identity_rules']:
        for side in ('source','target'):
            s=rule[side]
            if s:groups.setdefault((s['source_role'],s['collection']),{})[s['field_path']]=dict(name=s['field_path'],types=['string'])
    with f.store.transaction() as db:
        for role in ('service','quality'):
            datasets=[]
            for (r,name),fields in groups.items():
                if r!=role:continue
                fields['_id']=dict(name='_id',types=['string'])
                datasets.append(dict(dataset_id='dataset:'+name,name=name,fields=list(fields.values())))
            secret=manager.cipher.encrypt(json.dumps(dict(engine='mongodb',database=role)).encode()).decode()
            db.execute('UPDATE data_source_connections SET secret=? WHERE connection_id=?',(secret,role))
            db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(role,1,json.dumps(dict(datasets=datasets))))
    reader=Reader();current=deepcopy(a)
    service=BusinessRetrieval(f,manager,lambda *args:current,reader)
    return SimpleNamespace(f=f,s=service,a=a,old=old,version=result['version_id'],snapshot=snapshot,reader=reader,current=current,manager=manager)


def preview(x,question='Show complaints for engine E123.',**kwargs):
    return x.s.preview(x.a,dict(question=question,request_key='test_request_001',**kwargs))


def execute(x,p):return x.s.execute(x.a,p['request_id'],{})


@pytest.mark.parametrize('question', ['Show complaints for engine E123.','Find service issues for motor E123.','Find customer issues for engine E123.'])
def test_aliases_preview_and_correct_exact_records(retrieval,question):
    x=retrieval;p=preview(x,question)
    assert p['intent']['task']=='complaints' and p['intent']['identifiers']=={'serial':'E123'}
    assert p['ready'] and not x.reader.calls and p['company_reads']==0
    assert 'complaints:warranty_ticket' in p['dependency_resolution']['concept_ids']
    assert any(c['matched_names'] for c in p['intent']['candidates'])
    result=execute(x,p)
    assert [r['fields']['_id'] for r in result['records']]==['C123']
    assert result['version_id']==x.version and result['company_writes']==0
    record=result['records'][0]
    assert record['values']['mapping:complaint_hours']['value']=='1000'
    assert record['values']['mapping:ticket_hours']['value']=='99'
    assert result['physical_engine_identity']=='unresolved'
    assert result['completeness']=='complete_for_scoped_reads'
    assert all(c['limit']<=21 for c in x.reader.calls)
    assert all(not {'password','attachments','photos'} & set(c['fields']) for c in x.reader.calls)


def test_inspection_exact_reference_not_unrelated_or_orphan(retrieval):
    x=retrieval;p=preview(x,'Show inspection findings for complaint C123.')
    assert p['ready'] and p['dependency_resolution']['dependencies']==['dependency:inspection']
    assert 'mapping:inspection_status' in {m['id'] for m in p['mappings']}
    assert p['rules'] and not x.reader.calls
    result=execute(x,p)
    assert {r['fields']['_id'] for r in result['records']}=={'C123','J1'}
    assert result['reference_edges'][0]['binding_id']=='identity:inspection_ticket'
    jir=next(r for r in result['records'] if r['collection']=='jointinspectionreports')
    assert jir['states'][0]['result']['activity_completion_inferred'] is False
    assert result['completeness']=='incomplete'
    assert any(m.get('fact')=='inspection_activity_completion_evidence' for m in result['missing'])


def test_comparison_with_explicit_anchor(retrieval):
    x=retrieval;p=preview(x,'Compare this complaint with its joint inspection.',inputs={'complaint_id':'C123'})
    assert p['ready'] and p['intent']['task']=='inspection'
    assert {r['fields']['_id'] for r in execute(x,p)['records']}=={'C123','J1'}


def test_bounded_cooling_search_and_invalid_hours(retrieval):
    x=retrieval;p=preview(x,'Find previous cooling-related breakdown reports.')
    r=execute(x,p)
    assert {r['fields']['_id'] for r in r['records']}=={'C123','C124'}
    assert r['conversion_issues'] and not r['population_complete']
    assert 'Q1' not in {r['fields']['_id'] for r in r['records']}


def test_numeric_filter_never_lexical_and_missing_source_values(retrieval):
    x=retrieval;p=preview(x,'Show complaints over 100 hours.')
    r=execute(x,p)
    assert [row['fields']['_id'] for row in r['records']]==['C123']
    assert x.reader.calls[0]['filters']=={}
    assert r['conversion_issues'] and not r['population_complete']


def test_saved_mappings_and_unavailable_fields(retrieval):
    x=retrieval;p=preview(x,'Show engine history for engine E123 including model and build date.')
    assert {'mapping:engine_build_date','mapping:invoice_model'} <= {m['mapping_id'] for m in p['missing'] if 'mapping_id' in m}
    assert all('buildDate' not in s['fields'] and 'engineModel' not in s['fields'] for s in p['steps'])
    r=execute(x,p)
    assert {r['fields']['_id'] for r in r['records']}=={'C123','I1','Q1'}
    assert r['ambiguous_associations'][0]['classification']=='candidate'
    assert not r['ambiguous_associations'][0]['physical_merge']
    assert r['completeness']=='incomplete'


def test_history_cross_source_qualified_identity(retrieval):
    x=retrieval;r=execute(x,preview(x,'Show history for engine E123.'))
    assert len({r['record_id'] for r in r['records']})==3
    assert r['ambiguous_associations'] and not r['business_conclusions']
    assert r['physical_engine_identity']=='unresolved'


def test_empty_exact_result(retrieval):
    x=retrieval;r=execute(x,preview(x,'Show complaints for engine NONE123.'))
    assert r['records']==[] and r['executed_steps'][0]['empty']
    assert r['completeness']=='complete_for_scoped_reads'


@pytest.mark.parametrize('question', ['Show inspection findings.','Show complaints for engine E123 and engine E999.','Approve warranty for engine E123.','Count all complaints for engine E123.','Show complaints after yesterday for engine E123.','Show completed inspections for engine E123.'])
def test_unsupported_ambiguous_and_write_requests_never_execute(retrieval,question):
    x=retrieval;p=preview(x,question)
    assert not p['ready']
    with pytest.raises(ApiFailure):execute(x,p)
    assert not x.reader.calls


def test_facts_missing_policy_and_conditional_closure(retrieval):
    x=retrieval;p=preview(x,'Check warranty for engine E123.')
    assert p['dependency_resolution']['dependencies']==['dependency:warranty']
    assert {c['state'] for c in p['dependency_resolution']['conditions']}=={'unknown'}
    assert {'mapping:sale_date','mapping:invoice_date'} <= {m['id'] for m in p['mappings']}
    assert any(f['fact']=='engine_identity' and f['provider']=='derived_check' for f in p['fact_providers'])
    r=execute(x,p)
    assert r['rule_results'] and all(r['result']['official_policy_result'] is False for r in r['rule_results'])
    assert not r['business_conclusions'] and r['completeness']=='incomplete'


def test_dependency_cycles_and_budget(retrieval):
    x=retrieval;v=deepcopy(x.snapshot)
    v['knowledge']['dependencies'][0]['concepts'].append('warranty:warranty_assessment')
    result=closure(v,['warranty:warranty_assessment'],{},96)
    assert result['complete'] and result['dependencies']==['dependency:warranty']
    assert not closure(v,['warranty:warranty_assessment'],{},2)['complete']
    v['knowledge']['dependencies'][0]['conditional'][0]['when']='arbitrary executable meaning'
    assert not closure(v,['warranty:warranty_assessment'],{},96)['complete']


def test_policy_registered_predicates(retrieval):
    x=retrieval;v=deepcopy(x.snapshot)
    v['knowledge']['manifest']['policy_snapshots']=[dict(policy_id='p1',clauses={'coverage_mode':{'value':'invoice_and_hours'}})]
    d=closure(v,['warranty:warranty_assessment'],{'policy_id':'p1'})
    assert [c['state'] for c in d['conditions']]==['false','true']
    assert 'mapping:sale_date' not in d['mapping_ids']


def test_version_pins_retries_and_history(retrieval):
    x=retrieval;p=preview(x)
    v=deepcopy(x.snapshot);v['version_id']='bov_new';v['revision']+=1
    with x.f.store.transaction() as db:db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',('one','alice','bov_new',json.dumps(v)))
    assert preview(x)==p
    assert execute(x,p)['version_id']==x.version
    assert x.f.version(x.a,x.old).get('knowledge') is None
    with pytest.raises(ApiFailure):preview(x,'Show complaints for engine E999.')
    with pytest.raises(ApiFailure):x.s.preview(x.a,dict(question='Show complaints for engine E123.',request_key='historical_request',version_id=x.old))


@pytest.mark.parametrize('change', ['metadata','secret','authority','disconnect','ownership'])
def test_stale_or_revoked_source_rejected_before_reads(retrieval,change):
    x=retrieval;p=preview(x)
    if change=='authority':x.current['decision']='deny'
    else:
        with x.f.store.transaction() as db:
            if change=='secret':db.execute("UPDATE data_source_connections SET secret='other' WHERE connection_id='service'")
            elif change=='ownership':db.execute("UPDATE data_source_connections SET owner='bob' WHERE connection_id='service'")
            else:
                d=json.loads(db.execute("SELECT document FROM data_source_connections WHERE connection_id='service'").fetchone()[0])
                if change=='metadata':d['metadata_revision']=2
                else:d['connection_status']='disconnected'
                db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='service'",(json.dumps(d),))
    with pytest.raises(ApiFailure):execute(x,p)
    assert not x.reader.calls


def test_late_authority_revocation_does_not_save_evidence(retrieval):
    x=retrieval;p=preview(x)
    x.reader.hook=lambda:x.current.update(decision='deny')
    with pytest.raises(ApiFailure):execute(x,p)
    x.current['decision']='allow'
    assert 'evidence' not in x.s.inspect(x.a,p['request_id'])


def test_server_plan_only_scoping_and_tampering(retrieval):
    x=retrieval;p=preview(x)
    for a in (auth(owner='bob'),auth(workspace='other')):
        with pytest.raises(ApiFailure):x.s.inspect(a,p['request_id'])
    with pytest.raises(ApiFailure):x.s.execute(x.a,p['request_id'],{'steps':p['steps']})
    with x.f.store.transaction() as db:
        q=deepcopy(p);q['steps'][0]['fields'].append('password')
        db.execute('UPDATE business_retrieval_requests SET document=?',(json.dumps(q),))
    with pytest.raises(ApiFailure):execute(x,p)
    assert not x.reader.calls


def test_execute_idempotent_rechecks_authority(retrieval):
    x=retrieval;p=preview(x);r=execute(x,p);calls=len(x.reader.calls)
    assert execute(x,p)==r and len(x.reader.calls)==calls
    x.current['decision']='deny'
    with pytest.raises(ApiFailure):execute(x,p)


def test_truncated_population_never_complete(retrieval):
    x=retrieval;x.reader.rows['tickets']=[dict(_id='C'+str(i),engineNo='E123') for i in range(25)]
    r=execute(x,preview(x))
    assert len(r['records'])==20 and r['executed_steps'][0]['truncated']
    assert r['completeness']=='incomplete' and not r['population_complete']


def test_native_objectid_references(retrieval):
    x=retrieval;oid=ObjectId('507f1f77bcf86cd799439011')
    x.reader.rows['tickets'][0]['_id']=oid;x.reader.rows['jointinspectionreports'][0]['ticketId']=oid
    with x.f.store.transaction() as db:
        d=json.loads(db.execute("SELECT document FROM data_source_snapshots WHERE connection_id='service'").fetchone()[0])
        for dataset in d['datasets']:
            for f in dataset['fields']:
                if (dataset['name'],f['name']) in [('tickets','_id'),('jointinspectionreports','ticketId')]:f['types']=['ObjectId']
        db.execute("UPDATE data_source_snapshots SET document=? WHERE connection_id='service'",(json.dumps(d),))
    # Ticket mapping declares string only: it is unavailable, not silently converted.
    p=preview(x,'Show inspection for engine E123.')
    assert any(m.get('mapping_id')=='mapping:ticket_id' and m['reason']=='type_mismatch' for m in p['missing'])
    r=execute(x,p)
    assert {rec['fields']['_id'] for rec in r['records']}=={str(oid),'J1'}
    assert r['reference_edges']
    assert r['records'][0]['source_reference']['native_value']=={'$objectid':str(oid)}


def test_reference_string_does_not_become_objectid(retrieval):
    x=retrieval;x.reader.rows['tickets'][0]['_id']=ObjectId('507f1f77bcf86cd799439011')
    r=execute(x,preview(x,'Show inspection for engine E123.'))
    assert [rec['fields']['_id'] for rec in r['records']]==['507f1f77bcf86cd799439011']
    assert any('native_reference_type_mismatch' in o['unresolved'] for o in r['executed_steps'])


def test_constrained_ai_and_fallback(retrieval):
    x=retrieval
    def valid(q,c,s):
        assert 'E123' not in q and 'IDENTIFIER_0' in q
        assert 'Cooling water leak' not in json.dumps(c)
        return dict(task='complaints',concept_ids=['complaints:warranty_ticket'],ambiguities=[],unsupported=[])
    x.s.interpreter=IntentInterpreter(provider=valid)
    p=preview(x,use_ai=True)
    assert p['intent']['interpretation']=='ai_validated' and p['intent']['model_calls']==1
    assert execute(x,p)['records'][0]['fields']['_id']=='C123'
    for bad in [dict(task='complaints',concept_ids=['evil:invented'],ambiguities=[],unsupported=[]),dict(task='complaints',concept_ids=[],ambiguities=[],unsupported=[],field='password')]:
        i=IntentInterpreter(provider=lambda *args:bad).run('Show complaints for engine E123.',x.snapshot,{},True)
        assert i['model_status']=='invalid_or_unavailable_deterministic_fallback' and i['task']=='complaints'
    assert IntentInterpreter().run('Show complaints for engine E123.',x.snapshot,{},True)['model_status']=='unavailable_deterministic_fallback'


def test_index_no_authoring_reads_or_semantic_diagnosis(retrieval):
    x=retrieval
    with patch('pathlib.Path.read_text',side_effect=AssertionError('Saved ontology only')):
        candidates=ConceptIndex(x.snapshot).search('MOTOR breakdown inspection report')
        assert candidates and all(c['concept_id'] in {c['id'] for c in x.snapshot['concepts']} for c in candidates)
    p=preview(x,'Show complaints for engine E123.')
    assert p['question'] and not x.reader.calls


def test_status_filter_stays_linked_to_anchor(retrieval):
    x=retrieval
    x.reader.rows['jointinspectionreports'].append(dict(_id='Junrelated',ticketId='C999',status='PUBLISHED'))
    p=preview(x,'Show PUBLISHED inspection reports for engine E123.')
    step=next(s for s in p['steps'] if s['collection']=='jointinspectionreports')
    assert step['reference']['binding_id']=='identity:inspection_ticket'
    r=execute(x,p)
    assert {r['fields']['_id'] for r in r['records']}=={'C123','J1'}
    edge=r['reference_edges'][0]
    assert edge['parent_record_id']==next(rec['record_id'] for rec in r['records'] if rec['fields']['_id']=='C123')


def test_filter_unavailable_is_never_dropped(retrieval):
    x=retrieval
    with x.f.store.transaction() as db:
        d=json.loads(db.execute("SELECT document FROM data_source_snapshots WHERE connection_id='service'").fetchone()[0])
        for dataset in d['datasets']:
            if dataset['name']=='tickets':dataset['fields']=[f for f in dataset['fields'] if f['name']!='complaintRecord.hmr']
        db.execute("UPDATE data_source_snapshots SET document=? WHERE connection_id='service'",(json.dumps(d),))
    p=preview(x,'Show complaints for engine E123 over 100 hours.')
    assert not p['ready'] and any(m['reason']=='filter_mapping_unavailable' for m in p['missing'])
    with pytest.raises(ApiFailure):execute(x,p)
    assert not x.reader.calls


def test_deadline_and_oversized_values_fail_without_persisting(retrieval):
    x=retrieval;p=preview(x)
    with patch('workflow_api.business_retrieval.time',SimpleNamespace(time=__import__('time').time,monotonic=Mock(side_effect=[0,0,0,21]))):
        with pytest.raises(ApiFailure) as e:execute(x,p)
    assert e.value.code=='BUSINESS_RETRIEVAL_TIMEOUT'
    assert 'evidence' not in x.s.inspect(x.a,p['request_id'])
    x.reader.rows['tickets'][0]['complaintRecord']['natureOfCustomerComplaint']='a'*70000
    with pytest.raises(ApiFailure):execute(x,p)
    assert 'evidence' not in x.s.inspect(x.a,p['request_id'])


def test_rule_facts_are_not_columns_and_nonpositive_inputs(retrieval):
    x=retrieval;p=preview(x,'Check warranty for engine E123.',inputs={'assessment_date':'2026-11-03'})
    assert {'identity_resolved','policy_applicable'}<={f['fact'] for f in p['fact_providers']}
    assert not {'identity_resolved','policy_applicable'} & {f for s in p['steps'] for f in s['fields']}
    x.reader.rows['tickets'][0]['complaintRecord']['hmr']='0'
    r=execute(x,p)
    assert next(rec for rec in r['records'] if rec['collection']=='tickets')['values']['mapping:complaint_hours']['value']=='0'
    assert all(result['result']['state']=='missing' for result in r['rule_results'])


def test_expired_preview_and_invalid_inputs(retrieval):
    x=retrieval
    for body in [None,{},dict(question='x',request_key='short'),dict(question='Show complaints for engine E123.',request_key='invalid_inputs',inputs={'identity_resolved':True}),dict(question='Show complaints for engine E123.',request_key='invalid_date',inputs={'assessment_date':'yesterday'})]:
        with pytest.raises(ApiFailure):x.s.preview(x.a,body)
    p=preview(x)
    with patch('workflow_api.business_retrieval.time.time',return_value=p['created_epoch']+3601):
        with pytest.raises(ApiFailure) as e:execute(x,p)
    assert e.value.code=='BUSINESS_RETRIEVAL_EXPIRED'
    assert not x.reader.calls


def test_planner_context_reads_saved_metadata_without_mutating_store(retrieval):
    from workflow_api.business_retrieval import planner_context
    x=retrieval
    with x.f.store.transaction(write=False) as db:
        before=db.execute('SELECT document FROM business_ontology_versions').fetchall()
        count=db.execute('SELECT COUNT(*) FROM business_retrieval_requests').fetchone()[0]
    context,ids=planner_context(x.f.store,x.a,'Show inspection for engine E123.',x.manager)
    assert context['version_id']==x.version and context['company_reads']==0
    assert {'dataset:tickets','dataset:jointinspectionreports'}<=set(ids)
    assert context['mappings'] and context['dependencies']['dependencies']==['dependency:inspection']
    with x.f.store.transaction(write=False) as db:
        assert db.execute('SELECT document FROM business_ontology_versions').fetchall()==before
        assert db.execute('SELECT COUNT(*) FROM business_retrieval_requests').fetchone()[0]==count
    assert not x.reader.calls


def test_http_preview_execute_inspect_and_session_security(retrieval):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    x=retrieval;app=create_app(database=x.f.store.path,dev_auth=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app);root='/business-ontology/v1/retrieval'
    assert client.post(root+'/preview',json={}).status_code==401
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    app.state.workflow_auth=x.a
    svc=app.state.business_retrieval;svc.reader=x.reader;svc.manager=x.manager;svc.sources.manager=x.manager
    body=dict(question='Show inspection for complaint C123.',request_key='http_request_001')
    assert client.post(root+'/preview',json=body,headers={'origin':'https://foreign.example'}).status_code==403
    response=client.post(root+'/preview',json=body)
    assert response.status_code==200
    p=response.json()['data'];assert not x.reader.calls
    response=client.post(root+'/'+p['request_id']+'/execute',json={})
    assert response.status_code==200 and len(response.json()['data']['records'])==2
    inspected=client.get(root+'/'+p['request_id'])
    assert inspected.status_code==200 and inspected.json()['data']['evidence']['version_id']==x.version
    assert client.post(root+'/'+p['request_id']+'/execute',json={'plan':{}}).status_code==422
    app.state.workflow_auth=auth(owner='bob')
    assert client.get(root+'/'+p['request_id']).status_code==404


def test_real_queryreader_dotted_projection_preserves_native_row():
    from contextlib import contextmanager
    from workflow_api.data_queries import QueryReader
    native=ObjectId('507f1f77bcf86cd799439011')
    row={'_id':native,'complaintRecord':{'hmr':'123'}}
    class Cursor:
        def sort(self,*a):return self
        def skip(self,*a):return self
        def limit(self,*a):return self
        def batch_size(self,*a):return self
        def max_time_ms(self,*a):return self
        def close(self):pass
        def __iter__(self):return iter([row])
    class Collection:
        def find(self,query,projection):
            assert query=={'_id':{'$eq':native}}
            assert projection=={'_id':1,'complaintRecord.hmr':1}
            return Cursor()
    class DB:
        def __getitem__(self,k):return Collection()
    class Client:
        def __getitem__(self,k):return DB()
    class Adapter:
        @contextmanager
        def connection(self,config):yield Client()
    reader=QueryReader(SimpleNamespace(adapter=Adapter()))
    import time
    result=reader.objects({'engine':'mongodb','database':'db'},{'name':'tickets'},[{'name':'_id','types':['ObjectId']},{'name':'complaintRecord.hmr','types':['string']}],['_id'],{'_id':str(native)},0,2,time.monotonic()+5)
    assert result==[row] and result[0]['_id'] is native


def test_nested_mapping_dependencies_reach_fixed_point(retrieval):
    x=retrieval;v=deepcopy(x.snapshot)
    v['knowledge']['dependencies'].append(dict(id='dependency:reported_symptom',subject_id='complaints:reported_symptom',concepts=['inspection:joint_inspection'],relationships=[],mappings=[],rules=[],required_facts=[],conditional=[]))
    v['knowledge_sha256']=digest(v['knowledge'])
    r=resolve(v,'Show complaints for engine E123.')
    assert {'dependency:reported_symptom','dependency:inspection'}<=set(r['dependency_resolution']['dependencies'])
    assert 'report_status' in r['intent']['requested_facts']
    assert any(f['fact']=='report_status' for f in r['fact_providers'])
    assert 'mapping:inspection_status' in {m['id'] for m in r['mappings']}


@pytest.mark.parametrize('task,question,expected',[
 ('replacement','Show replacement evidence for complaint C123.',{'C123','J1','R1'}),
 ('recurrence','Check recurrence evidence for engine E123.',{'I1','Q1'}),
])
def test_replacement_and_recurrence_retrieve_only_evidence(retrieval,task,question,expected):
    x=retrieval;p=preview(x,question)
    assert p['intent']['task']==task and p['ready']
    r=execute(x,p)
    assert {rec['fields']['_id'] for rec in r['records']}==expected
    assert r['completeness']=='incomplete' and r['missing']
    assert not r['business_conclusions'] and r['physical_engine_identity']=='unresolved'


def test_unknown_condition_and_explicit_policy_fail_safely(retrieval):
    x=retrieval;p=preview(x,'Show complaints for engine E123 with high priority.')
    assert not p['ready']
    with pytest.raises(ApiFailure):execute(x,p)
    with pytest.raises(ApiFailure):x.s.preview(x.a,dict(question='Check warranty for engine E123.',request_key='unknown_policy_01',inputs={'policy_id':'not_pinned'}))
    assert not x.reader.calls


def test_compound_numeric_filters_and_multiple_statuses(retrieval):
    x=retrieval
    p=preview(x,'Show complaints over 100 hours and under 2000 hours.')
    assert len(p['intent']['filters'])==2
    assert [r['fields']['_id'] for r in execute(x,p)['records']]==['C123']
    assert all(c['filters']=={} for c in x.reader.calls if c['collection']=='tickets')
    assert all(c['filters'] for c in x.reader.calls if c['collection']!='tickets')
    i=interpret('Show OPENED and CLOSED complaints for engine E123.',x.snapshot)
    assert i['ambiguities'] and not i['filters']
    assert interpret('Show complaints with hours > 100 for engine E123.',x.snapshot)['unsupported']


def test_controlled_code_and_engineer_native_reference_resolution(retrieval):
    x=retrieval;x.reader.rows['tickets'][0]['complaintRecord']['natureOfCustomerComplaint']='symptom-key'
    x.reader.rows['tickets'][0]['serviceEngineer']='engineer-key'
    x.reader.rows['simpsoncodes']=[dict(_id='symptom-key',code='C07',description='Observed source description',codeType='COMPLAINT',active=True)]
    x.reader.rows['users']=[dict(_id='engineer-key',name='Fixture engineer',active=False,password='must-not-project')]
    r=execute(x,preview(x,'Compare complaint C123 with inspection.'))
    views={v['kind']:v for v in r['resolved_references']}
    assert views['controlled_code']['original_value']=='symptom-key'
    assert views['controlled_code']['resolved_values']['mapping:code_description']=='Observed source description'
    assert views['engineer']['status']=='resolved'
    assert views['engineer']['resolved_values']['mapping:engineer_active'] is False
    assert all('password' not in call['fields'] for call in x.reader.calls)
    assert all(len(v['source_references'])==2 for v in views.values())


def test_invoice_path_is_an_explicit_candidate_not_a_physical_merge(retrieval):
    x=retrieval;x.reader.rows['enginedetails'].append(dict(_id='I2',engineSerialNumber='E123',invoiceDate=datetime(2025,12,2,tzinfo=timezone.utc)))
    p=preview(x,'Check warranty for complaint C123.');r=execute(x,p)
    invoice=next(s for s in p['steps'] if s['collection']=='enginedetails')
    assert invoice['reference']['classification']=='candidate'
    assert {v['fields']['_id'] for v in r['records'] if v['collection']=='enginedetails'}=={'I1','I2'}
    assert len([c for c in r['ambiguous_associations'] if c['binding_id']=='identity:ticket_invoice_serial'])==2
    assert not any(e['binding_id']=='identity:ticket_invoice_serial' for e in r['reference_edges'])
    gap=next(g for g in r['normalized_gaps'] if g['fact_id']=='invoice_association')
    assert gap['state']=='ambiguous_value' and len(gap['source_references'])==2
    assert r['physical_engine_identity']=='unresolved' and not r['business_conclusions']


@pytest.mark.parametrize('raw,state,value',[('21-03-2026','value','2026-03-21'),('31-04-2026','conversion_issue',None),('03/04/2026','ambiguous_value',None),(None,'unknown',None)])
def test_source_date_raw_value_precision_and_no_fallback(retrieval,raw,state,value):
    x=retrieval;x.reader.rows['jointinspectionreports'][0]['dateOfFailure']=raw
    r=execute(x,preview(x,'Compare complaint C123 with inspection.'))
    rec=next(v for v in r['records'] if v['collection']=='jointinspectionreports')
    date=rec['values']['mapping:inspection_failure_date']
    assert date['raw_value']==raw and date['state']==state and date['value']==value
    assert date['precision']=='calendar_day' and not date['timezone_inferred']
    assert rec['fields']['dateOfFailure']==raw


def test_missing_lookup_has_an_actionable_gap_without_description_invention(retrieval):
    x=retrieval;x.reader.rows['tickets'][0]['complaintRecord']['natureOfCustomerComplaint']='unknown-key'
    r=execute(x,preview(x,'Show complaints for engine E123.'))
    v=next(v for v in r['resolved_references'] if v['kind']=='controlled_code')
    assert v['status']=='not_found' and not v['resolved_values']
    g=next(g for g in r['normalized_gaps'] if g['fact_id']=='symptom_description')
    assert g['recovery_action']['id']=='resolve_code' and g['impact']=='optional_supporting_evidence'


def test_timeline_native_link_is_observation_not_verified_completion(retrieval):
    x=retrieval;x.reader.rows['tickettimelines']=[dict(_id='T1',ticketId='C123',stage='CLOSED',description='Source closure explanation',createdAt=datetime(2026,1,3,tzinfo=timezone.utc)),dict(_id='T9',ticketId='C999',stage='CLOSED',description='Unrelated')]
    r=execute(x,preview(x,'Show history for engine E123.'))
    assert {v['fields']['_id'] for v in r['records'] if v['collection']=='tickettimelines'}=={'T1'}
    assert next(q for q in r['evidence_requirements'] if q['fact_id']=='closure_rationale')['state']=='satisfied'
    assert r['physical_engine_identity']=='unresolved' and not r['business_conclusions']
