# Build context is the repository root (see docker-compose.yml) so the shared
# fixtures/ directory can be bundled into the image for seeding.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FIXTURE_PATH=/fixtures/warehouse_modernization.json

WORKDIR /app

# Install dependencies first for better layer caching.
COPY apps/api/pyproject.toml README.md ./
RUN pip install --upgrade pip && pip install -e ".[local]"

# Application code + shared fixtures.
COPY apps/api /app
COPY fixtures /fixtures

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
