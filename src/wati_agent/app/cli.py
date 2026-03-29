import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from wati_agent.agent.executor import PlanExecutor
from wati_agent.agent.orchestrator import AgentOrchestrator
from wati_agent.agent.planner import Planner
from wati_agent.agent.validator import PlanValidator
from wati_agent.app.config import settings
from wati_agent.domain.models import ExecutionPlan, ExecutionResult, PlanStatus
from wati_agent.integrations.wati.factory import build_wati_client
from wati_agent.llm.factory import build_llm_provider

app = typer.Typer(help="WATI automation agent CLI.")
console = Console()


def build_orchestrator() -> AgentOrchestrator:
    llm_provider = build_llm_provider(settings)
    wati_client = build_wati_client(settings)
    return AgentOrchestrator(
        planner=Planner(llm_provider=llm_provider),
        validator=PlanValidator(),
        executor=PlanExecutor(wati_client=wati_client),
    )


def render_plan_preview(plan: ExecutionPlan) -> None:
    console.print(
        Panel(
            f"[bold]User request[/bold]\n{plan.user_request}\n\n"
            f"[bold]Plan summary[/bold]\n{plan.summary}",
            title="Request Overview",
            border_style="blue",
        )
    )

    status_text = {
        PlanStatus.READY: "[green]Ready[/green]",
        PlanStatus.NEEDS_CLARIFICATION: "[yellow]Needs clarification[/yellow]",
        PlanStatus.UNSUPPORTED: "[red]Unsupported[/red]",
    }[plan.status]
    confirmation_text = "Yes" if plan.requires_confirmation else "No"

    console.print(
        Panel(
            f"[bold]Plan status:[/bold] {status_text}\n"
            f"[bold]Confirmation required:[/bold] {confirmation_text}",
            title="Plan Status",
            border_style="cyan",
        )
    )

    if plan.missing_information:
        missing_items = "\n".join(f"- {item}" for item in plan.missing_information)
        console.print(
            Panel(
                missing_items,
                title="Missing Information",
                border_style="yellow",
            )
        )

    if not plan.steps:
        console.print(
            Panel(
                "No executable steps were created for this request.",
                title="Plan Steps",
                border_style="red",
            )
        )
        return

    steps_table = Table(title="Execution Plan", header_style="bold magenta")
    steps_table.add_column("Step", style="cyan", no_wrap=True)
    steps_table.add_column("Action", style="green")
    steps_table.add_column("Description")
    steps_table.add_column("Endpoint")

    for step in plan.steps:
        steps_table.add_row(
            step.id,
            step.action,
            step.description,
            step.endpoint_hint or "-",
        )

    console.print(steps_table)


def render_execution_result(result: ExecutionResult) -> None:
    status_label = "[green]Success[/green]" if result.success else "[red]Failed[/red]"
    console.print(
        Panel(
            f"[bold]Execution status:[/bold] {status_label}\n"
            f"[bold]Summary:[/bold] {result.summary}",
            title="Execution Result",
            border_style="green" if result.success else "red",
        )
    )

    if result.completed_steps:
        completed_items = "\n".join(f"- {step_id}" for step_id in result.completed_steps)
        console.print(Panel(completed_items, title="Completed Steps", border_style="green"))

    if result.failed_steps:
        failed_items = "\n".join(f"- {step_id}" for step_id in result.failed_steps)
        console.print(Panel(failed_items, title="Failed Steps", border_style="red"))

    if result.details:
        detail_lines = "\n".join(f"- {detail}" for detail in result.details)
        console.print(Panel(detail_lines, title="Execution Details", border_style="blue"))


def should_stop_after_preview(plan: ExecutionPlan) -> bool:
    return plan.status != PlanStatus.READY


@app.command()
def preview(user_input: str) -> None:
    """Show the plan the agent would execute for a user request."""

    orchestrator = build_orchestrator()
    response = orchestrator.preview(user_input)
    render_plan_preview(response.plan)


@app.command()
def run(user_input: str, auto_confirm: bool = False) -> None:
    """Preview the plan, ask for confirmation, and then execute it."""

    orchestrator = build_orchestrator()
    plan_preview = orchestrator.preview(user_input)
    render_plan_preview(plan_preview.plan)

    if should_stop_after_preview(plan_preview.plan):
        console.print(
            Panel(
                "The plan is not ready to execute yet. Please refine the request and try again.",
                title="Execution Paused",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=1)

    should_execute = auto_confirm or typer.confirm("Execute this plan?")
    if not should_execute:
        console.print(
            Panel("Execution cancelled by the user.", title="Execution Cancelled", border_style="yellow")
        )
        raise typer.Exit(code=0)

    execution_response = orchestrator.execute(plan_preview.plan)
    render_execution_result(execution_response.result)


@app.command()
def chat() -> None:
    """Start a simple terminal loop for testing multiple requests."""

    orchestrator = build_orchestrator()
    console.print(
        Panel(
            "Write a request in English. Type 'exit' or 'quit' to leave.",
            title="WATI Agent Chat",
            border_style="blue",
        )
    )

    while True:
        user_input = typer.prompt("Request").strip()
        if user_input.lower() in {"exit", "quit"}:
            console.print("Session closed.")
            raise typer.Exit(code=0)

        plan_preview = orchestrator.preview(user_input)
        render_plan_preview(plan_preview.plan)

        if should_stop_after_preview(plan_preview.plan):
            continue

        should_execute = typer.confirm("Execute this plan?")
        if not should_execute:
            console.print("Execution skipped.")
            continue

        execution_response = orchestrator.execute(plan_preview.plan)
        render_execution_result(execution_response.result)


if __name__ == "__main__":
    app()
