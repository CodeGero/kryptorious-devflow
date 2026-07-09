"""devflow audit — Comprehensive codebase health check.

Checks linting, formatting, security, dependencies, and documentation.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any

from ..utils import (
    console, print_header, print_success, print_error, print_warning, print_info,
    find_project_root, check_tool_available, run_cmd, create_results_table
)


def run(path: str, output_format: str, severity: str, security: bool, deps: bool):
    """Run comprehensive codebase audit."""

    root = find_project_root(path)
    print_header(f"DevFlow Audit — [bold cyan]{root.name}[/bold cyan]")

    results = {
        "project": str(root),
        "checks": [],
        "score": 0,
        "max_score": 0,
    }

    # Detect project type
    ptype = _detect_project_type(root)
    print_info(f"Detected project type: [bold]{ptype}[/bold]")

    # Run all checks
    checks: List[Tuple[str, str, bool, List[str]]] = []

    checks.extend(_check_structure(root, ptype))
    checks.extend(_check_linting(root, ptype))
    checks.extend(_check_formatting(root, ptype))
    checks.extend(_check_testing(root, ptype))
    checks.extend(_check_documentation(root))

    if security:
        checks.extend(_check_security(root, ptype))

    if deps:
        checks.extend(_check_dependencies(root, ptype))

    # Filter by severity
    sev_order = {"error": 0, "warning": 1, "info": 2}
    min_sev = sev_order.get(severity, 2)
    checks = [c for c in checks if sev_order.get(c[2], 2) <= min_sev]

    # Score
    passed = sum(1 for c in checks if c[1] == "pass")
    total = len(checks)
    score = int((passed / total) * 100) if total > 0 else 100

    # Output
    if output_format == "terminal":
        _output_terminal(checks, score, root, ptype)
    elif output_format == "markdown":
        _output_markdown(checks, score, root, ptype)
    elif output_format == "json":
        _output_json(checks, score, root)

    results["checks"] = [{"name": c[0], "status": c[1], "severity": c[2], "details": c[3]} for c in checks]
    results["score"] = score
    results["max_score"] = 100


def _detect_project_type(root: Path) -> str:
    """Detect project type from config files."""
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        # Check if it's an API
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            if "fastapi" in content.lower() or "flask" in content.lower():
                return "python-api"
            if "click" in content.lower() and "[project.scripts]" in content:
                return "python-cli"
        return "python"
    elif (root / "package.json").exists():
        return "node"
    elif (root / "go.mod").exists():
        return "go"
    return "unknown"


def _check_structure(root: Path, ptype: str) -> List[Tuple[str, str, str, List[str]]]:
    """Check project structure conventions."""
    checks = []

    # Source directory
    if ptype.startswith("python"):
        has_src = (root / "src").is_dir()
        # In src layout, package is inside src/ — check subdirectories for __init__.py
        has_pkg = False
        if has_src:
            for d in (root / "src").iterdir():
                if d.is_dir() and (d / "__init__.py").exists():
                    has_pkg = True
                    break
        checks.append((
            "Source directory (src/)",
            "pass" if has_src else "warning",
            "warning",
            ["Use src/ layout for clean package separation"] if not has_src else []
        ))
        checks.append((
            "Package __init__.py",
            "pass" if has_pkg else "error",
            "error",
            ["No Python package found in src/ — missing __init__.py"] if not has_pkg else []
        ))

    # Tests directory
    has_tests = (root / "tests").is_dir() or (root / "test").is_dir()
    checks.append((
        "Test directory (tests/)",
        "pass" if has_tests else "warning",
        "warning",
        ["No test directory found. Add tests/ with at least one test file."] if not has_tests else []
    ))

    # README
    has_readme = any((root / f).exists() for f in ["README.md", "README.rst", "README"])
    checks.append((
        "README file",
        "pass" if has_readme else "warning",
        "warning",
        ["No README found. Every project needs one."] if not has_readme else []
    ))

    # .gitignore
    has_gitignore = (root / ".gitignore").exists()
    checks.append((
        ".gitignore file",
        "pass" if has_gitignore else "error",
        "error",
        ["No .gitignore — risk of committing generated files."] if not has_gitignore else []
    ))

    return checks


def _check_linting(root: Path, ptype: str) -> List[Tuple[str, str, str, List[str]]]:
    """Check linting setup and run."""
    checks = []

    if ptype.startswith("python"):
        # ruff or flake8
        has_ruff = check_tool_available("ruff")
        has_flake8 = check_tool_available("flake8")

        if has_ruff:
            code, out, err = run_cmd(["ruff", "check", str(root)], cwd=str(root))
            issue_count = len([l for l in out.split("\n") if l.strip()])
            checks.append((
                "Ruff lint check",
                "pass" if code == 0 else "warning",
                "warning" if issue_count > 0 else "info",
                out.split("\n")[:5] if issue_count > 0 else ["Clean — no lint issues."]
            ))
            checks.append((
                "Linting tool configured",
                "pass", "info", ["Ruff is available and configured."]
            ))
        elif has_flake8:
            checks.append((
                "Linting tool",
                "pass", "info", ["flake8 detected. Consider upgrading to ruff for speed."]
            ))
        else:
            checks.append((
                "Linting tool",
                "warning", "warning",
                ["No linter found. Install: pip install ruff"]
            ))

    elif ptype == "node":
        has_eslint = (root / ".eslintrc.js").exists() or (root / ".eslintrc.json").exists() or (root / "eslint.config.js").exists()
        checks.append((
            "ESLint configured",
            "pass" if has_eslint else "warning",
            "warning",
            ["No ESLint config found."] if not has_eslint else []
        ))

    return checks


def _check_formatting(root: Path, ptype: str) -> List[Tuple[str, str, str, List[str]]]:
    """Check code formatting."""
    checks = []

    if ptype.startswith("python"):
        has_black = check_tool_available("black")
        if has_black:
            code, out, err = run_cmd(["black", "--check", "--diff", str(root)], cwd=str(root))
            checks.append((
                "Black formatting",
                "pass" if code == 0 else "warning",
                "warning" if code != 0 else "info",
                ["Code would be reformatted."] if code != 0 else ["All files properly formatted."]
            ))
        else:
            checks.append((
                "Formatter (black)",
                "warning", "warning",
                ["black not installed. Install: pip install black"]
            ))

        # isort
        has_isort = check_tool_available("isort")
        if has_isort:
            code, out, err = run_cmd(["isort", "--check-only", str(root)], cwd=str(root))
            checks.append((
                "Import sorting (isort)",
                "pass" if code == 0 else "warning",
                "warning" if code != 0 else "info",
                ["Imports need sorting."] if code != 0 else ["Imports properly sorted."]
            ))

    elif ptype == "node":
        has_prettier = check_tool_available("prettier") or (root / ".prettierrc").exists()
        checks.append((
            "Prettier configured",
            "pass" if has_prettier else "warning",
            "warning",
            ["No Prettier config found."] if not has_prettier else []
        ))

    return checks


def _check_testing(root: Path, ptype: str) -> List[Tuple[str, str, str, List[str]]]:
    """Check testing setup."""
    checks = []

    if ptype.startswith("python"):
        test_dir = root / "tests" if (root / "tests").exists() else root / "test"
        if test_dir.exists():
            test_files = list(test_dir.rglob("test_*.py")) + list(test_dir.rglob("*_test.py"))
            checks.append((
                f"Test files ({len(test_files)} found)",
                "pass" if test_files else "warning",
                "warning" if not test_files else "info",
                ["No test files in test directory."] if not test_files else [f"{len(test_files)} test files found."]
            ))

            # Try running pytest
            if test_files and check_tool_available("pytest"):
                code, out, err = run_cmd(["pytest", "--tb=no", "-q", str(test_dir)], cwd=str(root))
                checks.append((
                    "Tests passing",
                    "pass" if code == 0 else "error",
                    "error" if code != 0 else "info",
                    out.split("\n")[-3:] if code != 0 else [out.strip().split("\n")[-1]]
                ))
        else:
            checks.append((
                "Test directory",
                "warning", "warning",
                ["No test directory. Create tests/ and add your first test."]
            ))

    elif ptype == "node":
        has_jest = check_tool_available("jest") or (root / "jest.config.js").exists()
        checks.append((
            "Jest configured",
            "pass" if has_jest else "warning",
            "warning",
            ["No Jest config found."] if not has_jest else []
        ))

    return checks


def _check_documentation(root: Path) -> List[Tuple[str, str, str, List[str]]]:
    """Check documentation coverage."""
    checks = []

    # Docstring coverage (Python only)
    py_files = list(root.rglob("*.py"))
    if py_files:
        no_docstring = 0
        total_functions = 0
        for pf in py_files:
            if "test" in str(pf) or "__init__" in pf.name:
                continue
            content = pf.read_text(errors="ignore")
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("def ") or line.strip().startswith("async def "):
                    total_functions += 1
                    # Check if next line is a docstring
                    if i + 1 < len(lines) and '"""' in lines[i + 1]:
                        pass
                    elif i + 2 < len(lines) and '"""' in lines[i + 2]:
                        pass
                    else:
                        no_docstring += 1

        if total_functions > 0:
            pct = int((total_functions - no_docstring) / total_functions * 100)
            checks.append((
                f"Docstring coverage ({pct}%)",
                "pass" if pct >= 80 else "warning",
                "warning" if pct < 80 else "info",
                [f"{no_docstring}/{total_functions} functions missing docstrings."] if no_docstring else ["All functions documented."]
            ))

    return checks


