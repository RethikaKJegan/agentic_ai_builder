"""Offline, version-bound OWL/SHACL compilation of business drafts.

No RDF from the caller is parsed, imported, inferred or executed. All triples and
shapes are constructed from the existing bounded structured definition schema.
"""
from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
import json
import re
from urllib.parse import quote
from xml.etree import ElementTree as ET

from .business_extraction import OUTPUT_SCHEMA, validate_result
from .business_ontology import identity, MODULES
from .google_connections import now
from .service import ApiFailure

COMPILER_VERSION = 'simpson-owl-shacl-v1'
KNOWLEDGE_COMPILER_VERSION = 'simpson-owl-shacl-knowledge-v1'


def compiler_version(snapshot):
    return KNOWLEDGE_COMPILER_VERSION if snapshot.get('knowledge') else COMPILER_VERSION
VOCAB_IRI = 'urn:simpson-business:vocabulary:'


def invalid(message='The saved draft cannot be compiled. Inspect its definitions and source evidence.'):
    raise ApiFailure('BUSINESS_COMPILATION_INVALID', message, 422)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def check_snapshot(snapshot):
    """Recheck immutable input, including all retained modules, before mapping."""
    if snapshot.get('kind') != 'draft' or not snapshot.get('concepts'):
        raise ApiFailure('BUSINESS_DRAFT_REQUIRED', 'Generate a module draft before compiling this version.', 409)
    if len(canonical(snapshot)) > 12000000:
        invalid('The saved draft exceeds the compilation size limit.')
    namespace = snapshot.get('workspace', {}).get('namespace', '')
    if not re.fullmatch(r'urn:simpson-business:[a-f0-9]{24}:', namespace):
        invalid()
    sources = snapshot.get('sources', [])
    if len({s['source_id'] for s in sources}) != len(sources):
        invalid()
    for source in sources:
        if sha256(source['text'].encode()).hexdigest() != source['sha256']:
            invalid('A saved evidence document does not match its recorded hash.')
    groups = ('concepts', 'relationships', 'rules')
    definitions = {kind: snapshot[kind] for kind in groups}
    modules = {x['module_id'] for items in definitions.values() for x in items}
    if not modules <= {m[0] for m in MODULES}:
        invalid()
    for module in sorted(modules):
        result = {kind: [] for kind in groups}
        retained = {kind: [x for x in items if x['module_id'] != module] for kind, items in definitions.items()}
        for kind, items in definitions.items():
            fields = OUTPUT_SCHEMA['properties'][kind]['items']['properties']
            for item in items:
                if item['module_id'] != module:
                    continue
                if item.get('status') != 'draft' or (kind == 'rules' and item.get('executable') is not False):
                    invalid()
                result[kind].append({key: item[key] for key in fields})
        result['questions'] = snapshot.get('questions', {}).get(module, [])
        try:
            validate_result(result, module, sources, retained)
        except ApiFailure:
            invalid()
    from .business_knowledge_model import validate_knowledge
    validate_knowledge(snapshot)
    return namespace


def dependencies():
    # Optional at import time so an un-upgraded environment still starts safely.
    try:
        from rdflib import Graph, Literal, Namespace, URIRef
        from rdflib.namespace import OWL, PROV, RDF, RDFS, SH, XSD
        from pyshacl import validate
    except ImportError:
        raise ApiFailure('BUSINESS_COMPILER_UNAVAILABLE', 'Install the backend RDF and SHACL dependencies before compiling.', 503) from None
    return Graph, Literal, Namespace, URIRef, OWL, PROV, RDF, RDFS, SH, XSD, validate


