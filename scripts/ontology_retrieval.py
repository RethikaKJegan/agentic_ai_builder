"""Phase 2 terminal interface using the backend's exact preview/execute/inspect services.

Use a separate isolated application database. --credentials-database optionally
borrows owned encrypted credentials in memory from a read-only application DB;
it never copies credentials or writes to that source application database.
"""
import argparse
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.check_business_knowledge import readonly
from workflow_api.business_ontology import BusinessOntology
from workflow_api.business_retrieval import BusinessRetrieval
from workflow_api.data_sources import DataSources
from workflow_api.service import ApiFailure
from workflow_api.storage import WorkflowStore


def build(database,scope,credentials_database=None,use_ai=False):
    if not database.is_file():raise ValueError('Prepare an isolated knowledge store first.')
    if database.resolve()==(ROOT/'.local/workflows.sqlite3').resolve() or credentials_database and database.resolve()==credentials_database.resolve():
        raise ValueError('Use separate isolated application storage for this diagnostic.')
    env={}
    if credentials_database or use_ai:
        from scripts.integration_config import load_env
        env={**load_env(),**os.environ}
    auth=dict(subject=dict(workspace_id=scope[0],subject_id=scope[1]),decision='allow',permissions=['tools.read'],scopes=['workspace:read'])
    store=WorkflowStore(database);manager=DataSources(store,env)
    if credentials_database:
        owned=manager.owned
        def current_owned(db,authority,cid):
            # Local ownership must still exist; live ownership/access must agree.
            owned(db,authority,cid)
            with readonly(credentials_database) as source:
                row=source.execute('SELECT secret,document FROM data_source_connections WHERE connection_id=? AND workspace=? AND owner=?',(cid,*scope)).fetchone()
            if not row:raise ApiFailure('BUSINESS_SOURCE_DENIED','Current source ownership unavailable.',403)
            return row[0],json.loads(row[1])
        manager.owned=current_owned
    return BusinessRetrieval(BusinessOntology(store),manager,env=env),auth


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,required=True);p.add_argument('--workspace',default='local-workspace');p.add_argument('--owner',default='local-builder')
    p.add_argument('--credentials-database',type=Path)
    actions=p.add_subparsers(dest='action',required=True)
    preview=actions.add_parser('preview');preview.add_argument('--question',required=True);preview.add_argument('--request-key',required=True);preview.add_argument('--version');preview.add_argument('--inputs',default='{}');preview.add_argument('--use-ai',action='store_true')
    for name in ('execute','inspect'):
        action=actions.add_parser(name);action.add_argument('--request-id',required=True)
    args=p.parse_args()
    try:
        service,auth=build(args.database,(args.workspace,args.owner),args.credentials_database,getattr(args,'use_ai',False))
        if args.action=='preview':
            body=dict(question=args.question,request_key=args.request_key,inputs=json.loads(args.inputs),use_ai=args.use_ai)
            if args.version:body['version_id']=args.version
            result=service.preview(auth,body)
        elif args.action=='execute':result=service.execute(auth,args.request_id,{})
        else:result=service.inspect(auth,args.request_id)
        print(json.dumps(result,indent=2,allow_nan=False));return 0
    except (ApiFailure,ValueError,json.JSONDecodeError) as exc:
        print(json.dumps(dict(error=getattr(exc,'code','RETRIEVAL_INPUT'),message=str(exc))));return 1
    except Exception:
        print(json.dumps(dict(error='RETRIEVAL_UNAVAILABLE',message='Check isolated storage, current source access and local configuration.')));return 1


if __name__=='__main__':sys.exit(main())
