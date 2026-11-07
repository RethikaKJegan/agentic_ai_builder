"""Grounding, namespace, backwards compatibility and nonexecution of code rules."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
import pytest
from workflow_api.business_compiler import check_snapshot,compile_snapshot
from workflow_api.business_rules import catalogue
from workflow_api.subway_onboarding import build_package
from workflow_api.service import ApiFailure
from workflow_api.storage import WorkflowStore
from workflow_api.business_ontology import BusinessOntology
from workflow_api.business_planning import retrieve
from scripts.build_subway_code_ontology import ARCHIVES

ROOT=Path(__file__).resolve().parents[1]
OLD=json.loads((ROOT/'ontology/subway/business-ontology-v1.json').read_text())
NEW=json.loads((ROOT/'ontology/subway/business-ontology-v2.json').read_text())
MANIFEST=json.loads((ROOT/'ontology/subway/code-evidence-manifest-v2.json').read_text())


def test_code_enrichment_is_immutable_scoped_and_explicitly_descriptive():
    assert NEW['revision']==2 and NEW['code_enrichment']['previous_version']==OLD['version_id']
    assert len(NEW['concepts'])==89 and len(NEW['relationships'])==91 and len(NEW['rules'])==28
    assert NEW['workspace']['sources']==OLD['workspace']['sources']
    assert {c['id'] for c in OLD['concepts']} <= {c['id'] for c in NEW['concepts']}
    assert NEW['relationships'][:len(OLD['relationships'])]==OLD['relationships']
    assert len([c for c in NEW['concepts'] if c.get('data_availability')=='code_only_not_connected'])==35
    for rule in catalogue(NEW):
        assert rule['basis']=='descriptive_implementation' and rule['executable'] is False
        assert not rule['execution']['available'] and not rule['business_policy_verified']
    assert check_snapshot(NEW).startswith('urn:subway-business:')
    report,_=compile_snapshot(NEW)
    assert report['status']=='passed' and report['instance_validation']=='not_run'


def test_every_code_quote_matches_its_source_and_manifest():
    sources={s['source_id']:s for s in NEW['sources']}
    for kind in ['concepts','relationships','rules']:
        for item in NEW[kind]:
            for e in item['evidence']:
                assert ' '.join(e['quote'].split()) in ' '.join(sources[e['source_id']]['text'].split())
    for s in sources.values():assert hashlib.sha256(s['text'].encode()).hexdigest()==s['sha256']
    for excerpt in MANIFEST['excerpts']:
        source=sources['subway_code_'+next(k for k,a in MANIFEST['archives'].items() if a['name']==excerpt['archive'])]
        header=f"FILE {excerpt['member']} LINES {excerpt['start_line']}-{excerpt['end_line']}\n"
        assert header in source['text']


def test_all_eight_original_archives_and_excerpts_are_preserved():
    for key,record in MANIFEST['archives'].items():
        path=ROOT/record['name'];assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
        with zipfile.ZipFile(path) as archive:
            for e in [e for e in MANIFEST['excerpts'] if e['archive']==record['name']]:
                raw=archive.read(e['member']);assert hashlib.sha256(raw).hexdigest()==e['member_sha256']
                quote=''.join(raw.decode().splitlines(keepends=True)[e['start_line']-1:e['end_line']]).rstrip('\r\n')
                assert hashlib.sha256(quote.encode()).hexdigest()==e['excerpt_sha256']
    assert set(MANIFEST['archives'])==set(ARCHIVES)


def test_ast_reference_scan_ignores_comments_and_unrelated_strings():
    source="""// fake: {type:Number,ref:'Foreign'}
    const schema={site:{type:Number,ref:'Location'}, note:'ref: Other'};
    /* x:{ref:'Commented'} */
    """
    output=json.loads(subprocess.check_output(['node',str(ROOT/'scripts/subway_code_model_scan.mjs')],input=json.dumps({'text':source}),text=True))
    assert [(r['field'],r['target']) for r in output['references']]==[('site','Location')]


def test_code_only_services_keep_separate_model_identity():
    refs=NEW['relationships'][len(OLD['relationships']):]
    def target(source,predicate):return {r['target'] for r in refs if r['source']==source and r['predicate']==predicate}
    assert target('procurement:finance_purchaseorders','references_company')=={'organization:finance_companies'}
    assert target('procurement:finance_purchaseorders','references_site')=={'organization:finance_locations'}
    assert target('invoice_tracking:invoice','references_vendor')=={'invoice_tracking:vendor'}
    assert target('technical_support:ticket','references_store')=={'technical_support:store_record'}
    assert not any(r['target']=='stores:central_stores' for r in refs if r['source'].startswith(('quality_cases:','technical_support:','document_storage:','franchise_records:')))
    # Actual model refs give evidence, never a data-access grant.
    assert all(r.get('relationship_basis')=='declared_model_reference' for r in refs)


def test_known_defects_and_bypass_conditions_are_not_normalized_into_policy():
    rules={r['id']:r for r in NEW['rules']}
    assert 'initialApproval' in rules['procurement:code_rule_budget_approval']['outcome']
    assert 'CF_READ_ONLY' in rules['cf_approvals:code_rule_step_approval']['outcome']
    assert {x['code'] for x in MANIFEST['excluded_rule_defects']}=={'SMALLWARE_APPROVER_GUARD','ADVANCE_ZERO_AMOUNT_GUARD'}
    assert not any('positive advance' in r['label'].lower() for r in NEW['rules'])


def test_old_package_remains_exact_and_v2_pins_new_knowledge_without_executable_rules():
    old=build_package(OLD);assert old==json.loads((ROOT/'ontology/subway/knowledge-package-v1.json').read_text())
    new=build_package(NEW,2);assert new==json.loads((ROOT/'ontology/subway/knowledge-package-v2.json').read_text())
    assert new['resource_bindings']==old['resource_bindings']
    assert new['ontology_version']==NEW['version_id'] and new['revision']==2
    assert new['rules']==[] # Package comparison handlers must not execute descriptive source logic.
    assert len(new['concepts'])==89 and len(new['capability_contracts'])==12


def test_pinned_planning_context_uses_new_rules_and_owner_scope(tmp_path):
    store=WorkflowStore(tmp_path/'app.sqlite3');ontology=BusinessOntology(store)
    auth=dict(decision='allow',subject=dict(workspace_id='client-subway',subject_id='subway-client'),permissions=['tools.read'],scopes=['workspace:read'])
    with store.transaction() as db:
        for snapshot in [OLD,NEW]:db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',('client-subway','subway-client',snapshot['version_id'],json.dumps(snapshot)))
    result=retrieve(store,auth,'Explain the purchase order budget approval guard and initialApproval bypass.',NEW['version_id'])
    assert result['state']=='matched' and result['version_id']==NEW['version_id']
    assert any(r['kind']=='rule' and r['id']=='procurement:code_rule_budget_approval' for r in result['references'])
    assert all(e['source_kind']=='application_code' for r in result['references'] if r['kind']=='rule' for e in r['evidence'])
    other=deepcopy(auth);other['subject']['workspace_id']='client-simpsons'
    assert retrieve(store,other,'purchase order')['state']=='not_configured'
    damaged=deepcopy(NEW);damaged['sources'][-1]['text']+=' forged'
    with pytest.raises(ApiFailure):check_snapshot(damaged)


def test_subway_coverage_and_rule_questions_never_load_simpsons_reference(tmp_path,monkeypatch):
    from workflow_api.business_reference import BusinessReference
    from workflow_api.business_rules import BusinessRules
    from workflow_api.business_compiler import BusinessCompiler
    store=WorkflowStore(tmp_path/'app.sqlite3');ontology=BusinessOntology(store)
    auth=dict(decision='allow',subject=dict(workspace_id='client-subway',subject_id='subway-client'),permissions=['tools.read'],scopes=['workspace:read'])
    with store.transaction() as db:db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',('client-subway','subway-client',NEW['version_id'],json.dumps(NEW)))
    def forbidden():raise AssertionError('Foreign reference loaded')
    monkeypatch.setattr('workflow_api.business_reference.load_kit',forbidden)
    monkeypatch.setattr('workflow_api.business_rules.question_reference',forbidden)
    coverage=BusinessReference(ontology,None).coverage(auth,NEW['version_id'])
    assert len(coverage['modules'])==15 and not coverage['import_available']
    assert 'engines' not in {m['module_id'] for m in coverage['modules']}
    view=BusinessRules(ontology,BusinessCompiler(ontology)).view(auth,NEW['version_id'])
    assert len(view['rules'])==28 and view['question_source']['title']=='Subway saved ontology questions'
    assert all(q['id'].startswith('subway_question_') for q in view['business_questions'])
