from jinja2 import Undefined

from qd_core.filters.convert import to_bool


def ternary(value, true_val, false_val, none_val=None):
    """value ? true_val : false_val"""
    if (value is None or isinstance(value, Undefined)) and none_val is not None:
        return none_val
    if to_bool(value):
        return true_val
    return false_val
