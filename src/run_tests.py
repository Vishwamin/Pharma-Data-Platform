"""
Phase 6 — Test Runner Script
=============================
Runs the full test suite with coverage reporting.
Execute from project root:

    python src/run_tests.py

Or run pytest directly:
    pytest tests/ -v                         # all tests
    pytest tests/test_validation.py -v       # validation tests only
    pytest tests/test_build_gold.py -v       # gold layer tests only
    pytest tests/test_config.py -v           # config/structure tests only
    pytest tests/test_data_ingestion.py -v   # raw data tests only
    pytest tests/ -v --tb=short -q           # quiet mode
    pytest tests/ -v -k "TestAgeValidation"  # run only one test class
"""

import sys
import subprocess
from pathlib import Path

# Ensure we run from the project root regardless of where script is called from
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_tests():
    """Run the full Phase 6 test suite with coverage output."""
    print("=" * 65)
    print("  PHASE 6 — PIPELINE TEST SUITE")
    print("=" * 65)
    print()

    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",                       # verbose: show each test name
        "--tb=short",               # short traceback on failure
        "--no-header",
        "-rN",                      # suppress extra summary (handled by -v)
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    print()
    print("=" * 65)
    if result.returncode == 0:
        print("  ALL TESTS PASSED")
    else:
        print(f"  TESTS FAILED (exit code: {result.returncode})")
    print("=" * 65)

    return result.returncode


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
