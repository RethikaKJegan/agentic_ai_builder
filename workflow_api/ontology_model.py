"""Ontology-owned data shapes; executable workflow contracts are unchanged."""
from jsonschema import Draft202012Validator
from .service import ApiFailure

ID = {'type':'string','pattern':r'^[A-Za-z0-9_:.\[\]-]{1,160}$'}
TEXT = {'type':'string','maxLength':2000}
RECORD = {
 'type':'object','additionalProperties':False,
 'required':['id','kind','layer','label','definition','dependencies','source_refs','evidence_class','properties'],
 'properties':{
  'id':ID,'kind':{'enum':['concept','attribute','mapping','constraint','relationship']},
  'layer':{'enum':['common','domain','organization']},'label':{'type':'string','minLength':1,'maxLength':160},
  'domain':{'enum':['Sales','Procurement','Finance','Customer Service',None]},'definition':TEXT,
  'dependencies':{'type':'array','maxItems':100,'uniqueItems':True,'items':ID},
  'source_refs':{'type':'array','maxItems':100,'uniqueItems':True,'items':ID},
  'evidence_class':{'enum':['observed_fact','model_inference','statistical_finding','unverified_hypothesis']},
  'properties':{'type':'object','additionalProperties':False,'properties':{
   'source':ID,'target':ID,'attribute':ID,'predicate':{'type':'string','maxLength':80},
   'datatype':{'enum':['string','integer','number','boolean','date','datetime','object','array','unknown']},
   'minimum':{'type':'number'},'maximum':{'type':'number'},
   'rule':{'enum':['required','allowed_values','range','approval_roles']},
   'approval_roles':{'type':'array','maxItems':20,'items':{'type':'string','minLength':1,'maxLength':80}},
   'acyclic':{'type':'boolean'},'required':{'type':'boolean'},
   'allowed_values':{'type':'array','maxItems':100,'items':{'type':['string','number','boolean','null']}},
   'risk':{'enum':['low','medium','high']},'method':{'type':'string','maxLength':160},
   'alternatives':{'type':'array','maxItems':10,'items':TEXT},
   'contradictions':{'type':'array','maxItems':20,'items':TEXT},
   'technical_relationship_id':ID,'field_pairs':{'type':'array','maxItems':20,'items':{
    'type':'object','additionalProperties':False,'required':['source_field_id','target_field_id'],
    'properties':{'source_field_id':ID,'target_field_id':ID}}}}}}}


def check(schema, value):
    if list(Draft202012Validator(schema).iter_errors(value)):
        raise ApiFailure('ONTOLOGY_INVALID','Supply a valid ontology record or action.',422)


def validate_record(value):
    check(RECORD,value)
    if value['id'] in {'.','..'}:raise ApiFailure('ONTOLOGY_INVALID','Choose a stable non-path ontology ID.',422)
    p=value['properties'];kind=value['kind']
    needed={'relationship':{'source','target','predicate'},'attribute':{'source','datatype'},
            'mapping':{'source','target'},'constraint':{'source'}}.get(kind,set())
    if not needed<=set(p) or (p.get('acyclic') and kind!='relationship'):
        raise ApiFailure('ONTOLOGY_INVALID','The record is missing typed endpoints or has an invalid relationship rule.',422)
    if value['layer']=='domain' and not value.get('domain'):
        raise ApiFailure('ONTOLOGY_INVALID','Domain records require a supported business domain.',422)


def dependencies(record):
    return set(record['dependencies']) | {record['properties'][k] for k in ('source','target','attribute') if k in record['properties']}


