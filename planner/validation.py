"""Planner-specific safety and cross-reference validation."""

from __future__ import annotations

import ast
import re
from typing import Any

from .contracts import validate_instance
from .errors import PlannerFailure
from runtime.expressions import validate_expression


def mark_automatic_inputs(workflow: dict[str, Any], context: dict[str, Any]) -> None:
    """Opt fresh proposals into prompt-only setup without rewriting their mappings."""
    if context.get('execution_input_mode') == 'automatic':
        workflow.setdefault('metadata', {})['execution_input_mode'] = 'automatic'


def validate_automatic_inputs(workflow: dict[str, Any]) -> None:
    if workflow['metadata'].get('execution_input_mode') != 'automatic':
        return
    fields = {field['name'] for field in workflow['inputs']}
    triggers = workflow['metadata'].get('trigger_templates', [])
    if not isinstance(triggers, list) or any(not isinstance(trigger, dict) or
            not isinstance(trigger.get('input_mapping', {}), dict) for trigger in triggers):
        raise PlannerFailure('AUTOMATIC_INPUT_SOURCE_REQUIRED',
            'Configure automatic trigger inputs with event mappings.', field='metadata.trigger_templates')
    if not triggers and fields:
        raise PlannerFailure('AUTOMATIC_INPUT_SOURCE_REQUIRED',
            'Save fixed settings in node configuration. Automatic manual workflows cannot ask for run inputs.',
            field='inputs')
    for trigger in triggers:
        if fields - set(trigger.get('input_mapping', {})):
            raise PlannerFailure('AUTOMATIC_INPUT_SOURCE_REQUIRED',
                'Map every automatic workflow input from its trigger; save fixed settings in node configuration.',
                field='metadata.trigger_templates.input_mapping')
    expressions = [condition['expression'] for condition in workflow['conditions']]
    for node in workflow['nodes']:
        expressions.extend(node.get('configuration', {}).get('input_mapping', {}).values())
    for expression in expressions:
        try:
            tree = validate_expression(expression)
        except Exception:
            continue  # The ordinary expression validator reports unsupported syntax.
        for part in ast.walk(tree):
            name = None
            if isinstance(part, (ast.Attribute, ast.Subscript)) and isinstance(part.value, ast.Name) and part.value.id in {'input', 'inputs'}:
                name = part.attr if isinstance(part, ast.Attribute) else part.slice.value if isinstance(part.slice, ast.Constant) else None
                if name not in fields:
                    raise PlannerFailure('AUTOMATIC_INPUT_SOURCE_REQUIRED',
                        'Automatic mappings cannot reference undeclared run inputs. Use saved settings or trigger data.',
                        field='nodes.configuration.input_mapping')

SECRET_PATTERNS = (
    re.compile(r"(?:api[_-]?key|secret|password|token)\s*[:=]\s*[^\s,}]+", re.I),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"),
)


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, str):
        result = value
        for pattern in SECRET_PATTERNS:
            result = pattern.sub("[REDACTED]", result)
        return result
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_sensitive(item) for key, item in value.items()}
    return value


def reject_sensitive(value: Any, path: str = "") -> None:
    if isinstance(value, str):
        if any(pattern.search(value) for pattern in SECRET_PATTERNS):
            raise PlannerFailure("SENSITIVE_DATA_DETECTED", "The planning data contains secret-like material.", field=path or None)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_sensitive(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            reject_sensitive(item, f"{path}.{key}" if path else key)


def preserve_unmapped_conditions(workflow: dict[str, Any]) -> None:
    """Keep unsupported boolean model conditions reviewable, never guess their meaning.

    Used only for fresh planner proposals, not saved/approved workflow validation.
    Missing graph paths and non-boolean outcome mappings still fail validation.
    """
    reject_sensitive(workflow)
    # Only repair otherwise canonical documents; malformed model data is rejected.
    try:
        validate_instance(workflow, "workflow")
    except ValueError as exc:
        raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "The proposed workflow does not match the contract.", field="workflow") from exc
    names = {field['name'] for field in workflow['inputs']}
    for index, condition in enumerate(workflow['conditions']):
        try:
            validate_expression(condition['expression'])
            continue
        except Exception:
            if set(condition['outcomes']) != {'yes', 'no'}:
                continue
        name = f'condition_review_{index + 1}'
        while name in names:
            name += '_result'
        names.add(name)
        workflow['inputs'].append(dict(name=name, type='boolean', required=True,
            description='Explicit reviewed condition result; provider event mapping must be configured before publication.'))
        condition['expression'] = f'inputs.{name}'
        requirements = workflow['metadata'].setdefault('unresolved_requirements', [])
        if not isinstance(requirements, list):
            raise PlannerFailure('WORKFLOW_VALIDATION_FAILED', 'Unresolved requirements must be a list.', field='metadata.unresolved_requirements')
        requirements.append(dict(requirement='condition_mapping', condition_id=condition['condition_id'],
                                 input_name=name, reason='condition_mapping_required'))