def _check_security(root: Path, ptype: str) -> List[Tuple[str, str, str, List[str]]]:
    """Security checks."""
    checks = []

    # Check for bandit
    if ptype.startswith("python") and check_tool_available("bandit"):
        code, out, err = run_cmd(["bandit", "-r", str(root), "-q"], cwd=str(root))
        issues = [l for l in out.split("\n") if "Issue:" in l]
        checks.append((
            "Bandit security scan",
            "pass" if not issues else "error",
            "error" if issues else "info",
            issues[:5] if issues else ["No security issues found."]
        ))
    elif ptype.startswith("python"):
        checks.append((
            "Security scanner",
            "warning", "warning",
            ["bandit not installed. Install: pip install bandit"]
        ))

    # Check for secrets in code
    secret_patterns = ["API_KEY", "SECRET", "PASSWORD", "TOKEN", "PRIVATE_KEY"]
    found_secrets = []
    for pattern in secret_patterns:
        for py_file in root.rglob("*.py"):
            if "test" in str(py_file).lower():
                continue
            content = py_file.read_text(errors="ignore")
            if f'{pattern} = "' in content or f"{pattern} = '" in content:
                found_secrets.append(f"{py_file.relative_to(root)}: hardcoded {pattern}")

    checks.append((
        "Hardcoded secrets",
        "pass" if not found_secrets else "error",
        "error" if found_secrets else "info",
        found_secrets[:5] if found_secrets else ["No hardcoded secrets detected."]
    ))

    return checks


