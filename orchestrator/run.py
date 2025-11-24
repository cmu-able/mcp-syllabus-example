# -*- coding: utf-8 -*-
import os
import sys
import json
import asyncio
from dataclasses import asdict
import typing as t

import click
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.json import JSON
from rich.text import Text
from rich.tree import Tree
from rich.columns import Columns
from prompts import load_prompt

from syllabus_server.server import parse_syllabus, mcp as syllabus_mcp
from productivity_server.server import (
    create_calendar_event,
    create_reminder, get_calendar_events, get_reminders,
    mcp as productivity_mcp,
)
from orchestrator.models import Plan, PlannedEvent, PlannedReminder


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
console = Console()


def display_verbose_json(title: str, data: t.Any, expandable: bool = True) -> None:
    """Display JSON data in a rich, collapsible format."""
    json_obj = JSON(json.dumps(data, indent=2))
    
    if expandable:
        # Display as a collapsed summary with option to expand via separate flag
        tree = Tree(f"📋 {title}")
        tree.add(f"[dim]{len(json.dumps(data))} characters of JSON data[/dim]")
        console.print(Panel(tree, expand=False, border_style="dim"))
        
        # For verbose mode, always show the full data
        console.print(Panel(json_obj, title=f"📄 {title} - Details", expand=True, border_style="blue"))
    else:
        console.print(Panel(json_obj, title=f"📄 {title}", expand=True))


def format_datetime_human(iso_datetime: str) -> str:
    """Convert ISO datetime to human-readable format (MM/DD HH:MM)."""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
        return dt.strftime("%m/%d %H:%M")
    except (ValueError, AttributeError):
        # Fallback for malformed dates
        return iso_datetime


def truncate_title(title: str, max_length: int = 45) -> str:
    """Truncate title to max_length characters, adding ellipsis if needed."""
    if len(title) <= max_length:
        return title
    return title[:max_length-3] + "..."


def create_summary_table(events: list, reminders: list) -> Table:
    """Create a summary table for events and reminders."""
    table = Table(title="📅 Plan Summary", show_header=True, header_style="bold magenta")
    table.add_column("", style="cyan", width=3)  # Just emoji
    table.add_column("Title", style="white")
    table.add_column("Date/Time", style="yellow")
    
    # Add events
    for event in events:
        start_formatted = format_datetime_human(event.start)
        end_formatted = format_datetime_human(event.end)
        table.add_row(
            "📅",
            truncate_title(event.title),
            f"{start_formatted} → {end_formatted}"
        )
    
    # Add reminders
    for reminder in reminders:
        due_formatted = format_datetime_human(reminder.due)
        table.add_row(
            "⏰",
            truncate_title(reminder.title),
            due_formatted
        )
    
    return table



SYSTEM_PROMPT = load_prompt("orchestrator_system_prompt")


async def list_tool_schemas() -> list[dict]:
    """Collect and return JSON schemas of all available tools from MCP servers."""
    schemas = []
    
    # Get schemas from syllabus server
    syllabus_tools = await syllabus_mcp.get_tools()
    for tool_key, tool in syllabus_tools.items():
        schemas.append({
            "server": "syllabus_server",
            "name": tool_key,
            "title": tool.title or tool_key,
            "description": tool.description or "",
            "inputSchema": tool.parameters or {},
            "outputSchema": tool.output_schema or {},
        })
    
    # Get schemas from productivity server
    productivity_tools = await productivity_mcp.get_tools()
    for tool_key, tool in productivity_tools.items():
        schemas.append({
            "server": "productivity_server",
            "name": tool_key,
            "title": tool.title or tool_key,
            "description": tool.description or "",
            "inputSchema": tool.parameters or {},
            "outputSchema": tool.output_schema or {},
        })
    
    return schemas


