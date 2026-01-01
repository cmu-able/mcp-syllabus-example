from __future__ import annotations

import asyncio
import json
import typing as t
from pathlib import Path

import os

from fastmcp import Context, FastMCP

from prompts import load_prompt
from services.shared.models import (
    AnswerQuestionAboutSyllabiRequest,
    AnswerQuestionRequest,
    ParsedSyllabus,
    ParseSyllabusRequest,
    StructureSyllabusRequest,
    TextExtractionResponse,
)
from services.shared.sampling_utils import extract_sampling_content
from syllabus_server.pdf_utils import extract_pdf_pages, extract_pdf_pages_from_content

mcp = FastMCP("SyllabusServiceMCP")

SYSTEM_PROMPT = load_prompt("syllabus_parser_system_prompt")

MAX_FULL_TEXT_CHARS = 30000
MAX_SCHEDULE_TEXT_CHARS = 15000


def _derive_schedule_text(pages: list[str] | None, provided_schedule_text: str | None) -> str:
    if provided_schedule_text:
        return provided_schedule_text
    if not pages:
        return ""
    schedule_pages: list[str] = []
    for page in pages:
        lp = page.lower()
        if (
            "schedule" in lp
            or "course calendar" in lp
            or "course schedule" in lp
            or ("week" in lp and "date" in lp and "topic" in lp)
            or "deliverable" in lp
            or "assignment schedule" in lp
        ):
            schedule_pages.append(page)
    return "\n\n".join(schedule_pages) if schedule_pages else ""


def _normalize_assignment_category(category: str) -> str:
    if not category:
        return "other"
    category_lower = category.lower().strip()
    valid = {"exam", "project", "homework", "quiz", "participation", "presentation", "other"}
    if category_lower in valid:
        return category_lower
    if "exam" in category_lower or "midterm" in category_lower or "final" in category_lower:
        return "exam"
    if "project" in category_lower or "report" in category_lower:
        return "project"
    if "homework" in category_lower or "hw" in category_lower or "assignment" in category_lower:
        return "homework"
    if "quiz" in category_lower or "test" in category_lower:
        return "quiz"
    if "participation" in category_lower or "attendance" in category_lower:
        return "participation"
    if "presentation" in category_lower or "present" in category_lower:
        return "presentation"
    return "other"


def _convert_to_pydantic_syllabus(data: dict[str, t.Any]) -> ParsedSyllabus:
    from services.shared.models import (
        Assignment as PydanticAssignment,
        CourseSection as PydanticCourseSection,
        ExplicitMeeting as PydanticExplicitMeeting,
        MeetingPattern as PydanticMeetingPattern,
        Policies as PydanticPolicies,
        ScheduleEntry as PydanticScheduleEntry,
    )

    sections: list[PydanticCourseSection] = []
    for sec in data.get("sections", []) or []:
        meeting_patterns = [PydanticMeetingPattern(**mp) for mp in sec.get("meeting_patterns", []) or []]
        explicit_meetings = [PydanticExplicitMeeting(**em) for em in sec.get("explicit_meetings", []) or []]
        sections.append(
            PydanticCourseSection(
                section_id=sec.get("section_id", "") or "",
                instructors=sec.get("instructors", []) or [],
                meeting_patterns=meeting_patterns,
                explicit_meetings=explicit_meetings,
            )
        )

    assignments: list[PydanticAssignment] = []
    for a in data.get("assignments", []) or []:
        raw_category = a.get("category", "other") or "other"
        normalized_category = _normalize_assignment_category(raw_category)
        assignments.append(
            PydanticAssignment(
                title=a.get("title", "") or "",
                due=a.get("due", "") or "",
                weight_percent=float(a.get("weight_percent", 0.0) or 0.0),
                category=normalized_category,
                is_in_class=bool(a.get("is_in_class", False)),
                notes=a.get("notes", "") or "",
            )
        )

    schedule: list[PydanticScheduleEntry] = []
    for s in data.get("schedule", []) or []:
        schedule.append(
            PydanticScheduleEntry(
                week=s.get("week", None),
                date=s.get("date", "") or "",
                topic=s.get("topic", "") or "",
                deliverables=s.get("deliverables", []) or [],
                notes=s.get("notes", "") or "",
            )
        )

    pol_src = data.get("policies", {}) or {}
    policies = PydanticPolicies(
        due_time_default=pol_src.get("due_time_default", "") or "",
        late_policy=pol_src.get("late_policy", "") or "",
        attendance_policy=pol_src.get("attendance_policy", "") or "",
        ai_policy=pol_src.get("ai_policy", "") or "",
        other=pol_src.get("other", "") or "",
    )

    return ParsedSyllabus(
        course_code=data.get("course_code", "") or "",
        course_title=data.get("course_title", "") or "",
        term=data.get("term", "") or "",
        timezone=data.get("timezone", "") or "",
        sections=sections,
        assignments=assignments,
        schedule=schedule,
        policies=policies,
    )


