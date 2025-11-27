# Docker Deployment Guide

This guide explains how to deploy the SyllabusMCP distributed services using Docker and Docker Compose.

## Architecture Overview

The distributed system consists of four containerized services:

- **syllabus-service** (port 8001): PDF parsing and LLM-powered syllabus analysis
- **academic-planner-service** (port 8002): LLM-powered academic planning
- **productivity-service** (port 8003): Calendar events and reminders management
- **mcp-gateway**: Unified MCP interface for all services

## Prerequisites

1. **Docker and Docker Compose** installed
2. **OpenAI API key** for LLM services
3. **curl** (for health checks)

## Quick Start

### 1. Environment Setup

Copy the environment template and configure your API key:

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Build and Start Services

```bash
# Build all services and start them
docker-compose up --build -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

### 3. Verify Services

Check that all services are healthy:

```bash
# Health checks
curl http://localhost:8001/health  # Syllabus service
curl http://localhost:8002/health  # Academic planner
curl http://localhost:8003/health  # Productivity service

# Service discovery
docker-compose exec mcp-gateway uv run python -c "
from mcp_gateway.server import get_service_status
print(get_service_status())
"
```

## Service Details

### Syllabus Service (Port 8001)
- **Endpoints**: `/parse-syllabus`, `/answer-question`, `/health`
- **Timeouts**: 5 minutes for parsing, 2 minutes for questions
- **Requirements**: OpenAI API key

### Academic Planner Service (Port 8002)
- **Endpoints**: `/create-plan`, `/show-assignment-summary`, `/health`
- **Timeouts**: 5 minutes for plan creation
- **Requirements**: OpenAI API key

### Productivity Service (Port 8003)
- **Endpoints**: 8 endpoints for calendar/reminder CRUD operations
- **Timeouts**: 30 seconds (fast operations)
- **Storage**: In-memory (resets on restart)

### MCP Gateway
- **Function**: Unified MCP interface for all 12 tools
- **Network**: Internal only (no exposed ports)
- **Dependencies**: All other services must be healthy

## Usage Examples

### Direct HTTP API Usage

```bash
# Parse a syllabus
curl -X POST http://localhost:8001/parse-syllabus \
  -H "Content-Type: application/json" \
  -d '{"pdf_path_or_url": "https://example.com/syllabus.pdf"}'

# Create a calendar event
curl -X POST http://localhost:8003/create-calendar-event \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Study Session",
    "start": "2024-01-15T14:00:00-05:00",
    "end": "2024-01-15T16:00:00-05:00",
    "location": "Library"
  }'
```

### MCP Gateway Usage

```python
# In your orchestrator or client code
from mcp_gateway.server import mcp

# All tools available through single interface
syllabus = mcp.parse_syllabus("syllabus.pdf")
plan = mcp.create_academic_plan([syllabus])
event = mcp.create_calendar_event("Study", "2024-01-01T10:00", "2024-01-01T11:00")
```

## Management Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart a specific service
docker-compose restart syllabus-service

# View service logs
docker-compose logs -f syllabus-service

# Scale services (if needed)
docker-compose up -d --scale productivity-service=3

# Update services
docker-compose build --no-cache
docker-compose up -d
```

## Troubleshooting

### Service Won't Start
1. Check logs: `docker-compose logs [service-name]`
2. Verify environment variables in `.env`
3. Check if ports 8001-8003 are available

### Health Check Failures
1. Wait for service startup (LLM services take longer)
2. Check OpenAI API key is valid
3. Verify network connectivity between containers

### High Memory Usage
1. LLM services require significant memory
2. Consider limiting Docker memory if needed
3. Monitor with `docker stats`

### Timeout Issues
1. LLM operations can take 1-5 minutes
2. Adjust client timeouts accordingly
3. Check service logs for actual processing time

## Production Considerations

1. **Secrets Management**: Use Docker secrets or external secret management
2. **Persistent Storage**: Add volumes for productivity service data
3. **Load Balancing**: Use nginx or similar for HTTP load balancing
4. **Monitoring**: Add Prometheus/Grafana for service monitoring
5. **Logging**: Configure centralized logging (ELK stack)
6. **Security**: Run containers as non-root (already configured)

## Development Mode

For development with hot reloading:

```bash
# Mount source code as volumes (add to docker-compose.yml)
volumes:
  - .:/app
  - /app/.venv  # Exclude virtual environment
```

## Cleanup

```bash
# Stop and remove all containers, networks, images
docker-compose down --volumes --rmi all

# Remove unused Docker objects
docker system prune -a
```