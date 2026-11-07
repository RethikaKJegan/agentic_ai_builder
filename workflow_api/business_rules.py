"""Read-only candidate-rule catalogue and fixed local RDF competency queries."""
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from threading import Lock
from urllib.parse import quote

from .business_compiler import COMPILER_VERSION, VOCAB_IRI, canonical, check_snapshot, dependencies, compiler_version
from .business_ontology import identity
from .service import ApiFailure

QUERY_VERSION = 'simpson-competency-v1'
REFERENCE = Path(__file__).resolve().parents[1] / 'ontology/business-reference/competency-questions.json'
BASIS_LABELS = dict(policy_statement='Policy statement (unverified)', descriptive_implementation='Describes code behavior', proposed_logic='Proposed logic')
PREFIXES = '''PREFIX sb: <urn:simpson-business:vocabulary:>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX prov: <http://www.w3.org/ns/prov#>
'''
# Query strings are code-owned. Only integer pagination and RDF variable bindings
# vary. No caller text is parsed as SPARQL, a graph URL or an external IRI.
QUERIES = {
 'rule_inputs': dict(label='Which input definitions and attributes do candidate rules use?',focus_kind='rule',description='Lists directly declared input concepts and attributes. Required flags describe the draft schema, not whether company records contain values.',select='''SELECT DISTINCT ?rule ?rule_label ?input ?input_label ?attribute ?attribute_name ?datatype ?required WHERE {
 ?rule a sb:RuleCandidate; rdfs:label ?rule_label; sb:input ?input .
 ?input rdfs:label ?input_label .
 OPTIONAL { ?attribute rdfs:domain ?input; sb:required ?required; rdfs:label ?attribute_name . OPTIONAL { ?attribute rdfs:range ?datatype . } }
 FILTER(!BOUND(?focus) || ?rule = ?focus)
} ORDER BY ?rule ?input ?attribute'''),
 'rule_evidence': dict(label='What source evidence supports each candidate rule?',focus_kind='rule',description='Returns the saved source kind, hash and exact quotation; source presence is not policy approval.',select='''SELECT DISTINCT ?rule ?rule_label ?basis ?source ?source_label ?source_kind ?source_hash ?quote WHERE {
 ?rule a sb:RuleCandidate; rdfs:label ?rule_label; sb:basis ?basis; sb:evidence ?evidence .
 ?evidence prov:wasDerivedFrom ?source; sb:quote ?quote .
 ?source rdfs:label ?source_label; sb:sourceKind ?source_kind; sb:sourceHash ?source_hash .
 FILTER(!BOUND(?focus) || ?rule = ?focus)
} ORDER BY ?rule ?source ?quote'''),
 'policy_candidates': dict(label='Which candidates cite policy statements?',focus_kind='rule',description='Returns policy-statement candidates only. Results do not establish complete or approved warranty policy.',select='''SELECT DISTINCT ?rule ?rule_label ?outcome ?unknown WHERE {
 ?rule a sb:RuleCandidate; rdfs:label ?rule_label; sb:basis "policy_statement"; sb:outcome ?outcome .
 OPTIONAL { ?rule sb:unknown ?unknown . }
 FILTER(!BOUND(?focus) || ?rule = ?focus)
} ORDER BY ?rule ?unknown'''),
 'implementation_candidates': dict(label='Which candidates describe existing code behavior?',focus_kind='rule',description='Shows implementation descriptions and their conditions/outcomes, without treating existing code as approved policy.',select='''SELECT DISTINCT ?rule ?rule_label ?condition ?outcome WHERE {
 ?rule a sb:RuleCandidate; rdfs:label ?rule_label; sb:basis "descriptive_implementation"; sb:outcome ?outcome .
 OPTIONAL { ?rule sb:condition ?condition . }
 FILTER(!BOUND(?focus) || ?rule = ?focus)
} ORDER BY ?rule ?condition'''),
 'concept_relationships': dict(label='How are concept definitions connected?',focus_kind='concept',description='Lists declared relationship domain/range definitions, not links between actual engines, tickets or claims.',select='''SELECT DISTINCT ?relationship ?relationship_label ?source ?source_label ?predicate ?target ?target_label WHERE {
 ?relationship a owl:ObjectProperty; rdfs:label ?relationship_label; rdfs:domain ?source; rdfs:range ?target; sb:predicateText ?predicate .
 ?source rdfs:label ?source_label . ?target rdfs:label ?target_label .
 FILTER(!BOUND(?focus) || ?source = ?focus || ?target = ?focus)
} ORDER BY ?relationship ?source ?target'''),
 'unresolved_information': dict(label='What unresolved information is recorded?',focus_kind='definition',description='Lists recorded definition unknowns and, when unfiltered, module questions. No rows does not prove completeness.',select='''SELECT DISTINCT ?item ?item_label ?information WHERE {
 { ?item sb:unknown ?information; rdfs:label ?item_label . }
 UNION { ?item a owl:Ontology; sb:question ?information . BIND("Module question" AS ?item_label) }
 FILTER(!BOUND(?focus) || ?item = ?focus)
} ORDER BY ?item ?information'''),
}
QUERY_GUARD = Lock()


