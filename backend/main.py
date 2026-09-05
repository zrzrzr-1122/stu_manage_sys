# uvicorn main:app --host=0.0.0.0 --port=8000 --reload
from pathlib import Path

from dotenv import load_dotenv

# 优先加载仓库根目录 .env，其次 backend/.env，最后 .env.example（含可共享配置如高德 Key）
_root = Path(__file__).resolve().parent.parent
_backend = Path(__file__).resolve().parent
load_dotenv(_root / ".env")
load_dotenv(_backend / ".env")
load_dotenv(_root / ".env.example")
load_dotenv(_backend / ".env.example")

import time
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response as StarletteResponse

from database import init_database
from utils.log_config import logger
from utils.operation_log import record_from_request, should_record
from jwt_auth.oauth_router import auth_router
from api.v1.router import v1_router
from api.v2.router import v2_router
from api.v1.result import ok
from exceptions import register_exception_handlers

init_database()

app = FastAPI(title="沃林学生管理系统", version="2.0")
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    # 监听 0.0.0.0 时允许局域网前端直连
    allow_origin_regex=r"https?://("
    r"localhost|127\.0\.0\.1|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["开始访问测试"])
def index():
    logger.message("info", "访问首页接口")
    return ok({
        "msg": "服务正常运行",
        "admin": "http://localhost:3000",
        "portal": "http://localhost:5173",
    })


@app.middleware("http")
async def log_request(request, call_next):
    path = request.url.path
    skip_paths = ["/docs", "/openapi.json", "/favicon.ico"]
    started = time.perf_counter()
    response = None
    if path not in skip_paths:
        logger.message("info", f"收到请求：{request.method} {path}")
    try:
        response = await call_next(request)
    except Exception as e:
        logger.message("error", f"错误：{request.method} {path}")
        record_from_request(
            request,
            None,
            int((time.perf_counter() - started) * 1000),
            str(e),
        )
        raise e

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if path not in skip_paths:
        logger.message("info", f"请求结束，状态码：{response.status_code}")

    # SSE / 流式响应禁止整包缓冲，否则客户端收不到流且连接占用变长
    media_type = (response.media_type or "").split(";")[0].strip().lower()
    if media_type == "text/event-stream":
        return response

    if should_record(request.method, path):
        body_chunks = []
        async for chunk in response.body_iterator:
            body_chunks.append(chunk if isinstance(chunk, (bytes, bytearray)) else str(chunk).encode("utf-8"))
        body = b"".join(body_chunks)
        record_from_request(request, response, elapsed_ms, body=body)
        return StarletteResponse(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
            background=getattr(response, "background", None),
        )

    return response


app.include_router(v1_router)
app.include_router(v2_router)

app.include_router(auth_router, prefix="/auth", tags=["JWT登录"])


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
