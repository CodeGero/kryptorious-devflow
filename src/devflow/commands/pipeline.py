"""devflow pipeline — Generate real CI/CD pipeline configurations."""

import os
from pathlib import Path

from ..utils import console, print_success, print_info


def generate_pipeline(project_path: str, platform: str, deploy: str) -> str:
    """Generate a real CI/CD pipeline YAML file.

    Args:
        project_path: Path to the project
        platform: 'github-actions' or 'gitlab-ci'
        deploy: 'none', 'aws', 'gcp', 'vercel', or 'docker'

    Returns:
        Path to the generated file
    """
    root = Path(project_path).resolve()

    if platform in ("github-actions", "all"):
        return _generate_github_actions(root, deploy)
    elif platform == "gitlab-ci":
        return _generate_gitlab_ci(root, deploy)

    return ""


def _generate_github_actions(root: Path, deploy: str) -> str:
    """Generate .github/workflows/ci.yml"""
    workflows_dir = root / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    yaml_content = _build_github_actions_yaml(deploy)
    output_path = workflows_dir / "ci.yml"
    output_path.write_text(yaml_content, encoding="utf-8")

    console.print(f"[green]✓[/green] Generated {output_path}")
    return str(output_path)


def _build_github_actions_yaml(deploy: str) -> str:
    """Build the CI YAML content."""
    lines = [
        "name: CI",
        "",
        "on:",
        "  push:",
        "    branches: [main, master]",
        "  pull_request:",
        "    branches: [main, master]",
        "",
        "jobs:",
        "",
    ]

    # Lint job
    lines.extend([
        "  lint:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - uses: actions/checkout@v4",
        "      - uses: actions/setup-python@v5",
        "        with:",
        "          python-version: '3.12'",
        "      - run: pip install ruff black",
        "      - run: ruff check .",
        "      - run: black --check .",
        "",
    ])

    # Type check
    lines.extend([
        "  typecheck:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - uses: actions/checkout@v4",
        "      - uses: actions/setup-python@v5",
        "        with:",
        "          python-version: '3.12'",
        "      - run: pip install mypy",
        "      - run: mypy src/ --ignore-missing-imports",
        "",
    ])

    # Security scan
    lines.extend([
        "  security:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - uses: actions/checkout@v4",
        "      - uses: actions/setup-python@v5",
        "        with:",
        "          python-version: '3.12'",
        "      - run: pip install bandit",
        "      - run: bandit -r src/ -f txt",
        "",
    ])

    # Test job
    lines.extend([
        "  test:",
        "    runs-on: ubuntu-latest",
        "    strategy:",
        "      matrix:",
        "        python-version: ['3.9', '3.10', '3.11', '3.12', '3.13']",
        "    steps:",
        "      - uses: actions/checkout@v4",
        "      - uses: actions/setup-python@v5",
        "        with:",
        "          python-version: ${{ matrix.python-version }}",
        "      - run: pip install -e '.[dev]'",
        "      - run: pytest --cov=. --cov-report=xml",
        "",
    ])

    # Build + Deploy
    if deploy != "none":
        lines.extend([
            "  build:",
            "    runs-on: ubuntu-latest",
            "    needs: [lint, typecheck, security, test]",
            "    steps:",
            "      - uses: actions/checkout@v4",
            "      - run: pip install build",
            "      - run: python -m build",
            "      - uses: actions/upload-artifact@v4",
            "        with:",
            "          name: dist",
            "          path: dist/",
            "",
        ])

        deploy_configs = {
            "aws": [
                "  deploy:",
                "    runs-on: ubuntu-latest",
                "    needs: [build]",
                "    if: github.ref == 'refs/heads/main'",
                "    steps:",
                "      - uses: actions/download-artifact@v4",
                "        with:",
                "          name: dist",
                "      - uses: aws-actions/configure-aws-credentials@v4",
                "        with:",
                "          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}",
                "          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}",
                "          aws-region: us-east-1",
                "      - run: |",
                "          # Add your deployment commands here",
                "          echo 'Deploy to AWS'",
                "",
            ],
            "gcp": [
                "  deploy:",
                "    runs-on: ubuntu-latest",
                "    needs: [build]",
                "    if: github.ref == 'refs/heads/main'",
                "    steps:",
                "      - uses: actions/download-artifact@v4",
                "        with:",
                "          name: dist",
                "      - uses: google-github-actions/auth@v2",
                "        with:",
                "          credentials_json: ${{ secrets.GCP_SA_KEY }}",
                "      - run: |",
                "          # Add your deployment commands here",
                "          echo 'Deploy to GCP'",
                "",
            ],
            "vercel": [
                "  deploy:",
                "    runs-on: ubuntu-latest",
                "    needs: [build]",
                "    if: github.ref == 'refs/heads/main'",
                "    steps:",
                "      - uses: actions/checkout@v4",
                "      - uses: amondnet/vercel-action@v25",
                "        with:",
                "          vercel-token: ${{ secrets.VERCEL_TOKEN }}",
                "          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}",
                "          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}",
                "",
            ],
            "docker": [
                "  deploy:",
                "    runs-on: ubuntu-latest",
                "    needs: [build]",
                "    if: github.ref == 'refs/heads/main'",
                "    steps:",
                "      - uses: actions/checkout@v4",
                "      - uses: docker/login-action@v3",
                "        with:",
                "          username: ${{ secrets.DOCKER_USERNAME }}",
                "          password: ${{ secrets.DOCKER_PASSWORD }}",
                "      - uses: docker/build-push-action@v5",
                "        with:",
                "          push: true",
                "          tags: latest",
                "",
            ],
        }

        lines.extend(deploy_configs.get(deploy, []))

    # Release job
    lines.extend([
        "  release:",
        "    runs-on: ubuntu-latest",
        "    needs: [deploy] if deploy != 'none' else [test]",
        "    if: github.ref == 'refs/heads/main'",
        "    steps:",
        "      - uses: actions/checkout@v4",
        "        with:",
        "          fetch-depth: 0",
        "      - uses: CodeGero/release-forge@v1",
        "        with:",
        "          github-token: ${{ secrets.GITHUB_TOKEN }}",
        "",
    ])

    return "\n".join(lines)


