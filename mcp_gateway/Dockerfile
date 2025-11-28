# Dockerfile for MCP Gateway
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy pyproject.toml, uv.lock, and README.md first for better caching
COPY pyproject.toml uv.lock* README.md ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# MCP Gateway doesn't expose HTTP ports - it's an MCP server
# The orchestrator will connect to it directly

# Set environment variables for service discovery
ENV SYLLABUS_SERVICE_URL=http://syllabus-service:8001
ENV ACADEMIC_PLANNER_SERVICE_URL=http://academic-planner-service:8002
ENV PRODUCTIVITY_SERVICE_URL=http://productivity-service:8003

# Run the MCP Gateway
CMD ["uv", "run", "python", "mcp_gateway/server.py"]