"""
Local conftest for api/auth tests.
Disables the global rate limiter so auth tests don't exceed the limit
when run as part of the full test suite.
"""
import pytest

@pytest.fixture(autouse=True)
def _disable_global_limiter():
    """Disable the app-level rate limiter for auth API tests."""
    try:
        from app.main import limiter as _global_limiter
        was_enabled = _global_limiter.enabled
        _global_limiter.enabled = False
        yield
        _global_limiter.enabled = was_enabled
    except Exception:
        yield