def validate_workflow(workflow: dict[str, Any], max_nodes: int = 100, max_depth: int = 50) -> dict[str, Any]:
    reject_sensitive(workflow)
    try:
        validate_instance(workflow, "workflow")
    except ValueError as exc:
        raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", str(exc), field="workflow") from exc
    validate_automatic_inputs(workflow)
    nodes = workflow["nodes"]
    if len(nodes) > max_nodes:
        raise PlannerFailure("WORKFLOW_GRAPH_TOO_LARGE", "The workflow exceeds the maximum node limit.", field="nodes", details={"max_nodes": max_nodes})
    node_ids = [node["node_id"] for node in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Workflow node identifiers must be unique.", field="nodes")
    node_set = set(node_ids)
    agent_ids = {agent["agent_id"] for agent in workflow["agents"]}
    hierarchy = {agent["agent_id"]: agent for agent in workflow["agents"]}
    for agent in workflow["agents"]:
        parent = agent.get("parent_agent_id")
        role = agent.get("hierarchy_role", "standalone")
        if parent and (parent not in agent_ids or parent == agent["agent_id"]):
            raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Agent hierarchy references an invalid parent.", field="agents.parent_agent_id")
        if role == "sub_agent" and not parent:
            raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "A sub-agent must identify its parent.", field="agents.hierarchy_role")
        if role == "master" and parent:
            raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "A master agent cannot have a parent.", field="agents.parent_agent_id")
    for agent in workflow["agents"]:
        seen_parents = set()
        current = agent
        while current.get("parent_agent_id"):
            parent_id = current["parent_agent_id"]
            if parent_id in seen_parents:
                raise PlannerFailure("WORKFLOW_INVALID_TRANSITION", "Agent hierarchy contains a cycle.", field="agents.parent_agent_id")
            seen_parents.add(parent_id)
            current = hierarchy[parent_id]
            if len(seen_parents) > 8:
                raise PlannerFailure("WORKFLOW_GRAPH_TOO_DEEP", "Agent hierarchy exceeds the maximum depth.", field="agents.parent_agent_id")
    edges = workflow["edges"]
    edge_ids = [edge["edge_id"] for edge in edges]
    if len(edge_ids) != len(set(edge_ids)):
        raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Workflow edge identifiers must be unique.", field="edges")
    for index, edge in enumerate(edges):
        if edge["source"] not in node_set:
            raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Edge source does not reference a workflow node.", field=f"edges[{index}].source")
        if edge["target"] not in node_set:
            raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Edge target does not reference a workflow node.", field=f"edges[{index}].target")
    conditions = {item["condition_id"]: item for item in workflow["conditions"]}
    approvals = {item["approval_gate_id"]: item for item in workflow["approval_gates"]}
    tools = {item["tool_id"] for item in workflow["tools"]}
    for index, node in enumerate(nodes):
        if node.get("kind") == "condition" and node.get("condition_id") not in conditions:
            raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Condition node references a missing condition.", field=f"nodes[{index}].condition_id")
        if node.get("kind") == "approval" and node.get("approval_gate_id") not in approvals:
            raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Approval node references a missing approval gate.", field=f"nodes[{index}].approval_gate_id")
        if node.get("kind") == "tool" and node.get("tool_id") not in tools:
            raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Tool node references a missing tool.", field=f"nodes[{index}].tool_id")
        if node.get("kind") == "agent" and node.get("agent_id") not in agent_ids:
            raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Agent node references a missing agent.", field=f"nodes[{index}].agent_id")
    from runtime.delegation import validate_delegation
    try:
        validate_delegation(workflow)
    except Exception as exc:
        raise PlannerFailure('WORKFLOW_VALIDATION_FAILED', 'Invalid dynamic delegation configuration.', field='metadata.dynamic_delegation') from exc
    condition_nodes = {condition_id: [] for condition_id in conditions}
    for node in nodes:
        if node.get("kind") == "condition":
            condition_nodes[node["condition_id"]].append(node)
    for condition_id, condition in conditions.items():
        try:
            validate_expression(condition['expression'])
        except Exception as exc:
            raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Condition expression is outside the supported deterministic language.", field="conditions.expression") from exc
        declared = set(condition["outcomes"])
        linked = [node for node in condition_nodes[condition_id]]
        if len(linked) != 1:
            raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Each declared condition must have exactly one graph node.", field="conditions")
        outgoing = [edge for edge in edges if edge["source"] == linked[0]["node_id"]]
        if ({edge.get("outcome") for edge in outgoing} != declared or
                any(sum(edge.get("outcome") == outcome for edge in outgoing) != 1 for outcome in declared)):
            raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Every declared condition outcome must have exactly one graph path.", field="edges.outcome")
        for edge in edges:
            source = next((node for node in nodes if node["node_id"] == edge["source"]), None)
            if source and source.get("condition_id") == condition["condition_id"] and edge.get("outcome") not in declared:
                raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Condition edge has an undeclared outcome.", field="edges.outcome")
    adjacency = {node_id: [] for node_id in node_set}
    incoming = {node_id: 0 for node_id in node_set}
    for edge in edges:
        adjacency[edge["source"]].append(edge["target"])
        incoming[edge["target"]] += 1
    if not any(node.get("kind") == "trigger" for node in nodes) or not any(node.get("kind") == "output" for node in nodes):
        raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "A workflow requires a trigger and an output node.", field="nodes")
    starts = [node_id for node_id, count in incoming.items() if count == 0]
    seen: set[str] = set()
    stack = [(node_id, 1, frozenset()) for node_id in starts]
    while stack:
        node_id, depth, path = stack.pop()
        if node_id in path:
            raise PlannerFailure("WORKFLOW_INVALID_TRANSITION", "Workflow graph contains a cycle.", field="edges")
        if depth > max_depth:
            raise PlannerFailure("WORKFLOW_GRAPH_TOO_DEEP", "The workflow exceeds the maximum graph depth.", field="edges", details={"max_depth": max_depth})
        seen.add(node_id)
        stack.extend((target, depth + 1, path | {node_id}) for target in adjacency[node_id])
    if seen != node_set:
        raise PlannerFailure("WORKFLOW_VALIDATION_FAILED", "Workflow contains unreachable nodes.", field="nodes")
    for gate in workflow["approval_gates"]:
        if workflow["execution_policy"].get("allow_external_writes") and not gate.get("approver_roles"):
            raise PlannerFailure("APPROVAL_REQUIRED", "External writes require an approval role.", field="approval_gates")
    return redact_sensitive(workflow)

