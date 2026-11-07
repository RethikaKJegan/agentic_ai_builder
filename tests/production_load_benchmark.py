"""Bounded sustained local process workload. No live provider or model transport."""
import json
import argparse
from tests.worker_scaling_benchmark import measure

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--postgres',action='store_true');args=parser.parse_args()
    if args.postgres:
        from tests import worker_scaling_benchmark as benchmark
        from tests.test_distributed_postgres import ToolPostgresFixture
        benchmark.ToolGraphTests=ToolPostgresFixture
    results=[measure(n,multi_active=True,processes=True,jobs=96,delay=.15) for n in (1,2,4)]
    qualification=dict(targets={'lost_jobs':0,'duplicate_effects':0,'max_completion_seconds':180,'p99_seconds':120},host_scope='One development host, '+('PostgreSQL' if args.postgres else 'SQLite')+' workflow persistence, separate worker processes and controlled 150ms effects; not multi-host qualification. Auxiliary provider double ledger uses SQLite.',results=results)
    for result in results:
        assert result['lost_jobs']==0 and result['duplicate_effects']==0
        assert result['elapsed_seconds']<=180 and result['p99_latency_seconds']<=120
    print(json.dumps(qualification,indent=2))
