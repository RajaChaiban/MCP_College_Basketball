FROM python:3.12-slim

WORKDIR /app

# Install system deps for C extensions (rapidfuzz, lxml)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

# Non-root user for security
RUN useradd -m cbbmcp
USER cbbmcp

# Default to HTTP transport for container deployments
ENV CBB_TRANSPORT=streamable-http
ENV CBB_HOST=0.0.0.0
ENV CBB_PORT=8000
ENV CBB_CACHE_DIR=/tmp/cbb-cache

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/mcp', timeout=4)" || exit 1

ENTRYPOINT ["cbb-mcp"]
