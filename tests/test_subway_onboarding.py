"""Subway archive, ontology, source pinning and tenant regression checks. No network."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tarfile

import pytest
from scripts.subway_archive_analysis import analyze
from workflow_api.restored_subway_sources import RestoredSubwayAdapters
from workflow_api.business_compiler import check_snapshot, compile_snapshot
from workflow_api.service import ApiFailure
from workflow_api.subway_onboarding import build_package, install_package_sources
from workflow_api.client_packages import ClientPackages, PackageEvidenceConnector
from workflow_api.business_ontology import BusinessOntology
from workflow_api.business_sources import BusinessSources
from workflow_api.data_sources import DataSources
from workflow_api.storage import WorkflowStore
from cryptography.fernet import Fernet

ROOT=Path(__file__).resolve().parents[1]
SNAPSHOT=json.loads((ROOT/'ontology/subway/business-ontology-v1.json').read_text())


def test_subway_ontology_has_its_own_layers_modules_evidence_and_compilation():
    ns=check_snapshot(SNAPSHOT)
    assert ns.startswith('urn:subway-business:')
    assert {c['layer'] for c in SNAPSHOT['concepts']}=={'foundational','common','domain','organization','business'}
    assert len(SNAPSHOT['concepts'])==54 and len(SNAPSHOT['relationships'])==11
    assert SNAPSHOT['rules']==[]
    report,_=compile_snapshot(SNAPSHOT)
    assert report['status']=='passed' and report['business_policy_verified'] is False
    assert report['instance_validation']=='not_run'
    package=build_package(SNAPSHOT)
    assert package==json.loads((ROOT/'ontology/subway/knowledge-package-v1.json').read_text())
    assert len(package['capability_contracts'])==12


@pytest.mark.parametrize('change',['namespace','evidence','endpoint'])
def test_subway_compiler_rejects_forged_snapshot(change):
    draft=deepcopy(SNAPSHOT)
    if change=='namespace':draft['workspace']['namespace']='urn:simpson-business:'+'a'*24+':'
    if change=='evidence':draft['sources'][0]['text']+=' modified'
    if change=='endpoint':draft['relationships'][0]['target']='engines:foreign'
    with pytest.raises(ApiFailure):check_snapshot(draft)


@pytest.mark.parametrize('member,kind',[('../outside.bson','file'),('/absolute.bson','file'),('link.bson','symlink'),('script.py','file')])
def test_archive_extraction_rejects_unsafe_members(tmp_path,member,kind):
    archive=tmp_path/'dump.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        item=tarfile.TarInfo(member)
        if kind=='symlink':item.type=tarfile.SYMTYPE;item.linkname='/etc/passwd';tar.addfile(item)
        else:item.size=1;tar.addfile(item,io.BytesIO(b'x'))
    with pytest.raises(ValueError):analyze(archive,tmp_path/'out')
    assert not (tmp_path/'outside.bson').exists()


def test_restore_adapter_rejects_any_endpoint_database_or_principal_change(tmp_path):
    uri='mongodb://reader:fixture@127.0.0.1:27028/?authSource=admin'
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(dict(client_id='subway',sources={'central':dict(database='subway_central',uri_sha256=hashlib.sha256(uri.encode()).hexdigest())})))
    adapter=RestoredSubwayAdapters(dict(BUILDER_CLIENT_ID='subway',BUILDER_SUBWAY_RESTORED_MANIFEST=str(manifest)))
    config=dict(engine='mongodb',uri=uri,database='subway_central',_subway_source_id='central')
    assert adapter.target(config)['database']=='subway_central'
    for changed in [dict(database='simpsons'),dict(_subway_source_id='foreign'),dict(uri=uri.replace('reader:','admin:')),dict(uri=uri.replace('27028','27017')),dict(uri=uri.replace('127.0.0.1','example.com')),dict(engine='postgresql')]:
        with pytest.raises(ApiFailure):adapter.target({**config,**changed})


def test_package_reads_recheck_owner_source_binding_and_revoke_stale_metadata(tmp_path,monkeypatch):
    store=WorkflowStore(tmp_path/'app.sqlite3');key=tmp_path/'key';key.write_bytes(Fernet.generate_key())
    manager=DataSources(store,dict(BUILDER_DATA_SOURCE_KEY_FILE=str(key)))
    ontology=BusinessOntology(store);auth=dict(decision='allow',subject=dict(workspace_id='client-subway',subject_id='subway-client'),roles=['admin'],permissions=['workflow.plan','workflow.edit','workflow.execute','tools.read','tools.assign','tools.manage'],scopes=['workspace:read','workspace:write'])
    scope=('client-subway','subway-client')
    with store.transaction() as db:
        db.execute('INSERT INTO business_ontology_workspaces VALUES (?,?,?,?)',(*scope,'subway',json.dumps(SNAPSHOT['workspace'])))
        db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(*scope,SNAPSHOT['version_id'],json.dumps(SNAPSHOT)))
        for role in ['central','finance']:
            cid='dbconn_subway_'+role;datasets=[]
            for c in SNAPSHOT['concepts']:
                prefix=':'+role+'_'
                if prefix not in c['id']:continue
                name=c['id'].split(prefix)[1]
                datasets.append(dict(dataset_id=name,name=name,fields=[dict(name=p['name'],field_id=p['name'],types=['integer' if p['name']=='_id' else 'string']) for p in c['properties']]))
            doc=dict(connection_id=cid,name=cid,engine='mongodb',database='subway_'+role,connection_status='connected',profiling_status='ready',metadata_revision=1,generation=1)
            secret=manager.cipher.encrypt(json.dumps(dict(engine='mongodb',database='subway_'+role)).encode()).decode()
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,*scope,secret,json.dumps(doc)))
            db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(cid,1,json.dumps(dict(datasets=datasets))))
    packages=ClientPackages(store);packages.publish(auth,build_package(SNAPSHOT))
    service=SimpleNamespace(store=store,business_composition=SimpleNamespace(packages=packages))
    app=SimpleNamespace(state=SimpleNamespace(workflow_service=service,business_ontology=ontology,data_sources=manager,business_sources=BusinessSources(ontology,manager)))
    install_package_sources(app,auth,dict(BUILDER_CLIENT_ID='subway'))
    calls=[]
    def objects(self,config,dataset,fields,keys,filters,offset,limit,deadline):
        calls.append((config['database'],dataset['name'],limit))
        return [{f['name']:1 if f['name']=='_id' else 'fixture' for f in fields}]
    monkeypatch.setattr('workflow_api.data_queries.QueryReader.objects',objects)
    inputs=dict(package_id='subway-business-v1',revision=1,capability_id='subway.read.stores')
    result=packages.read(auth,inputs)
    assert result['records'] and calls==[('subway_central','stores',25)]
    other=deepcopy(auth);other['subject']['workspace_id']='client-simpsons'
    with pytest.raises(Exception):packages.read(other,inputs)
    binding=packages.get(auth,'subway-business-v1',1)['resource_bindings']['subway.read.stores']
    provider=packages.providers[(*scope,binding['source_id'])]
    with pytest.raises(ApiFailure):provider(auth,{**binding,'collection':'tokens'})
    with store.transaction() as db:
        raw=db.execute('SELECT document FROM data_source_connections WHERE connection_id=?',('dbconn_subway_central',)).fetchone()[0];doc=json.loads(raw);doc['metadata_revision']=2
        db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(doc),'dbconn_subway_central'))
    with pytest.raises(ApiFailure):packages.read(auth,inputs)
    assert len(calls)==1
