"""Agent-based dynamic orchestrator for tool execution planning.

This module uses an LLM to dynamically create execution plans based on available
tools from the registry and user goals.
"""
import asyncio
import json
import os
import sys
import typing as t
from dataclasses import asdict

import click
from openai import OpenAI
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table

from prompts import load_prompt
from registry import list_tool_schemas
from orchestrator.models import ExecutionPlan, ExecutionStep
from orchestrator.utils import expand_pdf_paths


# Initialize console for output
console = Console()

# Load system prompt template from file
SYSTEM_PROMPT_TEMPLATE = load_prompt("orchestrator_system_prompt")


def format_result_for_display(result: t.Any, verbose: bool) -> None:
    """Format and print a step result.
    
    Args:
        result: The result to format (dataclass, list, string, etc.)
        verbose: Whether to show full details for lists
    """
    if hasattr(result, "__dataclass_fields__"):
        # It's a dataclass - convert to dict for pretty printing
        result_dict = asdict(result)
        console.print("    [dim]Result:[/dim]")
        console.print(JSON(json.dumps(result_dict, indent=2)))
    elif isinstance(result, list) and result and hasattr(result[0], "__dataclass_fields__"):
        # List of dataclasses
        result_dicts = [asdict(item) for item in result]
        console.print(f"    [dim]Result: {len(result)} item(s)[/dim]")
        if verbose:
            console.print(JSON(json.dumps(result_dicts, indent=2)))
    elif isinstance(result, str) and result.strip():
        # Non-empty string
        console.print(f"    [dim]Result:[/dim] {result}")
    # Skip empty strings or other cases


