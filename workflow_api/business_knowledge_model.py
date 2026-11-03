"""Typed Phase 1 knowledge. No source I/O, model calls or expression execution."""
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from jsonschema import Draft202012Validator
from .service import ApiFailure

SCHEMA = 'simpson-knowledge-v1'
CONVERSIONS = {'identity', 'parse_nonnegative_decimal', 'iso_date', 'iso_datetime'}
OPERATORS = {'is_present', 'is_nonnegative', 'equals', 'greater_or_equal', 'less_or_equal', 'in', 'date_on_or_after'}
ROOT_KEYS = {'schema_version', 'concept_details', 'relationship_details', 'source_mappings', 'identity_rules', 'state_models', 'temporal_models', 'structured_rules', 'dependencies', 'manifest'}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def fail(message, code='BUSINESS_KNOWLEDGE_INVALID', status=422):
    raise ApiFailure(code, message, status)


def obj(properties, required=None):
    return dict(type='object', properties=properties, required=list(properties) if required is None else required, additionalProperties=False)


def arr(items):
    return dict(type='array', items=items, maxItems=500)


S = dict(type='string', minLength=1, maxLength=3000)
ID = dict(type='string', pattern=r'^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$', maxLength=160)
NULLS = dict(type=['string', 'null'], maxLength=3000)
COUNT = dict(type=['integer', 'null'], minimum=0)
EVIDENCE = arr(obj(dict(source_id=S, quote=S)))
PROVENANCE = obj(dict(origin=dict(enum=['source_definition', 'application_behavior', 'configured_logic']), evidence=EVIDENCE))
ATTRIBUTE = obj(dict(name=S, business_meaning=S, business_datatype=dict(enum=['string','integer','decimal','boolean','date','datetime','reference','enumeration']), stored_datatypes=arr(S), unit=NULLS, allowed_values=arr(S), nullable=dict(type='boolean'), missing_behavior=dict(enum=['unknown']), reference_target=NULLS, min_count=COUNT, max_count=COUNT, date_precision=dict(enum=[None,'calendar_day','instant']), measurement_origin=dict(enum=['reported','recorded','observed','derived','not_applicable']), provenance=PROVENANCE))
BINDING = obj(dict(source_role=dict(enum=['service','quality']), collection=S, field_path=S))
ATOM = obj(dict(fact=S, operator=dict(enum=sorted(OPERATORS)), value={}, parameter=S), required=['fact','operator'])
RULE = obj(dict(id=ID, label=S, provenance=PROVENANCE, fact_types=dict(type='object', additionalProperties=dict(enum=['string','decimal','boolean','date','datetime'])), required_facts=arr(S), conditions=obj(dict(all=arr(ATOM))), parameters=dict(type='object',additionalProperties=True), applicability=obj(dict(oems=arr(S), models=arr(S))), outcomes=obj(dict(satisfied=S, unsatisfied=S, missing=S)), handler=dict(enum=['typed_conditions_v1']), executable_effects=dict(const=False)))
MODEL_SCHEMA = obj(dict(
 schema_version=dict(const=SCHEMA),
 concept_details=arr(obj(dict(concept_id=ID, entity_kind=dict(enum=['class']), aliases=arr(S), attributes=arr(ATTRIBUTE), provenance=PROVENANCE))),
 relationship_details=arr(obj(dict(relationship_id=ID, inverse_label=NULLS, min_count=COUNT, max_count=COUNT, traversable=dict(type='boolean'), binding_id=NULLS, provenance=PROVENANCE))),
 source_mappings=arr(obj(dict(id=ID, concept_id=ID, attribute=S, source_role=dict(enum=['service','quality']), collection=S, field_path=S, stored_datatypes=arr(S), business_datatype=dict(enum=['string','integer','decimal','boolean','date','datetime','reference','enumeration']), conversion=dict(enum=sorted(CONVERSIONS)), unit=NULLS, missing_behavior=dict(const='unknown'), provenance=PROVENANCE))),
 identity_rules=arr(obj(dict(id=ID, kind=dict(enum=['source_identity','direct_reference','candidate']), source=BINDING, target=dict(anyOf=[BINDING,dict(type='null')]), comparison=dict(enum=['source_scoped_native_id','native_type_and_value','exact_serial_candidate']), permits_physical_merge=dict(const=False), provenance=PROVENANCE))),
 state_models=arr(obj(dict(id=ID, concept_id=ID, semantic_kind=dict(enum=['case','activity','report','approval','replacement','change_applicability','incorporation']), mapping_id=NULLS, values=arr(obj(dict(raw=S, meaning=S))), transitions=arr(obj(dict(source=S,target=S,required_facts=arr(S)))), unknown_behavior=dict(const='unknown'), provenance=PROVENANCE))),
 temporal_models=arr(obj(dict(id=ID, concept_id=ID, attribute=S, meaning=S, mapping_id=NULLS, precision=dict(enum=['calendar_day','instant']), fallback_mapping_id=dict(type='null'), provenance=PROVENANCE))),
 structured_rules=arr(RULE),
 dependencies=arr(obj(dict(id=ID, subject_id=ID, concepts=arr(ID), relationships=arr(ID), mappings=arr(ID), rules=arr(ID), required_facts=arr(S), conditional=arr(obj(dict(when=S,concepts=arr(ID),mappings=arr(ID),required_facts=arr(S))))))),
 manifest=obj(dict(package_id=S,package_revision=dict(type='integer',minimum=1),configuration_revision=dict(type='integer',minimum=1),package_sha256=S,base_version_id=S,source_catalog_sha256=S,identity_basis_sha256=S,source_stamps=dict(type='object'),policy_refs=arr(obj(dict(policy_id=S,policy_key=S,revision=dict(type='integer',minimum=1),sha256=S))),policy_snapshots=arr(dict(type='object')),source_status=arr(dict(type='object')),protected=obj(dict(concepts=arr(ID),relationships=arr(ID),rules=arr(ID)))))
))


