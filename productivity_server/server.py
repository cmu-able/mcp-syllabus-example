# -*- coding: utf-8 -*-
from dataclasses import asdict
from mcp.server import FastMCP

from productivity_server.store import add_event, add_reminder, calendar_events, CalendarEvent, Reminder, reminders

mcp = FastMCP("ProductivitySerer")


@mcp.tool()
def create_calendar_event(
        title: str,
        start: str,
        end: str,
        location: str = ""
) -> dict:
    """Creates a calendar event.

    :param title: Title of the event.
    :param start: Start time in ISO format.
    :param end: End time in ISO format.
    :param location: Location of the event (optional).
    :return: A CalendarEvent object.
    """
    event = CalendarEvent(
        title=title,
        start=start,
        end=end,
        location=location
    )
    add_event(event)
    return {"status": "ok", "event": asdict(event)}


@mcp.tool()
def create_reminder(
        title: str,
        due: str,
        notes: str = ""
) -> dict:
    """Creates a reminder.

    :param title: Title of the reminder.
    :param due: Due time in ISO format.
    :param notes: Additional notes (optional).
    :return: A dictionary representing the reminder.
    """
    reminder = Reminder(
        title=title,
        due=due,
        notes=notes
    )
    add_reminder(reminder)
    return {"status": "ok", "reminder": asdict(reminder)}


def get_calendar_events() -> list[CalendarEvent]:
    """Internal function to get calendar events as dataclass objects.
    
    :return: A list of CalendarEvent objects.
    """
    return calendar_events


def get_reminders() -> list[Reminder]:
    """Internal function to get reminders as dataclass objects.
    
    :return: A list of Reminder objects.
    """
    return reminders


@mcp.tool()
def list_calendar_events() -> list[dict]:
    """Lists all calendar events.

    :return: A list of calendar event dictionaries.
    """
    return [asdict(event) for event in calendar_events]


@mcp.tool()
def list_reminders() -> list[dict]:
    """Lists all reminders.

    :return: A list of reminder dictionaries.
    """
    return [asdict(reminder) for reminder in reminders]


if __name__ == "__main__":
    mcp.run()