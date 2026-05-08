# -*- coding: utf-8 -*-
# Odoo GTK 19 — Safe Expression Evaluator
# Replaces dangerous eval() calls for invisible/readonly/required expressions

import ast
import operator

# Supported operators for safe evaluation
_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
    ast.And: None,  # handled separately
    ast.Or: None,
    ast.Not: operator.not_,
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
}


def safe_eval(expr, record_data=None, context=None):
    """Safely evaluate an Odoo expression string.
    
    Supports:
      - field == 'value', field != 'value'
      - field > 0, field <= 10
      - not field
      - field in ('a', 'b')
      - field1 and field2
      - field1 or field2
      - True, False, None
      - Integer/float/string literals
    
    Args:
        expr: Expression string (e.g. "state == 'draft'")
        record_data: Dict of field_name → value
        context: Optional context dict
    
    Returns:
        Evaluated result (usually bool)
    """
    if not expr or not isinstance(expr, str):
        return bool(expr) if expr is not None else False
    
    expr = expr.strip()
    if not expr:
        return False

    data = dict(record_data or {})
    if context:
        data['context'] = context
    # Add common Python builtins that Odoo uses
    data.setdefault('True', True)
    data.setdefault('False', False)
    data.setdefault('None', None)
    data.setdefault('true', True)
    data.setdefault('false', False)

    try:
        tree = ast.parse(expr, mode='eval')
        return _eval_node(tree.body, data)
    except Exception:
        return False


def _eval_node(node, data):
    """Recursively evaluate an AST node."""
    
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, data)
    
    # Constants: True, False, None, 42, 'hello'
    if isinstance(node, ast.Constant):
        return node.value
    
    # Name lookup: field_name → record_data[field_name]
    if isinstance(node, ast.Name):
        return data.get(node.id, False)
    
    # Unary ops: not x, -x
    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, data)
        if isinstance(node.op, ast.Not):
            return not operand
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        return operand
    
    # Boolean ops: x and y, x or y
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            result = True
            for v in node.values:
                result = _eval_node(v, data)
                if not result:
                    return result
            return result
        if isinstance(node.op, ast.Or):
            result = False
            for v in node.values:
                result = _eval_node(v, data)
                if result:
                    return result
            return result
    
    # Comparisons: a == b, a > b, a in (x, y)
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, data)
        for op_node, comp_node in zip(node.ops, node.comparators):
            right = _eval_node(comp_node, data)
            op_func = _OPS.get(type(op_node))
            if op_func is None:
                return False
            if not op_func(left, right):
                return False
            left = right
        return True
    
    # Binary ops: a + b, a - b
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, data)
        right = _eval_node(node.right, data)
        op_func = _OPS.get(type(node.op))
        if op_func:
            return op_func(left, right)
        return False
    
    # Tuple/List: (a, b, c) or [a, b, c]
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(_eval_node(e, data) for e in node.elts)
    
    # Attribute access: record.field (we don't support deep access)
    if isinstance(node, ast.Attribute):
        val = _eval_node(node.value, data)
        if isinstance(val, dict):
            return val.get(node.attr, False)
        return getattr(val, node.attr, False)
    
    # Subscript: data['key']
    if isinstance(node, ast.Subscript):
        val = _eval_node(node.value, data)
        key = _eval_node(node.slice, data)
        try:
            return val[key]
        except (KeyError, IndexError, TypeError):
            return False
    
    # If expression: x if cond else y
    if isinstance(node, ast.IfExp):
        test = _eval_node(node.test, data)
        if test:
            return _eval_node(node.body, data)
        return _eval_node(node.orelse, data)
    
    # Call: limited to len(), bool(), int(), str()
    if isinstance(node, ast.Call):
        func_name = ''
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        
        safe_funcs = {
            'len': len,
            'bool': bool,
            'int': int,
            'str': str,
            'float': float,
            'abs': abs,
        }
        if func_name in safe_funcs:
            args = [_eval_node(a, data) for a in node.args]
            return safe_funcs[func_name](*args)
        return False
    
    return False
