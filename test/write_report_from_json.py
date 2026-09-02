"""从 test/.pytest_report.json 生成 test/report.md（run_all 失败时的兜底）。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "backend"))
from utils.date_format import format_datetime
data = json.loads((ROOT / ".pytest_report.json").read_text(encoding="utf-8"))
summary = data.get("summary") or {}
passed = int(summary.get("passed", 0))
failed = int(summary.get("failed", 0))
skipped = int(summary.get("skipped", 0))
errors = int(summary.get("error", 0)) + int(summary.get("errors", 0))
total = passed + failed + skipped + errors
status = "通过" if failed == 0 and errors == 0 else "未通过"


def bucket(n: str) -> str:
    if "login_e2e" in n:
        return "前端 E2E"
    if "login_smoke" in n:
        return "前端冒烟"
    if "jwt_util" in n:
        return "后端单元"
    if "admin_login" in n or "portal_login" in n:
        return "登录接口"
    if "protected" in n:
        return "鉴权/业务接口"
    return "其他"


lines = [
    "# 自动化测试报告",
    "",
    f"- **生成时间**：{format_datetime(datetime.now())}",
    "- **执行命令**：`python test/run_all.py` / `pytest test/backend test/frontend/test_login_smoke.py`",
    f"- **总结果**：{status}",
    f"- **统计**：共 {total} 项 — 通过 {passed} / 失败 {failed} / 跳过 {skipped} / 错误 {errors}",
    "",
    "## 测试范围",
    "",
    "| 层级 | 内容 | 工具 |",
    "|------|------|------|",
    "| 后端单元 | JWT 签发/解析 | pytest |",
    "| 登录接口 | B 端 captcha/login/refresh/logout；C 端 portal login | pytest + TestClient |",
    "| 鉴权接口 | users/me、menus、sms overview、portal/me/scores；角色隔离 | pytest |",
    "| 前端冒烟 | admin/web 登录页可达；前后端登录契约 | httpx |",
    "| 前端 E2E | token 注入进首页；web 学号登录（可选） | Playwright |",
    "",
    "## 用例明细",
    "",
    "| 分类 | 用例 | 结果 | 备注 |",
    "|------|------|------|------|",
]

for t in data.get("tests") or []:
    nodeid = t.get("nodeid", "")
    outcome = t.get("outcome", "")
    note = ""
    if outcome in ("failed", "skipped"):
        note = str((t.get("call") or {}).get("longrepr") or "")[:120].replace("|", "/").replace("\n", " ")
    icon = {"passed": "✅", "failed": "❌", "skipped": "⏭️", "error": "💥"}.get(outcome, outcome)
    lines.append(f"| {bucket(nodeid)} | `{nodeid}` | {icon} {outcome} | {note} |")

lines.extend(
    [
        "",
        "## 账号与前置条件",
        "",
        "- MySQL `yanjiusheng` 可用；建议已执行 `python data/seed_mock.py`",
        "- B 端：`admin / 123456`",
        "- C 端：学号 `1` / `123456`",
        "- 前端冒烟/E2E 需要 `npm run dev`（admin:3000、backend:8000）；web:5173 可选",
        "",
        "## 如何复现",
        "",
        "```bash",
        "pip install -r test/requirements.txt",
        "playwright install chromium   # 可选 E2E",
        "python test/run_all.py",
        "```",
        "",
        "## 说明",
        "",
        "- 后端用例通过 FastAPI `TestClient` 进程内调用，不依赖已启动的 uvicorn。",
        "- 前端冒烟探测 `http://127.0.0.1:3000`；本次 `web(:5173)` 未启动时对应用例会 skip。",
        "- Playwright E2E 需本机安装 chromium；下载完成后再次执行 `python test/run_all.py` 即可补跑。",
        "",
    ]
)

(ROOT / "report.md").write_text("\n".join(lines), encoding="utf-8")
print(f"wrote report.md -> {status} ({passed}/{total})")
