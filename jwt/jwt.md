# 沃林学生管理系统 — JWT 鉴权说明

本文档说明 JWT（JSON Web Token）在本项目中的作用、模块结构、完整运作流程，以及 B 端 / C 端两套登录体系的区别。

---

## 1. JWT 在本项目中的作用

JWT 是本项目的**无状态身份凭证**，用来回答三个问题：

1. **你是谁**（`sub`：用户 ID 或学号）
2. **你是什么角色**（`role`：`admin` 或 `student`）
3. **凭证是否仍然有效**（`exp` 过期时间 + 服务端密钥验签）

项目采用**前后端分离**架构，前端（`admin/`、`web/`）不保存 Session，而是在登录成功后拿到 Token，之后每次请求在 Header 里带上：

```http
Authorization: Bearer <accessToken>
```

后端 FastAPI 通过 `jwt_auth/deps.py` 中的依赖函数解析 Token，再决定是否放行接口。

### JWT 承担的核心职责

| 职责 | 说明 |
|------|------|
| **身份认证** | 证明请求来自已登录的管理员或学生 |
| **接口保护** | 业务 API 通过 `Depends(get_current_admin/student)` 拦截未登录请求 |
| **双端隔离** | 同一套 JWT 工具，用 `role` 区分 B 端管理员与 C 端学生 |
| **短期访问 + 长期续期** | Access Token 2 小时，Refresh Token 7 天（仅 B 端实现刷新） |
| **与业务权限解耦** | JWT 只管「是谁」；菜单、按钮权限仍由 `/api/v1/system/*` 单独返回 |

> **注意**：JWT 是无状态的，服务端**不存储** Token 黑名单。Logout 接口目前只做前端清 Token，不会使已签发的 Token 立即失效。

---

## 2. 模块结构与文件职责

```
backend/jwt_auth/
├── jwt_util.py       # 签发 / 解析 JWT（HS256）
├── service.py        # 登录业务：校验账号密码，调用签发
├── dao.py            # 管理员账号查询（sys_user 表）
├── deps.py           # FastAPI 依赖：get_current_admin / get_current_student
├── admin_router.py   # B 端：验证码、登录、刷新、登出
├── portal_router.py  # C 端：学生登录
├── oauth_router.py   # 兼容 OAuth2 格式的 /auth/login（Swagger 用）
└── schemas.py        # 请求 / 响应模型

admin/src/            # B 端：存 Token、自动刷新、路由守卫
web/src/              # C 端：localStorage 存 accessToken
```

### 2.1 后端路由挂载

| 路径 | 来源 | 用途 |
|------|------|------|
| `POST /api/v1/auth/login` | `admin_router.py` | B 端登录（含验证码） |
| `POST /api/v1/auth/refresh-token` | `admin_router.py` | B 端刷新 Token |
| `DELETE /api/v1/auth/logout` | `admin_router.py` | B 端登出（前端清 Token） |
| `GET /api/v1/auth/captcha` | `admin_router.py` | B 端验证码 |
| `POST /api/v1/portal/login` | `portal_router.py` | C 端学生登录 |
| `POST /auth/login` | `oauth_router.py` | OAuth2 兼容登录 |

受保护的业务接口示例：

- B 端：`/api/v1/sms/*`、`/api/v1/system/*`、`/api/v2/*` → `Depends(get_current_admin)`
- C 端：`/api/v1/portal/me`、`/scores`、`/employment` 等 → `Depends(get_current_student)`

---

## 3. Token 结构与配置

### 3.1 算法与密钥

```python
# backend/jwt_auth/jwt_util.py
JWT_SECRET = os.getenv("JWT_SECRET", "woling-sms-jwt-secret-key-change-me-32")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 2 * 60 * 60      # 2 小时
REFRESH_TOKEN_EXPIRE_SECONDS = 7 * 24 * 60 * 60  # 7 天
```

生产环境务必通过环境变量 `JWT_SECRET` 覆盖默认密钥。

### 3.2 Access Token Payload 示例

**管理员：**

