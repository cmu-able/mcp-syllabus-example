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
class Plan:
    """Complete plan with events and reminders."""
    events: list[PlannedEvent] = field(default_factory=list)
    reminders: list[PlannedReminder] = field(default_factory=list)