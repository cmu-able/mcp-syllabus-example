# -*- coding: utf-8 -*-
from productivity_server.server import mcp as productivity_mcp
from syllabus_server.server import mcp as syllabus_mcp
from academic_planner.server import mcp as academic_planner_mcp

# Server registry mapping server names to MCP instances
SERVER_REGISTRY = {
    "syllabus_server": syllabus_mcp,
    "productivity_server": productivity_mcp,
    "academic_planner_server": academic_planner_mcp,
}

async def list_tool_schemas() -> list[dict]:
    """Collect and return JSON schemas of all available tools from MCP servers."""
    schemas = []

    # Get schemas from syllabus server
    syllabus_tools = await syllabus_mcp.get_tools()
    for tool_key, tool in syllabus_tools.items():
        schemas.append({
            "server": "syllabus_server",
            "name": tool_key,
            "title": tool.title or tool_key,
            "description": tool.description or "",
            "inputSchema": tool.parameters or {},
            "outputSchema": tool.output_schema or {},
        })

    # Get schemas from productivity server
    productivity_tools = await productivity_mcp.get_tools()
    for tool_key, tool in productivity_tools.items():
        schemas.append({
            "server": "productivity_server",
            "name": tool_key,
            "title": tool.title or tool_key,
            "description": tool.description or "",
            "inputSchema": tool.parameters or {},
            "outputSchema": tool.output_schema or {},
        })
    # Get schemas from academic planner server
    academic_planner_tools = await academic_planner_mcp.get_tools()
    for tool_key, tool in academic_planner_tools.items():
        schemas.append({
            "server": "academic_planner_server",
            "name": tool_key,
            "title": tool.title or tool_key,
            "description": tool.description or "",
            "inputSchema": tool.parameters or {},
            "outputSchema": tool.output_schema or {},
        })

    return schemas
