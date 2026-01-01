"""Shared utilities for orchestrator modules.

This module contains common functionality used by the orchestrator.
"""
import os
from openai import OpenAI
from dotenv import load_dotenv
from registry import list_tool_schemas

# Load environment variables from .env file
load_dotenv()


def get_openai_client() -> OpenAI:
    """Get OpenAI client with API key."""
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def list_available_tools() -> list[dict]:
    """List all available tools from the registry."""
    return await list_tool_schemas()
