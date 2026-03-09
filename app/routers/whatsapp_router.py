
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.whatsapp_service import verify_webhook
from app.workers.whatsapp_worker import process_inbound_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


@router.get(
    "/webhook",
    response_model=None,
    summary="WhatsApp webhook verification",
)
def whatsapp_webhook_verify(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
) -> Response:
    """
    Respond to WhatsApp's webhook verification handshake.

    WhatsApp sends a GET request with the three ``hub.*`` query parameters.
    This endpoint validates them via :func:`~app.services.whatsapp_service.verify_webhook`
    and echoes back the challenge string as plain text so that WhatsApp can
    confirm the endpoint is reachable and owned by the expected application.
    """
    challenge = verify_webhook(
        mode=hub_mode,
        challenge=hub_challenge,
        token=hub_verify_token,
    )
    return Response(content=challenge, media_type="text/plain")


@router.post(
    "/webhook",
    response_model=dict,
    summary="Receive inbound WhatsApp messages",
)
async def whatsapp_webhook_receive(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    """
    Receive and acknowledge inbound WhatsApp messages.

    WhatsApp requires an HTTP 200 response within a few seconds or it will
    retry.  The actual payload processing is therefore offloaded to a
    :class:`fastapi.BackgroundTasks` task so the acknowledgement is returned
    immediately.

    No authentication is performed here — the endpoint is public (as required
    by WhatsApp).  The integrity of inbound requests should instead be
    verified via the ``X-Hub-Signature-256`` header in production.
    """
    payload: Any = await request.json()

    if not isinstance(payload, dict):
        logger.warning("WhatsApp webhook received non-dict payload; ignoring")
        return {"status": "success", "data": {}}

    background_tasks.add_task(process_inbound_message, db, payload)

    logger.debug("WhatsApp webhook payload queued for background processing")
    return {"status": "success", "data": {}}
