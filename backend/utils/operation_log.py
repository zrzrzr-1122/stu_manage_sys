import json
import re

from database import Session
from dao.log_dao import add_operation_log
from jwt_auth.jwt_util import decode_token, JwtError

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

SKIP_PATHS = {
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
    "/api/v1/auth/captcha",
    "/api/v1/auth/refresh-token",
    "/api/v1/sse/connect",
}

MODULE_RULES = (
    ("/api/v2/students", "学生信息"),
    ("/api/v2/classes", "班级管理"),
    ("/api/v2/teachers", "教师管理"),
    ("/api/v2/scores", "成绩管理"),
    ("/api/v2/employments", "就业管理"),
    ("/api/v2/departments", "部门管理"),
    ("/api/v2/consultants", "顾问管理"),
    ("/api/v1/sms/students", "学生信息"),
    ("/api/v1/sms/classes", "班级管理"),
    ("/api/v1/sms/teachers", "教师管理"),
    ("/api/v1/sms/scores", "成绩管理"),
    ("/api/v1/sms/employments", "就业管理"),
    ("/api/v1/sms/departments", "部门管理"),
    ("/api/v1/sms/consultants", "顾问管理"),
    ("/api/v1/auth", "登录认证"),
    ("/api/v1/portal", "学生门户"),
)

ACTION_LABEL = {
    "POST": ("CREATE", "新增"),
    "PUT": ("UPDATE", "修改"),
    "PATCH": ("UPDATE", "修改"),
    "DELETE": ("DELETE", "删除"),
}


def should_record(method: str, path: str) -> bool:
    if method.upper() not in WRITE_METHODS:
        return False
    return path not in SKIP_PATHS


def resolve_title(method: str, path: str) -> tuple[str, str, str]:
    method = method.upper()
    if path.endswith("/password/reset") or path.endswith("/password-resets"):
        return "学生信息", "RESET_PWD", "学生信息 - 重置密码"
    if path == "/api/v1/auth/login":
        return "登录认证", "LOGIN", "管理员登录"
    if path == "/api/v1/auth/logout":
        return "登录认证", "LOGOUT", "管理员退出"
    if path == "/api/v1/portal/login":
        return "学生门户", "LOGIN", "学生登录"
    if path == "/api/v1/portal/password":
        return "学生门户", "UPDATE", "学生门户 - 修改密码"
    if path == "/api/v1/portal/me" and method == "PUT":
        return "学生门户", "UPDATE", "学生门户 - 修改资料"

    module = "系统"
    for prefix, name in MODULE_RULES:
        if path == prefix or path.startswith(prefix + "/"):
            module = name
            break
    action_type, action_label = ACTION_LABEL.get(method, ("OTHER", method))
    return module, action_type, f"{module} - {action_label}"


def client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for") or ""
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return (request.client.host or "")[:64]
    return ""


def parse_user_agent(ua: str) -> tuple[str, str]:
    ua = ua or ""
    if "Windows" in ua:
        os_name = "Windows"
    elif "Mac OS" in ua or "Macintosh" in ua:
        os_name = "macOS"
    elif "Android" in ua:
        os_name = "Android"
    elif "iPhone" in ua or "iPad" in ua:
        os_name = "iOS"
    elif "Linux" in ua:
        os_name = "Linux"
    else:
        os_name = "未知"

    if "Edg/" in ua:
        browser = "Edge"
    elif "Chrome/" in ua:
        browser = "Chrome"
    elif "Firefox/" in ua:
        browser = "Firefox"
    elif "Safari/" in ua:
        browser = "Safari"
    else:
        browser = "未知"
    return browser, os_name


def _operator_from_request(request) -> tuple[int | None, str | None]:
    name = getattr(request.state, "log_operator_name", None)
    operator_id = getattr(request.state, "log_operator_id", None)
    if name:
        return operator_id, str(name)

    auth = request.headers.get("Authorization") or ""
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else auth.strip()
    if not token:
        return None, None
    try:
        payload = decode_token(token, expect_type="access")
    except JwtError:
        return None, None
    try:
        operator_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        operator_id = None
    name = payload.get("username") or payload.get("stuName")
    return operator_id, str(name) if name else None


def _status_from_body(status_code: int, body: bytes | None) -> tuple[int, str | None]:
    if status_code >= 400:
        return 0, f"HTTP {status_code}"
    if not body:
        return 1, None
    try:
        payload = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return 1, None
    if isinstance(payload, dict) and payload.get("code") and payload.get("code") != "00000":
        return 0, payload.get("msg") or "业务失败"
    return 1, None


def record_from_request(
    request,
    response,
    elapsed_ms: int,
    error_msg: str | None = None,
    body: bytes | None = None,
) -> None:
    path = request.url.path
    if not should_record(request.method, path):
        return

    module, action_type, title = resolve_title(request.method, path)
    status_code = getattr(response, "status_code", 500) if response is not None else 500
    if body is None and response is not None:
        body = getattr(response, "body", None)
    status, biz_error = _status_from_body(status_code, body)
    if response is None:
        status = 0
        biz_error = error_msg or "请求异常"
    operator_id, operator_name = _operator_from_request(request)
    browser, os_name = parse_user_agent(request.headers.get("user-agent") or "")
    path_id = None
    matched = re.search(r"/(\d+)(?:/|$)", path)
    if matched:
        path_id = matched.group(1)

    content_parts = [f"{request.method} {path}"]
    if path_id:
        content_parts.append(f"编号 {path_id}")
    content = "，".join(content_parts)[:500]

    db = Session()
    try:
        add_operation_log(
            db,
            module=module,
            action_type=action_type,
            title=title,
            content=content,
            operator_id=operator_id,
            operator_name=operator_name,
            request_uri=path[:255],
            request_method=request.method.upper(),
            ip=client_ip(request),
            browser=browser,
            os=os_name,
            status=status,
            execution_time=max(elapsed_ms, 0),
            error_msg=(error_msg or biz_error),
        )
    except Exception as exc:
        db.rollback()
        print(f"[operation_log] 写入失败: {exc}")
    finally:
        db.close()
