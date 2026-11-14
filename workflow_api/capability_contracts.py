"""Registered operation semantics; text from a model never installs executables."""
from copy import deepcopy
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from .business_knowledge_model import digest
from .investigation_graph import ANALYSIS_SCHEMA,fail

RESULT_SCHEMA=deepcopy(ANALYSIS_SCHEMA)
RESULT_SCHEMA['additionalProperties']=True
RESULT_SCHEMA['properties']['findings']['items']['additionalProperties']=True
RESULT_SCHEMA['properties'].update(state={'enum':['completed','needs_input','insufficient_evidence','conflicting_evidence','unsupported']},classification={'type':'string'},source_evidence={'type':'array','items':{'type':'object'}},coverage={'type':'object'},tool_results={'type':'array','items':{'type':'object'}})
INPUT_SCHEMA={'type':'object','additionalProperties':False,'required':['task_id'],'properties':{'task_id':{'type':'string'},'context':{'type':'object'}}}
MASTER_SCHEMA={'type':'object','additionalProperties':False,'required':['summary'],'properties':{'summary':{'type':'string','maxLength':3000},'task_results':{'type':'array','items':{'type':'object'}},'narrative_classification':{'type':'string'}}}
SCHEMA=json.loads((Path(__file__).parent/'schemas'/'capability-contract-v1.json').read_text())
# Registered domain configuration over existing Phase 1 outcome identifiers.
BUSINESS_BINDINGS={
 'complaints':['business.read.complaints'],
 'inspection':['business.read.complaints','business.read.inspection','business.compare'],
 'warranty':['business.read.warranty','business.assess_warranty'],
 'replacement':['business.read.replacement','business.review_replacement'],
 'history':['business.read.history','business.review_history'],
 'recurrence':['business.read.recurrence','business.review_recurrence'],
}
REVIEW_DEPENDENCIES={'business.compare':['business.read.complaints','business.read.inspection'],'business.assess_warranty':['business.read.warranty'],'business.review_replacement':['business.read.replacement'],'business.review_history':['business.read.history'],'business.review_recurrence':['business.read.recurrence']}
# These semantics come from existing installed connector contracts, not name guessing.
EXTERNAL={
 'mail_send':('mail.send','write','message_id'),
 'mail_reply':('mail.reply','write','message_id'),
 'mail_attachment':('mail.attachment','read','schema_and_tool_receipt'),
 'calendar_discover':('calendar.discover','read','schema_and_tool_receipt'),
 'mail_profile':('mail.profile','read','schema_and_tool_receipt'),
 'web_search':('research.search','read','schema_and_tool_receipt'),
 'read_public_page':('research.fetch','read','schema_and_tool_receipt'),
 'send_email':('mail.send','write','message_id'),
 'mail_search':('mail.search','read','schema_and_tool_receipt'),
 'mail_message':('mail.read','read','schema_and_tool_receipt'),
 'mail_thread':('mail.thread','read','schema_and_tool_receipt'),
 'mail_draft':('mail.draft','draft','draft_id'),
 'calendar_list':('calendar.events','read','schema_and_tool_receipt'),
 'calendar_create':('calendar.create','write','event_id'),
 'calendar_update':('calendar.update','write','event_id'),
 'calendar_cancel':('calendar.cancel','write','cancelled_event'),
 'read_spreadsheet':('sheet.read','read','schema_and_tool_receipt'),
 'update_spreadsheet':('sheet.update','write','schema_and_tool_receipt'),
 'discover_spreadsheet':('sheet.discover','read','spreadsheet_id'),
 'create_spreadsheet':('sheet.create','write','spreadsheet_id'),
 'create_spreadsheet_report':('report.publish','write','spreadsheet_id'),
 'create_spreadsheet_tabs':('sheet.tabs','write','spreadsheet_id'),
 'upsert_spreadsheet_record':('sheet.upsert','write','schema_and_tool_receipt'),
}


def contract(cid,operation,purpose,kind='model',task=None,tool_operation=None,effect='none',inputs=None,outputs=None,verify='cited_interpretation',domain='any'):
 c=dict(schema_version='capability-contract-v1',capability_id=cid,supported_operation=operation,business_purpose=purpose,kind=kind,input_schema=deepcopy(inputs or INPUT_SCHEMA),output_schema=deepcopy(outputs or RESULT_SCHEMA),required_ontology=[],required_evidence=[],preconditions=[],allowed_tool_operations=[tool_operation] if tool_operation else [],side_effect=effect,verification_method=verify,completion_criteria=['Output matches schema','Required evidence or tool receipt is present','No inferred business authority'],domain_scope=[domain],retrieval_task=task)
 if list(Draft202012Validator(SCHEMA).iter_errors(c)):fail('Invalid registered capability contract.','CAPABILITY_CONTRACT_INVALID',422)
 return c


