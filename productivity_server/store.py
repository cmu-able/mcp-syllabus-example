# -*- coding: utf-8 -*-
from dataclasses import dataclass


@dataclass
class CalendarEvent:
    title: str
    start: str
    end: str
    location: str = ""


@dataclass
class Reminder:
    title: str
    due: str
    notes: str = ""


calendar_events: list[CalendarEvent] = []
reminders: list[Reminder] = []


def add_event(event: CalendarEvent) -> None:
    """Adds an event to the calendar.

    :param event: A dictionary representing the event details.
    """
    calendar_events.append(event)


def add_reminder(reminder:Reminder) -> None:
    """Adds a reminder.

    :param reminder: A dictionary representing the reminder details.
    """
    reminders.append(reminder)