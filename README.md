# 沃林学生管理系统

前后端分离的学生管理系统。后端沿用 FastAPI，B 端管理后台基于 [vue3-element-template](https://gitee.com/youlaiorg/vue3-element-template)，C 端学生门户基于 [Vuetify](https://github.com/vuetifyjs/vuetify)。

## 目录

```
backend/   FastAPI 接口（业务 + 有来脚手架适配层）
  jwt_auth/ JWT 登录与 RBAC（角色/菜单/权限、班级数据范围）
admin/     B 端后台（Vue3 + Element Plus）
web/       C 端学生门户（Vue3 + Vuetify）
```

## 环境

- Python 3.10+
- Node.js 20+
- MySQL 8，库名 `yanjiusheng`（可用环境变量 `DATABASE_URL` 覆盖）
- B 端推荐 pnpm，也可用 npm

环境变量示例见根目录 `.env.example`。

重要变量：

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | MySQL 连接串 |
| `JWT_SECRET` | JWT 签名密钥（生产务必修改） |
| `ALLOW_DEFAULT_ADMIN` | `1` 时种子演示账号（默认开启） |
| `ALLOW_OAUTH_PASSWORD_LOGIN` | `1` 允许 Swagger `/auth/login` 无验证码登录 |

## 角色与权限（RBAC）

B 端三角色（学生走 C 端，不进后台）：

| 角色 | 演示账号 | 能力摘要 |
|------|----------|----------|
| 超级管理员 | `admin` / `123456` | 全部权限（含删学生、系统用户接口） |
| 教导主任 | `director` / `123456` | 业务全校；可删成绩；**不可删学生**；不管账号 |
| 老师（含任课） | `teacher` / `123456` | 本班范围；可改学生档案但**不可改学号/姓名**；可改本班就业；**不可删成绩** |

老师数据范围：`sys_user.teacher_id` → `teacher_class` / 教师表 `class_id`（`class_info.id`）。

密码存储：bcrypt（兼容旧 MD5，登录成功后自动升级）。B 端登录**必须**验证码。

学生门户：仅查看本人资料/成绩/就业；不可改资料。

账号管理 API（仅超管）：`/api/v1/system/users`、`/api/v1/system/roles`。

## 数据库

启动后端时会自动：

1. 删除当前库中全部外键约束（表与表只保留逻辑关联，不再建 FK）
2. `create_all` 补齐缺失的表（含 RBAC 表）
3. 为学生表增加/加宽 `password_md5`，为 `sys_user` 增加 `teacher_id` 等
4. 种子：`admin` + RBAC 角色菜单；在 `ALLOW_DEFAULT_ADMIN=1` 时还有 `director`/`teacher`

演示 / mock 数据在 `data/` 目录，导入：

```bash
python data/seed_mock.py
```

详见 `data/README.md`。若先有教师数据再启后端，演示老师账号会自动关联首位教师及其班级。

## 启动后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

接口文档：http://127.0.0.1:8000/docs

登录页验证码依赖该服务。若只启动了 `admin`/`web`，页面会提示后端未启动，而不会把 Vite 代理错误刷满终端。

推荐在仓库根目录一次拉起后端和 B 端：

```bash
npm run dev
```

统一响应格式（B/C 端使用）：

```json
{ "code": "00000", "data": {}, "msg": "一切ok" }
```

## 启动 B 端后台

```bash
cd admin
npm install
npm run dev
```

访问 http://localhost:3000

已接入菜单：学生、班级、教师、成绩、就业、部门、顾问、统计分析、操作日志（按角色裁剪）。

## 启动 C 端门户

```bash
cd web
npm install
npm run dev
```

访问 http://localhost:5173

- 账号：学号（`stu_id`）
- 默认密码：`123456`（后台新增学生时自动写入）

## 自动化测试

```bash
pip install -r test/requirements.txt
python test/run_all.py          # 生成 test/report.md
# 或：npm test
```

详见 `test/README.md`。

## 说明

- 日期格式：纯日期 `YYYY-MM-DD`，日期时间 `YYYY-MM-DD HH:mm:ss`（后端 `utils/date_format.py`，前端 `@/constants/date`）
- 登录使用 JWT（HS256），代码在 `backend/jwt_auth/`：access 2 小时，refresh 7 天。
- 成绩表、顾问表原先的数据库外键已去掉，关联 ID 仍由接口层写入，查询用 JOIN，不再依赖数据库约束。
- 原有 `/student`、`/class` 等旧接口仍保留，新前台走 `/api/v1/sms/*` 与 `/api/v1/portal/*`。
- 若本地曾跑过旧种子菜单，RBAC 菜单不会自动重刷；需要时可清空 `sys_menu`/`sys_role_menu` 后重启后端重新种子。