def cardinality(value):
    low, high = value['min_count'], value['max_count']
    if low is not None and high is not None and low > high:
        fail('Minimum cardinality exceeds maximum cardinality.')


def validate_knowledge(snapshot):
    k = snapshot.get('knowledge')
    if k is None:
        if snapshot.get('schema_version')=='simpson-business-snapshot-v2' or 'knowledge_sha256' in snapshot:
            fail('The versioned knowledge extension is missing.')
        return
    if not isinstance(k, dict) or snapshot.get('knowledge_sha256') != digest(k):
        fail('Saved knowledge hash does not match its contents.', 'BUSINESS_KNOWLEDGE_INTEGRITY', 409)
    try:
        Draft202012Validator(MODEL_SCHEMA).validate(k)
    except Exception:
        fail('Knowledge does not satisfy the versioned schema.')
    concepts = {c['id']: c for c in snapshot['concepts']}
    relationships = {r['id']: r for r in snapshot['relationships']}
    rules = {r['id']: r for r in snapshot['rules']}
    sources = {s['source_id']: s for s in snapshot['sources']}
    sections = [name for name in ROOT_KEYS if name not in {'schema_version','manifest'}]
    for section in sections:
        key = 'concept_id' if section == 'concept_details' else 'relationship_id' if section == 'relationship_details' else 'id'
        ids = [x[key] for x in k[section]]
        if len(set(ids)) != len(ids):
            fail('Knowledge section contains duplicate identifiers: ' + section)
    mappings = {m['id']: m for m in k['source_mappings']}
    identities = {i['id']: i for i in k['identity_rules']}
    structured = {r['id']: r for r in k['structured_rules']}
    def evidence(p):
        if not p['evidence']:
            fail('Knowledge provenance requires source evidence.')
        for e in p['evidence']:
            source = sources.get(e['source_id'])
            if not source or ' '.join(e['quote'].split()) not in ' '.join(source['text'].split()) or len(e['quote'].strip()) < 4:
                fail('Knowledge evidence quotation does not match its source.')
        if p['origin']=='application_behavior' and not any(sources[e['source_id']]['kind']=='application_code' for e in p['evidence']):
            fail('Application behavior requires an application-code source.')
    details = {d['concept_id']: d for d in k['concept_details']}
    for section in sections:
        for item in k[section]:
            if 'provenance' in item:evidence(item['provenance'])
            if 'concept_id' in item and item['concept_id'] not in concepts:fail('Knowledge references a missing concept.')
    for d in k['concept_details']:
        props={p['name']:p for p in concepts[d['concept_id']]['properties']}
        if len({a['name'] for a in d['attributes']}) != len(d['attributes']):fail('Duplicate attribute metadata.')
        for a in d['attributes']:
            evidence(a['provenance']);cardinality(a)
            if a['name'] not in props or props[a['name']]['datatype']!=a['business_datatype']:fail('Attribute metadata conflicts with its concept property.')
            if a['reference_target'] is not None and (a['business_datatype']!='reference' or a['reference_target'] not in concepts):fail('Reference target is missing or incompatible.')
            if a['allowed_values'] and a['business_datatype'] not in ('string','enumeration'):fail('Allowed values require a string or enumeration property.')
            if len(set(a['allowed_values']))!=len(a['allowed_values']):fail('Allowed values must be distinct.')
            if props[a['name']]['required'] and (a['min_count'] is None or a['min_count']<1):fail('Required attributes cannot have optional cardinality.')
    for m in mappings.values():
        props={p['name']:p for p in concepts[m['concept_id']]['properties']}
        if m['attribute'] not in props or props[m['attribute']]['datatype']!=m['business_datatype']:fail('Source mapping references an absent or incompatible property.')
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*',m['field_path']):fail('Unsafe field path.')
        if m['conversion']=='parse_nonnegative_decimal' and m['business_datatype'] not in ('decimal','integer'):fail('Numeric conversion requires numeric business type.')
        if m['conversion']=='iso_date' and m['business_datatype']!='date':fail('Date conversion requires a date property.')
        if m['conversion']=='iso_datetime' and m['business_datatype']!='datetime':fail('Datetime conversion requires a datetime property.')
    for i in identities.values():
        if i['kind']=='source_identity' and (i['target'] is not None or i['comparison']!='source_scoped_native_id'):fail('Invalid source identity definition.')
        if i['kind']=='direct_reference' and (i['target'] is None or i['comparison']!='native_type_and_value' or i['source']['source_role']!=i['target']['source_role']):fail('Direct references require a same-source typed reference contract.')
        if i['kind']=='candidate' and (i['target'] is None or i['comparison']!='exact_serial_candidate'):fail('Invalid candidate association definition.')
    for r in k['relationship_details']:
        cardinality(r)
        if r['relationship_id'] not in relationships:fail('Relationship details reference a missing relationship.')
        if r['traversable'] and (r['binding_id'] not in identities or identities[r['binding_id']]['kind']!='direct_reference'):fail('Traversable relationships require a direct-reference binding.')
        if not r['traversable'] and r['binding_id'] is not None:fail('Non-traversable relationships cannot advertise a direct binding.')
        if r['traversable']:
            edge=relationships[r['relationship_id']];binding=identities[r['binding_id']]
            for endpoint,side in [('source','source'),('target','target')]:
                locations={(m['source_role'],m['collection']) for m in mappings.values() if m['concept_id']==edge[endpoint]}
                actual=(binding[side]['source_role'],binding[side]['collection'])
                if locations and actual not in locations:fail('Relationship direction conflicts with its source binding.')
    for s in k['state_models']:
        if s['mapping_id'] is not None and s['mapping_id'] not in mappings:fail('State model references a missing mapping.')
        values={v['raw'] for v in s['values']}
        if len(values)!=len(s['values']):fail('Duplicate state values.')
        for t in s['transitions']:
            if t['source'] not in values or t['target'] not in values:fail('Transition references an unknown state.')
    for t in k['temporal_models']:
        if t['attribute'] not in {p['name'] for p in concepts[t['concept_id']]['properties']}:fail('Temporal model references a missing attribute.')
        if t['mapping_id'] is not None:
            m=mappings.get(t['mapping_id'])
            if not m or (m['concept_id'],m['attribute'])!=(t['concept_id'],t['attribute']) or m['business_datatype'] not in ('date','datetime'):fail('Temporal mapping conflicts with its business date.')
    for r in structured.values():
        facts=r['fact_types']
        if not set(r['required_facts'])<=facts.keys():fail('Rule requires undefined facts.')
        for c in r['conditions']['all']:
            if c['fact'] not in facts or ('value' in c and 'parameter' in c):fail('Rule condition references an invalid fact or operand.')
            if 'parameter' in c and c['parameter'] not in r['parameters']:fail('Rule references an undefined parameter.')
            if c['operator'] in {'is_present','is_nonnegative'} and set(c)!={'fact','operator'}:fail('Unary rule operator cannot have an operand.')
            if c['operator'] not in {'is_present','is_nonnegative'} and not ({'value','parameter'} & c.keys()):fail('Binary rule operator needs an operand.')
            if c['operator'] in {'is_nonnegative','greater_or_equal','less_or_equal'} and facts[c['fact']]!='decimal':fail('Numeric operator requires a numeric fact.')
            if c['operator']=='date_on_or_after' and facts[c['fact']]!='date':fail('Date operator requires a date fact.')
            operand=c.get('value',r['parameters'].get(c.get('parameter')))
            if operand is not None and c['operator'] not in {'is_present','is_nonnegative'}:
                values=operand if c['operator']=='in' else [operand]
                if not isinstance(values,list) or not values:fail('Membership conditions require nonempty lists.')
                kind=facts[c['fact']]
                conversion='parse_nonnegative_decimal' if kind=='decimal' else 'iso_date' if kind=='date' else 'iso_datetime' if kind=='datetime' else 'identity'
                if any(convert(v,conversion,kind)['state']!='value' for v in values):fail('Rule operand has an incompatible type.')
        for key,fact in [('oems','oem'),('models','model')]:
            if r['applicability'][key] and facts.get(fact)!='string':fail('Scoped rules must declare their applicability fact.')
    allrules=set(rules)|set(structured)
    for d in k['dependencies']:
        if d['subject_id'] not in set(concepts)|allrules:fail('Dependency subject is absent.')
        if not set(d['concepts'])<=concepts.keys() or not set(d['relationships'])<=relationships.keys() or not set(d['mappings'])<=mappings.keys() or not set(d['rules'])<=allrules:fail('Dependency references are incomplete.')
        for c in d['conditional']:
            if not set(c['concepts'])<=concepts.keys() or not set(c['mappings'])<=mappings.keys():fail('Conditional dependency references are incomplete.')
    manifest=k['manifest']
    for group,ids in manifest['protected'].items():
        if not set(ids)<={x['id'] for x in snapshot[group]}:fail('Protected definitions are missing.')
    policies={p['policy_id']:p for p in manifest['policy_snapshots']}
    if len(policies)!=len(manifest['policy_snapshots']) or len(policies)!=len(manifest['policy_refs']):fail('Policy manifest is incomplete.')
    from .business_policies import checked
    for p in manifest['policy_refs']:
        saved=policies.get(p['policy_id'])
        if not saved or any(saved.get(f)!=p[f] for f in ('policy_key','revision','sha256')):fail('Pinned policy revision differs from its manifest.')
        checked(saved)


