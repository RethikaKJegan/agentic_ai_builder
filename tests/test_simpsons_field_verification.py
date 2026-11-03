"""Read-only probe contracts; fixtures are not production business evidence."""
import pytest

from scripts.verify_simpsons_field_bindings import MAX_TIME_MS, SAMPLE_LIMIT, failure, probe_collection


class Collection:
    def __init__(self,has_records=True,types=(),error=None):
        self.has_records=has_records;self.types=types;self.error=error;self.calls=[]

    def aggregate(self,pipeline,**options):
        self.calls.append((pipeline,options))
        assert not any('$out' in stage or '$merge' in stage for stage in pipeline)
        if len(self.calls)==1:
            return [{'has_record':True}] if self.has_records else []
        if self.error:raise self.error
        return self.types


def test_targeted_probe_returns_only_types_with_limits():
    collection=Collection(types=[{'_id':'string','count':24},{'_id':'null','count':1}])
    result=probe_collection(collection,['approvedBy'],{})[0]
    assert result['status']=='observed_field'
    assert result['observed_bson_types']==['null','string']
    assert result['matching_sample_count']==25
    assert not result['reference_target_verified'] and not result['business_policy_approved']
    pipeline,options=collection.calls[1]
    assert pipeline[0]=={'$match':{'approvedBy':{'$exists':True}}}
    assert pipeline[1]=={'$limit':SAMPLE_LIMIT}
    assert pipeline[2]=={'$project':{'_id':0,'bson_type':{'$type':'$approvedBy'}}}
    assert options==dict(maxTimeMS=MAX_TIME_MS,allowDiskUse=False)


@pytest.mark.parametrize('declared',[False,True])
def test_empty_collection_distinguished_from_undeclared_schema(declared):
    info={'options':{'validator':{'$jsonSchema':{'properties':{'version':{'bsonType':'int'}} if declared else {}}}}}
    collection=Collection(has_records=False)
    result=probe_collection(collection,['version'],info)[0]
    assert result['status']==('schema_declared_empty_collection' if declared else 'empty_collection_no_schema_declaration')
    assert result['json_schema_declared']==declared
    assert result['observed_bson_types']==[]
    assert len(collection.calls)==1


def test_no_matching_field_does_not_claim_schema_absence():
    result=probe_collection(Collection(types=[]),['requestedBy'],{})[0]
    assert result['status']=='not_observed_in_completed_probe'
    assert result['collection_has_records'] and not result['json_schema_declared']
    assert not result['reference_target_verified']


def test_query_failure_remains_unavailable_and_redacts_error_values():
    result=probe_collection(Collection(error=RuntimeError('private-value@private-host')),['status'],{})[0]
    assert result['status']=='unavailable'
    assert result['error_type']=='RuntimeError'
    assert 'private' not in str(result)
    assert failure(RuntimeError('password=private'))==dict(error_type='RuntimeError',code=None)


def test_declared_field_without_stored_values_keeps_declaration():
    info={'options':{'validator':{'$jsonSchema':{'properties':{'version':{'bsonType':'int'}},'required':['version']}}}}
    result=probe_collection(Collection(types=[]),['version'],info)[0]
    assert result['status']=='schema_declared_not_observed'
    assert result['declared_bson_type']=='int' and result['declared_required']


def test_targeted_observation_survives_sample_omission_without_hiding_type_drift():
    from copy import deepcopy
    from workflow_api.data_drift import retain_targeted_observations
    old=dict(datasets=[dict(dataset_id='tickets',name='tickets',discovery_method='sampled',fields=[
        dict(name='serial',types=['string'],discovery_method='sampled'),
        dict(name='approval',types=['string'],discovery_method='sampled')])])
    sample=deepcopy(old);sample['datasets'][0]['fields'].pop()
    evidence=[dict(dataset_id='tickets',field=deepcopy(old['datasets'][0]['fields'][1]))]
    merged=retain_targeted_observations(old,sample,evidence)
    assert merged['datasets'][0]['fields']==old['datasets'][0]['fields']
    assert 'prior targeted observation retained' in merged['warnings'][0]
    changed=deepcopy(old);changed['datasets'][0]['fields'][1].update(types=['integer'],discovery_method='sampled')
    changed['datasets'][0]['fields'].reverse()
    observed=retain_targeted_observations(old,changed,evidence)['datasets'][0]['fields']
    assert [f['name'] for f in observed]==['serial','approval']
    assert observed[1]['types']==['integer']


def test_targeted_observation_does_not_fill_declared_schema_or_missing_collection():
    from workflow_api.data_drift import retain_targeted_observations
    old=dict(datasets=[dict(dataset_id='d',fields=[dict(name='old',discovery_method='targeted_read_only_field_probe')])])
    declared=dict(datasets=[dict(dataset_id='d',name='d',discovery_method='declared',fields=[])])
    evidence=[dict(dataset_id='d',field=dict(name='old',types=['string'],discovery_method='sampled'))]
    assert retain_targeted_observations(old,declared,evidence)['datasets'][0]['fields']==[]
    assert retain_targeted_observations(old,dict(datasets=[]),evidence)['datasets']==[]
