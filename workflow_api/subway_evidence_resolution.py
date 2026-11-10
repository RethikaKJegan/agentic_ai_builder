"""Cited ontology evidence routes; no workflow, source or policy execution authority."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from .business_compiler import canonical

ARTIFACT = Path(__file__).resolve().parents[1] / 'ontology/subway/evidence-resolution-v1.json'
SCOPE = ('client-subway', 'subway-client')


def load(scope, snapshot):
    if tuple(scope) != SCOPE or snapshot.get('version_id') != 'bov_subway_dump_v4':
        return None
    document = json.loads(ARTIFACT.read_text())
    stamp = document.pop('sha256')
    if sha256(canonical(document).encode()).hexdigest() != stamp:
        raise ValueError('Subway evidence-resolution artifact integrity failure')
    if document['scope'] != dict(workspace_id=scope[0], subject_id=scope[1]):
        raise ValueError('Subway evidence-resolution scope mismatch')
    if document['definition_sha256'] != sha256(canonical(snapshot).encode()).hexdigest():
        return None
    ids = {item['id'] for kind in ('concepts', 'relationships', 'rules') for item in snapshot[kind]}
    sources = {s['source_id']: s for s in document['sources']}
    if not set(document['entries']) <= ids:
        raise ValueError('Unknown ontology resolution target')
    for source in sources.values():
        if sha256(source['text'].encode()).hexdigest() != source['sha256']:
            raise ValueError('Subway resolution citation integrity failure')
    for resolution in document['entries'].values():
        if not set(resolution['source_ids']) <= set(sources):
            raise ValueError('Unknown resolution citation')
        if any(e['concept_id'] not in ids for e in resolution['available_evidence']):
            raise ValueError('Unknown resolution evidence concept')
    return dict(sha256=stamp, entries=document['entries'], sources=sources)


def annotate(reference, bundle):
    """Enrich retrieved copies, preserving immutable saved definitions and their hash."""
    if not bundle or reference['id'] not in bundle['entries']:
        return reference
    resolution = deepcopy(bundle['entries'][reference['id']])
    reference['evidence_resolution'] = {k: v for k, v in resolution.items() if k != 'source_ids'}
    reference['evidence_resolution']['sha256'] = bundle['sha256']
    if reference.get('external_prerequisites'):
        reference['conditional_external_prerequisites'] = reference.pop('external_prerequisites')
        reference['unknowns'] = [u for u in reference.get('unknowns', [])
                                 if not u.startswith('This guard also depends on records absent from the supplied dumps:')]
    for sid in resolution['source_ids']:
        source = bundle['sources'][sid]
        reference['evidence'].append(dict(source_id=sid, quote=source['text'],
            source_sha256=source['sha256'], source_kind=source['kind'], title=source['title']))
    return reference