def build_graphs(snapshot):
    namespace = check_snapshot(snapshot)
    Graph, Literal, Namespace, URIRef, OWL, PROV, RDF, RDFS, SH, XSD, _ = dependencies()
    vocab = Namespace(VOCAB_IRI)
    ontology, shapes, definitions = Graph(), Graph(), Graph()
    for graph in (ontology, shapes, definitions):
        for prefix, value in [('sb', vocab), ('owl', OWL), ('rdf', RDF), ('rdfs', RDFS), ('sh', SH), ('xsd', XSD), ('prov', PROV)]:
            graph.bind(prefix, value)
    def iri(kind, *parts):
        return URIRef(namespace + kind + ':' + ':'.join(quote(str(p), safe='') for p in parts))
    warnings = []
    def warn(code, focus, message):
        warnings.append(dict(code=code, focus=focus, message=message))
    root = iri('ontology')
    version = iri('version', snapshot['version_id'])
    ontology.add((root, RDF.type, OWL.Ontology))
    ontology.add((root, OWL.versionIRI, version))
    ontology.add((root, OWL.versionInfo, Literal(snapshot['version_id'])))
    ontology.add((root, vocab.compilerVersion, Literal(compiler_version(snapshot))))
    ontology.add((root, vocab.status, Literal('draft')))
    ontology.add((root, vocab.businessPolicyVerified, Literal(False)))
    # Metadata stays annotations rather than introducing formal business axioms.
    for name in ('module', 'layer', 'status', 'confidence', 'evidence', 'unknown', 'basis', 'executable', 'input', 'condition', 'outcome', 'sourceHash', 'sourceKind', 'quote', 'predicateText', 'question', 'compilerVersion', 'businessPolicyVerified', 'extractionMetadata', 'required'):
        ontology.add((vocab[name], RDF.type, OWL.AnnotationProperty))
    ontology.add((vocab.RuleCandidate, RDF.type, OWL.Class))
    ontology.add((vocab.Evidence, RDF.type, OWL.Class))
    if snapshot.get('extraction'):
        ontology.add((root, vocab.extractionMetadata, Literal(canonical(snapshot['extraction']))))
    used_sources = {e['source_id'] for kind in ('concepts', 'relationships', 'rules') for item in snapshot[kind] for e in item['evidence']}
    for source in snapshot['sources']:
        if source['source_id'] not in used_sources:
            continue
        node = iri('source', source['source_id'])
        ontology.add((node, RDF.type, PROV.Entity))
        ontology.add((node, RDFS.label, Literal(source['title'])))
        ontology.add((node, vocab.sourceHash, Literal(source['sha256'])))
        ontology.add((node, vocab.sourceKind, Literal(source['kind'])))
        ontology.add((node, PROV.value, Literal(canonical(source.get('origin', '')))))
    def annotate(node, item):
        for predicate, value in [(RDFS.label, item['label']), (RDFS.comment, item['definition']), (vocab.module, item['module_id']), (vocab.layer, item['layer']), (vocab.status, 'draft'), (vocab.confidence, item['confidence'])]:
            ontology.add((node, predicate, Literal(value)))
        for index, evidence in enumerate(item['evidence']):
            ev = iri('evidence', item['id'], index)
            source = iri('source', evidence['source_id'])
            ontology.add((node, vocab.evidence, ev))
            ontology.add((node, PROV.wasDerivedFrom, source))
            ontology.add((ev, RDF.type, vocab.Evidence))
            ontology.add((ev, PROV.wasDerivedFrom, source))
            ontology.add((ev, vocab.quote, Literal(evidence['quote'])))
        for unknown in item['unknowns']:
            ontology.add((node, vocab.unknown, Literal(unknown)))
            warn('UNRESOLVED_INFORMATION', item['id'], unknown)
    types = dict(string=XSD.string, integer=XSD.integer, decimal=XSD.decimal, boolean=XSD.boolean, date=XSD.date, datetime=XSD.dateTime, enumeration=XSD.string)
    for concept in snapshot['concepts']:
        node = iri('concept', concept['id'])
        ontology.add((node, RDF.type, OWL.Class))
        annotate(node, concept)
        if concept['parent_id']:
            ontology.add((node, RDFS.subClassOf, iri('concept', concept['parent_id'])))
        shape = iri('shape', concept['id'])
        shapes.add((shape, RDF.type, SH.NodeShape))
        shapes.add((shape, SH.targetClass, node))
        for prop in concept['properties']:
            path = iri('attribute', concept['id'], prop['name'])
            pshape = iri('property-shape', concept['id'], prop['name'])
            is_reference = prop['datatype'] == 'reference'
            ontology.add((path, RDF.type, OWL.ObjectProperty if is_reference else OWL.DatatypeProperty))
            ontology.add((path, RDFS.label, Literal(prop['name'])))
            ontology.add((path, RDFS.comment, Literal(prop['description'])))
            ontology.add((path, RDFS.domain, node))
            ontology.add((path, vocab.required, Literal(prop['required'])))
            ontology.add((path, PROV.wasDerivedFrom, node))
            shapes.add((shape, SH.property, pshape))
            shapes.add((pshape, RDF.type, SH.PropertyShape))
            shapes.add((pshape, SH.path, path))
            shapes.add((pshape, SH.name, Literal(prop['name'])))
            shapes.add((pshape, SH.description, Literal(prop['description'])))
            if prop['required']:
                shapes.add((pshape, SH.minCount, Literal(1)))
            if is_reference:
                shapes.add((pshape, SH.nodeKind, SH.IRI))
                warn('REFERENCE_TARGET_UNSPECIFIED', concept['id'], 'Reference attribute ' + prop['name'] + ' has no declared target class; only an IRI constraint is emitted.')
            else:
                ontology.add((path, RDFS.range, types[prop['datatype']]))
                shapes.add((pshape, SH.datatype, types[prop['datatype']]))
                if prop['datatype'] == 'enumeration':
                    warn('ENUMERATION_VALUES_UNSPECIFIED', concept['id'], 'Enumeration attribute ' + prop['name'] + ' is a string; allowed values were not supplied.')
    for edge in snapshot['relationships']:
        node = iri('relationship', edge['id'])
        ontology.add((node, RDF.type, OWL.ObjectProperty))
        annotate(node, edge)
        ontology.add((node, RDFS.domain, iri('concept', edge['source'])))
        ontology.add((node, RDFS.range, iri('concept', edge['target'])))
        ontology.add((node, vocab.predicateText, Literal(edge['predicate'])))
        pshape = iri('relationship-shape', edge['id'])
        shapes.add((iri('shape', edge['source']), SH.property, pshape))
        shapes.add((pshape, RDF.type, SH.PropertyShape))
        shapes.add((pshape, SH.path, node))
        shapes.add((pshape, SH.nodeKind, SH.IRI))
        shapes.add((pshape, SH['class'], iri('concept', edge['target'])))
    for rule in snapshot['rules']:
        node = iri('rule', rule['id'])
        ontology.add((node, RDF.type, vocab.RuleCandidate))
        annotate(node, rule)
        ontology.add((node, vocab.executable, Literal(False)))
        ontology.add((node, vocab.basis, Literal(rule['basis'])))
        ontology.add((node, vocab.outcome, Literal(rule['outcome'])))
        for condition in rule['conditions']:
            ontology.add((node, vocab.condition, Literal(condition)))
        for cid in rule['inputs']:
            ontology.add((node, vocab.input, iri('concept', cid)))
    for module, questions in sorted(snapshot.get('questions', {}).items()):
        for question in questions:
            ontology.add((root, vocab.question, Literal(module + ': ' + question)))
            warn('UNRESOLVED_QUESTION', module, question)
    # Separate definition shapes validate the compiled TBox and annotations, not
    # invented company instances or example records.
    def constraint(shape, name, path, **kwargs):
        prop = iri('definition-property', name)
        definitions.add((shape, SH.property, prop))
        definitions.add((prop, SH.path, path))
        for key, value in kwargs.items():
            definitions.add((prop, SH[key], Literal(value) if isinstance(value, (int, bool)) else value))
    class_shape = iri('definition-shape', 'class')
    definitions.add((class_shape, RDF.type, SH.NodeShape))
    for concept in snapshot['concepts']:
        definitions.add((class_shape, SH.targetNode, iri('concept', concept['id'])))
    constraint(class_shape, 'class-type', RDF.type, hasValue=OWL.Class)
    constraint(class_shape, 'class-label', RDFS.label, minCount=1, datatype=XSD.string)
    constraint(class_shape, 'class-evidence', vocab.evidence, minCount=1, **{'class': vocab.Evidence})
    constraint(class_shape, 'class-parent', RDFS.subClassOf, **{'class': OWL.Class})
    for name, target in [('object', OWL.ObjectProperty), ('datatype', OWL.DatatypeProperty)]:
        shape = iri('definition-shape', name)
        definitions.add((shape, RDF.type, SH.NodeShape))
        definitions.add((shape, SH.targetClass, target))
        constraint(shape, name + '-domain', RDFS.domain, minCount=1, maxCount=1, **{'class': OWL.Class})
        # Reference attributes deliberately lack a range until the target is known.
        constraint(shape, name + '-range', RDFS.range, nodeKind=SH.IRI, **({'minCount': 1} if name == 'datatype' else {}))
    rule_shape = iri('definition-shape', 'rule')
    definitions.add((rule_shape, RDF.type, SH.NodeShape))
    definitions.add((rule_shape, SH.targetClass, vocab.RuleCandidate))
    constraint(rule_shape, 'rule-executable', vocab.executable, minCount=1, maxCount=1, hasValue=Literal(False), datatype=XSD.boolean)
    constraint(rule_shape, 'rule-input', vocab.input, **{'class': OWL.Class})
    constraint(rule_shape, 'rule-evidence', vocab.evidence, minCount=1, **{'class': vocab.Evidence})
    evidence_shape = iri('definition-shape', 'evidence')
    definitions.add((evidence_shape, RDF.type, SH.NodeShape))
    definitions.add((evidence_shape, SH.targetClass, vocab.Evidence))
    constraint(evidence_shape, 'evidence-quote', vocab.quote, minCount=1, datatype=XSD.string)
    constraint(evidence_shape, 'evidence-source', PROV.wasDerivedFrom, minCount=1, **{'class': PROV.Entity})
    if snapshot.get('knowledge'):
        from .business_knowledge_model import append_rdf
        append_rdf(snapshot,ontology,shapes,iri,vocab)
    return ontology, shapes, definitions, warnings


