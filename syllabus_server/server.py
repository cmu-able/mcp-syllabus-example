# -*- coding: utf-8 -*-
import typing as t

import os
import json
from dataclasses import asdict, dataclass, field
from email.policy import default

from mcp.server.fastmcp import FastMCP  # from official MCP python package
from openai import OpenAI

from .pdf_utils import extract_pdf_pages

# ----------- Data Shapes ------------
# syllabus_server/server.py (top of file)

from typing import Literal, Optional


MeetingKind = Literal["lecture", "recitation", "lab", "exercise", "exam", "other"]
AssignmentCategory = Literal[
    "exam", "project", "homework", "quiz", "participation", "presentation", "other"
]


@dataclass
class MeetingPattern:
    kind: MeetingKind = "lecture"                            # e.g. "lecture"
    days_of_week: list[str] = field(default_factory=list)    # e.g. ["Mon", "Wed"]
    start_time_local: str = ""                               # "HH:MM", 24h, local time, "" if unknown
    end_time_local: str = ""                                 # "HH:MM", "", if unknown
    location: str = ""                                       # "", if unknown


@dataclass
class ExplicitMeeting:
    date: str = ""                     # "YYYY-MM-DD"
    start: str = ""                    # ISO datetime if known, else ""
    end: str = ""                      # ISO datetime if known, else ""
    location: str = ""                 # "", if unknown
    topic: str = ""                    # short label
    kind: MeetingKind = "lecture"      # best guess


@dataclass
class CourseSection:
    section_id: str = ""
    instructors: list[str] = field(default_factory=list)
    meeting_patterns: list[MeetingPattern] = field(default_factory=list)
    explicit_meetings: list[ExplicitMeeting] = field(default_factory=list)


@dataclass
class ScheduleEntry:
    week: t.Optional[int] = None
    date: str = ""                     # "YYYY-MM-DD"
    topic: str = ""
    deliverables: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class Assignment:
    title: str = ""
    due: str = ""                           # ISO datetime if concrete, else "" (leave resolution to orchestrator)
    weight_percent: float = 0.0             # 0.0 if not explicitly stated
    category: AssignmentCategory = "other"  # classifier based on title/description
    is_in_class: bool = False               # True if clearly an in-class activity/exam
    notes: str = ""                         # brief description or source line


@dataclass
class Policies:
    due_time_default: str = ""     # "start_of_class" | "23:59" | "unspecified" | other short phrase
    late_policy: str  = ""         # paraphrased or quoted
    attendance_policy: str = ""    # paraphrased or quoted
    ai_policy: str = ""            # paraphrased or quoted
    other: str = ""                # any other relevant course-wide rules


@dataclass
class ParsedSyllabus:
    course_code: str = ""          # e.g. "17-611"
    course_title: str = ""         # e.g. "Statistics for Decision Making"
    term: str = ""                 # e.g. "Fall 2025"
    timezone: str = ""             # IANA, e.g. "America/New_York" or ""
    sections: list[CourseSection] = field(default_factory=list)
    assignments: list[Assignment] = field(default_factory=list)
    schedule: list[ScheduleEntry] = field(default_factory=list)
    policies: Policies = field(default_factory=Policies)


mcp = FastMCP("SyllabusServer")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a precise, conservative parser for ONE university course syllabus.

You must output EXACTLY ONE JSON object of the following shape:

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

DETAILED RULES:

1. DO NOT HALLUCINATE.
   - Use ONLY information from the syllabus text.
   - If something is not clearly stated, leave it empty:
     - "" for strings, 0.0 for weight_percent, null or omit for week, [] for arrays.

2. course_code, course_title, term:
   - Extract from the header if present (e.g. "17-603 Communications for Software Leaders I", "Fall 2025").
   - If missing, use "".

3. timezone:
   - If the syllabus clearly implies a campus location (e.g., Pittsburgh main campus),
     you MAY set "America/New_York".
   - If unsure, use "".

4. sections:
   - Some syllabi list multiple sections (A, B, C, etc.) with different times/rooms.
   - For each distinct section:
       - section_id: label like "A", "B", "C", "D".
       - instructors: instructor names if specific; otherwise use the common instructor list.
       - meeting_patterns:
           - Parse lines like "Section A, Tuesdays, 9:30-10:50 am, 3SC 265".
           - days_of_week: ["Tue"] etc.
           - start_time_local/end_time_local: 24-hour format, e.g. "09:30".
           - location: room string.
       - explicit_meetings:
           - If there is a schedule table with specific dates tied to sections, map them if clear;
             otherwise leave this empty and use top-level "schedule".

5. meeting_patterns for single-section courses:
   - If no sections are distinguished, you may use one synthetic section with section_id "default".

