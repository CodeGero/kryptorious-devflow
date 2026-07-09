"""devflow init — Smart project scaffolding.

Creates production-ready project structures with best practices baked in.
"""

import os
import stat
from pathlib import Path
from typing import Dict, List

from ..utils import (
    console, print_header, print_success, print_info, print_warning, run_cmd
)


TEMPLATES = ["python", "node", "fullstack", "cli", "api", "lib"]


def _safe_pkg_name(name: str) -> str:
    """Convert project name to valid Python package name."""
    return name.replace("-", "_").replace(" ", "_").lower()


def run(name: str, template: str, path: str, docker: bool,
        ci: bool, git_init: bool, license_type: str, description: str):
    """Scaffold a new project."""

    project_dir = Path(path).resolve() / name
    pkg_name = _safe_pkg_name(name)

    if project_dir.exists():
        console.print(f"[red]Error:[/red] Directory '{project_dir}' already exists.")
        return

    print_header(f"DevFlow Init — Scaffolding [bold cyan]{name}[/bold cyan] ({template})")

    # Build file tree
    files = _build_template(name, pkg_name, template, description, license_type, docker, ci)

    # Create directories and files
    dirs_created = 0
    files_created = 0

    for filepath, content in files.items():
        full_path = project_dir / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if content is not None:
            full_path.write_text(content, encoding="utf-8")
            files_created += 1
        else:
            # Just create directory
            full_path.mkdir(parents=True, exist_ok=True)
            dirs_created += 1

    # Make scripts executable
    for script in [".github/workflows/ci.yml"]:
        sp = project_dir / script
        if sp.exists():
            sp.chmod(sp.stat().st_mode | stat.S_IEXEC)

    print_success(f"Created {dirs_created} directories, {files_created} files in {project_dir}")

    # Initialize git
    if git_init:
        code, out, err = run_cmd(["git", "init"], cwd=str(project_dir))
        if code == 0:
            print_success("Initialized git repository")
            # Create .gitignore
            gitignore = project_dir / ".gitignore"
            gitignore.write_text(_gitignore_content(template))
            # Initial commit
            run_cmd(["git", "add", "-A"], cwd=str(project_dir))
            run_cmd(["git", "commit", "-m", f"Initial commit — DevFlow scaffold ({template})"],
                    cwd=str(project_dir))
            print_success("Created initial commit")
        else:
            print_warning(f"Git init failed: {err}")

    # Install dependencies if possible
    if template in ("python", "cli", "api", "lib", "fullstack"):
        if _has_uv():
            code, out, err = run_cmd(["uv", "pip", "install", "-e", "."], cwd=str(project_dir))
        else:
            code, out, err = run_cmd([os.sys.executable, "-m", "pip", "install", "-e", "."],
                                     cwd=str(project_dir))
        if code == 0:
            print_success("Installed project in development mode")
        else:
            print_info("Run 'pip install -e .' to install in dev mode")

    # Show next steps
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  cd {name}")
    console.print(f"  devflow audit              # Check project health")
    console.print(f"  devflow fix                # Auto-fix issues")
    console.print(f"  devflow ship --bump patch  # Ship your first release")
    console.print()


def _build_template(name: str, pkg_name: str, template: str, description: str,
                    license_type: str, docker: bool, ci: bool) -> Dict[str, str]:
    """Build the file tree for a template."""

    desc = description or f"{name} — built with DevFlow"

    if template in ("python", "cli", "api", "lib"):
        return _python_template(name, pkg_name, template, desc, license_type, docker, ci)
    elif template == "node":
        return _node_template(name, desc, license_type, docker, ci)
    elif template == "go":
        return _go_template(name, pkg_name, desc, license_type, docker, ci)
    elif template == "rust":
        return _rust_template(name, pkg_name, desc, license_type, docker, ci)
    elif template == "react":
        return _react_template(name, desc, license_type, docker, ci)
    elif template == "fullstack":
        return _fullstack_react_template(name, pkg_name, desc, license_type, docker, ci)
    else:
        return _python_template(name, pkg_name, "python", desc, license_type, docker, ci)


