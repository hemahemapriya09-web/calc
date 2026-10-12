"""Rewrite calculator-style input into the strict dialect the evaluator parses.

The keypad lets people enter mathematics the way a calculator writes it:
``2pi``, ``3(4+5)``, ``2sin(30)``, ``(1+2)(3+4)``.  :func:`ast.parse` needs the
multiplication to be explicit, so this module inserts the omitted ``*``
operators and hands the evaluator a canonical expression.  Keeping the two
sides of the system on one dialect means the browser never sends something the
server reads differently.
"""

import re

from dialect import (
    CLOSING_PARENTHESIS,
    CONSTANT_NAMES,
    IMPLICIT_MULTIPLICATION,
    MAX_NORMALISED_LENGTH,
    ONE_CHARACTER_OPERATORS,
    OPENING_PARENTHESIS,
    TWO_CHARACTER_OPERATORS,
)
from errors import CalculationError

NUMBER = "number"
NAME = "name"
OPERATOR = "operator"
WHITESPACE = "whitespace"
UNKNOWN = "unknown"

NUMBER_PATTERN = r"\d+(?:\.\d*)?|\.\d+"
NAME_PATTERN = r"[A-Za-z_][A-Za-z_]*"
TWO_CHARACTER_PATTERN = "|".join(
    re.escape(operator) for operator in TWO_CHARACTER_OPERATORS
)
ONE_CHARACTER_PATTERN = "[" + "".join(
    re.escape(operator) for operator in ONE_CHARACTER_OPERATORS
) + "]"

TOKEN_PATTERN = re.compile(
    "(?P<" + NUMBER + ">" + NUMBER_PATTERN + ")"
    "|(?P<" + NAME + ">" + NAME_PATTERN + ")"
    "|(?P<" + OPERATOR + ">" + TWO_CHARACTER_PATTERN + "|" + ONE_CHARACTER_PATTERN + ")"
    "|(?P<" + WHITESPACE + r">\s+)"
)


class Token:
    """A single lexical unit of an expression."""

    __slots__ = ("kind", "text")

    def __init__(self, kind, text):
        self.kind = kind
        self.text = text

    def __repr__(self):
        return "Token(" + repr(self.kind) + ", " + repr(self.text) + ")"


def tokenize(raw_expression):
    """Split ``raw_expression`` into tokens, raising on unknown characters."""
    tokens = []
    position = 0
    length = len(raw_expression)

    while position < length:
        match = TOKEN_PATTERN.match(raw_expression, position)
        if match is None:
            raise CalculationError(
                "Unexpected character: " + repr(raw_expression[position])
            )

        position = match.end()
        kind = match.lastgroup
        if kind != WHITESPACE:
            tokens.append(Token(kind, match.group()))

    return tokens


def _ends_a_value(token):
    if token.kind in (NUMBER, NAME):
        return True
    return token.kind == OPERATOR and token.text == CLOSING_PARENTHESIS


def _starts_a_value(token):
    if token.kind in (NUMBER, NAME):
        return True
    return token.kind == OPERATOR and token.text == OPENING_PARENTHESIS


def _is_function_call(previous, current):
    """``sin(30)`` is a call; ``pi(2)`` only looks like one."""
    if previous.kind != NAME or current.text != OPENING_PARENTHESIS:
        return False
    return previous.text not in CONSTANT_NAMES


def _needs_multiplication(previous, current):
    if not _ends_a_value(previous) or not _starts_a_value(current):
        return False
    if _is_function_call(previous, current):
        return False
    return True


def normalize_expression(raw_expression):
    """Return ``raw_expression`` with every implicit ``*`` made explicit."""
    if not isinstance(raw_expression, str):
        raise CalculationError("Expression must be text.")

    tokens = tokenize(raw_expression)
    if not tokens:
        raise CalculationError("Enter an expression.")

    pieces = [tokens[0].text]
    for previous, current in zip(tokens, tokens[1:]):
        if _needs_multiplication(previous, current):
            pieces.append(IMPLICIT_MULTIPLICATION)
        pieces.append(current.text)

    normalized = "".join(pieces)
    if len(normalized) > MAX_NORMALISED_LENGTH:
        raise CalculationError("Expression is too long.")

    return normalized
