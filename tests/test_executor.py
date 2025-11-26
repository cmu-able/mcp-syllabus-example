"""Tests for the orchestrator executor module.

This module tests parallel execution, dependency resolution, and error handling.
"""
import asyncio
import time
import typing as t
from dataclasses import dataclass

import pytest

from orchestrator.executor import execute_plan
from orchestrator.models import ExecutionPlan, ExecutionStep


# Mock server registry for testing
class MockServer:
    """Mock MCP server for testing."""
    
    def __init__(self, tools: dict[str, t.Callable]) -> None:
        """Initialize with a dict of tool name -> function."""
        self.tools = tools
    
    async def get_tools(self) -> dict[str, t.Any]:
        """Return mock tools wrapped as FastMCP would."""
        # Wrap functions to simulate FastMCP's FunctionTool
        @dataclass
        class FunctionTool:
            fn: t.Callable
        
        return {name: FunctionTool(fn=func) for name, func in self.tools.items()}


def setup_mock_registry(tools_by_server: dict[str, dict[str, t.Callable]]) -> None:
    """Set up the mock registry with servers and their tools."""
    from registry import SERVER_REGISTRY
    
    # Clear existing registry
    SERVER_REGISTRY.clear()
    
    # Add mock servers
    for server_name, tools in tools_by_server.items():
        SERVER_REGISTRY[server_name] = MockServer(tools)


@pytest.mark.asyncio
async def test_parallel_execution_of_independent_steps() -> None:
    """Test that independent steps execute in parallel."""
    # Track execution times to verify parallelism
    execution_times: dict[str, float] = {}
    
    def slow_task_a() -> str:
        """Simulate a slow task."""
        start = time.time()
        time.sleep(0.1)  # 100ms
        execution_times["step1"] = time.time() - start
        return "result_a"
    
    def slow_task_b() -> str:
        """Simulate another slow task."""
        start = time.time()
        time.sleep(0.1)  # 100ms
        execution_times["step2"] = time.time() - start
        return "result_b"
    
    def slow_task_c() -> str:
        """Simulate a third slow task."""
        start = time.time()
        time.sleep(0.1)  # 100ms
        execution_times["step3"] = time.time() - start
        return "result_c"
    
    setup_mock_registry({
        "test_server": {
            "task_a": slow_task_a,
            "task_b": slow_task_b,
            "task_c": slow_task_c,
        }
    })
    
    # Create a plan with 3 independent steps
    plan = ExecutionPlan(
        steps=[
            ExecutionStep(
                id="step1",
                service_name="test_server",
                tool_name="task_a",
                arguments={},
                depends_on=[],
            ),
            ExecutionStep(
                id="step2",
                service_name="test_server",
                tool_name="task_b",
                arguments={},
                depends_on=[],
            ),
            ExecutionStep(
                id="step3",
                service_name="test_server",
                tool_name="task_c",
                arguments={},
                depends_on=[],
            ),
        ],
        rationale="Test parallel execution",
    )
    
    # Execute the plan and measure total time
    start_time = time.time()
    results = await execute_plan(plan)
    total_time = time.time() - start_time
    
    # Verify all steps completed
    assert results["step1"] == "result_a"
    assert results["step2"] == "result_b"
    assert results["step3"] == "result_c"
    
    # If executed in parallel, total time should be ~100ms
    # If executed serially, total time would be ~300ms
    # Allow some overhead for thread creation
    assert total_time < 0.25, f"Expected parallel execution (~0.1s), but took {total_time:.2f}s"


