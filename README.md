# SyllabusMCP - Distributed Architecture

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)
[![MCP](https://img.shields.io/badge/MCP-Gateway-orange.svg)](https://modelcontextprotocol.io/)

**SyllabusMCP** is an educational project for **CMU 17-625 API Design** demonstrating a **distributed microservices architecture** using the Model Context Protocol (MCP). The system transforms academic syllabus processing into a scalable, containerized solution with HTTP-based communication between services.

## 🎯 Distributed Architecture Overview

This system demonstrates a **production-ready distributed MCP architecture** with native protocol support and LLM sampling capabilities. Key architectural achievements:

- **🐳 Containerized MCP Servers** - Each service runs as an MCP server in Docker
- **🌐 Native MCP Protocol** - Direct MCP communication via StreamableHTTP transport
- **🤖 Sampling Support** - MCP servers can request LLM completions via ctx.sample()
- **📋 Dynamic Registry** - Service discovery and MCP client management
- **⚖️ Horizontal Scaling** - Stateless MCP servers enable load balancing
- **🔄 Service Independence** - Services deployed and scaled independently
- **🛡️ Type-safe APIs** - Pydantic models ensure data consistency
- **📊 Health Monitoring** - TCP health checks for all services
- **🚀 Production Ready** - Complete Docker Compose infrastructure

## 🏗️ Architecture Diagram

```mermaid
graph TB
    subgraph "Orchestration Layer"
        CLI1["orchestrator/run.py<br/>📋 Batch Processing"]
        CLI2["orchestrator/run_agent.py<br/>🤖 AI-Driven Workflow"]
    end
    
    subgraph "Registry & Sampling"
        REGISTRY["📚 MCP Client Registry<br/>Service Discovery<br/>Dynamic Client Creation"]
        SAMPLING["🤖 OpenAI Sampling Handler<br/>Provides LLM to MCP Servers<br/>GPT-4o / GPT-5 Support"]
    end

    subgraph "MCP Servers - Docker Containers"
        SERVICE1["📄 Syllabus Server<br/>FastMCP :8601/mcp<br/>• get_syllabus_text<br/>• structure_syllabus (sampling)<br/>• answer_syllabus_question (sampling)<br/>• answer_question_about_syllabi"]
        SERVICE2["🎓 Academic Planner<br/>FastMCP :8602/mcp<br/>• create_academic_plan (sampling)<br/>• show_assignment_summary"]
        SERVICE3["📅 Productivity Server<br/>FastMCP :8603/mcp<br/>• Calendar Events CRUD<br/>• Reminders CRUD<br/>• Bulk Operations"]
    end
    
    CLI1 --> REGISTRY
    CLI2 --> REGISTRY
    REGISTRY -->|MCP Protocol<br/>StreamableHTTP| SERVICE1
    REGISTRY -->|MCP Protocol<br/>StreamableHTTP| SERVICE2
    REGISTRY -->|MCP Protocol<br/>StreamableHTTP| SERVICE3
    
    SERVICE1 -.->|ctx.sample()| SAMPLING
    SERVICE2 -.->|ctx.sample()| SAMPLING
    SAMPLING -.->|LLM Response| SERVICE1
    SAMPLING -.->|LLM Response| SERVICE2
    
    classDef orchestration fill:#e1f5fe
    classDef registry fill:#f3e5f5
    classDef service fill:#e8f5e8
    classDef sampling fill:#fff3e0
    
    class CLI1,CLI2 orchestration
    class REGISTRY registry
    class SAMPLING sampling
    class SERVICE1,SERVICE2,SERVICE3 service
```

## 🎯 Service Architecture

### 📄 Syllabus Server (Port 8601)
**MCP server for PDF processing and AI-powered syllabus structuring**
- **MCP Endpoint**: `http://localhost:8601/mcp` (StreamableHTTP)
- **Tools**: `get_syllabus_text`, `structure_syllabus`, `answer_syllabus_question`, `answer_question_about_syllabi`
- **Flow**: Extract PDF → Structure via sampling (GPT-5) → Answer questions via sampling
- **Sampling**: Uses `ctx.sample()` for LLM-powered structuring and Q&A
- **Dependencies**: pdfplumber, FastMCP, MCP sampling support

### 🎓 Academic Planner Server (Port 8602)  
**MCP server for multi-course planning and analysis**
- **MCP Endpoint**: `http://localhost:8602/mcp` (StreamableHTTP)
- **Tools**: `create_academic_plan`, `show_assignment_summary`
- **Features**: Cross-course analysis, conflict detection, workload balancing
- **Sampling**: Uses `ctx.sample()` for GPT-5 powered academic planning
- **Returns**: Structured `Plan` with events, reminders, and assignments

### 📅 Productivity Server (Port 8603)
**MCP server for calendar and reminder management**
- **MCP Endpoint**: `http://localhost:8603/mcp` (StreamableHTTP)
- **Tools**: 8 CRUD tools for events/reminders + bulk operations + formatted displays
- **Features**: Fast CRUD operations, bulk processing, formatted output
- **Storage**: In-memory with Pydantic models
- **No Sampling**: Pure CRUD operations without LLM calls

### 📚 MCP Client Registry
**Dynamic service discovery and client management**
- **Function**: Creates FastMCP clients with sampling support for each service
- **Location**: `registry/__init__.py`
- **Sampling Handler**: Provides OpenAI-based LLM access to MCP servers
- **Benefits**: Single point of configuration, automatic client creation

## 🚀 Quick Start - Docker Deployment

The fastest way to run SyllabusMCP is using Docker Compose, which automatically starts all services:

### Prerequisites

- **Docker & Docker Compose** 
- **OpenAI API Key** (for AI-powered parsing)
- **PDF files or directories** (syllabi to process - supports individual files, directories, or mixed)

### 🐳 Docker Deployment (Recommended)

1. **Clone and setup**:
   ```bash
   git clone https://github.com/cmu-able/SyllabusMCP-distributed.git
   cd SyllabusMCP-distributed
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

2. **Start all services**:
   ```bash
   docker-compose up -d
   ```
   
   This starts:
   - 📄 Syllabus MCP Server on port 8601
   - 🎓 Academic Planner MCP Server on port 8602  
   - 📅 Productivity MCP Server on port 8603
   - 💓 TCP health checks for all services

3. **Verify deployment**:
   ```bash
   docker-compose ps
   # MCP servers don't have /health endpoints - use docker ps to check status
   docker ps --filter "name=syllabus-service" --filter "name=academic-planner-service" --filter "name=productivity-service"
   ```

### 💻 Local Development Setup

For development without Docker:

```bash
# Install dependencies
uv sync --extra dev

# Set environment
export OPENAI_API_KEY="your-api-key-here"

# Run MCP servers individually (3 separate terminals)
uv run python services/syllabus_service/mcp_server.py
uv run python services/academic_planner_service/mcp_server.py  
uv run python services/productivity_service/mcp_server.py
```

## 💬 Usage Examples

### Basic Academic Planning
```bash
# Traditional batch processing
uv run python orchestrator/run.py syllabus1.pdf syllabus2.pdf

# AI-driven workflow with custom goals
uv run python orchestrator/run_agent.py run \
  --prompt "Create calendar events and reminders for all assignments" \
  syllabus1.pdf syllabus2.pdf
```

### Natural Language Queries
```bash
# Ask questions about syllabi
uv run python orchestrator/run_agent.py run \
  --prompt "What are the attendance policies across all courses?" \
  course1.pdf course2.pdf

# Analyze workload across directory of syllabi
uv run python orchestrator/run_agent.py run \
  --prompt "Which weeks will be the busiest this semester?" \
  ../syllabus-pdfs

# Mix files and directories
uv run python orchestrator/run_agent.py run \
  --prompt "Compare assignment loads" \
  course1.pdf ../more-courses course2.pdf
```

### Tool Discovery & Execution
```bash
# List all 16 available tools
uv run python orchestrator/run_agent.py tools

# View specific tool schemas  
uv run python orchestrator/run_agent.py tools syllabus_server.get_syllabus_text

# Show all tools from a service
uv run python orchestrator/run.py --list

# Execute a specific tool directly
uv run python orchestrator/run_agent.py exec productivity_server.show_reminders
uv run python orchestrator/run_agent.py exec productivity_server.show_calendar_events

# Execute a tool with arguments
uv run python orchestrator/run_agent.py exec productivity_server.create_reminder \
  --args '{"title": "Submit assignment", "due": "2025-12-15T23:59:00"}'
```

### Service Interaction
```bash
# MCP servers use MCP protocol, not REST
# Use the orchestrator or registry to interact with services:

# List available tools from all services
uv run python orchestrator/run_agent.py tools

# Execute a specific tool
uv run python orchestrator/run_agent.py exec syllabus_server.get_syllabus_text \
  --args '{"pdf_path_or_url": "../syllabus-pdfs/17603.pdf"}'

# Check container status
docker ps
```

## 📊 Production Features

### 📈 Health Monitoring
```bash
# Check service status via Docker
docker ps
docker-compose ps

# Services use TCP health checks (netcat)
# Health status shows in docker ps output as (healthy) or (unhealthy)
```

### 📊 Service Metrics
```bash
# View MCP server logs
docker-compose logs syllabus-service
docker-compose logs academic-planner-service
docker-compose logs productivity-service

# Monitor resource usage
docker stats

# Follow live logs
docker-compose logs -f syllabus-service
```

### 🔄 Scaling Services
```bash
# Scale individual MCP servers
docker-compose up -d --scale syllabus-service=3
docker-compose up -d --scale productivity-service=2

# MCP servers are stateless and can be horizontally scaled
# Note: You'll need a load balancer to distribute MCP requests
```

## 🧪 Testing

Comprehensive testing across all layers:

```bash
# Test distributed services (requires services to be running)
uv run python -m pytest tests/test_syllabus_service.py -v

# Test orchestrator integration
uv run python -m pytest tests/test_executor.py -v

# Test individual components
uv run python -m pytest tests/ -v

# Test Docker deployment
docker-compose up -d
./scripts/test_services.sh  # If available
```

## 🛠️ Development

### Distributed Project Structure
```
├── services/                     # 🏬 MCP Servers (FastMCP)
│   ├── syllabus_service/         # PDF processing :8601
│   │   ├── mcp_server.py        # FastMCP server with sampling
│   │   └── Dockerfile           # Container definition
│   ├── academic_planner_service/ # Planning :8602
│   │   ├── mcp_server.py        # FastMCP server with sampling
│   │   └── Dockerfile           # Container definition
│   ├── productivity_service/     # CRUD :8603
│   │   ├── mcp_server.py        # FastMCP server (no sampling)
│   │   └── Dockerfile           # Container definition
│   └── shared/
│       ├── models.py            # 🏷️ Pydantic models
│       └── sampling_utils.py    # Shared sampling utilities
├── orchestrator/                # 🎭 Client Applications
│   ├── run.py                   # Batch processor
│   ├── run_agent.py             # AI-driven workflow
│   ├── shared.py                # Common utilities
│   ├── executor.py              # Parallel execution
│   ├── sampling.py              # OpenAI sampling handler
│   └── models.py                # Execution models
├── registry/                    # 📚 MCP Client Registry
│   └── __init__.py              # Dynamic client creation
├── docker-compose.yml           # 🐳 Service Orchestration
├── .env.example                 # Environment template
└── README.md                    # This file
```

### Adding New MCP Servers

1. **Create FastMCP Server**:
   ```bash
   mkdir services/new_service
   # Add mcp_server.py with FastMCP and @mcp.tool() decorators
   # Add Dockerfile
   ```

2. **Register in Registry**:
   ```python
   # Add to MCP_SERVICES dict in registry/__init__.py
   MCP_SERVICES = {
       "new_server": os.getenv("NEW_SERVICE_URL", "http://localhost:8604") + "/mcp",
   }
   ```

3. **Update Docker Compose**:
   ```yaml
   # Add service definition in docker-compose.yml
   # Use TCP health check: nc -z localhost PORT
   # Expose port for MCP protocol
   ```

4. **Add Sampling (if needed)**:
   ```python
   # In your tool function:
   async def your_tool(data: dict, ctx: Context | None = None):
       if ctx and hasattr(ctx, "sample"):
           result = await ctx.sample(messages="your prompt", model_preferences="gpt-4o")
   ```

## 🔧 Configuration

### Environment Variables (.env file)
```bash
# Required
OPENAI_API_KEY=your-openai-key-here

# MCP Service URLs (automatically configured in Docker)
SYLLABUS_SERVICE_URL=http://localhost:8601
ACADEMIC_PLANNER_SERVICE_URL=http://localhost:8602  
PRODUCTIVITY_SERVICE_URL=http://localhost:8603

# Optional: MCP Server Configuration
SYLLABUS_MCP_HOST=0.0.0.0
SYLLABUS_MCP_PORT=8601
ACADEMIC_PLANNER_MCP_HOST=0.0.0.0
ACADEMIC_PLANNER_MCP_PORT=8602
PRODUCTIVITY_MCP_HOST=0.0.0.0
PRODUCTIVITY_MCP_PORT=8603
```

### Docker Configuration
- **Networking**: MCP servers communicate via internal Docker network
- **Health Checks**: TCP checks using `nc -z localhost PORT`
- **Volumes**: No persistent storage required (stateless servers)
- **Ports**: 8601, 8602, 8603 exposed for MCP protocol access
- **Protocol**: StreamableHTTP transport for MCP communication

## 🎓 Educational Context - API Design Principles

This project demonstrates **advanced API design concepts** for **CMU 17-625**:

### 📚 Core Concepts Demonstrated
1. **🌐 Protocol-Driven Architecture** - MCP protocol for distributed services
2. **🎁 Service Decomposition** - Single responsibility per MCP server
3. **📋 Dynamic Service Discovery** - Registry pattern for client management
4. **📊 Type Safety** - Pydantic models for data validation across protocol
5. **🔄 Horizontal Scaling** - Stateless MCP server design
6. **🤖 LLM Integration** - Native sampling support in MCP protocol
7. **🚀 Containerization** - Production-ready Docker deployment
8. **🛠️ Developer Experience** - Tool discovery, typed interfaces, error handling

### 💯 API Design Best Practices
- **Protocol Design** - MCP specification with StreamableHTTP transport
- **Error Handling** - Consistent error propagation across MCP servers
- **Capability Discovery** - Runtime tool schema discovery via MCP
- **Separation of Concerns** - MCP servers, sampling handlers, orchestration
- **Testing** - Component testing with MCP client/server isolation
- **Security** - Environment-based secrets, validated inputs via Pydantic

## ⚠️ Production Considerations

### Security
- **API Keys**: Store OpenAI API key securely using environment variables
- **Network Security**: Services communicate via internal Docker network
- **Input Validation**: All endpoints validate input data using Pydantic models
- **Error Handling**: No sensitive information leaked in error responses

### Monitoring
- **Health Checks**: Each service exposes `/health` endpoint
- **Logging**: Structured logging for debugging and monitoring
- **Metrics**: Docker stats for resource monitoring
- **Alerting**: Can be integrated with monitoring solutions

### Costs & Limits
- **OpenAI API**: Monitor usage to control costs
- **Resource Usage**: Each service configured with appropriate memory/CPU limits
- **Rate Limiting**: Consider implementing rate limiting for production use

## 🚀 Deployment Options

### Local Development
```bash
docker-compose up -d
```

### Production Kubernetes
```bash
# Convert Docker Compose to Kubernetes manifests
kompose convert
kubectl apply -f .
```

### Cloud Deployment
- **AWS**: ECS/EKS with Application Load Balancer
- **GCP**: Cloud Run or GKE
- **Azure**: Container Instances or AKS

## 📝 License

Created for **CMU 17-625 API Design** - Educational use only.

## 🤝 Contributing

This project demonstrates distributed architecture patterns for CMU students. For questions about the implementation patterns shown here, see course materials or contact the instructor.

---

**🏆 Achievement Unlocked**: Successfully transformed a monolithic MCP application into a production-ready distributed microservices architecture! 🎉
