# -*- coding: utf-8 -*-
from mcp_gateway.server import mcp as gateway_mcp

# Server registry mapping server names to MCP instances
# All services are now unified through the MCP Gateway
SERVER_REGISTRY = {
    "syllabus_server": gateway_mcp,
    "productivity_server": gateway_mcp,
    "academic_planner_server": gateway_mcp,
}

async def list_tool_schemas() -> list[dict]:
    """Collect and return JSON schemas of all available tools from MCP servers."""
    schemas = []

    # Get all tools from the unified MCP gateway
    all_tools = await gateway_mcp.get_tools()
    
    # Map tool names to their originating services for backward compatibility
    tool_service_mapping = {
        # Syllabus server tools
        "parse_syllabus": "syllabus_server",
        "answer_syllabus_question": "syllabus_server",
        # Academic planner tools
        "create_academic_plan": "academic_planner_server",
        "show_assignment_summary": "academic_planner_server",
        # Productivity server tools
        "create_calendar_event": "productivity_server",
        "create_reminder": "productivity_server",
        "create_calendar_events_bulk": "productivity_server",
        "create_reminders_bulk": "productivity_server",
        "list_calendar_events": "productivity_server",
        "list_reminders": "productivity_server",
        "show_calendar_events": "productivity_server",
        "show_reminders": "productivity_server",
        # Gateway tools
        "get_gateway_info": "gateway",
        "list_available_tools": "gateway",
    }
    
    for tool_key, tool in all_tools.items():
        # Determine which server this tool belongs to
        server_name = tool_service_mapping.get(tool_key, "unknown_server")
        
        schemas.append({
            "server": server_name,
            "name": tool_key,
            "title": tool.title or tool_key,
            "description": tool.description or "",
            "inputSchema": tool.parameters or {},
            "outputSchema": tool.output_schema or {},
        })

    return schemas
