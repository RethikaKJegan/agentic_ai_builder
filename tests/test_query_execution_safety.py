"""Durable-query safety integration; real job store and controlled source reader."""
import json
import pytest
from tests.test_data_query_jobs import jobs, queries, postgres, auth, saved, submit, raw
from workflow_api.service import ApiFailure


def set_policy(jobs, **values):
    from runtime.governance import DEFAULT
    policy = {**DEFAULT, **values}
    with jobs.store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS runtime_governance (workspace TEXT PRIMARY KEY,revision INTEGER,document TEXT)')
        db.execute('INSERT INTO runtime_governance VALUES (?,?,?) ON CONFLICT(workspace) DO UPDATE SET revision=excluded.revision,document=excluded.document', ('one',1,json.dumps(policy)))


def test_queued_query_respects_new_dataset_restriction(jobs):
    item = submit(jobs)
    selected = json.loads(raw(jobs, item['job_id'])['document'])['plan']['base_dataset_id']
    set_policy(jobs, restricted_sources=[selected])
    assert jobs.tick()
    result = jobs.get(auth(), item['job_id'])
    assert result['state'] == 'failed'
    assert result['error']['code'] == 'SOURCE_RESTRICTED'
    assert not jobs.queries.reader.calls


def test_restriction_blocks_cached_query_result(jobs):
    item = submit(jobs)
    assert jobs.tick()
    selected = json.loads(raw(jobs, item['job_id'])['document'])['plan']['base_dataset_id']
    set_policy(jobs, restricted_sources=[selected])
    with pytest.raises(ApiFailure) as failure:
        jobs.result(auth(), item['job_id'])
    assert failure.value.code == 'SOURCE_RESTRICTED'


def test_stopped_parent_prevents_background_query_execution(jobs):
    plan = saved(jobs.queries)
    with jobs.store.transaction() as db:
        db.execute('CREATE TABLE runtime_runs (workspace TEXT,subject TEXT,run_id TEXT,document TEXT)')
        db.execute('INSERT INTO runtime_runs VALUES (?,?,?,?)', ('one','alice','run_parent',json.dumps(dict(status='cancelled',governance_policy={}))))
    item = jobs.submit(auth(), {'plan_id':plan['plan_id']}, 'linked_query_retry', runtime_reference=dict(run_id='run_parent',node_id='query'))
    jobs.tick()
    result = jobs.get(auth(), item['job_id'])
    assert result['state'] == 'cancelled'
    assert not result['result_available']
    assert not jobs.queries.reader.calls
