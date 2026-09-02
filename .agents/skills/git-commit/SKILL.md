---
name: git-commit
description: >-
  Enforce Conventional Commits for this repo: analyze staged diffs, choose
  type/scope, write concise commit messages, and run the safe commit workflow.
  Use when the user asks to commit, create a git commit, write a commit message,
  amend a commit, or mentions 提交 / commit / git commit.
---

# Git Commit 规范

为本仓库写 commit 时，必须遵循本 skill。仅在用户明确要求提交时才执行 `git commit`。

## 消息格式

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

规则：
- 第一行（header）不超过 72 字符
- `subject` 用祈使语气，说明**为什么/意图**，不以句号结尾
- `subject` 可用中文或英文；同一仓库内保持与近期历史一致（无历史时默认中文）
- header 与 body 之间空一行
- 禁止含糊文案：`update`、`fix bug`、`改一下`、`临时提交`

## Type（必选）

| type | 何时使用 |
|------|----------|
| `feat` | 新功能 |
| `fix` | 修复缺陷 |
| `docs` | 仅文档 |
| `style` | 格式/空格/分号等，不影响逻辑 |
| `refactor` | 重构，非功能非修复 |
| `perf` | 性能优化 |
| `test` | 增改测试 |
| `build` | 构建系统或依赖 |
| `ci` | CI 配置 |
| `chore` | 杂项维护（不属于以上） |
| `revert` | 回滚某次提交 |

一次提交只对应一个主 type。若改动跨多类，拆成多次提交，或选最能代表用户意图的 type。

## Scope（推荐）

按改动模块选用短 scope，常见值：

`auth` · `student` · `teacher` · `course` · `grade` · `class` · `user` · `api` · `ui` · `db` · `config` · `deps`

无明确模块时可省略 scope：`feat: 添加登录页`

## Body / Footer（按需）

- Body：补充动机、关键方案、副作用；每行建议 ≤100 字符
- Footer：
  - 破坏性变更：`BREAKING CHANGE: <说明>`
  - 关联议题：`Closes #123` / `Refs #123`

破坏性变更也可在 type 后加 `!`：`feat(api)!: 调整学生列表响应结构`

## 提交前工作流

按顺序执行（可并行读状态）：

1. `git status` — 看暂存/未跟踪文件
2. `git diff` 与 `git diff --staged` — 理解改动
3. `git log -8 --oneline` — 对齐本仓库文案风格
4. 拟定 type/scope/subject；必要时写 body
5. 暂存相关文件（不要 `git add .` 除非用户要求）；**绝不**暂存密钥类文件（`.env`、`credentials.json`、私钥等）
6. 提交（Windows PowerShell）：

```powershell
git commit -m @"
feat(student): 支持按学号精确查询

增加学号唯一索引校验，避免重复学号入库。
"@
```

7. `git status` 确认成功

## 安全约束

- 不修改 git config
- 不 `--no-verify` / 不跳过 hooks（除非用户明确要求）
- 不 `push --force`、不硬重置（除非用户明确要求）
- 不主动 `git push`（除非用户明确要求）
- 不用 `git commit --amend`，除非同时满足：用户要求或 hook 自动改写需纳入、且 HEAD 由本次对话创建、且未推送到远程
- 钩子失败：修复后**新建** commit，不要 amend 失败提交
- 无改动时不要空提交

## 好例子 / 坏例子

**好：**
```
feat(student): 新增学生分页列表接口
fix(auth): 修复 token 过期后未跳转登录
refactor(grade): 抽取成绩校验为独立服务
docs: 补充本地启动说明
```

**坏：**
```
update
fix bug
改代码
feat: 完成了学生模块的所有功能和一些修复以及文档更新
```

## 决策提示

- 只有文档 → `docs`
- 只有依赖/锁文件 → `build` 或 `chore(deps)`
- 行为不变的结构调整 → `refactor`
- 用户可见新能力 → `feat`
- 纠正错误行为 → `fix`