def _python_template(display_name: str, pkg_name: str, subtype: str, desc: str,
                     license_type: str, docker: bool, ci: bool) -> Dict[str, str]:
    """Python project template."""
    name = pkg_name  # backward compatibility alias within this function

    files = {}

    # pyproject.toml
    deps = []
    dev_deps = ['pytest>=7.0', 'pytest-cov>=4.0', 'black>=23.0', 'ruff>=0.1', 'mypy>=1.0']
    if subtype == "api":
        deps = ['fastapi>=0.100', 'uvicorn>=0.23']
    elif subtype == "cli":
        deps = ['click>=8.0', 'rich>=13.0']
    elif subtype == "lib":
        dev_deps.extend(['sphinx>=7.0', 'furo>=2024'])

    deps_str = ',\n    '.join(f'"{d}"' for d in deps)
    dev_str = ',\n    '.join(f'"{d}"' for d in dev_deps)

    # Build dependencies section (skip if empty)
    deps_section = ""
    if deps:
        deps_section = f"\ndependencies = [\n    {deps_str},\n]"
    else:
        deps_section = "\ndependencies = []"

    if subtype == "lib":
        cli_entry = ""
    else:
        cli_entry = f'\n[project.scripts]\n{display_name} = "{pkg_name}.cli:main"\n'

    extra_requires = ""
    if dev_deps:
        extra_requires = f'\n[project.optional-dependencies]\ndev = [\n    {dev_str},\n]\n'

    files[f"src/{pkg_name}/__init__.py"] = f'"""{desc}"""\n\n__version__ = "0.1.0"\n'

    if subtype != "lib":
        files[f"src/{pkg_name}/cli.py"] = _generate_cli_stub(pkg_name, desc)

    files[f"src/{pkg_name}/core.py"] = _generate_core_stub(pkg_name, subtype)

    files["pyproject.toml"] = f"""[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{display_name}"
version = "0.1.0"
description = "{desc}"
readme = "README.md"
license = {{text = "{license_type}"}}
requires-python = ">=3.9"
authors = [{{name = "Your Name"}}]{deps_section}{extra_requires}{cli_entry}
[tool.setuptools.packages.find]
where = ["src"]

[tool.black]
line-length = 100
target-version = ["py39"]

[tool.ruff]
line-length = 100
target-version = "py39"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.9"
strict = true
ignore_missing_imports = true
"""

    # Tests
    files["tests/__init__.py"] = ""
    files["tests/test_core.py"] = f'''"""Tests for {name}."""\n\nfrom {name}.core import hello\n\n\ndef test_hello():\n    assert hello() == "Hello from {name}, world!"\n\ndef test_hello_custom():\n    assert hello("World") == "Hello from {name}, World!"\n'''

    # README
    files["README.md"] = _generate_readme(name, desc, subtype)

    # CI
    if ci:
        files[".github/workflows/ci.yml"] = _generate_ci(name)

    # Docker
    if docker:
        files["Dockerfile"] = _generate_dockerfile(name, subtype)

    # License
    if license_type == "MIT":
        files["LICENSE"] = _mit_license()

    return files


def _node_template(name: str, desc: str, license_type: str,
                   docker: bool, ci: bool) -> Dict[str, str]:
    """Node.js project template."""
    files = {}

    files["package.json"] = f'''{{
  "name": "{name}",
  "version": "0.1.0",
  "description": "{desc}",
  "main": "src/index.js",
  "scripts": {{
    "start": "node src/index.js",
    "test": "jest",
    "lint": "eslint src/",
    "format": "prettier --write src/"
  }},
  "license": "{license_type}"
}}
'''

    files["src/index.js"] = f'''/**
 * {name} — {desc}
 */

function hello(name = "world") {{
  return `Hello from {name}, ${{name}}!`;
}}

module.exports = {{ hello }};

if (require.main === module) {{
  console.log(hello());
}}
'''

    files["tests/index.test.js"] = f'''const {{ hello }} = require("../src/index");

test("returns greeting", () => {{
  expect(hello()).toBe("Hello from {name}, world!");
}});

test("custom name", () => {{
  expect(hello("Dev")).toBe("Hello from {name}, Dev!");
}});
'''

    files["README.md"] = _generate_readme(name, desc, "node")
    files[".gitignore"] = "node_modules/\ndist/\n.env\n"

    if ci:
        files[".github/workflows/ci.yml"] = _generate_ci_node(name)
    if docker:
        files["Dockerfile"] = _generate_dockerfile_node(name)
    if license_type == "MIT":
        files["LICENSE"] = _mit_license()

    return files


