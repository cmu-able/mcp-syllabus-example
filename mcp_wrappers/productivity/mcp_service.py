"""
MCP wrapper for productivity service.

This module maintains the MCP tool signatures but makes HTTP calls
to the distributed productivity service. It uses Pydantic models end-to-end
for validation and serialization of calendar events and reminders.
"""
from __future__ import annotations

import os

import httpx
from fastmcp import FastMCP

from services.shared.models import (
    CalendarEvent,
    Reminder,
    CreateCalendarEventRequest,
    CreateReminderRequest,
    CreateCalendarEventsBulkRequest,
    CreateRemindersBulkRequest,
    ShowCalendarEventsResponse,
    ShowRemindersResponse,
)


mcp = FastMCP("ProductivityMCPWrapper")

# Service URL - configurable via environment variable
PRODUCTIVITY_SERVICE_URL = os.getenv("PRODUCTIVITY_SERVICE_URL", "http://localhost:8003")

# Timeout settings for fast operations (in seconds)
STANDARD_TIMEOUT = 30.0  # 30 seconds for standard CRUD operations


def _create_calendar_event(
    title: str,
    start: str,
    end: str,
    location: str = ""
) -> CalendarEvent:
    """
    Create a calendar event.
    
    This maintains the exact same signature as the original MCP tool
    but makes an HTTP call to the distributed productivity service.
    """
    try:
        request = CreateCalendarEventRequest(
            title=title,
            start=start,
            end=end,
            location=location
        )
        
        # Make HTTP call with standard timeout
        with httpx.Client(timeout=STANDARD_TIMEOUT) as client:
            response = client.post(
                f"{PRODUCTIVITY_SERVICE_URL}/calendar/event",
                json=request.model_dump(),
            )
            response.raise_for_status()
            
        return CalendarEvent(**response.json())
        
    except httpx.TimeoutException:
        raise RuntimeError(f"Calendar event creation timed out after {STANDARD_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error from productivity service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling productivity service: {str(e)}")


def _create_reminder(
    title: str,
    due: str,
    notes: str = ""
) -> Reminder:
    """
    Create a reminder.
    
    This maintains the exact same signature as the original MCP tool
    but makes an HTTP call to the distributed productivity service.
    """
    try:
        request = CreateReminderRequest(
            title=title,
            due=due,
            notes=notes
        )
        
        # Make HTTP call with standard timeout
        with httpx.Client(timeout=STANDARD_TIMEOUT) as client:
            response = client.post(
                f"{PRODUCTIVITY_SERVICE_URL}/reminders/reminder",
                json=request.model_dump(),
            )
            response.raise_for_status()
            
        return Reminder(**response.json())
        
    except httpx.TimeoutException:
        raise RuntimeError(f"Reminder creation timed out after {STANDARD_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error from productivity service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling productivity service: {str(e)}")


def _create_calendar_events_bulk(events: list[CalendarEvent]) -> list[CalendarEvent]:
    """
    Create multiple calendar events at once.
    
    This maintains the exact same signature as the original MCP tool
    but makes an HTTP call to the distributed productivity service.
    """
    try:
        request = CreateCalendarEventsBulkRequest(events=events)
        
        # Make HTTP call with standard timeout
        with httpx.Client(timeout=STANDARD_TIMEOUT) as client:
            response = client.post(
                f"{PRODUCTIVITY_SERVICE_URL}/calendar/events",
                json=request.model_dump(),
            )
            response.raise_for_status()
            
        response_data = response.json()
        return [CalendarEvent(**event_data) for event_data in response_data]
        
    except httpx.TimeoutException:
        raise RuntimeError(f"Bulk calendar events creation timed out after {STANDARD_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error from productivity service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling productivity service: {str(e)}")


def _create_reminders_bulk(reminders_list: list[Reminder]) -> list[Reminder]:
    """
    Create multiple reminders at once.
    
    This maintains the exact same signature as the original MCP tool
    but makes an HTTP call to the distributed productivity service.
    """
    try:
        request = CreateRemindersBulkRequest(reminders_list=reminders_list)
        
        # Make HTTP call with standard timeout
        with httpx.Client(timeout=STANDARD_TIMEOUT) as client:
            response = client.post(
                f"{PRODUCTIVITY_SERVICE_URL}/reminders",
                json=request.model_dump(),
            )
            response.raise_for_status()
            
        response_data = response.json()
        return [Reminder(**reminder_data) for reminder_data in response_data]
        
    except httpx.TimeoutException:
        raise RuntimeError(f"Bulk reminders creation timed out after {STANDARD_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error from productivity service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling productivity service: {str(e)}")


