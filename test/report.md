# 自动化测试报告

- **生成时间**：2026-08-29 09:49:44
- **执行命令**：`python test/run_all.py`
- **总结果**：通过
- **统计**：共 29 项 — 通过 27 / 失败 0 / 跳过 2 / 错误 0
- **Playwright 浏览器**：已安装

## 测试范围

| 层级 | 内容 | 工具 |
|------|------|------|
| 后端单元 | JWT 签发/解析 | pytest |
| 登录接口 | B 端 captcha/login/refresh/logout；C 端 portal login | pytest + TestClient |
| 鉴权接口 | users/me、menus、sms overview、portal/me/scores；角色隔离 | pytest |
| 前端冒烟 | admin/web 登录页可达；前后端登录契约 | httpx |
| 前端 E2E | token 注入进首页；web 学号登录（可选） | Playwright |

## 用例明细

| 分类 | 用例 | 结果 | 备注 |
|------|------|------|------|
| 登录接口 | `test/backend/test_admin_login.py::test_captcha_ok` | ✅ passed |  |
| 登录接口 | `test/backend/test_admin_login.py::test_admin_login_success` | ✅ passed |  |
| 登录接口 | `test/backend/test_admin_login.py::test_admin_login_wrong_password` | ✅ passed |  |
| 登录接口 | `test/backend/test_admin_login.py::test_admin_login_wrong_captcha` | ✅ passed |  |
| 登录接口 | `test/backend/test_admin_login.py::test_refresh_token` | ✅ passed |  |
| 登录接口 | `test/backend/test_admin_login.py::test_logout` | ✅ passed |  |
| 后端单元 | `test/backend/test_jwt_util.py::test_issue_tokens_structure` | ✅ passed |  |
| 后端单元 | `test/backend/test_jwt_util.py::test_access_token_payload` | ✅ passed |  |
| 后端单元 | `test/backend/test_jwt_util.py::test_refresh_token_type_guard` | ✅ passed |  |
| 后端单元 | `test/backend/test_jwt_util.py::test_invalid_token` | ✅ passed |  |
| 登录接口 | `test/backend/test_portal_login.py::test_portal_login_success` | ✅ passed |  |
| 登录接口 | `test/backend/test_portal_login.py::test_portal_login_wrong_password` | ✅ passed |  |
| 登录接口 | `test/backend/test_portal_login.py::test_portal_me_requires_token` | ✅ passed |  |
| 登录接口 | `test/backend/test_portal_login.py::test_portal_me_with_token` | ✅ passed |  |
| 登录接口 | `test/backend/test_portal_login.py::test_admin_token_cannot_access_portal` | ✅ passed |  |
| 鉴权/业务接口 | `test/backend/test_protected_api.py::test_users_me_without_token` | ✅ passed |  |
| 鉴权/业务接口 | `test/backend/test_protected_api.py::test_users_me_with_admin_token` | ✅ passed |  |
| 鉴权/业务接口 | `test/backend/test_protected_api.py::test_menu_routes_with_admin` | ✅ passed |  |
| 鉴权/业务接口 | `test/backend/test_protected_api.py::test_sms_overview_with_admin` | ✅ passed |  |
| 鉴权/业务接口 | `test/backend/test_protected_api.py::test_student_token_cannot_access_admin_api` | ✅ passed |  |
| 鉴权/业务接口 | `test/backend/test_protected_api.py::test_portal_scores_with_student` | ✅ passed |  |
| 前端冒烟 | `test/frontend/test_login_smoke.py::test_admin_login_page_html` | ✅ passed |  |
| 前端冒烟 | `test/frontend/test_login_smoke.py::test_admin_dev_api_captcha_via_proxy_or_backend` | ✅ passed |  |
| 前端冒烟 | `test/frontend/test_login_smoke.py::test_admin_login_api_contract` | ✅ passed |  |
| 前端冒烟 | `test/frontend/test_login_smoke.py::test_web_login_page_or_skip` | ⏭️ skipped | ('D:\\git_proj_storege\\proj_0814\\test\\frontend\\test_login_smoke.py', 79, 'Skipped: web(:5173) 未启动') |
| 前端冒烟 | `test/frontend/test_login_smoke.py::test_portal_login_api_contract` | ✅ passed |  |
| 前端 E2E | `test/frontend/test_login_e2e.py::test_admin_login_page_loads[chromium]` | ✅ passed |  |
| 前端 E2E | `test/frontend/test_login_e2e.py::test_admin_api_login_then_open_home[chromium]` | ✅ passed |  |
| 前端 E2E | `test/frontend/test_login_e2e.py::test_web_login_page_and_flow[chromium]` | ⏭️ skipped | ('D:\\git_proj_storege\\proj_0814\\test\\frontend\\test_login_e2e.py', 82, 'Skipped: web 未启动（可选：cd web && npm run dev）') |