def _fullstack_template(name: str, desc: str, license_type: str,
                        docker: bool, ci: bool) -> Dict[str, str]:
    """Full-stack project (Python backend + Node frontend)."""
    files = {}

    # Backend
    files.update(_python_template(f"{name}", "api", desc, license_type, docker, ci))

    # Frontend
    fe_name = f"{name}-frontend"
    fe_files = _node_template(fe_name, f"{desc} — frontend", license_type, docker, ci)
    for k, v in fe_files.items():
        files[f"frontend/{k}"] = v

    # Root docker-compose
    if docker:
        files["docker-compose.yml"] = f"""version: "3.8"
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src
    environment:
      - ENV=development

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src
    depends_on:
      - backend
"""

    # Root README
    files["README.md"] = f"""# {name}

{desc}

## Architecture

- `backend/` — Python FastAPI backend
- `frontend/` — Node.js React frontend

## Quick Start

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn {name}.main:app --reload

# Frontend
cd frontend
npm install
npm start
```

Built with [DevFlow](https://devflow.sh).
"""

    return files


def _generate_cli_stub(name: str, desc: str) -> str:
    return f'''"""{desc} — CLI entry point."""

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """{desc}"""
    pass


@main.command()
@click.argument("name", default="world")
def hello(name: str):
    """Say hello."""
    from .core import hello as say_hello
    console.print(say_hello(name))


if __name__ == "__main__":
    main()
'''


def _generate_core_stub(name: str, subtype: str) -> str:
    return f'''"""{name} core module."""


def hello(name: str = "world") -> str:
    """Return a friendly greeting.

    Args:
        name: Who to greet (default: world)

    Returns:
        A greeting string
    """
    return f"Hello from {name}, {{name}}!"
'''


def _generate_readme(name: str, desc: str, subtype: str) -> str:
    badges = ""
    if subtype in ("python", "cli", "api", "lib"):
        badges = "![Python](https://img.shields.io/badge/python-3.9+-blue.svg)\n"

    return f"""# {name}

{badges}
{desc}

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/
ruff check src/ tests/ --fix
```

## Project Structure

```
src/{name}/     # Application code
tests/          # Test suite
pyproject.toml  # Project config and dependencies
```

## Built with DevFlow

Scaffolded using [DevFlow](https://devflow.sh) — the developer workflow automation CLI.
"""


def _generate_ci(name: str) -> str:
    return f"""name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ matrix.python-version }}}}

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Lint
        run: |
          ruff check src/ tests/
          black --check src/ tests/

      - name: Type check
        run: |
          mypy src/

      - name: Test
        run: |
          pytest --cov={name} --cov-report=term-missing
"""


def _generate_ci_node(name: str) -> str:
    return f"""name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18, 20, 22]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{{{ matrix.node-version }}}}

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Test
        run: npm test
"""


def _generate_dockerfile(name: str, subtype: str) -> str:
    if subtype == "api":
        cmd = f'CMD ["uvicorn", "{name}.main:app", "--host", "0.0.0.0", "--port", "8000"]'
    elif subtype == "cli":
        cmd = f'CMD ["{name}"]'
    else:
        cmd = f'CMD ["python", "-m", "{name}"]'

    return f"""FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e .

{cmd}
"""


