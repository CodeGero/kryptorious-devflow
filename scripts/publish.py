#!/usr/bin/env python3
"""Auto-publish script for DevFlow. Run via cron to publish new versions to PyPI."""
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path("D:/aitest/devflow")
CREDENTIALS_FILE = Path.home() / "AppData/Local/hermes/credentials/.pypirc"

def get_pypi_password():
    with open(CREDENTIALS_FILE) as f:
        for line in f:
            if line.startswith("password = "):
                return line.split(" = ", 1)[1].strip()
    raise RuntimeError("PyPI password not found in credentials file")

def main():
    # Check if there's a version bump
    pyproject = PROJECT_DIR / "pyproject.toml"
    content = pyproject.read_text()
    
    # Only publish if dist files exist
    dist_dir = PROJECT_DIR / "dist"
    if not dist_dir.exists() or not list(dist_dir.glob("*.whl")):
        print("No distribution files. Run 'python -m build' first.")
        return 1
    
    # Publish
    import os
    os.environ["TWINE_USERNAME"] = "__token__"
    os.environ["TWINE_PASSWORD"] = get_pypi_password()
    
    result = subprocess.run(
        [sys.executable, "-m", "twine", "upload", str(dist_dir / "*")],
        cwd=str(PROJECT_DIR),
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode
    
    print("Published successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
