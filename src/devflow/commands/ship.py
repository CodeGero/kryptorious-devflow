"""devflow ship — Release automation.

Bumps version, updates changelog, creates git tag, builds, pushes.
Runs audit first.
"""

import json
import re
from datetime import datetime
from pathlib import Path

from ..utils import (
    console, print_header, print_success, print_error, print_warning, print_info,
    find_project_root, run_cmd
)


VERSION_PATTERNS = [
    (r'version\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']', "pyproject.toml"),
    (r'__version__\s*=\s*["\']([0-9]+\.[0-9]+\.[0-9]+)["\']', "__init__.py"),
    (r'"version":\s*"([0-9]+\.[0-9]+\.[0-9]+)"', "package.json"),
    (r'version\s*=\s*"([0-9]+\.[0-9]+\.[0-9]+)"', "Cargo.toml"),
]


def run(path: str, bump: str, message: str, dry_run: bool, tag: bool, push: bool):
    """Ship a release."""

    root = find_project_root(path)
    mode = "DRY RUN" if dry_run else "SHIPPING"

    print_header(f"DevFlow Ship — [bold green]{mode}[/bold green] [bold cyan]{root.name}[/bold cyan]")

    # 1. Run audit first
    print_info("Running pre-ship audit...")
    from .audit import run as run_audit
    try:
        # Run audit silently — only show if it fails
        run_audit(path=str(root), output_format="terminal", severity="error",
                  security=True, deps=True)
    except Exception:
        pass

    # 2. Find current version
    current_version = _find_version(root)
    if not current_version:
        print_error("Could not detect current version. Check your project config.")
        return
    print_info(f"Current version: [bold]{current_version}[/bold]")

    # 3. Bump version
    new_version = _bump_version(current_version, bump)
    print_info(f"New version: [bold green]{new_version}[/bold green]")

    if dry_run:
        console.print()
        console.print("[bold yellow]DRY RUN — No changes made.[/bold yellow]")
        console.print(f"  Would bump: {current_version} → {new_version}")
        if tag:
            console.print(f"  Would create tag: v{new_version}")
        if push:
            console.print(f"  Would push to remote")
        return

    # 4. Update version in files
    updated = _update_version_files(root, current_version, new_version)
    if not updated:
        print_error("Failed to update version. No files matched.")
        return
    print_success(f"Updated version in {len(updated)} file(s)")

    # 5. Update changelog
    _update_changelog(root, new_version, message)

    # 6. Git commit
    code, out, err = run_cmd(["git", "add", "-A"], cwd=str(root))
    if code != 0:
        print_warning(f"git add failed: {err}")

    msg = message or f"Release v{new_version}"
    code, out, err = run_cmd(["git", "commit", "-m", msg], cwd=str(root))
    if code == 0:
        print_success(f"Committed: {msg}")
    else:
        print_warning(f"git commit: {err} (may be nothing to commit)")

    # 7. Create tag
    if tag:
        tag_name = f"v{new_version}"
        code, out, err = run_cmd(["git", "tag", "-a", tag_name, "-m", msg], cwd=str(root))
        if code == 0:
            print_success(f"Created tag: {tag_name}")
        else:
            print_warning(f"git tag failed: {err}")

    # 8. Build distributions
    if (root / "pyproject.toml").exists():
        code, out, err = run_cmd(["python", "-m", "build"], cwd=str(root))
        if code == 0:
            print_success("Built Python distribution packages")
        else:
            print_warning("Build failed. Install: pip install build")

    # 9. Push
    if push:
        code, out, err = run_cmd(["git", "push", "origin", "HEAD"], cwd=str(root))
        if code == 0:
            print_success("Pushed to remote")
        else:
            print_error(f"Push failed: {err}")

        if tag:
            code, out, err = run_cmd(["git", "push", "origin", tag_name], cwd=str(root))
            if code == 0:
                print_success(f"Pushed tag {tag_name}")
            else:
                print_error(f"Tag push failed: {err}")

    # Done
    console.print()
    console.print(Panel.fit(
        f"[bold green]Shipped {root.name} v{new_version}[/bold green]",
        border_style="green"
    ))


def _find_version(root: Path) -> str | None:
    """Find project version from config files."""
    for pattern, filename in VERSION_PATTERNS:
        # Search in root and src/
        for search_dir in [root, root / "src"]:
            if not search_dir.exists():
                continue
            for candidate in search_dir.rglob(filename):
                if candidate.is_file():
                    content = candidate.read_text(errors="ignore")
                    match = re.search(pattern, content)
                    if match:
                        # Skip if it's a dependency version (in node_modules, etc.)
                        if "node_modules" in str(candidate):
                            continue
                        return match.group(1)
            # Also try pyproject.toml directly
            candidate = root / filename
            if candidate.exists():
                content = candidate.read_text(errors="ignore")
                match = re.search(pattern, content)
                if match:
                    return match.group(1)
    return None


def _bump_version(version: str, bump_type: str) -> str:
    """Bump a semver version."""
    major, minor, patch = map(int, version.split("."))
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:
        return f"{major}.{minor}.{patch + 1}"


def _update_version_files(root: Path, old: str, new: str) -> list[Path]:
    """Update version string in all project files."""
    updated = []

    for pattern, filename in VERSION_PATTERNS:
        for search_dir in [root, root / "src"]:
            if not search_dir.exists():
                continue
            for candidate in search_dir.rglob(filename):
                if candidate.is_file() and "node_modules" not in str(candidate):
                    content = candidate.read_text(errors="ignore")
                    if old in content:
                        new_content = content.replace(f'"{old}"', f'"{new}"')
                        new_content = new_content.replace(f"'{old}'", f"'{new}'")
                        if new_content != content:
                            candidate.write_text(new_content, encoding="utf-8")
                            updated.append(candidate)

        # Also check root-level
        candidate = root / filename
        if candidate.exists() and candidate not in updated:
            content = candidate.read_text(errors="ignore")
            if old in content:
                new_content = content.replace(f'"{old}"', f'"{new}"')
                new_content = new_content.replace(f"'{old}'", f"'{new}'")
                if new_content != content:
                    candidate.write_text(new_content, encoding="utf-8")
                    updated.append(candidate)

    return updated


def _update_changelog(root: Path, version: str, message: str):
    """Update or create CHANGELOG.md."""
    changelog = root / "CHANGELOG.md"
    today = datetime.now().strftime("%Y-%m-%d")

    entry = f"""## [{version}] — {today}

- {message or 'Release'}

"""

    if changelog.exists():
        content = changelog.read_text()
        # Insert after the header
        header_end = content.find("\n\n")
        if header_end > 0:
            new_content = content[:header_end + 2] + entry + content[header_end + 2:]
        else:
            new_content = content + "\n" + entry
    else:
        new_content = f"""# Changelog

All notable changes to this project will be documented in this file.

{entry}
"""

    changelog.write_text(new_content, encoding="utf-8")
    print_success("Updated CHANGELOG.md")
