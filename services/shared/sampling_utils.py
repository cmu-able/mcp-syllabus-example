"""Utilities for working with MCP sampling results.

This module provides common functions for extracting content from
MCP sampling responses across different service implementations.
"""
import typing as t


def extract_sampling_content(sample_result: t.Any, operation_name: str = "operation") -> str:
    """Extract text content from an MCP sampling result.
    
    MCP sampling can return either a string directly or a CreateMessageResult
    containing TextContent. This function handles both cases.
    
    Args:
        sample_result: The result from ctx.sample()
        operation_name: Name of the operation for error messages
        
    Returns:
        The extracted text content
        
    Raises:
        RuntimeError: If content extraction fails or returns empty content
    """
    content: str | None = None
    
    # Handle direct string response
    if isinstance(sample_result, str):
        content = sample_result
    # Handle TextContent object directly (has .text attribute)
    elif hasattr(sample_result, "text"):
        content = sample_result.text
    # Handle CreateMessageResult with TextContent
    elif hasattr(sample_result, "content"):
        text_content = sample_result.content
        if hasattr(text_content, "text"):
            content = text_content.text
        else:
            content = str(text_content)
    # Fallback to string conversion
    else:
        content = str(sample_result)
    
    # Validate we got non-empty content
    if not content or not str(content).strip():
        raise RuntimeError(
            f"Sampling produced empty content for {operation_name}. "
            f"Result type: {type(sample_result)}, Result: {sample_result}"
        )
    
    return content
