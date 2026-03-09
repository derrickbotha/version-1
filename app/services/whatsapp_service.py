
import logging

import httpx
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_GRAPH_BASE = "https://graph.facebook.com/v18.0"


async def send_whatsapp_message(phone: str, text: str) -> bool:
    """
    Send a free-form text message via the WhatsApp Cloud API.

    Parameters
    ----------
    phone:
        Recipient phone number in E.164 format (e.g. ``+15551234567``).
    text:
        Message body.

    Returns
    -------
    bool
        ``True`` when the API responds with HTTP 200, ``False`` otherwise.
    """
    url = f"{_GRAPH_BASE}/{settings.whatsapp_phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            logger.info("WhatsApp message sent to %s", phone)
            return True
        logger.error(
            "WhatsApp API error: status=%s body=%s",
            response.status_code,
            response.text,
        )
        return False
    except httpx.HTTPError as exc:
        logger.error("WhatsApp request failed: %s", exc)
        return False


async def send_whatsapp_template(
    phone: str,
    template_name: str,
    params: list[str],
) -> bool:
    """
    Send a pre-approved WhatsApp template message.

    Parameters
    ----------
    phone:
        Recipient phone number in E.164 format.
    template_name:
        Name of the approved template (e.g. ``hello_world``).
    params:
        Ordered list of parameter strings that fill the template placeholders.

    Returns
    -------
    bool
        ``True`` when the API responds with HTTP 200, ``False`` otherwise.
    """
    url = f"{_GRAPH_BASE}/{settings.whatsapp_phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }

    components: list[dict] = []
    if params:
        components.append(
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": param} for param in params
                ],
            }
        )

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en_US"},
            "components": components,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            logger.info(
                "WhatsApp template '%s' sent to %s", template_name, phone
            )
            return True
        logger.error(
            "WhatsApp template API error: status=%s body=%s",
            response.status_code,
            response.text,
        )
        return False
    except httpx.HTTPError as exc:
        logger.error("WhatsApp template request failed: %s", exc)
        return False


def verify_webhook(mode: str, challenge: str, token: str) -> str:
    """
    Validate an incoming WhatsApp webhook verification request.

    WhatsApp sends a GET request with ``hub.mode``, ``hub.challenge``, and
    ``hub.verify_token`` query parameters.  This function verifies that
    *mode* is ``"subscribe"`` and *token* matches
    ``settings.whatsapp_verify_token``, then returns *challenge* so the
    caller can echo it back to WhatsApp.

    Raises:
        HTTPException 403 — if the mode or token is invalid.
    """
    if mode != "subscribe" or token != settings.whatsapp_verify_token:
        logger.warning(
            "WhatsApp webhook verification failed: mode=%s token_match=%s",
            mode,
            token == settings.whatsapp_verify_token,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook verification failed",
        )

    logger.info("WhatsApp webhook verified successfully")
    return challenge
