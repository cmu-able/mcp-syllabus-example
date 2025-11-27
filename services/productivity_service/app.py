"""
FastAPI service for productivity operations.

This service extracts the core business logic from productivity_server/server.py
and exposes it as REST API endpoints. These are fast operations that manage
calendar events and reminders without LLM involvement.
"""
from __future__ import annotations

import typing as t
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException

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


# In-memory storage for calendar events and reminders
# In a distributed system, this would be replaced with a persistent database
calendar_events: list[PydanticCalendarEvent] = []
reminders: list[PydanticReminder] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup and cleanup on shutdown."""
    # No special initialization needed for productivity service
    yield


app = FastAPI(
    title="Productivity Service",
    description="REST API for calendar events and reminder management",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "productivity-service"}


@app.post("/create-calendar-event", response_model=PydanticCalendarEvent)
async def create_calendar_event(request: CreateCalendarEventRequest) -> PydanticCalendarEvent:
    """
    Create a single calendar event.
    
    This is a fast operation that adds an event to the in-memory store.
    """
    try:
        event = PydanticCalendarEvent(
            title=request.title,
            start=request.start,
            end=request.end,
            location=request.location
        )
        calendar_events.append(event)
        return event
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating calendar event: {str(e)}")


@app.post("/create-reminder", response_model=PydanticReminder)
async def create_reminder(request: CreateReminderRequest) -> PydanticReminder:
    """
    Create a single reminder.
    
    This is a fast operation that adds a reminder to the in-memory store.
    """
    try:
        reminder = PydanticReminder(
            title=request.title,
            due=request.due,
            notes=request.notes
        )
        reminders.append(reminder)
        return reminder
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating reminder: {str(e)}")


@app.post("/create-calendar-events-bulk", response_model=list[PydanticCalendarEvent])
async def create_calendar_events_bulk(request: CreateCalendarEventsBulkRequest) -> list[PydanticCalendarEvent]:
    """
    Create multiple calendar events at once.
    
    This is a fast operation that adds multiple events to the in-memory store.
    """
    try:
        created_events = []
        for event in request.events:
            calendar_events.append(event)
            created_events.append(event)
        return created_events
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating calendar events in bulk: {str(e)}")


@app.post("/create-reminders-bulk", response_model=list[PydanticReminder])
async def create_reminders_bulk(request: CreateRemindersBulkRequest) -> list[PydanticReminder]:
    """
    Create multiple reminders at once.
    
    This is a fast operation that adds multiple reminders to the in-memory store.
    """
    try:
        created_reminders = []
        for reminder in request.reminders_list:
            reminders.append(reminder)
            created_reminders.append(reminder)
        return created_reminders
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating reminders in bulk: {str(e)}")


@app.get("/list-calendar-events", response_model=list[PydanticCalendarEvent])
async def list_calendar_events() -> list[PydanticCalendarEvent]:
    """
    List all calendar events.
    
    Returns the raw list of calendar events as JSON objects.
    """
    return calendar_events


@app.get("/list-reminders", response_model=list[PydanticReminder])
async def list_reminders() -> list[PydanticReminder]:
    """
    List all reminders.
    
    Returns the raw list of reminders as JSON objects.
    """
    return reminders


@app.get("/show-calendar-events", response_model=ShowCalendarEventsResponse)
async def show_calendar_events() -> ShowCalendarEventsResponse:
    """
    Show all calendar events in a formatted display.
    
    Returns a nicely formatted table view of all calendar events.
    """
    try:
        formatted_display = _format_calendar_events()
        return ShowCalendarEventsResponse(formatted_events=formatted_display)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error formatting calendar events: {str(e)}")


@app.get("/show-reminders", response_model=ShowRemindersResponse)
async def show_reminders() -> ShowRemindersResponse:
    """
    Show all reminders in a formatted display.
    
    Returns a nicely formatted table view of all reminders.
    """
    try:
        formatted_display = _format_reminders()
        return ShowRemindersResponse(formatted_reminders=formatted_display)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error formatting reminders: {str(e)}")


def _format_datetime(iso_string: str) -> str:
    """
    Format an ISO datetime string into a concise readable format.
    
    Converts ISO 8601 formatted datetime strings to format: 'Mon 1/15 2:30 PM'.
    If parsing fails, returns the original string.
    """
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        # Format: 'Mon 1/15 2:30 PM' (day of week, month/day, time)
        return dt.strftime("%a %-m/%-d %-I:%M %p")
    except (ValueError, AttributeError):
        # If parsing fails, return the original string
        return iso_string


def _format_calendar_events() -> str:
    """
    Format calendar events as a clean table.
    
    Returns a formatted table string of all calendar events.
    """
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
    """
    Format reminders as a clean table.
    
    Returns a formatted table string of all reminders.
    """
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
        lines.append(
            f"{idx:<4} {title:<35} {_format_datetime(reminder.due):<18} {notes:<40}"
        )
    
    lines.append("=" * 100)
    lines.append(f"Total: {len(reminders)} reminder(s)")
    return "\n".join(lines)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)