FROM cloudflare/cloudflared:2026.10.3 AS connector
FROM python:3.13-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY --from=connector /usr/local/bin/cloudflared /usr/local/bin/cloudflared
COPY backend/app/observability.py backend/app/observability.py
COPY backend/app/log_export.py backend/app/log_export.py
COPY production/run_tunnel.py production/run_tunnel.py
ENTRYPOINT ["python", "/app/production/run_tunnel.py"]