@mcp.tool()
def get_syllabus_text(
    pdf_path_or_url: str | None = None,
    pdf_content_base64: str | None = None,
) -> TextExtractionResponse:
    """Extract text and pages from a syllabus PDF or base64 content."""
    request = ParseSyllabusRequest(
        pdf_path_or_url=pdf_path_or_url,
        pdf_content_base64=pdf_content_base64,
    )
    if request.pdf_content:
        pages = extract_pdf_pages_from_content(request.pdf_content)
        source = "bytes"
    else:
        # Only URLs are permitted here; validator ensures this
        assert request.pdf_path_or_url is not None
        pages = extract_pdf_pages(request.pdf_path_or_url)
        source = "url"

    full_text = "\n\n".join(pages)
    truncated = False
    if len(full_text) > MAX_FULL_TEXT_CHARS:
        full_text = full_text[:MAX_FULL_TEXT_CHARS]
        truncated = True

    metadata = {"page_count": len(pages), "source": source, "truncated": truncated}
    return TextExtractionResponse(pages=pages, full_text=full_text, metadata=metadata)


@mcp.tool()
async def structure_syllabus(
    full_text: str,
    pages: list[str] | None = None,
    schedule_text: str | None = None,
    ctx: Context | None = None,
) -> ParsedSyllabus:
    """Convert extracted syllabus text into structured data via sampling."""
    if ctx is None or not hasattr(ctx, "sample"):
        raise RuntimeError("Sampling context is required but not available.")

    request = StructureSyllabusRequest(full_text=full_text, pages=pages, schedule_text=schedule_text)
    effective_schedule_text = _derive_schedule_text(request.pages, request.schedule_text)

    model_input = {
        "full_text": request.full_text[:MAX_FULL_TEXT_CHARS],
        "schedule_text": (effective_schedule_text or "")[:MAX_SCHEDULE_TEXT_CHARS],
    }

    # Construct user message combining system prompt and input
    # MCP sampling only supports user/assistant roles, not system
    user_content = f"{SYSTEM_PROMPT}\n\nInput:\n{json.dumps(model_input)}"

    sample_result = await ctx.sample(
        messages=user_content,
        model_preferences="gpt-5",
    )

    content = extract_sampling_content(sample_result, "structure_syllabus")

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Sampling returned invalid JSON: {exc}") from exc

    return _convert_to_pydantic_syllabus(data)


@mcp.tool()
async def answer_syllabus_question(syllabus_data: ParsedSyllabus, question: str, ctx: Context | None = None) -> str:
    """Answer a question about a single parsed syllabus using sampling."""
    if ctx is None or not hasattr(ctx, "sample"):
        raise RuntimeError("Sampling context is required but not available.")

    request = AnswerQuestionRequest(syllabus_data=syllabus_data, question=question)
    user_message = {"syllabus": request.syllabus_data.model_dump(), "question": request.question}
    system_prompt = (
        "You answer questions about a single academic syllabus. Use only the provided JSON data. "
        "If information is missing, say so."
    )
    
    # Combine system prompt and user message (MCP only supports user/assistant roles)
    user_content = f"{system_prompt}\n\nData:\n{json.dumps(user_message)}"

    sample_result = await ctx.sample(
        messages=user_content,
        model_preferences="gpt-5",
    )

    return extract_sampling_content(sample_result, "answer_syllabus_question")


@mcp.tool()
async def answer_question_about_syllabi(
    syllabi_data: list[ParsedSyllabus],
    question: str,
    ctx: Context | None = None,
) -> str:
    """Answer a question about multiple parsed syllabi using sampling."""
    if ctx is None or not hasattr(ctx, "sample"):
        raise RuntimeError("Sampling context is required but not available.")

    request = AnswerQuestionAboutSyllabiRequest(syllabi_data=syllabi_data, question=question)
    user_message = {"syllabi": [s.model_dump() for s in request.syllabi_data], "question": request.question}
    system_prompt = (
        "You answer questions that may compare or consolidate information across multiple academic syllabi. "
        "Use only the provided JSON data. If information is missing, say so."
    )
    
    # Combine system prompt and user message (MCP only supports user/assistant roles)
    user_content = f"{system_prompt}\n\nData:\n{json.dumps(user_message)}"

    sample_result = await ctx.sample(
        messages=user_content,
        model_preferences="gpt-5",
    )

    return extract_sampling_content(sample_result, "answer_question_about_syllabi")


if __name__ == "__main__":
    host = os.getenv("SYLLABUS_MCP_HOST", "0.0.0.0")
    port = int(os.getenv("SYLLABUS_MCP_PORT", "8601"))
    asyncio.run(mcp.run_streamable_http_async(host=host, port=port))