def build_plan(parsed_syllabi: list[dict]) -> Plan:

    tool_schemas = {
        "create_calendar_event": {
            "required": ["title", "start", "end"],
            "optional": ["location"],
        },
        "create_reminder": {
            "required": ["title", "due"],
            "optional": ["notes"],
        },
    }

    completion = client.chat.completions.create(
        model="gpt-5",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps({"parsed_syllabi": parsed_syllabi,
                                       "tool_schemas": tool_schemas}),
            },
        ],
    )

    plan_json = completion.choices[0].message.content or "{}"
    plan_data = json.loads(plan_json)
    plan = Plan(
        events=[
            PlannedEvent(**event) for event in plan_data.get("events", [])
        ],
        reminders=[
            PlannedReminder(**reminder) for reminder in plan_data.get("reminders", [])
        ],
    )
    return plan


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument(
    "syllabus_pdfs",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.option("--list", "list_tools", is_flag=True, help="List all tool schemas without running the orchestrator.")
def main(syllabus_pdfs: tuple[str, ...], verbose: bool, list_tools: bool) -> None:
    """Orchestrator to parse syllabi and create calendar events and reminders.

    SYLLABUS_PDFS: Paths to syllabus PDF files.
    """
    # If list option is specified, display tool schemas and exit
    if list_tools:
        schemas = asyncio.run(list_tool_schemas())
        console.print(JSON(json.dumps(schemas, indent=2)))
        return
    
    if not syllabus_pdfs:
        console.print("[red]Error:[/red] Provide one or more syllabus PDF files.", file=sys.stderr)
        raise SystemExit(1)

    # Header
    console.print(
        Panel.fit(
            f"[bold blue]📚 Syllabus MCP Orchestrator[/bold blue]\n"
            f"Processing [bold]{len(syllabus_pdfs)}[/bold] syllabus PDFs",
            border_style="blue"
        )
    )

    # Parse syllabi with progress indicator
    parsed_syllabi = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        parse_task = progress.add_task("Parsing syllabi...", total=len(syllabus_pdfs))
        
        for pdf_path in syllabus_pdfs:
            progress.update(parse_task, description=f"Parsing {os.path.basename(pdf_path)}...")
            parsed = parse_syllabus(pdf_path)
            
            if verbose:
                display_verbose_json(f"Parsed Syllabus: {os.path.basename(pdf_path)}", parsed)
            else:
                console.print(f"   ✓ {pdf_path}")
                
            parsed_syllabi.append(parsed)
            progress.update(parse_task, advance=1)

    # Build plan
    with console.status("[bold green]Building unified plan...") as status:
        plan = build_plan(parsed_syllabi)
    
    if verbose:
        display_verbose_json("Generated Plan", asdict(plan))

    # Create events and reminders
    console.print("\n[bold cyan]📝 Creating calendar events and reminders...[/bold cyan]")
    
    created_events = []
    created_reminders = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        total_items = len(plan.events) + len(plan.reminders)
        create_task = progress.add_task("Creating items...", total=total_items)
        
        for event in plan.events:
            progress.update(create_task, description=f"Creating event: {event.title}")
            resp = create_calendar_event(
                title=event.title,
                start=event.start,
                end=event.end,
                location=event.location,
            )
            created_events.append(event)
            
            if verbose:
                console.print(f"   ✓ Event created: {resp}")
            progress.update(create_task, advance=1)

        for reminder in plan.reminders:
            progress.update(create_task, description=f"Creating reminder: {reminder.title}")
            resp = create_reminder(
                title=reminder.title,
                due=reminder.due,
                notes=reminder.notes,
            )
            created_reminders.append(reminder)
            
            if verbose:
                console.print(f"   ✓ Reminder created: {resp}")
            progress.update(create_task, advance=1)

    # Success message
    console.print("\n[bold green]✅ Processing complete![/bold green]")
    
    # Display summary
    calendar_events = get_calendar_events()
    reminders = get_reminders()
    
    # Statistics panel
    stats_text = Text()
    stats_text.append(f"Total calendar events: ", style="white")
    stats_text.append(f"{len(calendar_events)}", style="bold green")
    stats_text.append("\n")
    stats_text.append(f"Total reminders: ", style="white")
    stats_text.append(f"{len(reminders)}", style="bold green")
    
    console.print(Panel(stats_text, title="📊 Statistics", border_style="green"))
    
    # Detailed summary table
    if calendar_events or reminders:
        table = create_summary_table(calendar_events, reminders)
        console.print("\n", table)


if __name__ == "__main__":
    main()