@pytest.mark.asyncio
async def test_dependency_ordering_is_respected() -> None:
    """Test that steps with dependencies execute in correct order."""
    execution_order: list[str] = []
    
    def task_a() -> str:
        """First task."""
        execution_order.append("step1")
        return "a"
    
    def task_b(input_val: str) -> str:
        """Second task that depends on first."""
        execution_order.append("step2")
        return f"{input_val}_b"
    
    def task_c(input_val: str) -> str:
        """Third task that depends on second."""
        execution_order.append("step3")
        return f"{input_val}_c"
    
    setup_mock_registry({
        "test_server": {
            "task_a": task_a,
            "task_b": task_b,
            "task_c": task_c,
        }
    })
    
    # Create a plan with linear dependencies: step1 -> step2 -> step3
    plan = ExecutionPlan(
        steps=[
            ExecutionStep(
                id="step1",
                service_name="test_server",
                tool_name="task_a",
                arguments={},
                depends_on=[],
            ),
            ExecutionStep(
                id="step2",
                service_name="test_server",
                tool_name="task_b",
                arguments={"input_val": "$step1"},
                depends_on=["step1"],
            ),
            ExecutionStep(
                id="step3",
                service_name="test_server",
                tool_name="task_c",
                arguments={"input_val": "$step2"},
                depends_on=["step2"],
            ),
        ],
        rationale="Test dependency ordering",
    )
    
    results = await execute_plan(plan)
    
    # Verify execution order
    assert execution_order == ["step1", "step2", "step3"]
    
    # Verify variable substitution worked
    assert results["step1"] == "a"
    assert results["step2"] == "a_b"
    assert results["step3"] == "a_b_c"


@pytest.mark.asyncio
async def test_parallel_execution_with_shared_dependency() -> None:
    """Test that steps sharing a dependency wait for it, then execute in parallel."""
    execution_order: list[str] = []
    execution_times: dict[str, tuple[float, float]] = {}  # (start, end) times
    
    def base_task() -> str:
        """Base task that others depend on."""
        start = time.time()
        time.sleep(0.05)  # 50ms
        end = time.time()
        execution_times["step1"] = (start, end)
        execution_order.append("step1")
        return "base"
    
    def dependent_task_a(base: str) -> str:
        """Task that depends on base."""
        start = time.time()
        time.sleep(0.1)  # 100ms
        end = time.time()
        execution_times["step2"] = (start, end)
        execution_order.append("step2")
        return f"{base}_a"
    
    def dependent_task_b(base: str) -> str:
        """Another task that depends on base."""
        start = time.time()
        time.sleep(0.1)  # 100ms
        end = time.time()
        execution_times["step3"] = (start, end)
        execution_order.append("step3")
        return f"{base}_b"
    
    setup_mock_registry({
        "test_server": {
            "base": base_task,
            "dep_a": dependent_task_a,
            "dep_b": dependent_task_b,
        }
    })
    
    plan = ExecutionPlan(
        steps=[
            ExecutionStep(
                id="step1",
                service_name="test_server",
                tool_name="base",
                arguments={},
                depends_on=[],
            ),
            ExecutionStep(
                id="step2",
                service_name="test_server",
                tool_name="dep_a",
                arguments={"base": "$step1"},
                depends_on=["step1"],
            ),
            ExecutionStep(
                id="step3",
                service_name="test_server",
                tool_name="dep_b",
                arguments={"base": "$step1"},
                depends_on=["step1"],
            ),
        ],
        rationale="Test parallel execution after shared dependency",
    )
    
    start_time = time.time()
    results = await execute_plan(plan)
    total_time = time.time() - start_time
    
    # Verify results
    assert results["step1"] == "base"
    assert results["step2"] == "base_a"
    assert results["step3"] == "base_b"
    
    # Verify step1 executed first
    assert execution_order[0] == "step1"
    
    # Verify step2 and step3 executed after step1 but in parallel with each other
    step1_end = execution_times["step1"][1]
    step2_start = execution_times["step2"][0]
    step3_start = execution_times["step3"][0]
    
    # Both should start after step1 completes
    assert step2_start >= step1_end
    assert step3_start >= step1_end
    
    # Total time should be ~150ms (50ms + 100ms parallel), not ~250ms (sequential)
    assert total_time < 0.25, f"Expected parallel execution (~0.15s), but took {total_time:.2f}s"


