"""Bounded, owner-scoped real-record KG exploration via validated read plans."""
import time
from .data_relationships import fingerprint
from .data_queries import query_types
from .data_selection import dataset_label
from .google_connections import GoogleConnections, now
from .service import ApiFailure


class KnowledgeRecords:
    def __init__(self,semantic,queries):self.semantic,self.queries,self.manager=semantic,queries,queries.manager

    def explore(self,auth,body):
        GoogleConnections.identity(auth,True);GoogleConnections.identity(auth)
        keys={'revision','dataset_id','identity_field_id','identity_value','label_field_id','relationship_id','neighbor_identity_field_id','neighbor_label_field_id','limit'}
        if not isinstance(body,dict) or set(body)!=keys or any(not isinstance(body[k],str) for k in keys-{'identity_value','limit'}) or type(body['limit']) is not int or not 1<=body['limit']<=10:
            raise ApiFailure('KG_RECORD_INPUT','Choose a current dataset, scalar identity and label fields, optional relationship and a limit of 1–10.',400)
        view=self.semantic.get(auth)
        if view['stale'] or body['revision']!=view['revision']:raise ApiFailure('KG_STALE','KG evidence changed. Reload before exploring records.',409)
        context=self.queries.context(auth);graph,datasets,fields,technical=context
        did=body['dataset_id']
        if did not in datasets:raise ApiFailure('KG_RECORD_SOURCE','Dataset not found in your current graph.',404)
        def field(fid,dataset):
            value=fields.get(fid)
            if not value or value['dataset_id']!=dataset:raise ApiFailure('KG_RECORD_FIELD','Select a supported scalar field from the chosen dataset.',400)
            return value
        identity=field(body['identity_field_id'],did);field(body['label_field_id'],did)
        def key_value(meta,value):
            types=query_types(meta)
            valid=(types=={'string'} and isinstance(value,str) or types=={'integer'} and type(value) is int and abs(value)<=9007199254740991 or types=={'boolean'} and type(value) is bool)
            if not valid:raise ApiFailure('KG_RECORD_KEY','Record keys must use a supported text, exact integer or boolean value matching the selected field. Decimal, nested and ObjectId keys require a different scalar key.',422)
            return value
        key_value(identity,body['identity_value'])
        edge=None;neighbor=None
        if body['relationship_id']:
            edge=next((e for e in view['relationships'] if e['relationship_id']==body['relationship_id']),None)
            if not edge or did not in (edge['source_dataset_id'],edge['target_dataset_id']):raise ApiFailure('KG_RECORD_RELATIONSHIP','Select a relationship connected to this dataset.',400)
            if edge['status'] not in {'inferred','confirmed'} or not edge['predicate'] or edge['technical_relationship_id'] not in technical:
                raise ApiFailure('KG_RECORD_RELATIONSHIP','Record expansion requires a current semantic predicate and an independently declared or accepted technical link.',409)
            neighbor=edge['target_dataset_id'] if did==edge['source_dataset_id'] else edge['source_dataset_id']
            field(body['neighbor_identity_field_id'],neighbor);field(body['neighbor_label_field_id'],neighbor)
        elif body['neighbor_identity_field_id'] or body['neighbor_label_field_id']:
            raise ApiFailure('KG_RECORD_INPUT','Neighbor fields require a selected relationship.',400)
        deadline=time.monotonic()+55;traces=[];source_evidence=[];warnings=[]
        def read(dataset,selected,filters,limit):
            if self.semantic.authenticate is not None:
                subject=auth['subject'];current=self.semantic.authenticate(subject['workspace_id'],subject['subject_id'])
                if not current or current.get('subject')!=subject or current.get('decision')!='allow':raise ApiFailure('KG_RECORD_AUTHORITY','Record access changed. Reload your workspace.',403)
                GoogleConnections.identity(current,True);GoogleConnections.identity(current)
            if self.semantic.get(auth)['revision']!=view['revision']:raise ApiFailure('KG_STALE','Semantic KG changed during record exploration. Reload and retry.',409)
            plan=dict(base_dataset_id=dataset,joins=[],fields=sorted(set(selected)),filters=filters,group_by=[],metrics=[],order_by=[],limit=limit,explanation='Explicit bounded KG record exploration using current field IDs.',clarification='')
            self.queries.validate(plan,context)
            saved=dict(plan_id='dq_'+fingerprint([view['revision'],plan])[:32],plan=plan,expires_at=time.time()+60,context_hash=fingerprint(graph),
                field_labels={fid:dataset_label(datasets[f['dataset_id']])+' / '+f['name'] for fid,f in fields.items()},
                dataset_labels={id:dataset_label(d) for id,d in datasets.items()})
            result=self.queries.execute(auth,{'plan_id':saved['plan_id']},saved_snapshot=saved,deadline=deadline)
            traces.append(dict(plan_id=result['plan_id'],plan=result['executed_plan'],total_result_rows=result['total_result_rows'],executed_at=result['executed_at']))
            source_evidence.extend(result['sources']);warnings.extend(result['warnings'])
            return result
        def eq(fid,value):return dict(field_id=fid,op='eq',value=value)
        root_fields={identity['field_id'],body['label_field_id']}
        if edge:
            side='source_field_id' if did==edge['source_dataset_id'] else 'target_field_id'
            other='target_field_id' if side=='source_field_id' else 'source_field_id'
            root_fields.update(p[side] for p in edge['field_pairs'])
        root=read(did,root_fields,[eq(identity['field_id'],body['identity_value'])],2)
        if root['total_result_rows']>1:raise ApiFailure('KG_RECORD_IDENTITY','The selected identity matches multiple records. Choose a unique scalar key.',409)
        nodes=[];edges=[];limited=False
        def node(dataset,row,identity_id,label_id):
            value=key_value(field(identity_id,dataset),row.get(identity_id))
            item=dict(node_id='record_'+fingerprint([dataset,identity_id,type(value).__name__,value])[:32],dataset_id=dataset,
                dataset_label=dataset_label(datasets[dataset]),identity_field_id=identity_id,identity_value=value,label_field_id=label_id,
                label=str(row.get(label_id)) if row.get(label_id) is not None else 'null',
                fields=[dict(field_id=fid,name=fields[fid]['name'],value=value) for fid,value in row.items()])
            nodes.append(item);return item
        if root['rows']:
            row=root['rows'][0];first=node(did,row,identity['field_id'],body['label_field_id'])
            if edge:
                filters=[]
                for pair in edge['field_pairs']:
                    value=row.get(pair[side])
                    if value is None:break
                    key_value(field(pair[other],neighbor),value);filters.append(eq(pair[other],value))
                if len(filters)==len(edge['field_pairs']):
                    selected={body['neighbor_identity_field_id'],body['neighbor_label_field_id'],*(p[other] for p in edge['field_pairs'])}
                    adjacent=read(neighbor,selected,filters,body['limit']);limited=adjacent['limited']
                    seen=set()
                    for candidate in adjacent['rows']:
                        identity_id=body['neighbor_identity_field_id'];value=key_value(field(identity_id,neighbor),candidate.get(identity_id))
                        marker=fingerprint([type(value).__name__,value])
                        if marker in seen:raise ApiFailure('KG_RECORD_IDENTITY','Neighbor identity is not unique. Choose another scalar key.',409)
                        seen.add(marker)
                        proof=read(neighbor,{identity_id},[eq(identity_id,value)],2)
                        if proof['total_result_rows']!=1:raise ApiFailure('KG_RECORD_IDENTITY','Neighbor identity is not unique in the actual data.',409)
                        second=node(neighbor,candidate,identity_id,body['neighbor_label_field_id'])
                        source,target=(first,second) if did==edge['source_dataset_id'] else (second,first)
                        if edge['reversed']:source,target=target,source
                        edges.append(dict(edge_id='observed_'+fingerprint([edge['relationship_id'],source['node_id'],target['node_id']])[:32],relationship_id=edge['relationship_id'],
                            source_node_id=source['node_id'],target_node_id=target['node_id'],predicate=edge['predicate'],semantic_status=edge['status'],
                            structural_relationship_id=edge['technical_relationship_id'],observed_fields=[dict(source_field_id=p['source_field_id'],target_field_id=p['target_field_id'],value=row[p[side]]) for p in edge['field_pairs']]))
                else:warnings.append('The selected record has a null linking key; no related record was invented.')
        else:warnings.append('No record matches the selected identity.')
        if self.semantic.get(auth)['revision']!=view['revision']:raise ApiFailure('KG_STALE','KG changed during record exploration. Retry with current evidence.',409)
        if limited:warnings.append('Related records exceed the selected limit; this record graph is partial.')
        warnings.append('Observed matching keys establish record links, not independent proof of an inferred business interpretation. Sources use independent reads.')
        return dict(version=1,kg_revision=view['revision'],retrieved_at=now(),nodes=nodes,edges=edges,limited=limited,sources=source_evidence,query_traces=traces,warnings=sorted(set(warnings)))
