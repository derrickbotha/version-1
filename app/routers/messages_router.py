
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.message_schema import (
    ConversationListResponse,
    ConversationResponse,
    MessageCreate,
    MessageListResponse,
    MessageResponse,
)
from app.services import messaging_service
from app.utils.jwt_handler import get_current_user

router = APIRouter(tags=["Messages"])


@router.get(
    "/conversations",
    response_model=dict,
    summary="List own conversations",
)
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    conversations = messaging_service.get_user_conversations(
        db=db,
        user_id=current_user.id,
    )
    response = ConversationListResponse(
        items=[ConversationResponse.model_validate(c) for c in conversations],
    )
    return {"status": "success", "data": response.model_dump()}


@router.get(
    "/conversations/{conversation_id}",
    response_model=dict,
    summary="Get conversation detail (participant only)",
)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    conversation = messaging_service.get_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    return {
        "status": "success",
        "data": ConversationResponse.model_validate(conversation).model_dump(),
    }


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=dict,
    summary="Paginated message list for a conversation (participant only)",
)
def get_messages(
    conversation_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    items, total = messaging_service.get_messages(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    response = MessageListResponse(
        items=[MessageResponse.model_validate(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
    )
    return {"status": "success", "data": response.model_dump()}


@router.post(
    "/messages",
    response_model=dict,
    status_code=201,
    summary="Send a message (participant only)",
)
def send_message(
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    message = messaging_service.send_message(
        db=db,
        sender_id=current_user.id,
        data=body,
    )
    return {
        "status": "success",
        "data": MessageResponse.model_validate(message).model_dump(),
    }
