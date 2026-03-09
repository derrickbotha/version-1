
import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.message import Conversation, Message, Notification
from app.models.user import User

logger = logging.getLogger(__name__)


def _extract_inbound(payload: dict[str, Any]) -> dict[str, Any] | None:
    """
    Navigate the WhatsApp webhook payload envelope and return a normalised
    dict with keys ``from_number``, ``message_id``, ``message_text``, and
    ``timestamp``.

    Returns ``None`` if the payload does not contain a text message (e.g. a
    delivery-status notification).
    """
    try:
        entry = payload["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
        messages = value.get("messages")
        if not messages:
            return None
        msg = messages[0]
        if msg.get("type") != "text":
            return None
        return {
            "from_number": msg["from"],
            "message_id": msg["id"],
            "message_text": msg["text"]["body"],
            "timestamp": msg.get("timestamp"),
        }
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("Could not parse WhatsApp payload: %s", exc)
        return None


def process_inbound_message(db: Session, payload: dict[str, Any]) -> None:
    """
    Handle an inbound WhatsApp message received via the webhook.

    Steps
    -----
    1. Extract message fields from the raw webhook payload.
    2. Find the platform user whose ``whatsapp_number`` matches the sender.
    3. Find the most recent active conversation for that user.
    4. Persist a :class:`~app.models.message.Message` with
       ``channel='whatsapp'``.
    5. Create a :class:`~app.models.message.Notification` for the other
       participant in the conversation.

    If any prerequisite is not met the function logs a warning and returns
    without raising, because WhatsApp requires a ``200`` response within
    a few seconds regardless of processing outcome.
    """
    extracted = _extract_inbound(payload)
    if extracted is None:
        logger.debug("Inbound payload contained no actionable message; skipping")
        return

    from_number: str = extracted["from_number"]
    message_id: str = extracted["message_id"]
    message_text: str = extracted["message_text"]
    timestamp: str | None = extracted["timestamp"]

    # --- 1. Resolve sender ---
    sender: User | None = (
        db.query(User).filter(User.whatsapp_number == from_number).first()
    )
    if sender is None:
        logger.warning(
            "Inbound WhatsApp from unknown number %s (message_id=%s); ignoring",
            from_number,
            message_id,
        )
        return

    sender_id: uuid.UUID = sender.id

    # --- 2. Find the most recent conversation for this user ---
    conversation: Conversation | None = (
        db.query(Conversation)
        .filter(
            (Conversation.student_id == sender_id)
            | (Conversation.researcher_id == sender_id)
        )
        .order_by(Conversation.created_at.desc())
        .first()
    )
    if conversation is None:
        logger.warning(
            "No active conversation found for user %s (WhatsApp %s); ignoring",
            sender_id,
            from_number,
        )
        return

    # --- 3. Persist the message ---
    message = Message(
        conversation_id=conversation.id,
        sender_id=sender_id,
        message_type="text",
        content=message_text,
        channel="whatsapp",
        whatsapp_message_id=message_id,
    )
    db.add(message)

    # --- 4. Notify the other participant ---
    other_user_id: uuid.UUID = (
        conversation.researcher_id
        if conversation.student_id == sender_id
        else conversation.student_id
    )

    notification = Notification(
        user_id=other_user_id,
        title="New WhatsApp message",
        message=(
            f"You have a new message from {sender.first_name} {sender.last_name} "
            f"via WhatsApp in conversation {conversation.id}."
        ),
        notification_type="whatsapp_message",
    )
    db.add(notification)

    db.commit()

    logger.info(
        "Inbound WhatsApp processed: message=%s conversation=%s sender=%s",
        message.id,
        conversation.id,
        sender_id,
    )
