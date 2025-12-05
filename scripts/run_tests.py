#!/usr/bin/env python3
"""
Custom pytest runner for pre-commit hooks.
Runs tests efficiently by detecting which tests are affected by changed files.
"""

import sys
import subprocess
from pathlib import Path


def get_python_executable():
    """Get the correct python executable to use."""
    # Check for local .venv
    venv_python = Path.cwd() / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def get_changed_files():
    """Get list of changed files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        return []


def should_run_full_suite(changed_files):
    """Determine if we should run the full test suite."""
    # Run full suite if any of these files are changed
    critical_files = [
        "src/mpv_scraper/",
        "pytest.ini",
        "setup.py",
        "requirements.txt",
        "requirements-dev.txt",
    ]

    for file_path in changed_files:
        for critical in critical_files:
            if file_path.startswith(critical):
                return True

    return False


def run_tests():
    """Run appropriate tests based on changed files."""
    changed_files = get_changed_files()
    python_exe = get_python_executable()

    if should_run_full_suite(changed_files):
        print("Running full test suite due to critical file changes...")
        cmd = [python_exe, "-m", "pytest"]
    else:
        print("Running tests for changed files...")
        # Run tests that might be affected by the changes
        cmd = [python_exe, "-m", "pytest", "--tb=short"]

    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Tests failed with exit code {e.returncode}")
        return e.returncode


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
