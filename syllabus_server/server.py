from __future__ import annotations

import json
import os

from fastmcp import FastMCP
from openai import OpenAI

from prompts import load_prompt
from .models import (Assignment, CourseSection, ExplicitMeeting, MeetingPattern, ParsedSyllabus, Policies,
                     ScheduleEntry)
from .pdf_utils import extract_pdf_pages

# -----------------------------
# Imports from models module
# -----------------------------

# -----------------------------
# MCP + OpenAI client setup
# -----------------------------

mcp = FastMCP("SyllabusServer")

_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
client = OpenAI(api_key=_api_key)


# -----------------------------
# SYSTEM PROMPT
# -----------------------------

SYSTEM_PROMPT = load_prompt("syllabus_parser_system_prompt")



# -----------------------------
# MCP Tool Implementation
# -----------------------------

@mcp.tool()
def parse_syllabus(pdf_path_or_url: str) -> ParsedSyllabus:
    """
    Parse a syllabus PDF/URL into ParsedSyllabus.
    """
    pages = extract_pdf_pages(pdf_path_or_url)

    # Join all pages for global parsing
    full_text = "\n\n".join(pages)

    # Heuristic: pick likely schedule pages
    schedule_pages: list[str] = []
    for p in pages:
        lp = p.lower()
        if (
                "schedule" in lp
                or "course calendar" in lp
                or "course schedule" in lp
                or ("week" in lp and "date" in lp and "topic" in lp)
                or "deliverable" in lp
                or "assignment schedule" in lp
        ):
            schedule_pages.append(p)

    # Fallback: if no explicit schedule page detected, leave empty string
    schedule_text = "\n\n".join(schedule_pages) if schedule_pages else ""

    model_input = {
        "full_text": full_text[:30000],          # increased for full semester schedules
        "schedule_text": schedule_text[:15000],   # increased to capture complete schedule tables
    }

    completion = client.chat.completions.create(
        model="gpt-5",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(model_input),
            },
        ],
    )

    raw = completion.choices[0].message.content or "{}"
    data = json.loads(raw)

    # ---- Convert raw JSON → dataclasses defensively ----

    # Sections
    sections: list[CourseSection] = []
    for sec in data.get("sections", []):
        meeting_patterns = [
            MeetingPattern(**mp) for mp in sec.get("meeting_patterns", []) or []
        ]
        explicit_meetings = [
            ExplicitMeeting(**em) for em in sec.get("explicit_meetings", []) or []
        ]
        sections.append(
            CourseSection(
                section_id=sec.get("section_id", ""),
                instructors=sec.get("instructors", []) or [],
                meeting_patterns=meeting_patterns,
                explicit_meetings=explicit_meetings,
            )
        )

    # Assignments
    assignments: list[Assignment] = []
    for a in data.get("assignments", []) or []:
        assignments.append(
            Assignment(
                title=a.get("title", "") or "",
                due=a.get("due", "") or "",
                weight_percent=float(a.get("weight_percent", 0.0) or 0.0),
                category=a.get("category", "other") or "other",
                is_in_class=bool(a.get("is_in_class", False)),
                notes=a.get("notes", "") or "",
            )
        )

    # Schedule entries
    schedule: list[ScheduleEntry] = []
    for s in data.get("schedule", []) or []:
        schedule.append(
            ScheduleEntry(
                week=s.get("week", None),
                date=s.get("date", "") or "",
                topic=s.get("topic", "") or "",
                deliverables=s.get("deliverables", []) or [],
                notes=s.get("notes", "") or "",
            )
        )

    # Policies
    pol_src = data.get("policies", {}) or {}
    policies = Policies(
        due_time_default=pol_src.get("due_time_default", "") or "",
        late_policy=pol_src.get("late_policy", "") or "",
        attendance_policy=pol_src.get("attendance_policy", "") or "",
        ai_policy=pol_src.get("ai_policy", "") or "",
        other=pol_src.get("other", "") or "",
    )

    parsed = ParsedSyllabus(
        course_code=data.get("course_code", "") or "",
        course_title=data.get("course_title", "") or "",
        term=data.get("term", "") or "",
        timezone=data.get("timezone", "") or "",
        sections=sections,
        assignments=assignments,
        schedule=schedule,
        policies=policies,
    )

    return parsed


if __name__ == "__main__":
    # Run as an MCP server over stdio
    mcp.run()