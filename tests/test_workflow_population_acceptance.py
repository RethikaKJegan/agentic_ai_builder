"""Two customer metadata fixtures, one query engine; controlled model proposals."""
from decimal import Decimal
import json
import pytest
from cryptography.fernet import Fernet

from tests.test_data_relationships import auth,dataset
from workflow_api.data_sources import DataSources
from workflow_api.data_queries import DataQueries
from workflow_api.data_query_jobs import DataQueryJobs
from workflow_api.storage import WorkflowStore
from workflow_api.workflow_queries import WorkflowQueries,QueryPending

@pytest.fixture(params=[('simpson','complaints','operating_hours'),('subway','purchase_orders','total_amount')])
def population(request,tmp_path):
    customer,entity,measure=request.param
    authority=auth(workspace=customer)
    key=tmp_path/'population.key';key.write_bytes(Fernet.generate_key())
    manager=DataSources(WorkflowStore(tmp_path/'population.sqlite'),{'BUILDER_DATA_SOURCE_KEY_FILE':str(key)})
    ds=dataset('source',entity,[(measure,['numeric'])],'business')
    with manager.store.transaction() as db:
        document=dict(connection_id='source',name=entity,engine='postgresql',connection_status='connected',metadata_revision=1,generation=1)
        secret=manager.cipher.encrypt(json.dumps({'engine':'postgresql'}).encode()).decode()
        db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',('source',customer,'alice',secret,json.dumps(document)))
        db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',('source',1,json.dumps(dict(revision=1,coverage='declared',warnings=[],datasets=[ds]))))
    manager.relationships.request(authority);assert manager.relationships.tick()
    values=[Decimal(i%151) for i in range(602)]+[None]
    fid=ds['fields'][0]['field_id']
    class Reader:
        def read(self,*args):return [{fid:v} for v in values],10000
    q=DataQueries(manager,reader=Reader())
    jobs=DataQueryJobs(q,lambda w,o:authority if (w,o)==(customer,'alice') else None)
    catalog=q.catalogue(authority)
    c=WorkflowQueries(q,jobs).bind_context({'metadata':{'action_binding_context':{'validated_context':{'data_query_catalog':catalog}}}},{},authority,{})
    return c,entity,measure,ds['dataset_id'],fid,values

@pytest.mark.parametrize('operation',['count','min','max','avg','sum'])
def test_five_controlled_natural_language_acceptance_patterns(population,operation):
    c,entity,measure,did,fid,values=population
    goal=f'Find {entity} with {measure} from 0 to 100 inclusive and calculate {operation}.'
    query=dict(base_dataset_id=did,joins=[],fields=[],filters=[dict(field_id=fid,op='gte',value=0),dict(field_id=fid,op='lte',value=100)],group_by=[],metrics=[dict(label='value',op=operation,expression=fid)],order_by=[],limit=1,explanation=goal,clarification='')
    # Independent expected values include records beyond display row 500.
    matched=[v for v in values if v is not None and 0<=v<=100]
    expected={'count':len(matched),'min':min(matched),'max':max(matched),'avg':sum(matched)/len(matched),'sum':sum(matched)}[operation]
    with pytest.raises(QueryPending):c.invoke({'tool_id':'workflow_data_query'},{'query':query},goal)
    assert c.jobs.tick()
    result=c.invoke({'tool_id':'workflow_data_query'},{'query':query},goal)
    assert Decimal(str(result['result']['rows'][0]['value']))==Decimal(str(expected))
    assert result['result']['matched_rows']==len(matched)
    assert result['coverage']['aggregate_complete'] and result['coverage']['returned_rows']==1
