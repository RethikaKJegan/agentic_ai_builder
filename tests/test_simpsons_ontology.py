"""Offline descriptive ontology checks, not Simpsons business approval."""
import json
import sqlite3

import pytest

from scripts import build_simpsons_ontology as builder
from tests.test_data_relationships import dataset
from workflow_api.data_sources import DataSources
from workflow_api.ontology_model import graph_errors, select_concepts
from workflow_api.service import ApiFailure
from workflow_api.storage import WorkflowStore


@pytest.fixture
def catalogue():
    definitions=json.loads((builder.DEFINITIONS/'definitions.json').read_text())
    bindings=json.loads((builder.DEFINITIONS/'field-bindings.json').read_text())
    result={}
    for slug,(collection,*_) in definitions['concepts'].items():
        if not collection:continue
        names=set(bindings.get(slug,{}))|{'_id'}
        # Deliberately absent code-reported fields exercise unresolved bindings.
        names-={'engineReplacementStatus','cutInNumber'} if collection=='tickets' else set()
        item=dataset('fixture',collection,[(name,['string']) for name in sorted(names)])
        item['connection_id']='fixture'
        result[collection]=item
    result['enginedetails']['indexes']=[dict(unique=True,columns=[dict(name='oem'),dict(name='engineSerialNumber')])]
    return result


@pytest.fixture
def draft(catalogue):
    return builder.Draft(catalogue,builder.evidence()).construct()


def test_native_graph_keeps_code_evidence_unapproved(draft):
    assert not graph_errors(draft.records)
    assert {r['layer'] for r in draft.records}=={'common','domain','organization'}
    assert all(r['evidence_class']=='unverified_hypothesis' for r in draft.records)
    assert all(not p['business_policy_approved'] and not p['independent_code_verification'] for p in draft.provenance.values())
    assert all(len(p['review_evidence'])==2 for p in draft.provenance.values())
    assert len({r['id'] for r in draft.records})==len(draft.records)


def test_invoice_company_and_text_ticket_links_are_distinct(draft):
    relationships=[r for r in draft.records if r['kind']=='relationship']
    invoice_links=[r for r in relationships if r['properties']['source']==builder.cid('engine_invoice')]
    assert any(r['properties']['target']==builder.cid('oem_company') for r in invoice_links)
    assert not any(r['properties']['target']==builder.cid('oem_account') for r in invoice_links)
    ticket_invoice=next(r for r in relationships if r['properties']['source']==builder.cid('ticket') and r['properties']['target']==builder.cid('engine_invoice'))
    assert 'text' in draft.provenance[ticket_invoice['id']]['reference_kind']
    assert draft.provenance[ticket_invoice['id']]['join_authorized'] is False
    assert any(g['collection']=='tickets' and g['field']=='engineReplacementStatus' for g in draft.gaps)
    attr=next(r for r in draft.records if r['id']=='simpsons:attribute:ticket:engineReplacementStatus')
    assert attr['source_refs']==[] and attr['properties']['datatype']=='unknown'


def test_known_application_defects_do_not_become_invariants(draft):
    p=draft.provenance
    assert p['simpsons:constraint:open_ticket_attempt']['rule_payload']['guaranteed'] is False
    warranty=p['simpsons:constraint:warranty_code_only']['rule_payload']
    assert warranty['operators'] is None and warranty['executable'] is False
    stages=p['simpsons:constraint:stage_categories']['rule_payload']
    assert [len(stages[k]) for k in ('workflow_labels','timeline_only','unused')]==[14,11,2]
    assert not stages['transition_policy_complete']


def test_previews_are_bounded_and_do_not_select_unrelated_training(draft):
    previews=builder.question_previews(draft)
    assert len(previews)==3
    for preview in previews:
        assert 0<preview['record_count']<=200
        assert not preview['execution_ready'] and preview['preview_only']
        assert preview['records_retrieved']==0 and not preview['workflow_executed']
        assert builder.cid('booking') not in preview['record_ids']
        chosen=[r for r in draft.records if r['id'] in preview['record_ids']]
        assert not graph_errors(chosen)
    assert any(g['field']=='engineReplacementStatus' for g in previews[1]['mapping_gaps'])


