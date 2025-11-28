"""
FastAPI service for syllabus parsing operations.

This service extracts the core business logic from syllabus_server/server.py
and exposes it as REST API endpoints. It handles LLM operations that can take
30-60 seconds for complex PDFs.
"""
from __future__ import annotations

import json
import os
import typing as t
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from openai import OpenAI

from services.shared.models import (
    ParsedSyllabus as PydanticParsedSyllabus,
    ParseSyllabusRequest,
    AnswerQuestionRequest,
    AnswerQuestionResponse,
    AnswerQuestionAboutSyllabiRequest,
    Assignment as PydanticAssignment,
    CourseSection as PydanticCourseSection,
    ExplicitMeeting as PydanticExplicitMeeting,
    MeetingPattern as PydanticMeetingPattern,
    Policies as PydanticPolicies,
    ScheduleEntry as PydanticScheduleEntry,
)
from syllabus_server.pdf_utils import extract_pdf_pages, extract_pdf_pages_from_content
from prompts import load_prompt


# Global OpenAI client - will be initialized on startup
client: OpenAI = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup and cleanup on shutdown."""
    global client
    
    # Startup: Initialize OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
    client = OpenAI(api_key=api_key)
    
    yield
    
    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title="Syllabus Service",
    description="REST API for syllabus parsing and question answering using LLM",
    version="1.0.0",
    lifespan=lifespan,
)


# System prompt for LLM
SYSTEM_PROMPT = load_prompt("syllabus_parser_system_prompt")


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "syllabus-service"}


@app.post("/parse-syllabus", response_model=PydanticParsedSyllabus)
async def parse_syllabus(request: ParseSyllabusRequest) -> PydanticParsedSyllabus:
    """
    Parse a syllabus PDF/URL into structured data.
    
    This endpoint can take 30-60 seconds for complex PDFs due to LLM processing.
    """
    try:
        # Extract PDF content
        if request.pdf_content:
            pages = extract_pdf_pages_from_content(request.pdf_content)
        else:
            pages = extract_pdf_pages(request.pdf_path_or_url)
        
        # Join all pages for global parsing
        full_text = "\\n\\n".join(pages)
        
        # Heuristic: pick likely schedule pages
        schedule_pages: list[str] = []
        for p in pages:
            lp = p.lower()
            if (
                "schedule" in lp
                or "course calendar" in lp
                or "course schedule" in lp
                or ("week" in lp and "date" in lp and "topic" in lp)
                or "deliverable" in lp
                or "assignment schedule" in lp
            ):
                schedule_pages.append(p)
        
        # Fallback: if no explicit schedule page detected, leave empty string
        schedule_text = "\\n\\n".join(schedule_pages) if schedule_pages else ""
        
        model_input = {
            "full_text": full_text[:30000],          # increased for full semester schedules
            "schedule_text": schedule_text[:15000],   # increased to capture complete schedule tables
        }
        
        # Call OpenAI API - this is the long-running LLM operation
        completion = client.chat.completions.create(
            model="gpt-5",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(model_input),
                },
            ],
        )
        
        raw = completion.choices[0].message.content or "{}"
        data = json.loads(raw)
        
        # Convert raw JSON → Pydantic models defensively
        parsed_syllabus = _convert_to_pydantic_syllabus(data)
        
        return parsed_syllabus
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing syllabus: {str(e)}")


@app.post("/answer-question", response_model=AnswerQuestionResponse)
async def answer_question(request: AnswerQuestionRequest) -> AnswerQuestionResponse:
    """
    Answer a question about a parsed syllabus using an LLM.
    
    This endpoint can take 10-30 seconds depending on the complexity of the question.
    """
    try:
        # Convert Pydantic syllabus to JSON for the LLM
        syllabus_json = request.syllabus_data.model_dump()
        
        system_prompt = (
            "You are a helpful assistant that answers questions about academic syllabi. "
            "You will be given structured syllabus data in JSON format and a question. "
            "Provide clear, concise answers based on the data provided. "
            "If the information isn't in the data, say so."
        )
        
        user_message = {
            "syllabus": syllabus_json,
            "question": request.question,
        }
        
        # Call OpenAI API
        completion = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_message)},
            ],
        )
        
        answer = completion.choices[0].message.content or "Unable to generate answer."
        
        return AnswerQuestionResponse(answer=answer)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")


@app.post("/answer-question-about-syllabi", response_model=AnswerQuestionResponse)
async def answer_question_about_syllabi(request: AnswerQuestionAboutSyllabiRequest) -> AnswerQuestionResponse:
    """
    Answer a question about multiple parsed syllabi using an LLM.
    
    This endpoint handles questions that involve comparison, consolidation, or analysis
    across multiple courses.
    """
    try:
        # Convert Pydantic syllabi to JSON for the LLM
        syllabi_json = [syllabus.model_dump() for syllabus in request.syllabi_data]
        
        system_prompt = (
            "You are a helpful assistant that answers questions about multiple academic syllabi. "
            "You will be given structured data for multiple courses in JSON format and a question. "
            "Provide clear, well-organized answers that may involve comparing, consolidating, or "
            "analyzing information across the courses. "
            "When appropriate, organize your response by course. "
            "If the information isn't in the data, say so."
        )
        
        user_message = {
            "syllabi": syllabi_json,
            "question": request.question,
        }
        
        # Call OpenAI API
        completion = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_message)},
            ],
        )
        
        answer = completion.choices[0].message.content or "Unable to generate answer."
        
        return AnswerQuestionResponse(answer=answer)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question about syllabi: {str(e)}")


def _convert_to_pydantic_syllabus(data: dict[str, t.Any]) -> PydanticParsedSyllabus:
    """
    Convert raw JSON from LLM response to Pydantic ParsedSyllabus model.
    
    Handles defensive conversion with fallback values for missing or invalid data.
    """
    # Sections
    sections: list[PydanticCourseSection] = []
    for sec in data.get("sections", []):
        meeting_patterns = [
            PydanticMeetingPattern(**mp) for mp in sec.get("meeting_patterns", []) or []
        ]
        explicit_meetings = [
            PydanticExplicitMeeting(**em) for em in sec.get("explicit_meetings", []) or []
        ]
        sections.append(
            PydanticCourseSection(
                section_id=sec.get("section_id", ""),
                instructors=sec.get("instructors", []) or [],
                meeting_patterns=meeting_patterns,
                explicit_meetings=explicit_meetings,
            )
        )
    
    # Assignments
    assignments: list[PydanticAssignment] = []
    for a in data.get("assignments", []) or []:
        assignments.append(
            PydanticAssignment(
                title=a.get("title", "") or "",
                due=a.get("due", "") or "",
                weight_percent=float(a.get("weight_percent", 0.0) or 0.0),
                category=a.get("category", "other") or "other",
                is_in_class=bool(a.get("is_in_class", False)),
                notes=a.get("notes", "") or "",
            )
        )
    
    # Schedule entries
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
    
    # Policies
    pol_src = data.get("policies", {}) or {}
    policies = PydanticPolicies(
        due_time_default=pol_src.get("due_time_default", "") or "",
        late_policy=pol_src.get("late_policy", "") or "",
        attendance_policy=pol_src.get("attendance_policy", "") or "",
        ai_policy=pol_src.get("ai_policy", "") or "",
        other=pol_src.get("other", "") or "",
    )
    
    parsed = PydanticParsedSyllabus(
        course_code=data.get("course_code", "") or "",
        course_title=data.get("course_title", "") or "",
        term=data.get("term", "") or "",
        timezone=data.get("timezone", "") or "",
        sections=sections,
        assignments=assignments,
        schedule=schedule,
        policies=policies,
    )
    
    return parsed


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)