def _generate_dockerfile_node(name: str) -> str:
    return f"""FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --production

COPY src/ src/

CMD ["node", "src/index.js"]
"""


def _gitignore_content(template: str) -> str:
    base = """# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg

# Virtual environments
.venv/
venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Environment
.env
.env.local
.env.*.local

# Coverage
htmlcov/
.coverage
.coverage.*
coverage.xml

# Misc
*.log
"""

    if template == "node":
        return "node_modules/\ndist/\n.env\n" + base.split("__pycache__")[0]
    elif template == "fullstack":
        return "node_modules/\ndist/\n" + base

    return base


def _mit_license() -> str:
    from datetime import datetime
    year = datetime.now().year
    return f"""MIT License

Copyright (c) {year}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def _go_template(name: str, pkg_name: str, desc: str,
                 license_type: str, docker: bool, ci: bool) -> Dict[str, str]:
    """Go project template."""
    module_path = f"github.com/{pkg_name}/{name}"

    files = {}
    files["go.mod"] = f"""module {module_path}

go 1.22
"""
    files["main.go"] = f"""package main

import "fmt"

func main() {{
    fmt.Println(hello("world"))
}}

func hello(name string) string {{
    return fmt.Sprintf("Hello from {name}, %s!", name)
}}
"""
    files["main_test.go"] = f"""package main

import "testing"

func TestHello(t *testing.T) {{
    got := hello("world")
    want := "Hello from {name}, world!"
    if got != want {{
        t.Errorf("hello() = %q, want %q", got, want)
    }}
}}

func TestHelloCustom(t *testing.T) {{
    got := hello("DevFlow")
    want := "Hello from {name}, DevFlow!"
    if got != want {{
        t.Errorf("hello(\\"DevFlow\\") = %q, want %q", got, want)
    }}
}}
"""
    files["README.md"] = f"""# {name}

{desc}

## Quick Start

```bash
go run main.go
go test ./...
```

