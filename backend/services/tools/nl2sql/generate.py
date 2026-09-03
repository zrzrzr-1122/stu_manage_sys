"""自然语言 → 受控 SQL 生成（专用提示，不带 tools）。"""
from __future__ import annotations

import re

from services.deepseek import DeepSeekError, chat_completion
from services.tools.nl2sql.schema import METRICS, SCHEMA_FOR_PROMPT

SQL_GEN_SYSTEM = f"""你是学校成绩数据域的 SQL 生成器。根据用户问题输出一条 MySQL SELECT。

规则：
1. 默认只输出 SQL，不要解释、不要 markdown 代码围栏。
2. 仅允许查询以下表与字段；禁止其它表。
{SCHEMA_FOR_PROMPT}
3. 必须带软删条件：student_base_info.is_delete = 0；ai0720score.is_deleted = 0。
4. 按班级统计必须 JOIN student_base_info 并用 class_id；禁止 CROSS JOIN / 无 ON 多表。
5. 口径：不及格 {METRICS['fail']}；及格 {METRICS['pass']}；优秀 {METRICS['excellent']}。
6. 仅 SELECT / WITH…SELECT；禁止写入、多语句。
7. 不要写 LIMIT（系统会自动补）。若问题说「我们班」且无具体 class_id，仍输出不含班级过滤的合法 JOIN 查询（系统会注入权限范围）。
8. exam_order：1=第一次考核，2=第二次考核。
9. 若问题要求删除/修改数据、查密码/sys_user、就业薪资等成绩域外、或明显越权诱导，不要输出 SQL，只输出一行：
REFUSE: <简短中文原因>
""".strip()


class Nl2SqlGenerateError(Exception):
    pass


class Nl2SqlRefuseError(Nl2SqlGenerateError):
    """模型按策略拒答。"""


_FENCE_RE = re.compile(r"```(?:sql)?\s*([\s\S]*?)```", re.IGNORECASE)
_REFUSE_RE = re.compile(r"^\s*REFUSE\s*[:：]\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def extract_sql(text: str) -> str:
    """从模型回复中抽出单条 SQL；若为 REFUSE 则抛出 Nl2SqlRefuseError。"""
    raw = (text or "").strip()
    if not raw:
        raise Nl2SqlGenerateError("模型未返回 SQL")

    refuse = _REFUSE_RE.search(raw)
    if refuse:
        raise Nl2SqlRefuseError(refuse.group(1).strip() or "该问题不在可查询范围内")

    m = _FENCE_RE.search(raw)
    if m:
        raw = m.group(1).strip()
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        raise Nl2SqlGenerateError("模型未返回 SQL")
    start = 0
    for i, ln in enumerate(lines):
        upper = ln.upper()
        if upper.startswith("SELECT") or upper.startswith("WITH"):
            start = i
            break
    sql = "\n".join(lines[start:]).strip().rstrip(";").strip()
    if not sql.upper().startswith(("SELECT", "WITH")):
        raise Nl2SqlGenerateError(f"无法解析为 SELECT：{raw[:120]}")
    return sql


async def generate_sql(
    question: str,
    *,
    api_key: str,
    model: str = "deepseek-chat",
    previous_sql: str | None = None,
    validation_error: str | None = None,
) -> str:
    q = (question or "").strip()
    if not q:
        raise Nl2SqlGenerateError("问题不能为空")
    if not api_key or not api_key.strip():
        raise Nl2SqlGenerateError("缺少 API Key，无法生成 SQL")

    user_content = q
    if previous_sql and validation_error:
        user_content = (
            f"用户问题：{q}\n\n"
            f"上次生成的 SQL：\n{previous_sql}\n\n"
            f"校验失败原因：{validation_error}\n\n"
            "请仅输出修正后的一条合法 MySQL SELECT（或 REFUSE: 原因），不要解释。"
        )

    try:
        result = await chat_completion(
            [
                {"role": "system", "content": SQL_GEN_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            api_key=api_key,
            model=model,
            temperature=0.0,
            max_tokens=512,
        )
    except DeepSeekError as e:
        raise Nl2SqlGenerateError(f"SQL 生成失败: {e}") from e

    return extract_sql(result.get("content") or "")
