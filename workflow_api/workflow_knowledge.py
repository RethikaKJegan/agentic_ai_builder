"""Exact ontology/source provenance for connected plans; no provider calls."""
from copy import deepcopy
from .business_knowledge_model import digest
from .service import ApiFailure


def source_mappings(snapshot):
    """Normalize existing explicit field bindings, including imported collections."""
    mappings=deepcopy((snapshot.get('knowledge') or {}).get('source_mappings',[]))
    sources=snapshot.get('workspace',{}).get('sources',{})
    for concept in snapshot.get('concepts',[]):
        binding=concept.get('dump_mapping') or {}
        role=binding.get('role');collection=binding.get('collection')
        if not role or not collection or not binding.get('connection_id') or sources.get(role)!=binding['connection_id']:continue
        for prop in concept.get('properties',[]):
            field=prop['name']
            mappings.append(dict(id='source-field:'+digest([snapshot['version_id'],concept['id'],binding['connection_id'],collection,field])[:32],
                concept_id=concept['id'],source_role=role,collection=collection,field_path=field,attribute=field))
    return mappings


def capture(composition, auth, context, version_id=None):
    """Resolve owned metadata once; never substitute a newer requested version."""
    service=composition.preparation.service
    ontology=getattr(service,'ontology',None)
    if ontology is None:return None
    try:
        version_id=version_id or service.retrieval.latest(auth)
        snapshot=ontology.version(auth,version_id)
    except ApiFailure as exc:
        return dict(unavailable=exc.code)
    scope=dict(workspace_id=auth['subject']['workspace_id'],owner_id=auth['subject']['subject_id'])
    mappings=source_mappings(snapshot)
    # Source role binding + collection + exact field path, never display labels.
    sources=snapshot.get('workspace',{}).get('sources',{})
    catalog=context.get('validated_context',{}).get('data_query_catalog',{})
    allowed={f['field_id'] for d in catalog.get('datasets',[]) for f in d['fields']}
    queries=getattr(composition.service,'workflow_queries',None)
    limitation=None
    subway=getattr(composition.service,'subway_queries',None)
    subway_catalog=context.get('validated_context',{}).get('subway_query_catalog')
    subway_pin=None
    if subway and subway_catalog and subway_catalog.get('ontology_version')==snapshot['version_id']:
        current=subway.catalog(auth)
        allowed={f['field_id'] for d in subway_catalog['sources'] for f in d['fields']}
        for mapping in mappings:
            matches=[fid for fid,f in current['fields'].items() if fid in allowed and
                f['name']==mapping['field_path'] and
                current['datasets'][f['dataset_id']]['collection']==mapping['collection'] and
                current['datasets'][f['dataset_id']]['connection_id']==sources.get(mapping['source_role'])]
            if len(matches)==1:mapping.update(field_id=matches[0],dataset_id=current['fields'][matches[0]]['dataset_id'])
        definitions={r['id']:r for r in snapshot.get('relationships',[])}
        subway_pin=dict(query_kind='subway',relationships=[{**deepcopy(r),'source':definitions[r['relationship_id']]['source'],
            'target':definitions[r['relationship_id']]['target']} for r in subway_catalog['relationships'] if r['relationship_id'] in definitions])
    if queries and allowed and not subway_pin:
        try:
            _,datasets,fields,_=queries.queries.context(auth)
        except ApiFailure as exc:limitation=exc.code
        else:
            for mapping in mappings:
                matches=[fid for fid,f in fields.items() if fid in allowed and
                    f['name']==mapping['field_path'] and
                    datasets[f['dataset_id']]['name']==mapping['collection'] and
                    datasets[f['dataset_id']]['connection']['connection_id']==sources.get(mapping['source_role'])]
                # Ambiguous source metadata never establishes a field mapping.
                if len(matches)==1:
                    mapping['field_id']=matches[0]
                    mapping['dataset_id']=fields[matches[0]]['dataset_id']
    result=dict(schema_version=1,version_id=version_id,scope=scope,
                mapping_sha256=digest(source_mappings(snapshot)),mappings=mappings)
    if limitation:result['query_mapping_unavailable']=limitation
    if subway_pin:result.update(subway_pin)
    return result


def query_fields(query, catalog):
    """Use the same expression parser as validation; include exact join operands."""
    from .data_query_engine import expression
    allowed={f['field_id'] for d in catalog.get('datasets',[]) for f in d['fields']}
    used=set(query.get('fields',[])+query.get('group_by',[]))
    used.update(f['field_id'] for f in query.get('filters',[]))
    for metric in query.get('metrics',[]):
        if metric.get('expression'):
            _,refs=expression(metric['expression'],allowed)
            used.update(refs)
    edges={e['relationship_id']:e for e in catalog.get('relationships',[])}
    for join in query.get('joins',[]):
        for pair in edges.get(join['relationship_id'],{}).get('field_pairs',[]):
            used.update([pair['source_field_id'],pair['target_field_id']])
    return used & allowed


