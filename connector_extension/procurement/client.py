"""Local operator helper for setup/status; never approves runtime actions."""
import argparse
import json
from pathlib import Path
import requests
from uuid import uuid4


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['setup','status','advance'])
    parser.add_argument('--plan',type=Path)
    parser.add_argument('--project-id')
    parser.add_argument('--ui-port',type=int,default=3002)
    args=parser.parse_args()
    if not 1024<=args.ui_port<=65535:parser.error('Use an unprivileged isolated UI port.')
    if args.command=='setup' and not args.plan:parser.error('setup requires --plan.')
    if args.command!='setup' and not args.project_id:parser.error('status/advance require --project-id.')
    base=f'http://127.0.0.1:{args.ui_port}/api/backend'
    with requests.Session() as session:
        session.get(base+'/session',timeout=15).raise_for_status()
        if args.command=='status':response=session.get(base+'/procurement/projects/'+args.project_id,timeout=30)
        else:
            payload=json.loads(args.plan.read_text()) if args.command=='setup' else {'project_id':args.project_id}
            path='/procurement/projects' if args.command=='setup' else '/procurement/projects/'+args.project_id+'/advance'
            response=session.post(base+path,json={'request_id':'req_'+uuid4().hex,
                'operation':'procurement_'+args.command,'idempotency_key':'client_'+uuid4().hex,'payload':payload},timeout=300)
        print(json.dumps(response.json(),indent=2));response.raise_for_status()


if __name__=='__main__':main()
