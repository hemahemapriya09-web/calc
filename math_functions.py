"""The whitelisted function and constant library of the calculator.

Every name offered to a user must exist here, and every entry here is exposed
by :mod:`dialect`, which the keypad is rendered from. The import-time check at
the bottom keeps the two definitions from drifting apart.
"""

import math

from dialect import CONSTANT_NAMES, FUNCTION_NAMES, TAN_EPSILON
from errors import CalculationError

DEGREE_MODE = "DEG"

CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _to_radians(value, mode):
    return math.radians(value) if mode == DEGREE_MODE else value


def _from_radians(value, mode):
    return math.degrees(value) if mode == DEGREE_MODE else value


def _sin(value, mode):
    return math.sin(_to_radians(value, mode))


def _cos(value, mode):
    return math.cos(_to_radians(value, mode))


def _tan(value, mode):
    angle = _to_radians(value, mode)
    if abs(math.cos(angle)) < TAN_EPSILON:
        raise CalculationError("Tangent is undefined at this angle.")
    return math.tan(angle)


def _asin(value, mode):
    try:
        return _from_radians(math.asin(value), mode)
    except ValueError as error:
        raise CalculationError("Input outside the domain of arcsin.") from error


def _acos(value, mode):
    try:
        return _from_radians(math.acos(value), mode)
    except ValueError as error:
        raise CalculationError("Input outside the domain of arccos.") from error


def _atan(value, mode):
    return _from_radians(math.atan(value), mode)


def _sqrt(value, mode):
    if value < 0:
        raise CalculationError("Cannot take the square root of a negative number.")
    return math.sqrt(value)


def _log10(value, mode):
    if value <= 0:
        raise CalculationError("Logarithm is undefined for non-positive numbers.")
    return math.log10(value)


def _ln(value, mode):
    if value <= 0:
        raise CalculationError("Logarithm is undefined for non-positive numbers.")
    return math.log(value)


def _exp(value, mode):
    try:
        return math.exp(value)
    except OverflowError as error:
        raise CalculationError("Result is outside the supported range.") from error


def _abs(value, mode):
    return abs(value)


FUNCTIONS = {
    "sin": _sin,
    "cos": _cos,
    "tan": _tan,
    "asin": _asin,
    "acos": _acos,
    "atan": _atan,
    "sqrt": _sqrt,
    "log": _log10,
    "ln": _ln,
    "exp": _exp,
    "abs": _abs,
}


def _assert_dialect_is_complete():
    """Fail loudly at import time if dialect and the library disagree."""
    missing = set(FUNCTION_NAMES) - set(FUNCTIONS)
    extra = set(FUNCTIONS) - set(FUNCTION_NAMES)
    if missing or extra:
        raise RuntimeError(
            "Function library does not match dialect.FUNCTION_NAMES "
            "(missing=" + repr(sorted(missing)) + ", extra=" + repr(sorted(extra)) + ")."
        )

    if set(CONSTANTS) != set(CONSTANT_NAMES):
        raise RuntimeError(
            "Constant library does not match dialect.CONSTANT_NAMES."
        )


_assert_dialect_is_complete()
