"""Finalization uses validated business findings and durable connector receipts."""
from copy import deepcopy
import pytest
from runtime.service import RuntimeFailure,digest
from workflow_api.workflow_adaptive import finalize_verified_actions,evidence
from tests.test_subway_autonomy import subway,engine,installed,start,decision,drain


def completed(f):
    calls=[]
    def evaluate(ctx,**_):
        calls.append(ctx)
        assert not all(a['action_id'] in ctx['completed_actions'] for a in ctx['plan']['actions']), 'A completed execution must not need a new model decision'
        result=decision(ctx)
        valid=[key for key,item in ctx['evidence'].items() if item['valid']]
        if valid:
            result['assessment']['requirements'][0].update(status='verified',evidence_ids=valid)
            result['assessment'].update(completion_eligible=True,gaps=[])
        return result
    rid,_,workflow=start(f,evaluate)
    run=drain(f,rid)
    assert run['status']=='completed' and run['adaptive']['status']=='completed'
    assert len(calls)==3
    assert run['adaptive']['decisions'][-1]['completion_basis']=='verified_action_receipts'
    return run,workflow


def test_business_ready_execution_finishes_without_post_execution_model_call(subway):
    completed(subway)


@pytest.mark.parametrize('mutation',['fingerprint','unverified_receipt','source_evidence','not_ready','unfinished'])
def test_finalization_does_not_bypass_receipts_evidence_or_unfinished_work(subway,mutation,monkeypatch):
    import workflow_api.workflow_adaptive as adaptive
    f=subway;run,workflow=completed(f);run=deepcopy(run)
    run['adaptive']['status']='active'
    if mutation=='fingerprint':run['action_instances']['report']['output']['summary']='changed'
    if mutation=='unverified_receipt':run['action_instances']['read']['verified_receipt']=False
    if mutation=='source_evidence':
        original=adaptive.evidence
        def revoked(*args):
            ev,limits=original(*args)
            for item in ev.values():item['valid']=False
            return ev,limits
        monkeypatch.setattr(adaptive,'evidence',revoked)
    if mutation=='not_ready':run['adaptive']['assessment']['completion_eligible']=False
    if mutation=='unfinished':run['action_instances']['report']['state']='pending'
    with f.service.store.transaction() as db:
        if mutation in ('not_ready','unfinished'):
            assert not finalize_verified_actions(f.service.runtime_runner.runtime,db,run,workflow,f.auth)
        else:
            with pytest.raises(RuntimeFailure):finalize_verified_actions(f.service.runtime_runner.runtime,db,run,workflow,f.auth)
    assert run['adaptive']['status']=='active'


def test_delivery_receipt_is_separate_from_business_evidence(subway):
    f=subway;run,workflow=completed(f);workflow=deepcopy(workflow);run=deepcopy(run)
    workflow['metadata']['connected_action_plan']['actions'].append(dict(action_id='delivery',capability_id='test.delivery'))
    workflow['metadata']['connected_contracts']['test.delivery']=dict(side_effect='write')
    output=dict(message_id='synthetic-confirmed-message')
    run['action_instances']['delivery']=dict(state='completed',verified_receipt=True,output=output,output_fingerprint=digest(output))
    with f.service.store.transaction() as db:
        ev,limits=evidence(f.service.runtime_runner.runtime,db,run,workflow,f.auth)
    assert ev and all(item['valid'] and item['action_id']!='delivery' for item in ev.values())
    assert not any(item['action_id']=='delivery' for item in limits)


@pytest.mark.parametrize('verified',[True,False])
def test_mail_finalization_requires_confirmed_receipt_and_never_replays_delivery(subway,verified):
    f=subway;run,workflow=completed(f);workflow=deepcopy(workflow);run=deepcopy(run)
    run['adaptive']['status']='active'
    plan=workflow['metadata']['connected_action_plan']
    plan['actions'].append(dict(action_id='delivery',capability_id='test.delivery'))
    plan['completion_criteria']=['delivery']
    workflow['metadata']['connected_contracts']['test.delivery']=dict(side_effect='write')
    output=dict(message_id='synthetic-confirmed-message',thread_id='synthetic-thread')
    run['action_instances']['delivery']=dict(state='completed',verified_receipt=verified,output=output,output_fingerprint=digest(output))
    with f.service.store.transaction() as db:
        if not verified:
            with pytest.raises(RuntimeFailure):finalize_verified_actions(f.service.runtime_runner.runtime,db,run,workflow,f.auth)
        else:
            assert finalize_verified_actions(f.service.runtime_runner.runtime,db,run,workflow,f.auth)
            count=len(run['adaptive']['decisions'])
            assert finalize_verified_actions(f.service.runtime_runner.runtime,db,run,workflow,f.auth)
            assert len(run['adaptive']['decisions'])==count
    assert run['action_instances']['delivery']['output']==output
