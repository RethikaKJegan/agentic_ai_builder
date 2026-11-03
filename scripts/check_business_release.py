"""Offline release gaps and owned ontology-artifact recovery; no deployment.

Exit 2: audit completed, public release not ready. Exit 1: audit unavailable.
Use a quiescent SQLite snapshot and a fresh private output directory.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from workflow_api.business_release import run

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,required=True);p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--workspace',required=True);p.add_argument('--owner',required=True)
    p.add_argument('--period-start',required=True);p.add_argument('--period-end',required=True)
    args=p.parse_args()
    try:
        result=run(args.database,args.directory,args.workspace,args.owner,args.period_start,args.period_end)
        print(json.dumps({k:result[k] for k in ['audit_version','public_release_status','accepted_business_answers','input_store_unchanged','report_sha256']}))
        sys.exit(2)
    except Exception as exc:
        print(json.dumps(dict(status='unavailable',error_type=type(exc).__name__)));sys.exit(1)
