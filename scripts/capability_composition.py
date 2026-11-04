"""Offline Phase 2 inspection using an explicit isolated read-only tool Registry.

This diagnostic CLI creates no live Registry grants, effects, approvals or model calls.
Use the normal authenticated backend for configured-model planning and execution.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.simpson_investigation import build as investigations
from workflow_api.business_composition import BusinessComposition
from workflow_api.business_preparation import BusinessEvidenceConnector,retrieval_tool_definition
from workflow_api.service import WorkflowService,ApiFailure
from workflow_api.registry_adapter import RegistryAdapter
from registry import RegistryService,WorkspacePolicy
from planner import PlannerService
from planner.provider import RuleBasedStructuredOutputProvider


def build(database,scope,credentials_database=None):
 if database.resolve()==(ROOT/'.local/workflows.sqlite3').resolve():raise ValueError('Use an isolated diagnostic application database.')
 investigation,auth=investigations(database,scope,credentials_database,models=False)
 auth.update(roles=['admin','approver']);auth['permissions']=sorted(set(auth['permissions'])|{'workflow.plan','workflow.view','workflow.edit','tools.manage','tools.assign','runs.view','workflow.approve'})
 auth['scopes']=sorted(set(auth['scopes'])|{'tools.read'})
 registry=RegistryService(WorkspacePolicy(scope[0],agent_permissions={'workflow.read_input','tools.read'},approved_providers={'builder_business'},remaining_quota={'business_retrieve_evidence':100}))
 response=registry.register_tool(retrieval_tool_definition(),auth)
 if response['status']!=200:raise ValueError('Diagnostic read adapter registration failed.')
 adapter=RegistryAdapter(registry);general=WorkflowService(investigation.store,PlannerService(RuleBasedStructuredOutputProvider()),registry_adapter=adapter)
 general.business_preparation=investigation.coverage.preparation
 composition=BusinessComposition(general,general.business_preparation,{'business_retrieve_evidence':BusinessEvidenceConnector(general.business_preparation)},model_id='offline-diagnostic')
 general.business_composition=composition
 return composition,auth


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);p.add_argument('--workspace',default='local-workspace');p.add_argument('--owner',default='local-builder');p.add_argument('--credentials-database',type=Path)
 commands=p.add_subparsers(dest='action',required=True)
 a=commands.add_parser('prepare');a.add_argument('--objective',required=True);a.add_argument('--request-key',required=True);a.add_argument('--preparation-id');a.add_argument('--evidence-context');a.add_argument('--inputs',default='{"identifiers":{}}');a.add_argument('--operations')
 for name in ('inspect','workflow','validate'):
  a=commands.add_parser(name);a.add_argument('--composition-id',required=True)
  if name=='inspect':a.add_argument('--section',choices=['all','tasks','configurations','contracts','selected_tools','gaps','planning'],default='all')
 args=p.parse_args()
 try:
  service,auth=build(args.database,(args.workspace,args.owner),args.credentials_database)
  if args.action=='prepare':
   body=dict(objective=args.objective,request_key=args.request_key,planning_mode='offline')
   if args.preparation_id:body['preparation_id']=args.preparation_id
   else:
    request=dict(inputs=json.loads(args.inputs))
    if args.evidence_context:request['evidence_context']=json.loads(args.evidence_context)
    body['business_request']=request
   if args.operations:body['operations']=json.loads(args.operations)
   result=service.prepare(auth,body)
  elif args.action=='workflow':result=service.workflow(auth,args.composition_id)
  elif args.action=='validate':
   from planner.validation import validate_workflow
   result=dict(valid=bool(validate_workflow(service.workflow(auth,args.composition_id))),composition_id=args.composition_id)
  else:
   result=service.get(auth,args.composition_id)
   if args.section!='all':result=result[args.section]
  print(json.dumps(result,indent=2,allow_nan=False));return 0
 except Exception as exc:
  print(json.dumps(dict(error=getattr(exc,'code','COMPOSITION_INPUT'),message=str(exc) if isinstance(exc,(ApiFailure,ValueError)) else 'Inspect isolated configuration and scoped capability inputs.')));return 1


if __name__=='__main__':sys.exit(main())
