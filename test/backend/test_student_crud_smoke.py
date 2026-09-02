"""学生增删改查冒烟（v1 /sms 与 v2 REST 共用 student_dao）。"""
from __future__ import annotations

import time


def _admin_headers(client) -> dict:
    resp = client.post(
        "/auth/login",
        data={"username": "admin", "password": "123456"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_student_crud_v1_and_v2(client):
    headers = _admin_headers(client)
    suffix = str(int(time.time()))

    lst = client.get(
        "/api/v1/sms/students",
        headers=headers,
        params={"pageNum": 1, "pageSize": 1},
    )
    assert lst.status_code == 200, lst.text
    body = lst.json()
    assert body["code"] == "00000", body
    sample = (body["data"]["list"] or [{}])[0]
    class_id = sample.get("class_id") or 1
    counselor = sample.get("counselor") or 1

    payload = {
        "stu_name": f"dao_smoke_{suffix}",
        "class_id": class_id,
        "address": "测试籍贯",
        "education": "本科",
        "counselor": counselor,
        "age": 22,
        "sex": "男",
    }

    # v1
    created = client.post("/api/v1/sms/students", headers=headers, json=payload)
    assert created.status_code == 200, created.text
    cbody = created.json()
    assert cbody["code"] == "00000", cbody
    stu_id = cbody["data"]["stu_id"]

    listed = client.get(
        "/api/v1/sms/students",
        headers=headers,
        params={"pageNum": 1, "pageSize": 10, "stu_name": payload["stu_name"]},
    )
    assert listed.json()["code"] == "00000"
    assert listed.json()["data"]["total"] >= 1

    updated = client.put(
        f"/api/v1/sms/students/{stu_id}",
        headers=headers,
        json={"address": "更新籍贯"},
    )
    assert updated.json()["code"] == "00000", updated.text

    deleted = client.delete(f"/api/v1/sms/students/{stu_id}", headers=headers)
    assert deleted.json()["code"] == "00000", deleted.text

    # v2
    payload2 = {**payload, "stu_name": f"dao_smoke_v2_{suffix}"}
    created2 = client.post("/api/v2/students", headers=headers, json=payload2)
    assert created2.json()["code"] == "00000", created2.text
    stu_id2 = created2.json()["data"]["stu_id"]

    got = client.get(f"/api/v2/students/{stu_id2}", headers=headers)
    assert got.json()["code"] == "00000"
    assert got.json()["data"]["stu_name"] == payload2["stu_name"]
    assert "password_md5" not in got.json()["data"]

    patched = client.patch(
        f"/api/v2/students/{stu_id2}",
        headers=headers,
        json={"major": "计算机"},
    )
    assert patched.json()["code"] == "00000", patched.text

    deleted2 = client.delete(f"/api/v2/students/{stu_id2}", headers=headers)
    assert deleted2.json()["code"] == "00000", deleted2.text