def test_shared_domain_dependency_does_not_expand_to_sibling_concepts(draft):
    chosen=select_concepts(draft.records,[builder.cid('jir')])
    ids={r['id'] for r in chosen}
    assert builder.cid('jir') in ids and builder.cid('foc') not in ids
    domain=next(r['properties']['target'] for r in chosen if r['kind']=='mapping')
    # Explicit domain queries still include their organization mappings.
    assert builder.cid('foc') in {r['id'] for r in select_concepts(draft.records,[domain])}
    with pytest.raises(ApiFailure) as error:select_concepts(draft.records,[builder.cid('jir')],limit=1)
    assert error.value.code=='ONTOLOGY_SELECTION_LIMIT'
    chosen[0]['label']='modified copy'
    assert all(r['label']!='modified copy' for r in draft.records)


def test_missing_compound_index_is_a_blocker(catalogue):
    catalogue['enginedetails']['indexes']=[]
    with pytest.raises(ValueError,match='compound-index'):
        builder.Draft(catalogue,builder.evidence()).construct()


@pytest.mark.parametrize('with_technical_evidence',[False,True])
def test_build_isolated_database_without_credentials_or_live_database(tmp_path,monkeypatch,catalogue,with_technical_evidence):
    source=tmp_path/'saved.sqlite3'
    manager=DataSources(WorkflowStore(source),{},adapter=builder.OfflineAdapter())
    connection=dict(connection_id='fixture',name='Simpsons fixture',connection_status='connected',metadata_revision=1,generation=1)
    snapshot=dict(revision=1,coverage='sampled',datasets=list(catalogue.values()))
    with manager.store.transaction() as db:
        db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',('fixture',*builder.SCOPE,'fixture-secret-must-not-copy',json.dumps(connection)))
        db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',('fixture',1,json.dumps(snapshot)))
    monkeypatch.setattr(builder,'ROOT',tmp_path)
    live=tmp_path/'.local/workflows.sqlite3';live.parent.mkdir();live.write_bytes(b'untouched live sentinel')
    connect=sqlite3.connect
    def guarded_connect(path,*args,**kwargs):
        assert str(live) not in str(path),'Live database must not be opened.'
        return connect(path,*args,**kwargs)
    monkeypatch.setattr(sqlite3,'connect',guarded_connect)
    target=tmp_path/'.local/ontology-foundation/draft.sqlite3';output=tmp_path/'artifacts'
    before=builder.digest(source)
    verification=None
    if with_technical_evidence:
        verification=tmp_path/'probe.json'
        verification.write_text(json.dumps(dict(business_policy_approved=False,source_writes=0,ontology_published=False,
            checked_at='2026-10-30T00:00:00+00:00',method='fixture_only',fields=[dict(collection='tickets',field='engineReplacementStatus',
            status='observed_field',matching_sample_count=2,observed_bson_types=['string'])])))
    report=builder.build(source,target,output,verification)
    assert report['technically_verified_bindings']==int(with_technical_evidence)
    assert builder.digest(source)==before
    assert live.read_bytes()==b'untouched live sentinel'
    assert report['company_reads']==report['company_writes']==report['approved_records']==report['published_versions']==0
    assert report['approved_api_rejects_draft'] and not report['credentials_copied']
    with sqlite3.connect(target) as db:
        assert db.execute('SELECT count(*) FROM data_source_connections WHERE secret IS NOT NULL').fetchone()[0]==0
        records=[json.loads(r[0]) for r in db.execute('SELECT document FROM ontology_records')]
        assert records and all(r['status']=='draft' for r in records)
        if with_technical_evidence:
            attr=next(r for r in records if r['id']=='simpsons:attribute:ticket:engineReplacementStatus')
            assert attr['properties']['datatype']=='string' and len(attr['source_refs'])==1
            exported=json.loads((output/'ontology.json').read_text())
            proof=exported['provenance'][attr['id']]['technical_verification']
            assert proof['sha256']==builder.digest(verification)
            assert not proof['business_policy_approved'] and not proof['reference_target_verified']
            assert db.execute('SELECT revision FROM data_source_snapshots').fetchone()[0]==2
    assert (output/'README.md').is_file()
    with pytest.raises(ValueError,match='never replaced'):builder.build(source,target,output)
    assert 'fixture-secret-must-not-copy' not in (output/'ontology.json').read_text()


@pytest.mark.parametrize('approved,count',[(True,1),(False,0),(False,26)])
def test_technical_enrichment_rejects_invalid_evidence(tmp_path,catalogue,approved,count):
    path=tmp_path/'invalid-probe.json'
    path.write_text(json.dumps(dict(business_policy_approved=approved,source_writes=0,ontology_published=False,
        fields=[dict(collection='tickets',field='engineReplacementStatus',status='observed_field',matching_sample_count=count,observed_bson_types=['string'])])))
    with pytest.raises(ValueError):builder.apply_field_verification(catalogue,[],[],path)