def _check_dependencies(root: Path, ptype: str) -> List[Tuple[str, str, str, List[str]]]:
    """Dependency checks."""
    checks = []

    if ptype.startswith("python"):
        # Check for pip-audit
        if check_tool_available("pip-audit"):
            code, out, err = run_cmd(["pip-audit", "-r", str(root / "requirements.txt")] if (root / "requirements.txt").exists() else ["pip-audit"], cwd=str(root))
            vulns = [l for l in out.split("\n") if "vulnerab" in l.lower()]
            checks.append((
                "Dependency vulnerabilities",
                "pass" if not vulns else "error",
                "error" if vulns else "info",
                vulns[:5] if vulns else ["No known vulnerabilities."]
            ))
        else:
            checks.append((
                "Vulnerability scanner",
                "warning", "warning",
                ["pip-audit not installed. Install: pip install pip-audit"]
            ))

        # Check for requirements.txt or pyproject.toml
        has_deps = (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() or (root / "setup.py").exists()
        checks.append((
            "Dependencies declared",
            "pass" if has_deps else "error",
            "error",
            ["No dependency declaration found."] if not has_deps else ["Dependencies properly declared."]
        ))

    elif ptype == "node":
        has_package_json = (root / "package.json").exists()
        checks.append((
            "package.json",
            "pass" if has_package_json else "error",
            "error",
            ["No package.json found."] if not has_package_json else []
        ))

        if has_package_json:
            has_lock = (root / "package-lock.json").exists() or (root / "yarn.lock").exists() or (root / "pnpm-lock.yaml").exists()
            checks.append((
                "Lock file",
                "pass" if has_lock else "warning",
                "warning",
                ["No lock file — builds may not be reproducible."] if not has_lock else []
            ))

    return checks


def _output_terminal(checks: List[Tuple[str, str, str, List[str]]], score: int, root: Path, ptype: str):
    """Print results to terminal."""
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    passed = sum(1 for c in checks if c[1] == "pass")
    warnings = sum(1 for c in checks if c[1] == "warning")
    errors = sum(1 for c in checks if c[1] == "error")

    # Score panel
    color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
    console.print()
    console.print(Panel(
        f"[bold {color}]{score}/100[/bold {color}] — "
        f"[green]{passed} passed[/green], "
        f"[yellow]{warnings} warnings[/yellow], "
        f"[red]{errors} errors[/red]",
        title="Audit Score",
        border_style=color
    ))

    # Results table
    table = Table(title="Audit Results", border_style="blue")
    table.add_column("Status", style="bold", width=8)
    table.add_column("Check", style="bold")
    table.add_column("Details")

    for name, status, severity, details in checks:
        icon = {"pass": "[green]✓[/green]", "warning": "[yellow]![/yellow]", "error": "[red]✗[/red]"}.get(status, "?")
        detail_text = details[0] if details else ""
        table.add_row(icon, name, detail_text)

    console.print(table)

    # Recommendations
    if errors > 0 or warnings > 0:
        console.print()
        console.print("[bold]Top recommendations:[/bold]")
        if errors > 0:
            console.print("  [red]Fix errors first:[/red]")
            for name, status, severity, details in checks:
                if status == "error":
                    console.print(f"    • {name}")
        if warnings > 0:
            console.print("  [yellow]Then address warnings:[/yellow]")
            for name, status, severity, details in checks:
                if status == "warning":
                    console.print(f"    • {name}")


def _output_markdown(checks: List[Tuple[str, str, str, List[str]]], score: int, root: Path, ptype: str):
    """Output results as markdown."""
    passed = sum(1 for c in checks if c[1] == "pass")
    warnings = sum(1 for c in checks if c[1] == "warning")
    errors = sum(1 for c in checks if c[1] == "error")

    md = f"""# DevFlow Audit Report

**Project:** {root.name}
**Path:** {root}
**Type:** {ptype}
**Score:** {score}/100 ({passed} passed, {warnings} warnings, {errors} errors)

---

## Results

| Status | Check | Details |
|--------|-------|---------|
"""
    for name, status, severity, details in checks:
        icon = {"pass": "✅", "warning": "⚠️", "error": "❌"}.get(status, "❓")
        detail_text = details[0] if details else ""
        md += f"| {icon} | {name} | {detail_text} |\n"

    md += f"""
---

*Generated by [DevFlow](https://devflow.sh)*
"""
    console.print(md)


def _output_json(checks, score, root):
    """Output results as JSON."""
    import json
    data = {
        "project": str(root),
        "score": score,
        "passed": sum(1 for c in checks if c[1] == "pass"),
        "warnings": sum(1 for c in checks if c[1] == "warning"),
        "errors": sum(1 for c in checks if c[1] == "error"),
        "checks": [{"name": c[0], "status": c[1], "severity": c[2], "details": c[3]} for c in checks]
    }
    console.print(json.dumps(data, indent=2))
