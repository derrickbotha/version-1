"""
Disable rate limiting and fraud checks for tests in this directory.
"""
from __future__ import annotations
import pytest

@pytest.fixture(autouse=True)
def _disable_rate_limit_and_fraud():
    """Disable the main app rate limiter and fraud checks."""
    try:
        from app.main import limiter as _main_limiter
        _main_limiter.enabled = False
        # Also reset the storage to clear any accumulated counts
        try:
            _main_limiter._storage.reset()
        except Exception:
            pass
    except Exception:
        _main_limiter = None

    try:
        import app.services.fraud_service as _fraud
        _orig_redis_ok = _fraud._REDIS_OK
        _fraud._REDIS_OK = False
    except Exception:
        _orig_redis_ok = None
        _fraud = None

    yield

    if _main_limiter is not None:
        try:
            _main_limiter.enabled = True
        except Exception:
            pass

    if _fraud is not None and _orig_redis_ok is not None:
        try:
            _fraud._REDIS_OK = _orig_redis_ok
        except Exception:
            pass

