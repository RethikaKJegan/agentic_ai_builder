"""Bounded workflow startup with keyset pages and page-scoped summaries."""
import json
from copy import deepcopy
import pytest
from tests import test_workflow_api as fixtures

@pytest.fixture
def context():
 f=fixtures.WorkflowApiTests('test_same_prompt_after_deletion_gets_stable_fresh_identity_and_agents');f.setUp()
 try:yield f
 finally:f.tearDown();f.doCleanups()

def test_pages_preserve_totals_latest_revisions_and_workspace(context):
 f=context
 with f.service.store.transaction() as db:
  for i in range(123):
   workflow=deepcopy(f.workflow);workflow['workflow_id']=f'page_{i:04}';f.service.store.put(db,'local-workspace',workflow)
  workflow['version']=2;workflow['name']='Latest revision';f.service.store.put(db,'local-workspace',workflow)
  f.service.store.put(db,'other-workspace',{**workflow,'workflow_id':'foreign'})
 cursor=None;ids=[]
 for expected in [50,50,23]:
  query='' if cursor is None else '?cursor='+cursor
  response=f.client.get('/workflows'+query);assert response.status_code==200,response.text
  page=response.json()['data'];assert len(page['items'])==expected and page['total']==123
  overview=f.client.get('/workflow-overview'+query);assert overview.status_code==200,overview.text
  snapshot=overview.json()['data'];assert [w['workflow_id'] for w in page['items']]==[w['workflow_id'] for w in snapshot['items']]
  assert snapshot['has_more']==page['has_more'] and snapshot['next_cursor']==page['next_cursor']
  ids.extend(w['workflow_id'] for w in page['items']);cursor=page['next_cursor']
 assert len(set(ids))==123 and cursor is None
 assert page['items'][-1]['version']==2

def test_page_cursor_validation_and_anonymous_denial(context):
 f=context
 for path in ['/workflows?cursor=bad%20cursor','/workflow-overview?cursor=bad%20cursor']:
  response=f.client.get(path);assert response.status_code==400,response.text
 f.client.cookies.clear();assert f.client.get('/workflows').status_code==401
