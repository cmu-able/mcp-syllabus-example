# -*- coding: utf-8 -*-
import json
import os

from fastmcp import FastMCP
from openai import OpenAI
from academic_planner.models import PlannedEvent, PlannedReminder, ResolvedAssignment, Plan
from prompts import load_prompt
from syllabus_server.models import ParsedSyllabus

mcp = FastMCP("AcademicPlanner")

_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
client = OpenAI(api_key=_api_key)

SYSTEM_PROMPT = load_prompt("academic_planner_system_prompt")

@mcp.tool()
def create_academic_plan(
        syllabi: list[ParsedSyllabus],
) -> Plan:
    """Creates an academic plan from ParsedSyllabus.

    :param syllabi: The list of ParsedSyllabus objects.
    :return: A Plan object containing events, reminders, and resolved assignments.
    """

    from dataclasses import asdict
    
    # Serialize syllabi to dict format for LLM
    syllabi_dicts = [
        asdict(s) if hasattr(s, "__dataclass_fields__") else s
        for s in syllabi
    ]
    
    completion = client.chat.completions.create(
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
    plan = Plan(
        events=[
            PlannedEvent(**event) for event in plan_data.get("events", [])
        ],
        reminders=[
            PlannedReminder(**reminder) for reminder in plan_data.get("reminders", [])
        ],
        assignments=[
            ResolvedAssignment(**assignment) for assignment in plan_data.get("assignments", [])
        ],
    )
    return plan


@mcp.tool()
def show_assignment_summary(plan: Plan) -> str:
    """Display consolidated assignment list with resolved due dates across all courses.
    
    Shows all assignments from the academic plan, sorted by due date, with their
    course, title, due date, weight, category, and classification (major/minor).
    
    :param plan: The Plan object containing resolved assignments.
    :return: Formatted string showing assignment summary table.
    """
    from datetime import datetime
    
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
