"""DevFlow CLI — main entry point."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.group()
@click.version_option(version="1.5.0", prog_name="devflow")
def main():
    """DevFlow — Developer Workflow Automation CLI.

    The unified tool for project scaffolding, codebase auditing,
    auto-fixing, release shipping, CI/CD pipeline generation,
    infrastructure-as-code, and project diagnostics.
    One tool, eight commands.
    """
    pass


@main.command()
@click.argument("name")
@click.option(
    "--template", "-t",
    type=click.Choice(["python", "node", "fullstack", "cli", "api", "lib", "go", "rust", "react"]),
    default="python",
    help="Project template type",
)
@click.option("--path", "-p", default=".", help="Parent directory for the new project")
@click.option("--docker/--no-docker", default=True, help="Include Docker config")
@click.option("--ci/--no-ci", default=True, help="Include CI/CD (GitHub Actions)")
@click.option("--git/--no-git", default=True, help="Initialize git repository")
@click.option("--license", "-l", default="MIT", help="License type")
@click.option("--description", "-d", default="", help="Project description")
def init(name, template, path, docker, ci, git, license, description):
    """Scaffold a new project with best practices.

    \b
    Examples:
        devflow init my-api --template api
        devflow init my-lib --template lib --no-docker
    """
    from .commands.init import run
    run(name=name, template=template, path=path, docker=docker,
        ci=ci, git_init=git, license_type=license, description=description)


@main.command()
@click.option("--path", "-p", default=".", help="Path to the project to audit")
@click.option("--format", "-f", "output_format",
              type=click.Choice(["terminal", "markdown", "json"]),
              default="terminal", help="Output format")
@click.option("--severity", "-s", type=click.Choice(["error", "warning", "info", "all"]),
              default="all", help="Minimum severity to show")
@click.option("--security/--no-security", default=True, help="Run security audit")
@click.option("--deps/--no-deps", default=True, help="Check dependencies")
def audit(path, output_format, severity, security, deps):
    """Run a comprehensive codebase health check.

    \b
    Examples:
        devflow audit
        devflow audit --format markdown --severity warning
    """
    from .commands.audit import run
    run(path=path, output_format=output_format, severity=severity,
        security=security, deps=deps)


@main.command()
@click.option("--path", "-p", default=".", help="Path to the project")
@click.option("--dry-run/--apply", default=False, help="Preview fixes without applying")
@click.option("--scope", "-s", type=click.Choice(["all", "format", "lint", "imports", "security"]),
              default="all", help="Fix scope")
def fix(path, dry_run, scope):
    """Automatically fix common code issues.

    \b
    Examples:
        devflow fix --dry-run
        devflow fix --scope format
    """
    from .commands.fix import run
    run(path=path, dry_run=dry_run, scope=scope)


@main.command()
@click.option("--path", "-p", default=".", help="Path to the project")
@click.option("--bump", "-b", type=click.Choice(["patch", "minor", "major"]),
              required=True, help="Version bump type")
@click.option("--message", "-m", default="", help="Release message for changelog")
@click.option("--dry-run/--execute", default=False, help="Preview release without executing")
@click.option("--tag/--no-tag", default=True, help="Create git tag")
@click.option("--push/--no-push", default=False, help="Push to remote")
def ship(path, bump, message, dry_run, tag, push):
    """Prepare and execute a release.

    \b
    Examples:
        devflow ship --bump patch --message "Bug fixes"
        devflow ship --bump minor --dry-run
    """
    from .commands.ship import run
    run(path=path, bump=bump, message=message, dry_run=dry_run,
        tag=tag, push=push)


@main.command()
@click.option("--path", "-p", default=".", help="Path to the project")
@click.option("--platform", type=click.Choice(["github-actions", "gitlab-ci", "all"]),
              default="all", help="CI platform")
@click.option("--deploy", type=click.Choice(["none", "aws", "gcp", "vercel", "docker"]),
              default="none", help="Deployment target")
def pipeline(path, platform, deploy):
    """Generate CI/CD pipeline configuration (free).

    Creates GitHub Actions / GitLab CI workflows with lint, type-check,
    security scan, test, build, and deploy stages.

    \b
    Examples:
        devflow pipeline --platform github-actions --deploy aws
        devflow pipeline --deploy vercel
    """
    from .commands.pipeline import generate_pipeline

    console.print()
    console.print(Panel(
        f"[bold]DevFlow Pipeline[/bold] — [cyan]{platform}[/cyan] + [green]{deploy}[/green]",
        border_style="blue"))
    result = generate_pipeline(str(Path(path).resolve()), platform, deploy)
    if result:
        console.print()
        console.print("[green]Pipeline generated successfully.[/green]")
        console.print(f"  File: {result}")
        console.print()
        console.print("[bold]Next steps:[/bold]")
        console.print("  1. Review the generated file")
        console.print("  2. Add secrets to your repo settings")
        console.print("  3. Push to trigger the pipeline")
        console.print()
        console.print("[dim]Premium (devflow premium) adds multi-environment "
                      "configs, approval gates, and infra-as-code.[/dim]")


@main.command()
@click.option("--path", "-p", default=".", help="Path to the project")
@click.option("--fix/--no-fix", default=False, help="Auto-apply fixes where possible")
def doctor(path, fix):
    """Diagnose common project issues.

    \b
    Examples:
        devflow doctor
        devflow doctor --fix
    """
    from .commands.doctor import diagnose, apply_fixes

    console.print()
    console.print(Panel("[bold]DevFlow Doctor[/bold] — Project Health Diagnostic",
                        border_style="blue"))
    console.print()

    result = diagnose(str(Path(path).resolve()))
    console.print()
    if result["total"] == 0:
        console.print("[green]✓ Your project is healthy. No issues found.[/green]")
    else:
        errors = sum(1 for i in result["issues"] if i["severity"] == "error")
        warnings = sum(1 for i in result["issues"] if i["severity"] == "warning")
        infos = sum(1 for i in result["issues"] if i["severity"] == "info")
        console.print(f"[bold]Found {result['total']} issue(s):[/bold] "
                      f"[red]{errors} errors[/red], [yellow]{warnings} warnings[/yellow], "
                      f"[blue]{infos} info[/blue]")
        console.print()
        for issue in result["issues"]:
            icon = {"error": "[red]✗[/red]", "warning": "[yellow]![/yellow]",
                     "info": "[blue]ℹ[/blue]"}.get(issue["severity"], "?")
            console.print(f"  {icon} {issue['what']}")
            if issue.get("fix"):
                console.print(f"    [dim]Fix: {issue['fix']}[/dim]")
        if fix:
            console.print()
            fixed = apply_fixes(str(Path(path).resolve()), result["issues"])
            if fixed:
                console.print(f"[green]✓ Auto-fixed {fixed} issue(s)[/green]")


@main.command()
@click.argument("key")
def activate(key):
    """Activate a DevFlow premium license key.

    Stores the key locally (~/.config/devflow/license) so premium
    commands work without re-typing it.

    \b
    Example:
        devflow activate KRYP-XXXX-XXXX-XXXX-XXXX
    """
    from .license import activate as do_activate

    if do_activate(key):
        console.print()
        console.print("[green]✓ Premium license activated.[/green]")
        console.print("  Premium commands are now unlocked.")
        console.print()
    else:
        console.print()
        console.print("[red]✗ Invalid license key format.[/red]")
        console.print("  Get a key at https://kryptorious.gumroad.com/l/jbvet")
        console.print()
        raise SystemExit(1)


@main.command()
@click.option("--path", "-p", default=".", help="Path to the project")
@click.option("--deploy", type=click.Choice(["docker", "aws", "gcp", "vercel"]),
              default="docker", help="Deployment target")
@click.option("--key", default=None, help="Premium license key (or set via 'devflow activate')")
def premium(path, deploy, key):
    """Generate premium CI + infrastructure-as-code (DevFlow Premium).

    Produces a multi-environment GitHub Actions workflow (staging auto /
    production with a manual approval gate), a Dockerfile, docker-compose.yml,
    and per-environment Terraform stubs. Requires a premium license.

    \b
    Examples:
        devflow premium --deploy docker
        devflow premium --deploy aws --key KRYP-XXXX-XXXX-XXXX-XXXX
    """
    from .commands.premium import generate_premium

    console.print()
    console.print(Panel(
        f"[bold]DevFlow Premium[/bold] — CI + IaC for [cyan]{deploy}[/cyan]",
        border_style="blue"))
    ok = generate_premium(str(Path(path).resolve()), deploy, key)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
