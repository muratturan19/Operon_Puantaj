# Stage 1: Build React frontend (SaaS modu — Portal SSO, cookie tabanlı auth)
FROM node:20-slim AS frontend-builder
WORKDIR /build
ENV VITE_AUTH_MODE=saas
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend (gömülü frontend build'ini de servis eder)
FROM python:3.12-slim
# Log satirlari docker logs'a ANINDA dussun (blok-buffer'da takilip kaybolmasin)
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-builder /build/dist /frontend/dist
# security 2026-10-23: drop pip, setuptools and wheel from the runtime image (build-time tools only)
# pip is not used at runtime; even the latest pip (26.2.2) vendors vulnerable urllib3 2.7.0, msgpack 1.1.2 and
# setuptools 70.3.0 (pip/_vendor); python<=3.11 bases also ship setuptools 79 + wheel with vendored jaraco.context
# 5.3.0 / wheel 0.45.1. None of them is imported at runtime. Every Python found (system + venvs) is handled.
RUN set -e; for py in /usr/local/bin/python3 /opt/*/bin/python3 /app/.venv/bin/python3 /venv/bin/python3; do \
      if [ -x "$py" ] && "$py" -m pip --version >/dev/null 2>&1; then "$py" -m pip uninstall -y -q setuptools wheel pip; fi; \
    done; \
    ! /usr/local/bin/python3 -m pip --version >/dev/null 2>&1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
