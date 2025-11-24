"""
Data models for productivity server calendar events and reminders.

This module contains all the dataclasses used to represent calendar events 
and reminders in the productivity server.
"""
from __future__ import annotations

from dataclasses import dataclass
import typing as t


@dataclass
class CalendarEvent:
    """Represents a calendar event with title, dates, and location."""
    title: str
    start: str
    end: str
    location: str = ""


@dataclass
class Reminder:
    """Represents a reminder with title, due date, and notes."""
    title: str
    due: str
    notes: str = ""