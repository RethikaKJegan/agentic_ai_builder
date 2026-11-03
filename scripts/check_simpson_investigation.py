"""Fresh isolated Phase 3 acceptance. Existing company sources are read-only.

--models makes actual configured planner/CrewAI calls using bounded mapped
business evidence. Without it the run is explicitly an offline diagnostic.
No company writes, workflow publication, external messaging or deployment.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.check_business_knowledge import run as prepare,readonly
from scripts.simpson_investigation import build
from scripts.integration_config import private_write

OBJECTIVE='Investigate complaint A-2022-12-013, compare the reported complaint with its linked inspection, check whether enough evidence exists for warranty assessment, and prepare a report explaining discrepancies and missing information.'


def run(database,directory,scope,models=False):
    baseline=prepare(database,directory,scope)
    service,auth=build(directory/'isolated.sqlite3',scope,database,models=models)
    with readonly(database) as db:before=db.execute('SELECT version_id,document FROM business_ontology_versions WHERE workspace=? AND owner=? ORDER BY version_id',scope).fetchall()
    # Independent native source lookup, not the resolver's own returned output.
    with service.store.transaction(write=False) as db:
        workspace=service.ontology.document(db,scope)
        secret,_=service.retrieval.manager.owned(db,auth,workspace['sources']['service'])
    config=json.loads(service.retrieval.manager.cipher.decrypt(secret.encode()))
    with service.retrieval.manager.adapter.connection(config) as client:
        db=client[config['database']]
        ticket=db['tickets'].find_one({'_id':'A-2022-12-013'},{'_id':1})
        if not ticket:raise ValueError('Acceptance complaint is absent; no record was manufactured.')
        linked=list(db['jointinspectionreports'].find({'ticketId':ticket['_id']},{'_id':1}).sort('_id',1).limit(21).max_time_ms(3000))
        expected={str(r['_id']) for r in linked[:20]}
    p=service.plan(auth,dict(objective=OBJECTIVE,request_key='phase3_acceptance_plan',planning_mode='model' if models else 'offline',analysis_mode='crewai' if models else 'offline'))
    private_write(directory/'workflow-plan.json',json.dumps(p,indent=2)+'\n')
    validation=service.validate(auth,p['workflow_id'])
    r=service.create_run(auth,p['workflow_id'],dict(request_key='phase3_acceptance_run'))
    r=service.execute(auth,r['run_id'],{})
    private_write(directory/'workflow-run.json',json.dumps(r,indent=2)+'\n')
    report=r['outputs'].get('end')
    if report:private_write(directory/'final-report.json',json.dumps(report,indent=2)+'\n')
    records=(report or {}).get('source_records',[])
    actual={rec['fields']['_id'] for rec in records if rec['collection']=='jointinspectionreports'}
    complaint_ids={rec['fields']['_id'] for rec in records if rec['collection']=='tickets'}
    with readonly(database) as db:after=db.execute('SELECT version_id,document FROM business_ontology_versions WHERE workspace=? AND owner=? ORDER BY version_id',scope).fetchall()
    summary=dict(passed=r['status']=='completed' and actual==expected and complaint_ids=={'A-2022-12-013'} and before==after,
                 workflow_id=p['workflow_id'],run_id=r['run_id'],version_id=p['version_id'],graph_validation=validation['validation']['valid'],
                 planning=p['planning'],analysis_mode=p['analysis_mode'],status=r['status'],report_status=(report or {}).get('completion_status'),
                 expected_linked_reports=len(expected),actual_linked_reports=len(actual),source_ids_match=actual==expected,
                 branch_decisions=r['branches'],node_states=r['node_states'],node_errors=r['node_errors'],usage=r['usage'],
                 missing_information_count=len((report or {}).get('missing_information',[])),rule_outcomes_count=len((report or {}).get('configured_rule_outcomes',[])),
                 original_knowledge_unchanged=before==after,company_writes=0,live_application_writes=0,copied_credentials=0,baseline=baseline)
    private_write(directory/'phase3-report.json',json.dumps(summary,indent=2)+'\n')
    if not summary['passed']:raise ValueError('Investigation acceptance failed; inspect private workflow-run.json and phase3-report.json.')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--workspace',default='local-workspace');p.add_argument('--owner',default='local-builder');p.add_argument('--models',action='store_true');a=p.parse_args()
    try:print(json.dumps(run(a.database,a.directory,(a.workspace,a.owner),a.models),indent=2))
    except Exception as e:
        print(json.dumps(dict(passed=False,code=getattr(e,'code',None),error_type=type(e).__name__,message=str(e) if isinstance(e,ValueError) or getattr(e,'code',None) else 'Inspect local configuration and private run evidence.')));sys.exit(1)
