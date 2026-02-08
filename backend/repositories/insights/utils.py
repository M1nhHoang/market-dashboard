"""
Shared utilities for insights repositories.
"""
import operator
import re


# Operators for condition parsing
OPERATORS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


def parse_condition(condition: str) -> tuple:
    """Parse condition like '> 3.0' into (operator_func, value)."""
    if not condition:
        return operator.gt, 0.0
    match = re.match(r'([><=!]+)\s*([\d.]+)', condition.strip())
    if match:
        op_str, value = match.groups()
        return OPERATORS.get(op_str, operator.gt), float(value)
    return operator.gt, 0.0
