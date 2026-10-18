"""Phase 3 source isolation, reviewed context and truthful preview coverage."""
import json

import pytest

from tests.test_data_queries import queries, saved, joined_plan, plan
from tests.test_data_relationships import auth
from workflow_api.service import ApiFailure


def mapping(queries, node='pg_lines', status='confirmed', role='represents'):
    graph = queries.manager.relationships.detailed.get(auth())['graph']
    return queries.manager.relationships.detailed.edit(auth(), node, dict(
        revision=graph['revision'], entity_name='Sale', role=role, status=status))


def test_confirmed_context_uses_only_owned_supported_nodes(queries):
    mapping(queries)
    mapping(queries, 'pg_lines_price', role='attribute')
    item = saved(queries)
    catalog = queries.planner.calls[-1][1]
    assert catalog['confirmed_business_mappings'] == [
        dict(node_id='pg_lines', entity_name='Sale', role='represents'),
        dict(node_id='pg_lines_price', entity_name='Sale', role='attribute')]
    assert queries.reader.calls == []
    assert item['selection_preview']['business_mappings'] == catalog['confirmed_business_mappings']
    assert 'Food' not in json.dumps(catalog) and '10.20' not in json.dumps(catalog)
    with pytest.raises(ApiFailure):
        queries.plan(auth('other'), {'question': 'Count sales'})


@pytest.mark.parametrize('status', ['suggested', 'rejected', 'needs_review'])
def test_unconfirmed_or_changed_mapping_is_not_business_context(queries, status):
    mapping(queries, status='confirmed' if status == 'needs_review' else status)
    if status == 'needs_review':
        with queries.store.transaction() as db:
            source = json.loads(db.execute("SELECT document FROM data_source_connections WHERE connection_id='pg'").fetchone()[0])
            snapshot = json.loads(db.execute("SELECT document FROM data_source_snapshots WHERE connection_id='pg' AND revision=1").fetchone()[0])
            source['metadata_revision'] = 2
            snapshot['revision'] = 2
            snapshot['datasets'][0]['fields'][0]['native_type'] = 'int4'
            db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='pg'", (json.dumps(source),))
            db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)', ('pg', 2, json.dumps(snapshot)))
        queries.manager.relationships.request(auth())
        queries.manager.relationships.tick()
    saved(queries)
    assert queries.planner.calls[-1][1]['confirmed_business_mappings'] == []


@pytest.mark.parametrize('engine', ['postgresql', 'mongodb'])
def test_single_engine_preview_and_execution_exclude_unrelated_source(queries, engine):
    if engine == 'mongodb':
        queries.planner.output = dict(plan(), base_dataset_id='mongo_categories',
                                     fields=['mongo_categories_name'], metrics=[])
    item = saved(queries)
    preview = item['selection_preview']
    assert preview['catalog_dataset_count'] == 2
    assert len(preview['sources']) == 1 and preview['sources'][0]['engine'] == engine
    assert preview['relationships'] == []
    assert len(preview['sources'][0]['fields']) == (1 if engine == 'mongodb' else 3)
    assert all(field['purposes'] == ['output' if engine == 'mongodb' else 'metric']
               for field in preview['sources'][0]['fields'])
    result = queries.execute(auth(), {'plan_id': item['plan_id']})
    assert result['executed_plan'] == item['plan']
    assert queries.reader.calls == [preview['sources'][0]['dataset_id']]


def test_combined_preview_retains_exact_join_keys_and_actual_sources(queries):
    item = joined_plan(queries)
    preview = item['selection_preview']
    assert [source['engine'] for source in preview['sources']] == ['postgresql', 'mongodb']
    edge = preview['relationships'][0]
    assert edge['status'] == 'accepted'
    assert edge['field_pairs'] == [dict(source_field_id='pg_lines_categoryID', target_field_id='mongo_categories_categoryID')]
    assert preview['sources'][0]['label'] == 'pg / demo / northwind / lines'
    uses = {field['field_id']: field['purposes'] for source in preview['sources'] for field in source['fields']}
    assert uses['pg_lines_categoryID'] == ['join']
    assert uses['mongo_categories_name'] == ['group']
    result = queries.execute(auth(), {'plan_id': item['plan_id']})
    assert {source['dataset_id'] for source in result['sources']} == {source['dataset_id'] for source in preview['sources']}


def test_confirmed_business_entity_never_authorizes_a_join(queries):
    mapping(queries)
    edge = queries.manager.relationships.get(auth())['graph']['relationships'][0]
    queries.planner.output = dict(plan(), joins=[dict(relationship_id=edge['relationship_id'], target_dataset_id='mongo_categories')])
    with pytest.raises(ApiFailure):
        saved(queries)
    assert queries.reader.calls == []


def test_clarification_has_no_selected_sources_or_reads(queries):
    queries.planner.output = dict(plan(), clarification='Which measure do you mean?')
    preview = saved(queries)['selection_preview']
    assert preview['sources'] == preview['relationships'] == preview['business_mappings'] == []
    assert queries.reader.calls == []


def test_mapping_change_invalidates_saved_preview_before_reads(queries):
    item = saved(queries)
    mapping(queries)
    with pytest.raises(ApiFailure) as exc:
        queries.execute(auth(), {'plan_id': item['plan_id']})
    assert exc.value.code == 'DATA_QUERY_STALE' and queries.reader.calls == []


def test_row_count_preview_and_legacy_plan_compatibility(queries):
    queries.planner.output = dict(plan(), metrics=[dict(label='rows', op='count', expression='')])
    item = saved(queries)
    assert item['selection_preview']['sources'][0]['fields'][0]['purposes'] == ['row_count']
    with queries.store.transaction() as db:
        document = json.loads(db.execute('SELECT document FROM data_query_plans WHERE plan_id=?', (item['plan_id'],)).fetchone()[0])
        document.pop('selection_preview')
        db.execute('UPDATE data_query_plans SET document=? WHERE plan_id=?', (json.dumps(document), item['plan_id']))
    assert queries.execute(auth(), {'plan_id': item['plan_id']})['rows'] == [{'rows': 3}]


def test_background_job_preserves_selection_after_coordinator_restart(queries):
    from workflow_api.data_query_jobs import DataQueryJobs
    item = joined_plan(queries)
    jobs = DataQueryJobs(queries, lambda workspace, owner: auth())
    job = jobs.submit(auth(), {'plan_id': item['plan_id']}, 'selection_preview_job')
    assert job['planned_query']['selection_preview'] == item['selection_preview']
    recovered = DataQueryJobs(queries, lambda workspace, owner: auth()).get(auth(), job['job_id'])
    assert recovered['planned_query']['selection_preview'] == item['selection_preview']
    assert queries.reader.calls == []


def test_business_review_race_does_not_publish_a_plan(queries):
    generate = queries.planner.generate

    def changed(question, catalog):
        mapping(queries)
        return generate(question, catalog)

    queries.planner.generate = changed
    with pytest.raises(ApiFailure) as exc:
        saved(queries)
    assert exc.value.code == 'DATA_QUERY_STALE' and queries.reader.calls == []
    with queries.store.transaction(write=False) as db:
        assert db.execute('SELECT count(*) FROM data_query_plans').fetchone()[0] == 0
