"""Run existing API/lifecycle/runtime acceptance against real, isolated PostgreSQL schemas."""
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4
from unittest.mock import patch

import pytest
from tests import test_lifecycle as lifecycle_fixtures
from tests import test_runtime as runtime_fixtures
from tests import test_workflow_api as api_fixtures
from workflow_api.storage import WorkflowStore


def test_dsn():
    value=os.getenv('BUILDER_TEST_POSTGRES_DSN')
    path=Path(__file__).resolve().parents[1]/'.local/phase2-stage/postgres-check.json'
    if not value and path.exists():value=json.loads(path.read_text())['dsn']
    if not value:pytest.skip('Real PostgreSQL not configured; set BUILDER_TEST_POSTGRES_DSN.')
    return value

test_dsn.__test__=False


class PostgresFixture:
    def setUp(self):
        psycopg=pytest.importorskip('psycopg')
        from psycopg import sql
        base=test_dsn();schema='check_'+uuid4().hex
        with psycopg.connect(base,autocommit=True) as connection:
            connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        def cleanup():
            with psycopg.connect(base,autocommit=True) as connection:
                connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
        self.addCleanup(cleanup)
        self.postgres_dsn=base+('&' if '?' in base else '?')+urlencode({'options':'-csearch_path='+schema})
        factory=lambda _path,*args,**kwargs:WorkflowStore(self.postgres_dsn,**kwargs)
        for module in [lifecycle_fixtures,runtime_fixtures,api_fixtures]:
            replacement=patch.object(module,'WorkflowStore',side_effect=factory);replacement.start();self.addCleanup(replacement.stop)
        replacement=patch('workflow_api.main.WorkflowStore',side_effect=factory);replacement.start();self.addCleanup(replacement.stop)
        super().setUp()


class LifecyclePostgresTests(PostgresFixture,lifecycle_fixtures.LifecycleTests):pass
class WorkflowApiPostgresTests(PostgresFixture,api_fixtures.WorkflowApiTests):pass
class RuntimePostgresTests(PostgresFixture,runtime_fixtures.RuntimeTests):pass
class GraphPostgresTests(PostgresFixture,runtime_fixtures.GraphTests):pass
class ObservabilityPostgresTests(PostgresFixture,runtime_fixtures.ObservabilityTests):pass


from connector_extension.tests import test_procurement_store as procurement_fixtures
from connector_extension.tests import test_sheet_creation as creation_fixtures


class AuxiliaryPostgresFixture:
    def setUp(self):
        psycopg=pytest.importorskip('psycopg');from psycopg import sql
        base=test_dsn()
        with psycopg.connect(base) as db:
            before={row[0] for row in db.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'builder_aux_%'").fetchall()}
        def cleanup():
            with psycopg.connect(base,autocommit=True) as db:
                schemas={row[0] for row in db.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'builder_aux_%'").fetchall()}
                for name in schemas-before:db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(name)))
        self.addCleanup(cleanup)
        settings=patch.dict(os.environ,{'BUILDER_AUXILIARY_DATABASE_URL':base});settings.start();self.addCleanup(settings.stop)
        super().setUp()


class ProcurementStorePostgresTests(AuxiliaryPostgresFixture,procurement_fixtures.StoreTests):
    def test_database_has_foreign_keys_and_private_permissions(self):
        import sqlite3
        with self.store.connection() as db:
            count=db.connection.execute("SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema=current_schema() AND constraint_type='FOREIGN KEY'").fetchone()[0]
            self.assertGreater(count,0)
            privileges=db.connection.execute('SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user').fetchone()
            self.assertEqual(privileges,(False,False,False))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT INTO projects VALUES (?,?,?,?)',('foreign_workspace','foreign_project','missing_record','{}'))


class SheetCreationPostgresTests(AuxiliaryPostgresFixture,creation_fixtures.CreationTests):pass


from connector_extension.tests import test_tracking_recovery as recovery_fixtures

class TrackingRecoveryPostgresTests(AuxiliaryPostgresFixture,recovery_fixtures.TrackingRecoveryTests):pass
class EffectDiagnosticsPostgresTests(AuxiliaryPostgresFixture,recovery_fixtures.DiagnosticsTests):pass
