import os
import asyncio
import pytest

from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport

skip_reason = "Set RUN_MCP_INTEGRATION=1 to run MCP integration tests (requires services running)"
run_integration = os.getenv("RUN_MCP_INTEGRATION") == "1"


@pytest.mark.skipif(not run_integration, reason=skip_reason)
@pytest.mark.asyncio
async def test_gateway_lists_tools():
    gateway_host = os.getenv("GATEWAY_MCP_HOST", "localhost")
    gateway_port = int(os.getenv("GATEWAY_MCP_PORT", "8600"))
    gateway_url = f"http://{gateway_host}:{gateway_port}/mcp"
    client = Client(StreamableHttpTransport(gateway_url))
    tools = await client.list_tools()
    assert any("structure_syllabus" in t.name for t in tools)

