from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Literal, Optional, Any, Dict

from mcp.server.fastmcp import FastMCP
from openai import OpenAI

from .pdf_utils import extract_pdf_pages

# -----------------------------
# Data classes for parsed syllabus
# -----------------------------

MeetingKind = Literal["lecture", "recitation", "lab", "exercise", "exam", "other"]
AssignmentCategory = Literal[
    "exam",
    "project",
    "homework",
    "quiz",
    "participation",
    "presentation",
    "other",
]


@dataclass
class MeetingPattern:
    """
    Recurring meeting pattern like:
    - "MW 9:30-10:50 am, 3SC 265"
    """
    kind: MeetingKind = "lecture"
    days_of_week: List[str] = field(default_factory=list)  # ["Mon", "Wed"]
    start_time_local: str = ""  # "HH:MM" 24h
    end_time_local: str = ""    # "HH:MM" 24h
    location: str = ""


@dataclass
class ExplicitMeeting:
    """
    A specific dated meeting row from a schedule table.
    """
    date: str = ""          # "YYYY-MM-DD"
    start: str = ""         # ISO datetime if known, else ""
    end: str = ""           # ISO datetime if known, else ""
    location: str = ""
    topic: str = ""
    kind: MeetingKind = "lecture"


@dataclass
class Assignment:
    """
    A graded (or clearly important) deliverable.
    """
    title: str = ""
    due: str = ""                   # ISO datetime if concrete; else ""
    weight_percent: float = 0.0
    category: AssignmentCategory = "other"
    is_in_class: bool = False
    notes: str = ""


@dataclass
class Policies:
    """
    Coarse policies relevant to planning and orchestration.
    """
    due_time_default: str = ""      # e.g. "start_of_class", "23:59", "unspecified"
    late_policy: str = ""
    attendance_policy: str = ""
    ai_policy: str = ""
    other: str = ""


@dataclass
class CourseSection:
    """
    One section of a multi-section course, e.g.:
    - Section A: Tue 9:30–10:50
    - Section B: Tue 12:30–1:50
    """
    section_id: str = ""                          # "A", "B", "C", etc.
    instructors: List[str] = field(default_factory=list)
    meeting_patterns: List[MeetingPattern] = field(default_factory=list)
    explicit_meetings: List[ExplicitMeeting] = field(default_factory=list)


@dataclass
class ScheduleEntry:
    """
    One row from a schedule/calendar table.
    Used to preserve the mapping of dates → topics → deliverables.
    """
    week: Optional[int] = None
    date: str = ""                                  # "YYYY-MM-DD" or ""
    topic: str = ""
    deliverables: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class ParsedSyllabus:
    """
    Top-level parsed representation for one syllabus.
    Designed to:
    - support multiple sections,
    - expose schedule table information,
    - support downstream LLM orchestration.
    """
    course_code: str = ""
    course_title: str = ""
    term: str = ""
    timezone: str = ""
    sections: List[CourseSection] = field(default_factory=list)
    assignments: List[Assignment] = field(default_factory=list)
    schedule: List[ScheduleEntry] = field(default_factory=list)
    policies: Policies = field(default_factory=Policies)


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

