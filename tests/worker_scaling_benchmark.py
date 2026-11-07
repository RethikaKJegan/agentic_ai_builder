"""Reproducible offline I/O workload through actual Registry, approvals and runtime.

Run with python -B -m tests.worker_scaling_benchmark [--multi-active].
The provider double uses its own durable ledger and never accesses a network.
"""
import argparse
import json
import multiprocessing
from pathlib import Path
import sqlite3
import statistics
import tempfile
import time

from runtime.worker import RuntimeWorker
from workflow_api.worker_control import WorkerSupervisor
from tests.test_runtime import ToolGraphTests


def measure(count, *, multi_active=False, processes=False, jobs=16, delay=.15):
    f = ToolGraphTests()
    f.setUp()
    with tempfile.TemporaryDirectory(prefix='builder-scaling-') as directory:
        try:
            f.configure()
            f.put()
            if multi_active:
                from workflow_api.resource_limits import ResourceControls,ResourcePolicy
                f.runtime.resource_controls=ResourceControls(f.store,ResourcePolicy())
            ledger = Path(directory) / 'provider.sqlite3'
            with sqlite3.connect(ledger) as db:
                db.execute('CREATE TABLE effects (reference TEXT PRIMARY KEY, started REAL, finished REAL)')
            def invoke(binding, params, reference):
                started = time.time()
                time.sleep(delay)
                with sqlite3.connect(ledger) as db:
                    db.execute('INSERT INTO effects VALUES (?,?,?)', (reference, started, time.time()))
                return {'message_id': reference}
            f.connector.invoke = invoke
            runs = []
            for index in range(jobs):
                request = f.request()
                request['idempotency_key'] = 'scaling_request_' + str(index)
                rid = f.runtime.create_run(request, f.auth)['run_id']
                paused = f.graph.advance(rid, f.auth)
                decision = f.decision(paused, 'approved')
                decision['idempotency_key'] += str(index)
                f.graph.decide(decision, f.approver())
                runs.append(rid)
            workers = [RuntimeWorker(f.graph, lambda *_: f.auth, interval=.01,fair=multi_active) for _ in range(count)]
            supervisors = [WorkerSupervisor(f.store, [] if multi_active else [w],
                **({'parallel_workers': [w]} if multi_active else {})) for w in workers]
            context=multiprocessing.get_context('fork')
            stop=context.Event();statuses=context.Queue();children=[]
            def consume(supervisor):
                baseline=dict(f.store.metrics)
                supervisor.start()
                try:stop.wait(180)
                finally:
                    active=bool(supervisor.owned or supervisor.parallel_started)
                    supervisor.stop()
                    statuses.put((active,{key:value-baseline[key] for key,value in f.store.metrics.items()}))
            child_metrics=[]
            started = time.time()
            try:
                for supervisor in supervisors:
                    if processes:
                        child=context.Process(target=consume,args=(supervisor,));child.start();children.append(child)
                    else:supervisor.start()
                while time.time() - started < 180:
                    with f.store.transaction(write=False) as db:
                        states = [json.loads(r[0]) for r in db.execute('SELECT document FROM runtime_runs').fetchall()]
                    if all(r['status'] == 'completed' for r in states):
                        break
                    time.sleep(.02)
                else:
                    raise AssertionError('Benchmark failed to complete; inspect run states.')
                elapsed = time.time() - started
                if processes:
                    stop.set();observations=[statuses.get(timeout=20) for _ in children]
                    active=sum(item[0] for item in observations);child_metrics=[item[1] for item in observations]
                else:active = sum(bool(s.owned or getattr(s, 'parallel_started', False)) for s in supervisors)
            finally:
                if processes:
                    stop.set()
                    for child in children:
                        child.join(10)
                        if child.is_alive():child.kill();child.join(5)
                        assert child.exitcode==0
                else:
                    for supervisor in supervisors:supervisor.stop()
            with sqlite3.connect(ledger) as db:
                effects = db.execute('SELECT started,finished FROM effects').fetchall()
            with f.store.transaction(write=False) as db:
                retries=sum(json.loads(row[0])['event_type']=='node.retry' for row in db.execute('SELECT document FROM runtime_events').fetchall())
            assert len(effects) == jobs
            assert len({r['run_id'] for r in states}) == jobs
            latencies = sorted(end - started for _, end in effects)
            starts = sorted(start - started for start, _ in effects)
            peak = max(sum(a <= point < b for a, b in effects) for point, _ in effects)
            return dict(workers=count, active_workers=active, jobs=jobs, elapsed_seconds=elapsed,
                throughput_per_second=jobs / elapsed, average_latency_seconds=statistics.mean(latencies),
                p95_latency_seconds=latencies[min(len(latencies)-1, int(.95*len(latencies)))],
                p50_latency_seconds=statistics.median(latencies),p99_latency_seconds=latencies[min(len(latencies)-1,int(.99*len(latencies)))], average_queue_wait_seconds=statistics.mean(starts), concurrent_effects_peak=peak,
                duplicate_effects=0, lost_jobs=0, retry_events=retries, effect_busy_fraction=sum(b-a for a,b in effects)/(count*elapsed), database_metrics={key:value+sum(m[key] for m in child_metrics) for key,value in f.store.metrics.items()},
                qualification='Actual runtime/Registry/approval transactions; controlled 150ms provider latency; '+('processes' if processes else 'threads')+' on one host with '+('PostgreSQL' if f.store.database else 'SQLite')+' workflow persistence; no live effect. Database metrics include parent setup and child execution transactions.')
        finally:
            f.doCleanups()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--multi-active', action='store_true')
    parser.add_argument('--processes',action='store_true')
    args = parser.parse_args()
    print(json.dumps([measure(n, multi_active=args.multi_active,processes=args.processes) for n in (1, 2, 4)], indent=2))
