"""Write isolated synthetic lifecycle scenarios; never connect to a company DB.

This harness tests scenario readiness separately from live evidence evaluation.
Generated events cannot satisfy production facts through any HTTP/CLI override.
"""
import argparse
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from workflow_api.business_evidence import evaluate

FACT_EVENTS={
 'physical_identity':'identity_confirmation',
 'policy_applicable':'policy_applicability',
 'exclusion_findings':'exclusion_review',
 'inspection_activity_completion_evidence':'inspection_signoff',
 'technical_disposition':'technical_recommendation',
 'commercial_authorization':'replacement_authorization',
 'comparable_confirmed_failure':'qa_conclusion',
 'change_applicability':'change_scope',
 'actual_incorporation':'incorporation_verification',
 'monitored_population':'cohort_definition',
 'operating_exposure':'exposure_observation',
}


def evaluate_scenario(document):
    if document.get('environment')!='isolated_scenario' or document.get('provenance')!='generated' or not document.get('scenario_id','').startswith('scenario_'):
        raise ValueError('Explicit generated isolated scenario context required')
    original=evaluate(document['task'],document['evidence'],document.get('inputs',{}),document.get('policies',[]))
    events=document['events'];previous=None;facts={}
    for event in events:
        if event['scenario_id']!=document['scenario_id'] or event['case_id']!=document['case_id'] or event['provenance']!='generated':raise ValueError('Foreign or unqualified scenario event')
        at=datetime.fromisoformat(event['at'])
        if at.tzinfo is None or previous and at<previous:raise ValueError('Scenario timeline is not ordered')
        if FACT_EVENTS.get(event['fact_id'])!=event['kind']:raise ValueError('Unsupported scenario fact event')
        if type(event['value']) is not bool:raise ValueError('Scenario facts require explicit boolean values')
        previous=at;facts.setdefault(event['fact_id'],[]).append(event['value'])
    receipt=document.get('return_receipt')
    if receipt:
        if receipt.get('case_id')!=document['case_id'] or receipt.get('provenance')!='generated':raise ValueError('Foreign return receipt')
        received=datetime.fromisoformat(receipt['at'])
        if received.tzinfo is None:raise ValueError('Receipt time must be explicit')
        authorized=[datetime.fromisoformat(e['at']) for e in events if e['fact_id']=='commercial_authorization']
        qa=[datetime.fromisoformat(e['at']) for e in events if e['fact_id']=='comparable_confirmed_failure']
        if authorized and received<max(authorized) or qa and received>min(qa):raise ValueError('Return receipt must follow authorization and precede returned-engine QA')
    gaps=[]
    for g in original['gaps']:
        values=facts.get(g['fact_id'],[])
        if values==[True]:continue
        gaps.append(dict(g,scenario_state='ambiguous_value' if len(set(values))>1 else 'not_met' if values==[False] else g['state']))
    return dict(scenario_id=document['scenario_id'],provenance='generated',scenario_only=True,
                scenario_conclusion_ready=not any(g['impact'].startswith('blocking_') for g in gaps),scenario_gaps=gaps,
                live_evaluation=original,business_conclusion=None,warranty_approval='not_performed',company_writes=0)


def build_scenario(task,variant):
    sid='scenario_'+task+'_'+variant;case=sid+'_case';start=datetime(2026,1,1,tzinfo=timezone.utc)
    ticket=dict(record_id='scenario_ticket',collection='tickets',fields={},values={'mapping:complaint_hours':{'state':'value','value':'100'}},source_reference={'native_value':case})
    report=dict(record_id='scenario_report',collection='jointinspectionreports',fields={},values={'mapping:inspection_defect_text':{'state':'value','value':'Scenario observation'},'mapping:inspection_failure_date':{'state':'value','value':'2026-01-01'}},source_reference={'native_value':sid+'_report'})
    evidence=dict(records=[ticket,report],reference_edges=[dict(record_id=report['record_id'],parent_record_id=ticket['record_id'],binding_id='identity:inspection_ticket',classification='direct_reference')])
    doc=dict(environment='isolated_scenario',scenario_id=sid,case_id=case,provenance='generated',task=task,evidence=evidence,inputs={'assessment_date':'2026-01-03','policy_id':'scenario_policy'},policies=[dict(policy_id='scenario_policy',revision=1,sha256='scenario_only',clauses={'coverage_mode':{'value':None}})],events=[])
    for i,(fact,kind) in enumerate(FACT_EVENTS.items()):
        if variant=='incomplete':continue
        event=dict(scenario_id=sid,case_id=case,provenance='generated',fact_id=fact,kind=kind,value=True,at=(start+timedelta(days=i+1 if i<6 else i+2)).isoformat())
        doc['events'].append(event)
        if variant=='ambiguous' and fact in ('commercial_authorization','physical_identity'):
            doc['events'].append(dict(event,value=False))
    if variant=='incomplete' and task=='inspection':doc['evidence']['records']=[ticket];doc['evidence']['reference_edges']=[]
    if variant=='ambiguous' and task=='inspection':doc['evidence']['reference_edges'][0]['classification']='candidate'
    # A returned-engine receipt is retained as a lifecycle event, not a fake
    # database record or an implicit provider of an unrelated requirement.
    doc['return_receipt']=dict(case_id=case,provenance='generated',at=(start+timedelta(days=7)).isoformat())
    return doc


def run(directory):
    directory=Path(directory)
    if directory.exists():raise ValueError('Choose a fresh isolated directory')
    directory.mkdir(mode=0o700,parents=True)
    results=[]
    for task in ('inspection','warranty','replacement','recurrence'):
        for variant in ('complete','incomplete','ambiguous'):
            doc=build_scenario(task,variant);result=evaluate_scenario(doc)
            expected=variant=='complete'
            if result['scenario_conclusion_ready']!=expected:raise ValueError('Unexpected independent scenario result: '+doc['scenario_id'])
            path=directory/(doc['scenario_id']+'.json');path.write_text(json.dumps(dict(scenario=doc,result=result),indent=2)+'\n');path.chmod(0o600)
            results.append(dict(task=task,variant=variant,passed=True,scenario_only=True))
    summary=dict(passed=True,checks=results,company_reads=0,company_writes=0,model_calls=0,live_application_writes=0)
    (directory/'report.json').write_text(json.dumps(summary,indent=2)+'\n');return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',required=True,type=Path);args=parser.parse_args()
    print(json.dumps(run(args.directory),indent=2))
