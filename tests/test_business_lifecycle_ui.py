"""Scoped lifecycle list reads consumed by the existing investigation UI."""
from copy import deepcopy
from tests.test_business_cases import service,auth,process,stage,create


def test_case_index_is_scoped_bounded_and_cursor_stable(service):
    first=create(service)
    for i in range(51):
        service.create(auth(),dict(request_key=f'case_index_{i:08}',process_definition_id='warranty',process_definition_version=1,original_user_goal=f'Fixture {i}'))
    page=service.listing(auth())
    assert len(page['items'])==50 and page['next_cursor']
    assert 'inputs' not in page['items'][0] and 'stages' not in page['items'][0]
    older=service.listing(auth(),page['next_cursor'])
    assert len(older['items'])==2 and older['next_cursor'] is None
    assert older['items'][-1]['case_id']==first['case_id']
    for key in ('workspace_id','subject_id'):
        other=deepcopy(auth());other['subject'][key]='different'
        assert service.listing(other)['items']==[]
        assert service.process_listing(other)['items']==[]


def test_process_index_preserves_exact_scoped_versions(service):
    service.publish(auth(),process(stage()))
    service.publish(auth(),process(stage(name='new definition'),version=2))
    items=service.process_listing(auth())['items']
    assert [p['version'] for p in items]==[2,1]
    assert 'stages' not in items[0]
    assert service.process(auth(),'warranty',1)['stages'][0]['name']=='first'
