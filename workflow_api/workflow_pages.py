"""Bounded, workspace-scoped workflow discovery; cursor is a workflow ID."""
from contextlib import nullcontext
import json
import re

def read_page(store, workspace, cursor=None, limit=50, connection=None):
    from .service import ApiFailure
    if cursor is not None and (not isinstance(cursor,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',cursor)):
        raise ApiFailure('INVALID_CURSOR','Use the workflow cursor returned by the server.',400)
    with (nullcontext(connection) if connection is not None else store.transaction(write=False)) as db:
        rows=db.execute('''SELECT r.document FROM revisions r WHERE r.workspace=? AND r.workflow_id>?
            AND r.version=(SELECT MAX(s.version) FROM revisions s WHERE s.workspace=r.workspace AND s.workflow_id=r.workflow_id)
            AND NOT EXISTS (SELECT 1 FROM lifecycle_tombstones t WHERE t.workspace=r.workspace AND t.workflow_id=r.workflow_id)
            ORDER BY r.workflow_id LIMIT ?''',(workspace,cursor or '',limit+1)).fetchall()
        total=db.execute('''SELECT COUNT(DISTINCT r.workflow_id) FROM revisions r WHERE r.workspace=?
            AND NOT EXISTS (SELECT 1 FROM lifecycle_tombstones t WHERE t.workspace=r.workspace AND t.workflow_id=r.workflow_id)''',(workspace,)).fetchone()[0]
        from .workflow_titles import project
        items=[project(db,workspace,json.loads(row[0])) for row in rows[:limit]]
    return dict(items=items,total=total,has_more=len(rows)>limit,next_cursor=items[-1]['workflow_id'] if len(rows)>limit else None)