```json
{
  "sub": "1",
  "role": "admin",
  "token_type": "access",
  "username": "admin",
  "iat": 1710000000,
  "exp": 1710007200
}
```

**学生：**

```json
{
  "sub": "10001",
  "role": "student",
  "token_type": "access",
  "stuName": "张三",
  "iat": 1710000000,
  "exp": 1710007200
}
```

### 3.3 Refresh Token

- 仅包含 `sub`、`role`、`token_type: "refresh"`
- **只有 B 端**实现了 `/refresh-token` 续期
- C 端 Token 过期后需重新登录

### 3.4 统一错误码

| code | 含义 | 前端处理 |
|------|------|----------|
| `00000` | 成功 | 正常业务 |
| `A0230` | Access Token 无效或过期 | B 端尝试 Refresh |
| `A0231` | Refresh Token 无效或过期 | B 端跳转登录页 |
| `B0001` | 一般业务错误 | 提示 msg |

---

## 4. B 端（admin）完整流程

### 4.1 登录流程

```
用户输入账号/密码/验证码
        ↓
admin 前端 POST /dev-api/api/v1/auth/login
        ↓
Vite 代理 → FastAPI admin_router.login
        ↓
校验验证码 → service.login_admin
        ↓
查 sys_user 表，MD5 比对密码
        ↓
jwt_util.issue_tokens(role=admin)
        ↓
返回 { accessToken, refreshToken, tokenType, expiresIn }
        ↓
admin AuthStorage 写入 localStorage 或 sessionStorage
        ↓
路由守卫检测有 Token → 拉用户信息 → 生成动态菜单
```

**默认管理员**：`admin / 123456`（启动时 `database.seed_admin_user()` 自动创建）

### 4.2 请求鉴权流程

```
admin axios 请求拦截器
        ↓
读取 accessToken，注入 Authorization: Bearer ...
        ↓
FastAPI 业务接口 Depends(get_current_admin)
        ↓
deps._extract_bearer → decode_token(expect_type=access)
        ↓
校验 role == admin → 查 sys_user 是否存在
        ↓
通过 → 执行业务逻辑
失败 → 返回 401 + code A0230
```

### 4.3 Token 自动刷新（单飞模式）

当 Access Token 过期时：

```
业务请求返回 code=A0230
        ↓
admin request.ts 响应拦截器捕获
        ↓
userStore.refreshTokenOnce()（多个并发请求共享一次 refresh）
        ↓
POST /api/v1/auth/refresh-token?refreshToken=...
        ↓
后端 decode refresh token → 再次查用户 → 签发新 Token 对
        ↓
AuthStorage.setTokens 更新本地
        ↓
原请求带新 Token 重试一次
        ↓
若 refresh 也失败 (A0231) → redirectToLogin
```

关键代码位置：

- 刷新逻辑：`admin/src/stores/user.ts` → `refreshTokenOnce`
- 拦截重试：`admin/src/utils/request.ts`
- 后端刷新：`backend/jwt_auth/admin_router.py` → `refresh_token`

### 4.4 登出流程

```
用户点击退出
        ↓
POST /api/v1/auth/logout（可选，服务端直接返回成功）
        ↓
resetAllState：清 Token、清路由、清字典缓存、断 SSE
        ↓
跳转 /login
```

---

## 5. C 端（web）完整流程

### 5.1 登录流程

```
学生输入学号 + 密码
        ↓
web POST /api/v1/portal/login  { stu_id, password }
        ↓
service.login_student
        ↓
查 student_base_info，MD5 校验（默认密码 123456）
        ↓
issue_tokens(role=student, extra={ stuName })
        ↓
localStorage.setItem('portal_token', accessToken)
        ↓
路由守卫放行 → /home
```

### 5.2 请求鉴权

```
web axios 拦截器注入 Bearer portal_token
        ↓
/api/v1/portal/* 接口 Depends(get_current_student)
        ↓
decode access token → role == student → 查学生是否存在
        ↓
student 对象注入到接口 handler（如 portal_me、portal_scores）
```

