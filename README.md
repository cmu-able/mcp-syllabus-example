# SyllabusMCP

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.13.1-green.svg)](https://github.com/jlowin/fastmcp)
[![OpenAI API](https://img.shields.io/badge/OpenAI-GPT--4-orange.svg)](https://openai.com/)

**SyllabusMCP** is an educational project developed for **CMU 17-625 API Design** that demonstrates the Model Context Protocol (MCP) architecture through a practical academic planning system. The project showcases how multiple MCP servers can work together to parse course syllabi and generate personalized academic workflows.

## 🎯 Project Overview

This system was created as a hands-on exploration of MCP server design and integration patterns for the CMU API Design course. It demonstrates:

- **Multi-server MCP architecture** with specialized components
- **AI-powered document parsing** using OpenAI's GPT models
- **Structured data extraction** from academic documents
- **Workflow orchestration** across distributed services
- **Type-safe data modeling** with Python dataclasses
- **Natural language goal specification** through interactive prompting

The system takes PDF syllabi as input and produces structured academic plans with calendar events, reminders, and assignment summaries.

## 🏗️ System Architecture

The project implements a **modular MCP ecosystem** with four main components:

### 📚 Syllabus Server
**Purpose**: PDF processing and structured data extraction

- **Location**: `syllabus_server/`
- **Key Functions**:
  - `parse_syllabus()` - Extracts structured data from PDF syllabi
  - `answer_syllabus_question()` - Natural language Q&A about syllabus content
- **Technologies**: pdfplumber, OpenAI GPT-4
- **Output**: Structured `ParsedSyllabus` objects with courses, assignments, schedules, and policies

### 📅 Productivity Server  
**Purpose**: Calendar and reminder management

- **Location**: `productivity_server/`
- **Key Functions**:
  - `create_calendar_event()` - Individual event creation
  - `create_reminder()` - Task reminder creation
  - `create_*_bulk()` - Batch operations for multiple items
  - `show_calendar_events()` - Formatted display of all events
- **Storage**: In-memory data store with `CalendarEvent` and `Reminder` models

### 🎓 Academic Planner
**Purpose**: Multi-course academic planning and analysis

- **Location**: `academic_planner/`
- **Key Functions**:
  - `create_academic_plan()` - Generates comprehensive plans from multiple syllabi
  - `show_assignment_summary()` - Cross-course assignment analysis
- **Features**: Assignment conflict detection, workload balancing, deadline resolution

### 🎭 Orchestrator
**Purpose**: System coordination and user interface

- **Location**: `orchestrator/`
- **Key Functions**:
  - CLI interface for batch processing
  - Multi-server workflow coordination
  - Rich console output with progress indicators
  - Plan execution and summary generation
- **Entry Point**: `orchestrator/run.py` - Main CLI application

## 💬 Natural Language Prompting

A key feature of SyllabusMCP is its **intelligent prompting system** that lets you specify goals in natural language. The AI orchestrator automatically creates execution plans based on your intentions.

### Interactive Prompting

#### Command-Line Prompts (Recommended)
Specify your goal directly with the `--prompt` option:

```bash
# Extract assignment deadlines
uv run python orchestrator/run_agent.py run \
  --prompt "Extract all assignment due dates from the syllabi" \
  syllabus1.pdf syllabus2.pdf

# Create calendar events only
uv run python orchestrator/run_agent.py run \
  --prompt "Parse syllabi and create calendar events for all class sessions" \
  pdfs/*.pdf

# Analyze workload distribution
uv run python orchestrator/run_agent.py run \
  --prompt "Analyze workload distribution and identify busy weeks" \
  syllabus1.pdf syllabus2.pdf
```

#### Interactive Input Mode
Run without `--prompt` for multi-line interactive input:

```bash
uv run python orchestrator/run_agent.py run syllabus1.pdf
# System prompts:
# Enter your goal for the orchestrator:
# (Press Ctrl+D or Ctrl+Z when done)
#
# [Type your detailed goal here, multiple lines supported]
```

### Question Answering

Ask natural language questions about syllabus content:

#### Single Syllabus Questions
```bash
# Course policy questions
uv run python orchestrator/run_agent.py run \
  --prompt "What are the course policies?" \
  syllabus.pdf

# Assignment information
uv run python orchestrator/run_agent.py run \
  --prompt "How many assignments are there and when are they due?" \
  syllabus.pdf

# Specific policy details
uv run python orchestrator/run_agent.py run \
  --prompt "What is the late submission policy?" \
  syllabus.pdf
```

#### Multi-Course Comparisons
```bash
# Compare policies across courses
uv run python orchestrator/run_agent.py run \
  --prompt "Compare the late submission policies across all courses" \
  course1.pdf course2.pdf course3.pdf

# Consolidate information
uv run python orchestrator/run_agent.py run \
  --prompt "Consolidate all course policies into a summary" \
  pdfs/*.pdf

# Workload analysis
uv run python orchestrator/run_agent.py run \
  --prompt "Which course has the heaviest workload?" \
  pdfs/*.pdf
```

### Example Prompts

| Goal Type | Example Prompt | Result |
|-----------|---------------|---------|
| **Full Planning** | "Create a unified academic plan with calendar events and reminders" | Complete semester schedule with events and alerts |
| **Assignment Focus** | "Extract all assignment due dates and create reminders" | Assignment-only workflow with due date alerts |
| **Policy Questions** | "What are the attendance policies across all courses?" | Natural language policy summary |
| **Workload Analysis** | "Show me the busiest weeks of the semester" | Analysis of deadline clusters |
| **Calendar Only** | "Create calendar events for lectures and exams only" | Class schedule without assignments |

### Advanced Features

- **Dry Run Mode**: See execution plans without running them (`--dry-run`)
- **Verbose Output**: View detailed JSON data and intermediate results (`--verbose`)
- **Custom Models**: Specify different OpenAI models (`--model gpt-4`)
- **Tool Discovery**: List all available MCP tools (`tools` command)

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+** 
- **OpenAI API Key** (for AI-powered parsing)
- **PDF files** (syllabi to process)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/cmu-able/mcp-syllabus-example.git
   cd mcp-syllabus-example
   ```

2. **Install dependencies using uv**:
   ```bash
   uv sync --extra dev
   ```

3. **Set up OpenAI API key**:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

### Basic Usage

#### Default Academic Planning
```bash
uv run python orchestrator/run.py syllabus1.pdf syllabus2.pdf
```

#### Custom Goal-Driven Processing
```bash
# Agent-based orchestrator with custom prompts
uv run python orchestrator/run_agent.py run \
  --prompt "Your custom goal here" \
  syllabus1.pdf syllabus2.pdf
```

#### Interactive Question Mode
```bash
# Ask questions about syllabi
uv run python orchestrator/run_agent.py run \
  --prompt "What is the grading breakdown?" \
  syllabus.pdf
```

#### Tool Discovery
```bash
# List all available MCP tools
uv run python orchestrator/run_agent.py tools

# Show specific tool schemas
uv run python orchestrator/run_agent.py tools syllabus_server.parse_syllabus
```

## 📊 Example Output

The system produces rich console output showing:

```
📚 ASSIGNMENTS SUMMARY
====================================================
#    Course     Title                           Due                  Weight   Type         Category        
----------------------------------------------------
1    17-625     Project Proposal               Mon 2/12 11:59 PM    15.0%    MAJOR        project         
2    17-625     Midterm Exam                   Wed 3/14 2:00 PM     25.0%    MAJOR        exam           
3    17-614     Lab Assignment 1               Fri 2/16 5:00 PM     10.0%    minor        lab            
====================================================
Total: 3 assignment(s)

By Course:
  17-625: 2 assignment(s), 40.0% total weight
  17-614: 1 assignment(s), 10.0% total weight
```

## 🧪 Testing

Run the test suite to verify functionality:

```bash
# Run all tests
uv run python -m pytest tests/ -v

# Test specific functionality
uv run python -m pytest tests/test_executor.py -v

# Test PDF extraction directly
uv run python tests/test_pdf_extract.py
```

## 🛠️ Development

### Project Structure
```
├── academic_planner/          # Multi-course planning server
│   ├── models.py             # Data models for academic planning
│   └── server.py             # MCP server implementation
├── orchestrator/             # System coordinator
│   ├── executor.py           # Plan execution logic
│   ├── models.py             # Orchestration data models
│   ├── run.py                # Main CLI entry point
│   └── run_agent.py          # Agent-based execution with prompting
├── productivity_server/       # Calendar and reminder management
│   ├── models.py             # Event and reminder models
│   ├── server.py             # MCP server implementation
│   └── store.py              # In-memory data storage
├── prompts/                  # AI prompt templates
│   ├── __init__.py           # Prompt loading utilities
│   ├── syllabus_parser_system_prompt.txt
│   ├── academic_planner_system_prompt.txt
│   └── orchestrator_system_prompt.txt
├── registry/                 # MCP tool registration system
├── syllabus_server/          # PDF processing and extraction
│   ├── models.py             # Syllabus data models
│   ├── pdf_utils.py          # PDF text extraction utilities
│   └── server.py             # MCP server implementation
└── tests/                    # Test suite
```

### Code Quality Standards

The project follows strict code quality guidelines:

- **Type annotations** for all functions using modern Python syntax
- **Docstrings** for all public functions and classes  
- **Black formatting** with 120-character line length
- **Dataclasses** instead of generic dictionaries for better type safety
- **Error handling** with appropriate exceptions

### Adding New Features

1. **New MCP Tools**: Add to appropriate server in `server.py` files
2. **Data Models**: Define in corresponding `models.py` files  
3. **Prompts**: Store AI prompts in `prompts/` directory as `.txt` files
4. **Tests**: Add test cases in `tests/` directory

## 🔧 Configuration

### Environment Variables
- `OPENAI_API_KEY` - Required for AI-powered parsing (GPT-4/GPT-5)

### Supported Input Formats
- **PDF files** - Local file paths or URLs
- **Multiple syllabi** - Batch processing supported
- **Various syllabus formats** - Handles different academic document structures

## 🎓 Educational Context

This project was developed for **CMU 17-625 API Design** to demonstrate:

1. **MCP Protocol Implementation** - Multiple coordinating servers
2. **API Design Patterns** - Type-safe interfaces and error handling  
3. **AI Integration** - Structured document processing with LLMs
4. **System Architecture** - Modular, extensible component design
5. **Developer Experience** - Rich CLI, comprehensive testing, clear documentation
6. **Natural Language Interfaces** - Interactive AI-driven workflow planning

## ⚠️ Important Notes

- **Private Data**: The system is designed to handle academic documents. Do not commit actual course syllabi to version control.
- **API Costs**: Uses OpenAI API calls - monitor usage to avoid unexpected charges
- **Development Only**: This is an educational project, not production-ready software

## 📝 License

This project is created for educational purposes as part of CMU 17-625 API Design course.

## 🤝 Contributing

As this is a course project, contributions are limited to enrolled students. For questions about the MCP implementation patterns demonstrated here, please refer to the course materials or instructor.