def completed_usage(workflow,action,run):
    """Called only after normal runtime verification; persisted with the action."""
    metadata=workflow['metadata'];context=metadata['action_binding_context']
    pin=context.get('validated_context',{}).get('ontology_usage') or {}
    item=run['action_instances'][action['action_id']]
    scope=dict(workspace_id=run['workspace_id'],owner_id=run['subject_id'])
    if (not pin.get('version_id') or pin.get('scope')!=scope or
            item.get('state')!='completed' or item.get('provenance_type')=='SYNTHETIC'):return []
    mappings={m['id']:m for m in pin['mappings']};output=item['output'];result=[]
    def add(mapping,reason,**evidence):
        entry=dict(version_id=pin['version_id'],concept_id=mapping['concept_id'],mapping_id=mapping['id'],reason=reason,**evidence)
        if entry not in result:result.append(entry)
    if item.get('verified_receipt') and action['capability_id']=='tool.workflow_data_query':
        catalog=context['validated_context'].get('data_query_catalog',{})
        if (output.get('scope')==scope and output.get('metadata_revision')==catalog.get('context_hash') and output.get('query_id')):
            fields=query_fields(item.get('resolved_inputs',{}).get('query',{}),catalog)
            for mapping in mappings.values():
                if mapping.get('field_id') in fields:
                    add(mapping,'Verified query used this mapped source field.',field_id=mapping['field_id'],query_id=output['query_id'])
    elif item.get('verified_receipt') and action['capability_id']=='tool.subway_query' and pin.get('query_kind')=='subway':
        query=item.get('resolved_inputs',{}).get('query',{})
        if (output.get('scope')==scope and output.get('ontology_version')==pin['version_id'] and output.get('query_id')
                and output.get('query_sha256')==digest(query) and output.get('coverage',{}).get('complete_scan') is True):
            used=set(query.get('fields',[])+query.get('group_by',[]))
            used.update(f['field_id'] for f in query.get('filters',[]))
            used.update(m['field_id'] for m in query.get('metrics',[]) if m['field_id'])
            joins={r['relationship_id']:r for r in pin.get('relationships',[])}
            checks={r['relationship_id']:r for r in output.get('join_checks',[])}
            selected={query.get('base_dataset_id')}
            relationship_usage=[]
            for rid in query.get('joins',[]):
                if rid in joins and rid in checks:
                    r=joins[rid];selected.add(r['target_dataset_id'])
                    used.update([r['source_field_id'],r['target_field_id']])
                    relationship_usage.append(dict(relationship_id=rid,source=r['source'],target=r['target'],query_id=output['query_id'],coverage=deepcopy(checks[rid])))
            item['ontology_relationship_usage']=relationship_usage
            source_ids={s['dataset_id'] for s in output.get('sources',[])}
            for mapping in mappings.values():
                if mapping.get('dataset_id') in selected & source_ids and (mapping.get('field_id') in used or not used and mapping['field_path']=='_id'):
                    add(mapping,'Verified Subway query used this mapped source field.' if mapping.get('field_id') in used else 'Verified Subway row count scanned this mapped dataset.',
                        field_id=mapping.get('field_id'),dataset_id=mapping['dataset_id'],query_id=output['query_id'],source_role=mapping['source_role'],collection=mapping['collection'])
    elif item.get('verified_receipt'):
        # Native mapped readers return a records envelope, not query rows.
        for record in output.get('records',[]):
            if not isinstance(record,dict) or not isinstance(record.get('record_id'),str):continue
            for mid in record.get('values',{}):
                if mid in mappings:add(mappings[mid],'Verified reader returned this saved mapping.',record_id=record['record_id'])
    if action['capability_id']=='content.prepare':
        consumed={p.get('source_reference',{}).get('action_id') for p in item.get('input_provenance',[]) if p.get('binding_kind') in ('output','generated','receipt')}
        for dep in action['depends_on']:
            if dep not in consumed:continue
            upstream=run['action_instances'].get(dep,{})
            if upstream.get('state')!='completed' or upstream.get('provenance_type')=='SYNTHETIC':continue
            for usage in upstream.get('ontology_usage',[]):
                if usage['version_id']==pin['version_id'] and usage['mapping_id'] in mappings:
                    add(mappings[usage['mapping_id']],'Report consumed recorded mapped evidence.',upstream_action_id=dep,
                        **{k:usage[k] for k in ('query_id','record_id','field_id') if k in usage})
    return result