def convert(value, conversion, datatype):
    """Pure allowlisted conversion; null and zero remain different."""
    if conversion not in CONVERSIONS:fail('Unsupported conversion.')
    if value is None:return dict(state='unknown',value=None)
    try:
        if conversion=='parse_nonnegative_decimal':
            if isinstance(value,bool) or not isinstance(value,(str,int,float,Decimal)) or not re.fullmatch(r'\d+(?:\.\d+)?',str(value)):raise ValueError()
            number=Decimal(str(value))
            if not number.is_finite() or number<0 or (datatype=='integer' and number!=number.to_integral_value()):raise ValueError()
            result=int(number) if datatype=='integer' else format(number,'f')
        elif conversion=='iso_date':
            if isinstance(value,datetime):result=value.date().isoformat()
            elif isinstance(value,date):result=value.isoformat()
            else:result=date.fromisoformat(value).isoformat()
        elif conversion=='iso_datetime':
            parsed=value if isinstance(value,datetime) else datetime.fromisoformat(value.replace('Z','+00:00'))
            if parsed.tzinfo is None:raise ValueError()
            result=parsed.isoformat()
        elif datatype=='boolean':
            if type(value) is not bool:raise ValueError()
            result=value
        elif datatype in ('string','enumeration'):
            if not isinstance(value,str):raise ValueError()
            result=value
        elif datatype=='reference':
            # A record identifier is not a resolved ontology individual.
            return dict(state='reference_unresolved',value=value)
        else:raise ValueError()
        return dict(state='value',value=result)
    except (ValueError,TypeError,InvalidOperation,OverflowError,AttributeError):
        return dict(state='conversion_issue',value=None)


