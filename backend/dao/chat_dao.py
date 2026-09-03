from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from model.chat_model import ChatApiKey, ChatConversation, ChatLlmLog, ChatMessage, ChatUserMemory
from services.deepseek import decrypt_api_key, encrypt_api_key, mask_api_key

DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.7
REQUEST_PREVIEW_MAX = 8000
MEMORY_CONTENT_MAX = 4000
MAX_PINNED_CONVERSATIONS = 5
PINNED_MSGS_PER_CONV = 12
PINNED_MSG_CHAR_MAX = 400
PINNED_MEMORY_CHAR_MAX = 4000


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
    system_prompt: str | None = None,
    max_tokens: int | None = DEFAULT_MAX_TOKENS,
    temperature: float | None = DEFAULT_TEMPERATURE,
    stream_enabled: int = 1,
    thinking_enabled: int = 1,
    markdown_enabled: int = 1,
) -> ChatConversation:
    conv = ChatConversation(
        owner_type=owner_type,
        owner_id=owner_id,
        title=title or "新对话",
        model=model,
        system_prompt=system_prompt,
        max_tokens=max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS,
        temperature=temperature if temperature is not None else DEFAULT_TEMPERATURE,
        stream_enabled=1 if stream_enabled else 0,
        thinking_enabled=1 if thinking_enabled else 0,
        markdown_enabled=1 if markdown_enabled else 0,
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
    system_prompt: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    stream_enabled: int | None = None,
    thinking_enabled: int | None = None,
    markdown_enabled: int | None = None,
    memory_pinned: int | None = None,
    clear_system_prompt: bool = False,
) -> ChatConversation | None:
    conv = get_conversation(db, conversation_id, owner_type, owner_id)
    if not conv:
        return None
    if title is not None:
        conv.title = title.strip() or "新对话"
    if model is not None:
        conv.model = model
    if clear_system_prompt:
        conv.system_prompt = None
    elif system_prompt is not None:
        conv.system_prompt = system_prompt
    if max_tokens is not None:
        conv.max_tokens = max_tokens
    if temperature is not None:
        conv.temperature = temperature
    if stream_enabled is not None:
        conv.stream_enabled = 1 if stream_enabled else 0
    if thinking_enabled is not None:
        conv.thinking_enabled = 1 if thinking_enabled else 0
    if markdown_enabled is not None:
        conv.markdown_enabled = 1 if markdown_enabled else 0
    if memory_pinned is not None:
        want_pin = 1 if memory_pinned else 0
        if want_pin and not conv.memory_pinned:
            pinned_count = (
                db.query(ChatConversation)
                .filter(
                    ChatConversation.owner_type == owner_type,
                    ChatConversation.owner_id == owner_id,
                    ChatConversation.memory_pinned == 1,
                )
                .count()
            )
            if pinned_count >= MAX_PINNED_CONVERSATIONS:
                raise ValueError(f"最多钉选 {MAX_PINNED_CONVERSATIONS} 个会话作为记忆")
        conv.memory_pinned = want_pin
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
    db.query(ChatLlmLog).filter(ChatLlmLog.conversation_id == conversation_id).delete()
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


def add_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
    *,
    thinking_content: str | None = None,
    data_queries: list | dict | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
) -> ChatMessage:
    dq_json = None
    if data_queries is not None:
        dq_json = json.dumps(data_queries, ensure_ascii=False, default=str)
    msg = ChatMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        thinking_content=thinking_content,
        data_queries_json=dq_json,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    db.add(msg)
    conv = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if conv:
        if conv.title == "新对话" and role == "user":
            conv.title = auto_title(content)
        conv.updated_at = datetime.now()
    db.commit()
    db.refresh(msg)
    return msg


def _truncate_preview(messages: list[dict]) -> str:
    raw = json.dumps(messages, ensure_ascii=False)
    if len(raw) <= REQUEST_PREVIEW_MAX:
        return raw
    return raw[:REQUEST_PREVIEW_MAX] + "…"


