"""Snapshot, inventory and optionally migrate one Builder SQLite database.

Default is a read-only preparation report. --apply requires an isolated empty
PostgreSQL schema selected through a server environment variable. No provider
calls, automatic persistence cutover or application retries are performed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
IDENTIFIER=re.compile(r'^[a-z_][a-z0-9_]*$')
ADMIN_TABLES={'builder_schema_migrations','builder_store_versions'}


def identifier(name):
    if not IDENTIFIER.fullmatch(name):raise ValueError('Unsupported database identifier; review the inventory before migration.')
    return '"'+name+'"'


def row_bytes(row):
    return (json.dumps(list(row),ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()


def checksum(cursor):
    digest=hashlib.sha256();count=0
    while True:
        rows=cursor.fetchmany(500)
        if not rows:break
        for row in rows:digest.update(row_bytes(row));count+=1
    return count,digest.hexdigest()


def snapshot(source,destination):
    source=Path(source).resolve();destination=Path(destination).absolute()
    if not source.is_file() or destination.exists() or destination.is_symlink():raise ValueError('Use an existing source and a new private snapshot path.')
    destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    descriptor=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(descriptor)
    with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=3) as original:
        with sqlite3.connect(destination) as backup:original.backup(backup)
    return destination


def inventory(connection):
    if connection.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite integrity check failed; migration stopped.')
    if connection.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('SQLite foreign-key validation failed; repair before migration.')
    tables=[]
    for name,ddl in connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid").fetchall():
        identifier(name)
        if name in ADMIN_TABLES:continue
        if 'WITHOUT ROWID' in ddl.upper():raise ValueError('WITHOUT ROWID storage needs explicit migration review.')
        columns=[row[1] for row in connection.execute('PRAGMA table_info('+identifier(name)+')').fetchall()]
        for column in columns:identifier(column)
        count,digest=checksum(connection.execute('SELECT rowid,'+','.join(identifier(c) for c in columns)+' FROM '+identifier(name)+' ORDER BY rowid'))
        tables.append({'name':name,'ddl':ddl,'columns':columns,'rows':count,'sha256':digest})
    return tables


def migrate(source,*,target_dsn=None,apply=False):
    from workflow_api.postgres import PostgresDatabase
    source=Path(source).resolve()
    with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=3) as legacy:
        tables=inventory(legacy)
        result={'format':'builder-database-migration-v1','source':str(source),'applied':False,'validated':False,'tables':[{k:v for k,v in t.items() if k!='ddl'} for t in tables]}
        if not apply:return result
        if not target_dsn:raise ValueError('Select a private target DSN through the configured environment variable.')
        database=PostgresDatabase(target_dsn,3000)
        with database.transaction() as target:
            existing=target.connection.execute("SELECT table_name FROM information_schema.tables WHERE table_schema=current_schema() AND table_type='BASE TABLE'").fetchall()
            if {row[0] for row in existing}-ADMIN_TABLES:raise ValueError('Target schema must be empty; existing persistence is never overwritten.')
            for table in tables:target.execute(table['ddl'])
            for table in tables:
                columns=table['columns'];names=['rowid',*columns]
                query='SELECT rowid,'+','.join(identifier(c) for c in columns)+' FROM '+identifier(table['name'])+' ORDER BY rowid'
                source_rows=legacy.execute(query)
                insert='INSERT INTO '+identifier(table['name'])+' ('+','.join(identifier(c) for c in names)+') VALUES ('+','.join(['%s']*len(names))+')'
                while True:
                    rows=source_rows.fetchmany(500)
                    if not rows:break
                    with target.connection.cursor() as writer:writer.executemany(insert,rows)
            # Indexes are validated after row import, before commit/cutover.
            for name,ddl in legacy.execute("SELECT name,sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY rowid").fetchall():
                identifier(name);target.execute(ddl)
            sequences=dict(legacy.execute('SELECT name,seq FROM sqlite_sequence').fetchall()) if legacy.execute("SELECT 1 FROM sqlite_master WHERE name='sqlite_sequence'").fetchone() else {}
            for table in tables:
                for column in ['rowid',*table['columns']]:
                    sequence=target.connection.execute('SELECT pg_get_serial_sequence(%s,%s)',(table['name'],column)).fetchone()[0]
                    if sequence:
                        maximum=target.connection.execute('SELECT MAX('+identifier(column)+') FROM '+identifier(table['name'])).fetchone()[0]
                        if column!='rowid':maximum=max(maximum or 0,sequences.get(table['name'],0))
                        target.connection.execute('SELECT setval(%s,%s,%s)',(sequence,max(maximum or 1,1),bool(maximum)))
                query='SELECT rowid,'+','.join(identifier(c) for c in table['columns'])+' FROM '+identifier(table['name'])+' ORDER BY rowid'
                with target.connection.cursor(name='verify_'+uuid4().hex) as verifier:
                    verifier.execute(query);count,digest=checksum(verifier)
                if count!=table['rows'] or digest!=table['sha256']:raise ValueError('Migration validation failed; target transaction rolled back.')
            user_version=legacy.execute('PRAGMA user_version').fetchone()[0]
            if user_version:
                target.connection.execute('INSERT INTO builder_store_versions(version) VALUES (%s) ON CONFLICT DO NOTHING',(user_version,))
            result['applied'],result['validated']=True,True
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--target-dsn-env',default='BUILDER_MIGRATION_TARGET_URL')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    backup=snapshot(args.source,args.snapshot)
    result=migrate(backup,target_dsn=os.getenv(args.target_dsn_env),apply=args.apply)
    args.report.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    descriptor=os.open(args.report,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w') as report:json.dump(result,report,indent=2);report.write('\n')
    print('Migration report written. Applied:',result['applied'],'Validated:',result['validated'])


if __name__=='__main__':main()
