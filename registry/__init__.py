# -*- coding: utf-8 -*-
import importlib
import pkgutil

import mcp_wrappers


def _load_servers_from_pkg(pkg=mcp_wrappers) -> dict[str, object]:
    """Dynamically load all MCP instances exposed under mcp_wrappers.*."""
    registry: dict[str, object] = {}
    for info in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        mod = importlib.import_module(info.name)
        if hasattr(mod, "mcp"):
            server_name = f"{info.name.rsplit('.', 1)[-1]}_server"
            registry[server_name] = getattr(mod, "mcp")
    return registry


# Server registry mapping server names to MCP instances (dynamic)
SERVER_REGISTRY = _load_servers_from_pkg()

async def list_tool_schemas() -> list[dict]:
    """Collect and return JSON schemas of all available tools from MCP servers."""
    schemas = []

    # Collect tools from each server instance
    for server_name, mcp in SERVER_REGISTRY.items():
        tools = await mcp.get_tools()
        for tool_key, tool in tools.items():
            schemas.append({
                "server": server_name,
                "name": tool_key,
                "title": tool.title or tool_key,
                "description": tool.description or "",
                "inputSchema": tool.parameters or {},
                "outputSchema": tool.output_schema or {},
            })

    return schemas
