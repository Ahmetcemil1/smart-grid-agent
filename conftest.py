"""
conftest.py — pytest configuration for Smart-Grid Agent.

This file is automatically loaded by pytest before any test runs.
It adds the backend directory to sys.path so all test imports resolve correctly
without IDE or CI configuration changes.
"""

import sys
from pathlib import Path

# Make backend modules importable from tests/
BACKEND_DIR = Path(__file__).parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
