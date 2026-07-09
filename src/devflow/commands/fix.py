"""devflow fix — Auto-fix common code issues.

Applies formatting, sorts imports, fixes lint violations, addresses security issues.
"""

from pathlib import Path
from typing import List

from ..utils import (
    console, print_header, print_success, print_error, print_warning, print_info,
    find_project_root, check_tool_available, run_cmd
)


def run(path: str, dry_run: bool, scope: str):
    """Auto-fix code issues."""

    root = find_project_root(path)
    mode = "DRY RUN" if dry_run else "APPLY"

    print_header(f"DevFlow Fix — [bold yellow]{mode}[/bold yellow] on [bold cyan]{root.name}[/bold cyan]")

    fixed_count = 0
    actions: List[str] = []

    if scope in ("all", "format"):
        fixed, acts = _fix_formatting(root, dry_run)
        fixed_count += fixed
        actions.extend(acts)

    if scope in ("all", "imports"):
        fixed, acts = _fix_imports(root, dry_run)
        fixed_count += fixed
        actions.extend(acts)

    if scope in ("all", "lint"):
        fixed, acts = _fix_lint(root, dry_run)
        fixed_count += fixed
        actions.extend(acts)

    if scope in ("all", "security"):
        fixed, acts = _fix_security(root, dry_run)
        fixed_count += fixed
        actions.extend(acts)

    # Summary
    console.print()
    if dry_run:
        console.print(f"[bold yellow]DRY RUN:[/bold yellow] {fixed_count} issue(s) would be fixed:")
    else:
        console.print(f"[bold green]Done:[/bold green] {fixed_count} issue(s) fixed:")

    for action in actions[:20]:
        console.print(f"  • {action}")

    if len(actions) > 20:
        console.print(f"  ... and {len(actions) - 20} more")

    if fixed_count > 0 and not dry_run:
        print_success("All fixes applied. Run 'devflow audit' to verify.")
    elif fixed_count == 0:
        print_success("Everything looks clean. No fixes needed.")


def _fix_formatting(root: Path, dry_run: bool) -> tuple[int, list[str]]:
    """Fix code formatting with black."""
    if not check_tool_available("black"):
        print_warning("black not installed. Install: pip install black")
        return 0, []

    target = str(root)

    if dry_run:
        code, out, err = run_cmd(["black", "--check", "--diff", target], cwd=str(root))
        if code != 0:
            changed = sum(1 for l in out.split("\n") if l.startswith("---") or l.startswith("+++"))
            return changed // 2, [f"Formatting needed in {changed // 2} file(s)"]
        return 0, []

    code, out, err = run_cmd(["black", target], cwd=str(root))
    if "reformatted" in out:
        for line in out.split("\n"):
            if "reformatted" in line:
                print_success(f"Formatted: {line.strip()}")
                break
        return 1, ["Black formatting applied"]
    elif "unchanged" in out:
        print_info("All files already formatted.")
        return 0, []
    return 0, []


def _fix_imports(root: Path, dry_run: bool) -> tuple[int, list[str]]:
    """Sort imports with isort or ruff."""
    target = str(root)

    if check_tool_available("ruff"):
        if dry_run:
            code, out, err = run_cmd(["ruff", "check", "--select", "I", "--diff", target], cwd=str(root))
            if out.strip():
                count = len([l for l in out.split("\n") if l.startswith("---")])
                return count, [f"Import sorting needed in ~{count} file(s)"]
            return 0, []
        else:
            code, out, err = run_cmd(["ruff", "check", "--select", "I", "--fix", target], cwd=str(root))
            if "fixed" in (out + err).lower():
                print_success("Imports sorted with ruff.")
                return 1, ["Import sorting applied via ruff"]
            return 0, []

    if check_tool_available("isort"):
        if dry_run:
            code, out, err = run_cmd(["isort", "--check-only", "--diff", target], cwd=str(root))
            if code != 0:
                return 1, ["Import sorting needed (isort)"]
            return 0, []
        else:
            code, out, err = run_cmd(["isort", target], cwd=str(root))
            if code == 0:
                print_success("Imports sorted with isort.")
                return 1, ["Import sorting applied via isort"]
    return 0, []


def _fix_lint(root: Path, dry_run: bool) -> tuple[int, list[str]]:
    """Fix lint issues with ruff."""
    target = str(root)

    if check_tool_available("ruff"):
        if dry_run:
            code, out, err = run_cmd(["ruff", "check", "--diff", target], cwd=str(root))
            if out.strip():
                issues = len([l for l in out.split("\n") if l.strip() and not l.startswith("---") and not l.startswith("+++")])
                return issues, [f"{issues} lint issue(s) found"]
            return 0, []
        else:
            code, out, err = run_cmd(["ruff", "check", "--fix", target], cwd=str(root))
            if "fixed" in (out + err):
                # Count fixes
                fixes = [l for l in (out + err).split("\n") if "fixed" in l.lower()]
                for f in fixes:
                    if f.strip():
                        print_success(f.strip())
                return len(fixes) or 1, ["Lint fixes applied via ruff"]
            elif "no errors" in (out + err).lower() or "all good" in (out + err).lower():
                print_info("No lint issues found.")
            return 0, []

    if check_tool_available("flake8"):
        print_warning("flake8 detected but does not support auto-fix. Install ruff.")
        return 0, []

    return 0, []


def _fix_security(root: Path, dry_run: bool) -> tuple[int, list[str]]:
    """Basic security fixes."""
    target = str(root)
    fixed = 0
    actions = []

    # Remove common hardcoded patterns (only in dry_run, never auto-remove secrets)
    py_files = list(root.rglob("*.py"))
    for pf in py_files:
        if "test" in str(pf).lower():
            continue
        content = pf.read_text(errors="ignore")
        if 'SECRET_KEY = "' in content or "SECRET_KEY = '" in content:
            actions.append(f"Hardcoded SECRET_KEY in {pf.relative_to(root)} — move to .env")
        if 'API_KEY = "' in content or "API_KEY = '" in content:
            actions.append(f"Hardcoded API_KEY in {pf.relative_to(root)} — move to .env")

    if dry_run:
        return len(actions), actions
    return 0, actions
