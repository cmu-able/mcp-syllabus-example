"""Sampling handler for MCP clients.

This module provides OpenAI-based sampling capabilities to MCP servers.
When MCP servers call ctx.sample(), the client uses this handler to make
LLM requests on their behalf.
"""
import typing as t
import os

from openai import AsyncOpenAI
import mcp.types as mcp_types


# Global OpenAI client
_openai_client: t.Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create the OpenAI client for sampling."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not set")
        _openai_client = AsyncOpenAI(api_key=api_key)
    return _openai_client


async def openai_sampling_handler(
    messages: list[mcp_types.SamplingMessage],
    params: mcp_types.CreateMessageRequestParams,
    context: t.Any,
) -> str | mcp_types.CreateMessageResult:
    """Handle sampling requests from MCP servers using OpenAI.
    
    This function is called when an MCP server uses ctx.sample() to request
    LLM completion. The orchestrator client provides the LLM capability.
    
    Args:
        messages: List of messages in MCP format
        params: Sampling parameters (temperature, max_tokens, etc.)
        context: Request context from MCP
        
    Returns:
        The LLM response text or CreateMessageResult
    """
    client = get_openai_client()
    
    # Convert MCP messages to OpenAI format
    openai_messages = []
    for msg in messages:
        # Handle different message content formats
        if hasattr(msg, "content"):
            content = msg.content
            if hasattr(content, "text"):
                content_str = content.text
            elif hasattr(content, "data"):
                content_str = content.data
            else:
                content_str = str(content)
        else:
            content_str = str(msg)
        
        # Get role, handling both attribute and dict access
        role = getattr(msg, "role", "user")
        
        openai_messages.append({
            "role": role,
            "content": content_str,
        })
    
    # Extract parameters with safe attribute access
    model = "gpt-4o"  # Default model
    
    # Try to get model from params
    if hasattr(params, "modelPreferences"):
        model_prefs = params.modelPreferences
        if isinstance(model_prefs, str):
            model = model_prefs
        elif hasattr(model_prefs, "hints") and model_prefs.hints:
            if isinstance(model_prefs.hints, list) and len(model_prefs.hints) > 0:
                hint = model_prefs.hints[0]
                if isinstance(hint, dict) and "name" in hint:
                    model = hint["name"]
                elif hasattr(hint, "name"):
                    model = hint.name
    
    temperature = getattr(params, "temperature", 0.7)
    max_tokens = getattr(params, "maxTokens", 1000)
    
    # Call OpenAI with appropriate parameters for the model
    call_params = {
        "model": model,
        "messages": openai_messages,
    }
    
    # Newer reasoning models (o1, o3, gpt-5) don't support temperature or max_tokens
    is_reasoning_model = any(x in model for x in ["o1", "o3", "gpt-5"])
    
    if not is_reasoning_model:
        call_params["temperature"] = temperature
        # Only set max_tokens for non-reasoning models
        call_params["max_tokens"] = max_tokens
    # For reasoning models, omit token limits to use model defaults
    # This allows the model to use as many tokens as needed for reasoning + output
    elif "gpt-4o" in model:
        call_params["max_completion_tokens"] = max_tokens
    
    response = await client.chat.completions.create(**call_params)
    
    # Extract content from response
    choice = response.choices[0]
    message = choice.message
    
    # Reasoning models may have content in different fields
    content = message.content or ""
    
    # If content is empty, check for reasoning-specific fields
    if not content and hasattr(choice, "message"):
        if hasattr(message, "reasoning"):
            content = message.reasoning or ""
        elif hasattr(message, "text"):
            content = message.text or ""
    
    # Debug: log response details if content is still empty
    if not content:
        print(f"WARNING: Empty response from OpenAI.")
        print(f"Model: {model}")
        print(f"Message attrs: {dir(message)}")
        print(f"Message content: {message.content}")
        if hasattr(message, "reasoning"):
            print(f"Message reasoning: {message.reasoning}")
        print(f"Full response: {response}")
    
    return content
