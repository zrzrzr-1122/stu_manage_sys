"""AI 聊天 API：会话、消息、流式/非流式对话、个人 API Key、调用日志。"""
from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from api.v1.chat_deps import ChatOwner, get_chat_owner
from api.v1.result import ok, to_dict
from dao import chat_dao
from database import Session as DbSession, get_db
from exceptions import biz_error, not_found
from jwt_auth.access import AccessContext, require_perms
from services.chat_models import AVAILABLE_MODELS, is_valid_model, normalize_model
from services.chat_tools import run_tool_loop, tools_enabled_for_model
from services.deepseek import (
    ApiKeyError,
    DeepSeekError,
    chat_completion,
    stream_chat_completion,
    validate_deepseek_api_key,
)

router = APIRouter(prefix="/chat", tags=["AI助手"])

SYSTEM_PROMPT_MAX = 4000
MERGED_SYSTEM_MAX = 6000
MEMORY_PREFIX = (
    "以下内容为跨会话记忆与用户档案，请在回答时参考；"
    "不要主动向用户复述全文，除非对方明确要求。"
)


class ChatMessageIn(BaseModel):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn] = Field(min_length=1)
    conversation_id: int | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=8192)
    system_prompt: str | None = Field(default=None, max_length=SYSTEM_PROMPT_MAX)
    stream: bool | None = None
    thinking_enabled: bool | None = None

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not is_valid_model(value):
            raise ValueError("不支持的模型")
        return value


class CreateConversationBody(BaseModel):
    title: str = "新对话"
    model: str = "deepseek-chat"
    system_prompt: str | None = Field(default=None, max_length=SYSTEM_PROMPT_MAX)
    max_tokens: int | None = Field(default=2048, ge=1, le=8192)
    temperature: float | None = Field(default=0.7, ge=0, le=2)
    stream_enabled: bool = True
    thinking_enabled: bool = True
    markdown_enabled: bool = True

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        return normalize_model(value)


class UpdateConversationBody(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    model: str | None = None
    system_prompt: str | None = Field(default=None, max_length=SYSTEM_PROMPT_MAX)
    clear_system_prompt: bool = False
    max_tokens: int | None = Field(default=None, ge=1, le=8192)
    temperature: float | None = Field(default=None, ge=0, le=2)
    stream_enabled: bool | None = None
    thinking_enabled: bool | None = None
    markdown_enabled: bool | None = None
    memory_pinned: bool | None = None

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
        "system_prompt": row.system_prompt,
        "max_tokens": row.max_tokens,
        "temperature": row.temperature,
        "stream_enabled": bool(row.stream_enabled),
        "thinking_enabled": bool(row.thinking_enabled),
        "markdown_enabled": bool(row.markdown_enabled),
        "memory_pinned": bool(getattr(row, "memory_pinned", 0)),
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
        "thinking_content": row.thinking_content,
        "prompt_tokens": row.prompt_tokens,
        "completion_tokens": row.completion_tokens,
        "total_tokens": row.total_tokens,
        "created_at": row.created_at.isoformat(sep=" ", timespec="seconds") if row.created_at else None,
    }


def _log_out(row) -> dict:
    return {
        "id": row.id,
        "conversation_id": row.conversation_id,
        "message_id": row.message_id,
        "model": row.model,
        "stream": bool(row.stream),
        "temperature": row.temperature,
        "max_tokens": row.max_tokens,
        "request_preview": row.request_preview,
        "status": row.status,
        "prompt_tokens": row.prompt_tokens,
        "completion_tokens": row.completion_tokens,
        "total_tokens": row.total_tokens,
        "latency_ms": row.latency_ms,
        "error_message": row.error_message,
        "created_at": row.created_at.isoformat(sep=" ", timespec="seconds") if row.created_at else None,
    }


