"""Run the ontology acceptance suite against the existing PostgreSQL adapter."""
from urllib.parse import urlencode
from uuid import uuid4
import json
import pytest
from tests.test_postgres_backend import test_dsn
from tests.test_data_relationships import sources
from tests import test_ontology_foundation as checks
from workflow_api.storage import WorkflowStore
from workflow_api.data_sources import DataSources

@pytest.fixture
def foundation():
    psycopg=pytest.importorskip('psycopg');from psycopg import sql
    dsn=test_dsn();schema='ontology_'+uuid4().hex
    with psycopg.connect(dsn,autocommit=True) as db:db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    try:
        store=WorkflowStore(dsn+('&' if '?' in dsn else '?')+urlencode({'options':'-csearch_path='+schema}))
        manager=DataSources(store,{})
        with store.transaction() as db:
            for source in sources():
                c=source['connection'];db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(c['connection_id'],'one','alice','encrypted',json.dumps(c)))
                db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(c['connection_id'],1,json.dumps(source['snapshot'])))
        yield manager.ontology_foundation
    finally:
        with psycopg.connect(dsn,autocommit=True) as db:db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))

@pytest.mark.parametrize('check',[value for name,value in vars(checks).items() if name.startswith('test_') and 'foundation' in __import__('inspect').signature(value).parameters])
def test_postgres_ontology(foundation,check):check(foundation)


def test_real_postgres_readonly_value_profile():
    psycopg=pytest.importorskip('psycopg');from psycopg import sql
    from workflow_api.data_source_adapters import CloudAdapters
    from workflow_api.data_profiles import token
    dsn=test_dsn();schema='profile_'+uuid4().hex
    with psycopg.connect(dsn,autocommit=True) as db:
        db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        db.execute(sql.SQL('CREATE TABLE {}.sample (tenant INTEGER, id INTEGER, value TEXT, PRIMARY KEY(tenant,id))').format(sql.Identifier(schema)))
        db.execute(sql.SQL("INSERT INTO {}.sample VALUES (1,1,NULL),(1,2,'x'),(2,1,'x')").format(sql.Identifier(schema)))
    try:
        with psycopg.connect(dsn) as db:
            db.read_only=True
            result=CloudAdapters.postgres(db,dict(database='ontology_utf8',schemas=[schema],_ontology_profile=True),'test')
        dataset=result['datasets'][0];profile=result['ontology_profiles'][dataset['dataset_id']]
        value=next(f for f in dataset['fields'] if f['name']=='value')
        assert profile['fields'][value['field_id']]['null_rate']==pytest.approx(1/3)
        assert profile['composite_keys'][0]['comparable']==3
        assert 'x' not in json.dumps(profile) and token('x') in json.dumps(profile)
        assert dataset['sample_count']==0 and 'value_profiles' not in dataset
    finally:
        with psycopg.connect(dsn,autocommit=True) as db:db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