def graph_errors(records):
    by_id={r['id']:r for r in records};errors=[]
    redirects={r['id']:r['redirect'] for r in records if r.get('redirect')}
    for start in redirects:
        seen=set();at=start
        while at in redirects:
            if at in seen:
                errors.append(dict(id=start,rule='redirect_cycle'));break
            seen.add(at);at=redirects[at]
    for r in records:
        missing=dependencies(r)-set(by_id)
        if missing:errors.append(dict(id=r['id'],rule='missing_dependency',references=sorted(missing)))
        for k in ('source','target'):
            endpoint=by_id.get(r['properties'].get(k))
            if endpoint and endpoint['kind']!='concept':errors.append(dict(id=r['id'],rule='endpoint_must_be_concept'))
        if r['kind']=='mapping':
            a,b=(by_id.get(r['properties'].get(k)) for k in ('source','target'))
            if a and b and a['layer']=='common' and b['layer']=='organization':
                errors.append(dict(id=r['id'],rule='mapping_direction_more_specific_to_shared'))
    # Only explicitly acyclic predicates are checked. Ordinary cycles are legal.
    predicates={r['properties']['predicate'] for r in records if r['kind']=='relationship' and r['properties'].get('acyclic')}
    for predicate in predicates:
        adjacency={}
        for r in records:
            p=r['properties']
            if r['kind']=='relationship' and p['predicate']==predicate:adjacency.setdefault(p['source'],set()).add(p['target'])
        for start in adjacency:
            stack=list(adjacency[start]);seen=set()
            while stack:
                at=stack.pop()
                if at==start:
                    errors.append(dict(id=start,rule='acyclic_predicate',predicate=predicate));break
                if at not in seen:seen.add(at);stack.extend(adjacency.get(at,()))
    for r in records:
        p=r['properties']
        if r['kind']=='constraint':
            attribute=by_id.get(p.get('attribute'))
            if p.get('attribute') and (not attribute or attribute['kind']!='attribute' or attribute['properties']['source']!=p['source']):
                errors.append(dict(id=r['id'],rule='constraint_attribute_mismatch'))
            if 'minimum' in p and 'maximum' in p and p['minimum']>p['maximum']:errors.append(dict(id=r['id'],rule='invalid_range'))
            if p.get('rule')=='range' and (not attribute or attribute['properties']['datatype'] not in {'number','integer'}):errors.append(dict(id=r['id'],rule='range_requires_numeric_attribute'))
            if p.get('rule')=='allowed_values' and ('allowed_values' not in p or not attribute):errors.append(dict(id=r['id'],rule='allowed_values_requires_attribute'))
            if attribute and 'allowed_values' in p:
                datatype=attribute['properties']['datatype']
                accepted={'string':(str,),'integer':(int,),'number':(int,float),'boolean':(bool,)}.get(datatype)
                if accepted and any(type(v) not in accepted for v in p['allowed_values'] if v is not None):errors.append(dict(id=r['id'],rule='allowed_value_type_mismatch'))
            if p.get('rule')=='approval_roles' and not p.get('approval_roles'):errors.append(dict(id=r['id'],rule='approval_roles_required'))
    attributes={}
    for r in records:
        if r['kind']=='attribute':
            key=(r['properties']['source'],r['label'].casefold())
            if key in attributes and attributes[key]!=r['properties']['datatype']:errors.append(dict(id=r['id'],rule='conflicting_attribute_type'))
            attributes[key]=r['properties']['datatype']
    for r in records:
        if r['kind']=='mapping':
            p=r['properties'];a,b=p['source'],p['target']
            for (source,label),datatype in attributes.items():
                if source==a and (b,label) in attributes and attributes[(b,label)]!=datatype:
                    errors.append(dict(id=r['id'],rule='mapped_attribute_type_conflict'))
    return errors


def select_concepts(records, concept_ids, limit=200):
    """Pure bounded ontology closure; callers enforce access and publication status."""
    from copy import deepcopy
    if not isinstance(concept_ids,list) or not 1<=len(concept_ids)<=50 or any(not isinstance(x,str) for x in concept_ids):
        raise ApiFailure('ONTOLOGY_INVALID','Select one to fifty ontology concepts.',422)
    by_id={r['id']:r for r in records}
    if any(rid not in by_id or by_id[rid]['kind']!='concept' for rid in concept_ids):
        raise ApiFailure('ONTOLOGY_INVALID','Select existing ontology concepts.',422)
    selected=set(concept_ids)
    while True:
        required={dep for rid in selected for dep in dependencies(by_id[rid])}
        attached={r['id'] for r in records if (r['kind'] in {'attribute','constraint','mapping'} and r['properties'].get('source') in selected) or (r['kind']=='mapping' and r['properties'].get('target') in concept_ids)}
        relationships={r['id'] for r in records if r['kind']=='relationship' and {r['properties']['source'],r['properties']['target']}<=selected}
        more=required|attached|relationships
        if len(selected|more)>limit:raise ApiFailure('ONTOLOGY_SELECTION_LIMIT','Ontology subset exceeds its bound; narrow the concepts.',422)
        if more-set(by_id):raise ApiFailure('ONTOLOGY_STALE','Ontology dependency missing.',409)
        if more<=selected:break
        selected|=more
    return [deepcopy(by_id[rid]) for rid in sorted(selected)]
