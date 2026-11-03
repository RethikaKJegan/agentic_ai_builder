"""Backend-only Phase 3 planning, execution and inspection. No browser/server needed.

Use an isolated store; company reads use the existing authorized Phase 2 service.
Model planning is the default. --planning-mode offline and --analysis-mode offline
are explicit diagnostics, never represented as model or CrewAI execution.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.ontology_retrieval import build as retrieval_service
from workflow_api.business_investigations import BusinessInvestigations
from workflow_api.service import ApiFailure


def build(database,scope,credentials_database=None,models=True):
    retrieval,auth=retrieval_service(database,scope,credentials_database,use_ai=models)
    # Local operator CLI authority only; HTTP uses its actual session permissions.
    auth['permissions']+=['workflow.execute']
    return BusinessInvestigations(retrieval,env=retrieval.interpreter.env),auth


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,required=True);p.add_argument('--workspace',default='local-workspace');p.add_argument('--owner',default='local-builder');p.add_argument('--credentials-database',type=Path)
    actions=p.add_subparsers(dest='action',required=True)
    actions.add_parser('capabilities')
    a=actions.add_parser('plan');a.add_argument('--objective',required=True);a.add_argument('--request-key',required=True);a.add_argument('--version');a.add_argument('--inputs',default='{"identifiers":{}}');a.add_argument('--planning-mode',choices=['model','offline'],default='model');a.add_argument('--analysis-mode',choices=['crewai','offline'],default='crewai');a.add_argument('--wait-for-information',action='store_true')
    for name in ('graph','validate','run','requirements'):
        a=actions.add_parser(name);a.add_argument('--workflow-id',required=True)
        if name=='run':a.add_argument('--request-key',required=True)
    for name in ('execute','inspect','resume','cancel','report','input'):
        a=actions.add_parser(name);a.add_argument('--run-id',required=True)
        if name=='input':a.add_argument('--json',required=True)
        if name=='report':a.add_argument('--section',choices=['all','requirements','gaps','recovery','resolutions','dates','associations','findings'],default='all')
    args=p.parse_args()
    try:
        service,auth=build(args.database,(args.workspace,args.owner),args.credentials_database)
        if args.action=='capabilities':result=service.catalogue(auth)
        elif args.action=='plan':
            body=dict(objective=args.objective,request_key=args.request_key,inputs=json.loads(args.inputs),planning_mode=args.planning_mode,analysis_mode=args.analysis_mode,wait_for_information=args.wait_for_information)
            if args.version:body['version_id']=args.version
            result=service.plan(auth,body)
        elif args.action=='graph':result=service.get_plan(auth,args.workflow_id)
        elif args.action=='requirements':
            saved=service.get_plan(auth,args.workflow_id)
            result={t:c.get('evidence_requirements',[]) for t,c in saved['ontology_context']['tasks'].items()}
        elif args.action=='validate':result=service.validate(auth,args.workflow_id)
        elif args.action=='run':result=service.create_run(auth,args.workflow_id,dict(request_key=args.request_key))
        elif args.action in ('execute','resume'):result=service.execute(auth,args.run_id,{},resume=args.action=='resume')
        elif args.action=='cancel':result=service.cancel(auth,args.run_id,{})
        elif args.action=='input':result=service.supply_input(auth,args.run_id,json.loads(args.json))
        else:
            result=service.get_run(auth,args.run_id)
            if args.action=='report':
                result=result['outputs'].get('end') or next((i.get('partial_report') for i in result['pending_inputs'] if i.get('partial_report')),dict(status=result['status'],message='No final or pending report yet. Inspect node errors and pending inputs.'))
                section=args.section
                if section!='all':
                    key={'requirements':'task_evidence','gaps':'normalized_gaps','recovery':'recovery_actions','resolutions':'resolved_references','associations':'ambiguous_associations','findings':'unverified_findings'}.get(section)
                    result=([dict(record_id=r['record_id'],mapping_id=mid,**v) for r in result.get('source_records',[]) for mid,v in r['values'].items() if v.get('precision')=='calendar_day'] if section=='dates' else result.get(key,[]))
        print(json.dumps(result,indent=2,allow_nan=False));return 0
    except (ApiFailure,ValueError,json.JSONDecodeError) as e:
        print(json.dumps(dict(error=getattr(e,'code','INVESTIGATION_INPUT'),message=str(e))));return 1
    except Exception as e:
        print(json.dumps(dict(error=getattr(e,'code','INVESTIGATION_UNAVAILABLE'),message='Inspect source/model configuration and isolated storage.')));return 1


if __name__=='__main__':sys.exit(main())
