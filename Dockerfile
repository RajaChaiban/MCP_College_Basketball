FROM python:3.12-slim

WORKDIR /app

# Install system deps for C extensions (rapidfuzz, lxml) and geospatial libs
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgdal-dev \
    libgeos-dev \
    libproj-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY dashboard/ dashboard/
COPY start.sh .
COPY cbb_predictor_bundle.joblib .
COPY cbb_predictor_bundle_2025_26_safe.joblib .
COPY team_features_lookup.json .

# Install all dependencies (MCP server + dashboard)
RUN pip install --no-cache-dir -e ".[dashboard]"

# Fix line endings (Windows CRLF → Unix LF) and make executable
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

# Non-root user for security
RUN useradd -m cbbapp
USER cbbapp

# Environment defaults
ENV CBB_TRANSPORT=streamable-http
ENV CBB_HOST=0.0.0.0
ENV CBB_PORT=8000
ENV CBB_DASH_HOST=0.0.0.0
ENV CBB_LOG_LEVEL=INFO
ENV CBB_DEBUG=0
ENV CBB_CACHE_ENABLED=true

EXPOSE 8050

# Run both MCP server + Dash dashboard
CMD ["/app/start.sh"]
