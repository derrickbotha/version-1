"""
Fraud detection rules (spec §11).

Rules:
  - 3 deposits in 2 minutes → flag account
  - 5 failed payments in 10 minutes → block payments
  - deposits > $2000 → KYC flag
  - multiple country logins in 24h → identity flag (future: geo-IP lookup)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

import redis

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    _redis: redis.Redis = redis.from_url(settings.redis_url, decode_responses=True)
    _redis.ping()
    _REDIS_OK = True
except Exception:
    _redis = None  # type: ignore[assignment]
    _REDIS_OK = False
    logger.warning("Fraud service: Redis unavailable — fraud checks bypassed")


def _incr(key: str, window_seconds: int) -> int:
    """Increment a sliding-window counter in Redis."""
    if not _REDIS_OK or _redis is None:
        return 0
    pipe = _redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    results = pipe.execute()
    return int(results[0])


def check_deposit(user_id: uuid.UUID, amount: float) -> tuple[bool, str | None]:
    """
    Returns (flagged, reason).
    flagged=True means the deposit should be blocked/flagged.
    """
    uid = str(user_id)

    # Rule: deposits > $2000 → KYC required
    if amount > 2000:
        logger.warning("Fraud: large deposit user=%s amount=%s", uid, amount)
        return True, "Deposits over $2,000 require identity verification. Please contact support."

    # Rule: 3 deposits in 2 minutes → flag
    count = _incr(f"fraud:deposits:{uid}", window_seconds=120)
    if count >= 3:
        logger.warning("Fraud: rapid deposits user=%s count=%s", uid, count)
        return True, "Too many deposit attempts. Please wait a few minutes before trying again."

    return False, None


def record_failed_payment(user_id: uuid.UUID) -> tuple[bool, str | None]:
    """
    Record a failed payment attempt.
    Returns (blocked, reason) — blocked=True means payments should be refused.
    """
    uid = str(user_id)
    count = _incr(f"fraud:fails:{uid}", window_seconds=600)
    if count >= 5:
        logger.warning("Fraud: payment failures user=%s count=%s", uid, count)
        return True, "Too many failed payment attempts. Payments blocked for 10 minutes."
    return False, None


def check_payment_blocked(user_id: uuid.UUID) -> bool:
    """Return True if the user's payments are currently blocked."""
    if not _REDIS_OK or _redis is None:
        return False
    uid = str(user_id)
    val = _redis.get(f"fraud:fails:{uid}")
    return int(val or 0) >= 5
