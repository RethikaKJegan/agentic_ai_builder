"""Bounded reconciliation of RFQ tracking after a confirmed send."""
from copy import deepcopy
import json

class RFQProjectionRecovery:
    def recover_rfq_projection(self, workspace, job, auth):
        if job['phase'] != 'STOPPED' or not self.automatic(job) or not self.active(workspace, job):
            return False
        recovered = job.get('rfq_projection_recovery', {})
        failed = [(k,a) for k,a in job['actions'].items() if a.get('state') in ('failed','blocked','rejected','cancelled') and k not in recovered]
        if len(failed) != 1 or job.get('issues') != ['runtime:failed']:
            return False
        key, action = failed[0]
        if not key.startswith('sync_sent_rfq_') or '_reconcile' in key or action.get('state') != 'failed':
            return False
        project = job['plan']['project_id']
        intents = [i for i in self.store.pending_sync(workspace, project) if 'sync_'+i['key'] == key]
        if len(intents) != 1: return False
        intent = intents[0]; identifier = intent['record_id']
        send = job['actions'].get('send_'+identifier, {})
        rfq = self.store.get(workspace, project, identifier)
        if send.get('state') != 'completed' or not rfq or rfq['data']['status'] not in ('SENT','OPEN'):
            return False
        fields = intent['payload']['inputs']['fields']
        if (fields.get('gmail_message_id') != rfq['data']['gmail_message_id'] or
                fields.get('gmail_thread_ids') != ','.join(rfq['data']['gmail_thread_ids'])): return False
        events = self.workflows.runtime_runner.runtime.events(action['run_id'], auth)['items']
        codes = {e['details'].get('error_code') for e in events if e['event_type']=='node.failed'}
        if not codes or not codes <= {'SHEETS_RECORD_FAILED','SHEETS_RATE_LIMITED','SHEETS_PROVIDER_UNAVAILABLE','SHEETS_TIMEOUT','SHEETS_RECORD_UNCONFIRMED'}:
            return False
        with self.workflows.store.transaction(write=False) as db:
            row = db.execute('SELECT document FROM revisions WHERE workspace=? AND workflow_id=? AND version=?',
                (workspace,action['workflow_id'],action['workflow_version'])).fetchone()
        if not row: return False
        workflow = json.loads(row[0])
        nodes = [n for n in workflow['nodes'] if n['kind']=='tool']
        if (len(nodes)!=1 or nodes[0].get('tool_id')!='google_sheets_upsert_record' or
                nodes[0].get('configuration',{}).get('input') != intent['payload']['inputs']): return False
        params = intent['payload']['inputs']
        read = self.phase2_action(workspace,job,'projection_read_'+identifier,'google_sheets_read_rows',
            {'spreadsheet_id':params['spreadsheet_id'],'range':params['range']},auth)
        if read is None: return False
        rows = read['action'].get('rows', [])
        # Extension reads expose the actual raw header/data rows.
        if not rows or not isinstance(rows[0],list): return False
        headers = rows[0]
        if len(headers)!=len(set(headers)) or any(k not in headers for k in [params['identity_column'],*fields]): return False
        matches = [r for r in rows[1:] if len(r)>headers.index(params['identity_column']) and str(r[headers.index(params['identity_column'])])==identifier]
        if len(matches)!=1: return False
        actual = dict(zip(headers,matches[0]))
        try: prior_revision = int(actual.get('revision', ''))
        except (TypeError, ValueError): return False
        prior = self.store.get(workspace, project, identifier, prior_revision)
        if not prior or prior_revision > rfq['revision']: return False
        old = {'status':prior['data']['status'],'gmail_message_id':prior['data']['gmail_message_id'] or '',
            'gmail_thread_ids':','.join(prior['data']['gmail_thread_ids']),'revision':prior['revision']}
        equal = lambda desired: all(str(actual.get(k,''))==str(v if v is not None else '') for k,v in desired.items())
        if not (equal(fields) or equal(old)): return False
        job.setdefault('rfq_projection_recovery',{})[key] = {'previous':deepcopy(action),
            'observed':{k:actual.get(k,'') for k in fields},'basis':'DESIRED_ROW' if equal(fields) else 'UNCHANGED_PRIOR_ROW'}
        job['phase']='SENDING';job['issues']=[]
        self.save_job(workspace,job)
        return True
