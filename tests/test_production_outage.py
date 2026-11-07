"""Explicitly opt-in downtime of the agent-created disposable PostgreSQL cluster."""
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlsplit,parse_qs

import pytest
from tests.test_distributed_postgres import pg
from tests.test_distributed_execution import approved
from workflow_api.postgres import DatabaseFailure


def test_database_outage_after_effect_does_not_allow_replay(pg,monkeypatch):
    root_setting=os.getenv('BUILDER_DISPOSABLE_PG_ROOT')
    if not root_setting:pytest.skip('Requires the explicitly owned disposable test cluster.')
    root=Path(root_setting).resolve();assert root.parent==Path('/tmp') and root.name.startswith('builder-phase2-pg-')
    q=parse_qs(urlsplit(pg.postgres_dsn).query)
    socket=Path(q['host'][0]).resolve();assert socket.is_relative_to(root)
    assert q['port']==['55437']
    monkeypatch.setenv('BUILDER_RUNTIME_LEASE_SECONDS','30')
    rid=approved(pg);original=pg.connector.invoke;stopped=False
    def control(*args):
        result=subprocess.run(['/usr/lib/postgresql/16/bin/pg_ctl','-D',str(root/'data'),*args],capture_output=True,text=True,timeout=30)
        assert result.returncode==0,'Disposable PostgreSQL control failed; inspect its private log.'
    def start():
        control('-l',str(root/'phase3-server.log'),'-o',"-c listen_addresses='' -c unix_socket_directories="+str(socket)+' -p 55437','-w','start')
    def effect(*args):
        nonlocal stopped
        result=original(*args)
        control('-m','fast','-w','stop');stopped=True
        return result
    pg.connector.invoke=effect
    began=time.monotonic()
    try:
        try:pg.graph.advance(rid,pg.auth)
        except DatabaseFailure as failure:assert failure.retryable
        assert stopped and len(pg.invocations)==1
    finally:
        if stopped:start()
    pg.now+=31;pg.connector.invoke=original
    result=pg.graph.advance(rid,pg.auth)
    assert result['status']=='blocked'
    with pg.store.transaction(write=False) as db:
        assert pg.runtime.load(db,rid,pg.auth)['error_code']=='UNKNOWN_INVOCATION_RESULT'
    assert len(pg.invocations)==1
    assert time.monotonic()-began<30
