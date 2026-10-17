"""PostgreSQL implementation for the inventoried SQLite-shaped storage boundary.

Application values remain bound parameters. The compatibility compiler handles
only explicit known dialect constructs; it never retries external operations.
Writes use a database-scoped advisory transaction lock to preserve the existing
SQLite serialization invariant during migration. Reads remain concurrent.
"""
from contextlib import contextmanager
import logging
from pathlib import Path
import re
import sqlite3
import time


class DatabaseFailure(Exception):
    def __init__(self, category, sqlstate=None):
        super().__init__('The database transaction could not complete.')
        self.category, self.sqlstate = category, sqlstate
        self.retryable = category in {'contention','serialization','deadlock','unavailable'}


def classify(exc):
    state=getattr(exc,'sqlstate',None)
    category = 'deadlock' if state=='40P01' else 'serialization' if state=='40001' else 'contention' if state in {'55P03','57014'} else 'transaction_state' if state and state.startswith('25') else 'unavailable' if (state and state.startswith('08')) or (state is None and type(exc).__name__ in {'OperationalError','InterfaceError'}) else 'database_failure'
    return DatabaseFailure(category,state)


def placeholders(sql):
    """Convert qmark binds outside literals/identifiers; escape psycopg's % syntax."""
    result=[];quote=None;index=0
    while index<len(sql):
        character=sql[index]
        if quote:
            result.append('%%' if character=='%' else character)
            if character==quote:
                if index+1<len(sql) and sql[index+1]==quote:
                    result.append(sql[index+1]);index+=1
                else:quote=None
        elif character in {"'",'"'}:
            quote=character;result.append(character)
        elif character=='?':result.append('%s')
        elif character=='%':result.append('%%')
        else:result.append(character)
        index+=1
    if quote:raise ValueError('Unterminated SQL literal.')
    return ''.join(result)


class Cursor:
    def __init__(self,cursor,lastrowid=None):self.cursor,self.lastrowid=cursor,lastrowid
    def fetchone(self):return self.cursor.fetchone()
    def fetchall(self):return self.cursor.fetchall()
    def fetchmany(self,size=100):return self.cursor.fetchmany(size)
    def __iter__(self):return iter(self.cursor)
    @property
    def rowcount(self):return self.cursor.rowcount
    @property
    def description(self):return self.cursor.description


class Session:
    def __init__(self,connection,write):self.connection,self.write=connection,write;self.columns={}
    def execute(self,statement,parameters=()):
        sql=statement.strip().rstrip(';')
        if ';' in re.sub(r"'(?:''|[^'])*'",'',sql):raise ValueError('Use one database statement at a time.')
        if re.fullmatch(r'BEGIN\s+IMMEDIATE',sql,re.I):
            if not self.write:raise DatabaseFailure('transaction_state')
            # PostgreSQL already owns the write transaction/advisory reservation.
            return Cursor(self.connection.execute('SELECT true'))
        if re.match(r'^PRAGMA\s',sql,re.I):
            if re.fullmatch(r'PRAGMA\s+foreign_keys\s*=\s*ON',sql,re.I):
                return Cursor(self.connection.execute('SELECT true'))
            if re.fullmatch(r'PRAGMA\s+user_version',sql,re.I):
                return Cursor(self.connection.execute('SELECT COALESCE(MAX(version),0) FROM builder_store_versions'))
            if re.fullmatch(r'PRAGMA\s+user_version\s*=\s*1',sql,re.I):
                return Cursor(self.connection.execute('INSERT INTO builder_store_versions(version) VALUES (1) ON CONFLICT DO NOTHING'))
            raise ValueError('This SQLite pragma has no supported PostgreSQL equivalent.')
        if 'sqlite_master' in sql:
            sql=re.sub(r"FROM\s+sqlite_master\s+WHERE\s+type\s*=\s*'table'\s+AND\s+name\s*=", "FROM information_schema.tables WHERE table_schema=current_schema() AND table_name=",sql,flags=re.I)
            if 'sqlite_master' in sql:raise ValueError('Unsupported SQLite catalog query.')
        if re.match(r'CREATE\s+TABLE',sql,re.I):
            sql=re.sub(r'\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b','BIGSERIAL PRIMARY KEY',sql,flags=re.I)
            sql=re.sub(r'\bINTEGER\s+PRIMARY\s+KEY\b','BIGSERIAL PRIMARY KEY',sql,flags=re.I)
            sql=re.sub(r'\bINTEGER\b','BIGINT',sql,flags=re.I)
            # A logical insertion-order column replaces implicit SQLite rowid.
            sql=sql[:-1]+', rowid BIGSERIAL UNIQUE)' if sql.endswith(')') else sql
        sql=re.sub(r'\bREAL\b','DOUBLE PRECISION',sql,flags=re.I)
        if re.match(r'INSERT\s+OR\s+IGNORE',sql,re.I):
            sql=re.sub(r'^INSERT\s+OR\s+IGNORE','INSERT',sql,flags=re.I)+' ON CONFLICT DO NOTHING'
        elif re.match(r'INSERT\s+OR\s+REPLACE',sql,re.I):
            sql=re.sub(r'^INSERT\s+OR\s+REPLACE','INSERT',sql,flags=re.I)
            match=re.match(r'INSERT\s+INTO\s+([a-z_][a-z0-9_]*)\s',sql,re.I)
            if not match:raise ValueError('Use a known replacement table.')
            table=match[1]
            if table not in {'revisions','customer_mail_cursor','procurement_policy_proofs'}:raise ValueError('Replacement semantics are not inventoried for this table.')
            rows=self.connection.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s AND column_name<>'rowid' ORDER BY ordinal_position",(table,)).fetchall()
            keys=self.connection.execute("SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey) WHERE i.indrelid=to_regclass(%s) AND i.indisprimary ORDER BY a.attnum",(table,)).fetchall()
            columns=[r[0] for r in rows];primary=[r[0] for r in keys]
            if not columns or not primary:raise ValueError('Replacement requires an inventoried primary key.')
            update=', '.join(f'{c}=excluded.{c}' for c in columns if c not in primary)
            sql+=' ON CONFLICT ('+', '.join(primary)+') DO UPDATE SET '+update
        sql=sql.replace('MAX(resources.spreadsheet_owned,excluded.spreadsheet_owned)','builder_scalar_max(resources.spreadsheet_owned,excluded.spreadsheet_owned)').replace('MAX(resources.tab_owned,excluded.tab_owned)','builder_scalar_max(resources.tab_owned,excluded.tab_owned)')
        returning=bool(re.match(r'INSERT\s+INTO\s+(runtime_events|lifecycle_overview_events)\s*\(',sql,re.I)) and 'RETURNING' not in sql.upper()
        if returning:sql+=' RETURNING sequence'
        try:
            # SQLite rolls back a failed constraint statement, not the entire
            # transaction. A savepoint preserves that documented boundary.
            if re.match(r'(INSERT|UPDATE|DELETE)\b',sql,re.I):
                with self.connection.transaction():
                    cursor=self.connection.execute(placeholders(sql),tuple(parameters))
                    inserted=cursor.fetchone()[0] if returning else None
            else:
                cursor=self.connection.execute(placeholders(sql),tuple(parameters));inserted=None
        except Exception as exc:
            if str(getattr(exc,'sqlstate','')).startswith('23'):
                failure=sqlite3.IntegrityError('A database integrity constraint rejected the change.')
                failure.sqlite_errorcode=sqlite3.SQLITE_CONSTRAINT
                raise failure from None
            raise
        return Cursor(cursor,inserted)

    def executemany(self,statement,rows):
        for row in rows:self.execute(statement,row)

    def lock(self,namespace,identity):
        if self.write:self.connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(namespace+':'+str(identity),))




