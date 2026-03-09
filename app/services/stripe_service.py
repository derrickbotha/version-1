"""
Stripe payment integration (spec §7).

Handles:
  - Creating PaymentIntents for wallet top-up
  - Webhook event verification and processing
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.payment import PaymentMethod
from app.services import payment_service

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_stripe():
    """Lazy import + configure stripe."""
    try:
        import stripe as _stripe  # noqa: PLC0415
        if not settings.stripe_secret_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe is not configured on this server.",
            )
        _stripe.api_key = settings.stripe_secret_key
        return _stripe
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe library not installed.",
        )


def create_payment_intent(
    amount: Decimal,
    user_id: uuid.UUID,
    idempotency_key: str | None = None,
) -> dict:
    """
    Create a Stripe PaymentIntent for a wallet deposit (spec §7).
    Returns {client_secret, payment_intent_id, publishable_key}.
    """
    stripe = _get_stripe()
    amount_cents = int(amount * 100)
    kwargs: dict = dict(
        amount=amount_cents,
        currency="usd",
        metadata={"user_id": str(user_id), "purpose": "wallet_deposit"},
        automatic_payment_methods={"enabled": True},
    )
    if idempotency_key:
        kwargs["idempotency_key"] = idempotency_key

    try:
        intent = stripe.PaymentIntent.create(**kwargs)
        return {
            "client_secret": intent["client_secret"],
            "payment_intent_id": intent["id"],
            "publishable_key": settings.stripe_publishable_key,
        }
    except Exception as exc:
        logger.exception("Stripe PaymentIntent creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment provider error: {exc}",
        )


def handle_webhook(payload: bytes, sig_header: str, db: Session) -> dict:
    """
    Verify and process a Stripe webhook event (spec §7, §13).
    Handled events: payment_intent.succeeded, payment_intent.payment_failed,
    charge.refunded, payout.paid.
    """
    stripe = _get_stripe()
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook secret not configured.",
        )

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    event_type: str = event["type"]
    data = event["data"]["object"]

    logger.info("Stripe webhook: type=%s id=%s", event_type, event["id"])

    if event_type == "payment_intent.succeeded":
        _handle_payment_intent_succeeded(data, db)
    elif event_type == "payment_intent.payment_failed":
        _handle_payment_intent_failed(data, db)
    elif event_type == "charge.refunded":
        logger.info("Stripe charge.refunded: %s", data.get("id"))
    elif event_type == "payout.paid":
        _handle_payout_paid(data, db)

    return {"received": True, "type": event_type}


def _handle_payment_intent_succeeded(data: dict, db: Session) -> None:
    user_id_str = data.get("metadata", {}).get("user_id")
    if not user_id_str:
        return
    amount = Decimal(str(data["amount"])) / 100  # cents → dollars
    user_id = uuid.UUID(user_id_str)
    payment_service.deposit_to_wallet(db, user_id, amount)
    logger.info("Stripe deposit confirmed: user=%s amount=%s", user_id, amount)


def _handle_payment_intent_failed(data: dict, db: Session) -> None:
    user_id_str = data.get("metadata", {}).get("user_id")
    if user_id_str:
        from app.services import fraud_service  # noqa: PLC0415
        fraud_service.record_failed_payment(uuid.UUID(user_id_str))
    logger.warning("Stripe PaymentIntent failed: %s", data.get("id"))


def _handle_payout_paid(data: dict, db: Session) -> None:
    """Mark WriterPayout as completed when Stripe confirms payout."""
    payout_id_str = data.get("metadata", {}).get("payout_id")
    if not payout_id_str:
        return
    from app.models.payment import WriterPayout  # noqa: PLC0415
    payout = db.query(WriterPayout).filter(
        WriterPayout.id == uuid.UUID(payout_id_str)
    ).first()
    if payout and payout.status == "processing":
        payout.status = "completed"
        payout.provider_reference = data.get("id")
        db.commit()
        logger.info("WriterPayout completed: id=%s", payout_id_str)


def save_payment_method(
    db: Session,
    user_id: uuid.UUID,
    payment_method_id: str,
) -> PaymentMethod:
    """
    Attach a Stripe PaymentMethod to the user and persist it.
    """
    stripe = _get_stripe()
    try:
        pm = stripe.PaymentMethod.retrieve(payment_method_id)
        card = pm.get("card", {})
        pm_obj = PaymentMethod(
            user_id=user_id,
            provider="stripe",
            provider_token=payment_method_id,
            brand=card.get("brand"),
            last4=card.get("last4"),
            expiry_month=card.get("exp_month"),
            expiry_year=card.get("exp_year"),
            is_default=False,
        )
        db.add(pm_obj)
        db.commit()
        db.refresh(pm_obj)
        return pm_obj
    except Exception as exc:
        logger.exception("save_payment_method failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
