"""
Root pytest conftest — makes `src` and `scripts` importable as
`src.foo`/`scripts.foo` regardless of which directory pytest is invoked
from, and loads .env before any test module imports src.core.config.

This replaces the old per-test-file `sys.path.insert(...,'../../src')`
pattern, which only worked for non-relative imports and was part of why
`api.routes`'s relative imports (`from ..core...`) were never actually
exercised — see zima_codebase_audit memory / PR notes for the audit trail.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()
