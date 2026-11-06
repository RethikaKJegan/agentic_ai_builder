"""Server-owned dedicated-client boundary shared by HTTP and worker startup."""
from dataclasses import dataclass
import hashlib
import hmac
from pathlib import Path
import re
import time

CLIENT = 'simpsons'
WORKSPACE = 'client-simpsons'
OWNER = 'simpsons-client'
HEADER = 'x-builder-client-assertion'


@dataclass(frozen=True)
class ClientIsolation:
    secret: str
    database: Path
    client: str = CLIENT
    data_enabled: bool = False

    @classmethod
    def configured(cls, env, database=None):
        client = env.get('BUILDER_CLIENT_ID')
        if not client:
            return None
        if client not in {'simpsons', 'subway'}:
            raise ValueError('Unsupported dedicated client.')
        workspace, owner = f'client-{client}', f'{client}-client'
        secret = env.get(f'BUILDER_{client.upper()}_PROXY_SECRET', '')
        if len(secret) < 32:
            raise ValueError('Configure a separate Simpsons proxy secret of at least 32 characters.')
        raw = database or env.get('BUILDER_DATABASE_URL')
        if not raw or '://' in str(raw):
            raise ValueError('Configure a provisioned dedicated Simpsons SQLite database path.')
        path = Path(raw).resolve()
        # A marked, separately provisioned store is mandatory, including in worker processes.
        import sqlite3
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
            try:
                rows = db.execute('SELECT client_id,workspace,owner FROM client_isolation').fetchall()
            except sqlite3.Error:
                raise ValueError('Provision the Simpsons store before starting this process.') from None
            if rows != [(client, workspace, owner)]:
                raise ValueError('The application store is not provisioned for Simpsons.')
            try:
                allowed = {r[0] for r in db.execute('SELECT connection_id FROM client_source_bindings')}
                actual = {r[0] for r in db.execute('SELECT connection_id FROM data_source_connections')}
            except sqlite3.Error:
                raise ValueError('Provision the explicit Simpsons source allowlist.') from None
            data_enabled = client == 'subway' and env.get('BUILDER_SUBWAY_DATA_ENABLED') == '1'
            if len(allowed) != (2 if client == 'simpsons' or data_enabled else 0) or not actual <= allowed:
                raise ValueError('The client store contains an unprovisioned source.')
            # Reject any mixed workspace/owner state, even if someone adds a marker to a shared store.
            for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
                quoted = '"' + table.replace('"', '""') + '"'
                columns = {r[1] for r in db.execute(f'PRAGMA table_info({quoted})')}
                # This table belongs to process coordination, not tenant subjects.
                # Validate its exact shape and server-issued owner format before exemption.
                if table == 'builder_worker_leases' and columns == {'name','owner','expires'}:
                    leases=db.execute('SELECT name,owner,expires FROM builder_worker_leases').fetchall()
                    if any(name!='builder-live-workers' or not isinstance(holder,str) or
                           not re.fullmatch(r'worker_[a-f0-9]{32}',holder) or
                           not isinstance(expires,(int,float)) for name,holder,expires in leases):
                        raise ValueError('The dedicated client contains an invalid worker lease.')
                    continue
                for column, expected in [('workspace', workspace), ('owner', owner)]:
                    # Existing releases create server-owned automation subjects in
                    # this same workspace. Fresh worker resolution still validates
                    # their active identity and original publisher before execution.
                    automation = ' AND "owner" NOT LIKE \'automation:%\'' if column == 'owner' else ''
                    if column in columns and db.execute(
                            f'SELECT 1 FROM {quoted} WHERE "{column}" IS NOT NULL AND "{column}" != ?{automation} LIMIT 1',
                            (expected,)).fetchone():
                        raise ValueError('A dedicated client store cannot contain another company scope.')
        return cls(secret, path, client, data_enabled)

    @property
    def subject(self):
        return dict(workspace_id=f'client-{self.client}', subject_id=f'{self.client}-client')

    def accepts(self, token, now=None):
        if not isinstance(token, str) or not re.fullmatch(re.escape(self.client) + r'\.\d{10}\.[a-f0-9]{48}\.[a-f0-9]{64}', token):
            return False
        payload, mac = token.rsplit('.', 1)
        remaining = int(token.split('.')[1]) - int(time.time() if now is None else now)
        return 0 < remaining <= 60 and hmac.compare_digest(
            mac, hmac.new(self.secret.encode(), payload.encode(), hashlib.sha256).hexdigest())
