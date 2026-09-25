# Multi-stage: build the web app, then serve API + static from one container.
FROM node:22-slim AS web
WORKDIR /build
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY services/api/requirements.txt services/api/requirements.txt
RUN pip install --no-cache-dir -r services/api/requirements.txt
COPY services ./services
COPY skills ./skills
COPY evals ./evals
COPY --from=web /build/dist ./apps/web/dist
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
WORKDIR /app/services/api
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
