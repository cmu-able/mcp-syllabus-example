"""Execution engine for orchestrator plans.

This module handles the execution of execution plans, including dependency resolution,
variable substitution, and tool invocation.
"""
import typing as t
from dataclasses import asdict

from orchestrator.models import ExecutionPlan, ExecutionStep


async def execute_plan(plan: ExecutionPlan) -> dict[str, t.Any]:
    """Execute an execution plan and return the results.
    
    Args:
        plan: The execution plan to execute
        
    Returns:
        Dictionary mapping step IDs to their results
        
    Raises:
        RuntimeError: If a step fails or a tool is not found
    """
    from syllabus_server.server import parse_syllabus
    from productivity_server.server import (
        create_calendar_event,
        create_reminder,
        create_calendar_events_bulk,
        create_reminders_bulk,
    )
    from academic_planner.server import create_academic_plan
    
    # Map service.tool to actual function
    tool_registry = {
        "syllabus_server.parse_syllabus": parse_syllabus,
        "productivity_server.create_calendar_event": create_calendar_event,
        "productivity_server.create_reminder": create_reminder,
        "productivity_server.create_calendar_events_bulk": create_calendar_events_bulk,
        "productivity_server.create_reminders_bulk": create_reminders_bulk,
        "academic_planner_server.create_academic_plan": create_academic_plan,
    }
    
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
        
        # Resolve arguments (substitute variable references)
        resolved_args = _resolve_arguments(executable_step.arguments, results)
        
        # Get the tool function
        tool_key = f"{executable_step.service_name}.{executable_step.tool_name}"
        tool_func = tool_registry.get(tool_key)
        
        if tool_func is None:
            raise RuntimeError(
                f"Tool not found: {tool_key}. "
                f"Available tools: {list(tool_registry.keys())}"
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
            
        except Exception as e:
            raise RuntimeError(
                f"Error executing step '{executable_step.id}' "
                f"({tool_key}): {e}"
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
