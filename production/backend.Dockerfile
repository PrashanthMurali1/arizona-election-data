FROM python:3.13-slim-bookworm
ARG APP_UID=501
ARG APP_GID=20
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tzdata ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && (getent group "${APP_GID}" || groupadd --gid "${APP_GID}" app) \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY production/requirements-monitoring.txt production/requirements-monitoring.txt
RUN pip install --no-cache-dir -r production/requirements-monitoring.txt
COPY backend backend
COPY scripts scripts
COPY production production
RUN mkdir -p backend/local data/raw
USER app
