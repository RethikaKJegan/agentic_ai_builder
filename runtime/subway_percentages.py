"""Percentages from complete, verified grouped count queries only."""
from decimal import Decimal,localcontext,ROUND_HALF_UP
import json
from workflow_api.business_knowledge_model import digest


def evidence(instance,subject,query):
    from workflow_api.subway_queries import key
    if instance.get('state')!='completed' or instance.get('capability_id')!='tool.subway_query' or instance.get('verified_receipt') is not True or not query:return None
    output=instance.get('output',{});coverage=output.get('coverage',{})
    if output.get('scope')!=dict(workspace_id=subject.get('workspace_id'),owner_id=subject.get('subject_id')) or output.get('query_sha256')!=digest(query) or not output.get('query_id'):return None
    if any(coverage.get(k) is not True for k in ('complete_scan','aggregate_complete','filtered_on_entire_source')) or coverage.get('has_more') is not False or coverage.get('offset')!=0:return None
    rows=output.get('rows',[])
    if coverage.get('returned_rows')!=len(rows) or coverage.get('total_result_rows')!=len(rows):return None
    metrics=query.get('metrics',[])
    if query.get('joins')!=[] or query.get('fields')!=[] or len(metrics)!=1 or metrics[0].get('op')!='count' or metrics[0].get('field_id')!='':return None
    groups=query['group_by'];counts={};values={}
    for row in rows:
        if any(fid not in row for fid in groups):return None
        group=tuple(key(row[fid]) for fid in groups);count=row.get(metrics[0]['label'])
        if type(count) is not int or count<0 or group in counts:return None
        counts[group]=count;values[group]={fid:row[fid] for fid in groups}
    if type(coverage.get('matched_records')) is not int or sum(counts.values())!=coverage['matched_records']:return None
    sources=output.get('sources',[])
    if len(sources)!=1 or sources[0].get('dataset_id')!=query['base_dataset_id']:return None
    source=sources[0]
    if source.get('metadata_revision') is None or source.get('generation') is None or not output.get('ontology_version'):return None
    return dict(output=output,query=query,counts=counts,values=values,total=sum(counts.values()),source=(source['dataset_id'],source['metadata_revision'],source['generation']),
        filters={json.dumps(p,sort_keys=True,separators=(',',':')) for p in query['filters']})


def derive(instances,subject,catalog,queries):
    basis=(catalog.get('interpretation') or {}).get('percentage_basis','none')
    if basis not in ('overall_population','within_group'):return []
    items=[e for instance in instances if (e:=evidence(instance,subject,queries.get(instance.get('action_id')))) is not None]
    derived=[]
    for n in items:
        for d in items:
            if n['output']['query_id']==d['output']['query_id'] or n['source']!=d['source'] or n['output']['ontology_version']!=d['output']['ontology_version'] or n['query']['group_by']!=d['query']['group_by'] or not d['filters']<n['filters']:continue
            if any(group not in d['counts'] or count>d['counts'][group] for group,count in n['counts'].items()):continue
            for group,group_total in d['counts'].items():
                numerator=n['counts'].get(group,0);denominator=d['total'] if basis=='overall_population' else group_total
                with localcontext() as ctx:
                    ctx.prec=70
                    value=None if denominator==0 else format((Decimal(numerator)*100/Decimal(denominator)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),'f')
                derived.append(dict(kind='percentage_of_population',percentage_basis=basis,group=d['values'][group],numerator=str(numerator),denominator=str(denominator),percentage=value,
                    status='undefined_zero_denominator' if value is None else 'calculated',formula='numerator / denominator * 100',rounding='ROUND_HALF_UP, 2 decimal places',
                    numerator_query_id=n['output']['query_id'],denominator_query_id=d['output']['query_id'],base_dataset_id=n['query']['base_dataset_id'],scope=n['output']['scope'],
                    numerator_filters=n['query']['filters'],denominator_filters=d['query']['filters']))
    return derived