Built with [DevFlow](https://devflow.sh).
"""
    files[".gitignore"] = """# Binaries
*.exe
*.exe~
*.dll
*.so
*.dylib
bin/
dist/

# Test binary
*.test

# Go workspace
go.work

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
.env
"""

    if ci:
        files[".github/workflows/ci.yml"] = f"""name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: "1.22"
      - name: Test
        run: go test ./...
      - name: Vet
        run: go vet ./...
"""

    if docker:
        files["Dockerfile"] = f"""FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod ./
COPY *.go ./
RUN go build -o /{name} .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
COPY --from=builder /{name} /{name}
CMD ["/{name}"]
"""

    if license_type == "MIT":
        files["LICENSE"] = _mit_license()

    return files


def _rust_template(name: str, pkg_name: str, desc: str,
                   license_type: str, docker: bool, ci: bool) -> Dict[str, str]:
    """Rust project template."""
    safe_name = pkg_name.replace("_", "-")

    files = {}
    files["Cargo.toml"] = f"""[package]
name = "{safe_name}"
version = "0.1.0"
edition = "2021"
description = "{desc}"
license = "{license_type}"

[dependencies]
"""
    files["src/main.rs"] = f"""fn main() {{
    println!("{{}}", hello("world"));
}}

fn hello(name: &str) -> String {{
    format!("Hello from {safe_name}, {{}}!", name)
}}

#[cfg(test)]
mod tests {{
    use super::*;

    #[test]
    fn test_hello() {{
        assert_eq!(hello("world"), "Hello from {safe_name}, world!");
    }}

    #[test]
    fn test_hello_custom() {{
        assert_eq!(hello("DevFlow"), "Hello from {safe_name}, DevFlow!");
    }}
}}
"""
    files["README.md"] = f"""# {name}

{desc}

## Quick Start

```bash
cargo run
cargo test
cargo build --release
```

Built with [DevFlow](https://devflow.sh).
"""
    files[".gitignore"] = """target/
Cargo.lock
**/*.rs.bk
*.pdb
.vscode/
.idea/
.DS_Store
"""

    if ci:
        files[".github/workflows/ci.yml"] = f"""name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions-rust-lang/setup-rust-toolchain@v1
      - name: Test
        run: cargo test
      - name: Clippy
        run: cargo clippy -- -D warnings
      - name: Format check
        run: cargo fmt --check
"""

    if docker:
        files["Dockerfile"] = f"""FROM rust:1.82-slim AS builder
WORKDIR /app
COPY Cargo.toml ./
COPY src/ src/
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/{safe_name} /usr/local/bin/{safe_name}
CMD ["{safe_name}"]
"""

    if license_type == "MIT":
        files["LICENSE"] = _mit_license()

    return files


def _react_template(name: str, desc: str, license_type: str,
                    docker: bool, ci: bool) -> Dict[str, str]:
    """React (Vite + TypeScript) project template."""
    files = {}

    files["package.json"] = f'''{{
  "name": "{name}",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx",
    "test": "vitest run"
  }},
  "dependencies": {{
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  }},
  "devDependencies": {{
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.6.0",
    "vite": "^6.0.0",
    "vitest": "^3.0.0"
  }}
}}
'''

    files["tsconfig.json"] = """{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
"""

    files["vite.config.ts"] = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})
"""

    files["index.html"] = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{name}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

    files["src/main.tsx"] = """import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
"""

    files[f"src/App.tsx"] = f"""import {{ useState }} from 'react'

function App() {{
  const [count, setCount] = useState(0)

  return (
    <div style={{{{ padding: '2rem', fontFamily: 'system-ui' }}}}>
      <h1>{name}</h1>
      <p>{desc}</p>
      <button onClick={{() => setCount(c => c + 1)}}>
        Count: {{count}}
      </button>
    </div>
  )
}}

export default App
"""

    files["src/App.test.tsx"] = f"""import {{ describe, it, expect }} from 'vitest'
import {{ render, screen }} from '@testing-library/react'
import App from './App'

describe('App', () => {{
  it('renders project name', () => {{
    render(<App />)
    expect(screen.getByText('{name}')).toBeDefined()
  }})
}})
"""

    files["README.md"] = f"""# {name}

{desc}

## Quick Start

```bash
npm install
npm run dev
```

Built with [DevFlow](https://devflow.sh).
"""
    files[".gitignore"] = """node_modules/
dist/
.env
*.local
"""

    if ci:
        files[".github/workflows/ci.yml"] = f"""name: CI

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm ci
      - run: npm test
      - run: npm run build
"""

    if docker:
        files["Dockerfile"] = f"""FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""

    if license_type == "MIT":
        files["LICENSE"] = _mit_license()

    return files


def _fullstack_react_template(name: str, pkg_name: str, desc: str,
                              license_type: str, docker: bool, ci: bool) -> Dict[str, str]:
    """Full-stack: Python FastAPI backend + React TypeScript frontend."""
    files = {}

    # Backend
    be_files = _python_template(f"{name}-backend", f"{pkg_name}_backend", "api", f"{desc} — Backend API", license_type, docker, ci)
    for k, v in be_files.items():
        files[f"backend/{k}"] = v

    # Frontend
    fe_files = _react_template(f"{name}-frontend", f"{desc} — Frontend", license_type, docker, ci)
    for k, v in fe_files.items():
        files[f"frontend/{k}"] = v

    # Root
    files["README.md"] = f"""# {name}

{desc}

## Architecture

- `backend/` — Python FastAPI REST API
- `frontend/` — React TypeScript SPA (Vite)

## Quick Start

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn {pkg_name}_backend.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Built with [DevFlow](https://devflow.sh).
"""

    if docker:
        files["docker-compose.yml"] = f"""services:
  backend:
    build:
      context: ./backend
    ports:
      - "8000:8000"
    environment:
      - ENV=development

  frontend:
    build:
      context: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
"""

    return files


def _has_uv() -> bool:
    """Check if uv is available."""
    import subprocess
    return subprocess.run(["which", "uv"], capture_output=True).returncode == 0
