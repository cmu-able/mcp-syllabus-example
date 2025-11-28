# Convert SyllabusMCP to Distributed Microservices Architecture

## Problem Statement
The current SyllabusMCP system uses FastMCP to provide all services through a single interface. We need to convert this to a distributed microservices architecture where:
- Each service (syllabus_server, academic_planner, productivity_server) runs as an independent REST API in its own Docker container
- A local MCP layer provides the same interface but makes REST calls to the appropriate services
- The orchestrator continues to work with the MCP interface but now communicates with distributed services

## Current Architecture
The system currently has three main service components:
- **syllabus_server**: Provides `parse_syllabus()` and `answer_syllabus_question()` tools via FastMCP
- **academic_planner**: Provides `create_academic_plan()` and `show_assignment_summary()` tools via FastMCP  
- **productivity_server**: Provides calendar and reminder management tools via FastMCP
- **orchestrator**: Coordinates workflows using the MCP tools

All services currently use FastMCP decorators and run as MCP servers.

## Proposed Architecture
### Service Layer (REST APIs)
Each service becomes an independent FastAPI-based REST service:
- **syllabus-service**: FastAPI app exposing syllabus parsing endpoints
- **academic-planner-service**: FastAPI app exposing academic planning endpoints
- **productivity-service**: FastAPI app exposing calendar/reminder endpoints

### MCP Interface Layer
New MCP wrapper services that maintain the existing tool signatures:
- **mcp/syllabus/mcp_service.py**: MCP tools that make REST calls to syllabus-service
- **mcp/academic_planner/mcp_service.py**: MCP tools that make REST calls to academic-planner-service  
- **mcp/productivity/mcp_service.py**: MCP tools that make REST calls to productivity-service

### Container Infrastructure
Docker containers for each service:
- **syllabus-service**: Container running the syllabus FastAPI service
- **academic-planner-service**: Container running the academic planner FastAPI service
- **productivity-service**: Container running the productivity FastAPI service
- **mcp-gateway**: Container running the MCP interface layer

## Implementation Progress

### ✅ Phase 1: Create REST Service Framework
1. ✅ **Add FastAPI dependencies** to pyproject.toml
2. ✅ **Create service base structure**:
   - ✅ `services/syllabus_service/` directory
   - ✅ `services/academic_planner_service/` directory
   - ✅ `services/productivity_service/` directory
3. ✅ **Create shared models package** (`services/shared/models.py`) to ensure consistent data structures across services

### ✅ Phase 2: Convert Syllabus Server
1. ✅ **Create FastAPI service** (`services/syllabus_service/app.py`):
   - ✅ Extract core logic from `syllabus_server/server.py`
   - ✅ Remove MCP decorators, add FastAPI endpoints:
     - ✅ `POST /syllabus:parse` (accepts `{"pdf_path_or_url": str}`, returns `ParsedSyllabus`)
     - ✅ `POST /syllabus/qa` (accepts `{"syllabus_data": ParsedSyllabus, "question": str}`, returns `{"answer": str}`)
     - ✅ `POST /syllabi/qa` (accepts `{"syllabi_data": list[ParsedSyllabus], "question": str}`, returns `{"answer": str}`)
   - ✅ Add health check endpoint and proper error handling
   - ✅ Handle long-running LLM operations with proper async patterns
2. ✅ **Create MCP wrapper** (`mcp/syllabus/mcp_service.py`):
   - ✅ Implement `parse_syllabus()` and `answer_syllabus_question()` with identical signatures
   - ✅ Use `httpx` to make REST calls to the syllabus service with extended timeouts (5min parse, 2min questions)
   - ✅ Handle serialization/deserialization of `ParsedSyllabus` objects
   - ✅ Proper error handling and timeout management
3. ⏸️ **Create Dockerfile** for syllabus service

**✅ TESTING COMPLETED:**
- ✅ Mock service created for testing without LLM calls
- ✅ Comprehensive test suite validates entire distributed flow
- ✅ All tests passing: HTTP communication, data conversion, MCP interface compatibility
- ✅ Extended timeouts verified (5min parse, 2min questions)
- ✅ Error handling and service communication working correctly

### ✅ Phase 3: Convert Academic Planner Service
1. ✅ **Create FastAPI service** (`services/academic_planner_service/app.py`):
   - ✅ Extract core logic from `academic_planner/server.py`
   - ✅ Add endpoints:
     - ✅ `POST /academics/plan` (accepts `{"syllabi": list[ParsedSyllabus]}`, returns `Plan`)
     - ✅ `POST /academics/assignments` (accepts `{"plan": Plan}`, returns `{"summary": str}`)
   - ✅ Add health check endpoint and proper error handling
   - ✅ Handle long-running LLM operations (5min timeout for plan creation)
2. ✅ **Create MCP wrapper** (`mcp_wrappers/academic_planner/mcp_service.py`):
   - ✅ Implement `create_academic_plan()` and `show_assignment_summary()` with identical signatures
   - ✅ Use `httpx` to make REST calls with extended timeouts (5min create, 30sec summary)
   - ✅ Handle serialization/deserialization of `Plan` objects
   - ✅ Proper error handling and timeout management
