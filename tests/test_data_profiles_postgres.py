"""Native PostgreSQL source statistics; no cloud or model calls."""
from uuid import uuid4
import json
import pytest
from tests.test_postgres_backend import test_dsn

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
