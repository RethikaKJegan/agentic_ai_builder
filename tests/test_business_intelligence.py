"""Saved-graph intelligence is bounded evidence, never a warranty evaluator."""
from copy import deepcopy
from hashlib import sha256
import json
from unittest.mock import patch

import pytest
from tests.test_business_graph import graph,build,request as graph_request
from tests.test_business_compiler import compiled_draft
from tests.test_business_generation import generation
from tests.test_business_ontology import foundation,auth
from workflow_api.business_compiler import canonical
from workflow_api.business_intelligence import BusinessIntelligence,QUESTIONS,answer
from workflow_api.service import ApiFailure


def req(question='service_path',limit=50,offset=0):return dict(question_id=question,limit=limit,offset=offset)


def test_reports_use_saved_observations_and_never_network_or_policy(graph):
    x=graph;g=build(x);calls=len(x.reader.calls);service=BusinessIntelligence(x.f,x.service)
    with patch('socket.create_connection',side_effect=AssertionError('No network')):
        for qid in QUESTIONS:
            result=service.run(auth(write=False),x.snapshot['version_id'],g['graph_id'],req(qid))
            assert result['company_queries']==result['model_calls']==0 and result['rules_executed'] is False
            assert result['business_policy_verified'] is False
            assert set(result['unavailable_conclusions'].values())<= {'not_evaluated','unavailable'}
            assert result['provenance']['graph_sha256']==sha256(canonical(g).encode()).hexdigest()
            assert len(result['report_sha256'])==64
    assert len(x.reader.calls)==calls
    claims=service.run(auth(),x.snapshot['version_id'],g['graph_id'],req('claim_fields'))
    assert {r['collection'] for r in claims['rows']}=={'claims','claimsftps'}
    assert any(r['state']=='not_returned' for r in claims['rows'])
    assert all(r['record_sha256'] for r in claims['rows'])


def test_literal_status_potential_cause_and_bad_dates_are_not_promoted(graph):
    x=graph;x.reader.rows['claims'][0]['status']='PRIVATE_STATUS_7';x.reader.rows['claims'][0]['reason']='Recorded source reason'
    x.reader.rows['jointinspectionreports'][0]['potentialCause']='Possible gasket issue'
    x.reader.rows['tickets'][0]['createdAt']='not-a-date'
    x.reader.rows['jointinspectionreports'][0]['dateOfFailure']='2026-10-01'
    g=build(x)
    claims=answer(x.snapshot,g,req('claim_fields'))
    status=next(r for r in claims['rows'] if r['field']=='status' and r['collection']=='claims')
    assert status['value']=='PRIVATE_STATUS_7' and 'semantics are not established' in status['qualification']
    inspection=answer(x.snapshot,g,req('inspection_findings'))
    cause=next(r for r in inspection['rows'] if r['field']=='potentialCause')
    assert cause['value']=='Possible gasket issue' and 'not a confirmed root cause' in cause['qualification']
    timeline=answer(x.snapshot,g,req('dated_observations'))
    assert any(r['state']=='invalid_date' and r['value']=='not-a-date' for r in timeline['rows'])
    assert any(r['calendar_date']=='2026-10-01' and r['date_precision']=='date' for r in timeline['rows'])


def test_pages_empty_snapshot_and_qualified_gaps(graph):
    x=graph;g=build(x)
    whole=answer(x.snapshot,g,req('claim_fields'))
    first=answer(x.snapshot,g,req('claim_fields',3));second=answer(x.snapshot,g,req('claim_fields',3,3))
    assert first['has_more'] and first['next_offset']==3 and first['rows']+second['rows']==whole['rows'][:6]
    x.reader.rows['claims']=[];x.reader.rows['claimsftps']=[]
    g2=build(x,{**graph_request(x),'request_key':'second_graph_001'})
    empty=answer(x.snapshot,g2,req('claim_fields'))
    assert empty['result_state']=='no_matching_observations' and empty['total_rows']==0
    assert any('not absence from company' in text for text in empty['limits'])
    gaps=answer(x.snapshot,g2,req('evidence_gaps'));rows=list(gaps['rows'])
    while gaps['has_more']:
        gaps=answer(x.snapshot,g2,req('evidence_gaps',50,gaps['next_offset']));rows+=gaps['rows']
    assert any(r['state']=='shape_violation' for r in rows)
    assert any(r['state']=='definition_question' for r in rows)


@pytest.mark.parametrize('change',[
 {'question_id':'run this arbitrary prompt'}, {'limit':True}, {'limit':51}, {'limit':0}, {'offset':-1}, {'offset':20001}, {'sparql':'SELECT * {}'},
])
def test_bad_report_requests_rejected(graph,change):
    x=graph;g=build(x)
    with pytest.raises(ApiFailure) as exc:answer(x.snapshot,g,{**req(),**change})
    assert exc.value.status==422


@pytest.mark.parametrize('change',['record_hash','edge','version'])
def test_damaged_or_wrong_version_graph_rejected(graph,change):
    x=graph;g=build(x)
    if change=='record_hash':g['records'][0]['fields'][0]['value']='tampered'
    elif change=='edge':g['edges'][0]['source']='foreign'
    else:g['version_id']='foreign'
    with pytest.raises(ApiFailure):answer(x.snapshot,g,req())


def test_historical_and_foreign_graph_scope(graph):
    x=graph;g=build(x);service=BusinessIntelligence(x.f,x.service)
    for foreign in (auth(owner='bob'),auth(workspace='two')):
        with pytest.raises(ApiFailure):service.run(foreign,x.snapshot['version_id'],g['graph_id'],req())
    with x.f.store.transaction() as db:
        db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='quality'",(json.dumps(dict(connection_status='disconnected',metadata_revision=10)),))
    assert service.run(auth(write=False),x.snapshot['version_id'],g['graph_id'],req())['summary']['source_records']==len(g['records'])
