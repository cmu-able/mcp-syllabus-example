"""
MCP wrapper for academic planner service.

This module maintains the MCP tool signatures but makes HTTP calls
to the distributed academic planner service. It uses Pydantic models end-to-end
for validation/serialization and implements proper timeouts for long-running
LLM operations.
"""
from __future__ import annotations

import os

import requests
from fastmcp import FastMCP

from services.shared.models import (
    ParsedSyllabus,
    Plan,
    PlannedEvent,
    PlannedReminder,
    ResolvedAssignment,
    CreatePlanRequest,
    ShowAssignmentSummaryRequest,
    ShowAssignmentSummaryResponse,
)


mcp = FastMCP("AcademicPlannerMCPWrapper")

# Service URL - configurable via environment variable
ACADEMIC_PLANNER_SERVICE_URL = os.getenv("ACADEMIC_PLANNER_SERVICE_URL", "http://localhost:8002")

# Timeout settings for LLM operations (in seconds)
CREATE_PLAN_TIMEOUT = 600.0  # 10 minutes for academic plan creation with multiple syllabi
SUMMARY_TIMEOUT = 30.0  # 30 seconds for assignment summary formatting


def _create_academic_plan(syllabi: list[ParsedSyllabus]) -> Plan:
    """
    Create an academic plan from a list of ParsedSyllabus objects.
    
    This maintains the exact same signature as the original MCP tool
    but makes an HTTP call to the distributed academic planner service.
    """
    try:
        request = CreatePlanRequest(syllabi=syllabi)
        
        # Make HTTP call with extended timeout for LLM processing
        response = requests.post(
            f"{ACADEMIC_PLANNER_SERVICE_URL}/academics/plan",
            json=request.model_dump(),
            timeout=CREATE_PLAN_TIMEOUT,
        )
        response.raise_for_status()
            
        return Plan(**response.json())
        
    except requests.Timeout:
        raise RuntimeError(f"Academic plan creation timed out after {CREATE_PLAN_TIMEOUT} seconds")
    except requests.HTTPError as e:
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
        request = ShowAssignmentSummaryRequest(plan=plan)
        
        # Make HTTP call with normal timeout (this is a fast formatting operation)
        response = requests.post(
            f"{ACADEMIC_PLANNER_SERVICE_URL}/academics/assignments",
            json=request.model_dump(),
            timeout=SUMMARY_TIMEOUT,
        )
        response.raise_for_status()
            
        result = ShowAssignmentSummaryResponse(**response.json())
        return result.summary
        
    except requests.Timeout:
        raise RuntimeError(f"Assignment summary generation timed out after {SUMMARY_TIMEOUT} seconds")
    except requests.HTTPError as e:
        raise RuntimeError(f"HTTP error from academic planner service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling academic planner service: {str(e)}")



# MCP tool wrappers that call the raw functions
@mcp.tool()
def create_academic_plan(syllabi: list[ParsedSyllabus]) -> Plan:
    """Creates an academic plan from ParsedSyllabus."""
    return _create_academic_plan(syllabi)


@mcp.tool()
def show_assignment_summary(plan: Plan) -> str:
    """Display consolidated assignment list with resolved due dates across all courses."""
    return _show_assignment_summary(plan)
