"""Phase 4 backend case CLI: isolated diagnostics or the authenticated existing backend.

Examples:
  python scripts/business_cases.py --database /tmp/cases.sqlite publish --json process.json
  python scripts/business_cases.py --database /tmp/cases.sqlite create --json case.json
  python scripts/business_cases.py --database /tmp/cases.sqlite inspect --case-id case_...

JSON arguments name local files. Commands are durable and require request keys and
expected revisions. This diagnostic launcher never installs a paid model or a write tool.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.capability_composition import build
from workflow_api.business_cases import BusinessCases
from workflow_api.service import ApiFailure


def remote(args, body):
    from urllib.parse import urlsplit, quote
    from urllib.request import Request, build_opener, HTTPRedirectHandler
    from urllib.error import HTTPError
    parsed=urlsplit(args.api_url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname or (parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('localhost','127.0.0.1'))):
        raise ValueError('Use an HTTPS backend URL or a localhost HTTP URL.')
    if not args.cookie_file:raise ValueError('Supply a file containing your existing backend session Cookie header.')
    cookie=args.cookie_file.read_text().strip()
    if not cookie or len(cookie)>8192 or '=' not in cookie or any(ord(c)<32 for c in cookie):raise ValueError('Invalid session cookie file.')
    base=args.api_url.rstrip('/')+'/business-ontology/v1'
    if args.operation=='publish':path='/process-definitions'
    elif args.operation=='create':path='/cases'
    else:
        path='/cases/'+quote(args.case_id,safe='')
        if args.operation=='inspect':
            section={'execution_history':'timeline','source_evidence':'evidence'}.get(args.section,args.section)
            if section!='all':path+='/sections/'+section
        else:path+='/'+('events' if args.operation=='event' else args.operation)
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self,*_args,**_kwargs):return None
    request=Request(base+path,data=json.dumps(body,allow_nan=False).encode() if body is not None else None,
                    headers={'Cookie':cookie,'Content-Type':'application/json'},method='GET' if args.operation=='inspect' else 'POST')
    try:
        with build_opener(NoRedirect()).open(request,timeout=600) as response:result=json.load(response)
    except HTTPError as exc:
        raise ApiFailure('CASE_BACKEND_REQUEST_FAILED','Backend rejected the command; inspect your session, permissions and current case revision.',exc.code) from None
    if result.get('status')!=200 or not isinstance(result.get('data'),dict):raise ValueError('Invalid backend response.')
    return result['data']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    target=parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--database',type=Path)
    target.add_argument('--api-url')
    parser.add_argument('--cookie-file',type=Path)
    parser.add_argument('--workspace',default='local-workspace')
    parser.add_argument('--owner',default='local-builder')
    commands=parser.add_subparsers(dest='operation',required=True)
    for name in ('publish','create','prepare','start','advance','resume','cancel','input','event','inspect'):
        sub=commands.add_parser(name)
        if name not in ('publish','create'):sub.add_argument('--case-id',required=True)
        if name!='inspect':sub.add_argument('--json',type=Path,required=True)
        else:sub.add_argument('--section',choices=['all','stages','assumptions','conflicts','waits','execution_history','timeline','source_evidence','evidence','agents','tools','outcomes'],default='all')
    args=parser.parse_args()
    try:
        body=json.loads(args.json.read_text()) if args.operation!='inspect' else None
        if args.api_url:
            print(json.dumps(remote(args,body),indent=2,allow_nan=False));return 0
        if args.database.resolve()==(ROOT/'.local/workflows.sqlite3').resolve():
            raise ValueError('Use an isolated diagnostic database.')
        if not args.database.exists():
            from workflow_api.storage import WorkflowStore
            WorkflowStore(args.database)
        composition,auth=build(args.database,(args.workspace,args.owner))
        auth['permissions']=sorted(set(auth['permissions'])|{'workflow.execute','events.ingest'})
        auth['scopes']=sorted(set(auth['scopes'])|{'workspace:write'})
        service=BusinessCases(composition.service)
        if args.operation in ('publish','create'):result=getattr(service,args.operation)(auth,body)
        elif args.operation=='event':result=service.event(auth,args.case_id,body)
        elif args.operation=='inspect':
            result=service.get(auth,args.case_id)
            if args.section!='all':result=service.section(auth,args.case_id,{'execution_history':'timeline','source_evidence':'evidence'}.get(args.section,args.section))
        else:result=service.command(auth,args.case_id,args.operation,body)
        print(json.dumps(result,indent=2,allow_nan=False));return 0
    except Exception as exc:
        print(json.dumps({'error':getattr(exc,'code','CASE_UNAVAILABLE'),'message':str(exc) if getattr(exc,'code',None) else 'Inspect isolated case configuration.'}));return 1


if __name__=='__main__':sys.exit(main())
