# -*- coding: utf-8 -*-
from fastmcp import FastMCP

from productivity_server.models import CalendarEvent, Reminder
from productivity_server.store import add_event, add_reminder, calendar_events, reminders

mcp = FastMCP("ProductivitySerer")


@mcp.tool()
def create_calendar_event(
        title: str,
        start: str,
        end: str,
        location: str = ""
) -> CalendarEvent:
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
    return event


@mcp.tool()
def create_reminder(
        title: str,
        due: str,
        notes: str = ""
) -> Reminder:
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
    return reminder

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
def list_calendar_events() -> list[CalendarEvent]:
    """Lists all calendar events.

    :return: A list of calendar event dictionaries.
    """
    return calendar_events


@mcp.tool()
def list_reminders() -> list[Reminder]:
    """Lists all reminders.

    :return: A list of reminder dictionaries.
    """
    return reminders


if __name__ == "__main__":
    mcp.run()