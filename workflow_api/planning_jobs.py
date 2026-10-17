"""Durable, workspace/subject-scoped planning with no external-action execution.

Queued jobs survive restart. Expired running jobs fail explicitly rather than replaying
an uncertain model request. Cancellation discards results; it cannot undo model usage.
"""
from copy import deepcopy
import hashlib
import json
import re
from threading import Event, Lock, Thread
import time
from uuid import uuid4

from jsonschema import Draft202012Validator
from registry.contracts import schema
from registry.safety import reject_secrets
from .service import ApiFailure


class PlanningJobs:
    def __init__(self, service, authenticate, deadline=780):
        self.service, self.store, self.authenticate = service, service.store, authenticate
        self.deadline = deadline
        self.stop_event, self.wake = Event(), Event()
        self.thread, self.guard = None, Lock()
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS builder_planning_jobs (job_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, subject TEXT NOT NULL, retry_key TEXT NOT NULL, fingerprint TEXT NOT NULL, state TEXT NOT NULL, request TEXT, result TEXT, lease_until REAL, claim TEXT, created REAL NOT NULL, UNIQUE(workspace, subject, retry_key))')
            db.execute('CREATE INDEX IF NOT EXISTS builder_planning_queue ON builder_planning_jobs(state, created)')

    def submit(self, request, auth):
        self.service.authorize(auth, 'plan_workflow')
        reject_secrets(request)
        if (not isinstance(request, dict) or request.get('operation') != 'plan_workflow' or
                not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', str(request.get('request_id', ''))) or
                not isinstance(request.get('idempotency_key'), str) or not 8 <= len(request['idempotency_key']) <= 128):
            raise ApiFailure('INVALID_REQUEST', 'Use a canonical planning request and idempotency key.', 400)
        Draft202012Validator(schema('api')['properties']['request_envelope']).validate(request)
        payload = request['payload']
        if (not isinstance(payload.get('objective'), str) or not payload['objective'].strip() or
                set(payload) - {'objective', 'context'}):
            raise ApiFailure('INVALID_REQUEST', 'Provide a process description and optional planning context.', 400)
        workspace, subject = (auth['subject'][key] for key in ('workspace_id', 'subject_id'))
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with self.store.transaction() as db:
            retry_key = request['idempotency_key']
            while True:
                old = db.execute('SELECT job_id, fingerprint, state, result FROM builder_planning_jobs WHERE workspace=? AND subject=? AND retry_key=?',
                                 (workspace, subject, retry_key)).fetchone()
                if not old:
                    break
                if old[1] != fingerprint:
                    raise ApiFailure('IDEMPOTENCY_KEY_REUSED', 'This planning key belongs to a different request.', 409)
                if old[2] != 'succeeded':
                    break
                result = json.loads(old[3])
                workflow_id = (result.get('data') or {}).get('workflow', {}).get('workflow_id')
                deleted = db.execute('SELECT deleted_at FROM lifecycle_tombstones WHERE workspace=? AND workflow_id=?',
                                     (workspace, workflow_id)).fetchone()
                if not deleted:
                    break
                # Deletion ends this result's reuse. Preserve its job as history,
                # and make retries of the new generation converge on one job.
                retry_key = 'recreate_' + hashlib.sha256(f'{old[0]}:{deleted[0]}'.encode()).hexdigest()
            if old:
                job_id = old[0]
            else:
                job_id = 'plan_' + uuid4().hex
                queued_request = deepcopy(request)
                queued_request['idempotency_key'] = retry_key
                db.execute('INSERT INTO builder_planning_jobs VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?)',
                           (job_id, workspace, subject, retry_key, fingerprint, 'queued', json.dumps(queued_request), time.time()))
        self.wake.set()
        return self.get(job_id, auth)

    def get(self, job_id, auth):
        self.service.authorize(auth, 'plan_workflow')
        workspace, subject = (auth['subject'][key] for key in ('workspace_id', 'subject_id'))
        with self.store.transaction(write=False) as db:
            row = db.execute('SELECT state, result FROM builder_planning_jobs WHERE job_id=? AND workspace=? AND subject=?',
                             (job_id, workspace, subject)).fetchone()
        if not row:
            raise ApiFailure('PLANNING_JOB_NOT_FOUND', 'The planning job was not found for your account.', 404)
        return {'job_id': job_id, 'state': row[0], 'result': json.loads(row[1]) if row[1] else None}

    def cancel(self, job_id, auth):
        self.get(job_id, auth)
        with self.store.transaction() as db:
            db.execute("UPDATE builder_planning_jobs SET state='cancelled', request=NULL, result=NULL, lease_until=NULL, claim=NULL WHERE job_id=? AND workspace=? AND subject=? AND state IN ('queued','running')",
                       (job_id, auth['subject']['workspace_id'], auth['subject']['subject_id']))
        return self.get(job_id, auth)

    def tick(self):
        now, claim = time.time(), uuid4().hex
        with self.store.transaction() as db:
            interrupted = self.service.failure('req_planning_interrupted', ApiFailure('PLANNING_INTERRUPTED', 'Planning was interrupted. Start a new generation request.', 503))
            db.execute("UPDATE builder_planning_jobs SET state='failed', result=?, request=NULL, claim=NULL, lease_until=NULL WHERE state='running' AND lease_until < ?", (json.dumps(interrupted), now))
            row = db.execute("SELECT job_id, workspace, subject, request FROM builder_planning_jobs WHERE state='queued' ORDER BY created LIMIT 1").fetchone()
            if not row:
                return False
            db.execute("UPDATE builder_planning_jobs SET state='running', claim=?, lease_until=? WHERE job_id=? AND state='queued'", (claim, now + self.deadline, row[0]))
        try:
            auth = self.authenticate(row[1], row[2])
            if auth is None:
                raise ApiFailure('OPERATION_NOT_AUTHORIZED', 'Planning authority is no longer available.', 403)
            result = self.service.handle(json.loads(row[3]), deepcopy(auth))
        except ApiFailure as exc:
            result = self.service.failure('req_planning', exc)
        except Exception:
            result = self.service.failure('req_planning', ApiFailure('PLANNING_FAILED', 'Planning failed. Check the service and start a new generation request.', 503))
        with self.store.transaction() as db:
            db.execute("UPDATE builder_planning_jobs SET state=?, result=?, request=NULL, lease_until=NULL, claim=NULL WHERE job_id=? AND state='running' AND claim=?",
                       ('succeeded' if result['status'] < 400 else 'failed', json.dumps(result), row[0], claim))
        return True

    def start(self):
        with self.guard:
            if self.thread and self.thread.is_alive():
                return
            self.stop_event.clear()
            self.thread = Thread(target=self.loop, name='builder-planning', daemon=True)
            self.thread.start()

    def loop(self):
        while not self.stop_event.is_set():
            try:
                worked = self.tick()
            except Exception:
                import logging
                logging.getLogger(__name__).warning('Planning queue unavailable; durable jobs retained.')
                worked = False
            if not worked:
                self.wake.wait(1)
                self.wake.clear()

    def stop(self):
        self.stop_event.set()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=1)
