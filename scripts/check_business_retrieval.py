"""Fresh isolated Phase 2 acceptance with bounded independent live read expectations.

Company records are saved only in the explicitly selected private output directory.
No model calls, source writes, live application writes or credential copies.
"""
import argparse
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.check_business_knowledge import run as prepare,readonly
from scripts.ontology_retrieval import build
from scripts.integration_config import private_write
from workflow_api.business_knowledge_model import digest


def run(database,directory,scope,live=False):
    baseline=prepare(database,directory,scope)
    service,auth=build(directory/'isolated.sqlite3',scope,database if live else None)
    with readonly(database) as db:
        before=db.execute('SELECT version_id,document FROM business_ontology_versions WHERE workspace=? AND owner=? ORDER BY version_id',scope).fetchall()
    summary=dict(phase1_baseline=baseline,live=live,model_calls=0,company_writes=0,live_application_writes=0,copied_credentials=0,checks=[])
    if live:
        # Independently choose a real linked complaint; expected IDs come from
        # explicit source queries, never from the resolver's response.
        with service.store.transaction(write=False) as db:
            workspace=service.ontology.document(db,scope)
            secret,connection=service.manager.owned(db,auth,workspace['sources']['service'])
        config=json.loads(service.manager.cipher.decrypt(secret.encode()))
        with service.manager.adapter.connection(config) as client:
            source=client[config['database']]
            pairs=list(source['jointinspectionreports'].find({'ticketId':{'$ne':None}},{'_id':1,'ticketId':1}).limit(5).max_time_ms(3000))
            ticket=None
            for pair in pairs:
                ticket=source['tickets'].find_one({'_id':pair['ticketId']},{'_id':1,'engineNo':1})
                if ticket:break
            if not ticket:raise ValueError('No linked inspection sample available.')
            expected=list(source['jointinspectionreports'].find({'ticketId':ticket['_id']},{'_id':1}).limit(21).max_time_ms(3000))
            expected_ids={str(r['_id']) for r in expected[:20]}
            serial=ticket.get('engineNo')
            expected_tickets=list(source['tickets'].find({'engineNo':serial},{'_id':1}).sort('_id',1).limit(21).max_time_ms(3000)) if isinstance(serial,str) and serial else []
        cases=[('linked_inspection','Show inspection findings for complaint '+str(ticket['_id'])+'.',{'jointinspectionreports':expected_ids,'tickets':{str(ticket['_id'])}})]
        if expected_tickets:
            cases.append(('serial_complaints','Show complaints for engine '+serial+'.',{'tickets':{str(r['_id']) for r in expected_tickets[:20]}}))
        with service.store.transaction(write=False) as db:
            secret,_=service.manager.owned(db,auth,workspace['sources']['quality'])
        quality_config=json.loads(service.manager.cipher.decrypt(secret.encode()))
        with service.manager.adapter.connection(quality_config) as quality_client,service.manager.adapter.connection(config) as service_client:
            quality=quality_client[quality_config['database']];source=service_client[config['database']]
            observations=list(quality['failedengineanalyses'].find({'engineSerialNumber':{'$type':'string'}},{'_id':1,'engineSerialNumber':1}).limit(5).max_time_ms(3000))
            if observations:
                observation=observations[0]
                for candidate in observations:
                    if source['enginedetails'].find_one({'engineSerialNumber':candidate['engineSerialNumber']},{'_id':1}):
                        observation=candidate;break
                history_serial=observation['engineSerialNumber']
                history_expected={}
                for dbname,collection,field in [(source,'tickets','engineNo'),(source,'enginedetails','engineSerialNumber'),(quality,'failedengineanalyses','engineSerialNumber')]:
                    ids=list(dbname[collection].find({field:history_serial},{'_id':1}).sort('_id',1).limit(21).max_time_ms(3000))
                    history_expected[collection]={str(r['_id']) for r in ids[:20]}
                cases.append(('two_source_history','Show history for engine '+history_serial+'.',history_expected))
        for name,question,expected_by_collection in cases:
            p=service.preview(auth,dict(question=question,request_key='phase2_live_'+name))
            if not p['ready']:raise ValueError('Real source preview is not ready: '+json.dumps(p['missing']))
            result=service.execute(auth,p['request_id'],{})
            actual={collection:{r['fields']['_id'] for r in result['records'] if r['collection']==collection} for collection in expected_by_collection}
            passed=all(actual[c]==ids for c,ids in expected_by_collection.items())
            summary['checks'].append(dict(name=name,passed=passed,expected_counts={c:len(v) for c,v in expected_by_collection.items()},actual_counts={c:len(v) for c,v in actual.items()},request_id=p['request_id'],version_id=result['version_id'],completeness=result['completeness'],executed_steps=result['executed_steps']))
            private_write(directory/(name+'-preview.json'),json.dumps(p,indent=2)+'\n')
            private_write(directory/(name+'-evidence.json'),json.dumps(result,indent=2)+'\n')
            if not passed:raise ValueError('Independent source record comparison failed.')
    else:
        p=service.preview(auth,dict(question='Show complaints for engine E123.',request_key='phase2_metadata_preview'))
        summary['checks'].append(dict(name='metadata_preview',passed=p['ready'],version_id=p['version_id'],mapping_count=len(p['mappings']),steps=len(p['steps']),company_reads=p['company_reads']))
    with readonly(database) as db:
        after=db.execute('SELECT version_id,document FROM business_ontology_versions WHERE workspace=? AND owner=? ORDER BY version_id',scope).fetchall()
    summary['original_knowledge_unchanged']=before==after
    summary['passed']=all(c['passed'] for c in summary['checks']) and before==after
    private_write(directory/'phase2-report.json',json.dumps(summary,indent=2)+'\n')
    if not summary['passed']:raise ValueError('Phase 2 integration check failed.')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--workspace',default='local-workspace');p.add_argument('--owner',default='local-builder');p.add_argument('--live-sources',action='store_true');a=p.parse_args()
    try:print(json.dumps(run(a.database,a.directory,(a.workspace,a.owner),a.live_sources),indent=2))
    except Exception as e:
        print(json.dumps(dict(passed=False,error_type=type(e).__name__,code=getattr(e,'code',None),message=str(e) if isinstance(e,ValueError) else 'Check source availability and scoped credentials.')));sys.exit(1)
