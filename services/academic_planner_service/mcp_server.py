from __future__ import annotations

import asyncio
import json
import typing as t
from datetime import datetime

import os

from fastmcp import Context, FastMCP

from prompts import load_prompt
from services.shared.models import (
    Plan as PydanticPlan,
    PlannedEvent as PydanticPlannedEvent,
    PlannedReminder as PydanticPlannedReminder,
    ResolvedAssignment as PydanticResolvedAssignment,
    CreatePlanRequest,
    ShowAssignmentSummaryRequest,
)
from services.shared.sampling_utils import extract_sampling_content

mcp = FastMCP("AcademicPlannerServiceMCP")

SYSTEM_PROMPT = load_prompt("academic_planner_system_prompt")


def _convert_to_pydantic_plan(plan_data: dict[str, t.Any]) -> PydanticPlan:
    events = [
        PydanticPlannedEvent(
            title=e.get("title", ""),
            start=e.get("start", ""),
            end=e.get("end", ""),
            location=e.get("location", ""),
        )
        for e in plan_data.get("events", []) or []
    ]

    reminders = [
        PydanticPlannedReminder(
            title=r.get("title", ""),
            due=r.get("due", ""),
            notes=r.get("notes", ""),
        )
        for r in plan_data.get("reminders", []) or []
    ]

    assignments = [
        PydanticResolvedAssignment(
            course_code=a.get("course_code", ""),
            title=a.get("title", ""),
            due=a.get("due", ""),
            weight_percent=float(a.get("weight_percent", 0.0)),
            category=a.get("category", ""),
            is_major=bool(a.get("is_major", False)),
            notes=a.get("notes", ""),
        )
        for a in plan_data.get("assignments", []) or []
    ]

    return PydanticPlan(events=events, reminders=reminders, assignments=assignments)


def _format_datetime(iso_string: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%a %-m/%-d %-I:%M %p")
    except (ValueError, AttributeError):
        return iso_string


def _generate_assignment_summary(plan: PydanticPlan) -> str:
    if not plan.assignments:
        return "📚 No assignments found."

    sorted_assignments = sorted(plan.assignments, key=lambda a: a.due)
    lines = []
    lines.append("📚 ASSIGNMENTS SUMMARY")
    lines.append("=" * 120)
    lines.append(f"{'#':<4} {'Course':<10} {'Title':<40} {'Due':<20} {'Weight':<8} {'Type':<12} {'Category':<15}")
    lines.append("-" * 120)

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

    courses: dict[str, dict[str, t.Union[int, float]]] = {}
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


@mcp.tool()
async def create_academic_plan(syllabi: list[dict], ctx: Context | None = None) -> PydanticPlan:
    """Create an academic plan from parsed syllabi via sampling."""
    if ctx is None or not hasattr(ctx, "sample"):
        raise RuntimeError("Sampling context is required but not available.")

    # syllabi are already dicts - no need to validate through CreatePlanRequest
    # which would convert them back to Pydantic models
    syllabi_dicts = syllabi

    # Combine system and user messages since MCP sampling doesn't support 'system' role
    # Add explicit JSON instruction for reasoning models
    combined_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"CRITICAL: Your response must be ONLY valid JSON with no additional text, "
        f"explanation, or markdown formatting. Start with {{ and end with }}.\n\n"
        f"Input:\n{json.dumps({'syllabi': syllabi_dicts})}"
    )
    
    sample_result = await ctx.sample(
        messages=combined_prompt,
        model_preferences="gpt-5",
    )

    content = extract_sampling_content(sample_result, "create_academic_plan")

    try:
        plan_data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Sampling returned invalid JSON: {exc}") from exc

    return _convert_to_pydantic_plan(plan_data)


@mcp.tool()
def show_assignment_summary(plan: PydanticPlan) -> str:
    """Generate a formatted assignment summary from a plan."""
    request = ShowAssignmentSummaryRequest(plan=plan)
    return _generate_assignment_summary(request.plan)


if __name__ == "__main__":
    host = os.getenv("ACADEMIC_PLANNER_MCP_HOST", "0.0.0.0")
    port = int(os.getenv("ACADEMIC_PLANNER_MCP_PORT", "8602"))
    asyncio.run(mcp.run_streamable_http_async(host=host, port=port))
