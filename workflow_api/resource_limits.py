"""Server-owned admission/concurrency and durable per-account provider windows.

No workflow or model field is accepted as an override. Existing execution budgets
remain authoritative and reservations are never refunded after an unknown call.
"""
from dataclasses import dataclass, field
import json
import hashlib

from runtime.service import RuntimeFailure


class CapacityDeferred(RuntimeFailure):
    def __init__(self, code, retry_at):
        super().__init__(code, 'Server capacity is temporarily unavailable.', 429)
        self.retry_at = retry_at


@dataclass(frozen=True)
class ResourcePolicy:
    queued_per_account: int = 256
    running_per_account: int = 8
    agents_per_workflow: int = 4
    provider_per_minute: dict = field(default_factory=dict)
    max_deferrals: int = 64
    shared_provider_per_minute: dict = field(default_factory=dict)
    shared_credential_buckets: dict = field(default_factory=dict)
    total_concurrency: int = 128
    reserved_per_account: dict = field(default_factory=dict)

    def __post_init__(self):
        for name, maximum in [('queued_per_account',100000),('running_per_account',128),('agents_per_workflow',4),('max_deferrals',1000)]:
            value=getattr(self,name)
            if type(value) is not int or not 1<=value<=maximum:raise ValueError('Invalid server resource limit: '+name)
        if type(self.total_concurrency) is not int or not 1<=self.total_concurrency<=1024:raise ValueError('Invalid shared runtime capacity.')
        for values in (self.shared_provider_per_minute,self.reserved_per_account):
            if not isinstance(values,dict) or len(values)>100 or any(not isinstance(k,str) or not 1<=len(k)<=256 or type(v) is not int or not 1<=v<=100000 for k,v in values.items()):raise ValueError('Invalid trusted shared limits.')
        if sum(self.reserved_per_account.values())>self.total_concurrency or any(v>self.running_per_account for v in self.reserved_per_account.values()):raise ValueError('Reservations must fit total and account concurrency.')
        if not isinstance(self.shared_credential_buckets,dict) or len(self.shared_credential_buckets)>100 or any(not isinstance(k,str) or not isinstance(v,str) or not 1<=len(k)<=256 or v not in self.shared_provider_per_minute for k,v in self.shared_credential_buckets.items()):raise ValueError('Credential buckets must name configured shared limits.')
        if (not isinstance(self.provider_per_minute,dict) or len(self.provider_per_minute)>100 or
                any(not isinstance(k,str) or not 1<=len(k)<=128 or type(v) is not int or not 1<=v<=100000 for k,v in self.provider_per_minute.items())):
            raise ValueError('Provider limits require bounded provider IDs and positive integer rates.')

    @classmethod
    def from_environment(cls,env):
        return cls(queued_per_account=int(env.get('BUILDER_ACCOUNT_QUEUE_LIMIT','256')),
                   running_per_account=int(env.get('BUILDER_ACCOUNT_CONCURRENCY','8')),
                   agents_per_workflow=int(env.get('BUILDER_AGENT_CONCURRENCY','4')),
                   provider_per_minute=json.loads(env.get('BUILDER_PROVIDER_RATE_LIMITS','{}')),
                   shared_provider_per_minute=json.loads(env.get('BUILDER_SHARED_PROVIDER_RATE_LIMITS','{}')),
                   shared_credential_buckets=json.loads(env.get('BUILDER_CREDENTIAL_BUCKETS','{}')),
                   total_concurrency=int(env.get('BUILDER_TOTAL_CONCURRENCY','128')),
                   reserved_per_account=json.loads(env.get('BUILDER_ACCOUNT_RESERVED_CAPACITY','{}')))


