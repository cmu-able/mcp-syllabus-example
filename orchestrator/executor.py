"""Execution engine for orchestrator plans.

This module handles the execution of execution plans, including dependency resolution,
variable substitution, and tool invocation.
"""
import typing as t
from enum import Enum

from orchestrator.models import ExecutionPlan, ExecutionStep

class ExecutionState(Enum):
    """State of execution for a plan or step."""
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

async def execute_plan(
    plan: ExecutionPlan,
    progress_callback: t.Optional[t.Callable[[int, int, ExecutionStep, t.Optional[t.Any]], None]] = None
) -> dict[str, t.Any]:
    """Execute an execution plan and return the results.
    
    Args:
        plan: The execution plan to execute
        progress_callback: Optional callback function called before and after executing each step.
                          Called with (current_step_num, total_steps, step, result).
                          - Before execution: result is None
                          - After execution: result contains the step's output
        
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
    
    # Execute steps in dependency order
    while len(completed) < len(plan.steps):
        # Find a step that can be executed (all dependencies completed)
        executable_step = None
        for step in plan.steps:
            if step.id in completed:
                continue
            
            # Check if all dependencies are completed
            if all(dep in completed for dep in step.depends_on):
                executable_step = step
                break
        
        if executable_step is None:
            # No executable step found - circular dependency or missing step
            remaining = [s.id for s in plan.steps if s.id not in completed]
            raise RuntimeError(
                f"Cannot execute plan: circular dependency or missing steps. "
                f"Remaining steps: {remaining}"
            )
        
        # Report step start if callback provided
        current_step_num = len(completed) + 1
        if progress_callback:
            progress_callback(current_step_num, len(plan.steps), executable_step, None)
        
        # Resolve arguments (substitute variable references)
        resolved_args = _resolve_arguments(executable_step.arguments, results)
        
        # Get the MCP server
        mcp_server = SERVER_REGISTRY.get(executable_step.service_name)
        if mcp_server is None:
            raise RuntimeError(
                f"Server not found: {executable_step.service_name}. "
                f"Available servers: {list(SERVER_REGISTRY.keys())}"
            )
        
        # Get the tool from the MCP server
        tools = await mcp_server.get_tools()
        tool_func = tools.get(executable_step.tool_name)
        
        if tool_func is None:
            raise RuntimeError(
                f"Tool '{executable_step.tool_name}' not found in server '{executable_step.service_name}'. "
                f"Available tools: {list(tools.keys())}"
            )
        
        # Execute the tool
        # FastMCP wraps functions in FunctionTool objects, so we need to access the underlying function
        try:
            # All tools are wrapped by @mcp.tool(), so access the .fn attribute
            actual_func = tool_func.fn
            result = actual_func(**resolved_args)
            
            # Store the result as-is to preserve dataclass objects
            results[executable_step.id] = result
            completed.add(executable_step.id)
            
            # Report step completion if callback provided
            if progress_callback:
                progress_callback(current_step_num, len(plan.steps), executable_step, result)

            # Report the result
            if progress_callback:
                progress_callback(
                    ExecutionState.COMPLETED,
                    len(completed),
                    len(plan.steps),
                    executable_step
                )
            
        except Exception as e:
            raise RuntimeError(
                f"Error executing step '{executable_step.id}' "
                f"({executable_step.service_name}:{executable_step.tool_name}): {e}"
            ) from e
    
    return results


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
        else:
            raise TypeError(
                f"Cannot access field '{field}' on non-dict/non-dataclass value from step '{step_id}'"
            )
    
    return value
