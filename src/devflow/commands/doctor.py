"""devflow doctor — Diagnose and fix common project issues."""

import os
import sys
from pathlib import Path

from ..utils import console, print_success, print_error, print_warning, print_info, run_cmd


def diagnose(project_path: str) -> dict:
    """Run full diagnostic on a project. Returns issues found."""
    root = Path(project_path).resolve()
    issues = []
    fixes = []

    console.print(f"Examining [cyan]{root.name}[/cyan]...")
    console.print()

    # Python version check
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    console.print(f"  Python: [bold]{py_version}[/bold]")

    if sys.version_info < (3, 9):
        issues.append({"severity": "error", "what": f"Python {py_version} is too old", "fix": "Upgrade to Python 3.9+ or use pyenv to manage versions"})
    elif sys.version_info < (3, 11):
        issues.append({"severity": "info", "what": f"Python {py_version} works but 3.12+ is recommended", "fix": "Consider upgrading for performance improvements"})

    # Virtual environment check
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if in_venv:
        console.print(f"  Virtualenv: [green]active[/green] ({sys.prefix})")
    else:
        issues.append({"severity": "warning", "what": "Not running in a virtual environment", "fix": "Create one: python -m venv .venv && source .venv/bin/activate"})

    # Project files check
    has_pyproject = (root / "pyproject.toml").exists()
    has_setup = (root / "setup.py").exists() or (root / "setup.cfg").exists()
    has_readme = any((root / f).exists() for f in ["README.md", "README.rst", "README"])
    has_gitignore = (root / ".gitignore").exists()
    has_tests = (root / "tests").is_dir() or (root / "test").is_dir()
    has_license = (root / "LICENSE").exists() or (root / "LICENSE.md").exists()

    console.print(f"  pyproject.toml: {'[green]✓[/green]' if has_pyproject else '[red]✗[/red]'}")
    if not has_pyproject:
        issues.append({"severity": "error", "what": "Missing pyproject.toml", "fix": "Run: devflow init"})

    console.print(f"  README: {'[green]✓[/green]' if has_readme else '[yellow]![/yellow]'}")
    if not has_readme:
        issues.append({"severity": "warning", "what": "Missing README", "fix": "Add a README.md describing your project"})

    console.print(f"  .gitignore: {'[green]✓[/green]' if has_gitignore else '[yellow]![/yellow]'}")
    console.print(f"  Tests dir: {'[green]✓[/green]' if has_tests else '[yellow]![/yellow]'}")
    console.print(f"  License: {'[green]✓[/green]' if has_license else '[yellow]![/yellow]'}")

    # Git checks
    git_dir = root / ".git"
    if git_dir.exists():
        code, out, err = run_cmd(["git", "status", "--porcelain"], cwd=str(root))
        if code == 0:
            dirty = [l for l in out.split("\n") if l.strip()]
            if dirty:
                console.print(f"  Git: [yellow]{len(dirty)} uncommitted change(s)[/yellow]")
            else:
                console.print(f"  Git: [green]clean[/green]")

        # Check for unpushed commits
        code, out, err = run_cmd(["git", "log", "--oneline", "@{u}.."], cwd=str(root))
        if code == 0 and out.strip():
            unpushed = len([l for l in out.split("\n") if l.strip()])
            if unpushed:
                issues.append({"severity": "info", "what": f"{unpushed} unpushed commit(s)", "fix": "Run: git push"})

        # Check remote
        code, out, err = run_cmd(["git", "remote", "-v"], cwd=str(root))
        if code == 0 and out.strip():
            console.print(f"  Remote: [green]configured[/green]")
        else:
            issues.append({"severity": "warning", "what": "No git remote configured", "fix": "Add a remote: git remote add origin <url>"})
    else:
        issues.append({"severity": "warning", "what": "Not a git repository", "fix": "Initialize: git init"})

    # Check disk usage
    try:
        import shutil
        usage = shutil.disk_usage(root)
        free_gb = usage.free / (1024**3)
        if free_gb < 1:
            issues.append({"severity": "warning", "what": f"Low disk space: {free_gb:.1f} GB free", "fix": "Free up disk space"})
    except Exception:
        pass

    # Dependency checks
    if has_pyproject:
        # Check if package is installed in dev mode
        egg_info = list(root.glob("*.egg-info"))
        if not egg_info:
            # Try installing
            issues.append({"severity": "info", "what": "Package not installed in dev mode", "fix": "Run: pip install -e '.[dev]'"})

    return {"issues": issues, "total": len(issues)}


def apply_fixes(root: str, issues: list) -> int:
    """Apply automatic fixes where possible. Returns number fixed."""
    fixed = 0

    for issue in issues:
        if issue["severity"] == "error":
            continue  # Don't auto-fix errors

        what = issue["what"]
        fix = issue.get("fix", "")

        if "Not a git repository" in what:
            code, out, err = run_cmd(["git", "init"], cwd=root)
            if code == 0:
                print_success(f"Initialized git repository")
                fixed += 1

        if "Package not installed" in what:
            code, out, err = run_cmd([sys.executable, "-m", "pip", "install", "-e", "."], cwd=root)
            if code == 0:
                print_success("Installed package in dev mode")
                fixed += 1

    return fixed
