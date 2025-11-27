"""
MCP wrapper for academic planner service.

This module maintains the original MCP tool signatures but makes HTTP calls
to the distributed academic planner service. It handles serialization/deserialization
between dataclass and Pydantic models, and implements proper timeouts for
long-running LLM operations.
"""
from __future__ import annotations

import os
from dataclasses import asdict

import httpx
from fastmcp import FastMCP

# Import original dataclass models for MCP interface compatibility
from academic_planner.models import Plan, PlannedEvent, PlannedReminder, ResolvedAssignment
from syllabus_server.models import ParsedSyllabus
# Import Pydantic models for HTTP serialization
from services.shared.models import (
    Plan as PydanticPlan,
    PlannedEvent as PydanticPlannedEvent,
    PlannedReminder as PydanticPlannedReminder,
    ResolvedAssignment as PydanticResolvedAssignment,
    ParsedSyllabus as PydanticParsedSyllabus,
    CreatePlanRequest,
    ShowAssignmentSummaryRequest,
    ShowAssignmentSummaryResponse,
)


mcp = FastMCP("AcademicPlannerMCPWrapper")

# Service URL - configurable via environment variable
ACADEMIC_PLANNER_SERVICE_URL = os.getenv("ACADEMIC_PLANNER_SERVICE_URL", "http://localhost:8002")

# Timeout settings for LLM operations (in seconds)
CREATE_PLAN_TIMEOUT = 300.0  # 5 minutes for academic plan creation with multiple syllabi
SUMMARY_TIMEOUT = 30.0  # 30 seconds for assignment summary formatting


def _create_academic_plan(syllabi: list[ParsedSyllabus]) -> Plan:
    """
    Create an academic plan from a list of ParsedSyllabus objects.
    
    This maintains the exact same signature as the original MCP tool
    but makes an HTTP call to the distributed academic planner service.
    """
    try:
        # Convert dataclass syllabi to Pydantic for HTTP serialization
        pydantic_syllabi = []
        for syllabus in syllabi:
            syllabus_dict = asdict(syllabus)
            pydantic_syllabi.append(PydanticParsedSyllabus(**syllabus_dict))
        
        request = CreatePlanRequest(syllabi=pydantic_syllabi)
        
        # Make HTTP call with extended timeout for LLM processing
        with httpx.Client(timeout=CREATE_PLAN_TIMEOUT) as client:
            response = client.post(
                f"{ACADEMIC_PLANNER_SERVICE_URL}/create-plan",
                json=request.model_dump(),
            )
            response.raise_for_status()
            
        # Convert response back to original dataclass format
        pydantic_result = PydanticPlan(**response.json())
        dataclass_result = _pydantic_to_dataclass_plan(pydantic_result)
        
        return dataclass_result
        
    except httpx.TimeoutException:
        raise RuntimeError(f"Academic plan creation timed out after {CREATE_PLAN_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error from academic planner service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling academic planner service: {str(e)}")


def _show_assignment_summary(plan: Plan) -> str:
    """Display consolidated assignment list with resolved due dates across all courses.
    
    Shows all assignments from the academic plan, sorted by due date, with their
    course, title, due date, weight, category, and classification (major/minor).
    
    Args:
        plan: The Plan object containing resolved assignments.
        
    Returns:
        Formatted string showing assignment summary table.
    """
    try:
        # Convert dataclass plan to Pydantic for HTTP serialization
        pydantic_plan = _dataclass_to_pydantic_plan(plan)
        request = ShowAssignmentSummaryRequest(plan=pydantic_plan)
        
        # Make HTTP call with normal timeout (this is a fast formatting operation)
        with httpx.Client(timeout=SUMMARY_TIMEOUT) as client:
            response = client.post(
                f"{ACADEMIC_PLANNER_SERVICE_URL}/show-assignment-summary",
                json=request.model_dump(),
            )
            response.raise_for_status()
            
        # Extract summary from response
        result = ShowAssignmentSummaryResponse(**response.json())
        return result.summary
        
    except httpx.TimeoutException:
        raise RuntimeError(f"Assignment summary generation timed out after {SUMMARY_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error from academic planner service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling academic planner service: {str(e)}")


def _dataclass_to_pydantic_plan(plan: Plan) -> PydanticPlan:
    """
    Convert dataclass Plan to Pydantic Plan.
    
    This handles the conversion between the original dataclass models used by
    the MCP interface and the Pydantic models used by the REST API.
    """
    # Convert to dict first, then to Pydantic model
    plan_dict = asdict(plan)
    return PydanticPlan(**plan_dict)


def _pydantic_to_dataclass_plan(pydantic_plan: PydanticPlan) -> Plan:
    """
    Convert Pydantic Plan to dataclass Plan.
    
    This handles the conversion from REST API response back to the original
    dataclass format expected by the MCP interface.
    """
    # Convert Pydantic to dict, then reconstruct dataclasses
    data = pydantic_plan.model_dump()
    
    # Reconstruct nested dataclasses
    events = [PlannedEvent(**event) for event in data.get("events", [])]
    reminders = [PlannedReminder(**reminder) for reminder in data.get("reminders", [])]
    assignments = [ResolvedAssignment(**assignment) for assignment in data.get("assignments", [])]
    
    return Plan(
        events=events,
        reminders=reminders,
        assignments=assignments
    )


# MCP tool wrappers that call the raw functions
@mcp.tool()
def create_academic_plan(syllabi: list[ParsedSyllabus]) -> Plan:
    """Creates an academic plan from ParsedSyllabus."""
    return _create_academic_plan(syllabi)


@mcp.tool()
def show_assignment_summary(plan: Plan) -> str:
    """Display consolidated assignment list with resolved due dates across all courses."""
    return _show_assignment_summary(plan)