def create_progress_callback(verbose: bool) -> t.Callable[[int, int, ExecutionStep, t.Optional[t.Any]], None]:
    """Create a progress callback function with verbose setting.
    
    Args:
        verbose: Whether to display full result details
        
    Returns:
        Progress callback function
    """
    def progress_callback(current: int, total: int, step: ExecutionStep, result: t.Optional[t.Any]) -> None:
        """Report progress as each step executes.
        
        Args:
            current: Current step number (1-indexed)
            total: Total number of steps
            step: The step being executed
            result: The result (None if starting, actual result if completed)
        """
        if result is None:
            # Step is starting
            console.print(f"  [{current}/{total}] ▶ Executing: {step.service_name}.{step.tool_name}")
        else:
            # Step completed
            console.print(f"  [{current}/{total}] ✓ Completed: {step.service_name}.{step.tool_name}")
            # Show result if verbose
            if verbose:
                format_result_for_display(result, verbose)
    
    return progress_callback

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def create_execution_plan(user_goal: str, goal_description: str, model: str = "gpt-4o") -> ExecutionPlan:
    """Create an execution plan using LLM based on available tools and user goal.
    
    Args:
        user_goal: The user's goal statement to insert into the system prompt
        goal_description: The detailed goal description for the user message
        model: OpenAI model to use for planning (default: gpt-4o)
        
    Returns:
        ExecutionPlan containing steps and rationale
        
    Raises:
        ValueError: If the LLM response is invalid or cannot be parsed
        RuntimeError: If no tools are available in the registry
    """
    # Get available tools from registry
    available_tools = await list_tool_schemas()
    
    if not available_tools:
        raise RuntimeError("No tools available in registry")
    
    # Format the system prompt with the user's goal
    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{USER_GOAL}", user_goal)
    
    # Prepare the prompt with available tools and user goal
    user_message = {
        "goal": goal_description,
        "available_tools": available_tools,
    }
    
    # Call OpenAI API to generate execution plan
    completion = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_message, indent=2)},
        ],
    )
    
    # Parse the response
    response_content = completion.choices[0].message.content
    if not response_content:
        raise ValueError("Empty response from LLM")
    
    try:
        plan_data = json.loads(response_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response from LLM: {e}")
    
    # Validate and construct ExecutionPlan
    if "steps" not in plan_data:
        raise ValueError("LLM response missing 'steps' field")
    
    steps = []
    for step_data in plan_data["steps"]:
        # Validate required fields
        required_fields = ["id", "service_name", "tool_name", "arguments"]
        for field in required_fields:
            if field not in step_data:
                raise ValueError(f"Step missing required field: {field}")
        
        steps.append(ExecutionStep(
            id=step_data["id"],
            service_name=step_data["service_name"],
            tool_name=step_data["tool_name"],
            arguments=step_data["arguments"],
            depends_on=step_data.get("depends_on", []),
        ))
    
    return ExecutionPlan(
        steps=steps,
        rationale=plan_data.get("rationale", "No rationale provided"),
    )


def validate_execution_plan(plan: ExecutionPlan, available_tools: list[dict]) -> list[str]:
    """Validate an execution plan against available tools.
    
    Args:
        plan: The execution plan to validate
        available_tools: List of tool schemas from the registry
        
    Returns:
        List of validation errors (empty if plan is valid)
    """
    errors = []
    
    # Build a map of available tools
    tool_map = {}
    for tool in available_tools:
        key = f"{tool['server']}.{tool['name']}"
        tool_map[key] = tool
    
    # Track step IDs for dependency validation
    step_ids = {step.id for step in plan.steps}
    
    for step in plan.steps:
        # Check if tool exists
        tool_key = f"{step.service_name}.{step.tool_name}"
        if tool_key not in tool_map:
            errors.append(
                f"Step '{step.id}': Tool '{tool_key}' not found in registry"
            )
        
        # Check dependencies exist
        for dep in step.depends_on:
            if dep not in step_ids:
                errors.append(
                    f"Step '{step.id}': Dependency '{dep}' not found in plan"
                )
    
    return errors


async def async_main(
    syllabus_pdfs: tuple[str, ...],
    dry_run: bool,
    model: str,
    verbose: bool = True,
    prompt: t.Optional[str] = None,
) -> None:
    """Run the orchestrator to process PDFs and execute plan.
    
    Args:
        syllabus_pdfs: Tuple of PDF file paths or directories to process
        dry_run: If True, show plan but don't execute
        model: OpenAI model to use for planning
        verbose: If True, show full details; if False, show minimal output
        prompt: Optional custom goal prompt. If not provided, prompts user for input
    """

    # Expand directories to PDF files
    pdf_files = expand_pdf_paths(syllabus_pdfs)
    
    # Get user goal from prompt option or interactive input
    if prompt:
        user_goal = prompt
    else:
        console.print("[bold cyan]Enter your goal for the orchestrator:[/bold cyan]")
        console.print("[dim](Press Ctrl+D or Ctrl+Z when done)[/dim]\n")
        user_goal = sys.stdin.read().strip()
        if not user_goal:
            console.print("[red]No goal provided. Exiting.[/red]")
            raise SystemExit(1)
    
    # Build context about the PDFs (without dictating the goal)
    pdf_list = ", ".join(pdf_files)
    goal_description = f"Process the following syllabus PDFs: {pdf_list}"

    # Display header (only in verbose mode)
    if verbose:
        console.print(
            Panel.fit(
                f"[bold blue]🤖 Agent-Based Dynamic Orchestrator[/bold blue]\n"
                f"Processing [bold]{len(pdf_files)}[/bold] syllabus PDF(s)\n"
                f"Model: [cyan]{model}[/cyan]",
                border_style="blue",
            )
        )

    # Create execution plan
    console.print("\n[bold green]Creating execution plan...[/bold green]")
    try:
        plan = await create_execution_plan(user_goal, goal_description, model=model)
    except Exception as e:
        console.print(f"[red]Error creating plan:[/red] {e}")
        raise SystemExit(1)

    # Display the plan
    if verbose:
        console.print("\n[bold]📋 Execution Plan[/bold]")
        console.print(f"[dim]Rationale:[/dim] {plan.rationale}\n")

    # Create a table for the steps
    steps_table = Table(show_header=True, header_style="bold magenta")
    steps_table.add_column("Step", style="cyan", width=8)
    steps_table.add_column("Service", style="green")
    steps_table.add_column("Tool", style="yellow")
    steps_table.add_column("Dependencies", style="blue")
    steps_table.add_column("Arguments", style="white")

    for step in plan.steps:
        deps = ", ".join(step.depends_on) if step.depends_on else "(none)"
        
        if verbose:
            args_str = json.dumps(step.arguments, indent=0)[:60]
            if len(json.dumps(step.arguments)) > 60:
                args_str += "..."
            steps_table.add_row(
                step.id,
                step.service_name,
                step.tool_name,
                deps,
                args_str,
            )
        else:
            steps_table.add_row(
                step.id,
                step.service_name,
                step.tool_name,
                deps,
            )

    console.print(steps_table)

    # Show full plan as JSON (only in verbose mode)
    if verbose:
        console.print("\n[dim]Full plan (JSON):[/dim]")
        plan_dict = {
            "steps": [asdict(step) for step in plan.steps],
            "rationale": plan.rationale,
        }
        console.print(JSON(json.dumps(plan_dict, indent=2)))

    # Validate the plan
    if verbose:
        console.print("\n[bold]Validating plan...[/bold]")
    available_tools = await list_tool_schemas()
    errors = validate_execution_plan(plan, available_tools)

    if errors:
        console.print("[red]❌ Plan validation failed:[/red]")
        for error in errors:
            console.print(f"  • {error}")
        raise SystemExit(1)
    elif verbose:
        console.print("[green]✓ Plan is valid[/green]")

    # Stop here if dry run
    if dry_run:
        console.print(
            "\n[yellow]Dry run mode - execution skipped[/yellow]"
        )
        return

    # Execute the plan
    console.print("\n[bold green]Executing plan...[/bold green]")
    
    from orchestrator.executor import execute_plan
    
    try:
        progress_callback = create_progress_callback(verbose)
        results = await execute_plan(plan, progress_callback=progress_callback)
        
        # Display summary of results
        if verbose:
            console.print("\n[bold]📊 Execution Results[/bold]")
        
        # Count created items
        total_events = 0
        total_reminders = 0
        
        for step_id, result in results.items():
            if isinstance(result, list):
                # Bulk operations
                if result:
                    item = result[0]
                    # Check if it's a dataclass or dict
                    if hasattr(item, "__dataclass_fields__"):
                        if hasattr(item, "start") and hasattr(item, "end"):
                            total_events += len(result)
                        elif hasattr(item, "due"):
                            total_reminders += len(result)
                    elif isinstance(item, dict):
                        if "start" in item and "end" in item:
                            total_events += len(result)
                        elif "due" in item:
                            total_reminders += len(result)
        
        summary_table = Table(show_header=False)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Count", style="green", justify="right")
        
        summary_table.add_row("📅 Calendar Events Created", str(total_events))
        summary_table.add_row("⏰ Reminders Created", str(total_reminders))
        summary_table.add_row("🔄 Steps Executed", str(len(results)))
        
        console.print(summary_table)
        
        # Display any string results (formatted output from display tools)
        # Only show multi-line formatted strings (like tables), not JSON
        for step_id, result in results.items():
            if isinstance(result, str) and result.strip() and "\n" in result and not result.strip().startswith("{"):
                console.print(f"\n{result}")
        
    except Exception as e:
        console.print(f"\n[red]❌ Execution failed:[/red] {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    @click.group(context_settings={"help_option_names": ["-h", "--help"]})
    def cli() -> None:
        """Agent-based orchestrator for syllabus processing."""
        pass
    
    @cli.command()
    @click.argument(
        "pdfs",
        nargs=-1,
        type=click.Path(exists=True),
        required=True,
    )
    @click.option(
        "--verbose",
        "-v",
        is_flag=True,
        help="Print full execution details including JSON data.",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        help="Generate and display the execution plan without executing it.",
    )
    @click.option(
        "--model",
        default="gpt-5",
        help="OpenAI model to use for planning (default: gpt-5).",
    )
    @click.option(
        "--prompt",
        "-p",
        type=str,
        help="Custom goal prompt for the orchestrator. If not provided, will prompt interactively.",
    )
    def run(
        pdfs: tuple[str, ...],
        verbose: bool,
        dry_run: bool,
        model: str,
        prompt: t.Optional[str],
    ) -> None:
        """Run the orchestrator to process syllabus PDFs.
        
        PDFS: Paths to syllabus PDF files or directories containing PDFs to process.
        
        Examples:
            # Process PDFs with minimal output (interactive prompt)
            python -m orchestrator.run_agent run pdfs/17603.pdf pdfs/17611.pdf
            
            # Process with custom goal prompt
            python -m orchestrator.run_agent run --prompt "Your goal is to extract all assignment due dates" pdfs/17603.pdf
            
            # Process with verbose output showing all JSON data
            python -m orchestrator.run_agent run --verbose pdfs/17603.pdf
            
            # Generate plan without executing (dry run)
            python -m orchestrator.run_agent run --dry-run pdfs/17603.pdf
        """
        asyncio.run(async_main(pdfs, dry_run=dry_run, model=model, verbose=verbose, prompt=prompt))
    
    @cli.command()
    @click.argument("tool_names", nargs=-1, type=str)
    def tools(tool_names: tuple[str, ...]) -> None:
        """Display information about available MCP tools.
        
        TOOL_NAMES: Optional list of specific tool names to display (format: server.tool_name).
                    If not provided, lists all available tools.
        
        Examples:
            # List all tools (names only)
            python -m orchestrator.run_agent tools
            
            # Show schema for specific tools
            python -m orchestrator.run_agent tools syllabus_server.parse_syllabus
        """
        async def show_tools() -> None:
            """Async function to retrieve and display tools."""
            available_tools = await list_tool_schemas()
            
            if not available_tools:
                console.print("[yellow]No tools available in registry[/yellow]")
                return
            
            # If no tool names specified, just list all tool names
            if not tool_names:
                console.print("[bold blue]📋 Available MCP Tools[/bold blue]\n")
                
                # Group by server
                tools_by_server: dict[str, list[str]] = {}
                for tool in available_tools:
                    server = tool["server"]
                    if server not in tools_by_server:
                        tools_by_server[server] = []
                    tools_by_server[server].append(tool["name"])
                
                for server, names in sorted(tools_by_server.items()):
                    console.print(f"[cyan]{server}[/cyan]")
                    for name in sorted(names):
                        console.print(f"  • {name}")
                    console.print()
                
                console.print("[dim]Use 'python -m orchestrator.run_agent tools <tool_name>...' to see schemas[/dim]")
                return
            
            # Filter to requested tools
            filtered_tools = []
            for tool_name in tool_names:
                # Parse tool_name in format "server.tool"
                if "." in tool_name:
                    server_name, name = tool_name.split(".", 1)
                    matching = [
                        t for t in available_tools
                        if t["server"] == server_name and t["name"] == name
                    ]
                else:
                    # If no server specified, search by tool name only
                    matching = [t for t in available_tools if t["name"] == tool_name]
                
                if matching:
                    filtered_tools.extend(matching)
                else:
                    console.print(f"[yellow]Warning: Tool '{tool_name}' not found[/yellow]")
            
            if not filtered_tools:
                console.print("[red]No matching tools found[/red]")
                return
            
            # Display schemas for requested tools
            for tool in filtered_tools:
                console.print(f"\n[bold cyan]{tool['server']}.{tool['name']}[/bold cyan]\n")
                
                # Display full tool info including description
                tool_data = {
                    "server": tool["server"],
                    "name": tool["name"],
                    "title": tool.get("title", ""),
                    "description": tool.get("description", ""),
                    "inputSchema": tool.get("inputSchema", {}),
                    "outputSchema": tool.get("outputSchema", {}),
                }
                console.print(JSON(json.dumps(tool_data, indent=2)))
        
        asyncio.run(show_tools())
    
    cli()

