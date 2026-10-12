"""Production WSGI entry point.

Hosting platforms (Render, Railway, Fly.io, Heroku...) start the app with::

    gunicorn wsgi:app

``app`` below is the same Flask application that ``app.py`` builds, so the
development server and the deployed server always serve identical behaviour.
"""

from app import app

if __name__ == "__main__":  # pragma: no cover - convenience for local runs
    from app import run

    run()
