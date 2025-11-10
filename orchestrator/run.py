# -*- coding: utf-8 -*-
import os
import sys
import json
from dataclasses import dataclass, field, asdict

import click
from openai import OpenAI

from syllabus_server.server import parse_syllabus
from productivity_server.server import (
    create_calendar_event,
    create_reminder, get_calendar_events, get_reminders,
)


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@dataclass
class PlannedEvent:
    title: str
    start: str
    end: str
    location: str = ""


@dataclass
class PlannedReminder:
    title: str
    due: str
    notes: str = ""


@dataclass
class Plan:
    events: list[PlannedEvent] = field(default_factory=list)
    reminders: list[PlannedReminder] = field(default_factory=list)


SYSTEM_PROMPT = """
You are an academic planning assistant.

You receive:
- parsed_syllabi: array of ParsedSyllabus objects, one per course.
  Each has: course_title, timezone, policy_text, class_meetings[], assignments[].
- Tool schemas for:
    create_calendar_event(title, start, end, location?)
    create_reminder(title, due, notes?)

Your job:
1. For each course:
   a. Interpret policy_text to resolve vague rules like:
      - "All homework is due at the beginning of class"
      - "Unless otherwise stated"
   b. If an assignment due time is missing but a rule exists,
      fill in a reasonable ISO datetime based on that rule and the
      nearest relevant class_meeting.
2. If the course contains multiple sections, and no choice is specified, pick
   the first section that does not conflict with other courses' class_meetings.
3. Classify assignments:
   - MAJOR if:
       - weight_percent >= 10, OR
       - title contains "project", "exam", "midterm", "final", "report"
   - MINOR otherwise (quizzes, small homeworks < 5%, etc).
4. Create calendar events:
   - For every class_meeting with known start/end:
        -> one calendar event.
   - For MAJOR assessments with known due:
        -> optional calendar event on the due datetime (e.g. "API: Project 1 due").
5. Create reminders:
   - For MAJOR assessments:
        -> reminder at the due datetime.
        -> reminder 7 days before due ("Start working on ...").
        -> reminder 1 day before due ("Final check for ...").
   - For MINOR assessments:
        -> only ONE reminder at due datetime.
6. Avoid hallucinations:
   - If you CANNOT infer a concrete datetime, skip that item.
7. Output:
{
  "events": [ { "title", "start", "end", "location" } ],
  "reminders": [ { "title", "due", "notes" } ]
}

Rules:
- Use only data derivable from parsed_syllabi.
- You MAY infer a time from clear policies (e.g., "beginning of class" -> that day's class start time).
- Output MUST be valid JSON, no comments, no markdown.
"""


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
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps({"parsed_syllabi": parsed_syllabi,
                                       "tool_schemas": tool_schemas}),
            },
        ],
    )

    plan_json = completion.choices[0].message.content
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
def main(syllabus_pdfs, verbose):
    """Orchestrator to parse syllabi and create calendar events and reminders.

    SYLLABUS_PDFS: Paths to syllabus PDF files.
    """
    if not syllabus_pdfs:
        click.echo("Provide one or more syllabus PDF files.", err=True)
        raise SystemExit(1)

    click.echo(click.style(f"Processing {len(syllabus_pdfs)} syllabus PDFs...", fg="cyan"))
    parsed_syllabi = []
    for pdf_path in syllabus_pdfs:
        click.echo(f"   -> {pdf_path}")
        parsed = parse_syllabus(pdf_path)
        if verbose:
            click.echo(json.dumps(parsed, indent=2))
        parsed_syllabi.append(parsed)

    click.echo(click.style("Building plan...", fg="cyan"))
    plan = build_plan(parsed_syllabi)
    if verbose:
        click.echo("Plan:")
        click.echo(json.dumps(asdict(plan), indent=2))

    click.echo(click.style("Creating calendar events and reminders...", fg="cyan"))

    for event in plan.events:
        resp = create_calendar_event(
            title=event.title,
            start=event.start,
            end=event.end,
            location=event.location,
        )
        if verbose:
            click.echo(f"Created event: {resp}")

    for reminder in plan.reminders:
        resp = create_reminder(
            title=reminder.title,
            due=reminder.due,
            notes=reminder.notes,
        )
        if verbose:
            click.echo(f"Created reminder: {resp}")

    click.echo(click.style("✅ Done.", fg="green"))

    click.echo(click.style("Plan Summary:", fg="cyan"))
    calendar_events = get_calendar_events()
    click.echo(f"  Total calendar events: {len(calendar_events)}")
    reminders = get_reminders()
    click.echo(f"  Total reminders: {len(reminders)}")

    for event in calendar_events:
        click.echo(f"    - Event: {event.title} at {event.start} to {event.end}")
    for reminder in reminders:
        click.echo(f"    - Reminder: {reminder.title} due {reminder.due}")


if __name__ == "__main__":
    main()