def evaluate_rule(rule, facts, parameters=None):
    if not isinstance(facts,dict) or not set(facts)<=rule['fact_types'].keys():fail('Provide only declared rule facts.')
    params=deepcopy(rule['parameters'])
    if parameters:
        if not isinstance(parameters,dict) or not set(parameters)<=params.keys():fail('Unknown rule parameter.')
        params.update(parameters)
    checks=[];missing=[f for f in rule['required_facts'] if facts.get(f) is None]
    normalized={}
    for name,kind in rule['fact_types'].items():
        value=facts.get(name)
        conversion='parse_nonnegative_decimal' if kind=='decimal' else 'iso_date' if kind=='date' else 'iso_datetime' if kind=='datetime' else 'identity'
        cell=convert(value,conversion,kind);normalized[name]=cell
        if value is not None and cell['state']!='value':missing.append(name)
    for c in rule['conditions']['all']:
        cell=normalized[c['fact']];value=cell['value'];op=c['operator'];other=c.get('value',params.get(c.get('parameter')))
        result=None
        if cell['state']=='value':
            try:
                if op=='is_present':result=True
                elif op=='is_nonnegative':result=Decimal(str(value))>=0
                elif other is not None:
                    if op=='equals':result=type(value) is type(other) and value==other
                    elif op in ('greater_or_equal','less_or_equal'):
                        if isinstance(other,bool):raise ValueError()
                        a,b=Decimal(str(value)),Decimal(str(other))
                        if not b.is_finite():raise ValueError()
                        result=a>=b if op=='greater_or_equal' else a<=b
                    elif op=='in':result=isinstance(other,list) and value in other
                    elif op=='date_on_or_after':result=date.fromisoformat(value)>=date.fromisoformat(other)
            except (ValueError,TypeError,InvalidOperation):result=None
        checks.append(dict(fact=c['fact'],operator=op,result=result))
    applicable=True
    for key,fact in [('oems','oem'),('models','model')]:
        if rule['applicability'][key]:
            if facts.get(fact) is None:missing.append(fact)
            elif facts[fact] not in rule['applicability'][key]:applicable=False
    state='not_applicable' if not applicable else 'missing' if missing or any(c['result'] is None for c in checks) else 'satisfied' if all(c['result'] for c in checks) else 'unsatisfied'
    return dict(rule_id=rule['id'],outcome='not_applicable' if state=='not_applicable' else rule['outcomes'][state],state=state,missing_facts=sorted(set(missing)),checks=checks,provenance=deepcopy(rule['provenance']),parameters=params,official_policy_result=False,operational_effects=False)


