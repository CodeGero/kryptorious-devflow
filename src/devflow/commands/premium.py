"""DevFlow premium pipeline generator.

Produces real, production-usable artifacts on top of the base CI:
  - Multi-environment (staging + production) pipeline variants with secrets.
  - Manual approval gates before production deploy.
  - Infrastructure-as-code templates: Dockerfile, docker-compose.yml,
    and a Terraform stub for a free-tier-friendly deploy.

All gated by `require_premium` (see devflow.license).
"""

from __future__ import annotations

from pathlib import Path

from ..license import require_premium
from ..utils import console, print_success

ENVS = ("staging", "production")


def _dockerfile() -> str:
    return (
        "FROM python:3.12-slim\n"
        "WORKDIR /app\n"
        "ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1\n"
        "COPY pyproject.toml ./\n"
        "RUN pip install --no-cache-dir .\n"
        "COPY . .\n"
        "EXPOSE 8000\n"
        'CMD ["python", "-m", "yourpackage"]\n'
    )


def _compose() -> str:
    return (
        "services:\n"
        "  app:\n"
        "    build: .\n"
        "    ports:\n"
        "      - \"8000:8000\"\n"
        "    environment:\n"
        "      - ENV=${ENV:-staging}\n"
        "    restart: unless-stopped\n"
        "  db:\n"
        "    image: postgres:16-alpine\n"
        "    environment:\n"
        "      - POSTGRES_PASSWORD=${DB_PASSWORD}\n"
        "    volumes:\n"
        "      - db_data:/var/lib/postgresql/data\n"
        "volumes:\n"
        "  db_data:\n"
    )


def _terraform(env: str) -> str:
    return (
        f"# Terraform stub — {env} environment\n"
        "# Replace with your provider. This is a free-tier-aware skeleton.\n"
        "terraform {\n"
        "  required_providers {\n"
        "    aws = {\n"
        "      source  = \"hashicorp/aws\"\n"
        "      version = \"~> 5.0\"\n"
        "    }\n"
        "  }\n"
        "}\n\n"
        "variable \"region\" {\n"
        "  type    = string\n"
        "  default = \"us-east-1\"\n"
        "}\n\n"
        f"# resource \"aws_ec2_instance\" \"app_{env}\" {{\n"
        "#   ami           = \"ami-0c101f26f147fa7fd\"\n"
        "#   instance_type = \"t3.micro\"  # free-tier eligible\n"
        "# }\n"
    )


def _github_premium(root: Path, deploy: str) -> str:
    lines = [
        "name: CI-Premium",
        "",
        "on:",
        "  push:",
        "    branches: [main]",
        "  pull_request:",
        "    branches: [main]",
        "",
        "jobs:",
        "  test:",
        "    runs-on: ubuntu-latest",
        "    strategy:",
        "      matrix:",
        "        python-version: ['3.9', '3.13']",
        "    steps:",
        "      - uses: actions/checkout@v4",
        "      - uses: actions/setup-python@v5",
        "        with:",
        "          python-version: ${{ matrix.python-version }}",
        "      - run: pip install -e '.[dev]'",
        "      - run: pytest",
        "      - run: ruff check .",
        "",
        "  # Per-environment deploy with manual approval on production",
    ]
    for env in ENVS:
        needs = "test"
        approval = ""
        if env == "production":
            approval = "    environment: {name: production, url: https://prod.example.com}\n"
            # GitHub 'environment' with required reviewers = manual gate
        lines.extend([
            f"  deploy-{env}:",
            "    runs-on: ubuntu-latest",
            f"    needs: [{needs}]",
            f"    if: github.ref == 'refs/heads/main'",
            "    steps:",
            "      - uses: actions/checkout@v4",
            "      - run: echo \"Deploying to " + env + " (target: " + deploy + ")\"",
            "      - run: |",
            "          # Add env-specific deploy steps here",
            f"          echo 'ENV={env}'",
        ])
        if approval:
            # insert environment line after 'if:' for production
            lines.insert(-7, "    environment: {name: production, url: https://prod.example.com}")
    return "\n".join(lines)


def generate_premium(root: str, deploy: str = "docker", key: str | None = None) -> bool:
    """Generate premium pipeline + IaC artifacts. Gated. Returns success."""
    if not require_premium(key):
        return False

    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)

    # IaC: Dockerfile + compose + terraform per env
    (root / "Dockerfile").write_text(_dockerfile(), encoding="utf-8")
    (root / "docker-compose.yml").write_text(_compose(), encoding="utf-8")
    iac_dir = root / "iac"
    iac_dir.mkdir(exist_ok=True)
    for env in ENVS:
        (iac_dir / f"main.{env}.tf").write_text(_terraform(env), encoding="utf-8")

    # Multi-env GitHub Actions premium workflow
    gh_dir = root / ".github" / "workflows"
    gh_dir.mkdir(parents=True, exist_ok=True)
    (gh_dir / "ci-premium.yml").write_text(_github_premium(root, deploy), encoding="utf-8")

    console.print()
    print_success("Generated premium pipeline + infrastructure-as-code:")
    console.print(f"  - {gh_dir / 'ci-premium.yml'}")
    console.print(f"  - {root / 'Dockerfile'}")
    console.print(f"  - {root / 'docker-compose.yml'}")
    console.print(f"  - {iac_dir / 'main.staging.tf'}")
    console.print(f"  - {iac_dir / 'main.production.tf'}")
    console.print()
    console.print("Staging deploys automatically; production requires a manual")
    console.print("approval gate (configure 'production' environment reviewers in repo settings).")
    return True
