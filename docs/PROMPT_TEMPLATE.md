# Orchestrator Prompt Template

The orchestrator now supports customizable goal prompts through a template system.

## Overview

The system prompt for the orchestrator (`prompts/orchestrator_system_prompt.txt`) now uses a `{USER_GOAL}` placeholder that gets replaced with your custom goal at runtime.

## Usage

### Option 1: Command-line prompt (recommended)

Use the `--prompt` or `-p` option to specify your goal:

```bash
uv run python -m orchestrator.run_agent run \
  --prompt "Your goal is to extract all assignment due dates from syllabi" \
  pdfs/17603.pdf pdfs/17611.pdf
```

### Option 2: Interactive input

If you don't provide a `--prompt` option, the orchestrator will prompt you interactively:

```bash
uv run python -m orchestrator.run_agent run pdfs/17603.pdf
# You'll be prompted:
# Enter your goal for the orchestrator:
# (Press Ctrl+D or Ctrl+Z when done)
#
# [Type your goal here, can be multiple lines]
```

Then press:
- **macOS/Linux**: Ctrl+D
- **Windows**: Ctrl+Z

## Examples

### Example 1: Extract assignment deadlines
```bash
uv run python -m orchestrator.run_agent run \
  --prompt "Your goal is to create a list of all assignment due dates" \
  pdfs/17603.pdf
```

### Example 2: Create calendar events only
```bash
uv run python -m orchestrator.run_agent run \
  --prompt "Your goal is to parse syllabi and create calendar events for all class sessions" \
  pdfs/*.pdf
```

### Example 3: Analyze course workload
```bash
uv run python -m orchestrator.run_agent run \
  --prompt "Your goal is to analyze the workload distribution across the semester and identify busy weeks" \
  pdfs/17603.pdf pdfs/17611.pdf pdfs/17614.pdf
```

### Example 4: Default behavior (full academic plan)
The default prompt when not specified creates a unified academic plan with calendar events, reminders, and assignments:

```bash
uv run python -m orchestrator.run_agent run pdfs/17603.pdf
# Then enter: "Your goal is to take a set of PDFs and produce a unified academic plan with calendar events and reminders and assignments."
```

## How It Works

1. **Template Loading**: The system loads `prompts/orchestrator_system_prompt.txt`
2. **Placeholder Replacement**: The `{USER_GOAL}` placeholder is replaced with your custom goal
3. **Plan Generation**: The LLM uses the customized system prompt to create an execution plan
4. **Goal Context**: The PDF list and context are still provided separately in the user message

## Template Format

The prompt template (`prompts/orchestrator_system_prompt.txt`) has this structure:

```
You are a workflow orchestrator that coordinates distributed tool execution.

{USER_GOAL}

In addition to this goal, you will receive:
1. Available tools from a service registry...
[rest of the template]
```

The `{USER_GOAL}` is replaced at runtime with your custom goal statement.

## Tips

- Keep goals clear and specific
- Reference what you want to do with the PDFs
- The orchestrator will automatically know about the PDFs being processed
- You can focus on the desired outcome rather than implementation details
