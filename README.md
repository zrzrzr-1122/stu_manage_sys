# 沃林学生管理系统

前后端分离的学生管理系统。后端沿用 FastAPI，B 端管理后台基于 [vue3-element-template](https://gitee.com/youlaiorg/vue3-element-template)，C 端学生门户基于 [Vuetify](https://github.com/vuetifyjs/vuetify)。

## 目录

```
backend/   FastAPI 接口（业务 + 有来脚手架适配层）
  jwt_auth/ JWT 登录独立模块（签发、校验、B/C 端登录）
admin/     B 端后台（Vue3 + Element Plus）
web/       C 端学生门户（Vue3 + Vuetify）
```

## 环境

- Python 3.10+
- Node.js 20+
- MySQL 8，库名 `yanjiusheng`（账号默认 `root / 123456`，可在 `backend/database.py` 修改）
- B 端推荐 pnpm，也可用 npm

## 数据库

启动后端时会自动：

1. 删除当前库中全部外键约束（表与表只保留逻辑关联，不再建 FK）
2. `create_all` 补齐缺失的表
3. 为学生表增加 `password_md5`，为部门表补齐 `phone`、`dstatus`
4. 若不存在管理员，则创建 `admin / 123456`

手工查看/删除外键可参考 `backend/sql/drop_foreign_keys.sql`。

演示 / mock 数据在 `data/` 目录，导入：

```bash
python data/seed_mock.py
```

详见 `data/README.md`。

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

- 账号：`admin`
- 密码：`123456`
- 验证码：按页面图片输入（后端实时生成）

已接入菜单：学生、班级、教师、成绩、就业、部门、顾问、统计分析。

## 启动 C 端门户

```bash
cd web
npm install
npm run dev
```

访问 http://localhost:5173

- 账号：学号（`stu_id`）
- 默认密码：`123456`（后台新增学生时自动写入）

学生可查看个人信息、成绩和就业进展，并可修改籍贯/专业/毕业学校。

## 自动化测试

```bash
pip install -r test/requirements.txt
python test/run_all.py          # 生成 test/report.md
# 或：npm test
```

详见 `test/README.md`。

## 说明

- 登录使用 JWT（HS256），代码在 `backend/jwt_auth/`：access 2 小时，refresh 7 天。密码仍按 MD5 存储校验。
- 成绩表、顾问表原先的数据库外键已去掉，关联 ID 仍由接口层写入，查询用 JOIN，不再依赖数据库约束。
- 原有 `/student`、`/class` 等旧接口仍保留，新前台走 `/api/v1/sms/*` 与 `/api/v1/portal/*`。
