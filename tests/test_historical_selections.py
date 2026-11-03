"""Saved-reference compatibility using a fixture captured before retirement."""
import json
from pathlib import Path
import pytest
from tests.test_data_relationships import sources,auth
from workflow_api.data_sources import DataSources
from workflow_api.storage import WorkflowStore
from workflow_api.service import ApiFailure
from tests.test_runtime import RuntimeFixture
from types import SimpleNamespace
from runtime.graph import GraphRunner
from runtime.service import RuntimeFailure

FIXTURE=json.loads((Path(__file__).parent/'fixtures/historical-ontology.json').read_text())


def seed(manager,scope):
    with manager.store.transaction() as db:
        for source in sources():
            c=source['connection']
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(c['connection_id'],*scope,'encrypted',json.dumps(c)))
            db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(c['connection_id'],1,json.dumps(source['snapshot'])))
        for r in FIXTURE['records']:db.execute('INSERT INTO ontology_records VALUES (?,?,?,?)',(*scope,r['id'],json.dumps(r)))
        manifest=FIXTURE['manifest'];db.execute('INSERT INTO ontology_selections VALUES (?,?,?,?)',(*scope,manifest['selection_id'],json.dumps(manifest)))
    return manifest['selection_id']


@pytest.fixture
def historical(tmp_path):
    manager=DataSources(WorkflowStore(tmp_path/'historical.sqlite'),{})
    sid=seed(manager,('one','alice'))
    return manager,manager.ontology_foundation,sid


def test_exact_saved_selection_and_binding_parity(historical):
    manager,guard,sid=historical
    with manager.store.transaction() as db:
        assert guard.validate_selection(db,auth(),sid)==FIXTURE['manifest']
        assert guard.bind(db,auth(),sid,'workflow',1,'run')==FIXTURE['expected_binding']


@pytest.mark.parametrize('change',['disconnect','field_type','definition_revision','dependency_revision'])
def test_historical_revalidation_preserves_previous_authority(historical,change):
    manager,guard,sid=historical
    with manager.store.transaction() as db:
        if change=='disconnect':
            raw=db.execute("SELECT document FROM data_source_connections WHERE connection_id='pg'").fetchone()[0];doc=json.loads(raw);doc['connection_status']='disconnected';db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='pg'",(json.dumps(doc),))
        elif change=='field_type':
            raw=db.execute("SELECT document FROM data_source_snapshots WHERE connection_id='pg' AND revision=1").fetchone()[0];doc=json.loads(raw);doc['datasets'][0]['fields'][0]['types']=['boolean'];db.execute("UPDATE data_source_snapshots SET document=? WHERE connection_id='pg' AND revision=1",(json.dumps(doc),))
        else:
            rid='party' if change=='dependency_revision' else 'customer'
            raw=db.execute('SELECT document FROM ontology_records WHERE record_id=?',(rid,)).fetchone()[0];doc=json.loads(raw);doc['revision']+=1;db.execute('UPDATE ontology_records SET document=? WHERE record_id=?',(json.dumps(doc),rid))
        with pytest.raises(ApiFailure) as exc:guard.validate_selection(db,auth(),sid)
        assert exc.value.code=='ONTOLOGY_STALE'


def test_source_change_preserves_historical_impact_invalidation(historical):
    manager,guard,sid=historical
    with manager.store.transaction() as db:
        guard.bind(db,auth(),sid,'workflow',1,'run')
        raw=db.execute("SELECT document FROM data_source_connections WHERE connection_id='pg'").fetchone()[0];doc=json.loads(raw);doc['connection_status']='disconnected';db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='pg'",(json.dumps(doc),))
        guard.source_changed(db,('one','alice'))
        with pytest.raises(ApiFailure):guard.validate_selection(db,auth(),sid)
        impacts=[json.loads(r[0]) for r in db.execute('SELECT document FROM ontology_impacts')]
        assert any(i['workflow_id']=='workflow' and i['run_id']=='run' for i in impacts)


class HistoricalRuntimeTests(RuntimeFixture):
    def setUp(self):
        super().setUp()
        self.manager=DataSources(self.store,{})
        self.sid=seed(self.manager,('local-workspace','operator'))
        self.workflows.database_workflows=SimpleNamespace(manager=self.manager)
        self.workflow['metadata']['ontology_selection_id']=self.sid;self.put()

    def test_actual_runtime_completes_and_records_the_saved_reference(self):
        run=self.runtime.create_run(self.request(),self.auth)
        result=GraphRunner(self.runtime).advance(run['run_id'],self.auth)
        self.assertEqual(result['status'],'completed')
        with self.store.transaction(write=False) as db:bindings=[json.loads(r[0]) for r in db.execute('SELECT document FROM ontology_selections')]
        self.assertTrue(any(s.get('run_id')==run['run_id'] and s['origin_selection_id']==self.sid for s in bindings))

    def test_actual_runtime_denies_stale_reference_without_creating_a_run(self):
        with self.store.transaction() as db:
            raw=db.execute("SELECT document FROM ontology_records WHERE record_id='customer'").fetchone()[0]
            document=json.loads(raw);document['revision']+=1
            db.execute("UPDATE ontology_records SET document=? WHERE record_id='customer'",(json.dumps(document),))
        with self.assertRaises(RuntimeFailure) as error:self.runtime.create_run(self.request(),self.auth)
        self.assertEqual(error.exception.code,'ONTOLOGY_STALE')
        with self.store.transaction(write=False) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM runtime_runs').fetchone()[0],0)
