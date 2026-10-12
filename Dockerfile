# Portable image: runs on any container host (Cloud Run, Fly.io, Railway,
# Docker, Kubernetes) with the same command a PaaS buildpack would use.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /srv/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD gunicorn wsgi:app --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --timeout 60 --access-logfile - --error-logfile -
