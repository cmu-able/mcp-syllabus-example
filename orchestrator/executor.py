"""Execution engine for orchestrator plans.

This module handles the execution of execution plans, including dependency resolution,
variable substitution, and tool invocation.
"""
import asyncio
import base64
import json
from enum import Enum
from pathlib import Path
import typing as t

from pydantic import BaseModel

from orchestrator.models import ExecutionPlan, ExecutionStep

class ExecutionState(Enum):
    """State of execution for a plan or step."""
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def _extract_mcp_result(call_result: t.Any) -> t.Any:
    """Extract content from MCP CallToolResult.
    
    MCP returns results wrapped in CallToolResult with content as TextContent objects.
    This function extracts and parses the actual result.
    
    Args:
        call_result: The CallToolResult from MCP client
        
    Returns:
        Parsed result (dict, str, or original if parsing fails)
    """
    # Extract content from CallToolResult
    if hasattr(call_result, "content") and call_result.content:
        # result.content is a list of TextContent objects
        if isinstance(call_result.content, list) and len(call_result.content) > 0:
            content = call_result.content[0]
            if hasattr(content, "text"):
                # Try to parse as JSON (for structured returns)
                try:
                    return json.loads(content.text)
                except (json.JSONDecodeError, AttributeError):
                    # Return as string if not JSON
                    return content.text
    
    # Return as-is if we can't extract
    return call_result


def _serialize_value(value: t.Any) -> t.Any:
    """Recursively serialize Pydantic models and other complex types.
    
    Args:
        value: Value to serialize
        
    Returns:
        Serialized value (dicts for Pydantic models, unchanged for primitives)
    """
    if isinstance(value, BaseModel):
        return value.model_dump()
    elif isinstance(value, list):
        return [_serialize_value(item) for item in value]
    elif isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    else:
        return value


def _preprocess_pdf_arguments(arguments: dict[str, t.Any]) -> dict[str, t.Any]:
    """Preprocess arguments for MCP tool calls.
    
    This function:
    1. Converts local PDF paths to base64
    2. Serializes Pydantic models to dicts
    
    Args:
        arguments: Tool arguments that may contain PDF paths or Pydantic models
        
    Returns:
        Modified arguments ready for MCP transmission
    """
    arguments = arguments.copy()
    
    # Handle PDF path conversion
    if "pdf_path_or_url" in arguments:
        pdf_path = arguments["pdf_path_or_url"]
        
        # Check if it's a local file path (not a URL)
        if pdf_path and not pdf_path.startswith(("http://", "https://")):
            path = Path(pdf_path)
            if path.exists() and path.is_file():
                # Read and encode the file
                pdf_content = path.read_bytes()
                encoded_content = base64.b64encode(pdf_content).decode("utf-8")
                
                # Replace pdf_path_or_url with pdf_content_base64
                arguments["pdf_content_base64"] = encoded_content
                arguments["pdf_path_or_url"] = None
    
    # Serialize Pydantic models and other complex types
    for key, value in arguments.items():
        arguments[key] = _serialize_value(value)
    
    return arguments

async def execute_plan(
    plan: ExecutionPlan,
    progress_callback: t.Optional[t.Callable[[int, int, ExecutionStep, t.Optional[t.Any]], None]] = None,
    max_concurrent: t.Optional[int] = None
) -> dict[str, t.Any]:
    """Execute an execution plan and return the results.
    
    Steps with satisfied dependencies are executed in parallel batches.
    
    Args:
        plan: The execution plan to execute
        progress_callback: Optional callback function called before and after executing each step.
                          Called with (current_step_num, total_steps, step, result).
                          - Before execution: result is None
                          - After execution: result contains the step's output
        max_concurrent: Optional limit on number of steps to execute concurrently.
                       If None (default), all ready steps execute in parallel.
        
    Returns:
        Dictionary mapping step IDs to their results
        
    Raises:
        RuntimeError: If a step fails or a tool is not found
    """
    from registry import SERVER_REGISTRY
    
    # Store results by step ID
    results: dict[str, t.Any] = {}
    
    # Track completed steps
    completed: set[str] = set()
    
    # Create semaphore for concurrency limiting if specified
    semaphore = asyncio.Semaphore(max_concurrent) if max_concurrent else None
    
    # Execute steps in dependency order, with parallelism
    while len(completed) < len(plan.steps):
        # Find ALL steps that can be executed (all dependencies completed)
        executable_steps: list[ExecutionStep] = []
        for step in plan.steps:
            if step.id in completed:
                continue
            
            # Check if all dependencies are completed
            if all(dep in completed for dep in step.depends_on):
                executable_steps.append(step)
        
        if not executable_steps:
            # No executable steps found - circular dependency or missing step
            remaining = [s.id for s in plan.steps if s.id not in completed]
            raise RuntimeError(
                f"Cannot execute plan: circular dependency or missing steps. "
                f"Remaining steps: {remaining}"
            )
        
        # Execute all ready steps in parallel
        tasks = []
        for i, step in enumerate(executable_steps):
            # Assign unique step numbers to parallel tasks
            step_number = len(completed) + i + 1
            task = _execute_step(
                step=step,
                results=results,
                progress_callback=progress_callback,
                total_steps=len(plan.steps),
                step_number=step_number,
                semaphore=semaphore
            )
            tasks.append(task)
        
        # Wait for all tasks in this batch to complete
        step_results = await asyncio.gather(*tasks)
        
        # Update results and completed set
        for step, result in zip(executable_steps, step_results):
            results[step.id] = result
            completed.add(step.id)
            
            # Report step completion if callback provided
            if progress_callback:
                progress_callback(len(completed), len(plan.steps), step, result)
    
    return results


