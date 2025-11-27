"""
MCP Gateway Server - Unified entry point for all distributed services.

This server imports all MCP wrapper modules and provides a single interface
for accessing all tools across the distributed syllabus, academic planner,
and productivity services. It acts as a gateway that routes tool calls to
the appropriate distributed services via HTTP.
"""
from __future__ import annotations

import os
from fastmcp import FastMCP

# Import the raw functions from each MCP wrapper (not the decorated versions)
# This allows us to register them with our own unified FastMCP instance
from mcp_wrappers.syllabus.mcp_service import (
    _parse_syllabus, _answer_syllabus_question,
    SYLLABUS_SERVICE_URL
)
from mcp_wrappers.academic_planner.mcp_service import (
    _create_academic_plan, _show_assignment_summary,
    ACADEMIC_PLANNER_SERVICE_URL
)
from mcp_wrappers.productivity.mcp_service import (
    _create_calendar_event, _create_reminder, 
    _create_calendar_events_bulk, _create_reminders_bulk,
    _list_calendar_events, _list_reminders,
    _show_calendar_events, _show_reminders,
    PRODUCTIVITY_SERVICE_URL
)

# Import models for type hints
from syllabus_server.models import ParsedSyllabus
from academic_planner.models import Plan
from productivity_server.models import CalendarEvent, Reminder

# Create the unified MCP server
mcp = FastMCP("SyllabusDistributedGateway")


def get_service_status() -> dict[str, str]:
    """
    Get the status of all distributed services.
    
    This function checks the configured URLs for each service to help
    with debugging and service discovery.
    """
    return {
        "syllabus_service": SYLLABUS_SERVICE_URL,
        "academic_planner_service": ACADEMIC_PLANNER_SERVICE_URL,
        "productivity_service": PRODUCTIVITY_SERVICE_URL,
        "gateway_status": "running"
    }


# Register all tools from the imported raw functions with our unified MCP instance
# This creates a single entry point for all distributed services

# Syllabus Service Tools
@mcp.tool()
def parse_syllabus(pdf_path_or_url: str) -> ParsedSyllabus:
    """Parse a syllabus PDF/URL into ParsedSyllabus."""
    return _parse_syllabus(pdf_path_or_url)


@mcp.tool()
def answer_syllabus_question(syllabus_data: ParsedSyllabus, question: str) -> str:
    """Answer a question about a single parsed syllabus using an LLM."""
    return _answer_syllabus_question(syllabus_data, question)


# Academic Planner Service Tools
@mcp.tool()
def create_academic_plan(syllabi: list[ParsedSyllabus]) -> Plan:
    """Creates an academic plan from ParsedSyllabus."""
    return _create_academic_plan(syllabi)


@mcp.tool()
def show_assignment_summary(plan: Plan) -> str:
    """Display consolidated assignment list with resolved due dates across all courses."""
    return _show_assignment_summary(plan)


# Productivity Service Tools
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

@mcp.tool()
def get_gateway_info() -> dict[str, str]:
    """
    Get information about the MCP Gateway and connected services.
    
    This tool provides status information about the gateway and the
    URLs of all distributed services it connects to.
    """
    return get_service_status()


@mcp.tool()
def list_available_tools() -> dict[str, list[str]]:
    """
    List all available tools organized by service.
    
    This tool provides an overview of all tools available through
    the distributed architecture.
    """
    return {
        "syllabus_service": [
            "parse_syllabus - Parse a syllabus PDF/URL into structured data",
            "answer_syllabus_question - Answer questions about parsed syllabus content"
        ],
        "academic_planner_service": [
            "create_academic_plan - Create an academic plan from multiple syllabi", 
            "show_assignment_summary - Display formatted assignment summary"
        ],
        "productivity_service": [
            "create_calendar_event - Create a single calendar event",
            "create_reminder - Create a single reminder",
            "create_calendar_events_bulk - Create multiple calendar events",
            "create_reminders_bulk - Create multiple reminders", 
            "list_calendar_events - List all calendar events",
            "list_reminders - List all reminders",
            "show_calendar_events - Display formatted calendar events",
            "show_reminders - Display formatted reminders"
        ],
        "gateway_tools": [
            "get_gateway_info - Get gateway and service status information",
            "list_available_tools - List all available tools by service"
        ]
    }


if __name__ == "__main__":
    print("🌟 Starting MCP Gateway Server")
    print("📋 Available Services:")
    
    status = get_service_status()
    for service_name, service_url in status.items():
        if service_name != "gateway_status":
            print(f"  • {service_name}: {service_url}")
    
    print(f"\n🚀 Gateway Status: {status['gateway_status']}")
    print("🔧 All MCP tools from distributed services are now available!")
    print("\nTools available:")
    tools = list_available_tools()
    for service_name, tool_list in tools.items():
        print(f"\n📦 {service_name}:")
        for tool in tool_list:
            print(f"    - {tool}")
    
    print(f"\n🌐 Starting MCP server...")
    mcp.run()