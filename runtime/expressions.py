"""Small deterministic condition language; never eval or execute model code."""
import ast
import operator
from .service import RuntimeFailure

COMPARE = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
           ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
           ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b}


def validate_expression(expression):
    """Check the condition syntax without resolving workflow-specific fields."""
    try:
        tree = ast.parse(expression, mode='eval')
        supported = (ast.Expression, ast.Constant, ast.Name, ast.Attribute, ast.Subscript,
                     ast.List, ast.Tuple, ast.UnaryOp, ast.Not, ast.BoolOp, ast.And, ast.Or,
                     ast.Compare, ast.Load, *COMPARE.keys())
        if len(list(ast.walk(tree))) > 100 or any(not isinstance(node, supported) for node in ast.walk(tree)):
            raise ValueError()
        if any(isinstance(node, ast.Name) and node.id not in {'input', 'inputs', 'outputs', 'nodes'}
               for node in ast.walk(tree)):
            raise ValueError()
        if any(isinstance(node, ast.Constant) and not isinstance(node.value, (str, int, float, bool, type(None)))
               for node in ast.walk(tree)):
            raise ValueError()
        if any(isinstance(node, ast.Attribute) and node.attr.startswith('_') for node in ast.walk(tree)):
            raise ValueError()
        return tree
    except Exception as exc:
        raise RuntimeFailure('INVALID_CONDITION', 'The condition is outside the deterministic expression language.', 400) from exc


def evaluate(expression, inputs, outputs):
    try:
        tree = validate_expression(expression)
        def walk(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool, type(None))):
                return node.value
            if isinstance(node, ast.Name) and node.id in {'input', 'inputs', 'outputs', 'nodes'}:
                return inputs if node.id in {'input', 'inputs'} else outputs
            if isinstance(node, ast.Attribute) and not node.attr.startswith('_'):
                value = walk(node.value)
                if not isinstance(value, dict):
                    raise ValueError()
                return value[node.attr]
            if isinstance(node, ast.Subscript):
                value, key = walk(node.value), walk(node.slice)
                if not isinstance(value, (dict, list)) or not isinstance(key, (str, int)):
                    raise ValueError()
                return value[key]
            if isinstance(node, (ast.List, ast.Tuple)):
                return [walk(item) for item in node.elts]
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                return not walk(node.operand)
            if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
                values = [bool(walk(item)) for item in node.values]
                return all(values) if isinstance(node.op, ast.And) else any(values)
            if isinstance(node, ast.Compare):
                left = walk(node.left)
                for op, other in zip(node.ops, node.comparators):
                    right = walk(other)
                    if type(op) not in COMPARE or not COMPARE[type(op)](left, right):
                        return False
                    left = right
                return True
            raise ValueError()
        return walk(tree.body)
    except Exception as exc:
        raise RuntimeFailure('INVALID_CONDITION', 'The condition is outside the deterministic expression language.', 400) from exc
