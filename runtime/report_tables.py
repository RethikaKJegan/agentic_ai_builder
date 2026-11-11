"""Server-owned table context and no-match rendering before action approval."""
from copy import deepcopy
from jsonschema import Draft202012Validator

GUIDANCE=('Spreadsheet report tables must satisfy the supplied report_table_context contracts. '
 'For a complete zero-match query, provide an explicitly labelled report-status table stating '
 'No matching records. Do not invent status groups, counts per group or numeric averages. '
 'Preserve the original source, date filters and coverage in the report text.')


def context(plan,action,instances,contracts):
    schemas=[]
    for consumer in plan['actions']:
        contract=contracts.get(consumer['capability_id'],{})
        if contract.get('kind')!='tool':continue
        if any(b.get('action_id')==action['action_id'] and b.get('kind') in {'generated','output'}
               and b.get('path')==['tabs'] and b.get('target')==['tabs'] for b in consumer.get('bindings',[])):
            schema=contract.get('input_schema',{}).get('properties',{}).get('tabs')
            if schema and schema not in schemas:schemas.append(deepcopy(schema))
    if not schemas:return None
    queries=[instances[d] for d in action['depends_on'] if instances.get(d,{}).get('capability_id')=='tool.workflow_data_query']
    def empty(q):
        out=q.get('output',{});r=out.get('result',{});c=out.get('coverage',{})
        return (q.get('state')=='completed' and q.get('verified_receipt') is True
          and bool(out.get('query_id')) and r.get('matched_rows')==0 and r.get('rows')==[]
          and r.get('total_result_rows')==0 and r.get('limited') is False
          and c.get('complete_scan') is True and c.get('aggregate_complete') is True
          and c.get('has_more') is False and c.get('returned_rows')==0 and c.get('total_result_rows')==0)
    return dict(contracts=schemas,verified_empty=bool(queries) and all(empty(q) for q in queries),
                query_ids=[q['output']['query_id'] for q in queries if empty(q)])


def normalize(output,ctx):
    if not ctx or not ctx.get('verified_empty') or not ctx.get('contracts'):return
    tabs=output.get('tabs')
    if tabs==[]:
        tabs=[dict(title='Report status',headers=[],rows=[])]
        output['tabs']=tabs
    if not isinstance(tabs,list):return
    for tab in tabs:
        if isinstance(tab,dict) and tab.get('rows')==[]:
            tab['headers']=['Report status','Details']
            tab['rows']=[['No matching records','The verified query returned no matching records. No group metrics or averages are available.']]


def validate(output,ctx):
    if not ctx:return
    for schema in ctx.get('contracts',[]):
        errors=list(Draft202012Validator(schema).iter_errors(output.get('tabs')))
        if errors:
            from .service import RuntimeFailure
            error=RuntimeFailure('AGENT_OUTPUT_INVALID','Generated tables do not satisfy the downstream tool contract.',422)
            error.invalid_model_output=True;error.validation_field='tabs'
            error.validation_hint=('Return tabs matching report_table_context contracts: nonempty bounded headers/rows, unique headers, valid titles and scalar cells. For verified empty results use a report-status table, not invented groups or averages. Preserve evidence and scope.')
            raise error
