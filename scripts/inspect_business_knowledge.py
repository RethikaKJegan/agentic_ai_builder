"""Inspect/diagnose saved knowledge read-only, or explicitly import a package.

No .env, company connectors, model calls, workers or frontend dependency.
Import requires local database access and explicit --import-package.
"""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from workflow_api.business_ontology import BusinessOntology
from workflow_api.business_knowledge import BusinessKnowledge
from workflow_api.service import ApiFailure


class ReadOnlyStore:
    def __init__(self,path):self.path=str(path)
    @contextmanager
    def transaction(self,write=False):
        if write:raise ValueError('Read-only inspection')
        db=sqlite3.connect(Path(self.path).resolve().as_uri()+'?mode=ro',uri=True)
        try:
            db.execute('PRAGMA query_only=ON');db.execute('BEGIN');yield db
        finally:db.rollback();db.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,required=True);p.add_argument('--workspace',required=True);p.add_argument('--owner',required=True)
    p.add_argument('--version',default='latest')
    actions=p.add_mutually_exclusive_group();actions.add_argument('--concept');actions.add_argument('--diagnostic-json');actions.add_argument('--import-package',action='store_true')
    p.add_argument('--expected-revision',type=int);p.add_argument('--request-key')
    args=p.parse_args()
    try:
        if not args.database.is_file():raise ValueError('Database must already exist')
        scope=(args.workspace,args.owner)
        auth=dict(subject=dict(workspace_id=scope[0],subject_id=scope[1]),decision='allow',permissions=['tools.read']+(['tools.assign'] if args.import_package else []),scopes=['workspace:read']+(['workspace:write'] if args.import_package else []))
        if args.import_package:
            if args.expected_revision is None or not args.request_key:raise ValueError('Import requires expected revision and request key')
            from workflow_api.storage import WorkflowStore
            ontology=BusinessOntology(WorkflowStore(args.database))
        else:
            ontology=object.__new__(BusinessOntology);ontology.store=ReadOnlyStore(args.database)
        service=BusinessKnowledge(ontology)
        if args.import_package:result=service.import_package(auth,dict(expected_revision=args.expected_revision,request_key=args.request_key))
        else:
            version=args.version
            if version=='latest':
                with ontology.store.transaction(write=False) as db:
                    row=db.execute('SELECT version_id FROM business_ontology_versions WHERE workspace=? AND owner=? ORDER BY CAST(json_extract(document,\'$.revision\') AS INTEGER) DESC LIMIT 1',scope).fetchone()
                if not row:raise ValueError('Owned version unavailable')
                version=row[0]
            result=service.diagnose(auth,version,json.loads(args.diagnostic_json)) if args.diagnostic_json else service.inspect(auth,version,args.concept)
        print(json.dumps(result,indent=2,allow_nan=False));return 0
    except (ApiFailure,ValueError,json.JSONDecodeError) as e:
        print(json.dumps(dict(error=getattr(e,'code','BUSINESS_KNOWLEDGE_INPUT'),message=str(e))));return 1


if __name__=='__main__':sys.exit(main())
