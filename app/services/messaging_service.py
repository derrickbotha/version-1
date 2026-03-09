
import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.message import Conversation, Message
from app.schemas.message_schema import MessageCreate
from app.utils.security import sanitize_input

logger = logging.getLogger(__name__)


def get_user_conversations(
    db: Session,
    user_id: uuid.UUID,
) -> list[Conversation]:
    """
    Return all conversations where *user_id* is either the student or the
    researcher, ordered newest-first.
    """
    conversations: list[Conversation] = (
        db.query(Conversation)
        .filter(
            (Conversation.student_id == user_id)
            | (Conversation.researcher_id == user_id)
        )
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return conversations


def get_conversation(
    db: Session,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Conversation:
    """
    Return the conversation identified by *conversation_id* if *user_id* is a
    participant (student or researcher).

    Raises:
        HTTPException 404 — conversation not found.
        HTTPException 403 — user is not a participant.
    """
    conversation: Conversation | None = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id)
        .first()
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    if conversation.student_id != user_id and conversation.researcher_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this conversation",
        )

    return conversation


def send_message(
    db: Session,
    sender_id: uuid.UUID,
    data: MessageCreate,
) -> Message:
    """
    Send a platform message from *sender_id* in the conversation referenced
    by *data.conversation_id*.

    The message content is sanitized before persistence.

    Raises:
        HTTPException 404 — conversation not found.
        HTTPException 403 — sender is not a participant.
    """
    conversation = get_conversation(db, data.conversation_id, sender_id)

    clean_content = sanitize_input(data.content)

    message = Message(
        conversation_id=conversation.id,
        sender_id=sender_id,
        message_type="text",
        content=clean_content,
        channel="platform",
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    logger.info(
        "Message sent: id=%s conversation=%s sender=%s channel=platform",
        message.id,
        conversation.id,
        sender_id,
    )
    return message


def get_messages(
    db: Session,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int,
    page_size: int,
) -> tuple[list[Message], int]:
    """
    Return a paginated list of messages in *conversation_id* ordered by
    created_at ASC, and the total count.

    Raises:
        HTTPException 404/403 — forwarded from :func:`get_conversation`.
    """
    get_conversation(db, conversation_id, user_id)

    base_query = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    total: int = base_query.count()
    items: list[Message] = base_query.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def send_system_message(
    db: Session,
    conversation_id: uuid.UUID,
    content: str,
) -> Message:
    """
    Persist a system-generated message in *conversation_id*.

    System messages have ``message_type='system'`` and ``sender_id=None``.
    The conversation must already exist; this function does NOT verify
    participant access — callers are trusted internal services.

    Raises:
        HTTPException 404 — conversation not found.
    """
    conversation: Conversation | None = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    message = Message(
        conversation_id=conversation_id,
        sender_id=None,
        message_type="system",
        content=content,
        channel="platform",
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    logger.info(
        "System message sent: id=%s conversation=%s",
        message.id,
        conversation_id,
    )
    return message


def mark_messages_read(
    db: Session,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """
    Record that *user_id* has read messages up to now in *conversation_id*.

    The Conversation model does not yet have a persistent last_seen_at column,
    so this function logs the event for future use when the column is added.

    Raises:
        HTTPException 404/403 — forwarded from :func:`get_conversation`.
    """
    conversation = get_conversation(db, conversation_id, user_id)
    logger.info(
        "Messages marked as read: conversation=%s user=%s",
        conversation.id,
        user_id,
    )
