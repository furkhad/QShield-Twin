"""Shared pytest configuration.

Ensures tests are hermetic: they must never read or write the developer's real
``qshield_twin.db`` or production configuration. Environment variables are set
here, before any ``backend`` module is imported, so the cached settings pick
them up.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Use a throwaway on-disk SQLite database for the whole test session.
_TEST_DB = Path(tempfile.gettempdir()) / "qshield_twin_test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"