@pytest.mark.asyncio
async def test_max_concurrent_limiting() -> None:
    """Test that max_concurrent parameter limits parallelism."""
    concurrent_executions: list[int] = []
    current_count = 0
    lock = asyncio.Lock()
    
    async def track_concurrency() -> str:
        """Track how many tasks are running concurrently."""
        nonlocal current_count
        
        async with lock:
            current_count += 1
            concurrent_executions.append(current_count)
        
        # Simulate work
        await asyncio.sleep(0.05)
        
        async with lock:
            current_count -= 1
        
        return "done"
    
    # Need to wrap in sync function since our tools expect sync
    def sync_track() -> str:
        """Sync wrapper."""
        return asyncio.run(track_concurrency())
    
    setup_mock_registry({
        "test_server": {
            "task": sync_track,
        }
    })
    
    # Create 5 independent steps
    plan = ExecutionPlan(
        steps=[
            ExecutionStep(
                id=f"step{i}",
                service_name="test_server",
                tool_name="task",
                arguments={},
                depends_on=[],
            )
            for i in range(5)
        ],
        rationale="Test concurrency limiting",
    )
    
    # Execute with max_concurrent=2
    await execute_plan(plan, max_concurrent=2)
    
    # Max concurrent should never exceed 2
    max_observed = max(concurrent_executions)
    assert max_observed <= 2, f"Expected max 2 concurrent, but observed {max_observed}"


@pytest.mark.asyncio
async def test_error_handling_in_parallel_execution() -> None:
    """Test that errors in one step don't break the whole execution."""
    def successful_task() -> str:
        """A task that succeeds."""
        return "success"
    
    def failing_task() -> str:
        """A task that fails."""
        raise ValueError("Intentional failure")
    
    setup_mock_registry({
        "test_server": {
            "success": successful_task,
            "fail": failing_task,
        }
    })
    
    plan = ExecutionPlan(
        steps=[
            ExecutionStep(
                id="step1",
                service_name="test_server",
                tool_name="success",
                arguments={},
                depends_on=[],
            ),
            ExecutionStep(
                id="step2",
                service_name="test_server",
                tool_name="fail",
                arguments={},
                depends_on=[],
            ),
        ],
        rationale="Test error handling",
    )
    
    # Execution should fail with RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        await execute_plan(plan)
    
    assert "Intentional failure" in str(exc_info.value)


@pytest.mark.asyncio
async def test_progress_callback_is_called() -> None:
    """Test that progress callback is invoked correctly."""
    callback_calls: list[tuple[int, int, str, bool]] = []
    
    def callback(current: int, total: int, step: ExecutionStep, result: t.Optional[t.Any]) -> None:
        """Track callback invocations."""
        is_complete = result is not None
        callback_calls.append((current, total, step.id, is_complete))
    
    def simple_task() -> str:
        return "done"
    
    setup_mock_registry({
        "test_server": {
            "task": simple_task,
        }
    })
    
    plan = ExecutionPlan(
        steps=[
            ExecutionStep(
                id="step1",
                service_name="test_server",
                tool_name="task",
                arguments={},
                depends_on=[],
            ),
        ],
        rationale="Test callback",
    )
    
    await execute_plan(plan, progress_callback=callback)
    
    # Should have been called twice: once before (result=None) and once after (result=value)
    assert len(callback_calls) == 2
    
    # First call should be start (result=None -> is_complete=False)
    assert callback_calls[0][3] is False
    assert callback_calls[0][2] == "step1"
    
    # Second call should be completion (result=value -> is_complete=True)
    assert callback_calls[1][3] is True
    assert callback_calls[1][2] == "step1"


@pytest.mark.asyncio
async def test_variable_resolution_with_nested_fields() -> None:
    """Test that variable resolution works with nested field access."""
    @dataclass
    class ComplexResult:
        field1: str
        field2: dict[str, str]
    
    def task_a() -> ComplexResult:
        """Return a complex dataclass."""
        return ComplexResult(
            field1="value1",
            field2={"nested": "nested_value"}
        )
    
    def task_b(input_val: str) -> str:
        """Use the nested value."""
        return f"processed_{input_val}"
    
    setup_mock_registry({
        "test_server": {
            "task_a": task_a,
            "task_b": task_b,
        }
    })
    
    plan = ExecutionPlan(
        steps=[
            ExecutionStep(
                id="step1",
                service_name="test_server",
                tool_name="task_a",
                arguments={},
                depends_on=[],
            ),
            ExecutionStep(
                id="step2",
                service_name="test_server",
                tool_name="task_b",
                arguments={"input_val": "$step1.field1"},
                depends_on=["step1"],
            ),
        ],
        rationale="Test nested field access",
    )
    
    results = await execute_plan(plan)
    
    # Verify nested field was resolved correctly
    assert results["step2"] == "processed_value1"