async def _execute_step(
    step: ExecutionStep,
    results: dict[str, t.Any],
    progress_callback: t.Optional[t.Callable[[int, int, ExecutionStep, t.Optional[t.Any]], None]],
    total_steps: int,
    step_number: int,
    semaphore: t.Optional[asyncio.Semaphore]
) -> t.Any:
    """Execute a single step, potentially in parallel with other steps.
    
    Args:
        step: The step to execute
        results: Dictionary of completed step results (for dependency resolution)
        progress_callback: Optional callback for progress reporting
        total_steps: Total number of steps in the plan
        step_number: The step number to display (1-indexed)
        semaphore: Optional semaphore for concurrency limiting
        
    Returns:
        The result of executing the step
        
    Raises:
        RuntimeError: If the server/tool is not found or execution fails
    """
    from registry import SERVER_REGISTRY
    
    # Acquire semaphore if concurrency limiting is enabled
    if semaphore:
        await semaphore.acquire()
    
    try:
        # Report step start if callback provided
        if progress_callback:
            progress_callback(step_number, total_steps, step, None)
        
        # Resolve arguments (substitute variable references)
        resolved_args = _resolve_arguments(step.arguments, results)
        
        # Preprocess arguments (e.g., convert local PDF paths to base64)
        resolved_args = _preprocess_pdf_arguments(resolved_args)
        
        # Get the MCP client for this service
        mcp_client = SERVER_REGISTRY.get(step.service_name)
        if mcp_client is None:
            raise RuntimeError(
                f"Server not found: {step.service_name}. "
                f"Available servers: {list(SERVER_REGISTRY.keys())}"
            )
        
        # Call the tool via MCP protocol
        try:
            # Connect to the MCP server and call the tool
            async with mcp_client:
                call_result = await mcp_client.call_tool(step.tool_name, resolved_args)
                
                # Extract content from CallToolResult
                result = _extract_mcp_result(call_result)
                
                return result
            
        except Exception as e:
            raise RuntimeError(
                f"Error executing step '{step.id}' "
                f"({step.service_name}:{step.tool_name}): {e}"
            ) from e
    finally:
        # Release semaphore if we acquired it
        if semaphore:
            semaphore.release()


def _resolve_arguments(
    arguments: dict[str, t.Any],
    results: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Resolve variable references in arguments.
    
    Supports:
    - $stepX - entire step output
    - $stepX.field - specific field from step output
    - $stepX.field.nested - nested field access
    
    Args:
        arguments: The arguments dictionary potentially containing variable references
        results: The results from completed steps
        
    Returns:
        Dictionary with all variable references resolved
    """
    resolved = {}
    
    for key, value in arguments.items():
        if isinstance(value, str) and value.startswith("$"):
            # Variable reference
            resolved[key] = _resolve_variable(value, results)
        elif isinstance(value, list):
            # Handle lists (might contain variable references)
            resolved[key] = [
                _resolve_variable(item, results) if isinstance(item, str) and item.startswith("$")
                else item
                for item in value
            ]
        else:
            resolved[key] = value
    
    return resolved


def _resolve_variable(var_ref: str, results: dict[str, t.Any]) -> t.Any:
    """Resolve a single variable reference.
    
    Args:
        var_ref: Variable reference like "$step1" or "$step1.field"
        results: The results from completed steps
        
    Returns:
        The resolved value
        
    Raises:
        KeyError: If the variable reference is invalid
    """
    # Remove the $ prefix
    var_path = var_ref[1:]
    
    # Split on dots to handle nested access
    parts = var_path.split(".")
    step_id = parts[0]
    
    if step_id not in results:
        raise KeyError(f"Step '{step_id}' not found in results")
    
    # Start with the step result
    value = results[step_id]
    # Navigate nested fields
    for field in parts[1:]:
        if isinstance(value, dict):
            if field not in value:
                raise KeyError(f"Field '{field}' not found in step '{step_id}' result")
            value = value[field]
        elif hasattr(value, "__dataclass_fields__"):
            # Handle dataclass objects
            if not hasattr(value, field):
                raise KeyError(f"Field '{field}' not found in step '{step_id}' result")
            value = getattr(value, field)
        elif isinstance(value, BaseModel):
            model_dict = value.model_dump()
            if field not in model_dict:
                raise KeyError(f"Field '{field}' not found in step '{step_id}' result")
            value = model_dict[field]
        elif hasattr(value, field):
            value = getattr(value, field)
        else:
            raise TypeError(
                f"Cannot access field '{field}' on value of type '{type(value).__name__}' from step '{step_id}'"
            )
    
    return value