## 账号与前置条件

- MySQL `yanjiusheng` 可用；建议已执行 `python data/seed_mock.py`
- B 端：`admin / 123456`
- C 端：学号 `1` / `123456`
- 前端冒烟/E2E 需要 `npm run dev`（admin:3000、backend:8000）；web:5173 可选

## 如何复现

```bash
pip install -r test/requirements.txt
playwright install chromium   # 可选
python test/run_all.py
pytest test/backend -v
```

## 原始输出摘要

```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-8.3.4, pluggy-1.5.0 -- C:\Users\Windows\anaconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.13.5', 'Platform': 'Windows-10-10.0.19045-SP0', 'Packages': {'pytest': '8.3.4', 'pluggy': '1.5.0'}, 'Plugins': {'anyio': '4.7.0', 'base-url': '2.1.0', 'json-report': '1.5.0', 'metadata': '3.1.1', 'playwright': '0.9.0'}, 'JAVA_HOME': 'C:\\Program Files\\Java\\jdk1.8.0_181', 'Base URL': ''}
rootdir: D:\git_proj_storege\proj_0814
configfile: pytest.ini
plugins: anyio-4.7.0, base-url-2.1.0, json-report-1.5.0, metadata-3.1.1, playwright-0.9.0
collecting ... collected 29 items

test/backend/test_admin_login.py::test_captcha_ok PASSED                 [  3%]
test/backend/test_admin_login.py::test_admin_login_success PASSED        [  6%]
test/backend/test_admin_login.py::test_admin_login_wrong_password PASSED [ 10%]
test/backend/test_admin_login.py::test_admin_login_wrong_captcha PASSED  [ 13%]
test/backend/test_admin_login.py::test_refresh_token PASSED              [ 17%]
test/backend/test_admin_login.py::test_logout PASSED                     [ 20%]
test/backend/test_jwt_util.py::test_issue_tokens_structure PASSED        [ 24%]
test/backend/test_jwt_util.py::test_access_token_payload PASSED          [ 27%]
test/backend/test_jwt_util.py::test_refresh_token_type_guard PASSED      [ 31%]
test/backend/test_jwt_util.py::test_invalid_token PASSED                 [ 34%]
test/backend/test_portal_login.py::test_portal_login_success PASSED      [ 37%]
test/backend/test_portal_login.py::test_portal_login_wrong_password PASSED [ 41%]
test/backend/test_portal_login.py::test_portal_me_requires_token PASSED  [ 44%]
test/backend/test_portal_login.py::test_portal_me_with_token PASSED      [ 48%]
test/backend/test_portal_login.py::test_admin_token_cannot_access_portal PASSED [ 51%]
test/backend/test_protected_api.py::test_users_me_without_token PASSED   [ 55%]
test/backend/test_protected_api.py::test_users_me_with_admin_token PASSED [ 58%]
test/backend/test_protected_api.py::test_menu_routes_with_admin PASSED   [ 62%]
test/backend/test_protected_api.py::test_sms_overview_with_admin PASSED  [ 65%]
test/backend/test_protected_api.py::test_student_token_cannot_access_admin_api PASSED [ 68%]
test/backend/test_protected_api.py::test_portal_scores_with_student PASSED [ 72%]
test/frontend/test_login_smoke.py::test_admin_login_page_html PASSED     [ 75%]
test/frontend/test_login_smoke.py::test_admin_dev_api_captcha_via_proxy_or_backend PASSED [ 79%]
test/frontend/test_login_smoke.py::test_admin_login_api_contract PASSED  [ 82%]
test/frontend/test_login_smoke.py::test_web_login_page_or_skip SKIPPED   [ 86%]
test/frontend/test_login_smoke.py::test_portal_login_api_contract PASSED [ 89%]
test/frontend/test_login_e2e.py::test_admin_login_page_loads[chromium] PASSED [ 93%]
test/frontend/test_login_e2e.py::test_admin_api_login_then_open_home[chromium] PASSED [ 96%]
test/frontend/test_login_e2e.py::test_web_login_page_and_flow[chromium] SKIPPED [100%]

============================== warnings summary ===============================
C:\Users\Windows\anaconda3\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\Windows\anaconda3\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
--------------------------------- JSON report ---------------------------------
report saved to: D:\git_proj_storege\proj_0814\test\.pytest_report.json
================== 27 passed, 2 skipped, 1 warning in 13.25s ==================
```
