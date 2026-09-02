from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

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
) -> AsyncIterator[str]:
    if not api_key or not api_key.strip():
        raise DeepSeekError("请先在设置中配置 DeepSeek API Key")

    url = f"{deepseek_base_url()}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise DeepSeekError(
                    f"DeepSeek API 错误 ({response.status_code}): {body.decode(errors='replace')}"
                )
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
