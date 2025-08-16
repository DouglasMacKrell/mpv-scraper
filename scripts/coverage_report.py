#!/usr/bin/env python3
"""Coverage reporting script for local development.

This script generates coverage reports and provides coverage analysis
for the MPV Scraper project.
"""

import subprocess
import sys
from pathlib import Path


def run_coverage_report():
    """Run coverage report and display results."""
    print("🔍 Running coverage report...")

    # Run pytest with coverage
    result = subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "--cov=src/mpv_scraper",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-fail-under=65",
            "-q",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("❌ Coverage check failed!")
        print(result.stdout)
        print(result.stderr)
        return False

    print("✅ Coverage check passed!")
    print(result.stdout)

    # Check if HTML report was generated
    htmlcov_dir = Path("htmlcov")
    if htmlcov_dir.exists():
        index_file = htmlcov_dir / "index.html"
        if index_file.exists():
            print(f"📊 HTML coverage report generated: {index_file.absolute()}")
            print("   Open this file in your browser to view detailed coverage.")

    return True


def check_coverage_threshold():
    """Check if coverage meets minimum threshold."""
    print("🎯 Checking coverage threshold...")

    result = subprocess.run(
        [
            "python",
            "-m",
            "pytest",
            "--cov=src/mpv_scraper",
            "--cov-report=term",
            "--cov-fail-under=65",
            "-q",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("✅ Coverage threshold (65%) met!")
        return True
    else:
        print("❌ Coverage threshold (65%) not met!")
        print(result.stdout)
        return False


def main():
    """Main function."""
    print("📊 MPV Scraper Coverage Report")
    print("=" * 40)

    # Check if pytest and coverage are available
    try:
        import importlib.util

        if not importlib.util.find_spec("pytest"):
            raise ImportError("pytest not found")
        if not importlib.util.find_spec("coverage"):
            raise ImportError("coverage not found")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install pytest-cov: pip install pytest-cov")
        sys.exit(1)

    # Run coverage report
    success = run_coverage_report()

    if not success:
        print("\n💡 Tips to improve coverage:")
        print("   - Add tests for untested functions")
        print("   - Test error conditions and edge cases")
        print(
            "   - Run 'pytest --cov=src/mpv_scraper --cov-report=html' for detailed report"
        )
        sys.exit(1)

    print("\n🎉 Coverage report completed successfully!")


if __name__ == "__main__":
    main()