def failure(message='Select an available competency query, valid definition focus and bounded page.'):
    raise ApiFailure('BUSINESS_QUERY_INVALID', message, 422)


def question_reference():
    return json.loads(REFERENCE.read_text())


def catalogue(snapshot):
    """Pure projection; no fabricated facts or mutable policy interpretation."""
    if snapshot['kind'] == 'draft':
        check_snapshot(snapshot)
    concepts = {c['id']:c for c in snapshot['concepts']}
    sources = {s['source_id']:s for s in snapshot.get('sources', [])}
    rules = []
    for rule in sorted(snapshot['rules'], key=lambda r:(r['module_id'], r['label'].casefold(), r['id'])):
        item = deepcopy(rule)
        from .business_rule_execution import availability
        item['execution']=availability(rule)
        item['basis_label'] = BASIS_LABELS[rule['basis']]
        item['business_policy_verified'] = False
        item['input_definitions'] = [dict(id=cid,label=concepts[cid]['label'],module_id=concepts[cid]['module_id'],properties=deepcopy(concepts[cid]['properties']),data_availability='not_checked') for cid in rule['inputs']]
        item['evidence'] = [dict(**e,title=sources[e['source_id']]['title'],kind=sources[e['source_id']]['kind'],sha256=sources[e['source_id']]['sha256'],origin=deepcopy(sources[e['source_id']].get('origin',''))) for e in rule['evidence']]
        item['module_questions'] = deepcopy(snapshot.get('questions', {}).get(rule['module_id'], []))
        rules.append(item)
    return rules


def compilation_problem(snapshot, compilation):
    if snapshot['kind'] != 'draft':
        return 'Generate and compile a module draft for this version first.'
    if not compilation:
        return 'Compile and validate this saved version before running definition queries.'
    if (compilation.get('version_id') != snapshot['version_id'] or compilation.get('compiler_version') != compiler_version(snapshot)
        or compilation.get('input_sha256') != sha256(canonical(snapshot).encode()).hexdigest()):
        return 'The saved compilation does not match this definition version.'
    report = compilation.get('report', {})
    if (report.get('status') != 'passed' or report.get('definition_conforms') is not True
        or report.get('version_id') != snapshot['version_id'] or report.get('compiler_version') != compiler_version(snapshot)
        or any(report.get('checks',{}).get(key) != 'passed' for key in ('snapshot','rdf_syntax','shapes_meta_shacl','definition_shacl'))):
        return 'This version has no passing structural compilation.'
    artifacts = [a for a in compilation.get('artifacts', []) if a.get('name') == 'ontology.ttl']
    if len(artifacts) != 1 or not isinstance(artifacts[0].get('content'), str):
        return 'The saved ontology artifact is unavailable.'
    artifact = artifacts[0]
    if len(artifact['content'].encode()) > 12000000 or sha256(artifact['content'].encode()).hexdigest() != artifact.get('sha256'):
        return 'The saved ontology artifact failed its integrity check.'
    return None


@lru_cache(maxsize=64)
def prepared(query):
    from rdflib.plugins.sparql import prepareQuery
    return prepareQuery(query)


