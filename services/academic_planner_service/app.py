"""
FastAPI service for academic planning operations.

This service extracts the core business logic from academic_planner/server.py
and exposes it as REST API endpoints. It handles LLM operations that can take
1-2 minutes when processing multiple syllabi.
"""
from __future__ import annotations

import json
import os
import typing as t
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from openai import AsyncOpenAI

from services.shared.models import (
    Plan as PydanticPlan,
    PlannedEvent as PydanticPlannedEvent,
    PlannedReminder as PydanticPlannedReminder,
    ResolvedAssignment as PydanticResolvedAssignment,
    CreatePlanRequest,
    ShowAssignmentSummaryRequest,
    ShowAssignmentSummaryResponse,
)
from prompts import load_prompt


# Global async OpenAI client - will be initialized on startup
client: AsyncOpenAI = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup and cleanup on shutdown."""
    global client
    
    # Startup: Initialize async OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
    client = AsyncOpenAI(api_key=api_key)
    
    yield
    
    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title="Academic Planner Service",
    description="REST API for academic planning and assignment management using LLM",
    version="1.0.0",
    lifespan=lifespan,
)


# System prompt for LLM
SYSTEM_PROMPT = load_prompt("academic_planner_system_prompt")


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "academic-planner-service"}


@app.post("/academics/plan", response_model=PydanticPlan)
async def create_plan(request: CreatePlanRequest) -> PydanticPlan:
    """
    Create an academic plan from a list of parsed syllabi.
    
    This endpoint can take 1-2 minutes when processing multiple syllabi 
    due to complex LLM analysis and planning operations.
    """
    try:
        # Serialize syllabi to dict format for LLM
        syllabi_dicts = [
            syllabus.model_dump() for syllabus in request.syllabi
        ]
        
        # Call OpenAI API - this is the long-running LLM operation
        completion = await client.chat.completions.create(
            model="gpt-5",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps({"syllabi": syllabi_dicts}),
                },
            ],
        )
        
        plan_json = completion.choices[0].message.content or "{}"
        plan_data = json.loads(plan_json)
        
        # Convert to Pydantic models defensively
        plan = _convert_to_pydantic_plan(plan_data)
        
        return plan
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating academic plan: {str(e)}")


@app.post("/academics/assignments", response_model=ShowAssignmentSummaryResponse)
async def show_assignment_summary(request: ShowAssignmentSummaryRequest) -> ShowAssignmentSummaryResponse:
    """
    Generate a formatted assignment summary from an academic plan.
    
    This is a fast operation that formats the assignment data into a readable table.
    """
    try:
        # Generate the formatted summary
        summary_text = _generate_assignment_summary(request.plan)
        
        return ShowAssignmentSummaryResponse(summary=summary_text)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating assignment summary: {str(e)}")


def _convert_to_pydantic_plan(plan_data: dict[str, t.Any]) -> PydanticPlan:
    """
    Convert raw JSON from LLM response to Pydantic Plan model.
    
    Handles defensive conversion with fallback values for missing or invalid data.
    """
    try:
        # Events
        events = []
        for event_data in plan_data.get("events", []):
            events.append(PydanticPlannedEvent(
                title=event_data.get("title", ""),
                start=event_data.get("start", ""),
                end=event_data.get("end", ""),
                location=event_data.get("location", "")
            ))
        
        # Reminders
        reminders = []
        for reminder_data in plan_data.get("reminders", []):
            reminders.append(PydanticPlannedReminder(
                title=reminder_data.get("title", ""),
                due=reminder_data.get("due", ""),
                notes=reminder_data.get("notes", "")
            ))
        
        # Assignments
        assignments = []
        for assignment_data in plan_data.get("assignments", []):
            assignments.append(PydanticResolvedAssignment(
                course_code=assignment_data.get("course_code", ""),
                title=assignment_data.get("title", ""),
                due=assignment_data.get("due", ""),
                weight_percent=float(assignment_data.get("weight_percent", 0.0)),
                category=assignment_data.get("category", ""),
                is_major=bool(assignment_data.get("is_major", False)),
                notes=assignment_data.get("notes", "")
            ))
        
        return PydanticPlan(
            events=events,
            reminders=reminders,
            assignments=assignments
        )
        
    except Exception as e:
        # Fallback to empty plan if conversion fails
        return PydanticPlan(events=[], reminders=[], assignments=[])


def _generate_assignment_summary(plan: PydanticPlan) -> str:
    """
    Generate a formatted assignment summary from a plan.
    
    This replicates the logic from the original show_assignment_summary function
    but uses Pydantic models.
    """
    if not plan.assignments:
        return "📚 No assignments found."
    
    # Sort assignments by due date
    sorted_assignments = sorted(plan.assignments, key=lambda a: a.due)
    
    lines = []
    lines.append("📚 ASSIGNMENTS SUMMARY")
    lines.append("=" * 120)
    lines.append(f"{'#':<4} {'Course':<10} {'Title':<40} {'Due':<20} {'Weight':<8} {'Type':<12} {'Category':<15}")
    lines.append("-" * 120)
    
    def _format_datetime(iso_string: str) -> str:
        """Format ISO datetime to readable format."""
        try:
            dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
            return dt.strftime("%a %-m/%-d %-I:%M %p")
        except (ValueError, AttributeError):
            return iso_string
    
    for idx, assignment in enumerate(sorted_assignments, 1):
        title = assignment.title[:39] if len(assignment.title) > 39 else assignment.title
        course = assignment.course_code[:9] if len(assignment.course_code) > 9 else assignment.course_code
        due_formatted = _format_datetime(assignment.due)
        weight = f"{assignment.weight_percent:.1f}%"
        assignment_type = "MAJOR" if assignment.is_major else "minor"
        category = assignment.category[:14] if len(assignment.category) > 14 else assignment.category
        
        lines.append(
            f"{idx:<4} {course:<10} {title:<40} {due_formatted:<20} {weight:<8} {assignment_type:<12} {category:<15}"
        )
    
    lines.append("=" * 120)
    lines.append(f"Total: {len(sorted_assignments)} assignment(s)")
    
    # Summary by course
    courses = {}
    for assignment in sorted_assignments:
        if assignment.course_code not in courses:
            courses[assignment.course_code] = {"count": 0, "weight": 0.0}
        courses[assignment.course_code]["count"] += 1
        courses[assignment.course_code]["weight"] += assignment.weight_percent
    
    lines.append("")
    lines.append("By Course:")
    for course_code in sorted(courses.keys()):
        info = courses[course_code]
        lines.append(f"  {course_code}: {info['count']} assignment(s), {info['weight']:.1f}% total weight")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
