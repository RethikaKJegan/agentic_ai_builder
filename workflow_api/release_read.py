"""Read-only, workspace-scoped release identity for workflow journey guidance."""
import json


def read_release_state(store, workspace, workflow_id):
    with store.transaction(write=False) as db:
        row = db.execute('SELECT r.document FROM lifecycle_active a JOIN lifecycle_releases r ON r.release_id=a.release_id WHERE a.workspace=? AND r.workspace=? AND a.workflow_id=?', (workspace, workspace, workflow_id)).fetchone()
        if row is None:
            row = db.execute('SELECT document FROM lifecycle_releases WHERE workspace=? AND workflow_id=? ORDER BY generation DESC LIMIT 1', (workspace, workflow_id)).fetchone()
    if row is None:
        return {'workflow_id': workflow_id, 'release': None}
    release = json.loads(row[0])
    return {'workflow_id': workflow_id, 'release': {
        'release_id': release['release_id'], 'workflow_version': release['revision']['workflow_version'],
        'state': release['state'], 'trigger_binding_count': len(release['trigger_binding_ids']),
    }}
