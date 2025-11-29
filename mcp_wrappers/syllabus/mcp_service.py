"""
MCP wrapper for syllabus service.

This module maintains the original MCP tool signatures but makes HTTP calls
to the distributed syllabus service. It handles serialization/deserialization
between dataclass and Pydantic models, and implements proper timeouts for
long-running LLM operations.
"""
from __future__ import annotations

import os
import base64
from dataclasses import asdict
from pathlib import Path

import requests
from fastmcp import FastMCP

# Import original dataclass models for MCP interface compatibility
from syllabus_server.models import ParsedSyllabus
# Import Pydantic models for HTTP serialization
from services.shared.models import (
    ParsedSyllabus as PydanticParsedSyllabus,
    ParseSyllabusRequest,
    AnswerQuestionRequest,
    AnswerQuestionResponse,
    AnswerQuestionAboutSyllabiRequest,
)


mcp = FastMCP("SyllabusMCPWrapper")

# Service URL - configurable via environment variable
SYLLABUS_SERVICE_URL = os.getenv("SYLLABUS_SERVICE_URL", "http://localhost:8001")

# Timeout settings for LLM operations (in seconds)
PARSE_TIMEOUT = 600.0  # 10 minutes for syllabus parsing
QUESTION_TIMEOUT = 300.0  # 5 minutes for question answering


def _parse_syllabus(pdf_path_or_url: str) -> ParsedSyllabus:
    """
    Parse a syllabus PDF/URL into ParsedSyllabus.
    
    This maintains the exact same signature as the original MCP tool
    but makes an HTTP call to the distributed syllabus service.
    """
    try:
        # Determine if this is a URL or local file path
        if pdf_path_or_url.startswith('http://') or pdf_path_or_url.startswith('https://'):
            # For URLs, let the service handle the download
            request = ParseSyllabusRequest(pdf_path_or_url=pdf_path_or_url)
        else:
            # For local files, read the content and send it
            pdf_path = Path(pdf_path_or_url)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path_or_url}")
            
            pdf_content = pdf_path.read_bytes()
            pdf_content_base64 = base64.b64encode(pdf_content).decode('utf-8')
            request = ParseSyllabusRequest(pdf_content_base64=pdf_content_base64)
        
        # Make HTTP call with extended timeout for LLM processing
        # Using requests library instead of httpx for better compatibility with asyncio.to_thread()
        response = requests.post(
            f"{SYLLABUS_SERVICE_URL}/syllabus:parse",
            json=request.model_dump(),
            timeout=PARSE_TIMEOUT,
        )
        response.raise_for_status()
            
        # Convert response back to original dataclass format
        pydantic_result = PydanticParsedSyllabus(**response.json())
        dataclass_result = _pydantic_to_dataclass_syllabus(pydantic_result)
        
        return dataclass_result
        
    except requests.Timeout:
        raise RuntimeError(f"Syllabus parsing timed out after {PARSE_TIMEOUT} seconds")
    except requests.HTTPError as e:
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
        response = requests.post(
            f"{SYLLABUS_SERVICE_URL}/syllabus/qa",
            json=request.model_dump(),
            timeout=QUESTION_TIMEOUT,
        )
        response.raise_for_status()
            
        # Extract answer from response
        result = AnswerQuestionResponse(**response.json())
        return result.answer
        
    except requests.Timeout:
        raise RuntimeError(f"Question answering timed out after {QUESTION_TIMEOUT} seconds")
    except requests.HTTPError as e:
        raise RuntimeError(f"HTTP error from syllabus service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling syllabus service: {str(e)}")


def _answer_question_about_syllabi(
    syllabi_data: list[ParsedSyllabus],
    question: str,
) -> str:
    """Answer a question about multiple parsed syllabi using an LLM.
    
    This tool takes multiple structured syllabus data and answers questions that
    may involve comparison, consolidation, or analysis across courses. Examples:
    - "Consolidate all the course policies"
    - "Which course has the strictest late policy?"
    - "What's the total workload across all courses?"
    - "Compare the exam schedules"
    - "List all assignment due dates across courses"
    
    Args:
        syllabi_data: List of parsed syllabus data structures
        question: The natural language question to answer
        
    Returns:
        A natural language answer to the question
    """
    try:
        # Convert dataclasses to Pydantic for HTTP serialization
        pydantic_syllabi = [_dataclass_to_pydantic_syllabus(s) for s in syllabi_data]
        request = AnswerQuestionAboutSyllabiRequest(
            syllabi_data=pydantic_syllabi,
            question=question,
        )
        
        # Make HTTP call with extended timeout for LLM processing
        response = requests.post(
            f"{SYLLABUS_SERVICE_URL}/syllabi/qa",
            json=request.model_dump(),
            timeout=QUESTION_TIMEOUT,
        )
        response.raise_for_status()
            
        # Extract answer from response
        result = AnswerQuestionResponse(**response.json())
        return result.answer
        
    except requests.Timeout:
        raise RuntimeError(f"Question answering timed out after {QUESTION_TIMEOUT} seconds")
    except requests.HTTPError as e:
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


@mcp.tool()
def answer_question_about_syllabi(
    syllabi_data: list[ParsedSyllabus],
    question: str,
) -> str:
    """Answer a question about multiple parsed syllabi using an LLM."""
    return _answer_question_about_syllabi(syllabi_data, question)
