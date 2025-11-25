# -*- coding: utf-8 -*-
import typing as t
from datetime import datetime

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
    :return: A Reminder object.
    """
    reminder = Reminder(
        title=title,
        due=due,
        notes=notes
    )
    add_reminder(reminder)
    return reminder


@mcp.tool()
def create_calendar_events_bulk(
        events: list[CalendarEvent]
) -> list[CalendarEvent]:
    """Creates multiple calendar events at once.

    :param events: List of CalendarEvent objects to create.
    :return: The list of created CalendarEvent objects.
    """
    for event in events:
        add_event(event)
    return events


@mcp.tool()
def create_reminders_bulk(
        reminders_list: list[Reminder]
) -> list[Reminder]:
    """Creates multiple reminders at once.

    :param reminders_list: List of Reminder objects to create.
    :return: The list of created Reminder objects.
    """
    for reminder in reminders_list:
        add_reminder(reminder)
    return reminders_list

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


def _format_datetime(iso_string: str) -> str:
    """Formats an ISO datetime string into a concise readable format.
    
    Converts ISO 8601 formatted datetime strings to format: 'Mon 1/15 2:30 PM'.
    If parsing fails, returns the original string.
    
    :param iso_string: ISO 8601 formatted datetime string.
    :return: Concise datetime string (e.g., 'Mon 1/15 2:30 PM').
    """
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        # Format: 'Mon 1/15 2:30 PM' (day of week, month/day, time)
        return dt.strftime("%a %-m/%-d %-I:%M %p")
    except (ValueError, AttributeError):
        # If parsing fails, return the original string
        return iso_string


def format_calendar_events() -> str:
    """Internal function to format calendar events as a clean table.
    
    :return: Formatted table string of all calendar events.
    """
    if not calendar_events:
        return "📅 No calendar events found."
    
    lines = []
    lines.append("📅 CALENDAR EVENTS")
    lines.append("="* 100)
    lines.append(f"{'#':<4} {'Title':<35} {'Start':<18} {'End':<18} {'Location':<20}")
    lines.append("-"* 100)
    
    for idx, event in enumerate(calendar_events, 1):
        title = event.title[:34] if len(event.title) > 34 else event.title
        location = event.location[:19] if event.location and len(event.location) > 19 else (event.location or "—")
        lines.append(
            f"{idx:<4} {title:<35} {_format_datetime(event.start):<18} "
            f"{_format_datetime(event.end):<18} {location:<20}"
        )
    
    lines.append("="* 100)
    lines.append(f"Total: {len(calendar_events)} event(s)")
    return "\n".join(lines)


def format_reminders() -> str:
    """Internal function to format reminders as a clean table.
    
    :return: Formatted table string of all reminders.
    """
    if not reminders:
        return "✅ No reminders found."
    
    lines = []
    lines.append("✅ REMINDERS")
    lines.append("="* 100)
    lines.append(f"{'#':<4} {'Title':<35} {'Due':<18} {'Notes':<40}")
    lines.append("-"* 100)
    
    for idx, reminder in enumerate(reminders, 1):
        title = reminder.title[:34] if len(reminder.title) > 34 else reminder.title
        notes = reminder.notes[:39] if reminder.notes and len(reminder.notes) > 39 else (reminder.notes or "—")
        lines.append(
            f"{idx:<4} {title:<35} {_format_datetime(reminder.due):<18} {notes:<40}"
        )
    
    lines.append("="* 100)
    lines.append(f"Total: {len(reminders)} reminder(s)")
    return "\n".join(lines)


@mcp.tool()
def show_calendar_events() -> str:
    """Displays all calendar events in a nicely formatted view using rich markup.
    
    Returns a formatted string showing all calendar events with their details
    including title, time range, and location. Events are numbered and separated
    by dividers for easy reading. Uses rich console markup for colors and styling.
    
    :return: Rich-formatted string of all calendar events, or a message if no events exist.
    """
    return format_calendar_events()


@mcp.tool()
def show_reminders() -> str:
    """Displays all reminders in a nicely formatted view using rich markup.
    
    Returns a formatted string showing all reminders with their details
    including title, due date, and notes. Reminders are numbered and
    separated by dividers for easy reading. Uses rich console markup for
    colors and styling.
    
    :return: Rich-formatted string of all reminders, or a message if no reminders exist.
    """
    return format_reminders()


if __name__ == "__main__":
    mcp.run()