3. ⏸️ **Create Dockerfile** for academic planner service

### ✅ Phase 4: Convert Productivity Service
1. ✅ **Create FastAPI service** (`services/productivity_service/app.py`):
   - ✅ Extract core logic from `productivity_server/server.py`
   - ✅ Add endpoints for all calendar and reminder operations (8 total endpoints)
   - ✅ Maintain in-memory storage for fast operations
   - ✅ Add health check endpoint and proper error handling
2. ✅ **Create MCP wrapper** (`mcp_wrappers/productivity/mcp_service.py`):
   - ✅ Implement all 8 MCP tools with identical signatures
   - ✅ Use `httpx` with standard 30-second timeouts (fast operations)
   - ✅ Handle serialization/deserialization of `CalendarEvent` and `Reminder` objects
   - ✅ Proper error handling for HTTP communication
3. ⏸️ **Create Dockerfile** for productivity service

### ✅ Phase 5: Create MCP Gateway
1. ✅ **Create unified MCP server** (`mcp_gateway/server.py`):
   - ✅ Import raw functions from all MCP wrapper modules
   - ✅ Re-register all tools with unified FastMCP instance
   - ✅ Provide single entry point for all 12 MCP tools
   - ✅ Handle service discovery and status reporting
   - ✅ Clean abstraction - orchestrator only needs to import one gateway
2. ⏸️ **Create Dockerfile** for MCP gateway

### ✅ Phase 6: Docker Compose & Configuration
1. ✅ **Create docker-compose.yml**:
   - ✅ Define all 4 services with proper networking (syllabus-network)
   - ✅ Set up environment variables and health checks for all services
   - ✅ Configure service discovery with Docker DNS
   - ✅ Proper startup dependencies (MCP gateway waits for all services)
2. ✅ **Create Dockerfiles**:
   - ✅ One Dockerfile per service (4 total)
   - ✅ Optimized with uv package manager
   - ✅ Non-root user security
   - ✅ Health check integration
3. ✅ **Configuration management**:
   - ✅ Environment-based service URLs via Docker Compose
   - ✅ .env.example template for easy setup
   - ✅ .dockerignore for optimized builds
   - ✅ Comprehensive deployment documentation

### 🔄 Phase 7: Update Orchestrator
1. ⏸️ **Update orchestrator** to use the MCP gateway instead of direct service imports
2. ⏸️ **Test workflow execution** with distributed services
3. ⏸️ **Add resilience patterns** (retries, circuit breakers) if needed

## Key Design Decisions
### Data Serialization
- Use Pydantic models for FastAPI request/response validation
- Convert dataclass models to Pydantic where needed for JSON serialization
- MCP wrappers handle conversion between dataclasses and JSON

### Service Communication
- Use `httpx` for HTTP client calls from MCP wrappers to REST services
- Implement proper error handling and **extended timeouts** for LLM services (syllabus parsing, academic planning)
- Services communicate only through defined REST APIs
- **LLM Service Considerations**:
  - Syllabus parsing can take 30-60 seconds for complex PDFs
  - Academic planning with multiple syllabi can take 1-2 minutes
  - Set HTTP timeouts to 5+ minutes for LLM endpoints
  - Consider async processing patterns for very long operations

### Backward Compatibility
- MCP tool signatures remain identical to current implementation
- Orchestrator requires no changes to its tool usage
- Existing workflows continue to work unchanged

### Service Independence
- Each service manages its own dependencies and models
- Services can be developed, deployed, and scaled independently
- Clear API boundaries between services

## Files to Modify/Create
### New Files
- ✅ `services/syllabus_service/app.py`
- ✅ `services/syllabus_service/mock_app.py` (for testing)
- ✅ `services/academic_planner_service/app.py`
- ✅ `services/productivity_service/app.py`
- ✅ `services/shared/models.py`
- ✅ `mcp_wrappers/syllabus/mcp_service.py` (renamed to avoid conflicts)
- ✅ `test_syllabus_service.py` (comprehensive test suite)
- ✅ `mcp_wrappers/academic_planner/mcp_service.py`
- ✅ `mcp_wrappers/productivity/mcp_service.py`
- ✅ `mcp_gateway/server.py`
- ✅ `docker-compose.yml`
- ✅ `services/syllabus_service/Dockerfile`
- ✅ `services/academic_planner_service/Dockerfile`
- ✅ `services/productivity_service/Dockerfile`
- ✅ `mcp_gateway/Dockerfile`
- ✅ `.dockerignore`
- ✅ `.env.example`
- ✅ `DOCKER_DEPLOYMENT.md`

### Files to Modify
- ✅ `pyproject.toml` - Add FastAPI, httpx dependencies
- Existing server files - Remove MCP decorators, extract business logic

## Legend
- ✅ Complete
- 🔄 In Progress  
- ⏸️ Not Started
- ❌ Blocked/Issues