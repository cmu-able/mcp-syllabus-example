"""
Shared Pydantic models for REST API serialization.

This module contains Pydantic equivalents of the dataclass models used throughout
the system, ensuring consistent JSON serialization across all services.
"""
from __future__ import annotations

import typing as t
from pydantic import BaseModel, Field


# Type literals for commonly used values
MeetingKind = t.Literal["lecture", "recitation", "lab", "exercise", "exam", "other"]
AssignmentCategory = t.Literal[
    "exam",
    "project", 
    "homework",
    "quiz",
    "participation",
    "presentation",
    "other",
]


class MeetingPattern(BaseModel):
    """
    Recurring meeting pattern like:
    - "MW 9:30-10:50 am, 3SC 265"
    """
    kind: MeetingKind = "lecture"
    days_of_week: list[str] = Field(default_factory=list)  # ["Mon", "Wed"]
    start_time_local: str = ""  # "HH:MM" 24h
    end_time_local: str = ""    # "HH:MM" 24h
    location: str = ""


class ExplicitMeeting(BaseModel):
    """
    A specific dated meeting row from a schedule table.
    """
    date: str = ""          # "YYYY-MM-DD"
    start: str = ""         # ISO datetime if known, else ""
    end: str = ""           # ISO datetime if known, else ""
    location: str = ""
    topic: str = ""
    kind: MeetingKind = "lecture"


class Assignment(BaseModel):
    """
    A graded (or clearly important) deliverable.
    """
    title: str = ""
    due: str = ""                   # ISO datetime if concrete; else ""
    weight_percent: float = 0.0
    category: AssignmentCategory = "other"
    is_in_class: bool = False
    notes: str = ""


class Policies(BaseModel):
    """
    Coarse policies relevant to planning and orchestration.
    """
    due_time_default: str = ""      # e.g. "start_of_class", "23:59", "unspecified"
    late_policy: str = ""
    attendance_policy: str = ""
    ai_policy: str = ""
    other: str = ""


class CourseSection(BaseModel):
    """
    One section of a multi-section course, e.g.:
    - Section A: Tue 9:30–10:50
    - Section B: Tue 12:30–1:50
    """
    section_id: str = ""
    instructors: list[str] = Field(default_factory=list)
    meeting_patterns: list[MeetingPattern] = Field(default_factory=list)
    explicit_meetings: list[ExplicitMeeting] = Field(default_factory=list)


class ScheduleEntry(BaseModel):
    """
    One row from a schedule/calendar table.
    Used to preserve the mapping of dates → topics → deliverables.
    """
    week: t.Optional[int] = None
    date: str = ""                                  # "YYYY-MM-DD" or ""
    topic: str = ""
    deliverables: list[str] = Field(default_factory=list)
    notes: str = ""


class ParsedSyllabus(BaseModel):
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
    sections: list[CourseSection] = Field(default_factory=list)
    assignments: list[Assignment] = Field(default_factory=list)
    schedule: list[ScheduleEntry] = Field(default_factory=list)
    policies: Policies = Field(default_factory=Policies)


# Academic Planner Models
class PlannedEvent(BaseModel):
    """A planned calendar event."""
    title: str
    start: str
    end: str
    location: str = ""


class PlannedReminder(BaseModel):
    """A planned reminder."""
    title: str
    due: str
    notes: str = ""


class ResolvedAssignment(BaseModel):
    """Assignment with resolved due date and classification."""
    course_code: str
    title: str
    due: str  # ISO datetime string (resolved from potentially ambiguous syllabus text)
    weight_percent: float
    category: str
    is_major: bool  # True if major assignment, False if minor
    notes: str = ""


class Plan(BaseModel):
    """Complete plan with events, reminders, and resolved assignments."""
    events: list[PlannedEvent] = Field(default_factory=list)
    reminders: list[PlannedReminder] = Field(default_factory=list)
    assignments: list[ResolvedAssignment] = Field(default_factory=list)


# Productivity Server Models
class CalendarEvent(BaseModel):
    """Represents a calendar event with title, dates, and location."""
    title: str
    start: str
    end: str
    location: str = ""


class Reminder(BaseModel):
    """Represents a reminder with title, due date, and notes."""
    title: str
    due: str
    notes: str = ""


# Request/Response Models for API endpoints
class ParseSyllabusRequest(BaseModel):
    """Request model for parsing a syllabus."""
    pdf_path_or_url: str


class AnswerQuestionRequest(BaseModel):
    """Request model for answering a question about a syllabus."""
    syllabus_data: ParsedSyllabus
    question: str


class AnswerQuestionResponse(BaseModel):
    """Response model for syllabus question answers."""
    answer: str


class CreatePlanRequest(BaseModel):
    """Request model for creating an academic plan."""
    syllabi: list[ParsedSyllabus]


class ShowAssignmentSummaryRequest(BaseModel):
    """Request model for showing assignment summary."""
    plan: Plan


class ShowAssignmentSummaryResponse(BaseModel):
    """Response model for assignment summary."""
    summary: str


# Productivity Server Request/Response Models
class CreateCalendarEventRequest(BaseModel):
    """Request model for creating a calendar event."""
    title: str
    start: str
    end: str
    location: str = ""


class CreateReminderRequest(BaseModel):
    """Request model for creating a reminder."""
    title: str
    due: str
    notes: str = ""


class CreateCalendarEventsBulkRequest(BaseModel):
    """Request model for creating multiple calendar events."""
    events: list[CalendarEvent]


class CreateRemindersBulkRequest(BaseModel):
    """Request model for creating multiple reminders."""
    reminders_list: list[Reminder]


class ShowCalendarEventsResponse(BaseModel):
    """Response model for formatted calendar events display."""
    formatted_events: str


class ShowRemindersResponse(BaseModel):
    """Response model for formatted reminders display."""
    formatted_reminders: str