def _generate_gitlab_ci(root: Path, deploy: str) -> str:
    """Generate .gitlab-ci.yml"""
    lines = [
        "stages:",
        "  - lint",
        "  - test",
        "  - security",
        "  - build",
        "  - deploy",
        "",
        "lint:",
        "  stage: lint",
        "  image: python:3.12",
        "  script:",
        "    - pip install ruff black",
        "    - ruff check .",
        "    - black --check .",
        "",
        "typecheck:",
        "  stage: lint",
        "  image: python:3.12",
        "  script:",
        "    - pip install mypy",
        "    - mypy src/ --ignore-missing-imports",
        "",
        "security:",
        "  stage: security",
        "  image: python:3.12",
        "  script:",
        "    - pip install bandit",
        "    - bandit -r src/ -f txt",
        "",
        "test:",
        "  stage: test",
        "  image: python:3.12",
        "  script:",
        "    - pip install -e '.[dev]'",
        "    - pytest --cov=. --cov-report=xml",
        "",
    ]

    if deploy != "none":
        lines.extend([
            "build:",
            "  stage: build",
            "  image: python:3.12",
            "  script:",
            "    - pip install build",
            "    - python -m build",
            "  artifacts:",
            "    paths:",
            "      - dist/",
            "",
            f"deploy:",
            f"  stage: deploy",
            f"  script:",
            f"    - echo 'Deploying to {deploy}...'",
            "",
        ])

    output_path = root / ".gitlab-ci.yml"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"[green]✓[/green] Generated {output_path}")
    return str(output_path)
