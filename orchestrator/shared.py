"""Shared utilities for orchestrator modules.

This module contains common functionality used by both run.py and run_agent.py
to avoid code duplication.
"""
import asyncio
import os
import typing as t
from openai import OpenAI
from registry import list_tool_schemas
from mcp_gateway.server import mcp as gateway_mcp


def get_openai_client() -> OpenAI:
    """Get OpenAI client with API key."""
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def list_available_tools() -> list[dict]:
    """List all available tools from the registry."""
    return await list_tool_schemas()


# Async wrappers for MCP Gateway functions
async def _get_mcp_function(function_name: str):
    """Get a function from the MCP Gateway."""
    tools = await gateway_mcp.get_tools()
    tool = tools.get(function_name)
    if not tool:
        raise RuntimeError(f"Function '{function_name}' not found in MCP Gateway")
    return tool.fn


async def parse_syllabus_async(pdf_path: str) -> dict:
    """Parse a syllabus PDF using MCP Gateway."""
    func = await _get_mcp_function("parse_syllabus")
    return await asyncio.to_thread(func, pdf_path)


async def create_calendar_event_async(**kwargs) -> dict:
    """Create a calendar event using MCP Gateway."""
    func = await _get_mcp_function("create_calendar_event")
    return await asyncio.to_thread(func, **kwargs)


async def create_reminder_async(**kwargs) -> dict:
    """Create a reminder using MCP Gateway."""
    func = await _get_mcp_function("create_reminder")
    return await asyncio.to_thread(func, **kwargs)


async def get_calendar_events_async() -> list:
    """Get calendar events using MCP Gateway."""
    func = await _get_mcp_function("list_calendar_events")
    return await asyncio.to_thread(func)


async def get_reminders_async() -> list:
    """Get reminders using MCP Gateway."""
    func = await _get_mcp_function("list_reminders")
    return await asyncio.to_thread(func)