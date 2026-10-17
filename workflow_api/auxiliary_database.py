"""Opt-in PostgreSQL persistence for independent connector journals/case stores."""
from contextlib import contextmanager
from functools import lru_cache
import hashlib
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qsl,urlencode,urlsplit,urlunsplit


@lru_cache(maxsize=32)
def _postgres(dsn):
    from .postgres import PostgresDatabase
    return PostgresDatabase(dsn,int(os.getenv('BUILDER_DATABASE_BUSY_TIMEOUT_MS','3000')))


def scoped_dsn(base,path):
    """Stable shared namespace; separate legacy database files cannot collide."""
    from scripts.integration_config import ROOT
    path=Path(path).resolve()
    try:identity=str(path.relative_to(ROOT))
    except ValueError:identity=str(path)
    schema='builder_aux_'+re.sub('[^a-z0-9_]','_',path.stem.lower())[:20]+'_'+hashlib.sha256(identity.encode()).hexdigest()[:12]
    import psycopg
    from psycopg import sql
    with psycopg.connect(base,autocommit=True,connect_timeout=5) as connection:
        connection.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(schema)))
    parsed=urlsplit(base);parameters=dict(parse_qsl(parsed.query));parameters['options']='-csearch_path='+schema
    return urlunsplit((parsed.scheme,parsed.netloc,parsed.path,urlencode(parameters),parsed.fragment))


@lru_cache(maxsize=32)
def _scoped(base,path):return scoped_dsn(base,path)


@contextmanager
def connection(path,*,write=True,database_url=None,timeout=3):
    base=database_url or os.getenv('BUILDER_AUXILIARY_DATABASE_URL')
    if base:
        database=_postgres(_scoped(base,str(Path(path).resolve())))
        with database.transaction(write=write) as db:yield db
    else:
        db=sqlite3.connect(path,timeout=timeout)
        db.execute('PRAGMA foreign_keys=ON')
        if not write:db.execute('PRAGMA query_only=ON')
        try:
            with db:yield db
        finally:db.close()