def state_check(model, raw, target=None, facts=None):
    if raw is not None and not isinstance(raw,str) or target is not None and not isinstance(target,str) or facts is not None and not isinstance(facts,dict):fail('State inputs must use declared strings and an object of facts.')
    values={v['raw']:v['meaning'] for v in model['values']}
    if raw not in values:return dict(state='unknown',meaning=None,transition='undefined',activity_completion_inferred=False)
    result=dict(state='recognized',meaning=values[raw],transition='not_requested',activity_completion_inferred=False)
    if target is not None:
        t=next((t for t in model['transitions'] if t['source']==raw and t['target']==target),None)
        result['transition']='undefined' if t is None else 'requirements_missing' if any((facts or {}).get(f) is not True for f in t['required_facts']) else 'supported'
    return result


def associate(definition, left, right=None):
    """Compare supplied record observations; never create/merge records."""
    allowed={'connection_id','collection','native_type','native_value','serial','company','model','reference_type','reference_value'}
    for record in (left,right):
        if record is not None and (not isinstance(record,dict) or set(record)-allowed or not all(isinstance(record.get(k),str) and record[k] for k in ('connection_id','collection','native_type','native_value'))):fail('Source context and native identifier evidence are required.')
        if record is not None and any(record.get(k) is not None and not isinstance(record[k],str) for k in ('serial','company','model','reference_type','reference_value')):
            fail('Association observations must retain explicit scalar identifier types; no coercion is supported.')
    if left is None:fail('A left record is required.')
    def scoped(x):return tuple(x[k] for k in ('connection_id','collection','native_type','native_value'))
    result=dict(definition_id=definition['id'],kind=definition['kind'],association='insufficient_information',physical_engine_identity='unresolved',merge_permitted=False,conflicts=[],provenance=deepcopy(definition['provenance']))
    if right is None:return result
    if scoped(left)==scoped(right):result['association']='identical_source_record';return result
    if definition['kind']=='direct_reference':
        a,b=definition['source'],definition['target']
        matches=left['connection_id']==right['connection_id'] and left['collection']==a['collection'] and right['collection']==b['collection'] and left.get('reference_type')==right['native_type'] and left.get('reference_value')==right['native_value']
        result['association']='direct_reference' if matches else 'unresolved_reference';return result
    if definition['kind']=='candidate':
        if left['collection']!=definition['source']['collection'] or right['collection']!=definition['target']['collection']:fail('Records do not match the selected association definition.')
        result['conflicts']=[k for k in ('company','model') if left.get(k) is not None and right.get(k) is not None and left[k]!=right[k]]
        if result['conflicts']:result['association']='conflicting_candidate'
        elif left.get('serial') is not None and left['serial']==right.get('serial'):result['association']='scope_supported_candidate' if all(left.get(k) is not None and left.get(k)==right.get(k) for k in ('company','model')) else 'ambiguous_candidate'
    return result


