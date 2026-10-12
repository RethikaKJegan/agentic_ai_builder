"""Application-owned routing evidence, distinct from autonomous agent messages."""
import ast
from uuid import uuid4
from .expressions import validate_expression
from .trace import snapshot


def output_sources(expression, available):
    """Find referenced output nodes; dynamic roots are conservatively flagged."""
    tree = validate_expression(expression)
    sources, dynamic = set(), False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(node.value, ast.Name) and node.value.id in {'outputs', 'nodes'}:
            key = node.attr if isinstance(node, ast.Attribute) else node.slice.value if isinstance(node.slice, ast.Constant) else None
            if isinstance(key, str):
                sources.add(key)
            else:
                dynamic = True
        if isinstance(node, ast.Name) and node.id in {'outputs', 'nodes'}:
            parents = [parent for parent in ast.walk(tree) if isinstance(parent, (ast.Attribute, ast.Subscript)) and parent.value is node]
            if not parents:
                dynamic = True
    return sources & set(available), dynamic


def record_handoffs(runtime, db, run, workflow, node, params, invocation_id):
    config = node.get('configuration', {})
    fields = {}
    dynamic = False
    # Literal input wins over input_mapping in the execution engine.
    for field, expression in (config.get('input_mapping', {}) if 'input' not in config else {}).items():
        sources, uncertain = output_sources(expression, run['outputs'])
        dynamic = dynamic or uncertain
        for source in sources:
            fields.setdefault(source, {})[field] = expression
    incoming = [edge for edge in workflow['edges'] if edge['target'] == node['node_id'] and run['edge_states'].get(edge['edge_id']) == 'selected']
    sources = {edge['source'] for edge in incoming} | set(fields)
    by_id = {item['node_id']: item for item in workflow['nodes']}
    for source in sorted(sources):
        matches = [edge for edge in incoming if edge['source'] == source]
        mappings = fields.get(source, {})
        for edge in matches or [None]:
            details = {
                'handoff_id': str(uuid4()), 'node_id': node['node_id'],
                'source_node_id': source, 'target_node_id': node['node_id'],
                'source_agent_id': by_id[source].get('agent_id'), 'target_agent_id': node.get('agent_id'),
                'source_invocation_id': run.get('node_invocations', {}).get(source),
                'target_invocation_id': invocation_id,
                'edge_id': edge['edge_id'] if edge else None,
                'transfer_kind': 'mapped_data' if mappings else 'execution_transition',
                'stage': 'inputs_prepared',
                'input_mapping': snapshot(mappings),
                'mapped_fields': snapshot({key: params[key] for key in mappings}),
                'receiver_input': snapshot(params),
                'source_output': snapshot(run['outputs'].get(source)),
                'dynamic_output_reference': dynamic,
            }
            runtime.event(db, run, 'node.handoff', details)
