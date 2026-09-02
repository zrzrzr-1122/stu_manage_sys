from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from model.chat_model import ChatApiKey, ChatConversation, ChatMessage
from services.deepseek import decrypt_api_key, encrypt_api_key, mask_api_key


def get_api_key_row(db: Session, owner_type: str, owner_id: int) -> ChatApiKey | None:
    return (
        db.query(ChatApiKey)
        .filter(ChatApiKey.owner_type == owner_type, ChatApiKey.owner_id == owner_id)
        .first()
    )


def get_api_key_status(db: Session, owner_type: str, owner_id: int) -> dict:
    row = get_api_key_row(db, owner_type, owner_id)
    configured = bool(row and row.deepseek_api_key_enc)
    masked = None
    if configured and row:
        raw = decrypt_api_key(row.deepseek_api_key_enc)
        masked = mask_api_key(raw) if raw else None
    return {"configured": configured, "masked": masked}


def save_api_key(db: Session, owner_type: str, owner_id: int, api_key: str) -> dict:
    row = get_api_key_row(db, owner_type, owner_id)
    enc = encrypt_api_key(api_key)
    if not row:
        row = ChatApiKey(owner_type=owner_type, owner_id=owner_id, deepseek_api_key_enc=enc)
        db.add(row)
    else:
        row.deepseek_api_key_enc = enc
    db.commit()
    return get_api_key_status(db, owner_type, owner_id)


def delete_api_key(db: Session, owner_type: str, owner_id: int) -> None:
    row = get_api_key_row(db, owner_type, owner_id)
    if not row:
        return
    row.deepseek_api_key_enc = None
    db.commit()


def resolve_api_key(db: Session, owner_type: str, owner_id: int) -> str | None:
    row = get_api_key_row(db, owner_type, owner_id)
    if not row:
        return None
    return decrypt_api_key(row.deepseek_api_key_enc)


def list_conversations(db: Session, owner_type: str, owner_id: int) -> list[ChatConversation]:
    return (
        db.query(ChatConversation)
        .filter(
            ChatConversation.owner_type == owner_type,
            ChatConversation.owner_id == owner_id,
        )
        .order_by(ChatConversation.updated_at.desc())
        .all()
    )


def get_conversation(
    db: Session,
    conversation_id: int,
    owner_type: str,
    owner_id: int,
) -> ChatConversation | None:
    return (
        db.query(ChatConversation)
        .filter(
            ChatConversation.id == conversation_id,
            ChatConversation.owner_type == owner_type,
            ChatConversation.owner_id == owner_id,
        )
        .first()
    )


def create_conversation(
    db: Session,
    owner_type: str,
    owner_id: int,
    *,
    title: str = "新对话",
    model: str = "deepseek-chat",
) -> ChatConversation:
    conv = ChatConversation(
        owner_type=owner_type,
        owner_id=owner_id,
        title=title or "新对话",
        model=model,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def update_conversation(
    db: Session,
    conversation_id: int,
    owner_type: str,
    owner_id: int,
    *,
    title: str | None = None,
    model: str | None = None,
) -> ChatConversation | None:
    conv = get_conversation(db, conversation_id, owner_type, owner_id)
    if not conv:
        return None
    if title is not None:
        conv.title = title.strip() or "新对话"
    if model is not None:
        conv.model = model
    conv.updated_at = datetime.now()
    db.commit()
    db.refresh(conv)
    return conv


def delete_conversation(
    db: Session,
    conversation_id: int,
    owner_type: str,
    owner_id: int,
) -> bool:
    conv = get_conversation(db, conversation_id, owner_type, owner_id)
    if not conv:
        return False
    db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).delete()
    db.delete(conv)
    db.commit()
    return True


def list_messages(
    db: Session,
    conversation_id: int,
    owner_type: str,
    owner_id: int,
) -> list[ChatMessage]:
    if not get_conversation(db, conversation_id, owner_type, owner_id):
        return []
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


def auto_title(content: str, max_len: int = 30) -> str:
    text = " ".join(content.strip().split())
    if len(text) <= max_len:
        return text or "新对话"
    return text[:max_len] + "..."


def add_message(db: Session, conversation_id: int, role: str, content: str) -> ChatMessage:
    msg = ChatMessage(conversation_id=conversation_id, role=role, content=content)
    db.add(msg)
    conv = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if conv:
        if conv.title == "新对话" and role == "user":
            conv.title = auto_title(content)
        conv.updated_at = datetime.now()
    db.commit()
    db.refresh(msg)
    return msg
