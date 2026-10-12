"""Safe evaluation engine for the calculator.

Expressions are normalised into the dialect defined by :mod:`dialect`, parsed
with :mod:`ast` and evaluated against an explicit whitelist of operators,
functions and constants. Nothing from the builtins scope is reachable, so user
input cannot execute arbitrary code.
"""

import ast
import math
import operator

from dialect import (
    MAX_EXPONENT,
    MAX_INPUT_LENGTH,
    MAX_RESULT,
    RESULT_PRECISION,
    VALID_MODES,
)
from errors import CalculationError
from expression_normalizer import normalize_expression
from math_functions import CONSTANTS, FUNCTIONS

BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def validate_number(value):
    """Reject anything that is not a finite number inside the result range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalculationError("Result is not a number.")

    if abs(value) > MAX_RESULT:
        raise CalculationError("Result is outside the supported range.")

    if isinstance(value, float) and not math.isfinite(value):
        raise CalculationError("Result is outside the supported range.")

    return value


def clean_number(value):
    """Round binary floating-point noise out of a finished result.

    ``log(1000)`` evaluates to ``2.9999999999999996`` and ``0.1 + 0.2`` to
    ``0.30000000000000004``; a calculator should answer ``3`` and ``0.3``.
    """
    if isinstance(value, int):
        return value

    return float(f"{value:.{RESULT_PRECISION}g}")


class Evaluator:
    """Walks an AST and evaluates whitelisted nodes for a fixed angle mode."""

    def __init__(self, mode):
        self.mode = mode

    def evaluate(self, node):
        if isinstance(node, ast.Constant):
            return self._constant(node)

        if isinstance(node, ast.Name):
            return self._name(node)

        if isinstance(node, ast.UnaryOp):
            return self._unary(node)

        if isinstance(node, ast.BinOp):
            return self._binary(node)

        if isinstance(node, ast.Call):
            return self._call(node)

        raise CalculationError("Invalid expression.")

    def _constant(self, node):
        if type(node.value) in (int, float):
            return node.value
        raise CalculationError("Invalid number.")

    def _name(self, node):
        if node.id in CONSTANTS:
            return CONSTANTS[node.id]
        raise CalculationError("Unknown constant: " + node.id)

    def _unary(self, node):
        operation = UNARY_OPERATORS.get(type(node.op))
        if operation is None:
            raise CalculationError("Unsupported unary operation.")
        return operation(self.evaluate(node.operand))

    def _binary(self, node):
        operation = BINARY_OPERATORS.get(type(node.op))
        if operation is None:
            raise CalculationError("Unsupported operator.")

        left = self.evaluate(node.left)
        right = self.evaluate(node.right)

        if abs(left) > MAX_RESULT or abs(right) > MAX_RESULT:
            raise CalculationError("Number is too large.")

        if isinstance(node.op, ast.Pow):
            self._check_power(left, right)

        if isinstance(node.op, (ast.Div, ast.Mod)) and right == 0:
            raise CalculationError("Cannot divide by zero.")

        return validate_number(operation(left, right))

    @staticmethod
    def _check_power(base, exponent):
        if abs(exponent) > MAX_EXPONENT:
            raise CalculationError("Exponent is too large.")
        if base == 0 and exponent < 0:
            raise CalculationError("Cannot divide by zero.")

    def _call(self, node):
        if not isinstance(node.func, ast.Name):
            raise CalculationError("Invalid function.")

        name = node.func.id
        if name not in FUNCTIONS:
            raise CalculationError("Unknown function: " + name)

        if node.keywords or len(node.args) != 1:
            raise CalculationError("Function " + name + " takes one argument.")

        argument = self.evaluate(node.args[0])
        return validate_number(FUNCTIONS[name](argument, self.mode))


def calculate_expression(expression, mode="DEG"):
    """Evaluate ``expression`` and return a number, or raise CalculationError."""
    if not isinstance(expression, str) or not expression.strip():
        raise CalculationError("Enter an expression.")

    if len(expression) > MAX_INPUT_LENGTH:
        raise CalculationError("Expression is too long.")

    if mode not in VALID_MODES:
        raise CalculationError("Invalid angle mode.")

    normalized = normalize_expression(expression)

    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as error:
        raise CalculationError("Invalid expression syntax.") from error

    return clean_number(Evaluator(mode).evaluate(tree.body))