### 5.3 与 B 端的差异

| 对比项 | B 端 admin | C 端 web |
|--------|------------|----------|
| 登录接口 | `/api/v1/auth/login` | `/api/v1/portal/login` |
| 验证码 | 有 | 无 |
| Token 存储 | localStorage / sessionStorage | localStorage |
| Refresh Token | 有，自动刷新 | 无刷新接口 |
| 角色 | `admin` | `student` |
| 权限模型 | 菜单 + 按钮权限 | 仅能访问自己的数据 |
| 401 处理 | 尝试 refresh | 直接跳登录页 |

---

## 6. 后端鉴权依赖详解

### get_current_admin

```python
# backend/jwt_auth/deps.py（逻辑摘要）
1. 从 Authorization Header 提取 Bearer Token
2. decode_token(token, expect_type="access")
3. 断言 payload["role"] == "admin"
4. 根据 sub 查 SysUser（且 is_delete == 0）
5. 返回 user 对象供接口使用
```

用于：学生管理、成绩、就业、部门、顾问、系统菜单、日志等**全部 B 端写操作**。

### get_current_student

```python
1. 提取 Bearer Token
2. decode_token(expect_type="access")
3. 断言 payload["role"] == "student"
4. 根据 sub(stu_id) 查 Student（且 is_delete == 0）
5. 返回 student 对象
```

用于：C 端只能访问**与当前学生相关**的数据（个人信息、成绩、就业、班级）。

---

## 7. JWT 与「权限」的关系

本项目里 JWT **不等于**完整权限系统：

```
JWT 鉴权                业务权限（RBAC）
─────────               ─────────────────
证明已登录              决定能看到哪些菜单
区分 admin / student    决定能点哪些按钮
                         决定能调哪些接口
```

B 端登录后还会请求：

- `GET /api/v1/system/users/me` — 用户信息
- `GET /api/v1/system/menus/routes` — 动态路由

这些接口本身也需要 JWT，返回的 `roles`、`perms` 供前端 `v-hasPerm` 指令和路由守卫使用。

---

## 8. 安全说明与改进建议

### 当前设计特点

- 密码使用 **MD5** 存储（历史兼容，生产建议升级 bcrypt）
- JWT **无服务端吊销列表**，Token 在过期前始终有效
- C 端无 Refresh Token，体验略差但实现简单
- 密钥默认值写在代码中，**生产必须改 `JWT_SECRET`**

### 建议

1. 生产环境设置强随机 `JWT_SECRET`（≥32 字符）
2. HTTPS 传输，防止 Token 被窃听
3. 如需强制下线，可引入 Redis Token 黑名单
4. C 端可按需补充 refresh-token 接口
5. 密码哈希逐步从 MD5 迁移到 bcrypt / argon2

---

## 9. 快速调试

### 获取 B 端 Token

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}'
```

### 携带 Token 访问受保护接口

```bash
curl http://127.0.0.1:8000/api/v1/system/users/me \
  -H "Authorization: Bearer <accessToken>"
```

### Swagger 文档

http://127.0.0.1:8000/docs

---

## 10. 相关文件索引

| 文件 | 作用 |
|------|------|
| `backend/jwt_auth/jwt_util.py` | Token 签发与解析 |
| `backend/jwt_auth/deps.py` | 接口鉴权入口 |
| `backend/jwt_auth/admin_router.py` | B 端认证 API |
| `backend/jwt_auth/portal_router.py` | C 端登录 API |
| `admin/src/utils/auth.ts` | Token 本地存储 |
| `admin/src/utils/request.ts` | 自动带 Token + 自动刷新 |
| `admin/src/router/guards/permission.ts` | 前端路由守卫 |
| `web/src/api/http.ts` | C 端 Token 注入 |
| `web/src/router/index.ts` | C 端路由守卫 |

流程图见同目录 [`jwt.excalidraw`](./jwt.excalidraw)，可用 [Excalidraw](https://excalidraw.com) 或 VS Code Excalidraw 插件打开。
