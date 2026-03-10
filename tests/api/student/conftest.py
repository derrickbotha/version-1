"""
Local conftest for student API tests.

Disables the global app-level rate limiter so that running many tests
in the same session does not trigger 429 errors.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_global_rate_limiter():
    """Disable the global slowapi rate limiter for every test in this package."""
    try:
        from app.main import limiter as _global_limiter
        _global_limiter.enabled = False
        yield
        _global_limiter.enabled = True
    except Exception:
        yield
