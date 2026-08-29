"""
一键跑自动化测试并生成 test/report.md

用法（仓库根目录）：
  pip install -r test/requirements.txt
  playwright install chromium   # 可选，用于浏览器 E2E
  python test/run_all.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "test"
REPORT = TEST_DIR / "report.md"
JSON_REPORT = TEST_DIR / ".pytest_report.json"
(ROOT / "logs").mkdir(exist_ok=True)
(ROOT / "backend" / "logs").mkdir(exist_ok=True)


def run(cmd: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd))
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env or os.environ.copy(),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend") + os.pathsep + env.get("PYTHONPATH", "")

    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "-r",
            str(TEST_DIR / "requirements.txt"),
        ]
    )

    pw = run([sys.executable, "-m", "playwright", "install", "chromium"])
    has_browser = pw.returncode == 0

    pytest_cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(TEST_DIR / "backend"),
        str(TEST_DIR / "frontend" / "test_login_smoke.py"),
        "-v",
        "--tb=short",
        "--json-report",
        f"--json-report-file={JSON_REPORT}",
    ]
    if has_browser:
        pytest_cmd.extend(
            [
                str(TEST_DIR / "frontend" / "test_login_e2e.py"),
                "--browser",
                "chromium",
            ]
        )

    result = run(pytest_cmd, env=env)
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    combined = stdout + "\n" + stderr

    passed = failed = skipped = errors = 0
    cases: list[tuple[str, str, str]] = []

    if JSON_REPORT.exists():
        data = json.loads(JSON_REPORT.read_text(encoding="utf-8"))
        summary = data.get("summary") or {}
        passed = int(summary.get("passed", 0))
        failed = int(summary.get("failed", 0))
        skipped = int(summary.get("skipped", 0))
        errors = int(summary.get("error", 0)) + int(summary.get("errors", 0))
        for t in data.get("tests") or []:
            nodeid = t.get("nodeid", "")
            outcome = t.get("outcome", "")
            note = ""
            if outcome in ("failed", "skipped"):
                note = str((t.get("call") or {}).get("longrepr") or "")[:500]
            cases.append((nodeid, outcome, note))
    else:
        m2 = re.search(
            r"(\d+) passed(?:,\s*(\d+) failed)?(?:,\s*(\d+) skipped)?(?:,\s*(\d+) error)?",
            combined,
        )
        if m2:
            passed = int(m2.group(1) or 0)
            failed = int(m2.group(2) or 0)
            skipped = int(m2.group(3) or 0)
            errors = int(m2.group(4) or 0)

    total = passed + failed + skipped + errors
    status = "通过" if result.returncode == 0 and failed == 0 and errors == 0 else "未通过"

    def bucket(nodeid: str) -> str:
        if "login_e2e" in nodeid:
            return "前端 E2E"
        if "login_smoke" in nodeid:
            return "前端冒烟"
        if "jwt_util" in nodeid:
            return "后端单元"
        if "admin_login" in nodeid or "portal_login" in nodeid:
            return "登录接口"
        if "protected" in nodeid:
            return "鉴权/业务接口"
        return "其他"

    lines = [
        "# 自动化测试报告",
        "",
        f"- **生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "- **执行命令**：`python test/run_all.py`",
        f"- **总结果**：{status}",
        f"- **统计**：共 {total} 项 — 通过 {passed} / 失败 {failed} / 跳过 {skipped} / 错误 {errors}",
        f"- **Playwright 浏览器**：{'已安装' if has_browser else '未安装（已跳过 E2E，仅跑冒烟）'}",
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
    if cases:
        for nodeid, outcome, note in cases:
            icon = {"passed": "✅", "failed": "❌", "skipped": "⏭️", "error": "💥"}.get(
                outcome, outcome
            )
            safe_note = (note or "").replace("|", "/").replace("\n", " ")[:120]
            lines.append(
                f"| {bucket(nodeid)} | `{nodeid}` | {icon} {outcome} | {safe_note} |"
            )
    else:
        lines.append("| - | （未能解析用例列表，见下方原始输出） | - | - |")

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
            "playwright install chromium   # 可选",
            "python test/run_all.py",
            "pytest test/backend -v",
            "```",
            "",
            "## 原始输出摘要",
            "",
            "```",
        ]
    )
    out_lines = combined.strip().splitlines()
    lines.extend(out_lines[-100:] if len(out_lines) > 100 else out_lines)
    lines.append("```")
    lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[report] written -> {REPORT}")
    print(combined[-2500:])
    return 0 if result.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