def turtle(graph):
    # N-Triples is a Turtle subset. Canonical blank-node labels make reports
    # reproducible; schema graphs themselves use only stable named nodes.
    from rdflib.compare import to_canonical_graph
    return ''.join(' '.join(term.n3() for term in triple) + ' .\n' for triple in sorted(to_canonical_graph(graph), key=lambda t: tuple(x.n3() for x in t)))


def rdfxml(graph):
    """Stable RDF/XML bytes using only our named subjects and fixed predicates."""
    from rdflib import Literal
    from rdflib.namespace import RDF, split_uri
    ET.register_namespace('rdf', str(RDF))
    root = ET.Element(ET.QName(str(RDF), 'RDF'))
    subjects = defaultdict(list)
    for subject, predicate, value in graph:
        subjects[str(subject)].append((predicate, value))
    for subject, pairs in sorted(subjects.items()):
        element = ET.SubElement(root, ET.QName(str(RDF), 'Description'), {ET.QName(str(RDF), 'about'): subject})
        for predicate, value in sorted(pairs, key=lambda p: (str(p[0]), p[1].n3())):
            ns, name = split_uri(predicate)
            prop = ET.SubElement(element, ET.QName(ns, name))
            if isinstance(value, Literal):
                if value.datatype:
                    prop.set(ET.QName(str(RDF), 'datatype'), str(value.datatype))
                if value.language:
                    prop.set('{http://www.w3.org/XML/1998/namespace}lang', value.language)
                prop.text = str(value)
            else:
                prop.set(ET.QName(str(RDF), 'resource'), str(value))
    return ET.tostring(root, encoding='utf-8', xml_declaration=True).decode()


