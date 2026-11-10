"""Ontology-only recovery guidance, citation integrity and immutable scope."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import zipfile
import pytest
from workflow_api.business_ontology import BusinessOntology
from workflow_api.business_compiler import canonical
from workflow_api.business_planning import retrieve
from workflow_api.storage import WorkflowStore
from workflow_api.subway_evidence_resolution import load,annotate,ARTIFACT,SCOPE
from scripts.provision_subway_dump_ontology import AUTH
ROOT=Path(__file__).resolve().parents[1]
V=json.loads((ROOT/'ontology/subway/business-ontology-v4.json').read_text())

@pytest.fixture
def store(tmp_path):
 s=WorkflowStore(tmp_path/'ontology.sqlite3');BusinessOntology(s)
 with s.transaction() as db:
  db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(*SCOPE,V['version_id'],json.dumps(V)))
 return s


def ref(store,question,identifier):
 view=retrieve(store,AUTH,question,V['version_id'])
 assert view['definition_sha256']==sha256(canonical(V).encode()).hexdigest()
 value=next(r for r in view['references'] if r['id']==identifier)
 assert value['evidence_resolution']['sha256']==view['evidence_resolution_sha256']
 return value


def test_budget_comparison_uses_available_records_not_reservation_history(store):
 r=ref(store,'Can I reserve an amount from the available line item budget?','budgets:code_rule_reservation_available')
 assert 'external_prerequisites' not in r
 assert 'availableAmount' in r['evidence_resolution']['available_evidence'][0]['fields']
 assert r['evidence_resolution']['request_inputs']
 assert 'historical' in r['evidence_resolution']['conditional_requirements'][0]
 assert not any(u.startswith('This guard also depends on records absent') for u in r['unknowns'])


def test_requisition_guard_is_conditional_and_does_not_assume_historical_approval(store):
 r=ref(store,'Does a purchase order require an approved purchase requisition?','procurement:code_rule_approved_pr')
 resolution=r['evidence_resolution']
 assert 'if (body.purchaseRequestId)' in resolution['finding']
 assert 'not a substitute' in resolution['conditional_requirements'][0]
 assert 'external_prerequisites' not in r
 assert r['conditional_external_prerequisites'][0]['source_concept_id']=='procurement:purchase_request'


def test_stage_facts_remain_evidence_without_inventing_parent_status(store):
 r=ref(store,'Show approval stages status history and stageDate','approvals:finance_stages')
 resolution=r['evidence_resolution']
 assert {'_id','approvalId','status','stageDate'}<=set(resolution['available_evidence'][0]['fields'])
 assert 'does not establish final parent approval' in resolution['conditional_requirements'][0]
 assert 'exact approvals._id' in resolution['applicability']
 assert any(e['source_id']=='subway_resolution_stage_facts' for e in r['evidence'])


def test_original_snapshot_and_saved_versions_are_unchanged(store):
 before=canonical(V)
 retrieve(store,AUTH,'Budget reservation available amount',V['version_id'])
 with store.transaction(write=False) as db:
  saved=json.loads(db.execute('SELECT document FROM business_ontology_versions').fetchone()[0])
 assert canonical(saved)==before==canonical(V)
 assert sha256(canonical(V).encode()).hexdigest()==json.loads(ARTIFACT.read_text())['definition_sha256']


def test_foreign_owner_other_versions_and_changed_snapshot_get_no_supplement():
 assert load(('client-simpsons','subway-client'),V) is None
 assert load(('client-subway','other-owner'),V) is None
 old=deepcopy(V);old['version_id']='bov_subway_audited_v3';assert load(SCOPE,old) is None
 changed=deepcopy(V);changed['revision']=5;assert load(SCOPE,changed) is None


def test_every_recovery_citation_matches_exact_original_archive_lines():
 bundle=load(SCOPE,V)
 for source in bundle['sources'].values():
  origin=source['origin']
  with zipfile.ZipFile(ROOT/origin['archive']) as z:
   raw=z.read(origin['member']);quote=''.join(raw.decode().splitlines(keepends=True)[origin['start_line']-1:origin['end_line']]).rstrip('\r\n')
  assert sha256(raw).hexdigest()==origin['member_sha256']
  assert quote==source['text'] and sha256(quote.encode()).hexdigest()==source['sha256']


def test_tampered_resolution_rejected(monkeypatch,tmp_path):
 import workflow_api.subway_evidence_resolution as module
 document=json.loads(ARTIFACT.read_text());document['entries']['approvals:finance_stages']['finding']='Invented approval'
 path=tmp_path/'tampered.json';path.write_text(json.dumps(document));monkeypatch.setattr(module,'ARTIFACT',path)
 with pytest.raises(ValueError,match='integrity'):load(SCOPE,V)
