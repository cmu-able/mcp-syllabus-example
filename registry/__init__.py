# -*- coding: utf-8 -*-
"""Registry for distributed MCP services.

This module manages connections to remote MCP servers and provides
a unified interface for the orchestrator to discover and call tools.
"""
import os
import typing as t

from dotenv import load_dotenv
from fastmcp.client import Client
from fastmcp.client.sampling import create_sampling_callback
from fastmcp.client.transports import StreamableHttpTransport

# Load environment variables
load_dotenv()

# Import sampling handler
from orchestrator.sampling import openai_sampling_handler

# Configuration: service name -> MCP endpoint URL
MCP_SERVICES = {
    "syllabus_server": os.getenv("SYLLABUS_SERVICE_URL", "http://localhost:8601") + "/mcp",
    "academic_planner_server": os.getenv("ACADEMIC_PLANNER_SERVICE_URL", "http://localhost:8602") + "/mcp",
    "productivity_server": os.getenv("PRODUCTIVITY_SERVICE_URL", "http://localhost:8603") + "/mcp",
}

# Global client instances (created lazily on first use)
_mcp_clients: dict[str, Client] = {}


def get_mcp_client(service_name: str) -> Client:
    """Get or create MCP client for a service.
    
    Clients are created with sampling support, allowing MCP servers to use
    ctx.sample() for LLM requests.
    
    Args:
        service_name: Name of the service (e.g., 'syllabus_server')
        
    Returns:
        MCP Client instance for the service with sampling enabled
        
    Raises:
        KeyError: If service_name is not in MCP_SERVICES
    """
    if service_name not in _mcp_clients:
        if service_name not in MCP_SERVICES:
            raise KeyError(f"Unknown service: {service_name}. Available: {list(MCP_SERVICES.keys())}")
        
        url = MCP_SERVICES[service_name]
        transport = StreamableHttpTransport(url)
        
        # Create client with sampling support
        # Pass the handler directly - FastMCP will handle the callback wrapping
        _mcp_clients[service_name] = Client(
            transport,
            sampling_handler=openai_sampling_handler
        )
    
    return _mcp_clients[service_name]


# SERVER_REGISTRY maps service names to MCP clients
# This maintains compatibility with existing executor code
SERVER_REGISTRY: dict[str, Client] = {
    name: get_mcp_client(name) for name in MCP_SERVICES
}


async def list_tool_schemas() -> list[dict]:
    """Collect and return JSON schemas of all available tools from MCP servers.
    
    This queries each MCP server to discover available tools and their schemas.
    
    Returns:
        List of tool schema dictionaries with keys: server, name, title, 
        description, inputSchema, outputSchema
    """
    schemas = []

    # Collect tools from each MCP server
    for server_name, client in SERVER_REGISTRY.items():
        # Connect to the server to query tools
        async with client:
            tools = await client.list_tools()
            
            for tool in tools:
                schemas.append({
                    "server": server_name,
                    "name": tool.name,
                    "title": tool.name,  # MCP tools use 'name' field
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema or {},
                    "outputSchema": {},  # MCP protocol doesn't expose output schema
                })

    return schemas