class PostgresDatabase:
    def __init__(self,dsn,busy_timeout_ms):
        try:import psycopg
        except ImportError:raise ValueError('Install requirements-postgres.txt before selecting PostgreSQL.') from None
        self.psycopg,self.dsn,self.busy_timeout_ms=psycopg,dsn,busy_timeout_ms
        with self.transaction() as db:
            db.connection.execute('CREATE TABLE IF NOT EXISTS builder_schema_migrations (version INTEGER PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())')
            db.connection.execute('CREATE TABLE IF NOT EXISTS builder_store_versions (version INTEGER PRIMARY KEY)')
            version=db.connection.execute('SELECT COALESCE(MAX(version),0) FROM builder_schema_migrations').fetchone()[0]
            if version>1:raise ValueError('The database schema is newer than this application.')
            if version<1:
                migration=Path(__file__).resolve().parents[1]/'migrations/postgres/001_compatibility.sql'
                db.connection.execute(migration.read_text(),prepare=False)
                db.connection.execute('INSERT INTO builder_schema_migrations(version) VALUES (1)')

    @contextmanager
    def transaction(self,write=True):
        connection=None
        try:
            connection=self.psycopg.connect(self.dsn,connect_timeout=5)
            with connection.transaction():
                connection.execute('SET TRANSACTION READ WRITE' if write else 'SET TRANSACTION READ ONLY')
                connection.execute("SELECT set_config('lock_timeout',%s,true)",(str(max(1,self.busy_timeout_ms))+'ms',))
                if write:
                    connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(current_database()||':'||current_schema(),0))")
                yield Session(connection,write)
        except self.psycopg.Error as exc:
            failure=classify(exc)
            logging.getLogger(__name__).warning('PostgreSQL transaction failed',extra={'database_category':failure.category,'database_code':failure.sqlstate,'transaction_write':write})
            raise failure from None
        finally:
            if connection:connection.close()

    def run_transaction(self,callback,*,retry_safe=False,max_attempts=3):
        """Only explicit pure-database callbacks may be retried; never provider calls."""
        for attempt in range(max_attempts):
            try:
                with self.transaction() as db:return callback(db)
            except DatabaseFailure as exc:
                if not retry_safe or exc.category not in {'serialization','deadlock','contention'} or attempt+1>=max_attempts:raise
                time.sleep(min(.05*2**attempt,.5))
