# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

SyllabusMCP is an educational project for building MCP (Model Context Protocol) servers. The project is structured as a Python package that will implement MCP servers for processing and analyzing academic syllabi.

## Architecture

The project follows a modular architecture with three main server components:

- **`syllabus_server/`**: Contains PDF processing utilities for extracting text from syllabus documents. Currently implements `extract_pdf_text()` function that handles both local files and remote URLs.
- **`productivity_server/`**: Intended for productivity-related MCP tools (currently empty).
- **`orchestrator/`**: Intended to coordinate between different MCP servers (currently empty).
- **`tests/`**: Contains pytest-based tests for the PDF extraction functionality.

## Development Commands

### Package Management
This project uses `uv` for Python package management:
```bash
uv sync                    # Install dependencies
uv sync --extra dev        # Install with development dependencies (includes pytest)
uv add <package>          # Add a new dependency
uv remove <package>       # Remove a dependency
```

### Running Code
The project is configured as an installable package, so imports work directly:
```bash
uv run python tests/test_pdf_extract.py          # Run test script directly
uv run python -c "from syllabus_server.pdf_utils import extract_pdf_text; print('Import works!')"
```

### Testing
```bash
uv run python -m pytest tests/ -v               # Run all tests with verbose output
uv run python -m pytest tests/test_pdf_extract.py -v   # Run specific test file
```

### Dependencies
Key dependencies include:
- `mcp[cli]>=1.21.0`: Model Context Protocol framework
- `pdfplumber>=0.11.8`: PDF text extraction
- `requests>=2.32.5`: HTTP requests for remote PDFs
- `openai>=2.7.1`: OpenAI integration
- `pytest>=7.0.0`: Testing framework (dev dependency)

## Code Structure Notes

### PDF Processing
The `syllabus_server.pdf_utils.extract_pdf_text()` function is the core PDF processing component. It:
- Handles both local file paths and remote URLs
- Uses temporary files for remote PDF processing
- Returns extracted text as a single string
- Raises appropriate exceptions for missing files

### MCP Integration
The project is set up to use the MCP framework but the actual MCP server implementations are not yet completed. The `mcp[cli]` dependency suggests this will be a CLI-based MCP server.

### Test Data
The project includes sample syllabus PDFs in `pdfs/` directory:
- `17603.pdf`: Communications for Software Leaders I syllabus
- `17611.pdf`: Additional course syllabus
- `17614.pdf`: Additional course syllabus

## Package Configuration
The project is properly configured as an installable Python package:
- Uses `hatchling` as the build backend
- Packages are specified in `pyproject.toml` 
- Development dependencies are isolated in the `dev` extra
- No need for manual `PYTHONPATH` management