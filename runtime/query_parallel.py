"""Bounded scheduling of already durable read-only queries, under the run lease."""

def query_limit(env, resource_policy=None):
    # Trusted service configuration; workflow/model metadata cannot raise limits.
    limits=[4, int(env.get('BUILDER_QUERY_CONCURRENCY','2')),
            int(env.get('BUILDER_ACCOUNT_QUERY_CONCURRENCY','2'))]
    if resource_policy is not None:limits.append(resource_policy.agents_per_workflow)
    if any(v<1 or v>4 for v in limits):raise ValueError('Query concurrency must be 1–4.')
    return min(limits)


def eligible(runner, run, ready, excluded):
    pending=run.get('query_waits',{})
    ready=[n for n in ready if n['node_id'] not in excluded]
    if not pending:return ready
    limit=run.get('query_concurrency',1)
    return [n for n in ready if n['kind']=='tool' and
            getattr(runner.connectors.get(n.get('tool_id')), 'durable_query', False) and
            not getattr(runner.connectors.get(n.get('tool_id')), 'external_write', True) and
            (n['node_id'] in pending or len(pending)<limit)]


def stop_queries(db,run):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='data_query_governance'").fetchone():return
    db.execute("UPDATE data_query_jobs SET state=CASE WHEN state='queued' THEN 'cancelled' ELSE 'cancel_requested' END WHERE state IN ('queued','validating','running','finalizing') AND job_id IN (SELECT job_id FROM data_query_governance WHERE workspace=? AND owner=? AND run_id=?)", (run['workspace_id'],run['subject_id'],run['run_id']))