def execute(snapshot, compilation, body):
    """Pure local query of a previously compiled artifact; never compiles."""
    if (not isinstance(body,dict) or set(body) != {'query_id','focus_id','limit','offset'}
        or not isinstance(body['query_id'],str) or body['query_id'] not in QUERIES
        or (body['focus_id'] is not None and not isinstance(body['focus_id'],str))
        or type(body['limit']) is not int or not 1 <= body['limit'] <= 50
        or type(body['offset']) is not int or not 0 <= body['offset'] <= 20000):
        failure()
    definition = QUERIES[body['query_id']]
    by_kind = {kind:{i['id']:i for i in snapshot[kind+'s']} for kind in ('concept','relationship','rule')}
    allowed = by_kind.get(definition['focus_kind'], {key:item for items in by_kind.values() for key,item in items.items()})
    if body['focus_id'] is not None and body['focus_id'] not in allowed:
        failure('The selected focus does not belong to this version or question.')
    if snapshot['kind'] == 'draft':
        check_snapshot(snapshot)
    problem = compilation_problem(snapshot, compilation)
    if problem:
        raise ApiFailure('BUSINESS_QUERY_UNAVAILABLE',problem,409)
    Graph, Literal, _, URIRef, *_ = dependencies()
    artifact = next(a for a in compilation['artifacts'] if a['name'] == 'ontology.ttl')
    namespace = snapshot['workspace']['namespace']
    entities = {}
    for kind, items in by_kind.items():
        for cid,item in items.items():
            entities[namespace+kind+':'+quote(cid,safe='')] = dict(entity_id=cid,entity_kind=kind,label=item['label'])
    for source in snapshot.get('sources', []):
        entities[namespace+'source:'+quote(source['source_id'],safe='')] = dict(entity_id=source['source_id'],entity_kind='source',label=source['title'])
    bindings = {}
    if body['focus_id'] is not None:
        focused = next(iri for iri,value in entities.items() if value['entity_id']==body['focus_id'])
        bindings['focus'] = URIRef(focused)
    query = PREFIXES + definition['select'] + '\nLIMIT ' + str(body['limit']+1) + ' OFFSET ' + str(body['offset'])
    try:
        graph = Graph().parse(data=artifact['content'],format='turtle')
        def cell(term):
            if term is None:
                return None
            value = str(term)
            return dict(kind='literal' if isinstance(term,Literal) else 'iri',value=value,
                datatype=str(term.datatype) if isinstance(term,Literal) and term.datatype else None,
                **entities.get(value,{}))
        # Serialize RDFLib preparation/evaluation: parsing uses shared grammar
        # state. Only six fixed bounded SELECTs reach this block.
        with QUERY_GUARD:
            result = graph.query(prepared(query),initBindings=bindings)
            columns = [str(v) for v in result.vars]
            rows = [{key:cell(row[index]) for index,key in enumerate(columns)} for row in result]
        has_more = len(rows) > body['limit']
        rows = rows[:body['limit']]
    except Exception:
        raise ApiFailure('BUSINESS_QUERY_FAILED','The saved ontology query could not be completed. Refresh the catalogue before retrying.',503) from None
    return dict(version_id=snapshot['version_id'],revision=snapshot['revision'],query_id=body['query_id'],query_version=QUERY_VERSION,
        focus_id=body['focus_id'],columns=columns,rows=rows,offset=body['offset'],limit=body['limit'],has_more=has_more,
        next_offset=body['offset']+len(rows) if has_more else None, result_state='rows' if rows else 'no_matching_definitions',
        scope='definitions_only',business_policy_verified=False,company_records_queried=False,rules_executed=False,
        provenance=dict(compiler_version=compiler_version(snapshot),input_sha256=compilation['input_sha256'],ontology_sha256=artifact['sha256'],query_sha256=sha256((PREFIXES+definition['select']).encode()).hexdigest()))


class BusinessRules:
    def __init__(self, ontology, compiler):
        self.ontology=ontology
        self.compiler=compiler

    def view(self, auth, version_id):
        identity(auth)
        snapshot=self.ontology.version(auth,version_id)
        rules=catalogue(snapshot)
        compilation=self.compiler.get(auth,version_id)['compilation']
        problem=compilation_problem(snapshot,compilation)
        if snapshot.get('workspace',{}).get('ontology_id')=='subway':
            questions=[dict(id='subway_question_'+str(i),department=m['label'],question=q,status='requires_instance_mapping',prerequisites=['Matching deployed source version and data mappings','Current owned source access and authoritative business policy where needed']) for i,(m,q) in enumerate((m,q) for m in snapshot['modules'] for q in snapshot.get('questions',{}).get(m['id'],[]))]
            reference=dict(items=questions,source=dict(title='Subway saved ontology questions',section='Archive and code evidence gaps',sha256=sha256(canonical(questions).encode()).hexdigest()))
        else:
            reference=question_reference()
        return dict(version_id=version_id,revision=snapshot['revision'],kind=snapshot['kind'],query_version=QUERY_VERSION,
            rules=rules,counts={basis:sum(r['basis']==basis for r in rules) for basis in BASIS_LABELS},
            queries=[dict(query_id=qid,label=d['label'],description=d['description'],focus_kind=d['focus_kind'],available=problem is None,unavailable_reason=problem) for qid,d in QUERIES.items()],
            business_questions=reference['items'],question_source=reference['source'],scope='definitions_only',business_policy_verified=False)

    def run(self, auth, version_id, body):
        identity(auth)
        snapshot=self.ontology.version(auth,version_id)
        compilation=self.compiler.get(auth,version_id)['compilation']
        return execute(snapshot,compilation,body)
