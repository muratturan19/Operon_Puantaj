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
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-builder /build/dist /frontend/dist
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
