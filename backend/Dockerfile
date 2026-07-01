# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder

WORKDIR /app

# Install Python dependencies (wheels only, no C compilation needed)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

LABEL maintainer="EduAgent Team <dev@eduagent.ai>"
LABEL version="2.0.0"
LABEL description="EduAgent 2.0 - AI-Powered Adaptive Learning Backend"

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder (installed globally now)
COPY --from=builder /usr/local /usr/local/

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY docs/ ./docs/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user
RUN useradd -m -u 1000 eduagent && chown -R eduagent:eduagent /app
USER eduagent

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
