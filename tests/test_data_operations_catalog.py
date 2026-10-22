"""Catalog regressions use a disposable local store and never contact a database."""
import json
import pytest
from cryptography.fernet import Fernet
from workflow_api.data_sources import DataSources
from workflow_api.data_operations import DataOperations
from workflow_api.storage import WorkflowStore
from workflow_api.service import ApiFailure


def authority():
    return dict(subject=dict(workspace_id='one', subject_id='alice'), decision='allow',
                permissions=['tools.read', 'tools.assign', 'workflow.approve'], roles=['admin'],
                scopes=['workspace:read', 'workspace:write'])


@pytest.fixture
def catalog(tmp_path):
    key = tmp_path/'key'; key.write_bytes(Fernet.generate_key())
    manager = DataSources(WorkflowStore(tmp_path/'store.sqlite'), dict(BUILDER_DATA_SOURCE_KEY_FILE=str(key)))
    service = DataOperations(manager)
    target = dict(workspace_id='one', subject_id='alice', connection_id='current', dataset_id='records',
                  identity_fields=['id'], writable_fields=['name'], operations=['read', 'update'])
    dataset = dict(dataset_id='records', name='records', database='test', schema='public')
    with manager.store.transaction() as db:
        for cid, owner, state in [('current', 'alice', 'connected'), ('foreign', 'bob', 'connected'), ('offline', 'alice', 'disconnected')]:
            document = dict(connection_id=cid, name=cid, engine='postgresql', connection_status=state, metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)', (cid, 'one', owner, '', json.dumps(document)))
            db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)', (cid, 1, json.dumps(dict(datasets=[dataset]))))
    return service, target


def test_stale_and_unowned_entries_do_not_hide_valid_targets(catalog, monkeypatch):
    service, target = catalog
    monkeypatch.setattr(service, 'policy', lambda: {'targets': [{**target, 'connection_id': cid} for cid in ['removed', 'foreign', 'offline', 'current']]})
    result = service.status(authority())
    assert result['configured'] is True
    assert [(t['connection_id'], t['operations']) for t in result['targets']] == [('current', ['read', 'update'])]


def test_all_removed_entries_return_empty_catalog(catalog, monkeypatch):
    service, target = catalog
    monkeypatch.setattr(service, 'policy', lambda: {'targets': [{**target, 'connection_id': 'removed'}]})
    assert service.status(authority())['targets'] == []
    with pytest.raises(ApiFailure) as failure:
        service.context(authority(), dict(connection_id='removed', dataset_id='records', action='read'))
    assert failure.value.code == 'DATA_SOURCE_NOT_FOUND'
    with pytest.raises(ApiFailure) as failure:
        service.context(authority(), dict(connection_id='current', dataset_id='records', action='read'))
    assert failure.value.code == 'DATA_WRITE_TARGET_DENIED'


def test_unrelated_errors_are_not_suppressed(catalog, monkeypatch):
    service, target = catalog
    monkeypatch.setattr(service, 'policy', lambda: {'targets': [target]})
    def unavailable(*args):
        raise ApiFailure('DATA_SOURCE_UNAVAILABLE', 'Unavailable', 503)
    monkeypatch.setattr(service.manager, 'owned', unavailable)
    with pytest.raises(ApiFailure) as failure:
        service.status(authority())
    assert failure.value.code == 'DATA_SOURCE_UNAVAILABLE'
