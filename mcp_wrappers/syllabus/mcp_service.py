"""
MCP wrapper for syllabus service.

This module maintains the MCP tool signatures but makes HTTP calls
to the distributed syllabus service. It uses Pydantic models end-to-end for
validation and serialization, and implements proper timeouts for
long-running LLM operations.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

import requests
from fastmcp import FastMCP

from services.shared.models import (
    ParsedSyllabus,
    ParseSyllabusRequest,
    StructureSyllabusRequest,
    TextExtractionResponse,
    AnswerQuestionRequest,
    AnswerQuestionResponse,
    AnswerQuestionAboutSyllabiRequest,
)


mcp = FastMCP("SyllabusMCPWrapper")

# Service URL - configurable via environment variable
SYLLABUS_SERVICE_URL = os.getenv("SYLLABUS_SERVICE_URL", "http://localhost:8001")

# Timeout settings (in seconds)
TEXT_TIMEOUT = 180.0
STRUCTURE_TIMEOUT = 600.0  # LLM stage can be long
QUESTION_TIMEOUT = 300.0  # 5 minutes for question answering


def _resolve_pdf_in_request(pdf_path_or_url):
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
    return request


def _get_syllabus_text(pdf_path_or_url: str) -> TextExtractionResponse:
    """Call the syllabus text extraction endpoint and return raw text plus pages."""
    try:
        request = _resolve_pdf_in_request(pdf_path_or_url)

        response = requests.post(
            f"{SYLLABUS_SERVICE_URL}/syllabus/text",
            json=request.model_dump(),
            timeout=TEXT_TIMEOUT,
        )
        response.raise_for_status()

        extraction = TextExtractionResponse(**response.json())
        return extraction
    except requests.Timeout:
        raise RuntimeError(f"Syllabus text extraction timed out after {TEXT_TIMEOUT} seconds")
    except requests.HTTPError as e:
        raise RuntimeError(f"HTTP error from syllabus service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling syllabus text service: {str(e)}")


def _structure_syllabus(
    full_text: str,
    pages: list[str] | None = None,
    schedule_text: str | None = None,
) -> ParsedSyllabus:
    """Send extracted text to the structure endpoint and return ParsedSyllabus."""
    try:
        request = StructureSyllabusRequest(
            full_text=full_text,
            pages=pages,
            schedule_text=schedule_text,
        )

        response = requests.post(
            f"{SYLLABUS_SERVICE_URL}/syllabus/structure",
            json=request.model_dump(),
            timeout=STRUCTURE_TIMEOUT,
        )
        response.raise_for_status()

        return ParsedSyllabus(**response.json())
    except requests.Timeout:
        raise RuntimeError(f"Syllabus structuring timed out after {STRUCTURE_TIMEOUT} seconds")
    except requests.HTTPError as e:
        raise RuntimeError(f"HTTP error from syllabus service: {e.response.status_code} {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Error calling syllabus structure service: {str(e)}")


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
        request = AnswerQuestionRequest(
            syllabus_data=syllabus_data,
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
        request = AnswerQuestionAboutSyllabiRequest(
            syllabi_data=syllabi_data,
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



# MCP tool wrappers that call the raw functions
@mcp.tool()
def get_syllabus_text(pdf_path_or_url: str) -> TextExtractionResponse:
    """Extract text and pages from a syllabus PDF/URL."""
    return _get_syllabus_text(pdf_path_or_url)


@mcp.tool()
def structure_syllabus(
    full_text: str,
    pages: list[str] | None = None,
    schedule_text: str | None = None,
) -> ParsedSyllabus:
    """Convert extracted syllabus text to structured data."""
    return _structure_syllabus(full_text, pages, schedule_text)


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
