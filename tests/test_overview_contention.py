"""Overview reads must not compete with workflow saves for the writer lock."""
import json
import sqlite3
import unittest
from unittest.mock import patch
from tests import test_lifecycle as fixture

class OverviewContentionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.LifecycleTests();self.fixture.setUp();self.addCleanup(self.fixture.tearDown)
        self.service=self.fixture.service;self.auth=self.fixture.auth
        self.auth['permissions'].append('workflow.edit')
        with self.service.store.transaction() as db:
            self.service.store.put(db,self.auth['subject']['workspace_id'],self.fixture.workflow)
    def test_overview_reads_while_another_connection_holds_writer_lock(self):
        with sqlite3.connect(self.fixture.path) as writer:
            writer.execute('BEGIN IMMEDIATE')
            result=self.service.lifecycle.overview(self.auth)
            self.assertEqual(len(result['items']),1)
            self.assertEqual(self.service.lifecycle.overview(self.auth,0)['items'],[])
            writer.rollback()
    def test_summary_counts_all_runs_preserves_latest_and_workspace(self):
        workspace=self.auth['subject']['workspace_id'];identity=self.fixture.workflow['workflow_id']
        with self.service.store.transaction() as db:
            for identifier,status,approvals,owner in (
                ('old','completed',[{'status':'approved'}],workspace),
                ('active','running',[],workspace),
                ('latest','paused_for_approval',[{'status':'pending'},{'status':'pending'}],workspace),
                ('foreign','running',[{'status':'pending'}],'other-workspace')):
                doc={'status':status,'approvals':approvals,'outputs':{'large':'x'*100000}}
                db.execute('INSERT INTO runtime_runs(workspace,run_id,workflow_id,document) VALUES (?,?,?,?)',
                    (owner,identifier,identity,json.dumps(doc)))
        row=self.service.lifecycle.overview(self.auth)['items'][0]
        self.assertEqual((row['latest_run_id'],row['latest_run_status']),('latest','paused_for_approval'))
        self.assertEqual(row['active_run_count'],2);self.assertEqual(row['pending_approval_count'],2)
    def test_database_busy_is_retryable_for_save_and_overview(self):
        error=sqlite3.OperationalError('database is locked');error.sqlite_errorcode=sqlite3.SQLITE_BUSY
        request={'request_id':'req_busy','operation':'save_workflow_version','idempotency_key':'busy_test_key',
                 'payload':{'workflow_id':self.fixture.workflow['workflow_id'],'workflow_version':1,'base_version':0,'workflow':self.fixture.workflow}}
        with patch.object(self.service.store,'transaction',side_effect=error):
            result=self.service.handle(request,self.auth)
        self.assertEqual(result['status'],503)
        self.assertEqual(result['data']['error']['error_code'],'API_DATABASE_BUSY')
        self.assertTrue(result['data']['error']['retryable'])
        with patch.object(self.service.store,'transaction',side_effect=error):
            result=self.service.handle_lifecycle('list_workflow_overview',{'request_id':'req_busy'},self.auth)
        self.assertEqual(result['status'],503)
        self.assertEqual(result['data']['error']['error_code'],'API_DATABASE_BUSY')

