# -*- coding: utf-8 -*-
import json

from fastmcp import FastMCP
from academic_planner.models import PlannedEvent, PlannedReminder, Plan
from prompts import load_prompt
from syllabus_server.models import ParsedSyllabus

mcp = FastMCP("AcademicPlanner")

SYSTEM_PROMPT = load_prompt("academic_planner_system_prompt")

@mcp.tool()
def create_academic_plan(
        syllabi: list[ParsedSyllabus],
) -> Plan:
    """Creates an academic plan from ParsedSyllabus.

    :param syllabi: The list of ParsedSyllabus objects.
    :return: A Plan object containing events and reminders.
    """

    completion = mcp.chat.completions.create(
        model="gpt-5",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": {
                    "syllabi": [s.__dict__ for s in syllabi],
                },
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

