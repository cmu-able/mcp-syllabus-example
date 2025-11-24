"""
Data models for orchestrating syllabus-based calendar events and reminders.

This module contains all the dataclasses used to represent planned events and reminders
generated from parsed syllabus information.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import typing as t


@dataclass
class PlannedEvent:
    """Represents a planned calendar event derived from syllabus information."""
    title: str
    start: str
    end: str
    location: str = ""


@dataclass
class PlannedReminder:
    """Represents a planned reminder derived from syllabus assignment information."""
    title: str
    due: str
    notes: str = ""


@dataclass
class Plan:
    """Container for all planned events and reminders from syllabi."""
    events: list[PlannedEvent] = field(default_factory=list)
    reminders: list[PlannedReminder] = field(default_factory=list)