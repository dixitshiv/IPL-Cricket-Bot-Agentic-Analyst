# IPL Command Center — web app (server.py + web/).
# Build the DuckDB locally first (uv run python -m ingest.load); this image
# copies the prebuilt data/cricket.duckdb (ipl_json/ is excluded — too large).
FROM python:3.13-slim

RUN pip install --no-cache-dir uv
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV HOST=0.0.0.0 PORT=8765
EXPOSE 8765

# Readiness probe — the deterministic dashboard works even without an API key.
HEALTHCHECK --interval=30s --timeout=4s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/api/health').status==200 else 1)"

CMD ["uv", "run", "python", "server.py"]
