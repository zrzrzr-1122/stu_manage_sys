# 自动化测试

## 快速开始

先装依赖（只需一次）：

```bash
pip install -r test/requirements.txt
playwright install chromium   # 可选，浏览器 E2E
```

再用**两个终端**跑（前端冒烟 / E2E 需要服务已启动）：

```bash
# 终端 1：启动后端(8000) + B 端 admin(3000)
npm run dev

# 终端 2：执行测试并写入 report.md
npm test
```

只跑后端接口用例（不依赖 `npm run dev`）：

```bash
npm run test:backend
# 或
pytest test/backend -v
```

## 说明

- `npm test` 实际执行 `python test/run_all.py`，结果写入 `test/report.md`
- 未启动 `npm run dev` 时：后端 TestClient 用例仍会通过；前端冒烟 / E2E 会 **skip**，不算失败
- C 端门户冒烟还需另开 `npm run dev:web`（5173），可选

## 目录

```
test/
├── backend/           # FastAPI 登录与鉴权接口测试
├── frontend/          # 前端冒烟 + Playwright E2E
├── conftest.py
├── run_all.py         # 汇总执行并生成 report.md
├── report.md          # 最近一次测试报告
├── requirements.txt
└── README.md
```
