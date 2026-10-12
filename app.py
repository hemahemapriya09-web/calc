"""Flask server that serves the calculator frontend and its JSON API.

Run with::

    python app.py

Then open http://127.0.0.1:5000 in a browser. The page is rendered from
``templates/index.html`` and talks to the ``/calculate`` endpoint below.

API contract
------------

``POST /calculate``

    request   {"expression": "2pi + 1", "mode": "DEG"}
    success   200 {"result": 7.28318530718}
    failure   4xx {"error": "human readable reason"}

The dialect, the numeric limits and the keypad vocabulary all come from
:mod:`dialect`, so the page and the evaluator can never disagree about which
expressions are valid.
"""

import os

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from calculator import CalculationError, calculate_expression
from dialect import (
    DEFAULT_MODE,
    MAX_MODE_LENGTH,
    VALID_MODES,
    VALUE_STARTER_KEYS,
)

API_PREFIX = "/calculate"
HEALTH_PATH = "/healthz"
SERVICE_NAME = "Scientific Calculator"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
ALL_INTERFACES = "0.0.0.0"

app = Flask(__name__)


@app.route("/")
def home():
    """Render the calculator page."""
    return render_template(
        "index.html",
        angle_modes=VALID_MODES,
        default_mode=DEFAULT_MODE,
        value_starter_keys=VALUE_STARTER_KEYS,
    )


@app.post(API_PREFIX)
def calculate():
    """Evaluate an expression posted as JSON and return the result."""
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify(error="Invalid request body."), 400

    mode = payload.get("mode", DEFAULT_MODE)
    if (
        not isinstance(mode, str)
        or len(mode) > MAX_MODE_LENGTH
        or mode not in VALID_MODES
    ):
        return jsonify(error="Invalid angle mode."), 400

    try:
        result = calculate_expression(payload.get("expression"), mode)
    except CalculationError as error:
        return jsonify(error=str(error)), 400
    except ZeroDivisionError:
        return jsonify(error="Cannot divide by zero."), 400
    except OverflowError:
        return jsonify(error="Result is outside the supported range."), 400

    return jsonify(result=result)


@app.get(HEALTH_PATH)
def health():
    """Liveness probe for the hosting platform and any uptime monitor."""
    return jsonify(status="ok", service=SERVICE_NAME)


@app.errorhandler(HTTPException)
def handle_http_error(error):
    """Return JSON for API errors and the default page for everything else."""
    if request.path == API_PREFIX:
        return jsonify(error=error.description), error.code
    return error


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Answer API failures with JSON instead of an HTML traceback page."""
    if isinstance(error, HTTPException):
        return handle_http_error(error)

    app.logger.exception("Unhandled error while serving %s", request.path)
    if request.path == API_PREFIX:
        return jsonify(error="Internal server error."), 500
    return "Internal server error.", 500


def run():
    """Start the built-in server for local development.

    A deployed instance is served by a production WSGI server instead
    (``gunicorn wsgi:app``, see ``Procfile``), which reads ``app`` directly.
    """
    port_value = os.environ.get("PORT")
    host = os.environ.get("HOST") or (
        ALL_INTERFACES if port_value else DEFAULT_HOST
    )
    port = int(port_value or DEFAULT_PORT)
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run()
