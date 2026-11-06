"""Trusted Subway source bindings over the existing package/runtime pipeline."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
from .business_sources import fields_for
from .business_graph import at
from .data_queries import QueryReader
from .data_write_adapter import pack, public_record
from .service import ApiFailure

PACKAGE_ID='subway-business-v1'
VERSION_ID='bov_subway_archive_v1'
# Explicit scalar projections. These are bounded evidence reads, never totals or joins.
READS=[
 ('central','stores',['_id','name','storeNumber','restaurantName','region','status']),
 ('central','vendors',['_id','name','vendorCode']),
 ('finance','companies',['_id','name']),
 ('finance','purchaseorders',['_id','poNumber','poDate','vendorName','status','totalAmount']),
 ('finance','grns',['_id','purchaseOrderId','invoiceDataId','status']),
 ('finance','invoicedatas',['_id','poId','grnId','invoiceNumber','paymentStatus','status']),
 ('finance','budgets',['_id','name','storeId','amount','status']),
 ('finance','lineitems',['_id','budgetId','category','amount','status']),
 ('finance','approvals',['_id','approvalConfigId','status']),
 ('finance','smallwarepos',['_id','poNumber','status','amount']),
 ('central','plactuals',['_id','storeId','storeCode','plItem','actual','aop']),
 ('central','arolds',['_id','customerNum','entity','weekEndingDate','netSales','endBalance'])]


def build_package(snapshot):
    from .client_packages import PACKAGE_INPUT, PACKAGE_OUTPUT
    from .capability_contracts import contract
    package=dict(package_id=PACKAGE_ID,revision=1,client_id='subway',domain='restaurant_operations',ontology_version=snapshot['version_id'],concepts=[],relationships=[],source_mappings=[],evidence_requirements=[],capability_contracts={},rules=[],resource_bindings={},validation_requirements=['acyclic_dependencies','mapped_evidence','current_source_authority'])
    for role,name,preferred in READS:
        concept=next(c for c in snapshot['concepts'] if c['id'].endswith(':'+role+'_'+name))
        available={p['name'] for p in concept['properties']};names=[f for f in preferred if f in available]
        if '_id' not in names:raise ValueError('A source identity is required.')
        cid='subway.read.'+name;sid='subway.'+role+'.'+name
        package['concepts'].append(dict(id=concept['id'],label=concept['label'],definition=concept['definition']))
        cap=contract(cid,'retrieve_bounded_source_records','Read up to 25 '+concept['label']+' records in native ID order. This is a bounded snapshot sample; it cannot answer arbitrary filters, exact totals or exhaustive aggregate questions.','tool',tool_operation='business.retrieve_package_evidence',effect='read',inputs=PACKAGE_INPUT,outputs=PACKAGE_OUTPUT,verify='mapped_evidence_and_coverage',domain='restaurant_operations')
        cap['required_ontology']=[concept['id']];package['capability_contracts'][cid]=cap
        mids=[]
        for field in names:
            mid=sid+'.'+field;mids.append(mid)
            package['source_mappings'].append(dict(id=mid,concept=concept['id'],field=field,source=sid))
        package['resource_bindings'][cid]=dict(source_id=sid,mapping_ids=mids,connection_id='dbconn_subway_'+role,collection=name,fields=names,metadata_revision=1,generation=1,limit=25)
        package['evidence_requirements'].append(dict(capability_id=cid,mapping_id=sid+'._id'))
    return package


def install_package_sources(app,auth,env):
    if env.get('BUILDER_CLIENT_ID')!='subway' or auth['subject']!={'workspace_id':'client-subway','subject_id':'subway-client'}:
        raise ValueError('Subway bindings require the dedicated Subway authority.')
    service=app.state.workflow_service;packages=service.business_composition.packages
    snapshot=app.state.business_ontology.version(auth,VERSION_ID)
    expected=build_package(snapshot);stored=packages.get(auth,PACKAGE_ID,1)
    if {k:v for k,v in stored.items() if k!='sha256'}!=expected:
        raise ValueError('Subway package differs from trusted source bindings.')
    sources=app.state.business_sources;reader=QueryReader(app.state.data_sources)
    for binding in expected['resource_bindings'].values():
        pinned=deepcopy(binding)
        def provide(current,binding,pinned=pinned):
            if current['subject']!=auth['subject'] or binding!=pinned:
                raise ApiFailure('CLIENT_SOURCE_DENIED','The read is outside the pinned Subway source.',403)
            request=dict(connection_id=pinned['connection_id'],dataset_id='',metadata_revision=pinned['metadata_revision'],generation=pinned['generation'])
            sources.authorize(current)
            with service.store.transaction(write=False) as db:
                _,_,_,metadata=sources.bound(db,current,pinned['connection_id'])
            if not metadata:raise ApiFailure('CLIENT_SOURCE_UNAVAILABLE','Current source metadata is unavailable.',409)
            ds=next((d for d in metadata['datasets'] if d['name']==pinned['collection']),None)
            if ds is None:raise ApiFailure('CLIENT_SOURCE_UNAVAILABLE','The pinned collection is unavailable.',409)
            request['dataset_id']=ds['dataset_id'];bound=sources.binding(current,request)
            by_name={f['name']:f for f in fields_for(ds)}
            if not set(pinned['fields'])<=set(by_name):raise ApiFailure('CLIENT_SOURCE_UNAVAILABLE','Pinned fields are unavailable.',409)
            config=json.loads(sources.manager.cipher.decrypt(bound['secret'].encode()))
            raw=reader.objects(config,ds,[by_name[n] for n in pinned['fields']],['_id'],{},0,pinned['limit'],time.monotonic()+10)
            after=sources.binding(current,request)
            if after['stamp']!=bound['stamp']:raise ApiFailure('BUSINESS_SOURCE_STALE','Source authority changed.',409)
            rows=[]
            for row in raw:
                record=public_record(pack({name:at(row,name) for name in pinned['fields']},'mongodb'))
                record['id']=pinned['source_id']+':'+hashlib.sha256(json.dumps(record['_id'],sort_keys=True).encode()).hexdigest()
                rows.append(record)
            with service.store.transaction() as db:sources.manager.audit(db,current,pinned['connection_id'],'subway_package_read')
            return rows
        packages.register_source(auth,pinned['source_id'],provide)
    service.default_client_package=dict(package_id=PACKAGE_ID,revision=1)
