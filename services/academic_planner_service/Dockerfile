# Dockerfile for Academic Planner Service
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy pyproject.toml, uv.lock, and README.md first for better caching
COPY pyproject.toml uv.lock* README.md ./

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the application
CMD ["uv", "run", "python", "services/academic_planner_service/app.py"]