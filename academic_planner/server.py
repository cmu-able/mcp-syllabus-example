# -*- coding: utf-8 -*-
import json
import os

from fastmcp import FastMCP
from openai import OpenAI
from academic_planner.models import PlannedEvent, PlannedReminder, Plan
from prompts import load_prompt
from syllabus_server.models import ParsedSyllabus

mcp = FastMCP("AcademicPlanner")

_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
client = OpenAI(api_key=_api_key)

SYSTEM_PROMPT = load_prompt("academic_planner_system_prompt")

@mcp.tool()
def create_academic_plan(
        syllabi: list[ParsedSyllabus],
) -> Plan:
    """Creates an academic plan from ParsedSyllabus.

    :param syllabi: The list of ParsedSyllabus objects.
    :return: A Plan object containing events and reminders.
    """

    from dataclasses import asdict
    
    # Serialize syllabi to dict format for LLM
    syllabi_dicts = [
        asdict(s) if hasattr(s, "__dataclass_fields__") else s
        for s in syllabi
    ]
    
    completion = client.chat.completions.create(
        model="gpt-5",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps({"syllabi": syllabi_dicts}),
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

