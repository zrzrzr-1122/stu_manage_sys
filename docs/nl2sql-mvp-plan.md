# 本仓库 NL2SQL MVP 实施清单

> 对齐 [`enterprise-nl2sql-plan.md`](./enterprise-nl2sql-plan.md) 的原则，缩减为本系统可落地的试点。  
> 首期数据域：**成绩（Score + Student）**  
> 接入方式：AI 助手 tool（`services/tools/`）

## 1. 目标（可验收）

用户用自然语言问成绩相关统计；系统在权限范围内生成并执行**只读**查询，返回：

- 结果数据（限行）
- 指标口径 / 数据范围说明
- 实际执行的 SQL（或等价解释）

**不以「能生成 SQL」为成功**；以评测集上的结果等价率 + 越权拦截为准。

## 2. 非目标（MVP 明确不做）

- 开放全库 / 原始敏感明细随便查
- 写入、更新、删除
- 跨域（就业 + 成绩混查）
- 完整企业语义平台、血缘、多租户网关
- `deepseek-reasoner` 挂 NL2SQL（仅 `deepseek-chat` + tools）

## 3. 架构（瘦身版）

```text
用户问题 (chat)
  → tool: query_data
  → 权限上下文 (AccessContext.class_ids)
  → Schema 裁剪（仅白名单视图/字段）
  → LLM 生成 SQL
  → AST / 策略校验（SELECT-only、白名单、强制班级过滤）
  → 只读执行（超时 + LIMIT）
  → 结果 + 口径 + SQL → 回填 tool → 模型组织回答
  → 审计落库
```

目录预留：

```text
backend/services/tools/
  weather.py
  registry.py
  nl2sql/                 # 后续实现
    __init__.py
    schema.py             # 受控资产与口径
    generate.py           # 提示与生成
    validate.py           # AST / 策略
    execute.py            # 只读执行
    tool.py               # query_data 工具定义与入口
```

## 4. 受控资产（成绩域）

建议先落 **SQL 视图或等价查询描述**（实现时可先用「白名单表 + 强制软删条件」）：

| 逻辑名 | 来源 | 说明 |
|--------|------|------|
| `v_student_active` | `student_base_info` | `is_delete = 0`；字段：stu_id, stu_name, class_id, sex, age, major… |
| `v_score_active` | `ai0720score` | `is_deleted = 0`；字段：stu_id, stu_name, exam_order, score |
| `v_score_with_student` | score ⋈ student | 成绩 + 班级；供按班聚合 |

**口径约定（写入语义清单）：**

- 不及格：`score < 60`
- 优秀：`score >= 90`（若业务另有定义再改）
- `exam_order`：`1` 第一次考核，`2` 第二次考核
- 老师：仅 `class_id IN (授权班级)`；超管/主任：全校

## 5. 权限策略

| 角色 | class_ids | NL2SQL 行为 |
|------|-----------|-------------|
| 超管 / 教导主任 | `None`（全校） | 可查成绩域白名单全范围 |
| 老师 | 具体班级列表 | 生成与校验都必须带班级过滤；空列表 → 拒答 |
| 学生门户 | 不开放 NL2SQL MVP | tool 对 student owner 直接拒绝或未注册 |

工具入口必须传入 `AccessContext`（天气工具无此要求；NL2SQL 必做）。

## 6. 实施阶段（本仓库日历）

| 阶段 | 内容 | 预估 |
|------|------|------|
| **P0** | 本文档 + 评测集 v0 + 受控资产清单 | 完成 |
| **P1** | `nl2sql` 包：校验器 + 只读执行器 + 审计 | 完成 |
| **P2** | LLM 生成 + `query_data` 注册进 `registry` | 完成 |
| **P3** | 对评测集跑通；修口径/提示；前端展示 SQL/口径（可简） | 完成（直播 25/25；软删注入；S01–S03 等价；SQL 面板落库；校验失败重试 1 次） |
| **P4** | 可选：就业域第二切片 | 另开 |

## 7. 安全底线（P1 必须具备）

- 仅单条 `SELECT` / `WITH … SELECT`
- 对象白名单；禁 `;` 多语句、禁写入函数
- 强制 `LIMIT`（如 200）与语句超时
- 老师查询：AST 层检查或自动注入 `class_id` 条件
- 失败：返回可读错误，不执行

## 8. 评测集

见 [`nl2sql-eval-scores.v0.json`](./nl2sql-eval-scores.v0.json)。

上线门槛建议（可调）：

- 核心简单聚合题结果等价率 ≥ 80%
- 越权题拦截率 = 100%
- 写操作 / 非白名单对象拦截率 = 100%

## 9. 下一步立刻可做

1. 评审评测集题目是否覆盖真实高频问法。  
2. 实现 `services/tools/nl2sql/` 的 validate + execute（可先不接 LLM，用手写 SQL 测策略）。  
3. 再接生成与 chat tool。
