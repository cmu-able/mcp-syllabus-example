"""
Data models for syllabus parsing and representation.

This module contains all the dataclasses used to represent parsed syllabus information.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional


# Type literals for commonly used values
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