6. schedule:
   You will receive your input as a JSON object:

    {
      "full_text": "<entire syllabus as raw text>",
      "schedule_text": "<subset of pages that contain the course schedule/calendar; this text may look messy or have columns mushed together>"
    }
    
    Use BOTH, but:
    - Prefer `full_text` for course_code, course_title, term, policies, and assignment descriptions.
    - Prefer `schedule_text` to reconstruct the `schedule` array and any date-deliverable mappings.
    
    `schedule_text` is often poorly formatted:
    - columns may be concatenated (e.g. "Sections A & BSection DSections C & E...")
    - multiple sections may appear in the same row,
    - spacing may be inconsistent.
    
    Despite that, reconstruct `schedule` rows logically:
    - Identify date-like tokens (e.g. "Aug 27", "9/3", "Oct 15").
    - Look at nearby words for topics and deliverables ("HW1 due", "Team Presentation", "In-class exercise").
    - Each `schedule` entry should capture ONE logical row:
        - `week`: if explicitly labeled, otherwise null/omitted.
        - `date`: concrete "YYYY-MM-DD" if you can infer it.
        - `topic`: short description of that meeting’s main topic.
        - `deliverables`: list of items clearly due or happening that day.
        - `notes`: any extra context.
    
    If the layout is too garbled to be certain for a specific item:
    - You may leave that item out of `schedule`.
    - NEVER invent dates or deliverables that are not clearly supported.

7. assignments:
   - Include clearly graded or major deliverables:
       - exams, finals, midterms
       - projects, reports
       - homeworks, major quizzes, presentations
   - title:
       - short, e.g. "HW1: Logic", "In-Class Final", "Team Presentation".
   - due:
       - ONLY fill if:
           - a specific date/time is given, OR
           - a specific date is given AND a clear default due time rule exists
             (e.g. "all assignments due 11:59pm").
       - If due depends on "at the beginning of class", leave due = "" and
         describe in notes; the orchestrator will resolve it.
   - weight_percent:
       - Use explicit numbers from grading tables when clearly mapped.
       - Otherwise 0.0.
   - category:
       - exam: contains "exam", "midterm", "final".
       - project: "project", "report", "capstone".
       - homework: "homework", "HW".
       - quiz: "quiz".
       - participation: "participation", "attendance".
       - presentation: "presentation".
       - other: everything else.
   - is_in_class:
       - true if it clearly occurs during class time (e.g. "In-Class Final", "In-class exercise").
       - false otherwise.
   - notes:
       - short quote or paraphrase from syllabus describing this item.

8. policies:
   - due_time_default:
       - A short code/phrase for the clearest rule:
         - "start_of_class" if "all work due at the beginning of class".
         - "23:59" if "all work due at 11:59pm".
         - "unspecified" if no clear rule.
   - late_policy:
       - Brief summary of late work rules.
   - attendance_policy:
       - Brief summary of attendance expectations.
   - ai_policy:
       - Brief summary of AI / generative tools usage policy, if present.
   - other:
       - Any other global rule relevant to scheduling or workload.
   - If a policy is not discussed, use "".

9. VALIDITY:
   - Output MUST be valid JSON.
   - No comments, no trailing commas, no extra text.
"""

# ----------- MCP Tool ------------
@mcp.tool()
def parse_syllabus(pdf_path_or_url: str) -> dict:
    """
    Parses a university course syllabus PDF into structured data.

    Args:
        pdf_path_or_url: Local file path or URL to the syllabus PDF.

    Returns:
        ParsedSyllabus object with extracted information.
    """
    pages = extract_pdf_pages(pdf_path_or_url)
    full_text = "\n\n".join(pages)
    schedule_pages = [p for p in pages if "Schedule" in p or "Course Schedule" in p or "Calendar" in p]
    schedule_text = "\n\n".join(schedule_pages)

    model_input = {
        "full_text": full_text[:16000],  # Truncate to first 16k chars
        "schedule_text": schedule_text[:6000]  # Truncate to first 4k chars
    }

    completion = client.chat.completions.create(
        model = "gpt-5",
        response_format = {
            "type": "json_object",
        },
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(model_input)},
        ],
    )

    raw = completion.choices[0].message.content
    data = json.loads(raw)
    sections: list[CourseSection] = []
    for sec in data.get("sections", []):
        meeting_patterns = [
            MeetingPattern(**mp) for mp in sec.get("meeting_patterns", [])
        ]
        explicit_meetings = [
            ExplicitMeeting(**em) for em in sec.get("explicit_meetings", [])
        ]
        section = CourseSection(
            section_id=sec.get("section_id", ""),
            instructors=sec.get("instructors", []),
            meeting_patterns=meeting_patterns,
            explicit_meetings=explicit_meetings
        )
        sections.append(section)


    parsed = ParsedSyllabus(
        course_code=data.get("course_code", ""),
        course_title=data.get("course_title", ""),
        term=data.get("term", ""),
        timezone=data.get("timezone", ""),
        sections=sections,
        assignments=[
            Assignment(**a) for a in data.get("assignments", [])
        ],
        schedule=[
            ScheduleEntry(**s) for s in data.get("schedule", [])
        ],
        policies=Policies(**data.get("policies", {}))
    )


    return asdict(parsed)  # FastMCP returns structured result


# ----------- Main Entry Point ------------
if __name__ == "__main__":
    mcp.run()
