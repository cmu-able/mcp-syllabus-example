from __future__ import annotations

import asyncio
import os

from fastmcp import FastMCP

from services.shared.models import (
    CalendarEvent as PydanticCalendarEvent,
    Reminder as PydanticReminder,
    CreateCalendarEventRequest,
    CreateReminderRequest,
    CreateCalendarEventsBulkRequest,
    CreateRemindersBulkRequest,
    ShowCalendarEventsResponse,
    ShowRemindersResponse,
)

mcp = FastMCP("ProductivityServiceMCP")

# In-memory storage (same as REST service)
calendar_events: list[PydanticCalendarEvent] = []
reminders: list[PydanticReminder] = []


def _format_datetime(iso_string: str) -> str:
    from datetime import datetime

    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%a %-m/%-d %-I:%M %p")
    except (ValueError, AttributeError):
        return iso_string


def _format_calendar_events() -> str:
    if not calendar_events:
        return "📅 No calendar events found."

    lines = []
    lines.append("📅 CALENDAR EVENTS")
    lines.append("=" * 100)
    lines.append(f"{'#':<4} {'Title':<35} {'Start':<18} {'End':<18} {'Location':<20}")
    lines.append("-" * 100)

    for idx, event in enumerate(calendar_events, 1):
        title = event.title[:34] if len(event.title) > 34 else event.title
        location = event.location[:19] if event.location and len(event.location) > 19 else (event.location or "—")
        lines.append(
            f"{idx:<4} {title:<35} {_format_datetime(event.start):<18} "
            f"{_format_datetime(event.end):<18} {location:<20}"
        )

    lines.append("=" * 100)
    lines.append(f"Total: {len(calendar_events)} event(s)")
    return "\n".join(lines)


def _format_reminders() -> str:
    if not reminders:
        return "✅ No reminders found."

    lines = []
    lines.append("✅ REMINDERS")
    lines.append("=" * 100)
    lines.append(f"{'#':<4} {'Title':<35} {'Due':<18} {'Notes':<40}")
    lines.append("-" * 100)

    for idx, reminder in enumerate(reminders, 1):
        title = reminder.title[:34] if len(reminder.title) > 34 else reminder.title
        notes = reminder.notes[:39] if reminder.notes and len(reminder.notes) > 39 else (reminder.notes or "—")
        lines.append(f"{idx:<4} {title:<35} {_format_datetime(reminder.due):<18} {notes:<40}")

    lines.append("=" * 100)
    lines.append(f"Total: {len(reminders)} reminder(s)")
    return "\n".join(lines)


@mcp.tool()
def create_calendar_event(title: str, start: str, end: str, location: str = "") -> PydanticCalendarEvent:
    event = PydanticCalendarEvent(title=title, start=start, end=end, location=location)
    calendar_events.append(event)
    return event


@mcp.tool()
def create_reminder(title: str, due: str, notes: str = "") -> PydanticReminder:
    reminder = PydanticReminder(title=title, due=due, notes=notes)
    reminders.append(reminder)
    return reminder


@mcp.tool()
def create_calendar_events_bulk(events: list[PydanticCalendarEvent]) -> list[PydanticCalendarEvent]:
    calendar_events.extend(events)
    return events


@mcp.tool()
def create_reminders_bulk(reminders_list: list[PydanticReminder]) -> list[PydanticReminder]:
    reminders.extend(reminders_list)
    return reminders_list


@mcp.tool()
def list_calendar_events() -> list[PydanticCalendarEvent]:
    return calendar_events


@mcp.tool()
def list_reminders() -> list[PydanticReminder]:
    return reminders


@mcp.tool()
def show_calendar_events() -> str:
    return _format_calendar_events()


@mcp.tool()
def show_reminders() -> str:
    return _format_reminders()


if __name__ == "__main__":
    host = os.getenv("PRODUCTIVITY_MCP_HOST", "0.0.0.0")
    port = int(os.getenv("PRODUCTIVITY_MCP_PORT", "8603"))
    asyncio.run(mcp.run_streamable_http_async(host=host, port=port))