class ResourceControls:
    def __init__(self,store,policy):
        self.store,self.policy=store,policy
        with store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS runtime_provider_windows (workspace TEXT NOT NULL, provider TEXT NOT NULL, minute_window BIGINT NOT NULL, used BIGINT NOT NULL, PRIMARY KEY(workspace,provider))')

            db.execute('CREATE TABLE IF NOT EXISTS runtime_shared_provider_windows (bucket TEXT PRIMARY KEY, minute_window BIGINT NOT NULL, used BIGINT NOT NULL)')

    def admit(self,db,workspace):
        count=db.execute("SELECT COUNT(*) FROM runtime_runs WHERE workspace=? AND json_extract(document,'$.status')='queued'",(workspace,)).fetchone()[0]
        if count>=self.policy.queued_per_account:
            raise RuntimeFailure('QUEUE_CAPACITY_EXCEEDED','The account queue is full; retain the same request identity and retry later.',429)

    def claim(self,db,run,now):
        count=db.execute("SELECT COUNT(*) FROM runtime_runs WHERE workspace=? AND run_id<>? AND json_extract(document,'$.status')='running' AND CAST(json_extract(document,'$.lease_until') AS DOUBLE PRECISION)>?",(run['workspace_id'],run['run_id'],now)).fetchone()[0]
        active=dict(db.execute("SELECT workspace,COUNT(*) FROM runtime_runs WHERE run_id<>? AND json_extract(document,'$.status')='running' AND CAST(json_extract(document,'$.lease_until') AS DOUBLE PRECISION)>? GROUP BY workspace",(run['run_id'],now)).fetchall())
        protected=sum(max(0,reserved-active.get(account,0)) for account,reserved in self.policy.reserved_per_account.items() if account!=run['workspace_id'])
        if sum(active.values())>=self.policy.total_concurrency-protected:
            raise CapacityDeferred('SHARED_CAPACITY_EXCEEDED',now+1)
        if count>=self.policy.running_per_account:
            raise CapacityDeferred('ACCOUNT_CAPACITY_EXCEEDED',now+1)

    def reserve_provider(self,db,workspace,provider,now,credential=None):
        window=int(now//60)
        limit=self.policy.provider_per_minute.get(provider)
        row=db.execute('SELECT minute_window,used FROM runtime_provider_windows WHERE workspace=? AND provider=?',(workspace,provider)).fetchone() if limit else None
        used=row[1] if row and row[0]==window else 0
        bucket=self.policy.shared_credential_buckets.get(provider+':'+credential) if credential else None
        bucket=bucket or provider
        shared_limit=self.policy.shared_provider_per_minute.get(bucket)
        opaque=hashlib.sha256(bucket.encode()).hexdigest()
        shared=db.execute('SELECT minute_window,used FROM runtime_shared_provider_windows WHERE bucket=?',(opaque,)).fetchone() if shared_limit else None
        shared_used=shared[1] if shared and shared[0]==window else 0
        if limit and used>=limit:raise CapacityDeferred('PROVIDER_RATE_LIMITED',(window+1)*60)
        if shared_limit and shared_used>=shared_limit:raise CapacityDeferred('SHARED_PROVIDER_RATE_LIMITED',(window+1)*60)
        # Check both allowances before mutating either reservation.
        if limit:db.execute('INSERT INTO runtime_provider_windows VALUES (?,?,?,?) ON CONFLICT(workspace,provider) DO UPDATE SET minute_window=excluded.minute_window,used=excluded.used',(workspace,provider,window,used+1))
        if shared_limit:db.execute('INSERT INTO runtime_shared_provider_windows VALUES (?,?,?) ON CONFLICT(bucket) DO UPDATE SET minute_window=excluded.minute_window,used=excluded.used',(opaque,window,shared_used+1))

    @staticmethod
    def tool_credential(runtime,tool_id):
        record=runtime.workflows.registry_adapter.service._tools.get(tool_id)
        return record.get('credential_reference') if record else None

    @staticmethod
    def tool_provider(runtime,tool_id):
        record=runtime.workflows.registry_adapter.service._tools.get(tool_id)
        return record['definition']['provider_id'] if record else tool_id

    def defer(self,runtime,db,run,error):
        attempts=run.get('capacity_deferrals',0)+1
        if attempts>self.policy.max_deferrals:
            raise RuntimeFailure('BACKPRESSURE_EXHAUSTED','The server capacity deferral limit was reached.')
        run['capacity_deferrals']=attempts
        run['available_at']=max(error.retry_at,runtime.clock()+min(2**min(attempts-1,6),60))
        run['lease_until']=0
        runtime.event(db,run,'run.backpressure',{'error_code':error.code,'retry_at':run['available_at'],'deferral':attempts})
        runtime.save(db,run)

    def diagnostics(self,workspace,now):
        with self.store.transaction(write=False) as db:
            queued=db.execute("SELECT COUNT(*) FROM runtime_runs WHERE workspace=? AND json_extract(document,'$.status')='queued'",(workspace,)).fetchone()[0]
            running=db.execute("SELECT COUNT(*) FROM runtime_runs WHERE workspace=? AND json_extract(document,'$.status')='running' AND CAST(json_extract(document,'$.lease_until') AS DOUBLE PRECISION)>?",(workspace,now)).fetchone()[0]
            rates=[dict(provider=p,window=w,used=u,limit=self.policy.provider_per_minute.get(p)) for p,w,u in db.execute('SELECT provider,minute_window,used FROM runtime_provider_windows WHERE workspace=?',(workspace,)).fetchall()]
        return dict(queued=queued,running=running,queue_limit=self.policy.queued_per_account,concurrency_limit=self.policy.running_per_account,provider_windows=rates)
