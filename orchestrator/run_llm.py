"""LLM-based dynamic orchestrator for tool execution planning.

This module uses an LLM to dynamically create execution plans based on available
tools from the registry and user goals.
"""
import json
import os
import typing as t

from openai import OpenAI

from prompts import load_prompt
from registry import list_tool_schemas
from orchestrator.models import ExecutionPlan, ExecutionStep


# Load system prompt from file
SYSTEM_PROMPT = load_prompt("orchestrator_system_prompt")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def create_execution_plan(user_goal: str, model: str = "gpt-4o") -> ExecutionPlan:
    """Create an execution plan using LLM based on available tools and user goal.
    
    Args:
        user_goal: The user's goal or task description
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
    
    # Prepare the prompt with available tools and user goal
    user_message = {
        "goal": user_goal,
        "available_tools": available_tools,
    }
    
    # Call OpenAI API to generate execution plan
    completion = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
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
    list_tools: bool,
    dry_run: bool,
    model: str,
) -> None:
    # Handle --list option
    if list_tools:
        console.print("[bold blue]📋 Available MCP Tools[/bold blue]\n")
        tools = await list_tool_schemas()

        if not tools:
            console.print("[yellow]No tools available in registry[/yellow]")
            return

        # Group tools by server
        tools_by_server: dict[str, list[dict]] = {}
        for tool in tools:
            server = tool["server"]
            if server not in tools_by_server:
                tools_by_server[server] = []
            tools_by_server[server].append(tool)

        # Display tools grouped by server
        for server, server_tools in sorted(tools_by_server.items()):
            table = Table(title=f"🔧 {server}", show_header=True, header_style="bold cyan")
            table.add_column("Tool Name", style="green")
            table.add_column("Description", style="white")

            for tool in server_tools:
                table.add_row(
                    tool["name"],
                    tool["description"] or "(no description)",
                )

            console.print(table)
            console.print()

        # Optionally show full JSON
        console.print("[dim]Full tool schemas (JSON):[/dim]")
        console.print(JSON(json.dumps(tools, indent=2)))
        return

    # Require PDF files for planning/execution
    if not syllabus_pdfs:
        console.print(
            "[red]Error:[/red] Provide one or more syllabus PDF files.\n"
            "Use --list to see available tools."
        )
        raise SystemExit(1)

    # Build user goal from PDF files
    pdf_list = ", ".join(syllabus_pdfs)
    user_goal = (
        f"Create a unified semester schedule from the following syllabus PDFs: {pdf_list}. "
        f"Parse each PDF, create an academic plan with all course events and assignments, "
        f"and add them to the calendar and reminder systems."
    )

    # Display header
    console.print(
        Panel.fit(
            f"[bold blue]🤖 LLM-Based Dynamic Orchestrator[/bold blue]\n"
            f"Processing [bold]{len(syllabus_pdfs)}[/bold] syllabus PDF(s)\n"
            f"Model: [cyan]{model}[/cyan]",
            border_style="blue",
        )
    )

    # Create execution plan
    console.print("\n[bold green]Creating execution plan...[/bold green]")
    try:
        plan = await create_execution_plan(user_goal, model=model)
    except Exception as e:
        console.print(f"[red]Error creating plan:[/red] {e}")
        raise SystemExit(1)

    # Display the plan
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

    console.print(steps_table)

    # Show full plan as JSON
    console.print("\n[dim]Full plan (JSON):[/dim]")
    plan_dict = {
        "steps": [asdict(step) for step in plan.steps],
        "rationale": plan.rationale,
    }
    console.print(JSON(json.dumps(plan_dict, indent=2)))

    # Validate the plan
    console.print("\n[bold]Validating plan...[/bold]")
    available_tools = await list_tool_schemas()
    errors = validate_execution_plan(plan, available_tools)

    if errors:
        console.print("[red]❌ Plan validation failed:[/red]")
        for error in errors:
            console.print(f"  • {error}")
        raise SystemExit(1)
    else:
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
    from rich.progress import Progress, SpinnerColumn, TextColumn
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Show progress for each step
            exec_task = progress.add_task(
                f"Executing {len(plan.steps)} steps...",
                total=len(plan.steps)
            )
            
            # Execute the plan
            results = await execute_plan(plan)
            progress.update(exec_task, completed=len(plan.steps))
        
        console.print("[green]✓ Plan executed successfully[/green]")
        
        # Display summary of results
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
        
    except Exception as e:
        console.print(f"\n[red]❌ Execution failed:[/red] {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    import sys
    import asyncio
    from dataclasses import asdict
    
    import click
    from rich.console import Console
    from rich.json import JSON
    from rich.panel import Panel
    from rich.table import Table
    
    console = Console()
    
    @click.command(context_settings={"help_option_names": ["-h", "--help"]})
    @click.argument(
        "syllabus_pdfs",
        nargs=-1,
        type=click.Path(exists=True, dir_okay=False),
    )
    @click.option(
        "--list",
        "list_tools",
        is_flag=True,
        help="List all available MCP tools from the registry.",
    )
    @click.option(
        "--dry-run",
        "dry_run",
        is_flag=True,
        help="Generate and display the execution plan without executing it.",
    )
    @click.option(
        "--model",
        default="gpt-5",
        help="OpenAI model to use for planning (default: gpt-5).",
    )
    def main(
        syllabus_pdfs: tuple[str, ...],
        list_tools: bool,
        dry_run: bool,
        model: str,
    ) -> None:
        """Dynamic orchestrator that uses LLM to create execution plans.
        
        SYLLABUS_PDFS: Paths to syllabus PDF files to process.
        
        Examples:
            # List available tools
            python -m orchestrator.run_llm --list
            
            # Create execution plan (dry run)
            python -m orchestrator.run_llm --dry-run pdfs/17603.pdf pdfs/17611.pdf
            
            # Execute the plan
            python -m orchestrator.run_llm pdfs/17603.pdf pdfs/17611.pdf
        """

    
        # Run the async main function
        asyncio.run(async_main(syllabus_pdfs, list_tools, dry_run, model))
    
    main()

