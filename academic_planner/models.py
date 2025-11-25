# -*- coding: utf-8 -*-
from dataclasses import dataclass, field


@dataclass
class PlannedEvent:
    """A planned calendar event."""
    title: str
    start: str
    end: str
    location: str = ""


@dataclass
class PlannedReminder:
    """A planned reminder."""
    title: str
    due: str
    notes: str = ""


@dataclass
class ResolvedAssignment:
    """Assignment with resolved due date and classification."""
    course_code: str
    title: str
    due: str  # ISO datetime string (resolved from potentially ambiguous syllabus text)
    weight_percent: float
    category: str
    is_major: bool  # True if major assignment, False if minor
    notes: str = ""


@dataclass
class Plan:
    """Complete plan with events, reminders, and resolved assignments."""
    events: list[PlannedEvent] = field(default_factory=list)
    reminders: list[PlannedReminder] = field(default_factory=list)
    assignments: list[ResolvedAssignment] = field(default_factory=list)
