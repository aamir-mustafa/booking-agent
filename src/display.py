from __future__ import annotations

from contextlib import contextmanager

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status
from rich.table import Table

from .models import BookingState

console = Console()


def print_welcome() -> None:
    console.print(
        Panel(
            "[bold]Hotel Booking Agent[/bold]\n"
            "I'll help you find and book the perfect hotel.\n"
            "Type [bold]quit[/bold] or [bold]exit[/bold] to leave.",
            title="Welcome",
            border_style="blue",
        )
    )


def print_assistant(text: str) -> None:
    console.print()
    console.print(Markdown(text))
    console.print()


def print_state(state: BookingState) -> None:
    table = Table(title="Booking State", show_header=False, border_style="dim")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Destination", state.destination or "-")
    table.add_row("Check-in", str(state.check_in) if state.check_in else "-")
    table.add_row("Check-out", str(state.check_out) if state.check_out else "-")
    table.add_row("Guests", str(state.guests))
    if state.budget_max:
        table.add_row("Budget", f"{state.budget_max} {state.currency}/night")
    if state.preferences:
        table.add_row("Preferences", ", ".join(state.preferences))
    table.add_row("Phase", state.phase.value)
    console.print(table)


@contextmanager
def thinking_spinner():
    with Status("[bold cyan]Thinking...[/bold cyan]", console=console, spinner="dots"):
        yield


def print_tool_call(name: str, arguments: dict) -> None:
    args_str = ", ".join(f"{k}={v!r}" for k, v in arguments.items())
    console.print(f"  [bold yellow]TOOL CALL:[/bold yellow] [yellow]{name}({args_str})[/yellow]")


def print_tool_result(name: str, result: str) -> None:
    preview = result[:150] + "..." if len(result) > 150 else result
    console.print(f"  [bold yellow]TOOL RESULT:[/bold yellow] [dim]{preview}[/dim]")


def print_source(source: str) -> None:
    console.print(f"  [bold magenta]SOURCE:[/bold magenta] [magenta]{source}[/magenta]")


def print_error(message: str) -> None:
    console.print(f"[bold red]Error:[/bold red] {message}")


def get_user_input() -> str:
    try:
        return console.input("[bold green]You:[/bold green] ").strip()
    except EOFError:
        return "exit"
