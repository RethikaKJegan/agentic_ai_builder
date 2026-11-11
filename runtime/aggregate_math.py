"""Derived evidence from verified query aggregates, never displayed source rows."""
from decimal import Decimal,localcontext,ROUND_HALF_UP
import json

GUIDANCE=(
 'Use supplied verified_aggregate_math as deterministic derived evidence, including requested percentages '
 'in report text and spreadsheet cells. These values are computed by trusted Decimal arithmetic from '
 'complete compatible count aggregates, not estimated from displayed records. Preserve the supplied '
 'numerator/denominator query references and population filters; label rounded percentages to two '
 'decimal places. A zero denominator is undefined, never zero percent. Do not invent missing metrics '
 'or calculate population statistics from displayed sample rows.'
)


def count_evidence(instance,subject):
    if (instance.get('state')!='completed' or instance.get('capability_id')!='tool.workflow_data_query'
            or instance.get('verified_receipt') is not True):return None
    output=instance.get('output',{});coverage=output.get('coverage',{});result=output.get('result',{})
    expected=dict(workspace_id=subject.get('workspace_id'),owner_id=subject.get('subject_id'))
    if output.get('scope')!=expected or not output.get('metadata_revision') or not output.get('query_id'):return None
    if (coverage.get('complete_scan') is not True or coverage.get('aggregate_complete') is not True
            or coverage.get('has_more') is not False or coverage.get('returned_rows')!=1
            or coverage.get('total_result_rows')!=1 or result.get('limited') is not False
            or result.get('total_result_rows')!=1):return None
    plan=result.get('executed_plan',{})
    if (not plan.get('base_dataset_id') or plan.get('joins')!=[] or plan.get('group_by')!=[]
            or plan.get('fields')!=[] or plan.get('clarification')!=''
            or not isinstance(plan.get('filters'),list) or len(plan.get('metrics',[]))!=1):return None
    metric=plan['metrics'][0]
    if metric.get('op')!='count' or metric.get('expression')!='':return None
    rows=result.get('rows',[])
    if len(rows)!=1 or not isinstance(rows[0],dict):return None
    value=rows[0].get(metric.get('label'))
    if type(value) is int:count=value
    elif isinstance(value,str) and value.isascii() and value.isdigit() and len(value)<=32:count=int(value)
    else:return None
    if count<0 or count>10**30 or type(result.get('matched_rows')) is not int or result['matched_rows']!=count:return None
    filters={json.dumps(f,sort_keys=True,separators=(',',':')) for f in plan['filters']}
    return dict(count=count,filters=filters,plan=plan,query_id=output['query_id'],scope=output['scope'],revision=output['metadata_revision'])


def percentages(instances,subject):
    evidence=[e for i in instances if (e:=count_evidence(i,subject)) is not None]
    derived=[]
    for n in evidence:
        for d in evidence:
            if (n['query_id']==d['query_id'] or n['scope']!=d['scope'] or n['revision']!=d['revision']
                    or n['plan']['base_dataset_id']!=d['plan']['base_dataset_id']
                    or not d['filters']<n['filters'] or n['count']>d['count']):continue
            with localcontext() as ctx:
                ctx.prec=70
                value=None if not d['count'] else format((Decimal(n['count'])*100/Decimal(d['count'])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),'f')
            item=dict(kind='percentage_of_population',numerator_query_id=n['query_id'],denominator_query_id=d['query_id'],
                numerator=str(n['count']),denominator=str(d['count']),percentage=value,
                status='undefined_zero_denominator' if value is None else 'calculated',
                formula='numerator / denominator * 100',rounding='ROUND_HALF_UP, 2 decimal places',
                base_dataset_id=n['plan']['base_dataset_id'],scope=n['scope'],metadata_revision=n['revision'],
                numerator_filters=n['plan']['filters'],denominator_filters=d['plan']['filters'])
            if item not in derived:derived.append(item)
    return derived
