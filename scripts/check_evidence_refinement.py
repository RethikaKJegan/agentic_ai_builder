"""Independent bounded live-source checks in a fresh isolated application store.

No model calls, company writes, live application writes or credential copies.
Only requested ticket IDs are read. Output contains company evidence; keep private.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.check_business_knowledge import run as prepare,readonly
from scripts.ontology_retrieval import build
from scripts.integration_config import private_write
from workflow_api.business_investigations import BusinessInvestigations


def run(database,directory,scope,tickets):
    baseline=prepare(database,directory,scope)
    retrieval,auth=build(directory/'isolated.sqlite3',scope,database)
    auth['permissions'].append('workflow.execute')
    investigations=BusinessInvestigations(retrieval)
    with retrieval.store.transaction(write=False) as db:
        workspace=retrieval.ontology.document(db,scope)
        secret,_=retrieval.manager.owned(db,auth,workspace['sources']['service'])
    config=json.loads(retrieval.manager.cipher.decrypt(secret.encode()))
    checks=[]
    for index,ticket_id in enumerate(tickets):
        with retrieval.manager.adapter.connection(config) as client:
            source=client[config['database']]
            ticket=source['tickets'].find_one({'_id':ticket_id},{'_id':1,'engineNo':1,'serviceEngineer':1,'complaintRecord.natureOfCustomerComplaint':1},max_time_ms=3000)
            if not ticket:raise ValueError('Requested complaint not found')
            reports=list(source['jointinspectionreports'].find({'ticketId':ticket['_id']},{'_id':1,'dateOfFailure':1}).sort('_id',1).limit(21).max_time_ms(3000))
            timeline=list(source['tickettimelines'].find({'ticketId':ticket['_id']},{'_id':1}).sort('_id',1).limit(21).max_time_ms(3000))
            code=source['simpsoncodes'].find_one({'_id':ticket.get('complaintRecord',{}).get('natureOfCustomerComplaint')},{'_id':1,'code':1,'description':1,'codeType':1},max_time_ms=3000)
            engineer=source['users'].find_one({'_id':ticket.get('serviceEngineer')},{'_id':1},max_time_ms=3000)
            invoices=list(source['enginedetails'].find({'engineSerialNumber':ticket.get('engineNo')},{'_id':1}).sort('_id',1).limit(21).max_time_ms(3000))
        for task,objective in [
            ('inspection','Compare complaint '+ticket_id+' with its linked inspection and prepare a source-backed report.'),
            ('warranty','Check warranty readiness for complaint '+ticket_id+' and prepare a report.'),
            ('replacement','Review replacement evidence for complaint '+ticket_id+' and prepare a report.'),
            ('recurrence','Review corrective-action effectiveness evidence for complaint '+ticket_id+' and prepare a report.'),
        ]:
            key='refinement_'+str(index)+'_'+task
            plan=investigations.plan(auth,dict(objective=objective,request_key=key,planning_mode='offline',analysis_mode='offline'))
            pending=investigations.create_run(auth,plan['workflow_id'],dict(request_key=key+'_run'))
            result=investigations.execute(auth,pending['run_id'],{})
            if result['status']!='completed':raise ValueError('Offline source workflow failed: '+json.dumps(result['node_errors']))
            report=result['outputs']['end'];observed={r['fields']['_id'] for r in report['source_records'] if r['collection']=='jointinspectionreports'}
            if task=='inspection':
                assert observed=={str(r['_id']) for r in reports[:20]},'Independent inspection ID mismatch'
                assert {r['fields']['_id'] for r in report['source_records'] if r['collection']=='tickettimelines'}=={str(r['_id']) for r in timeline[:20]},'Independent timeline reference mismatch'
                views=report['resolved_references']
                if code and code.get('description') and code.get('codeType') in (None,'COMPLAINT'):
                    matches=[v for v in views if v['kind']=='controlled_code' and v['resolved_values'].get('mapping:code_description')==code['description']]
                    assert matches,'Independent controlled-code description mismatch'
                if engineer:assert any(v['kind']=='engineer' and v['status']=='resolved' for v in views),'Independent user reference mismatch'
                from datetime import datetime
                by_id={r['fields']['_id']:r for r in report['source_records'] if r['collection']=='jointinspectionreports'}
                for native in reports[:20]:
                    raw=native.get('dateOfFailure');value=by_id[str(native['_id'])]['values']['mapping:inspection_failure_date']
                    if isinstance(raw,str) and len(raw)==10 and raw[2:3]=='-' and raw[5:6]=='-':
                        try:expected=datetime.strptime(raw,'%d-%m-%Y').date().isoformat()
                        except ValueError:assert value['state']=='conversion_issue'
                        else:assert value['value']==expected and value['raw_value']==raw
                assert not any(g['task']=='warranty' or g['fact_id']=='actual_incorporation' for g in report['missing_information'])
            if task=='warranty':
                actual={r['fields']['_id'] for r in report['source_records'] if r['collection']=='enginedetails'}
                assert actual=={str(r['_id']) for r in invoices[:20]},'Independent invoice candidate ID mismatch'
            assert len({g['gap_id'] for g in report['normalized_gaps']})==len(report['normalized_gaps'])
            assert report['warranty_approval']=='not_performed' and report['physical_engine_identity']=='unresolved'
            assert result['usage']['model_calls']==0
            checks.append(dict(ticket=ticket_id,task=task,passed=True,run_id=result['run_id'],normalized_gap_count=len(report['normalized_gaps']),resolved_reference_count=len(report['resolved_references']),model_calls=0))
            for name,data in [('plan',plan),('run',result),('report',report)]:private_write(directory/(key+'-'+name+'.json'),json.dumps(data,indent=2)+'\n')
    with readonly(database) as db:
        current=db.execute('select version_id,document from business_ontology_versions where workspace=? and owner=? order by version_id',scope).fetchall()
    with readonly(directory/'isolated.sqlite3') as db:
        copied=db.execute('select version_id,document from business_ontology_versions where workspace=? and owner=? order by version_id',scope).fetchall()
    assert all(row in copied for row in current),'Original immutable versions changed'
    summary=dict(passed=True,baseline=baseline,checks=checks,planning_mode='offline',analysis_mode='offline',model_calls=0,company_writes=0,live_application_writes=0,copied_credentials=0)
    private_write(directory/'refinement-report.json',json.dumps(summary,indent=2)+'\n');return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--database',type=Path,required=True);parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--workspace',default='local-workspace');parser.add_argument('--owner',default='local-builder');parser.add_argument('--complaint-id',action='append',required=True)
    args=parser.parse_args()
    try:print(json.dumps(run(args.database,args.directory,(args.workspace,args.owner),args.complaint_id),indent=2))
    except Exception as exc:
        print(json.dumps(dict(passed=False,error_type=type(exc).__name__,code=getattr(exc,'code',None),message=str(exc) if isinstance(exc,(ValueError,AssertionError)) else 'Check source availability and isolated artifacts.')));sys.exit(1)
