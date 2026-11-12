"""Explicit example assumptions; never source observations or company authority."""
from hashlib import sha256
import json
from pathlib import Path
import re

from .business_compiler import canonical

ARTIFACT = Path(__file__).resolve().parents[1] / 'ontology/subway/demo-business-definitions-v1.json'
SCOPE = ('client-subway', 'subway-client')


def selected(scope, snapshot, objective):
    if tuple(scope) != SCOPE or snapshot.get('version_id') != 'bov_subway_dump_v4':
        return None
    # Explicit phrase selection avoids changing the meaning of existing requests.
    if not re.match(r'\s*use\s+subway\s+demo\s+definitions\s+v1\s*(?:[.!:;\n]|$)', objective, re.I):
        return None
    profile = json.loads(ARTIFACT.read_text())
    if (profile['scope'] != dict(workspace_id=SCOPE[0], subject_id=SCOPE[1])
            or profile['ontology_version'] != snapshot['version_id']
            or profile['authority'] != 'analytical_assumptions_only'
            or profile['source_basis'] != 'user_requested_generated_example'):
        raise ValueError('Invalid Subway example-definition scope or provenance')
    if profile['definition_sha256'] != sha256(canonical(snapshot).encode()).hexdigest():
        return None
    profile['sha256'] = sha256(canonical(profile).encode()).hexdigest()
    return profile
