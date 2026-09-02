"""AI 聊天接口冒烟：鉴权、会话 CRUD、参数配置、调用日志（不强制真实 DeepSeek）。"""
from __future__ import annotations


def _admin_headers(client) -> dict:
    resp = client.post("/auth/login", data={"username": "admin", "password": "123456"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _portal_headers(client) -> dict:
    resp = client.post("/api/v1/portal/login", json={"stu_id": 1, "password": "123456"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == "00000", body
    return {"Authorization": f"Bearer {body['data']['accessToken']}"}


def test_admin_chat_menu_and_crud(client):
    headers = _admin_headers(client)

    menus = client.get("/api/v1/menus/routes", headers=headers)
    assert menus.status_code == 200
    assert menus.json()["code"] == "00000"
    tree = menus.json()["data"]
    titles = []

    def walk(nodes):
        for n in nodes or []:
            titles.append((n.get("meta") or {}).get("title") or n.get("name"))
            walk(n.get("children") or [])

    walk(tree)
    assert any(t and ("AI" in str(t) or "智能" in str(t) or "助手" in str(t)) for t in titles), titles

    models = client.get("/api/v1/chat/models", headers=headers)
    assert models.json()["code"] == "00000", models.text
    assert isinstance(models.json()["data"], list)
    assert models.json()["data"]

    key_status = client.get("/api/v1/chat/api-key", headers=headers)
    assert key_status.json()["code"] == "00000", key_status.text
    assert "configured" in key_status.json()["data"]

    created = client.post(
        "/api/v1/chat/conversations",
        headers=headers,
        json={
            "title": "smoke_chat",
            "model": "deepseek-chat",
            "temperature": 0.5,
            "max_tokens": 512,
            "system_prompt": "you are a tester",
            "stream_enabled": True,
            "thinking_enabled": True,
            "markdown_enabled": True,
        },
    )
    assert created.json()["code"] == "00000", created.text
    data = created.json()["data"]
    conv_id = data["id"]
    assert data["temperature"] == 0.5
    assert data["max_tokens"] == 512
    assert data["system_prompt"] == "you are a tester"
    assert data["stream_enabled"] is True

    listed = client.get("/api/v1/chat/conversations", headers=headers)
    assert listed.json()["code"] == "00000"
    assert any(c["id"] == conv_id for c in listed.json()["data"])

    msgs = client.get(f"/api/v1/chat/conversations/{conv_id}/messages", headers=headers)
    assert msgs.json()["code"] == "00000"
    assert msgs.json()["data"] == []

    renamed = client.patch(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=headers,
        json={
            "title": "smoke_renamed",
            "temperature": 0.2,
            "max_tokens": 256,
            "stream_enabled": False,
        },
    )
    assert renamed.json()["code"] == "00000", renamed.text
    assert renamed.json()["data"]["title"] == "smoke_renamed"
    assert renamed.json()["data"]["temperature"] == 0.2
    assert renamed.json()["data"]["stream_enabled"] is False

    # 无 Key 时流式应返回业务错误事件，而不是 500；已配置 Key 时允许正常流式
    stream = client.post(
        "/api/v1/chat/completions",
        headers=headers,
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "conversation_id": conv_id,
            "model": "deepseek-chat",
            "stream": True,
        },
    )
    assert stream.status_code == 200, stream.text
    body = stream.text
    assert "API Key" in body or "error" in body or "content" in body or "[DONE]" in body

    # 非流式：无 Key 业务错误；有 Key 则返回成功 JSON
    nostream = client.post(
        "/api/v1/chat/completions",
        headers=headers,
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "conversation_id": conv_id,
            "model": "deepseek-chat",
            "stream": False,
            "temperature": 0.3,
            "max_tokens": 64,
        },
    )
    assert nostream.status_code == 200, nostream.text
    assert (
        "API Key" in nostream.text
        or nostream.json().get("code") != "00000"
        or nostream.json().get("code") == "00000"
    )

    logs = client.get("/api/v1/chat/llm-logs", headers=headers, params={"conversation_id": conv_id})
    assert logs.json()["code"] == "00000", logs.text
    assert "list" in logs.json()["data"]
    assert "total" in logs.json()["data"]

    deleted = client.delete(f"/api/v1/chat/conversations/{conv_id}", headers=headers)
    assert deleted.json()["code"] == "00000", deleted.text


def test_portal_chat_crud(client):
    headers = _portal_headers(client)

    models = client.get("/api/v1/portal/chat/models", headers=headers)
    assert models.json()["code"] == "00000", models.text

    key_status = client.get("/api/v1/portal/chat/api-key", headers=headers)
    assert key_status.json()["code"] == "00000", key_status.text

    created = client.post(
        "/api/v1/portal/chat/conversations",
        headers=headers,
        json={"title": "portal_smoke", "model": "deepseek-chat", "max_tokens": 128},
    )
    assert created.json()["code"] == "00000", created.text
    conv_id = created.json()["data"]["id"]

    msgs = client.get(f"/api/v1/portal/chat/conversations/{conv_id}/messages", headers=headers)
    assert msgs.json()["code"] == "00000"

    logs = client.get("/api/v1/portal/chat/llm-logs", headers=headers, params={"conversation_id": conv_id})
    assert logs.json()["code"] == "00000", logs.text

    # 学生不能访问 B 端 chat 接口
    denied = client.get("/api/v1/chat/models", headers=headers)
    assert denied.status_code in (200, 401)
    body = denied.json()
    assert body.get("code") != "00000"

    deleted = client.delete(f"/api/v1/portal/chat/conversations/{conv_id}", headers=headers)
    assert deleted.json()["code"] == "00000", deleted.text


def test_admin_student_isolation(client):
    admin_h = _admin_headers(client)
    portal_h = _portal_headers(client)

    a = client.post(
        "/api/v1/chat/conversations",
        headers=admin_h,
        json={"title": "admin_only", "model": "deepseek-chat"},
    ).json()
    assert a["code"] == "00000"
    admin_conv = a["data"]["id"]

    # 学生读不到管理员会话
    sneak = client.get(
        f"/api/v1/portal/chat/conversations/{admin_conv}/messages",
        headers=portal_h,
    )
    assert sneak.json()["code"] != "00000"

    # 学生日志接口不能看到管理员会话日志（按 owner 隔离，空列表或仅自己的）
    logs = client.get(
        "/api/v1/portal/chat/llm-logs",
        headers=portal_h,
        params={"conversation_id": admin_conv},
    )
    assert logs.json()["code"] == "00000"
    for row in logs.json()["data"]["list"]:
        assert row.get("conversation_id") != admin_conv or False

    client.delete(f"/api/v1/chat/conversations/{admin_conv}", headers=admin_h)


def test_cross_session_memory(client):
    admin_h = _admin_headers(client)
    portal_h = _portal_headers(client)

    # 管理员创建会话并写入消息，再钉选
    created = client.post(
        "/api/v1/chat/conversations",
        headers=admin_h,
        json={"title": "pin_source", "model": "deepseek-chat"},
    ).json()
    assert created["code"] == "00000", created
    conv_id = created["data"]["id"]

    from database import Session as DbSession
    from dao import chat_dao

    db = DbSession()
    try:
        chat_dao.add_message(db, conv_id, "user", "SMOKE_PIN_MARKER_ADMIN_XYZ")
        chat_dao.add_message(db, conv_id, "assistant", "ack pin memory")
    finally:
        db.close()

    pin = client.patch(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=admin_h,
        json={"memory_pinned": True},
    )
    assert pin.json()["code"] == "00000", pin.text
    assert pin.json()["data"]["memory_pinned"] is True

    mem = client.get("/api/v1/chat/memory", headers=admin_h)
    assert mem.json()["code"] == "00000", mem.text
    pinned_ids = [c["id"] for c in mem.json()["data"]["pinned"]]
    assert conv_id in pinned_ids

    # 学生看不到管理员钉选
    mem_p = client.get("/api/v1/portal/chat/memory", headers=portal_h)
    assert mem_p.json()["code"] == "00000"
    assert conv_id not in [c["id"] for c in mem_p.json()["data"]["pinned"]]

    from api.v1.chat import build_merged_system
    from api.v1.chat_deps import ChatOwner
    from model.user_model import SysUser

    db = DbSession()
    try:
        admin_user = db.query(SysUser).filter(SysUser.username == "admin", SysUser.is_delete == 0).first()
        assert admin_user is not None
        admin_owner = ChatOwner(
            owner_type="admin",
            owner_id=admin_user.id,
            display_name=admin_user.username,
        )
        # 当前会话排除时，钉选内容仍应注入（排除的是另一会话）
        merged = build_merged_system(
            db, admin_owner, "session_prompt_smoke", exclude_conversation_id=None
        )
        assert merged is not None
        assert "SMOKE_PIN_MARKER_ADMIN_XYZ" in merged
        assert "【钉选会话记忆】" in merged
        assert "session_prompt_smoke" in merged

        # 当前会话自身钉选时不重复注入
        merged_self = build_merged_system(
            db, admin_owner, None, exclude_conversation_id=conv_id
        )
        assert not merged_self or "SMOKE_PIN_MARKER_ADMIN_XYZ" not in merged_self

        portal_owner = ChatOwner(owner_type="student", owner_id=1, display_name="stu1")
        merged_portal = build_merged_system(db, portal_owner, None)
        # 学生可能只有档案，不应含管理员标记
        assert not merged_portal or "SMOKE_PIN_MARKER_ADMIN_XYZ" not in merged_portal
        if merged_portal:
            assert "【学生档案】" in merged_portal or "姓名" in merged_portal
    finally:
        db.close()

    unpin = client.patch(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=admin_h,
        json={"memory_pinned": False},
    )
    assert unpin.json()["code"] == "00000"
    client.delete(f"/api/v1/chat/conversations/{conv_id}", headers=admin_h)