def catalogue(preparation,tools,connectors=None):
 from .business_preparation import BusinessEvidenceAdapter
 result={}
 for task in ('complaints','inspection','warranty','replacement','history','recurrence'):
  cid='business.read.'+task
  c=contract(cid,'retrieve_mapped_evidence','Retrieve '+task+' evidence through pinned mappings','tool',task,'business.retrieve_evidence','read',BusinessEvidenceAdapter.input_schema,BusinessEvidenceAdapter.output_schema,'mapped_evidence_and_coverage','configured_business_ontology')
  if preparation and task in preparation['tasks']:
   c['required_ontology']=[v['id'] for v in preparation['tasks'][task]['concepts']]
   c['required_evidence']=[r['fact_id'] for r in preparation['coverage'][task]['requirements'] if r['requirement_level'] in ('required_to_execute','required_for_conclusion')]
  result[cid]=c
 for cid,deps in REVIEW_DEPENDENCIES.items():
  result[cid]=contract(cid,'interpret_supported_evidence',cid.rsplit('.',1)[-1].replace('_',' ').title(),domain='configured_business_ontology')
  result[cid]['preconditions']=deps
  result[cid]['required_ontology']=sorted({x for d in deps for x in result[d]['required_ontology']})
  result[cid]['required_evidence']=sorted({x for d in deps for x in result[d]['required_evidence']})
 result['business.report']=contract('business.report','summarize','Prepare a source-backed summary')
 for record in tools:
  d=record['definition'];semantic=EXTERNAL.get(d['capability'])
  if not semantic and connectors is not None and d['tool_id'] in connectors:
   connector=connectors[d['tool_id']]
   classifier=getattr(connector,'external_write_for_workflow',None)
   effect=classifier({'metadata':{}}) if callable(classifier) else getattr(connector,'external_write',True)
   semantic=('registered.'+d['capability'],'write' if effect else 'read','schema_and_tool_receipt')
  if semantic:
   op,effect,verify=semantic;cid='tool.'+d['tool_id']
   result[cid]=contract(cid,op,d['description'],'tool',tool_operation=d['capability'],effect=effect,inputs=d['input_schema'],outputs=d['output_schema'],verify=verify)
 return result


def validate_tasks(tasks,contracts,*,max_tasks=16):
 if not isinstance(tasks,list) or not 1<=len(tasks)<=max_tasks:fail('Select between one and sixteen supported tasks.' if max_tasks==16 else 'The capability catalogue exceeds its supported bound.','CAPABILITY_TASK_LIMIT',422)
 ids=[t.get('task_id') for t in tasks]
 if len(ids)!=len(set(ids)):fail('Duplicate task identifier.','CAPABILITY_TASK_GRAPH',422)
 pending=set(ids);done=set()
 for t in tasks:
  if t['capability_id'] not in contracts or set(t['depends_on'])-set(ids) or t['task_id'] in t['depends_on']:fail('Unknown capability or task dependency.','CAPABILITY_TASK_GRAPH',422)
 while pending:
  ready={t['task_id'] for t in tasks if t['task_id'] in pending and set(t['depends_on'])<=done}
  if not ready:fail('Task dependencies contain a cycle.','CAPABILITY_TASK_GRAPH',422)
  done|=ready;pending-=ready
 return True


# Fulfillment uses the existing registered operation semantics above.
REQUIRED_OPERATIONS={
 'email_send':{'mail.send'}, 'email_draft':{'mail.draft'},
 'calendar_write':{'calendar.create','calendar.update','calendar.cancel'},
 'sheet_create':{'sheet.create','report.publish'},
 'sheet_update':{'sheet.update','sheet.upsert','sheet.tabs'},
}

def operation_of(capability):
    operation=capability.get('supported_operation')
    if operation:return operation
    from connector_extension.catalog import CATALOG
    definition=CATALOG.get(capability.get('capability_id','').removeprefix('tool.'),{})
    return EXTERNAL.get(definition.get('capability'),(None,))[0]

def fulfills(requirement,capability):
    return operation_of(capability) in REQUIRED_OPERATIONS.get(requirement,set())