def append_rdf(snapshot, ontology, shapes, iri, vocab):
    """Export supported semantics; operational definitions remain annotations."""
    from rdflib import Literal
    from rdflib.namespace import OWL, RDF, SH, SKOS
    k=snapshot['knowledge']
    for name in ('knowledgeDefinition','unit','measurementOrigin','officialPolicyResult'):
        ontology.add((vocab[name],RDF.type,OWL.AnnotationProperty))
    for d in k['concept_details']:
        node=iri('concept',d['concept_id'])
        for alias in d['aliases']:ontology.add((node,SKOS.altLabel,Literal(alias)))
        for a in d['attributes']:
            path=iri('attribute',d['concept_id'],a['name']);pshape=iri('property-shape',d['concept_id'],a['name'])
            if a['unit']:ontology.add((path,vocab.unit,Literal(a['unit'])))
            ontology.add((path,vocab.measurementOrigin,Literal(a['measurement_origin'])))
            if a['reference_target']:
                from rdflib.namespace import RDFS
                target=iri('concept',a['reference_target']);ontology.add((path,RDFS.range,target));shapes.add((pshape,SH['class'],target))
            for name in ('min_count','max_count'):
                if a[name] is not None:
                    predicate=SH.minCount if name=='min_count' else SH.maxCount
                    shapes.set((pshape,predicate,Literal(a[name])))
            if a['allowed_values']:
                head=iri('allowed-values',d['concept_id'],a['name'],0);shapes.add((pshape,SH['in'],head))
                for n,value in enumerate(a['allowed_values']):
                    item=iri('allowed-values',d['concept_id'],a['name'],n)
                    shapes.add((item,RDF.first,Literal(value)));shapes.add((item,RDF.rest,RDF.nil if n==len(a['allowed_values'])-1 else iri('allowed-values',d['concept_id'],a['name'],n+1)))
    for r in k['relationship_details']:
        shape=iri('relationship-shape',r['relationship_id'])
        if r['min_count'] is not None:shapes.set((shape,SH.minCount,Literal(r['min_count'])))
        if r['max_count'] is not None:shapes.set((shape,SH.maxCount,Literal(r['max_count'])))
    for section in ('source_mappings','identity_rules','state_models','temporal_models','structured_rules','dependencies'):
        for value in k[section]:
            node=iri('knowledge',value['id']);ontology.add((node,vocab.knowledgeDefinition,Literal(canonical(value))))
            if section=='structured_rules':ontology.add((node,vocab.executable,Literal(False)))
