"""DevFlow utilities."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def run_cmd(cmd: list[str], cwd: Optional[str] = None, check: bool = True) -> Tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def find_project_root(start: str = ".") -> Path:
    """Find project root by looking for pyproject.toml, package.json, etc."""
    current = Path(start).resolve()
    markers = ["pyproject.toml", "setup.py", "setup.cfg", "package.json", "go.mod", "Cargo.toml"]

    for _ in range(10):  # Max depth
        for marker in markers:
            if (current / marker).exists():
                return current
        if current.parent == current:
            break
        current = current.parent

    return Path(start).resolve()


def check_tool_available(tool: str) -> bool:
    """Check if a CLI tool is available."""
    return subprocess.run(
        ["which", tool] if sys.platform != "win32" else ["where", tool],
        capture_output=True
    ).returncode == 0


def print_header(text: str):
    """Print a styled header."""
    console.print()
    console.print(Panel(f"[bold white]{text}[/bold white]", border_style="blue"))
    console.print()


def print_success(text: str):
    """Print a success message."""
    console.print(f"  [green]✓[/green] {text}")


def print_error(text: str):
    """Print an error message."""
    console.print(f"  [red]✗[/red] {text}")


def print_warning(text: str):
    """Print a warning message."""
    console.print(f"  [yellow]![/yellow] {text}")


def print_info(text: str):
    """Print an info message."""
    console.print(f"  [blue]ℹ[/blue] {text}")


def create_results_table(title: str) -> Table:
    """Create a styled results table."""
    table = Table(title=title, title_style="bold white", border_style="blue")
    return table
