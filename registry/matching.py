"""Conservative schema containment for capability matching."""


def schema_subset(source, target):
    """Prove source values satisfy target; unproven containment fails closed.

    Equal schemas and the unconstrained target are supported universally. For
    unequal schemas, support type/required/property constraints on open objects.
    Rich constraints must match exactly; no heuristic coercion is permitted.
    """
    if source == target or target == {}:
        return True
    supported = {'type', 'required', 'properties', 'description', 'title'}
    if set(source) - supported or set(target) - supported:
        return False
    if target.get('type') and source.get('type') != target['type']:
        return False
    if source.get('type') != 'object' or target.get('type') != 'object':
        return False
    if set(target.get('required', [])) - set(source.get('required', [])):
        return False
    for key, target_property in target.get('properties', {}).items():
        # Source objects are open, so a missing source property is unconstrained.
        if not schema_subset(source.get('properties', {}).get(key, {}), target_property):
            return False
    return True


def compatible(tool, input_schema, output_schema):
    return schema_subset(input_schema, tool['input_schema']) and schema_subset(tool['output_schema'], output_schema)
