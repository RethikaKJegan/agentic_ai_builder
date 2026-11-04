"""Test-only real authenticated lifecycle API over disposable, controlled fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

if __name__=='__main__':
    import os
    os.environ['CREWAI_TESTING']='true'
    os.environ['CREWAI_TRACING_ENABLED']='false'
    os.environ['CREWAI_DISABLE_TELEMETRY']='true'
    import crewai  # Initialize the controlled adapter on the server's main thread.
    import pytest
    import uvicorn
    from tests.test_business_ontology import foundation
    from tests.test_business_generation import generation
    from tests.test_business_reference import reference
    from tests.test_business_knowledge import knowledge
    from tests.test_business_retrieval import retrieval
    from tests.test_business_investigations import investigation
    from tests.test_business_composition import composition
    from tests.test_simpson_lifecycle import configure
    from workflow_api.client_packages import package_tool_definition,PackageEvidenceConnector
    from workflow_api.main import create_app
    with TemporaryDirectory(prefix='lifecycle-ui-') as directory,pytest.MonkeyPatch.context() as monkeypatch:
        tmp=Path(directory)
        f=composition.__wrapped__(investigation.__wrapped__(retrieval.__wrapped__(knowledge.__wrapped__(reference.__wrapped__(generation.__wrapped__(foundation.__wrapped__(tmp)),monkeypatch)),tmp)))
        cases,_,_=configure(f,True)
        preparation=f.general.business_preparation
        # Bootstrap the standard development app, then restore this fixture's scope.
        f.registry._policy.workspace_id='local-workspace'
        app=create_app(service=f.general,dev_auth=True,roles=['admin','approver'],runtime_enabled=True,start_workers=False,planning_worker_enabled=False,
            environment_name='test',ui_origins='http://127.0.0.1:3237',google_oauth_config={'BUILDER_DATA_SOURCE_KEY_FILE':str(tmp/'key')})
        app.state.workflow_auth.clear();app.state.workflow_auth.update(deepcopy(f.x.a))
        f.registry._policy.workspace_id='one'
        # Route closures retain the standard service; only trusted adapters use fixtures.
        app.state.business_composition.preparation=preparation
        f.general.business_preparation=preparation
        from workflow_api.business_preparation import BusinessEvidenceConnector
        f.connectors['business_retrieve_evidence']=BusinessEvidenceConnector(preparation)
        f.general.business_composition=f.c
        packages=f.c.packages
        package=json.loads((ROOT/'ontology/client-packages/retail-complaint-fixture-v1.json').read_text())
        f.registry._policy.remaining_quota['client_package_read']=100
        assert f.registry.register_tool(package_tool_definition(),f.x.a)['status']==200
        packages.publish(f.x.a,package)
        packages.register_source(f.x.a,'retail_orders_fixture',lambda a,b:[dict(id='retail_fixture_order',complaint_id='RETAIL-C1',order_id='ORDER-1',purchase_verified=True,product_observation='Reported incorrect item; no confirmed physical cause.')])
        app.state.business_composition.packages=packages
        f.connectors['client_package_read']=PackageEvidenceConnector(packages)
        f.general.runtime_runner.connectors=f.connectors
        uvicorn.run(app,host='127.0.0.1',port=8018,log_level='warning')