def _list_calendar_events() -> list[CalendarEvent]:
    """
    List all calendar events.
    
    This maintains the exact same signature as the original MCP tool
    but makes an HTTP call to the distributed productivity service.
    """
    try:
        # Make HTTP call with standard timeout
        with httpx.Client(timeout=STANDARD_TIMEOUT) as client:
            response = client.get(f"{PRODUCTIVITY_SERVICE_URL}/calendar/events")
            response.raise_for_status()
            
        response_data = response.json()
        return [CalendarEvent(**event_data) for event_data in response_data]
        
    except httpx.TimeoutException:
        raise RuntimeError(f"List calendar events timed out after {STANDARD_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error from productivity service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling productivity service: {str(e)}")


def _list_reminders() -> list[Reminder]:
    """
    List all reminders.
    
    This maintains the exact same signature as the original MCP tool
    but makes an HTTP call to the distributed productivity service.
    """
    try:
        # Make HTTP call with standard timeout
        with httpx.Client(timeout=STANDARD_TIMEOUT) as client:
            response = client.get(f"{PRODUCTIVITY_SERVICE_URL}/reminders")
            response.raise_for_status()
            
        response_data = response.json()
        return [Reminder(**reminder_data) for reminder_data in response_data]
        
    except httpx.TimeoutException:
        raise RuntimeError(f"List reminders timed out after {STANDARD_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error from productivity service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling productivity service: {str(e)}")


def _show_calendar_events() -> str:
    """
    Show all calendar events in a formatted display.
    
    This maintains the exact same signature as the original MCP tool
    but makes an HTTP call to the distributed productivity service.
    """
    try:
        # Make HTTP call with standard timeout
        with httpx.Client(timeout=STANDARD_TIMEOUT) as client:
            response = client.get(f"{PRODUCTIVITY_SERVICE_URL}/calendar/events:str")
            response.raise_for_status()
            
        result = ShowCalendarEventsResponse(**response.json())
        return result.formatted_events
        
    except httpx.TimeoutException:
        raise RuntimeError(f"Show calendar events timed out after {STANDARD_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error from productivity service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling productivity service: {str(e)}")


def _show_reminders() -> str:
    """
    Show all reminders in a formatted display.
    
    This maintains the exact same signature as the original MCP tool
    but makes an HTTP call to the distributed productivity service.
    """
    try:
        # Make HTTP call with standard timeout
        with httpx.Client(timeout=STANDARD_TIMEOUT) as client:
            response = client.get(f"{PRODUCTIVITY_SERVICE_URL}/reminders:str")
            response.raise_for_status()
            
        result = ShowRemindersResponse(**response.json())
        return result.formatted_reminders
        
    except httpx.TimeoutException:
        raise RuntimeError(f"Show reminders timed out after {STANDARD_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error from productivity service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling productivity service: {str(e)}")



# MCP tool wrappers that call the raw functions
@mcp.tool()
def create_calendar_event(title: str, start: str, end: str, location: str = "") -> CalendarEvent:
    """Creates a calendar event."""
    return _create_calendar_event(title, start, end, location)


@mcp.tool()
def create_reminder(title: str, due: str, notes: str = "") -> Reminder:
    """Creates a reminder."""
    return _create_reminder(title, due, notes)


@mcp.tool()
def create_calendar_events_bulk(events: list[CalendarEvent]) -> list[CalendarEvent]:
    """Creates multiple calendar events at once."""
    return _create_calendar_events_bulk(events)


@mcp.tool()
def create_reminders_bulk(reminders_list: list[Reminder]) -> list[Reminder]:
    """Creates multiple reminders at once."""
    return _create_reminders_bulk(reminders_list)


@mcp.tool()
def list_calendar_events() -> list[CalendarEvent]:
    """Lists all calendar events."""
    return _list_calendar_events()


@mcp.tool()
def list_reminders() -> list[Reminder]:
    """Lists all reminders."""
    return _list_reminders()


@mcp.tool()
def show_calendar_events() -> str:
    """Displays all calendar events in a nicely formatted view."""
    return _show_calendar_events()


@mcp.tool()
def show_reminders() -> str:
    """Displays all reminders in a nicely formatted view."""
    return _show_reminders()
