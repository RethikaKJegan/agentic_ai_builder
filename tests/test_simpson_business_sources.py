"""Fixture contracts for aggregate-only probes; not live business evidence."""
from scripts.verify_simpson_business_sources import (
    MAX_TIME_MS, SAMPLE_LIMIT, SOURCES, field_pipeline, profile,
    reference_pipeline, reference_profile, safe_failure,
)


class Collection:
    def __init__(self, rows=(), error=None):
        self.rows, self.error, self.calls = rows, error, []

    def aggregate(self, pipeline, **kwargs):
        self.calls.append((pipeline, kwargs))
        if self.error:
            raise self.error
        return self.rows


def test_both_scoped_sources_are_required_and_profiles_are_bounded():
    assert {label for label, _ in SOURCES.values()} == {'db1', 'db2'}
    for _, targets in SOURCES.values():
        for fields in targets.values():
            pipeline = field_pipeline(fields)
            assert pipeline[0] == {'$limit': SAMPLE_LIMIT}
            assert pipeline[-1]['$group']['count'] == {'$sum': 1}
            assert not any('$out' in s or '$merge' in s for s in pipeline)


def test_missing_null_and_observed_values_are_distinct():
    collection = Collection([
        {'_id': {'field': 'a', 'bson_type': 'missing'}, 'count': 2},
        {'_id': {'field': 'b', 'bson_type': 'null'}, 'count': 2},
        {'_id': {'field': 'c', 'bson_type': 'string'}, 'count': 1},
        {'_id': {'field': 'c', 'bson_type': 'missing'}, 'count': 1},
    ])
    result = profile(collection, ['a', 'b', 'c'])
    assert result['sample_size'] == 2
    assert [f['status'] for f in result['fields']] == ['not_observed_in_bounded_sample', 'observed_only_null', 'observed_value']
    assert collection.calls[0][1] == {'maxTimeMS': MAX_TIME_MS, 'allowDiskUse': False}


def test_empty_is_not_absent_schema():
    result = profile(Collection(), ['f'])
    assert result['status'] == 'empty_collection'
    assert result['fields'][0]['bson_type_counts'] == {}


def test_failures_never_export_driver_message_or_untrusted_code():
    exc = RuntimeError('private-uri/password/source-value')
    exc.code = 'private-value'
    assert safe_failure(exc) == {'error_type': 'RuntimeError', 'code': None}
    for result in (profile(Collection(error=exc), ['f']), reference_profile(Collection(error=exc), 'f', 'target')):
        assert result['status'] == 'unavailable'
        assert 'private' not in str(result)


def test_reference_checks_export_aggregate_counts_not_ids():
    collection = Collection([{'_id': 'single_target', 'count': 2}, {'_id': 'unresolved', 'count': 1}])
    result = reference_profile(collection, 'oem', 'oems')
    assert result['sample_size'] == 3
    assert result['counts'] == {'single_target': 2, 'unresolved': 1}
    pipeline = reference_pipeline('oem', 'oems')
    assert pipeline[0] == {'$limit': SAMPLE_LIMIT}
    assert pipeline[-1] == {'$group': {'_id': '$state', 'count': {'$sum': 1}}}