SYSTEM_PROMPT = """
You are a precise, conservative parser for ONE university course syllabus.

You will receive input as a JSON object:

{
  "full_text": "<entire syllabus as raw text>",
  "schedule_text": "<subset of pages that contain the course schedule/calendar; this text may look messy or have columns and sections mushed together>"
}

Your job is to output EXACTLY ONE JSON object of the following shape:

{
  "course_code": "string",
  "course_title": "string",
  "term": "string",
  "timezone": "string",
  "sections": [
    {
      "section_id": "string",
      "instructors": ["string"],
      "meeting_patterns": [
        {
          "kind": "lecture | recitation | lab | exercise | exam | other",
          "days_of_week": ["Mon","Wed"],
          "start_time_local": "HH:MM",
          "end_time_local": "HH:MM",
          "location": "string"
        }
      ],
      "explicit_meetings": [
        {
          "date": "YYYY-MM-DD",
          "start": "YYYY-MM-DDTHH:MM:SS",
          "end": "YYYY-MM-DDTHH:MM:SS",
          "location": "string",
          "topic": "string",
          "kind": "lecture | recitation | lab | exercise | exam | other"
        }
      ]
    }
  ],
  "assignments": [
    {
      "title": "string",
      "due": "YYYY-MM-DDTHH:MM:SS",
      "weight_percent": 0.0,
      "category": "exam | project | homework | quiz | participation | presentation | other",
      "is_in_class": true,
      "notes": "string"
    }
  ],
  "schedule": [
    {
      "week": 1,
      "date": "YYYY-MM-DD",
      "topic": "string",
      "deliverables": ["string"],
      "notes": "string"
    }
  ],
  "policies": {
    "due_time_default": "string",
    "late_policy": "string",
    "attendance_policy": "string",
    "ai_policy": "string",
    "other": "string"
  }
}

USE OF INPUT FIELDS:

- Use "full_text" for:
  - course_code, course_title, term, timezone
  - global descriptions of assessments and weights
  - policies (late work, AI use, attendance, etc.)

- Use "schedule_text" for:
  - reconstructing the "schedule" array
  - finding which dates/rows mention which deliverables
  - mapping deliverable names (e.g. "HW1 due") to specific dates when possible

"schedule_text" may be poorly formatted:
- Multiple section columns may be concatenated.
- Labels like "Sections A & BSection DSections C & E" may appear.
- Spacing and alignment may be broken.

Despite this, reconstruct `schedule` rows logically:
- Identify date-like tokens (e.g. "Aug 27", "9/3", "Oct 15") and convert to "YYYY-MM-DD" when the year is inferable.
- For each date (or week row), capture:
    - topic: the main topic/label.
    - deliverables: list of items clearly due or happening that day
      (e.g. "HW1 due", "Project 1 checkpoint", "In-class exercise").
    - notes: any extra context.
- If you are NOT confident about a mapping, leave that part empty rather than guessing.

DETAILED RULES:

1. DO NOT HALLUCINATE.
   - Use ONLY information from full_text and schedule_text.
   - If something is not clearly stated, leave it empty:
     - "" for strings, 0.0 for weight_percent, null/omitted for week, [] for arrays.

2. course_code, course_title, term:
   - Extract from header (e.g. "17-603 Communications for Software Leaders I", "Fall 2025").
   - If missing, use "".

3. timezone:
   - If clearly implied (e.g., CMU Pittsburgh), you MAY set "America/New_York".
   - If unsure, use "".

4. sections:
   - Some syllabi list multiple sections (A, B, C, etc.) with different times/rooms.
   - For each distinct section:
       - section_id: label like "A", "B", "C".
       - instructors: names if specified for that section; otherwise global instructors.
       - meeting_patterns:
           - Parse lines like "Section A, Tuesdays, 9:30-10:50 am, 3SC 265".
           - days_of_week: ["Tue"], etc. Use Mon/Tue/Wed/Thu/Fri abbreviations.
           - start_time_local/end_time_local: 24h, e.g. "09:30".
           - location: room string.
       - explicit_meetings:
           - Only if a date-specific entry is clearly tied to this section.
   - If only one meeting pattern applies, you may create one section with section_id "default".

5. schedule:
   - Capture rows from any course schedule/calendar table.
   - week:
       - numeric week if clearly labeled; else null/omit.
   - date:
       - "YYYY-MM-DD" if a specific date appears; else "".
   - topic:
       - short description of that day/week.
   - deliverables:
       - items that are clearly due or occurring that day ("HW1 due", "Team presentation", "In-class final").
   - notes:
       - leftover relevant text that doesn’t fit cleanly elsewhere.
   - If schedule_text is extremely garbled:
       - Only include rows you can reconstruct confidently.
       - Never invent dates.

6. assignments:
   - Include clearly graded or major deliverables:
       - exams, finals, midterms
       - projects, reports
       - homeworks, major quizzes
       - graded presentations
   - title: concise label.
   - due:
       - ONLY if:
           - a specific due DATE and (if applicable) TIME is clearly given, OR
           - a specific date is given AND a clear default due time rule exists
             in policies (e.g. "all assignments due 11:59pm").
       - If due depends on "at the beginning of class" or similar and
         requires picking a specific meeting, leave due = "" and explain in notes.
   - weight_percent:
       - Use explicit percentages from grading tables when clearly mapped.
       - Otherwise 0.0.
   - category:
       - exam, project, homework, quiz, participation, presentation, other
         based on keywords.
   - is_in_class:
       - true if clearly in-class (e.g. "In-class final", "In-class exercise").
       - false otherwise.
   - notes:
       - brief quote/paraphrase of description.

7. policies:
   - due_time_default:
       - "start_of_class", "23:59", "unspecified", or a short phrase.
   - late_policy:
       - short summary.
   - attendance_policy:
       - short summary.
   - ai_policy:
       - short summary of AI / LLM usage policy if present; else "".
   - other:
       - other global constraints.
   - If a policy is not discussed, use "".

8. VALIDITY:
   - Output MUST be valid JSON, nothing else.
   - No comments, no trailing commas, no prose.
"""


# -----------------------------
# MCP Tool Implementation
# -----------------------------

@mcp.tool()
def parse_syllabus(pdf_path_or_url: str) -> Dict[str, Any]:
    """
    Parse a syllabus PDF/URL into ParsedSyllabus.
    Returns a plain dict (JSON-serializable) suitable for MCP clients.
    """
    pages = extract_pdf_pages(pdf_path_or_url)

    # Join all pages for global parsing
    full_text = "\n\n".join(pages)

    # Heuristic: pick likely schedule pages
    schedule_pages: List[str] = []
    for p in pages:
        lp = p.lower()
        if "schedule" in lp or "course calendar" in lp or "course schedule" in lp:
            schedule_pages.append(p)

    # Fallback: if no explicit schedule page detected, leave empty string
    schedule_text = "\n\n".join(schedule_pages) if schedule_pages else ""

    model_input = {
        "full_text": full_text[:14000],          # keep within context
        "schedule_text": schedule_text[:6000],   # focused messy part
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
    sections: List[CourseSection] = []
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
    assignments: List[Assignment] = []
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
    schedule: List[ScheduleEntry] = []
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

    return asdict(parsed)


if __name__ == "__main__":
    # Run as an MCP server over stdio
    mcp.run()