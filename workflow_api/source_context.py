"""Bounded workspace evidence, never credentials, assignments or instructions."""
import ast
import json
from registry.safety import reject_secrets
from registry.contracts import RegistryError

MAX_SOURCES = 20
MAX_TEXT = 12000
MAX_CONTEXT = 48000
FIELDS = ('title', 'name', 'description', 'summary', 'content', 'text', 'url', 'spreadsheet_id', 'range', 'provider_id')


def knowledge_documents(store, workspace):
    with store.transaction(write=False) as db:
        rows = db.execute('SELECT source_id,document FROM knowledge_sources WHERE workspace=? ORDER BY updated_at DESC,source_id LIMIT ?',
                          (workspace, MAX_SOURCES)).fetchall()
    documents, remaining = [], MAX_CONTEXT
    for source_id, raw in rows:
        try:
            document = json.loads(raw)
            if not isinstance(document, dict) or document.get('status') in {'disabled', 'deleted', 'failed', 'pending', 'archived'}:
                continue
            reject_secrets(document)
            item = {'source_id': source_id}
            for key in FIELDS:
                value = document.get(key)
                if isinstance(value, str) and value.strip():
                    item[key] = value[:MAX_TEXT]
            item['content_available'] = any(item.get(key) for key in ('content', 'text', 'summary'))
            size = len(json.dumps(item))
            if size > remaining:
                break
            remaining -= size
            documents.append(item)
        except (ValueError, TypeError, RegistryError):
            continue
    return documents


def planning_context(store, auth, requested):
    context = dict(requested) if isinstance(requested, dict) else {}
    # Browser-provided workspace evidence is not authoritative.
    context['workspace_knowledge'] = []
    context['workspace_sources'] = []
    context['source_context_limits'] = {'max_sources': MAX_SOURCES, 'max_characters': MAX_CONTEXT}
    if 'workflow.view' not in auth.get('permissions', []):
        return context
    workspace = auth['subject']['workspace_id']
    context['workspace_knowledge'] = knowledge_documents(store, workspace)
    with store.transaction(write=False) as db:
        rows = db.execute("SELECT document FROM revisions WHERE workspace=? AND json_extract(document,'$.status')='published' ORDER BY workflow_id,version DESC LIMIT ?",
                          (workspace, MAX_SOURCES)).fetchall()
    sources, seen = [], set()
    for (raw,) in rows:
        try:
            document = json.loads(raw)
        except (TypeError, ValueError):
            continue
        if not isinstance(document, dict):
            continue
        metadata = document.get('metadata', {})
        if not isinstance(metadata, dict):
            continue
        read_targets, templates = metadata.get('sheet_read_targets'), metadata.get('trigger_templates')
        candidates = list(read_targets) if isinstance(read_targets, list) else []
        for template in templates if isinstance(templates, list) else []:
            if not isinstance(template, dict) or template.get('provider_id') != 'google_sheets':
                continue
            poll_input = template.get('poll_input', {})
            candidates.append(dict(provider_id='google_sheets', spreadsheet_id=template.get('resource_id'),
                                   range=poll_input.get('range') if isinstance(poll_input, dict) else None))
        catalogs = metadata.get('sheet_catalog', [])
        for catalog in catalogs if isinstance(catalogs, list) else []:
            if isinstance(catalog, dict) and isinstance(catalog.get('spreadsheet_id'), str):
                candidates.append({'spreadsheet_id': catalog['spreadsheet_id']})
        for node in document.get('nodes', []):
            configuration = node.get('configuration', {})
            literal = configuration.get('input', {})
            if isinstance(literal, dict) and literal.get('spreadsheet_id'):
                candidates.append(literal)
            mappings = configuration.get('input_mapping', {})
            constants = {}
            if isinstance(mappings, dict):
                for key in ('spreadsheet_id', 'range'):
                    try:
                        value = ast.literal_eval(mappings.get(key, ''))
                        if isinstance(value, str):
                            constants[key] = value
                    except (ValueError, SyntaxError, TypeError):
                        pass
            if constants.get('spreadsheet_id'):
                candidates.append(constants)
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            item = {key: candidate[key][:2048] for key in ('provider_id', 'spreadsheet_id', 'range')
                    if isinstance(candidate.get(key), str)}
            if not item.get('spreadsheet_id'):
                continue
            item.setdefault('provider_id', 'google_sheets')
            identity = json.dumps(item, sort_keys=True)
            try:
                reject_secrets(item)
            except RegistryError:
                continue
            if identity not in seen and len(sources) < MAX_SOURCES:
                sources.append(item)
                seen.add(identity)
    context['workspace_sources'] = sources
    return context
