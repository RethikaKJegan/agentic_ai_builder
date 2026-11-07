"""Deterministic scoped alert conditions; no records, credentials or remote sends."""
import time


def evaluate(snapshot,*,queue_threshold=100,oldest_seconds=300):
    alerts=[]
    def emit(code,severity,count,action):
        alerts.append(dict(code=code,severity=severity,count=count,action=action))
    workers=snapshot.get('workers',[])
    if not workers or all(w['state'] in ('stale','stopped','failed') for w in workers):
        emit('WORKERS_UNAVAILABLE','critical',len(workers),'Restore worker connectivity; retain queued job identities.')
    if snapshot.get('queued',0)>=queue_threshold:emit('QUEUE_BACKLOG','warning',snapshot['queued'],'Inspect capacity, provider windows and worker health.')
    if snapshot.get('oldest_queue_seconds',0)>=oldest_seconds:emit('QUEUE_WAIT_EXCEEDED','warning',1,'Inspect runnable ownership and dependency failures.')
    for key,code,action in [('dead_letter','DEAD_LETTER_JOBS','Review failed dispatch and original invocation identity.'),('unknown_effects','RECONCILIATION_REQUIRED','Verify provider and connector journal before any retry.'),('failed_runs','RUN_FAILURES','Inspect correlated run errors and recovery eligibility.'),('stale_graphs','KNOWLEDGE_REFRESH_REQUIRED','Refresh authorized evidence; preserve historical workflow pins.'),('component_failures','WORKER_COMPONENT_FAILURES','Inspect component health and correlated errors.'),('model_failures','MODEL_FAILURES','Review structured outputs and supported model configuration.'),('connector_failures','CONNECTOR_FAILURES','Review provider health and current authorization before retrying.')]:
        if snapshot.get(key,0):emit(code,'warning',snapshot[key],action)
    return alerts


def inspect(service,workspace,now=None):
    from .worker_control import health
    now=time.time() if now is None else now
    snapshot=health(service.store,workspace,clock=lambda:now)
    with service.store.transaction(write=False) as db:
        rows=db.execute("SELECT json_extract(document,'$.status'),COUNT(*) FROM runtime_runs WHERE workspace=? GROUP BY json_extract(document,'$.status')",(workspace,)).fetchall() if snapshot['runtime_available'] else []
        counts=dict(rows)
        oldest=db.execute("SELECT MIN(CAST(json_extract(document,'$.created_at') AS DOUBLE PRECISION)) FROM runtime_runs WHERE workspace=? AND json_extract(document,'$.status')='queued'",(workspace,)).fetchone()[0] if snapshot['runtime_available'] else None
        model_failures=sum(count for code,count in db.execute("SELECT json_extract(document,'$.error_code'),COUNT(*) FROM runtime_runs WHERE workspace=? AND json_extract(document,'$.status') IN ('failed','blocked') GROUP BY json_extract(document,'$.error_code')",(workspace,)).fetchall() if code in {'AGENT_OUTPUT_INVALID','MODEL_OUTPUT_SCHEMA_INVALID','MODEL_OUTPUT_TRUNCATED','INVESTIGATION_AGENT_REFERENCE','INVESTIGATION_AGENT_OUTPUT'}) if snapshot['runtime_available'] else 0
        connector_failures=db.execute("SELECT COUNT(*) FROM runtime_runs WHERE workspace=? AND json_extract(document,'$.status') IN ('failed','blocked') AND json_extract(document,'$.error_code') IN ('CONNECTOR_TIMEOUT','CONNECTOR_AUTH_FAILED','PROVIDER_REQUEST_FAILED','SMTP_DELIVERY_UNCERTAIN')",(workspace,)).fetchone()[0] if snapshot['runtime_available'] else 0
        uncertain=db.execute("SELECT COUNT(*) FROM runtime_runs WHERE workspace=? AND json_extract(document,'$.status')='blocked' AND json_extract(document,'$.error_code') IN ('UNKNOWN_INVOCATION_RESULT','SMTP_DELIVERY_UNCERTAIN','ACTION_EFFECT_UNVERIFIED','POST_INVOCATION_REVALIDATION_FAILED')",(workspace,)).fetchone()[0] if snapshot['runtime_available'] else 0
        available=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='account_graph_heads'").fetchone()
        stale=db.execute("SELECT COUNT(*) FROM account_graph_heads WHERE workspace=? AND (state<>'current' OR checked_at<?)",(workspace,now-300)).fetchone()[0] if available else 0
    facts=dict(component_failures=sum(c.get('state')=='error' for c in snapshot['components']),model_failures=model_failures,connector_failures=connector_failures,workers=snapshot['workers'],queued=counts.get('queued',0),failed_runs=counts.get('failed',0),unknown_effects=uncertain,dead_letter=snapshot['dispatch'].get('dead_letter',0),oldest_queue_seconds=max(0,now-oldest) if oldest is not None else 0,stale_graphs=stale)
    return dict(observed_at=now,alerts=evaluate(facts),counts={k:v for k,v in facts.items() if k!='workers'},qualification='Current persisted counts and heartbeat thresholds; blocked runs require inspection and may not contain an external effect. No alert delivery is configured.')
