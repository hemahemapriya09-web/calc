# Scientific Calculator

A Flask web app: a scientific calculator UI that evaluates expressions on the
server with a whitelisted AST evaluator. No `eval`, no expression ever reaches
Python's builtins scope.

* `GET /` — the calculator page
* `POST /calculate` — JSON API, `{"expression": "sin(30)", "mode": "DEG"}`
* `GET /healthz` — liveness probe used by hosting platforms

## Run locally

```powershell
python -m pip install -r requirements.txt
python app.py
```

Then open <http://127.0.0.1:5000>.

For a production-style server (what a host actually runs):

```powershell
.\start.ps1              # waitress on Windows, gunicorn elsewhere
.\start.ps1 -Port 8080   # different port
```

## Publish it on the internet

### Option 1 - public URL in one command, no account

```powershell
.\share.ps1
```

Starts the production server and opens a Cloudflare quick tunnel, printing an
address like `https://random-words-here.trycloudflare.com`. The site is then
reachable from any device on the internet.

Closing the window (or Ctrl+C) stops both the tunnel and the server it started,
so the address is temporary and a new one is issued on the next run - use
option 2 for a permanent home. The tunnel client is downloaded into `.tools/`
on first use; `.tools/` is git-ignored.

### Option 2 - permanent hosting on Render (free tier)

1. Push this repository to GitHub.
2. In Render, choose **New +** → **Blueprint** and select the repository.
3. Render reads `render.yaml`, installs `requirements.txt` and starts
   `gunicorn wsgi:app`. The health check is `/healthz`.

The service gets a stable `https://<name>.onrender.com` address and redeploys
on every push. Free instances sleep after inactivity and take a few seconds to
wake on the next request.

### Option 3 - any container host (Cloud Run, Fly.io, Railway, Kubernetes)

```powershell
docker build -t scientific-calculator .
docker run -p 8080:8080 scientific-calculator
```

The image listens on `$PORT` (default `8080`) and serves through gunicorn, so
it drops into any platform that runs a container.

### Option 4 - Railway / Heroku-style buildpack

Both read `Procfile`, which is already present:

```
web: gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60
```

`Procfile` is a single line - keep it that way.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `5000` | Port the built-in server binds (hosts set this automatically) |
| `HOST` | `127.0.0.1`, or `0.0.0.0` when `PORT` is set | Interface the built-in server binds |

A deployed instance ignores both: gunicorn and waitress read `wsgi:app` and are
told where to listen by the platform.

## Tests

`_verify_endpoints.py` exercises the page and the API, including the failure
paths (division by zero, syntax errors, domain errors, rejected code injection,
invalid angle mode). Point it at any deployment with `CALC_BASE_URL`:

```powershell
python _verify_endpoints.py
$env:CALC_BASE_URL = "https://your-app.onrender.com"; python _verify_endpoints.py
```

Every line should print `PASS` and the total failures must be `0`. Remote hosts
and tunnels answer more slowly than localhost, so raise the per-request timeout
if a run trips over the network rather than the app:

```powershell
$env:CALC_TIMEOUT_SECONDS = "30"; python _verify_endpoints.py
```

## Project layout

| File | Responsibility |
| --- | --- |
| `app.py` | Flask routes, request validation, JSON error handling, local server |
| `wsgi.py` | Production entry point - `gunicorn wsgi:app` |
| `calculator.py` | AST evaluator, numeric limits, float-noise cleanup |
| `expression_normalizer.py` | Rewrites UI notation (`2pi`, `3(4+5)`) into valid Python syntax |
| `math_functions.py` | Whitelisted functions and constants |
| `dialect.py` | Single source of truth for modes, keypad vocabulary and limits |
| `errors.py` | `CalculationError` shared by the evaluator and the API |
| `templates/index.html` | The calculator page (styles, keypad, fetch client) |
| `render.yaml`, `Procfile`, `Dockerfile` | Deployment targets |
| `start.ps1`, `share.ps1` | Run locally / publish publicly |
| `_verify_endpoints.py` | End-to-end endpoint tests |