def compile_snapshot(snapshot):
    try:
        ontology, shapes, definitions, warnings = build_graphs(snapshot)
        Graph, _, _, _, _, _, RDF, _, SH, _, validate = dependencies()
        options = dict(inference='none', advanced=False, js=False, do_owl_imports=False, meta_shacl=True)
        # This call meta-validates the instance shapes. Its empty data result is
        # deliberately NOT reported as instance conformance.
        validate(Graph(), shacl_graph=shapes, **options)
        conforms, results, _ = validate(ontology, shacl_graph=definitions, **options)
        if not isinstance(results, Graph):
            invalid('Generated shapes could not be validated.')
        issues = []
        for node in results.subjects(RDF.type, SH.ValidationResult):
            issues.append(dict(focus=str(results.value(node, SH.focusNode) or ''), path=str(results.value(node, SH.resultPath) or ''), message=str(results.value(node, SH.resultMessage) or 'Definition constraint failed.')))
        report = dict(status='passed' if conforms else 'failed', compiler_version=compiler_version(snapshot),
            version_id=snapshot['version_id'], revision=snapshot['revision'],
            checks=dict(snapshot='passed', rdf_syntax='passed', shapes_meta_shacl='passed', definition_shacl='passed' if conforms else 'failed'),
            definition_conforms=bool(conforms), instance_validation='not_run', owl_reasoning='not_run', business_policy_verified=False,
            counts=dict(concepts=len(snapshot['concepts']), relationships=len(snapshot['relationships']), rules=len(snapshot['rules']), ontology_triples=len(ontology), instance_shape_triples=len(shapes)),
            issues=sorted(issues, key=canonical), warnings=sorted(warnings, key=canonical))
        contents = [('ontology.ttl', 'text/turtle', turtle(ontology)), ('ontology.rdf', 'application/rdf+xml', rdfxml(ontology)),
            ('instance-shapes.ttl', 'text/turtle', turtle(shapes)), ('definition-shapes.ttl', 'text/turtle', turtle(definitions)),
            ('validation-report.ttl', 'text/turtle', turtle(results)), ('validation-report.json', 'application/json', json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + '\n')]
        # Parse only our generated local strings, with explicit formats. No URL,
        # file, JSON-LD context, owl:imports or external XML entity is accepted.
        for name, _, content in contents:
            if name.endswith(('.ttl', '.rdf')):
                Graph().parse(data=content, format='xml' if name.endswith('.rdf') else 'turtle')
        artifacts = [dict(name=name, media_type=media, content=content, sha256=sha256(content.encode()).hexdigest()) for name, media, content in contents]
        if sum(len(a['content'].encode()) for a in artifacts) > 32000000:
            invalid('Compiled artifacts exceed the export limit.')
        return report, artifacts
    except ApiFailure:
        raise
    except Exception:
        invalid()


