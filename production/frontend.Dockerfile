FROM node:22-alpine AS build
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM caddy:2.11.7-alpine
RUN apk add --no-cache python3
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY backend/app/observability.py backend/app/observability.py
COPY backend/app/log_export.py backend/app/log_export.py
COPY production/run_tunnel.py production/run_tunnel.py
COPY production/run_caddy.py production/run_caddy.py
COPY production/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /build/dist /srv
EXPOSE 80
STOPSIGNAL SIGTERM
ENTRYPOINT ["python3", "/app/production/run_caddy.py"]
CMD ["run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
