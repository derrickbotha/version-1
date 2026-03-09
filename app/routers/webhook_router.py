"""
Webhook endpoints for Stripe and PayPal (spec §7, §8, §13).
These endpoints are public (no auth) but verified via provider signatures.
"""
import logging

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services import paypal_service, stripe_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/stripe", response_model=dict, summary="Stripe webhook receiver")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
) -> dict:
    payload = await request.body()
    result = stripe_service.handle_webhook(payload, stripe_signature or "", db)
    return {"status": "success", "data": result}


@router.post("/paypal", response_model=dict, summary="PayPal webhook receiver")
async def paypal_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    result = await paypal_service.handle_webhook(request, db)
    return {"status": "success", "data": result}
