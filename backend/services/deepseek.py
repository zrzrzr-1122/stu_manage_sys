from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from services.crypto import decrypt_text, encrypt_text


class DeepSeekError(Exception):
    pass


class ApiKeyError(Exception):
    pass


def deepseek_base_url() -> str:
    return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")


def mask_api_key(key: str) -> str:
    key = key.strip()
    if len(key) <= 7:
        return "****"
    return f"{key[:3]}****{key[-4:]}"


def encrypt_api_key(api_key: str) -> str:
    return encrypt_text(api_key.strip())


def decrypt_api_key(encrypted: str | None) -> str | None:
    if not encrypted:
        return None
    try:
        return decrypt_text(encrypted).strip()
    except Exception:
        return None


def _build_payload(
    *,
    messages: list[dict],
    model: str,
    stream: bool,
    temperature: float | None,
    max_tokens: int | None,
    tools: list[dict] | None = None,
    tool_choice: str | dict | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }
    if max_tokens is not None and max_tokens > 0:
        payload["max_tokens"] = int(max_tokens)
    # deepseek-reasoner 官方通常忽略 temperature；其它模型可传
    if temperature is not None and model != "deepseek-reasoner":
        payload["temperature"] = float(temperature)
    if stream:
        payload["stream_options"] = {"include_usage": True}
    if tools:
        payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
    return payload


def _parse_error_body(response: httpx.Response, body: bytes | str) -> str:
    text = body.decode(errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
    try:
        data = json.loads(text)
        return data.get("error", {}).get("message", text)
    except json.JSONDecodeError:
        return text


async def validate_deepseek_api_key(api_key: str) -> None:
    url = f"{deepseek_base_url()}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return
        try:
            body = response.json()
            message = body.get("error", {}).get("message", response.text)
        except json.JSONDecodeError:
            message = response.text
        raise ApiKeyError(f"API Key 无效: {message}")


async def stream_chat_completion(
    messages: list[dict],
    api_key: str,
    model: str = "deepseek-chat",
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield structured events: content | thinking | usage."""
    if not api_key or not api_key.strip():
        raise DeepSeekError("请先在设置中配置 DeepSeek API Key")

    url = f"{deepseek_base_url()}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = _build_payload(
        messages=messages,
        model=model,
        stream=True,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise DeepSeekError(
                    f"DeepSeek API 错误 ({response.status_code}): {_parse_error_body(response, body)}"
                )
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue

                usage = chunk.get("usage")
                if usage:
                    yield {
                        "type": "usage",
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "total_tokens": usage.get("total_tokens"),
                    }

                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                reasoning = delta.get("reasoning_content")
                if reasoning:
                    yield {"type": "thinking", "content": reasoning}
                content = delta.get("content")
                if content:
                    yield {"type": "content", "content": content}


async def chat_completion(
    messages: list[dict],
    api_key: str,
    model: str = "deepseek-chat",
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    tools: list[dict] | None = None,
    tool_choice: str | dict | None = None,
) -> dict[str, Any]:
    """Non-stream completion. Returns content, thinking, usage, tool_calls, message."""
    if not api_key or not api_key.strip():
        raise DeepSeekError("请先在设置中配置 DeepSeek API Key")

    url = f"{deepseek_base_url()}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = _build_payload(
        messages=messages,
        model=model,
        stream=False,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools,
        tool_choice=tool_choice,
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            raise DeepSeekError(
                f"DeepSeek API 错误 ({response.status_code}): {_parse_error_body(response, response.content)}"
            )
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage = data.get("usage") or {}
        return {
            "content": message.get("content") or "",
            "thinking": message.get("reasoning_content") or "",
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "finish_reason": choice.get("finish_reason"),
            "tool_calls": message.get("tool_calls") or [],
            "message": message,
        }
