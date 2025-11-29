"""
Mock syllabus service for testing without LLM calls.

This is a test version of the syllabus service that returns mock data
instead of making expensive LLM calls. Perfect for testing HTTP communication
and data serialization without hitting OpenAI.
"""
from __future__ import annotations

import typing as t
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from services.shared.models import (
    ParsedSyllabus as PydanticParsedSyllabus,
    ParseSyllabusRequest,
    AnswerQuestionRequest,
    AnswerQuestionResponse,
    Assignment as PydanticAssignment,
    CourseSection as PydanticCourseSection,
    ExplicitMeeting as PydanticExplicitMeeting,
    MeetingPattern as PydanticMeetingPattern,
    Policies as PydanticPolicies,
    ScheduleEntry as PydanticScheduleEntry,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Mock lifespan - no initialization needed."""
    print("🧪 Mock Syllabus Service starting - no LLM calls will be made")
    yield
    print("🧪 Mock Syllabus Service shutting down")


app = FastAPI(
    title="Mock Syllabus Service",
    description="Mock REST API for testing syllabus parsing without LLM calls",
    version="1.0.0-mock",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "mock-syllabus-service", "mode": "test"}


@app.post("/syllabus:parse", response_model=PydanticParsedSyllabus)
async def parse_syllabus(request: ParseSyllabusRequest) -> PydanticParsedSyllabus:
    """
    Mock syllabus parsing - returns realistic test data instantly.
    
    This simulates the structure and data types that would be returned
    by the real LLM-powered parsing, but with predictable test data.
    """
    try:
        # Return mock parsed syllabus data
        mock_data = _get_mock_parse_response(request.pdf_path_or_url)
        return PydanticParsedSyllabus(**mock_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mock parsing error: {str(e)}")


@app.post("/syllabus/qa", response_model=AnswerQuestionResponse)
async def answer_question(request: AnswerQuestionRequest) -> AnswerQuestionResponse:
    """
    Mock question answering - returns a predictable test response.
    
    This simulates answering questions about syllabus content without
    making expensive LLM calls.
    """
    try:
        # Generate mock answer based on the question
        mock_answer = _get_mock_question_response(
            request.question, 
            request.syllabus_data.course_code
        )
        
        return AnswerQuestionResponse(answer=mock_answer)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mock question answering error: {str(e)}")


def _get_mock_parse_response(pdf_path_or_url: str) -> dict[str, t.Any]:
    """
    Return mock syllabus parsing data that matches the expected structure.
    
    Args:
        pdf_path_or_url: The input PDF path/URL (used to vary the mock data)
    
    Returns:
        Dictionary matching the ParsedSyllabus structure
    """
    # Vary the course code based on the input to make testing more realistic
    course_suffix = "101" if "101" in pdf_path_or_url else "625"
    
    return {
        "course_code": f"TEST-{course_suffix}",
        "course_title": f"Mock Course {course_suffix}: Testing Fundamentals",
        "term": "Fall 2024",
        "timezone": "America/New_York",
        "sections": [
            {
                "section_id": "A",
                "instructors": ["Dr. Mock Instructor", "TA Test Helper"],
                "meeting_patterns": [
                    {
                        "kind": "lecture",
                        "days_of_week": ["Mon", "Wed"],
                        "start_time_local": "14:00",
                        "end_time_local": "15:20",
                        "location": "Mock Hall 101"
                    },
                    {
                        "kind": "recitation",
                        "days_of_week": ["Fri"],
                        "start_time_local": "10:00",
                        "end_time_local": "10:50",
                        "location": "Test Room 205"
                    }
                ],
                "explicit_meetings": [
                    {
                        "date": "2024-03-15",
                        "start": "2024-03-15T14:00:00-05:00",
                        "end": "2024-03-15T15:20:00-05:00",
                        "location": "Mock Hall 101",
                        "topic": "Midterm Exam",
                        "kind": "exam"
                    }
                ]
            }
        ],
        "assignments": [
            {
                "title": "Mock Assignment 1: Setup",
                "due": "2024-02-01T23:59:00-05:00",
                "weight_percent": 15.0,
                "category": "homework",
                "is_in_class": False,
                "notes": "Initial setup assignment"
            },
            {
                "title": "Mock Project: Build Something",
                "due": "2024-03-01T23:59:00-05:00",
                "weight_percent": 25.0,
                "category": "project",
                "is_in_class": False,
                "notes": "Major project deliverable"
            },
            {
                "title": "Midterm Exam",
                "due": "2024-03-15T14:00:00-05:00",
                "weight_percent": 30.0,
                "category": "exam",
                "is_in_class": True,
                "notes": "In-class comprehensive exam"
            },
            {
                "title": "Final Presentation",
                "due": "2024-04-30T14:00:00-05:00", 
                "weight_percent": 20.0,
                "category": "presentation",
                "is_in_class": True,
                "notes": "10-minute final presentation"
            },
            {
                "title": "Class Participation",
                "due": "",
                "weight_percent": 10.0,
                "category": "participation",
                "is_in_class": True,
                "notes": "Overall participation grade"
            }
        ],
        "schedule": [
            {
                "week": 1,
                "date": "2024-01-15",
                "topic": "Course Introduction and Testing Basics",
                "deliverables": [],
                "notes": "Overview of testing methodologies"
            },
            {
                "week": 2,
                "date": "2024-01-22",
                "topic": "Unit Testing Fundamentals",
                "deliverables": ["Mock Assignment 1: Setup"],
                "notes": "Hands-on with testing frameworks"
            },
            {
                "week": 7,
                "date": "2024-03-15",
                "topic": "Midterm Exam",
                "deliverables": ["Midterm Exam"],
                "notes": "Comprehensive exam covering weeks 1-6"
            },
            {
                "week": 15,
                "date": "2024-04-30",
                "topic": "Final Presentations",
                "deliverables": ["Final Presentation"],
                "notes": "Student project presentations"
            }
        ],
        "policies": {
            "due_time_default": "23:59",
            "late_policy": "10% penalty per day late, max 3 days",
            "attendance_policy": "Attendance required, 2 unexcused absences = letter grade reduction",
            "ai_policy": "AI tools allowed for brainstorming and code review, not for direct solution generation",
            "other": "See full syllabus document for academic integrity and accommodation policies"
        }
    }


def _get_mock_question_response(question: str, course_code: str) -> str:
    """
    Generate mock answers to questions about the syllabus.
    
    Args:
        question: The question being asked
        course_code: The course code to personalize the response
        
    Returns:
        Mock answer string
    """
    question_lower = question.lower()
    
    # Provide realistic mock responses based on question keywords
    if "late" in question_lower or "policy" in question_lower:
        return f"According to the {course_code} syllabus, late assignments receive a 10% penalty per day late, with a maximum of 3 days accepted."
        
    elif "exam" in question_lower or "midterm" in question_lower:
        return f"The {course_code} midterm exam is scheduled for March 15th, 2024, during regular class time in Mock Hall 101. It's worth 30% of your final grade."
        
    elif "assignment" in question_lower or "homework" in question_lower:
        return f"The {course_code} course has several assignments including setup work (15%), a major project (25%), and class participation (10%). All homework is due at 11:59 PM unless specified otherwise."
        
    elif "attendance" in question_lower:
        return f"Attendance is required for {course_code}. More than 2 unexcused absences will result in a letter grade reduction."
        
    elif "ai" in question_lower or "artificial intelligence" in question_lower:
        return f"AI tools are allowed in {course_code} for brainstorming and code review purposes, but not for direct solution generation. Always cite when AI tools are used."
        
    elif "grade" in question_lower or "grading" in question_lower:
        return f"The {course_code} grading breakdown is: Homework 15%, Project 25%, Midterm 30%, Final Presentation 20%, Participation 10%."
        
    else:
        return f"Mock response for {course_code}: '{question}' - This is a test answer that would normally be generated by an LLM based on the syllabus content."


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)