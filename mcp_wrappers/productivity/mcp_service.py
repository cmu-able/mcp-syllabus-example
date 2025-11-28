"""
MCP wrapper for productivity service.

This module maintains the original MCP tool signatures but makes HTTP calls
to the distributed productivity service. It handles serialization/deserialization
between dataclass and Pydantic models for calendar events and reminders.
"""
from __future__ import annotations

import os
from dataclasses import asdict

import httpx
from fastmcp import FastMCP

# Import original dataclass models for MCP interface compatibility
from productivity_server.models import CalendarEvent, Reminder
# Import Pydantic models for HTTP serialization
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
            
        # Convert response back to original dataclass format
        pydantic_result = PydanticCalendarEvent(**response.json())
        dataclass_result = _pydantic_to_dataclass_calendar_event(pydantic_result)
        
        return dataclass_result
        
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
            
        # Convert response back to original dataclass format
        pydantic_result = PydanticReminder(**response.json())
        dataclass_result = _pydantic_to_dataclass_reminder(pydantic_result)
        
        return dataclass_result
        
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
        # Convert dataclass events to Pydantic for HTTP serialization
        pydantic_events = []
        for event in events:
            event_dict = asdict(event)
            pydantic_events.append(PydanticCalendarEvent(**event_dict))
        
        request = CreateCalendarEventsBulkRequest(events=pydantic_events)
        
        # Make HTTP call with standard timeout
        with httpx.Client(timeout=STANDARD_TIMEOUT) as client:
            response = client.post(
                f"{PRODUCTIVITY_SERVICE_URL}/calendar/events",
                json=request.model_dump(),
            )
            response.raise_for_status()
            
        # Convert response back to original dataclass format
        response_data = response.json()
        dataclass_results = []
        for event_data in response_data:
            pydantic_event = PydanticCalendarEvent(**event_data)
            dataclass_event = _pydantic_to_dataclass_calendar_event(pydantic_event)
            dataclass_results.append(dataclass_event)
        
        return dataclass_results
        
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
        # Convert dataclass reminders to Pydantic for HTTP serialization
        pydantic_reminders = []
        for reminder in reminders_list:
            reminder_dict = asdict(reminder)
            pydantic_reminders.append(PydanticReminder(**reminder_dict))
        
        request = CreateRemindersBulkRequest(reminders_list=pydantic_reminders)
        
        # Make HTTP call with standard timeout
        with httpx.Client(timeout=STANDARD_TIMEOUT) as client:
            response = client.post(
                f"{PRODUCTIVITY_SERVICE_URL}/reminders",
                json=request.model_dump(),
            )
            response.raise_for_status()
            
        # Convert response back to original dataclass format
        response_data = response.json()
        dataclass_results = []
        for reminder_data in response_data:
            pydantic_reminder = PydanticReminder(**reminder_data)
            dataclass_reminder = _pydantic_to_dataclass_reminder(pydantic_reminder)
            dataclass_results.append(dataclass_reminder)
        
        return dataclass_results
        
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
            
        # Convert response back to original dataclass format
        response_data = response.json()
        dataclass_results = []
        for event_data in response_data:
            pydantic_event = PydanticCalendarEvent(**event_data)
            dataclass_event = _pydantic_to_dataclass_calendar_event(pydantic_event)
            dataclass_results.append(dataclass_event)
        
        return dataclass_results
        
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
            
        # Convert response back to original dataclass format
        response_data = response.json()
        dataclass_results = []
        for reminder_data in response_data:
            pydantic_reminder = PydanticReminder(**reminder_data)
            dataclass_reminder = _pydantic_to_dataclass_reminder(pydantic_reminder)
            dataclass_results.append(dataclass_reminder)
        
        return dataclass_results
        
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
            
        # Extract formatted display from response
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
            
        # Extract formatted display from response
        result = ShowRemindersResponse(**response.json())
        return result.formatted_reminders
        
    except httpx.TimeoutException:
        raise RuntimeError(f"Show reminders timed out after {STANDARD_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error from productivity service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling productivity service: {str(e)}")


def _pydantic_to_dataclass_calendar_event(pydantic_event: PydanticCalendarEvent) -> CalendarEvent:
    """Convert Pydantic CalendarEvent to dataclass CalendarEvent."""
    return CalendarEvent(
        title=pydantic_event.title,
        start=pydantic_event.start,
        end=pydantic_event.end,
        location=pydantic_event.location
    )


def _pydantic_to_dataclass_reminder(pydantic_reminder: PydanticReminder) -> Reminder:
    """Convert Pydantic Reminder to dataclass Reminder."""
    return Reminder(
        title=pydantic_reminder.title,
        due=pydantic_reminder.due,
        notes=pydantic_reminder.notes
    )


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
