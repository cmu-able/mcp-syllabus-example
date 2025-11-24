# -*- coding: utf-8 -*-
from .models import CalendarEvent, Reminder


# In-memory storage for calendar events and reminders
# In a real application, this would be replaced with a persistent database


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