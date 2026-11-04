"""Prepare and inspect isolated connected Simpson evidence environments. No model calls."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.simpson_investigation import build
from workflow_api.business_environments import build_case,build_release,case_coverage,VARIANTS
from workflow_api.business_coverage import TASKS
from scripts.integration_config import private_write


def prepare(source,directory,tickets,scope):
    from scripts.check_evidence_refinement import run
    baseline=run(source,directory,scope,tickets)
    return release_captured(source,directory,scope,baseline)


def release_captured(source,directory,scope,baseline):
    tickets=list(dict.fromkeys(c['ticket'] for c in baseline['checks']))
    service,auth=build(directory/'isolated.sqlite3',scope,source,models=False)
    auth['permissions'].append('workflow.edit');auth['scopes'].append('workspace:write')
    knowledge=service.ontology.version(auth,baseline['baseline']['isolated_version_id'])
    basis=next((p for p in knowledge['knowledge']['manifest']['policy_snapshots'] if p.get('implementation_reference',{}).get('branch')=='other'),None)
    parameters={key:float(basis['clauses'][key]['value']) for key in ('sale_months','invoice_months','max_hours')} if basis else None
    cases=[]
    for index,_ in enumerate(tickets):
        captured=[]
        for task in TASKS:
            run_doc=json.loads((directory/('refinement_'+str(index)+'_'+task+'-run.json')).read_text())
            captured.extend(e for e in service.evidence(run_doc) if e['intent']['task']==task)
        for variant in VARIANTS:
            case=build_case(captured,variant,parameters)
            if basis:case['configuration_basis']=dict(policy_id=basis['policy_id'],revision=basis['revision'],sha256=basis['sha256'],application_limits=parameters,applicability_to_company_case='not_established')
            cases.append(case)
    release=build_release(cases,knowledge)
    service.coverage.environments.install(auth,release)
    private_write(directory/'environment.json',json.dumps(release,indent=2)+'\n')
    workflows=[]
    # Exercise the exact preparation/execution services for each released case.
    for case in release['cases']:
        objective='Compare complaint '+case['source_identifiers']['complaint_id']+' with its inspection, check warranty readiness and review replacement evidence.'
        body=dict(objective=objective,request_key=release['dataset_id']+'_'+case['case_id']+'_acceptance',planning_mode='offline',analysis_mode='offline',evidence_context=dict(dataset_id=release['dataset_id'],case_id=case['case_id']))
        plan=service.coverage.prepare_plan(auth,body);created=service.create_run(auth,plan['workflow_id'],dict(request_key=release['dataset_id']+'_'+case['case_id']+'_run'))
        result=service.execute(auth,created['run_id'],{})
        if result['status']!='completed':raise ValueError('Scenario workflow did not complete: '+json.dumps(result['node_errors']))
        report=result['outputs']['end']
        for task in TASKS:
            if report['decision_readiness'][task]['state']!=case_coverage(case,task)['state']:raise ValueError('Runtime coverage differs from released coverage')
        workflows.append(dict(case_id=case['case_id'],workflow_id=plan['workflow_id'],run_id=result['run_id'],status=result['status'],decision_readiness=report['decision_readiness']))
    receipt=dict(passed=True,dataset_id=release['dataset_id'],source_cases=len(tickets),scenario_cases=len(cases),task_checks=len(cases)*len(TASKS),workflows=workflows,real_source_checks=baseline['checks'],company_writes=0,live_application_writes=0,model_calls=0)
    private_write(directory/'acceptance.json',json.dumps(receipt,indent=2)+'\n');return {k:v for k,v in receipt.items() if k not in ('workflows','real_source_checks')}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path);p.add_argument('--credentials-database',type=Path);p.add_argument('--workspace',default='local-workspace');p.add_argument('--owner',default='local-builder')
    actions=p.add_subparsers(dest='action',required=True)
    a=actions.add_parser('prepare');a.add_argument('--source-database',type=Path,required=True);a.add_argument('--directory',type=Path,required=True);a.add_argument('--complaint-id',action='append',required=True)
    a=actions.add_parser('release');a.add_argument('--source-database',type=Path,required=True);a.add_argument('--directory',type=Path,required=True)
    actions.add_parser('cases');actions.add_parser('tasks')
    for name in ('manifest','coverage','records','mappings'):
        a=actions.add_parser(name);a.add_argument('--dataset-id',required=True)
        if name not in ('manifest','mappings'):a.add_argument('--case-id',required=True)
        if name=='coverage':a.add_argument('--task',choices=TASKS,required=True)
    a=actions.add_parser('revoke');a.add_argument('--dataset-id',required=True);a.add_argument('--record-id',required=True);a.add_argument('--reason',required=True)
    args=p.parse_args();scope=(args.workspace,args.owner)
    if args.action=='prepare':result=prepare(args.source_database,args.directory,args.complaint_id,scope)
    elif args.action=='release':result=release_captured(args.source_database,args.directory,scope,json.loads((args.directory/'refinement-report.json').read_text()))
    elif args.action=='tasks':result=list(TASKS)
    else:
        if args.database is None:p.error('--database is required for inspection')
        service,auth=build(args.database,scope,args.credentials_database,models=False);env=service.coverage.environments
        if args.action=='cases':result=env.list(auth)
        elif args.action=='manifest':result=env.get(auth,args.dataset_id)['manifest']
        elif args.action=='mappings':result=service.ontology.version(auth,env.get(auth,args.dataset_id)['manifest']['ontology_version'])['knowledge']['source_mappings']
        elif args.action=='revoke':
            auth['permissions'].append('workflow.edit');auth['scopes'].append('workspace:write');result=env.revoke(auth,args.dataset_id,args.record_id,args.reason)
        else:
            release,case=env.selected(auth,dict(dataset_id=args.dataset_id,case_id=args.case_id))
            result=case['business_records'] if args.action=='records' else case_coverage(case,args.task,revoked=env.revoked(auth,args.dataset_id))
    print(json.dumps(result,indent=2));return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print(json.dumps(dict(passed=False,code=getattr(exc,'code',type(exc).__name__),message=str(exc))));sys.exit(1)