def add_llm_log(
    db: Session,
    *,
    owner_type: str,
    owner_id: int,
    conversation_id: int | None,
    message_id: int | None,
    model: str,
    stream: bool,
    temperature: float | None,
    max_tokens: int | None,
    messages: list[dict],
    status: str,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    latency_ms: int | None = None,
    error_message: str | None = None,
) -> ChatLlmLog:
    row = ChatLlmLog(
        owner_type=owner_type,
        owner_id=owner_id,
        conversation_id=conversation_id,
        message_id=message_id,
        model=model,
        stream=1 if stream else 0,
        temperature=temperature,
        max_tokens=max_tokens,
        request_preview=_truncate_preview(messages),
        status=status,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        error_message=(error_message or "")[:2000] or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_llm_logs(
    db: Session,
    owner_type: str,
    owner_id: int,
    *,
    conversation_id: int | None = None,
    page_num: int = 1,
    page_size: int = 20,
) -> tuple[list[ChatLlmLog], int]:
    q = db.query(ChatLlmLog).filter(
        ChatLlmLog.owner_type == owner_type,
        ChatLlmLog.owner_id == owner_id,
    )
    if conversation_id is not None:
        q = q.filter(ChatLlmLog.conversation_id == conversation_id)
    total = q.count()
    rows = (
        q.order_by(ChatLlmLog.created_at.desc())
        .offset(max(page_num - 1, 0) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def get_memory(db: Session, owner_type: str, owner_id: int) -> ChatUserMemory | None:
    return (
        db.query(ChatUserMemory)
        .filter(
            ChatUserMemory.owner_type == owner_type,
            ChatUserMemory.owner_id == owner_id,
        )
        .first()
    )


def get_memory_content(db: Session, owner_type: str, owner_id: int) -> str:
    row = get_memory(db, owner_type, owner_id)
    return (row.content or "") if row else ""


def upsert_memory(
    db: Session,
    owner_type: str,
    owner_id: int,
    content: str | None,
) -> ChatUserMemory:
    text = (content or "").strip()
    if len(text) > MEMORY_CONTENT_MAX:
        text = text[:MEMORY_CONTENT_MAX]
    row = get_memory(db, owner_type, owner_id)
    now = datetime.now()
    if not row:
        row = ChatUserMemory(
            owner_type=owner_type,
            owner_id=owner_id,
            content=text or None,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.content = text or None
        row.updated_at = now
    db.commit()
    db.refresh(row)
    return row


def list_pinned_conversations(
    db: Session,
    owner_type: str,
    owner_id: int,
) -> list[ChatConversation]:
    return (
        db.query(ChatConversation)
        .filter(
            ChatConversation.owner_type == owner_type,
            ChatConversation.owner_id == owner_id,
            ChatConversation.memory_pinned == 1,
        )
        .order_by(ChatConversation.updated_at.desc())
        .all()
    )


def _clip_msg(content: str) -> str:
    text = " ".join((content or "").strip().split())
    if len(text) <= PINNED_MSG_CHAR_MAX:
        return text
    return text[:PINNED_MSG_CHAR_MAX] + "…"


def build_pinned_memory_text(
    db: Session,
    owner_type: str,
    owner_id: int,
    *,
    exclude_conversation_id: int | None = None,
) -> str:
    """把钉选会话的最近对话拼成跨会话记忆文本。"""
    pinned = list_pinned_conversations(db, owner_type, owner_id)
    blocks: list[str] = []
    used = 0
    for conv in pinned:
        if exclude_conversation_id is not None and conv.id == exclude_conversation_id:
            continue
        rows = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.conversation_id == conv.id,
                ChatMessage.role.in_(("user", "assistant")),
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(PINNED_MSGS_PER_CONV)
            .all()
        )
        if not rows:
            continue
        rows = list(reversed(rows))
        lines = [f"### 会话#{conv.id} {conv.title}"]
        for m in rows:
            role = "用户" if m.role == "user" else "助手"
            lines.append(f"{role}: {_clip_msg(m.content)}")
        block = "\n".join(lines)
        if used + len(block) + 2 > PINNED_MEMORY_CHAR_MAX:
            remain = PINNED_MEMORY_CHAR_MAX - used - 2
            if remain > 80:
                blocks.append(block[:remain] + "…")
            break
        blocks.append(block)
        used += len(block) + 2
    return "\n\n".join(blocks).strip()
