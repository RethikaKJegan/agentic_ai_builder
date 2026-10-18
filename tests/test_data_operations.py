"""Real disposable-engine CRUD; no connected cloud database is changed."""
import json
import os
import shutil
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from workflow_api.data_operations import DataOperations, validate
from workflow_api.data_operation_tools import registered_grant
from workflow_api.data_source_adapters import CloudAdapters
from workflow_api.data_sources import DataSources
from workflow_api.data_write_adapter import UncertainWrite, RolledBack
from workflow_api.service import ApiFailure
from workflow_api.storage import WorkflowStore


def auth(owner='alice', workspace='one', approve=True):
    return dict(subject=dict(subject_id=owner, workspace_id=workspace), roles=['admin'],
                permissions=['tools.read', 'tools.assign']+(['workflow.approve'] if approve else []),
                scopes=['workspace:read', 'workspace:write'], decision='allow')


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@pytest.fixture(scope='module')
def engines(tmp_path_factory):
    from pymongo import MongoClient
    root = tmp_path_factory.mktemp('crud-engines')
    pg = Path('/usr/lib/postgresql/16/bin')
    assert (pg/'initdb').exists() and shutil.which('mongod'), 'Real CRUD verification requires PostgreSQL 16 and mongod.'
    pgroot, mongoroot = root/'postgres', root/'mongo'
    mongoroot.mkdir()
    port, mongoport = free_port(), free_port()
    subprocess.run([str(pg/'initdb'), '-D', str(pgroot), '--auth=trust', '--no-locale', '--encoding=UTF8'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    subprocess.run([str(pg/'pg_ctl'), '-D', str(pgroot), '-l', str(root/'postgres.log'), '-o', f'-F -p {port} -h 127.0.0.1 -k {root}', '-w', 'start'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    process = None
    try:
        process = subprocess.Popen(['mongod', '--dbpath', str(mongoroot), '--port', str(mongoport), '--bind_ip', '127.0.0.1', '--replSet', 'crud_test', '--logpath', str(root/'mongo.log')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        client = MongoClient(f'mongodb://127.0.0.1:{mongoport}', directConnection=True, serverSelectionTimeoutMS=500, retryWrites=False)
        for _ in range(100):
            try:
                client.admin.command('ping')
                break
            except Exception:
                time.sleep(.1)
        client.admin.command('replSetInitiate', {'_id': 'crud_test', 'members': [{'_id': 0, 'host': f'127.0.0.1:{mongoport}'}]})
        for _ in range(150):
            if client.admin.command('hello')['isWritablePrimary']:
                break
            time.sleep(.1)
        assert client.admin.command('hello')['isWritablePrimary']
        client.close()
        client = MongoClient(f'mongodb://127.0.0.1:{mongoport}/?replicaSet=crud_test', serverSelectionTimeoutMS=5000, retryWrites=False)
        client.admin.command('ping')
        yield dict(dsn=f'host=127.0.0.1 port={port} dbname=postgres user={os.getenv("USER", "raf")}', mongo=client)
    finally:
        if 'client' in locals():
            client.close()
        if process:
            process.terminate()
            process.wait(timeout=20)
        subprocess.run([str(pg/'pg_ctl'), '-D', str(pgroot), '-m', 'immediate', '-w', 'stop'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


@pytest.fixture
def operations(engines, tmp_path):
    import psycopg
    from psycopg import sql
    from bson.decimal128 import Decimal128
    schema, database = 'crud_'+uuid4().hex, 'crud_'+uuid4().hex
    with psycopg.connect(engines['dsn'], autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        conn.execute(sql.SQL('CREATE TABLE {}.records (id text PRIMARY KEY, name text NOT NULL, amount numeric(12,2) DEFAULT 0, enabled boolean NOT NULL DEFAULT true, version integer DEFAULT 1)').format(sql.Identifier(schema)))
        conn.execute(sql.SQL("INSERT INTO {}.records VALUES ('seed','Seed',1,true,1)").format(sql.Identifier(schema)))
    collection = engines['mongo'][database]['records']
    collection.insert_one(dict(_id='seed', name='Seed', amount=Decimal128('1.00'), enabled=True, version=1))

    class LocalCloud:
        @contextmanager
        def connection(self, config):
            if config['engine'] == 'postgresql':
                with psycopg.connect(engines['dsn']) as conn:
                    conn.read_only = True
                    yield conn
            else:
                yield engines['mongo']

    key = tmp_path/'key'
    key.write_bytes(Fernet.generate_key())
    policyfile = tmp_path/'policy.json'
    manager = DataSources(WorkflowStore(tmp_path/'operations.sqlite'),
                          dict(BUILDER_DATA_SOURCE_KEY_FILE=str(key), BUILDER_DATA_WRITE_POLICY_FILE=str(policyfile)), LocalCloud())
    with psycopg.connect(engines['dsn']) as conn:
        snapshot = CloudAdapters.postgres(conn, dict(schemas=[schema], database='postgres'), 'pg')
    pgdataset = snapshot['datasets'][0]
    mongodataset = dict(dataset_id='mongo_records', name='records', database=database, schema=None, kind='collection',
                        fields=[dict(field_id='mongo_'+name, name=name, types=[kind], discovery_method='sampled') for name, kind in
                                [('_id', 'string'), ('name', 'string'), ('amount', 'Decimal128'), ('enabled', 'boolean'), ('version', 'integer')]],
                        indexes=[], constraints=[], sample_count=1, discovery_method='sampled')
    targets = []
    with manager.store.transaction() as db:
        for cid, engine, ds in [('pg', 'postgresql', pgdataset), ('mongo', 'mongodb', mongodataset)]:
            config = dict(engine=engine, database=ds['database'])
            document = dict(connection_id=cid, name=cid, engine=engine, database=ds['database'], connection_status='connected', profiling_status='ready', generation=1, metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)', (cid, 'one', 'alice', manager.cipher.encrypt(json.dumps(config).encode()).decode(), json.dumps(document)))
            db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)', (cid, 1, json.dumps(dict(datasets=[ds]))))
            targets.append(dict(workspace_id='one', subject_id='alice', connection_id=cid, dataset_id=ds['dataset_id'], identity_fields=['id' if cid == 'pg' else '_id'], writable_fields=['name', 'amount', 'enabled', 'version'], operations=['create', 'read', 'update', 'delete']))
    policyfile.write_text(json.dumps(dict(targets=targets)))
    service = DataOperations(manager)
    service.testing = dict(engines=engines, schema=schema, database=database, targets=targets, policyfile=policyfile)
    try:
        yield service
    finally:
        with psycopg.connect(engines['dsn'], autocommit=True) as conn:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
        engines['mongo'].drop_database(database)


def request(operations, engine='pg', action='create', identity='demo', **values):
    target = next(t for t in operations.testing['targets'] if t['connection_id'] == engine)
    return dict(connection_id=engine, dataset_id=target['dataset_id'], action=action,
                identity={target['identity_fields'][0]: identity}, values=values, unset_fields=[])


def prepare(operations, steps, key=None):
    return operations.prepare(auth(), dict(steps=steps), key or uuid4().hex)


def execute(operations, operation):
    return operations.execute(auth(), operation['operation_id'], dict(confirm=True))


def read(operations, engine='pg', identity='demo'):
    step = request(operations, engine, 'read', identity)
    return operations.read(auth(), {k: step[k] for k in ('connection_id', 'dataset_id', 'identity')})['record']


@pytest.mark.parametrize('engine', ['pg', 'mongo'])
def test_real_create_read_update_delete_recovery_and_idempotency(operations, engine):
    prepared = prepare(operations, [request(operations, engine, name='Created', amount='12.50', enabled=True, version=1)])
    assert read(operations, engine) is None
    created = execute(operations, prepared)
    assert created['state'] == 'succeeded' and created['steps'][0]['affected_records'] == 1
    assert execute(operations, prepared)['state'] == 'succeeded'
    assert read(operations, engine)['name'] == 'Created'
    updated = execute(operations, prepare(operations, [request(operations, engine, 'update', name='Updated', amount='15.75')]))
    assert updated['state'] == 'succeeded' and read(operations, engine)['amount'] == '15.75'
    deleted = execute(operations, prepare(operations, [request(operations, engine, 'delete')]))
    assert deleted['state'] == 'succeeded' and read(operations, engine) is None
    recovered = operations.recover(auth(), deleted['operation_id'], uuid4().hex)
    assert read(operations, engine) is None
    assert execute(operations, recovered)['state'] == 'succeeded'
    assert read(operations, engine)['name'] == 'Updated'
    assert operations.recover(auth(), deleted['operation_id'], uuid4().hex)['operation_id'] == recovered['operation_id']
    validate('operation', operations.get(auth(), deleted['operation_id']))


@pytest.mark.parametrize('engine', ['pg', 'mongo'])
def test_optimistic_conflict_rolls_back_and_newer_value_survives(operations, engine):
    old = prepare(operations, [request(operations, engine, 'update', 'seed', name='Old')])
    assert execute(operations, prepare(operations, [request(operations, engine, 'update', 'seed', name='New')]))['state'] == 'succeeded'
    conflict = execute(operations, old)
    assert conflict['state'] == 'failed' and conflict['steps'][0]['error_code'] == 'DATA_WRITE_CONFLICT'
    assert read(operations, engine, 'seed')['name'] == 'New'


def test_cross_database_partial_commit_and_guarded_compensation(operations):
    group = prepare(operations, [request(operations, 'pg', name='PG created'), request(operations, 'mongo', 'update', 'seed', name='Mongo update')])
    execute(operations, prepare(operations, [request(operations, 'mongo', 'update', 'seed', name='External change')]))
    partial = execute(operations, group)
    assert partial['state'] == 'partial' and read(operations, 'pg')['name'] == 'PG created'
    recovery = operations.recover(auth(), group['operation_id'], uuid4().hex)
    assert execute(operations, recovery)['state'] == 'succeeded'
    assert read(operations, 'pg') is None
    assert read(operations, 'mongo', 'seed')['name'] == 'External change'


def test_recovery_does_not_overwrite_changed_committed_record(operations):
    created = execute(operations, prepare(operations, [request(operations, name='Original')]))
    execute(operations, prepare(operations, [request(operations, action='update', name='Changed')]))
    with pytest.raises(ApiFailure) as exc:
        operations.recover(auth(), created['operation_id'], uuid4().hex)
    assert exc.value.code == 'DATA_WRITE_CONFLICT' and read(operations)['name'] == 'Changed'


def test_concurrent_execute_claim_only_invokes_adapter_once(operations):
    prepared = prepare(operations, [request(operations, name='Once')])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: execute(operations, prepared), range(2)))
    assert all(result['state'] in ('running', 'succeeded') for result in results)
    assert read(operations)['name'] == 'Once'
    with operations.store.transaction(write=False) as db:
        assert db.execute("SELECT count(*) FROM data_write_audit WHERE operation_id=? AND state='running'", (prepared['operation_id'],)).fetchone()[0] == 1


def test_unknown_commit_is_never_retried_or_compensated(operations):
    prepared = prepare(operations, [request(operations, name='Unknown')])
    original, calls = operations.adapter.mutate, []
    def unknown(*args):
        calls.append(True)
        original(*args)
        raise UncertainWrite()
    operations.adapter.mutate = unknown
    result = execute(operations, prepared)
    assert result['state'] == 'uncertain' and read(operations)['name'] == 'Unknown'
    assert execute(operations, prepared)['state'] == 'uncertain' and len(calls) == 1
    with pytest.raises(ApiFailure) as exc:
        operations.recover(auth(), prepared['operation_id'], uuid4().hex)
    assert exc.value.code == 'DATA_WRITE_RECOVERY_BLOCKED'


def test_owned_permissions_policy_fields_and_staleness(operations):
    body = dict(steps=[request(operations, name='Protected')])
    for context in (auth(approve=False), auth(owner='bob'), auth(workspace='other')):
        with pytest.raises(ApiFailure):
            operations.prepare(context, body, uuid4().hex)
    with pytest.raises(ApiFailure):
        prepare(operations, [request(operations, action='update', identity='seed', id='replacement')])
    pending = prepare(operations, body['steps'])
    policy = json.loads(operations.testing['policyfile'].read_text())
    policy['targets'][0]['operations'].remove('create')
    operations.testing['policyfile'].write_text(json.dumps(policy))
    assert execute(operations, pending)['state'] == 'failed'
    assert read(operations) is None
    with pytest.raises(ApiFailure) as exc:
        operations.get(auth('bob'), pending['operation_id'])
    assert exc.value.status == 404


def test_encrypted_storage_audit_no_values_and_intent_key_conflict(operations):
    secret_value, key = 'private-business-value-123', uuid4().hex
    pending = operations.prepare(auth(), dict(steps=[request(operations, name=secret_value)]), key)
    assert operations.prepare(auth(), dict(steps=[request(operations, name=secret_value)]), key)['operation_id'] == pending['operation_id']
    with pytest.raises(ApiFailure) as exc:
        operations.prepare(auth(), dict(steps=[request(operations, name='different')]), key)
    assert exc.value.code == 'DATA_WRITE_IDEMPOTENCY_CONFLICT'
    execute(operations, pending)
    with operations.store.transaction(write=False) as db:
        row = db.execute('SELECT secret,summary FROM data_write_operations').fetchone()
        assert secret_value not in row[0]+row[1]
        assert secret_value in operations.manager.cipher.decrypt(row[0].encode()).decode()
        assert secret_value not in str(db.execute('SELECT * FROM data_write_audit').fetchall())


def test_registered_binding_is_exact_and_approval_is_real():
    grant = registered_grant(auth(), 'postgresql', 'update', 'source', 'dataset', 'dbop_'+uuid4().hex, 0)
    assert grant['authorization_state'] == 'authorized' and grant['approval_reference']
    assert grant['destination'] == 'dataset' and grant['input_schema']['properties']['step_index'] == {'const': 0}
    with pytest.raises(ApiFailure):
        registered_grant(auth(approve=False), 'postgresql', 'update', 'source', 'dataset', 'dbop_'+uuid4().hex, 0)


def test_native_mongo_transaction_diagnostics(operations):
    step = request(operations, 'mongo', name='Native', amount='12.50', enabled=True, version=1)
    context = operations.context(auth(), step)
    try:
        result = operations.adapter.mutate(context['config'], context['dataset'], context['target'], step, None, lambda: None)
    except RolledBack as exc:
        pytest.fail(f'Isolated Mongo adapter failed: {type(exc.__context__).__name__}: {exc.__context__}')
    assert result['affected_records'] == 1


@pytest.mark.parametrize('engine', ['pg', 'mongo'])
def test_current_authority_revocation_before_commit_rolls_back(operations, engine):
    pending = prepare(operations, [request(operations, engine, name='Revoked')])
    calls = []
    def resolve(workspace, owner):
        calls.append(True)
        return auth(approve=len(calls) < 4)
    operations.resolve = resolve
    result = execute(operations, pending)
    assert result['state'] == 'failed'
    assert read(operations, engine) is None


def test_publication_loss_after_commit_is_not_replayed(operations):
    pending = prepare(operations, [request(operations, name='Committed but unacknowledged')])
    original = operations.audit
    def audit(db, context, operation_id, index, step):
        if step['state'] == 'succeeded' and operation_id == pending['operation_id']:
            raise RuntimeError('Synthetic publication crash')
        return original(db, context, operation_id, index, step)
    operations.audit = audit
    with pytest.raises(RuntimeError):
        execute(operations, pending)
    assert read(operations)['name'] == 'Committed but unacknowledged'
    with operations.store.transaction() as db:
        db.execute('UPDATE data_write_operations SET started=? WHERE operation_id=?', (time.time()-181, pending['operation_id']))
    assert operations.get(auth(), pending['operation_id'])['state'] == 'uncertain'
    assert execute(operations, pending)['state'] == 'uncertain'


@pytest.mark.parametrize('engine', ['pg', 'mongo'])
def test_update_recovery_and_noop_counts(operations, engine):
    changed = execute(operations, prepare(operations, [request(operations, engine, 'update', 'seed', name='Changed')]))
    recovery = operations.recover(auth(), changed['operation_id'], uuid4().hex)
    assert execute(operations, recovery)['state'] == 'succeeded'
    assert read(operations, engine, 'seed')['name'] == 'Seed'
    noop = execute(operations, prepare(operations, [request(operations, engine, 'update', 'seed', name='Seed')]))
    assert noop['steps'][0]['matched_records'] == 1 and noop['steps'][0]['affected_records'] == 0
    with pytest.raises(ApiFailure):
        operations.recover(auth(), noop['operation_id'], uuid4().hex)


def test_postgres_value_rounding_is_rejected_before_commit(operations):
    result = execute(operations, prepare(operations, [request(operations, name='Precision', amount='12.345')]))
    assert result['state'] == 'failed' and result['steps'][0]['error_code'] == 'DATA_WRITE_COERCION'
    assert read(operations) is None


def test_logical_expiry_and_invalid_policy_fail_closed(operations):
    pending = prepare(operations, [request(operations, name='Expired')])
    with operations.store.transaction() as db:
        row = operations.row(db, auth(), pending['operation_id'])
        summary = json.loads(row[2]); summary['expires_at'] = time.time()-1
        db.execute('UPDATE data_write_operations SET summary=? WHERE operation_id=?', (json.dumps(summary), pending['operation_id']))
    with pytest.raises(ApiFailure) as exc:
        execute(operations, pending)
    assert exc.value.code == 'DATA_WRITE_EXPIRED' and read(operations) is None
    operations.testing['policyfile'].write_text('{malformed')
    with pytest.raises(ApiFailure) as exc:
        prepare(operations, [request(operations, name='Denied')])
    assert exc.value.code == 'DATA_WRITE_SETUP_REQUIRED'


def test_http_review_execution_and_origin_protection(operations, tmp_path):
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app, COOKIE
    with patch('workflow_api.data_source_routes.DataSources', return_value=operations.manager):
        app = create_app(database=tmp_path/'http.sqlite', dev_auth=True, roles=['admin'], start_workers=False, planning_worker_enabled=False)
    with TestClient(app) as client:
        session = client.get('/session')
        client.cookies.set(COOKIE, session.cookies[COOKIE], path='/')
        app.state.workflow_auth = auth()
        body = dict(steps=[request(operations, name='HTTP')])
        response = client.post('/data-operations/prepare', json=body, headers={'Origin':'https://foreign.example','Idempotency-Key':uuid4().hex})
        assert response.status_code == 403
        headers = {'Origin':'http://localhost:3000','Idempotency-Key':uuid4().hex}
        response = client.post('/data-operations/prepare', json=body, headers=headers)
        assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
        pending = response.json()['data']; validate('operation', pending)
        assert read(operations) is None
        operation_id = pending['operation_id']
        assert client.post(f'/data-operations/{operation_id}/execute', json={'confirm':False}, headers=headers).status_code == 400
        response = client.post(f'/data-operations/{operation_id}/execute', json={'confirm':True}, headers=headers)
        assert response.status_code == 200 and response.json()['data']['state'] == 'succeeded'
        assert read(operations)['name'] == 'HTTP'
        status = client.get('/data-operations')
        assert status.status_code == 200
        validate('status', status.json()['data'])


def test_delete_cascades_and_user_triggers_are_rejected(operations):
    import psycopg
    from psycopg import sql
    schema=operations.testing['schema']
    with psycopg.connect(operations.testing['engines']['dsn'],autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE TABLE {}.children (id text PRIMARY KEY, parent text REFERENCES {}.records(id) ON DELETE CASCADE)').format(sql.Identifier(schema),sql.Identifier(schema)))
        conn.execute(sql.SQL("INSERT INTO {}.children VALUES ('child','seed')").format(sql.Identifier(schema)))
    with pytest.raises(ApiFailure):
        prepare(operations,[request(operations,action='delete',identity='seed')])
    assert read(operations,identity='seed')['name']=='Seed'
    with psycopg.connect(operations.testing['engines']['dsn'],autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE FUNCTION {}.write_trigger() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$').format(sql.Identifier(schema)))
        conn.execute(sql.SQL('CREATE TRIGGER controlled_test BEFORE UPDATE ON {}.records FOR EACH ROW EXECUTE FUNCTION {}.write_trigger()').format(sql.Identifier(schema),sql.Identifier(schema)))
    with pytest.raises(ApiFailure):
        prepare(operations,[request(operations,action='update',identity='seed',name='Denied')])


def test_recovery_expiry_is_enforced_even_before_cleanup(operations):
    created=execute(operations,prepare(operations,[request(operations,name='Retained')]))
    with operations.store.transaction() as db:
        row=operations.row(db,auth(),created['operation_id'])
        summary=json.loads(row[2]);summary['recovery_until']=time.time()-1
        db.execute('UPDATE data_write_operations SET summary=? WHERE operation_id=?',(json.dumps(summary),created['operation_id']))
    with pytest.raises(ApiFailure) as exc:
        operations.recover(auth(),created['operation_id'],uuid4().hex)
    assert exc.value.code=='DATA_WRITE_EXPIRED'
    assert read(operations)['name']=='Retained'


@pytest.mark.parametrize('engine',['pg','mongo'])
def test_identity_injection_is_data_and_operators_are_rejected(operations,engine):
    identity="demo'); DROP TABLE records; --"
    result=execute(operations,prepare(operations,[request(operations,engine,identity=identity,name='Literal')]))
    assert result['state']=='succeeded' and read(operations,engine,identity)['name']=='Literal'
    assert read(operations,engine,'seed')['name']=='Seed'
    body=request(operations,engine,identity={'$ne':None},name='Invalid')
    with pytest.raises(ApiFailure):
        prepare(operations,[body])


def test_real_postgres_operation_journal_and_reconstruction(operations):
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict
    from urllib.parse import urlencode
    schema='ledger_'+uuid4().hex
    config=conninfo_to_dict(operations.testing['engines']['dsn'])
    with psycopg.connect(operations.testing['engines']['dsn'],autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    url=f"postgresql://{config['user']}@127.0.0.1:{config['port']}/postgres?"+urlencode({'options':'-csearch_path='+schema})
    try:
        store=WorkflowStore(url)
        manager=DataSources(store,operations.env,operations.manager.adapter)
        with operations.store.transaction(write=False) as source,store.transaction() as target:
            for row in source.execute('SELECT * FROM data_source_connections').fetchall():
                target.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',row)
            for row in source.execute('SELECT * FROM data_source_snapshots').fetchall():
                target.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',row)
        fresh=DataOperations(manager)
        prepared=fresh.prepare(auth(),dict(steps=[request(operations,name='PG ledger')]),uuid4().hex)
        result=fresh.execute(auth(),prepared['operation_id'],dict(confirm=True))
        assert result['state']=='succeeded'
        restored=DataOperations(manager).get(auth(),prepared['operation_id'])
        assert restored['state']=='succeeded' and restored['steps'][0]['affected_records']==1
        assert read(operations)['name']=='PG ledger'
    finally:
        with psycopg.connect(operations.testing['engines']['dsn'],autocommit=True) as conn:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


@pytest.mark.parametrize('conflict',[False,True])
def test_two_source_recovery_is_guarded_and_can_itself_be_partial(operations,conflict):
    group=execute(operations,prepare(operations,[request(operations,'pg',name='PG'),request(operations,'mongo',name='Mongo')]))
    assert group['state']=='succeeded'
    recovery=operations.recover(auth(),group['operation_id'],uuid4().hex)
    assert [step['connection_id'] for step in recovery['steps']]==['mongo','pg']
    if conflict:
        execute(operations,prepare(operations,[request(operations,'pg','update',name='Newer')]))
    result=execute(operations,recovery)
    assert result['state']==('partial' if conflict else 'succeeded')
    assert read(operations,'mongo') is None
    assert (read(operations,'pg') or {}).get('name')==('Newer' if conflict else None)
    if conflict:
        with pytest.raises(ApiFailure):
            operations.recover(auth(),recovery['operation_id'],uuid4().hex)


def test_mongo_recovery_preserves_missing_instead_of_null(operations):
    collection=operations.testing['engines']['mongo'][operations.testing['database']]['records']
    collection.update_one({'_id':'seed'},{'$unset':{'version':''}})
    updated=execute(operations,prepare(operations,[request(operations,'mongo','update','seed',version=2)]))
    assert updated['state']=='succeeded' and read(operations,'mongo','seed')['version']==2
    inverse=operations.recover(auth(),updated['operation_id'],uuid4().hex)
    assert inverse['steps'][0]['unset_fields']==['version']
    assert execute(operations,inverse)['state']=='succeeded'
    assert 'version' not in read(operations,'mongo','seed')


def test_postgres_schema_write_lock_blocks_trigger_race(operations):
    import psycopg
    from psycopg import sql
    schema=operations.testing['schema']
    with psycopg.connect(operations.testing['engines']['dsn'],autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE FUNCTION {}.race_trigger() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$').format(sql.Identifier(schema)))
    pending=prepare(operations,[request(operations,name='DDL guarded')])
    original=operations.adapter.check_table
    attempts=[]
    def check(conn,dataset,target,action):
        original(conn,dataset,target,action)
        if action!='read':
            with psycopg.connect(operations.testing['engines']['dsn'],autocommit=True) as other:
                other.execute("SET lock_timeout='100ms'")
                with pytest.raises(psycopg.errors.LockNotAvailable):
                    other.execute(sql.SQL('CREATE TRIGGER racing_trigger BEFORE INSERT ON {}.records FOR EACH ROW EXECUTE FUNCTION {}.race_trigger()').format(sql.Identifier(schema),sql.Identifier(schema)))
                attempts.append(True)
    operations.adapter.check_table=check
    assert execute(operations,pending)['state']=='succeeded'
    assert attempts==[True] and read(operations)['name']=='DDL guarded'


def test_database_account_privileges_are_not_overridden_by_application_grants(operations):
    import psycopg
    from psycopg import sql
    role='crud_role_'+uuid4().hex
    schema=operations.testing['schema']
    dsn=operations.testing['engines']['dsn']
    with psycopg.connect(dsn,autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE ROLE {} LOGIN').format(sql.Identifier(role)))
        conn.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(schema),sql.Identifier(role)))
        conn.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE ON {}.records TO {}').format(sql.Identifier(schema),sql.Identifier(role)))
    class RestrictedCloud:
        @contextmanager
        def connection(self,config):
            with psycopg.connect(dsn,user=role) as conn:
                conn.read_only=True
                yield conn
    operations.adapter.cloud=RestrictedCloud()
    try:
        created=execute(operations,prepare(operations,[request(operations,name='Insert permitted')]))
        assert created['state']=='succeeded'
        denied=execute(operations,prepare(operations,[request(operations,action='delete')]))
        assert denied['state']=='failed'
        assert read(operations)['name']=='Insert permitted'
    finally:
        with psycopg.connect(dsn,autocommit=True) as conn:
            conn.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
            conn.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