def _inject_system(messages: list[dict], system_prompt: str | None) -> list[dict]:
    if not system_prompt or not system_prompt.strip():
        return messages
    if messages and messages[0].get("role") == "system":
        # 已有 system 时，将跨会话记忆合并进首条，避免被前端 system 覆盖掉记忆
        merged = f"{system_prompt.strip()}\n\n{messages[0].get('content') or ''}".strip()
        if len(merged) > MERGED_SYSTEM_MAX:
            merged = merged[:MERGED_SYSTEM_MAX]
        return [{"role": "system", "content": merged}, *messages[1:]]
    return [{"role": "system", "content": system_prompt.strip()}, *messages]


def _student_profile_block(db: Session, owner_id: int) -> str:
    from model.student_model import Student

    stu = (
        db.query(Student)
        .filter(Student.stu_id == owner_id, Student.is_delete == 0)
        .first()
    )
    if not stu:
        return ""
    parts = [
        f"学号: {stu.stu_id}",
        f"姓名: {stu.stu_name}" if stu.stu_name else None,
        f"班级ID: {stu.class_id}" if stu.class_id is not None else None,
        f"专业: {stu.major}" if stu.major else None,
        f"学历: {stu.education}" if stu.education else None,
        f"年龄: {stu.age}" if stu.age is not None else None,
        f"性别: {stu.sex}" if stu.sex else None,
    ]
    lines = [p for p in parts if p]
    if not lines:
        return ""
    return "【学生档案】\n" + "\n".join(lines)


def build_merged_system(
    db: Session,
    owner: ChatOwner,
    session_system_prompt: str | None,
    *,
    exclude_conversation_id: int | None = None,
) -> str | None:
    """合并前缀 + 学生档案 + 钉选会话记忆 + 会话 system_prompt。"""
    sections: list[str] = []
    memory = chat_dao.build_pinned_memory_text(
        db,
        owner.owner_type,
        owner.owner_id,
        exclude_conversation_id=exclude_conversation_id,
    )
    profile = ""
    if owner.owner_type == "student":
        profile = _student_profile_block(db, owner.owner_id).strip()

    has_cross = bool(memory or profile)
    if has_cross:
        sections.append(MEMORY_PREFIX)
    if profile:
        sections.append(profile)
    if memory:
        sections.append("【钉选会话记忆】\n" + memory)
    if session_system_prompt and session_system_prompt.strip():
        sections.append("【本会话指令】\n" + session_system_prompt.strip())

    if not sections:
        return None
    merged = "\n\n".join(sections)
    if len(merged) > MERGED_SYSTEM_MAX:
        merged = merged[:MERGED_SYSTEM_MAX]
    return merged


def _merge_settings(conv, body: ChatRequest) -> dict[str, Any]:
    model = normalize_model(body.model or (conv.model if conv else None))
    temperature = body.temperature
    if temperature is None and conv is not None:
        temperature = conv.temperature
    if temperature is None:
        temperature = chat_dao.DEFAULT_TEMPERATURE

    max_tokens = body.max_tokens
    if max_tokens is None and conv is not None:
        max_tokens = conv.max_tokens
    if max_tokens is None:
        max_tokens = chat_dao.DEFAULT_MAX_TOKENS

    system_prompt = body.system_prompt
    if system_prompt is None and conv is not None:
        system_prompt = conv.system_prompt

    stream = body.stream
    if stream is None:
        stream = bool(conv.stream_enabled) if conv is not None else True

    thinking_enabled = body.thinking_enabled
    if thinking_enabled is None:
        thinking_enabled = bool(conv.thinking_enabled) if conv is not None else True

    return {
        "model": model,
        "temperature": float(temperature) if temperature is not None else None,
        "max_tokens": int(max_tokens) if max_tokens is not None else None,
        "system_prompt": system_prompt,
        "stream": bool(stream),
        "thinking_enabled": bool(thinking_enabled),
    }


