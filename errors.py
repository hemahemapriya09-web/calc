"""Shared error type for the calculator's expression pipeline.

Both the front end contract (``app.py``) and the evaluation engine raise the
same error type, so a malformed expression is always reported to the browser
as a ``400`` with a human readable ``error`` field.
"""


class CalculationError(ValueError):
    """Raised when an expression cannot be normalised, parsed or evaluated."""
