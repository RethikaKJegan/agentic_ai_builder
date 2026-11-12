"""Preserve interpreted alternatives through bounded existing query/read actions."""
from copy import deepcopy


def validate_branches(branches,catalog,selected):
    from .subway_queries import fail,canonical
    from .query_predicates import validate_conjunction
    if not branches:return
    if len(branches)<2 or len({b['base_dataset_id'] for b in branches})!=1:
        fail('Alternative categories require two to four branches over one selected base source.','SUBWAY_SELECTION_INVALID')
    if len({canonical(b) for b in branches})!=len(branches):
        fail('Alternative categories must be distinct.','SUBWAY_SELECTION_INVALID')
    for branch in branches:
        if branch['base_dataset_id'] not in selected or not branch['filters']:
            fail('Alternative category is outside the selected source scope.','SUBWAY_SELECTION_INVALID')
        if any(p['field_id'] not in catalog['fields'] or catalog['fields'][p['field_id']]['dataset_id'] not in selected for p in branch['filters']):
            fail('Alternative predicates require exact selected field identities.','SUBWAY_SELECTION_INVALID')
        validate_conjunction(branch['filters'],catalog['fields'])


GUIDANCE = (' When interpretation.filter_branches is nonempty, create exactly one unconditional '
    'subway.plan_query and one unconditional tool.subway_query template, followed by content.prepare. '
    'The server expands this pair for every pinned category and passes all results to the report. '
    'Do not create other query pairs or encode alternatives in the template instructions. '
    'Select common projection, measures, joins and ordering. Each expanded query receives its exact '
    'base_dataset_id and complete filters in context.subway_filter_branch. Do not omit or add predicates. '
    'Reports must label separate category counts; never infer the absence of an unqueried category '
    'or sum possibly overlapping categories into a distinct population count.')


def expand(actions,completion,branches):
    """Expand only a generated template before review; never edit a saved plan."""
    from .action_bindings import deny
    if not branches:return actions,completion,{}
    planners=[a for a in actions if a.get('capability_id')=='subway.plan_query']
    readers=[a for a in actions if a.get('capability_id')=='tool.subway_query']
    if len(planners)!=1 or len(readers)!=1:
        deny('Pinned alternatives require one query/read template for server expansion.','ACTION_BINDING_INVALID')
    planner,reader=planners[0],readers[0];pid=planner['action_id'];rid=reader['action_id']
    if any(a.get('optional') or a.get('when') for a in (planner,reader)) or reader['depends_on']!=[pid]:
        deny('Alternative query templates must be unconditional and directly linked.','ACTION_BINDING_INVALID')
    query_bindings=[b for b in reader['bindings'] if b.get('target')==['query']]
    if len(query_bindings)!=1 or query_bindings[0].get('kind')!='output' or query_bindings[0].get('action_id')!=pid or query_bindings[0].get('path')!=['query']:
        deny('Alternative read must consume its exact query template.','ACTION_BINDING_INVALID')
    reports=[a for a in actions if a.get('capability_id')=='content.prepare' and rid in a['depends_on']]
    if not reports:deny('Alternative results must feed reporting directly.','ACTION_CONTENT_UNVERIFIED')
    result=deepcopy(actions);completion=deepcopy(completion);pins={};ids={a['action_id'] for a in actions}
    for index,branch in enumerate(branches):
        new_pid=pid if index==0 else pid+'_category_'+str(index+1)
        new_rid=rid if index==0 else rid+'_category_'+str(index+1)
        if index:
            if new_pid in ids or new_rid in ids:deny('Alternative action identity collision.','ACTION_BINDING_INVALID')
            ids.update((new_pid,new_rid))
            p=deepcopy(planner);r=deepcopy(reader);p['action_id']=new_pid;r['action_id']=new_rid
            r['depends_on']=[new_pid]
            r['evidence_references']=[new_pid if ref==pid else ref for ref in r['evidence_references']]
            for binding in r['bindings']:
                if binding.get('action_id')==pid:binding['action_id']=new_pid
            result.extend((p,r))
            for report in result:
                if report['action_id'] in {a['action_id'] for a in reports}:
                    report['depends_on'].append(new_rid);report['evidence_references'].append(new_rid)
            if rid in completion:completion.append(new_rid)
        pins[new_pid]=deepcopy(branch);pins[new_rid]=deepcopy(branch)
        for action in result:
            if action['action_id']==new_pid:
                action['instructions']+=' Implement only context.subway_filter_branch: preserve its exact base and complete filters. This is category '+str(index+1)+' of '+str(len(branches))+'.'
    if len(result)>16:deny('Alternative categories exceed the workflow action budget.','ACTION_BINDING_INVALID')
    for report in result:
        if report['action_id'] in {a['action_id'] for a in reports}:
            report['instructions']+=' Report every pinned filter category using its own complete receipt and matched count, including zero counts. Do not sum overlapping categories into a distinct total.'
    return result,completion,pins


def check(query,branch):
    from collections import Counter
    from .subway_queries import fail,key
    def predicates(items):return Counter((p['field_id'],p['op'],key(p['value'])) for p in items)
    if query.get('base_dataset_id')!=branch['base_dataset_id'] or predicates(query.get('filters',[]))!=predicates(branch['filters']):
        fail('Preserve the exact pinned category base and complete filter predicates.','SUBWAY_QUERY_INVALID')