def _persist_assistant_and_log(
    *,
    owner_type: str,
    owner_id: int,
    conversation_id: int | None,
    model: str,
    stream: bool,
    temperature: float | None,
    max_tokens: int | None,
    messages: list[dict],
    content: str,
    thinking: str,
    thinking_enabled: bool,
    usage: dict,
    latency_ms: int,
    status: str = "ok",
    error_message: str | None = None,
) -> int | None:
    db2 = DbSession()
    message_id = None
    try:
        if conversation_id and status == "ok" and content:
            msg = chat_dao.add_message(
                db2,
                conversation_id,
                "assistant",
                content,
                thinking_content=(thinking if thinking_enabled and thinking else None),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
            )
            message_id = msg.id
        chat_dao.add_llm_log(
            db2,
            owner_type=owner_type,
            owner_id=owner_id,
            conversation_id=conversation_id,
            message_id=message_id,
            model=model,
            stream=stream,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,
            status=status,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            latency_ms=latency_ms,
            error_message=error_message,
        )
        return message_id
    except Exception:
        db2.rollback()
        raise
    finally:
        db2.close()


async def _run_chat(db: Session, owner: ChatOwner, body: ChatRequest):
    messages = [m.model_dump() for m in body.messages]
    conversation_id = body.conversation_id
    owner_type = owner.owner_type
    owner_id = owner.owner_id
    api_key = chat_dao.resolve_api_key(db, owner_type, owner_id)

    conv = None
    if conversation_id is not None:
        conv = chat_dao.get_conversation(db, conversation_id, owner_type, owner_id)
        if not conv:
            conversation_id = None

    settings = _merge_settings(conv, body)
    model = settings["model"]
    temperature = settings["temperature"]
    max_tokens = settings["max_tokens"]
    system_prompt = settings["system_prompt"]
    use_stream = settings["stream"]
    thinking_enabled = settings["thinking_enabled"]

    if conversation_id and conv:
        patch: dict[str, Any] = {}
        if body.model and conv.model != model:
            patch["model"] = model
        if body.temperature is not None:
            patch["temperature"] = temperature
        if body.max_tokens is not None:
            patch["max_tokens"] = max_tokens
        if body.system_prompt is not None:
            patch["system_prompt"] = system_prompt
        if body.stream is not None:
            patch["stream_enabled"] = 1 if use_stream else 0
        if body.thinking_enabled is not None:
            patch["thinking_enabled"] = 1 if thinking_enabled else 0
        if patch:
            chat_dao.update_conversation(
                db, conversation_id, owner_type, owner_id, **patch
            )

    merged_system = build_merged_system(
        db,
        owner,
        system_prompt,
        exclude_conversation_id=conversation_id,
    )
    outbound = _inject_system(messages, merged_system)

    last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
    if conversation_id and last_user:
        chat_dao.add_message(db, conversation_id, "user", last_user["content"])

    persist_conversation_id = conversation_id
    try:
        db.close()
    except Exception:
        pass

    if not api_key:
        err = "请先在设置中配置自己的 DeepSeek API Key"
        if use_stream:
            async def _err_gen():
                yield f"data: {json.dumps({'type': 'error', 'error': err}, ensure_ascii=False)}\n\n"

            return StreamingResponse(
                _err_gen(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
            )
        return JSONResponse(
            content={"code": "A0400", "data": None, "msg": err},
            status_code=200,
        )

    if not use_stream:
        started = time.perf_counter()
        try:
            if tools_enabled_for_model(model):
                result = await run_tool_loop(
                    outbound,
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            else:
                result = await chat_completion(
                    outbound,
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                result = {
                    "content": result.get("content") or "",
                    "thinking": result.get("thinking") or "",
                    "usage": {
                        "prompt_tokens": result.get("prompt_tokens"),
                        "completion_tokens": result.get("completion_tokens"),
                        "total_tokens": result.get("total_tokens"),
                    },
                }
            latency_ms = int((time.perf_counter() - started) * 1000)
            usage = result.get("usage") or {}
            thinking = result.get("thinking") or ""
            content = result.get("content") or ""
            message_id = _persist_assistant_and_log(
                owner_type=owner_type,
                owner_id=owner_id,
                conversation_id=persist_conversation_id,
                model=model,
                stream=False,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=outbound,
                content=content,
                thinking=thinking,
                thinking_enabled=thinking_enabled,
                usage=usage,
                latency_ms=latency_ms,
            )
            return ok(
                {
                    "content": content,
                    "thinking": thinking if thinking_enabled else "",
                    "usage": usage,
                    "message_id": message_id,
                    "model": model,
                }
            )
        except DeepSeekError as e:
            latency_ms = int((time.perf_counter() - started) * 1000)
            try:
                _persist_assistant_and_log(
                    owner_type=owner_type,
                    owner_id=owner_id,
                    conversation_id=persist_conversation_id,
                    model=model,
                    stream=False,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=outbound,
                    content="",
                    thinking="",
                    thinking_enabled=thinking_enabled,
                    usage={},
                    latency_ms=latency_ms,
                    status="error",
                    error_message=str(e),
                )
            except Exception:
                pass
            raise biz_error(str(e))

    async def event_generator():
        assistant_parts: list[str] = []
        thinking_parts: list[str] = []
        usage: dict[str, Any] = {}
        started = time.perf_counter()
        try:
            # deepseek-chat：先非流式跑 tool loop，再把最终正文按 chunk 推给前端
            if tools_enabled_for_model(model):
                result = await run_tool_loop(
                    outbound,
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = result.get("content") or ""
                thinking = result.get("thinking") or ""
                usage = result.get("usage") or {}
                if thinking_enabled and thinking:
                    thinking_parts.append(thinking)
                    yield f"data: {json.dumps({'type': 'thinking', 'content': thinking}, ensure_ascii=False)}\n\n"
                # 分块推送，保持流式体验
                chunk_size = 24
                for i in range(0, len(content), chunk_size):
                    part = content[i : i + chunk_size]
                    assistant_parts.append(part)
                    yield f"data: {json.dumps({'type': 'content', 'content': part}, ensure_ascii=False)}\n\n"
                if usage:
                    yield f"data: {json.dumps({'type': 'usage', **usage}, ensure_ascii=False)}\n\n"
            else:
                async for event in stream_chat_completion(
                    outbound,
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    etype = event.get("type")
                    if etype == "thinking":
                        text = event.get("content") or ""
                        thinking_parts.append(text)
                        if thinking_enabled:
                            yield f"data: {json.dumps({'type': 'thinking', 'content': text}, ensure_ascii=False)}\n\n"
                    elif etype == "content":
                        text = event.get("content") or ""
                        assistant_parts.append(text)
                        yield f"data: {json.dumps({'type': 'content', 'content': text}, ensure_ascii=False)}\n\n"
                    elif etype == "usage":
                        usage = {
                            "prompt_tokens": event.get("prompt_tokens"),
                            "completion_tokens": event.get("completion_tokens"),
                            "total_tokens": event.get("total_tokens"),
                        }
                        yield f"data: {json.dumps({'type': 'usage', **usage}, ensure_ascii=False)}\n\n"

            latency_ms = int((time.perf_counter() - started) * 1000)
            content = "".join(assistant_parts)
            thinking = "".join(thinking_parts)
            message_id = None
            try:
                message_id = _persist_assistant_and_log(
                    owner_type=owner_type,
                    owner_id=owner_id,
                    conversation_id=persist_conversation_id,
                    model=model,
                    stream=True,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=outbound,
                    content=content,
                    thinking=thinking,
                    thinking_enabled=thinking_enabled,
                    usage=usage,
                    latency_ms=latency_ms,
                )
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': f'落库失败: {e}'}, ensure_ascii=False)}\n\n"
                return

            if message_id is not None:
                yield f"data: {json.dumps({'type': 'done', 'message_id': message_id}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except DeepSeekError as e:
            latency_ms = int((time.perf_counter() - started) * 1000)
            try:
                _persist_assistant_and_log(
                    owner_type=owner_type,
                    owner_id=owner_id,
                    conversation_id=persist_conversation_id,
                    model=model,
                    stream=True,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=outbound,
                    content="",
                    thinking="",
                    thinking_enabled=thinking_enabled,
                    usage={},
                    latency_ms=latency_ms,
                    status="error",
                    error_message=str(e),
                )
            except Exception:
                pass
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _list_logs_handler(
    db: Session,
    owner: ChatOwner,
    conversation_id: int | None,
    page_num: int,
    page_size: int,
):
    rows, total = chat_dao.list_llm_logs(
        db,
        owner.owner_type,
        owner.owner_id,
        conversation_id=conversation_id,
        page_num=page_num,
        page_size=page_size,
    )
    return ok(
        {
            "list": [_log_out(r) for r in rows],
            "total": total,
            "pageNum": page_num,
            "pageSize": page_size,
        }
    )


def _update_conv_handler(conversation_id: int, body: UpdateConversationBody, db: Session, owner: ChatOwner):
    fields = [
        body.title,
        body.model,
        body.system_prompt,
        body.max_tokens,
        body.temperature,
        body.stream_enabled,
        body.thinking_enabled,
        body.markdown_enabled,
        body.memory_pinned,
    ]
    if all(v is None for v in fields) and not body.clear_system_prompt:
        raise biz_error("请提供要更新的字段")
    try:
        row = chat_dao.update_conversation(
            db,
            conversation_id,
            owner.owner_type,
            owner.owner_id,
            title=body.title,
            model=body.model,
            system_prompt=body.system_prompt,
            clear_system_prompt=body.clear_system_prompt,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            stream_enabled=None if body.stream_enabled is None else (1 if body.stream_enabled else 0),
            thinking_enabled=None if body.thinking_enabled is None else (1 if body.thinking_enabled else 0),
            markdown_enabled=None if body.markdown_enabled is None else (1 if body.markdown_enabled else 0),
            memory_pinned=None if body.memory_pinned is None else (1 if body.memory_pinned else 0),
        )
    except ValueError as e:
        raise biz_error(str(e))
    if not row:
        raise not_found("会话不存在")
    return ok(_conv_out(row), "更新成功")


# ---------- 管理端 ----------
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


@router.get("/memory")
def get_memory(
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_admin),
):
    rows = chat_dao.list_pinned_conversations(db, owner.owner_type, owner.owner_id)
    return ok(
        {
            "pinned": [_conv_out(r) for r in rows],
            "max_pinned": chat_dao.MAX_PINNED_CONVERSATIONS,
        }
    )


@router.get("/llm-logs")
def list_llm_logs(
    conversation_id: int | None = None,
    page_num: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_admin),
):
    return _list_logs_handler(db, owner, conversation_id, page_num, page_size)


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
        system_prompt=body.system_prompt,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
        stream_enabled=1 if body.stream_enabled else 0,
        thinking_enabled=1 if body.thinking_enabled else 0,
        markdown_enabled=1 if body.markdown_enabled else 0,
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
    return _update_conv_handler(conversation_id, body, db, owner)


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
    return await _run_chat(db, owner, body)


# ---------- 学生门户 ----------
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


@portal_router.get("/memory")
def portal_get_memory(
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_portal),
):
    rows = chat_dao.list_pinned_conversations(db, owner.owner_type, owner.owner_id)
    return ok(
        {
            "pinned": [_conv_out(r) for r in rows],
            "max_pinned": chat_dao.MAX_PINNED_CONVERSATIONS,
        }
    )


@portal_router.get("/llm-logs")
def portal_list_llm_logs(
    conversation_id: int | None = None,
    page_num: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    owner: ChatOwner = Depends(_owner_for_portal),
):
    return _list_logs_handler(db, owner, conversation_id, page_num, page_size)


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
        system_prompt=body.system_prompt,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
        stream_enabled=1 if body.stream_enabled else 0,
        thinking_enabled=1 if body.thinking_enabled else 0,
        markdown_enabled=1 if body.markdown_enabled else 0,
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
    return _update_conv_handler(conversation_id, body, db, owner)


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
    return await _run_chat(db, owner, body)
