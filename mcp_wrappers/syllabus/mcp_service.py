"""
MCP wrapper for syllabus service.

This module maintains the original MCP tool signatures but makes HTTP calls
to the distributed syllabus service. It handles serialization/deserialization
between dataclass and Pydantic models, and implements proper timeouts for
long-running LLM operations.
"""
from __future__ import annotations

import os
from dataclasses import asdict

import httpx
from fastmcp import FastMCP

# Import original dataclass models for MCP interface compatibility
from syllabus_server.models import ParsedSyllabus
# Import Pydantic models for HTTP serialization
from services.shared.models import (
    ParsedSyllabus as PydanticParsedSyllabus,
    ParseSyllabusRequest,
    AnswerQuestionRequest,
    AnswerQuestionResponse,
)


mcp = FastMCP("SyllabusMCPWrapper")

# Service URL - configurable via environment variable
SYLLABUS_SERVICE_URL = os.getenv("SYLLABUS_SERVICE_URL", "http://localhost:8001")

# Timeout settings for LLM operations (in seconds)
PARSE_TIMEOUT = 300.0  # 5 minutes for syllabus parsing
QUESTION_TIMEOUT = 120.0  # 2 minutes for question answering


def _parse_syllabus(pdf_path_or_url: str) -> ParsedSyllabus:
    """
    Parse a syllabus PDF/URL into ParsedSyllabus.
    
    This maintains the exact same signature as the original MCP tool
    but makes an HTTP call to the distributed syllabus service.
    """
    try:
        # Prepare request
        request = ParseSyllabusRequest(pdf_path_or_url=pdf_path_or_url)
        
        # Make HTTP call with extended timeout for LLM processing
        with httpx.Client(timeout=PARSE_TIMEOUT) as client:
            response = client.post(
                f"{SYLLABUS_SERVICE_URL}/parse-syllabus",
                json=request.model_dump(),
            )
            response.raise_for_status()
            
        # Convert response back to original dataclass format
        pydantic_result = PydanticParsedSyllabus(**response.json())
        dataclass_result = _pydantic_to_dataclass_syllabus(pydantic_result)
        
        return dataclass_result
        
    except httpx.TimeoutException:
        raise RuntimeError(f"Syllabus parsing timed out after {PARSE_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error from syllabus service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling syllabus service: {str(e)}")


def _answer_syllabus_question(
    syllabus_data: ParsedSyllabus,
    question: str,
) -> str:
    """Answer a question about a single parsed syllabus using an LLM.
    
    This tool takes structured syllabus data and answers natural language questions
    about it. Examples:
    - "What are the course policies?"
    - "What is the late policy?"
    - "When is the first exam?"
    - "How many assignments are there?"
    
    Args:
        syllabus_data: The parsed syllabus data structure
        question: The natural language question to answer
        
    Returns:
        A natural language answer to the question
    """
    try:
        # Convert dataclass to Pydantic for HTTP serialization
        pydantic_syllabus = _dataclass_to_pydantic_syllabus(syllabus_data)
        request = AnswerQuestionRequest(
            syllabus_data=pydantic_syllabus,
            question=question,
        )
        
        # Make HTTP call with extended timeout for LLM processing
        with httpx.Client(timeout=QUESTION_TIMEOUT) as client:
            response = client.post(
                f"{SYLLABUS_SERVICE_URL}/answer-question",
                json=request.model_dump(),
            )
            response.raise_for_status()
            
        # Extract answer from response
        result = AnswerQuestionResponse(**response.json())
        return result.answer
        
    except httpx.TimeoutException:
        raise RuntimeError(f"Question answering timed out after {QUESTION_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error from syllabus service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling syllabus service: {str(e)}")


def _dataclass_to_pydantic_syllabus(syllabus: ParsedSyllabus) -> PydanticParsedSyllabus:
    """
    Convert dataclass ParsedSyllabus to Pydantic ParsedSyllabus.
    
    This handles the conversion between the original dataclass models used by
    the MCP interface and the Pydantic models used by the REST API.
    """
    # Convert to dict first, then to Pydantic model
    # This handles nested structures automatically
    syllabus_dict = asdict(syllabus)
    return PydanticParsedSyllabus(**syllabus_dict)


def _pydantic_to_dataclass_syllabus(pydantic_syllabus: PydanticParsedSyllabus) -> ParsedSyllabus:
    """
    Convert Pydantic ParsedSyllabus to dataclass ParsedSyllabus.
    
    This handles the conversion from REST API response back to the original
    dataclass format expected by the MCP interface.
    """
    from syllabus_server.models import (
        Assignment,
        CourseSection, 
        ExplicitMeeting,
        MeetingPattern,
        Policies,
        ScheduleEntry,
    )
    
    # Convert Pydantic to dict, then reconstruct dataclasses
    data = pydantic_syllabus.model_dump()
    
    # Reconstruct nested dataclasses
    sections = []
    for sec_data in data.get("sections", []):
        meeting_patterns = [MeetingPattern(**mp) for mp in sec_data.get("meeting_patterns", [])]
        explicit_meetings = [ExplicitMeeting(**em) for em in sec_data.get("explicit_meetings", [])]
        
        sections.append(CourseSection(
            section_id=sec_data.get("section_id", ""),
            instructors=sec_data.get("instructors", []),
            meeting_patterns=meeting_patterns,
            explicit_meetings=explicit_meetings,
        ))
    
    assignments = [Assignment(**a) for a in data.get("assignments", [])]
    schedule = [ScheduleEntry(**s) for s in data.get("schedule", [])]
    policies = Policies(**(data.get("policies", {})))
    
    return ParsedSyllabus(
        course_code=data.get("course_code", ""),
        course_title=data.get("course_title", ""),
        term=data.get("term", ""),
        timezone=data.get("timezone", ""),
        sections=sections,
        assignments=assignments,
        schedule=schedule,
        policies=policies,
    )


# MCP tool wrappers that call the raw functions
@mcp.tool()
def parse_syllabus(pdf_path_or_url: str) -> ParsedSyllabus:
    """Parse a syllabus PDF/URL into ParsedSyllabus."""
    return _parse_syllabus(pdf_path_or_url)


@mcp.tool()
def answer_syllabus_question(
    syllabus_data: ParsedSyllabus,
    question: str,
) -> str:
    """Answer a question about a single parsed syllabus using an LLM."""
    return _answer_syllabus_question(syllabus_data, question)