class BusinessCompiler:
    def __init__(self, ontology):
        self.ontology = ontology
        self.store = ontology.store
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS business_ontology_compilations (workspace TEXT NOT NULL, owner TEXT NOT NULL, version_id TEXT NOT NULL, compiler_version TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,version_id,compiler_version))')

    def get(self, auth, version_id):
        scope = identity(auth)
        selected_compiler=compiler_version(self.ontology.version(auth, version_id))
        with self.store.transaction(write=False) as db:
            row = db.execute('SELECT document FROM business_ontology_compilations WHERE workspace=? AND owner=? AND version_id=? AND compiler_version=?', (*scope, version_id, selected_compiler)).fetchone()
        return dict(compilation=json.loads(row[0]) if row else None)

    def compile(self, auth, version_id, body):
        scope = identity(auth, True)
        if not isinstance(body, dict) or body:
            raise ApiFailure('BUSINESS_COMPILATION_INVALID', 'Compile a saved version with an empty request body.', 422)
        snapshot = self.ontology.version(auth, version_id)
        existing = self.get(auth, version_id)
        if existing['compilation']:
            return existing
        digest = sha256(canonical(snapshot).encode()).hexdigest()
        report, artifacts = compile_snapshot(deepcopy(snapshot))
        selected_compiler=compiler_version(snapshot)
        document = dict(version_id=version_id, compiler_version=selected_compiler, input_sha256=digest, compiled_at=now(), report=report, artifacts=artifacts)
        with self.store.transaction() as db:
            # Recheck snapshot identity before committing, without depending on
            # a newer workspace revision or mutable company connection state.
            row = db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?', (*scope, version_id)).fetchone()
            if not row or sha256(canonical(json.loads(row[0])).encode()).hexdigest() != digest:
                raise ApiFailure('BUSINESS_VERSION_CHANGED', 'The saved version changed during compilation.', 409)
            identity(auth, True)
            inserted = db.execute('INSERT INTO business_ontology_compilations VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING RETURNING version_id', (*scope, version_id, selected_compiler, json.dumps(document))).fetchone()
            if inserted:
                event_id = 'boe_compile_' + sha256((version_id + selected_compiler).encode()).hexdigest()[:32]
                db.execute('INSERT INTO business_ontology_events VALUES (?,?,?,?)', (*scope, event_id, json.dumps(dict(action='compile_version', at=document['compiled_at'], version_id=version_id, compiler_version=selected_compiler, input_sha256=digest, status=report['status']))))
        return self.get(auth, version_id)
