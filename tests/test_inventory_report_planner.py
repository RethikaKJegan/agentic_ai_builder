"""Offline compilation and real arithmetic; no deployed workflows or provider calls."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from planner.errors import PlannerFailure
from planner.validation import normalize_generated_inputs, validate_output_mappings
from workflow_api.service import WorkflowService
from workflow_api.database_workflows import definitions as db_definitions, bind_generated
from workflow_api.inventory_report_planner import compile_inventory_report, meeting_window, REQUIRED
from workflow_api.inventory_ranking import TOOL, DELIVERY, NORMALIZE, rank_inventory, InventoryRank
from workflow_api.procurement import definitions, ScopedConnector
from connector_extension.catalog import CATALOG
from connector_extension.tests.test_connectors import grant
from runtime.service import RuntimeFailure
from runtime.supplier_search import SEARCH, PAGE

PROMPT = ('Check our inventory and find the five products that most urgently need restocking, taking stock already on order into account. '
          'Include their category and supplier. Search the web for relevant food-wholesale supply risks and source links. '
          'Put findings in a new Google spreadsheet, prepare an email summary, and arrange a 30-minute review on 19 October 2026, '
          'from 3:00–4:00 PM IST. Let me approve the spreadsheet creation, email and meeting first.')


def source_catalog():
    fields={'products': {'product_id':'productID','product_name':'productName','units_in_stock':'unitsInStock',
                        'units_on_order':'unitsOnOrder','reorder_level':'reorderLevel','discontinued':'discontinued'},
            'categories':{'category':'categoryName'},'suppliers':{'supplier':'companyName'}}
    sources=[{'dataset_id':did,'connection_id':'connection_'+did,'label':did,'engine':'postgresql','context_hash':'a'*64,
              'fields':[{'field_id':key,'name':name,'types':['integer' if key in ('units_in_stock','units_on_order','reorder_level') else 'string']} for key,name in fs.items()],
              'identity_fields':[],'writable_fields':[],'operations':['query']} for did,fs in fields.items()]
    from workflow_api.data_relationships import fingerprint
    return {'sources':sources,'graph_hash':fingerprint({}), 'business_mappings':[],
            'relationships':[{'relationship_id':'link_'+did,'source_dataset_id':'products','target_dataset_id':did,'field_pairs':[],'status':'accepted'} for did in ['categories','suppliers']]}


def context():
    tools = [*db_definitions(), *CATALOG.values(), SEARCH, PAGE, TOOL, DELIVERY, NORMALIZE]
    return {'google_connection_id':'gc_'+'a'*32,'database_catalog':source_catalog(),
            'database_workflow_tools':db_definitions(),'workflow_google_tools':tools}


def proposal():
    w=json.loads(Path('shared/contracts/examples/workflows/support-triage.json').read_text())
    a=json.loads(Path('shared/contracts/examples/agents/valid-classifier.json').read_text())
    for key in ['name','retry_policy','guardrails']:a.pop(key,None)
    w['agents']=[a];w['metadata']={'database_source_ids':['products','categories','suppliers']}
    return w


def test_compiled_graph_validates_with_typed_handoffs_and_exact_schedule():
    c=context();w=compile_inventory_report(proposal(),PROMPT,c)
    WorkflowService.validate_document(w)
    validate_output_mappings(w,{t['tool_id']:t['output_schema'] for t in c['workflow_google_tools']})
    assert w['inputs']==[] and w['metadata']['unresolved_requirements']==[]
    nodes={n['node_id']:n for n in w['nodes']}
    assert nodes['send_summary']['configuration']['input_mapping']['to']=='outputs.account_profile.email_address'
    assert nodes['prepare_delivery']['configuration']['input_mapping']['spreadsheet_url']=='outputs.create_report.spreadsheet_url'
    for node in ['create_report','send_summary','create_meeting']:
        edge=next(e for e in w['edges'] if e['target']==node)
        assert edge['outcome']=='approved' and nodes[edge['source']]['kind']=='approval'
    assert w['metadata']['delivery_preferences']['start']['dateTime']=='2026-10-19T15:30:00+05:30'
    assert not any(e.get('outcome')=='rejected' for e in w['edges'])  # Runtime stops rejected approvals; no unexecuted output references.
    assert REQUIRED=={t['tool_id'] for t in w['tools']}


def test_compiler_never_accepts_invented_source_or_missing_tool():
    w=proposal();w['metadata']['database_source_ids'][0]='invented'
    broken=context();broken['database_catalog']['relationships']=[]
    with pytest.raises(PlannerFailure):compile_inventory_report(w,PROMPT,broken)
    c=context();c['workflow_google_tools']=[t for t in c['workflow_google_tools'] if t['tool_id']!='extension_inventory_rank']
    with pytest.raises(PlannerFailure,match='REPORT_CAPABILITY_REQUIRED'):compile_inventory_report(proposal(),PROMPT,c)


def test_unrelated_workflows_are_not_rewritten():
    w=proposal();assert compile_inventory_report(w,'Summarize our customer records',context()) is w
    assert compile_inventory_report(w,PROMPT+' Also update customer records.',context()) is w


def test_literal_mapping_normalization_does_not_expand_expression_language():
    w={'nodes':[{'configuration':{'input_mapping':{'setup':"{'nested': ['value', 2]}", 'objective':"'Read stock'"}}}]}
    normalize_generated_inputs(w)
    assert w['nodes'][0]['configuration']=={'input':{'setup':{'nested':['value',2]},'objective':'Read stock'}}
    for expression in ["__import__('os').system('bad')", "{'x': outputs.other.value}"]:
        w={'nodes':[{'configuration':{'input_mapping':{'setup':expression}}}]};normalize_generated_inputs(w)
        assert 'input_mapping' in w['nodes'][0]['configuration']


def record(identifier,stock=0,on_order=0,reorder=10,discontinued=False):
    return {'product_id':identifier,'product_name':identifier,'category':'Actual category','supplier':'Actual supplier',
            'units_in_stock':stock,'units_on_order':on_order,'reorder_level':reorder,'discontinued':discontinued}


def test_ranking_accounts_for_orders_excludes_discontinued_and_labels_watchlist():
    result=rank_inventory([record('covered',on_order=10),record('small',stock=8),record('large',stock=1),
                           record('discontinued',reorder=100,discontinued=True)])
    assert [r['product_id'] for r in result['ranked_products']]==['large','small','covered']
    assert result['shortage_count']==2 and result['ranked_products'][0]['shortage']==9
    assert result['reviewed_records']==4
    assert result['ranked_products'][-1]['shortage']==0
    assert 'Watchlist only' in result['tabs'][0]['rows'][-1][-1]


def test_ranking_is_bounded_stable_and_preserves_truncation():
    result=rank_inventory([record(str(i)) for i in reversed(range(8))],limited=True)
    assert len(result['ranked_products'])==5 and result['limited']
    assert [r['product_id'] for r in result['ranked_products']]==['0','1','2','3','4']
    for records in [[record('a'),record('a')],[record('a',stock=float('nan'))],[record('a',stock=-1)]]:
        with pytest.raises(RuntimeFailure):rank_inventory(records)


def test_analysis_tool_is_registered_and_invocable_without_network():
    config={'enabled_providers':['google_sheets','gmail','google_calendar'],'sheet_creation_enabled':True,'_automatic_actions':True}
    tool=next(t for t in definitions(config) if t['tool_id']==TOOL['tool_id'])
    authorization={'tool_id':tool['tool_id'],'authorization_state':'authorized','authorization_reference':'offline',
                   'credential_reference':'cred_extension_builder_analysis','input_schema':tool['input_schema'],'output_schema':tool['output_schema']}
    result=InventoryRank(tool,None).invoke(authorization,{'records':[record('a')],'limited':False},'offline')
    assert result['ranked_products'][0]['shortage']==10


def test_legacy_automatic_mode_cannot_bypass_standalone_google_write_approval():
    from connector_extension.mail import MailConnector
    from connector_extension.common import EffectJournal
    from tempfile import TemporaryDirectory
    definition=deepcopy(CATALOG['extension_mail_send']);definition['approval_required']=False
    with TemporaryDirectory() as root:
        connector=ScopedConnector(MailConnector(definition,None,EffectJournal(root)),None)
        bound=connector.bind_workflow({'workflow_id':'offline','version':1,'metadata':{'workspace_id':'one'}})
        assert bound.external_write
        authorization=grant('extension_mail_send');authorization.pop('approval_reference')
        with pytest.raises(RuntimeFailure) as failure:
            bound.invoke(authorization,{'to':'owner@example.com','subject':'Review','body':'Test'},'offline')
        assert failure.value.code=='APPROVAL_REQUIRED'


def test_source_resolution_uses_field_coverage_and_real_relationships():
    from workflow_api.inventory_report_planner import inventory_sources
    def source(identifier,fields):return {'dataset_id':identifier,'fields':[{'name':n} for n in fields]}
    catalog={'sources':[source('actual_stock',['unitsInStock','unitsOnOrder','reorderLevel']),
        source('actual_category',['categoryName']),source('actual_supplier',['companyName']),
        source('unrelated_customer',['companyName'])],
        'relationships':[{'source_dataset_id':'actual_stock','target_dataset_id':target,'status':'accepted'} for target in ['actual_category','actual_supplier']]}
    assert inventory_sources(catalog,['invented'])==['actual_stock','actual_category','actual_supplier']
    catalog['relationships']=[]
    with pytest.raises(PlannerFailure):inventory_sources(catalog,['invented'])


def test_same_normal_prompt_uses_trusted_compiler_without_model_workflow_json():
    from workflow_api.live_providers import LivePlannerProvider
    from unittest.mock import patch
    c=context();c.update(generation_mode='hierarchy',execution_input_mode='automatic')
    provider=LivePlannerProvider('gpt-5.6-luna',['owner@example.com'],SimpleNamespace())
    with patch.object(provider.provider,'generate',side_effect=AssertionError('Must not generate model workflow JSON')):
        workflow=provider.generate(PROMPT,c)
    assert workflow['metadata']['inventory_report_compiler']==1
    assert workflow['metadata']['database_source_ids']==['products','categories','suppliers']
    assert workflow['inputs']==[]
    assert workflow['metadata']['delivery_preferences']['start']['dateTime']=='2026-10-19T15:30:00+05:30'
    WorkflowService.validate_document(workflow)
    bind_generated(workflow,c)
    assert len(workflow['metadata']['database_scope']['sources'])==3
