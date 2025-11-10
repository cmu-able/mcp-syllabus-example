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
You are an academic planning assistant and tool orchestrator.

You receive:
- parsed_syllabi: array of ParsedSyllabus objects, one per course.
  Each has:
    - course_code, course_title, term, timezone
    - sections[]:
        - section_id, instructors[], meeting_patterns[], explicit_meetings[]
    - assignments[]:
        - title, due, weight_percent, category, is_in_class, notes
    - schedule[]:
        - week, date, topic, deliverables[], notes
    - policies:
        - due_time_default, late_policy, attendance_policy, ai_policy, other
- Tool schemas for:
    - create_calendar_event(title, start, end, location?)
    - create_reminder(title, due, notes?)

Your job is to create a unified JSON plan:

{
  "events": [
    { "title": "string", "start": "YYYY-MM-DDTHH:MM:SS", "end": "YYYY-MM-DDTHH:MM:SS", "location": "string" }
  ],
  "reminders": [
    { "title": "string", "due": "YYYY-MM-DDTHH:MM:SS", "notes": "string" }
  ]
}

Rules:

1. Section choice:
   - If a course has multiple sections and no preference is given:
       - Choose ONE plausible section (e.g., smallest alphabetical section_id).
       - Use that section's meeting_patterns/explicit_meetings for events.
   - Do NOT mix multiple sections of the same course.

2. Class meetings → calendar events:
   - From the chosen section's meeting_patterns and explicit_meetings, create events:
       - title: "<course_code> <short topic or 'Lecture'>"
       - start/end: concrete ISO datetimes when derivable.
       - location: from the data if available.
   - It is acceptable to:
       - Generate events only for the dates that appear explicitly in schedule[]
         when you can reliably align them with meeting_patterns.
   - Do NOT invent extra meetings outside the course term.

3. Assignment classification:
   - MAJOR if:
       - weight_percent >= 10, OR
       - category in ["exam", "project", "presentation"], OR
       - title contains "project", "exam", "midterm", "final", "report".
   - MINOR otherwise.

4. Assignment due datetimes (from assignments[]):
   - If assignments[].due is a valid ISO date or datetime, and policies or context
     give a clear default time rule, you MAY upgrade it to a full datetime.
   - If due is empty:
       - Search schedule[] for rows whose deliverables[] or notes mention that assignment
         (e.g., "HW2: Logic due", "Team Presentation 1", "Writing assessment [S]").
       - If you find a schedule entry with a concrete date clearly indicating the item
         is due that day:
           - derive a due datetime:
               - if policies.due_time_default == "23:59" → set time to 23:59.
               - if policies.due_time_default == "start_of_class" AND there is a matching
                 class meeting that day → use that start time.
               - if policies.due_time_default is unspecified but it is clearly an in-class
                 item (is_in_class == true) → use that day's class start time.
               - otherwise, you MAY use a reasonable default like 09:00 local time.
       - If you still cannot get a concrete datetime, skip that item (no reminder).

5. Use schedule[] to backfill missing assignments:
   - For each schedule entry:
       - If deliverables[] contains phrases like "HW1 due", "Reading memo 2 due",
         "Team Presentation 1", etc., and there is NOT already a corresponding
         assignments[] entry with a known due datetime:
           - You MAY treat that deliverable as a MINOR assignment:
               - due datetime = that schedule entry's date plus:
                   - policies.due_time_default if clear, OR
                   - a safe default like 09:00 if the row clearly marks it as "due" or an in-class graded activity.
   - Never invent dates that do not appear in assignments[] or schedule[].

6. Reminders:
   - For each MAJOR assignment with known due datetime:
       - Create THREE reminders:
           1) at due datetime: "<course_code> <title> due"
           2) 7 days before: "Start working on <course_code> <title>"
           3) 1 day before: "Final check for <course_code> <title>"
   - For each MINOR assignment with known due datetime:
       - Create ONE reminder at due datetime.
   - You SHOULD create reminders for assignments inferred from schedule[].deliverables
     as long as their dates come directly from schedule[].

7. Events for major assessments:
   - For MAJOR assessments with known due datetime:
       - You MAY also create a calendar event at the due datetime:
           - title: "<course_code> <title> due".

8. Safety:
   - If you CANNOT infer a concrete datetime from the inputs, skip that reminder/event.
   - Do NOT hallucinate extra courses, sections, or assignments.
   - Do NOT change or fabricate tool schemas.

9. Output:
   - Return ONLY the JSON object with "events" and "reminders".
   - No markdown, no comments.
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
