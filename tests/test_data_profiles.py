"""Shared profiling regressions retained after workspace retirement."""
from workflow_api.data_profiles import summarize,overlap,composite

def test_profiles_have_honest_denominators_and_typed_hashes():
    fields=[dict(field_id='id',name='id')]
    profile=summarize([{},dict(id=None),dict(id=1),dict(id=1),dict(id='1'),dict(id=True)],fields)['id']
    assert (profile['sample_size'],profile['missing'],profile['nulls'],profile['null_rate'])==(6,1,1,.2)
    assert profile['distinct']==3 and profile['uniqueness']==.75
    assert summarize([],fields)['id']['null_rate'] is None
    assert overlap(profile,profile)['referential_consistency']==1
    assert not overlap(profile,profile)['population_verified']
    keys=composite([dict(a=1,b='2'),dict(a='1',b=2),dict(a=1)],['a','b'])
    assert keys['comparable']==2 and len(keys['key_hashes'])==2
    assert '1' not in profile['key_hashes']

def test_nested_fields_are_not_misreported_missing():
    fields=[dict(field_id='nested',name='a.b'),dict(field_id='array',name='items[].id')]
    profiles=summarize([{'a':{'b':None},'items':[{'id':1},{'id':2}]},{'a':{'b':'x'}}],fields)
    assert profiles['nested']['missing']==0 and profiles['nested']['nulls']==1
    assert profiles['array']['missing']==1 and profiles['array']['unsupported_values']==1

def test_rename_candidates_never_transfer_identity_or_approval():
    from workflow_api.data_drift import rename_candidates
    previous=dict(datasets=[dict(dataset_id='d',discovery_method='sampled',fields=[dict(field_id='old',name='customer_code',types=['string'])])])
    current=dict(datasets=[dict(dataset_id='d',fields=[dict(field_id='new',name='customerCode',types=['string'])])])
    candidate=rename_candidates(previous,current)[0]
    assert candidate['classification']=='unverified_hypothesis' and candidate['validation_status']=='needs_review'
    assert candidate['sampled_omission_is_not_deletion'] and candidate['previous_field_id']!=candidate['current_field_id']
