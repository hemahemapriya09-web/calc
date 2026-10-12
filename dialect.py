"""The expression dialect shared by the front end and the back end.

This module is the single source of truth for the vocabulary and the numeric
limits of the calculator. ``templates/index.html`` renders its keypad from the
same names, the normaliser rewrites user input into this dialect, and the
evaluator refuses anything outside it.

Dialect summary::

    values      numbers (3, 4.5, .5) and the constants pi and e
    functions   sin cos tan asin acos atan sqrt log ln exp abs
    operators   + - * / % **  and the grouping characters ( )
    angle modes DEG and RAD

``e`` is always Euler's number. Scientific notation (``1e5``) is therefore not
part of the dialect; use ``**`` or ``exp()`` instead.
"""

DEFAULT_MODE = "DEG"
VALID_MODES = ("DEG", "RAD")
MAX_MODE_LENGTH = max(len(mode) for mode in VALID_MODES)

FUNCTION_NAMES = (
    "sin",
    "cos",
    "tan",
    "asin",
    "acos",
    "atan",
    "sqrt",
    "log",
    "ln",
    "exp",
    "abs",
)

CONSTANT_NAMES = (
    "pi",
    "e",
)

TWO_CHARACTER_OPERATORS = (
    "**",
)

ONE_CHARACTER_OPERATORS = (
    "+",
    "-",
    "*",
    "/",
    "%",
    "(",
    ")",
)

OPENING_PARENTHESIS = "("
CLOSING_PARENTHESIS = ")"
IMPLICIT_MULTIPLICATION = "*"

# The keypad values that begin a fresh operand. The page renders this list
# straight into its script, so the browser and the evaluator agree on where a
# new value starts and where an implicit multiplication belongs.
VALUE_STARTER_KEYS = (
    tuple(name + OPENING_PARENTHESIS for name in FUNCTION_NAMES)
    + CONSTANT_NAMES
    + (OPENING_PARENTHESIS,)
)

MAX_INPUT_LENGTH = 250
MAX_NORMALISED_LENGTH = 2 * MAX_INPUT_LENGTH
MAX_RESULT = 1e100
MAX_EXPONENT = 1000
TAN_EPSILON = 1e-12
RESULT_PRECISION = 12
