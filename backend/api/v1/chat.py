"""AI 聊天 API：会话、消息、流式对话、个人 API Key。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from api.v1.chat_deps import ChatOwner, get_chat_owner
from api.v1.result import ok, to_dict
from dao import chat_dao
from database import get_db
from exceptions import biz_error, not_found
from jwt_auth.access import AccessContext, require_perms
from services.chat_models import AVAILABLE_MODELS, is_valid_model, normalize_model
from services.deepseek import ApiKeyError, DeepSeekError, stream_chat_completion, validate_deepseek_api_key

router = APIRouter(prefix="/chat", tags=["AI助手"])


class ChatMessageIn(BaseModel):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn] = Field(min_length=1)
    conversation_id: int | None = None
    model: str = "deepseek-chat"

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if not is_valid_model(value):
            raise ValueError("不支持的模型")
        return value


class CreateConversationBody(BaseModel):
    title: str = "新对话"
    model: str = "deepseek-chat"

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        return normalize_model(value)


class UpdateConversationBody(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    model: str | None = None

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not is_valid_model(value):
            raise ValueError("不支持的模型")
        return value


class SaveApiKeyBody(BaseModel):
    api_key: str = Field(min_length=10, max_length=256)


def _require_admin_chat(
    owner: ChatOwner = Depends(get_chat_owner),
    ctx: AccessContext = Depends(require_perms("chat:use")),
) -> ChatOwner:
    if owner.owner_type != "admin":
        raise biz_error("请使用后台账号访问")
    return owner


def _owner_for_admin(owner: ChatOwner = Depends(_require_admin_chat)) -> ChatOwner:
    return owner


def _owner_for_portal(owner: ChatOwner = Depends(get_chat_owner)) -> ChatOwner:
    if owner.owner_type != "student":
        raise biz_error("请使用学生账号访问")
    return owner


def _conv_out(row) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "model": row.model,
        "createdAt": to_dict(row).get("created_at") if hasattr(row, "created_at") else None,
        "updatedAt": to_dict(row).get("updated_at") if hasattr(row, "updated_at") else None,
        "created_at": row.created_at.isoformat(sep=" ", timespec="seconds") if row.created_at else None,
        "updated_at": row.updated_at.isoformat(sep=" ", timespec="seconds") if row.updated_at else None,
    }


def _msg_out(row) -> dict:
    return {
        "id": row.id,
        "role": row.role,
        "content": row.content,
        "created_at": row.created_at.isoformat(sep=" ", timespec="seconds") if row.created_at else None,
    }


# ---------- 管理端（需 chat:use） ----------
@router.get("/models")
def list_models(_owner: ChatOwner = Depends(_owner_for_admin)):
    return ok(AVAILABLE_MODELS)


@router.get("/api-key")
def get_api_key_status(
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_admin),
):
    return ok(chat_dao.get_api_key_status(db, owner.owner_type, owner.owner_id))


@router.put("/api-key")
async def save_api_key(
    body: SaveApiKeyBody,
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_admin),
):
    try:
        await validate_deepseek_api_key(body.api_key)
    except ApiKeyError as e:
        raise biz_error(str(e))
    data = chat_dao.save_api_key(db, owner.owner_type, owner.owner_id, body.api_key)
    return ok(data, "API Key 已保存（仅本人可用）")


@router.delete("/api-key")
def delete_api_key(
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_admin),
):
    chat_dao.delete_api_key(db, owner.owner_type, owner.owner_id)
    return ok(True, "已移除 API Key")


@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_admin),
):
    rows = chat_dao.list_conversations(db, owner.owner_type, owner.owner_id)
    return ok([_conv_out(r) for r in rows])


@router.post("/conversations")
def create_conversation(
    body: CreateConversationBody,
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_admin),
):
    row = chat_dao.create_conversation(
        db,
        owner.owner_type,
        owner.owner_id,
        title=body.title,
        model=body.model,
    )
    return ok(_conv_out(row), "创建成功")


@router.get("/conversations/{conversation_id}/messages")
def list_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_admin),
):
    conv = chat_dao.get_conversation(db, conversation_id, owner.owner_type, owner.owner_id)
    if not conv:
        raise not_found("会话不存在")
    rows = chat_dao.list_messages(db, conversation_id, owner.owner_type, owner.owner_id)
    return ok([_msg_out(r) for r in rows])


@router.patch("/conversations/{conversation_id}")
def update_conversation(
    conversation_id: int,
    body: UpdateConversationBody,
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_admin),
):
    if body.title is None and body.model is None:
        raise biz_error("请提供要更新的字段")
    row = chat_dao.update_conversation(
        db,
        conversation_id,
        owner.owner_type,
        owner.owner_id,
        title=body.title,
        model=body.model,
    )
    if not row:
        raise not_found("会话不存在")
    return ok(_conv_out(row), "更新成功")


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_admin),
):
    if not chat_dao.delete_conversation(db, conversation_id, owner.owner_type, owner.owner_id):
        raise not_found("会话不存在")
    return ok(True, "已删除")


@router.post("/completions")
async def chat_completions(
    body: ChatRequest,
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_admin),
):
    return await _stream_chat(db, owner, body)


# ---------- 学生门户（登录即可） ----------
portal_router = APIRouter(prefix="/portal/chat", tags=["AI助手-学生门户"])


@portal_router.get("/models")
def portal_list_models(_owner: ChatOwner = Depends(_owner_for_portal)):
    return ok(AVAILABLE_MODELS)


@portal_router.get("/api-key")
def portal_api_key_status(
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_portal),
):
    return ok(chat_dao.get_api_key_status(db, owner.owner_type, owner.owner_id))


@portal_router.put("/api-key")
async def portal_save_api_key(
    body: SaveApiKeyBody,
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_portal),
):
    try:
        await validate_deepseek_api_key(body.api_key)
    except ApiKeyError as e:
        raise biz_error(str(e))
    data = chat_dao.save_api_key(db, owner.owner_type, owner.owner_id, body.api_key)
    return ok(data, "API Key 已保存（仅本人可用）")


@portal_router.delete("/api-key")
def portal_delete_api_key(
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_portal),
):
    chat_dao.delete_api_key(db, owner.owner_type, owner.owner_id)
    return ok(True, "已移除 API Key")


@portal_router.get("/conversations")
def portal_list_conversations(
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_portal),
):
    rows = chat_dao.list_conversations(db, owner.owner_type, owner.owner_id)
    return ok([_conv_out(r) for r in rows])


@portal_router.post("/conversations")
def portal_create_conversation(
    body: CreateConversationBody,
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_portal),
):
    row = chat_dao.create_conversation(
        db,
        owner.owner_type,
        owner.owner_id,
        title=body.title,
        model=body.model,
    )
    return ok(_conv_out(row), "创建成功")


@portal_router.get("/conversations/{conversation_id}/messages")
def portal_list_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_portal),
):
    conv = chat_dao.get_conversation(db, conversation_id, owner.owner_type, owner.owner_id)
    if not conv:
        raise not_found("会话不存在")
    rows = chat_dao.list_messages(db, conversation_id, owner.owner_type, owner.owner_id)
    return ok([_msg_out(r) for r in rows])


@portal_router.patch("/conversations/{conversation_id}")
def portal_update_conversation(
    conversation_id: int,
    body: UpdateConversationBody,
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_portal),
):
    if body.title is None and body.model is None:
        raise biz_error("请提供要更新的字段")
    row = chat_dao.update_conversation(
        db,
        conversation_id,
        owner.owner_type,
        owner.owner_id,
        title=body.title,
        model=body.model,
    )
    if not row:
        raise not_found("会话不存在")
    return ok(_conv_out(row), "更新成功")


@portal_router.delete("/conversations/{conversation_id}")
def portal_delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_portal),
):
    if not chat_dao.delete_conversation(db, conversation_id, owner.owner_type, owner.owner_id):
        raise not_found("会话不存在")
    return ok(True, "已删除")


@portal_router.post("/completions")
async def portal_chat_completions(
    body: ChatRequest,
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_portal),
):
    return await _stream_chat(db, owner, body)


async def _stream_chat(db: Session, owner: ChatOwner, body: ChatRequest):
    messages = [m.model_dump() for m in body.messages]
    conversation_id = body.conversation_id
    model = normalize_model(body.model)
    api_key = chat_dao.resolve_api_key(db, owner.owner_type, owner.owner_id)

    if conversation_id is not None:
        conv = chat_dao.get_conversation(db, conversation_id, owner.owner_type, owner.owner_id)
        if not conv:
            conversation_id = None
        elif conv.model != model:
            chat_dao.update_conversation(
                db, conversation_id, owner.owner_type, owner.owner_id, model=model
            )

    last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
    if conversation_id and last_user:
        chat_dao.add_message(db, conversation_id, "user", last_user["content"])

    assistant_content: list[str] = []

    async def event_generator():
        if not api_key:
            payload = json.dumps(
                {"error": "请先在设置中配置自己的 DeepSeek API Key"},
                ensure_ascii=False,
            )
            yield f"data: {payload}\n\n"
            return
        try:
            async for token in stream_chat_completion(messages, api_key=api_key, model=model):
                assistant_content.append(token)
                yield f"data: {json.dumps({'content': token}, ensure_ascii=False)}\n\n"
            if conversation_id and assistant_content:
                chat_dao.add_message(db, conversation_id, "assistant", "".join(assistant_content))
            yield "data: [DONE]\n\n"
        except DeepSeekError as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
