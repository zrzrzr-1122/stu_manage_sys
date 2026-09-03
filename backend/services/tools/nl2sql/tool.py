"""query_data 工具：自然语言/SQL → 校验 → 只读执行。"""
from __future__ import annotations

import json
from typing import Any

from database import Session as DbSession
from services.tools.nl2sql.classes import enrich_question_with_classes, load_class_catalog
from services.tools.nl2sql.context import (
    get_nl2sql_api_key,
    get_nl2sql_class_ids,
    nl2sql_enabled,
)
from services.tools.nl2sql.execute import Nl2SqlExecuteError, run_sql
from services.tools.nl2sql.generate import (
    Nl2SqlGenerateError,
    Nl2SqlRefuseError,
    generate_sql,
)
from services.tools.nl2sql.schema import DEFAULT_ROW_LIMIT, SCHEMA_FOR_PROMPT
from services.tools.nl2sql.validate import Nl2SqlValidationError

# 落库/前端展示的结果行上限（完整执行仍用 row_limit）
RESULT_PREVIEW_ROWS = 30

QUERY_DATA_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "query_data",
        "description": (
            "查询学生成绩相关统计与明细（只读）。"
            "传入用户的数据问题（question），由系统生成并执行受控 SQL；"
            "不要自己编写 SQL，除非用户明确给出了 SQL。"
            "仅覆盖成绩域；天气请用 get_weather。"
            f"\n\n数据范围说明：\n{SCHEMA_FOR_PROMPT}"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "用户的中文数据查询问题，如「第二次考核全校平均分」",
                },
                "sql": {
                    "type": "string",
                    "description": "可选：已确认的单条 MySQL SELECT；若提供则跳过生成",
                },
                "row_limit": {
                    "type": "integer",
                    "description": f"返回行数上限，默认 {DEFAULT_ROW_LIMIT}，最大 500",
                },
            },
            "required": ["question"],
        },
    },
}


def summarize_query_data_from_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从 tool loop 消息中抽取 query_data 结果摘要，供前端展示 SQL/口径。"""
    summaries: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") != "tool":
            continue
        raw = msg.get("content") or ""
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        if not any(k in data for k in ("sql", "tables", "metrics", "generated")):
            continue
        summaries.append(
            {
                "ok": data.get("ok"),
                "question": data.get("question"),
                "sql": data.get("sql"),
                "row_count": data.get("row_count"),
                "truncated": data.get("truncated"),
                "metrics": data.get("metrics"),
                "scope_note": data.get("scope_note"),
                "error": data.get("error"),
                "generated": data.get("generated"),
                "retried": data.get("retried"),
                "tables": data.get("tables"),
                "columns": data.get("columns"),
                "rows": data.get("rows"),
            }
        )
    return summaries


def _preview_result(result: dict[str, Any]) -> dict[str, Any]:
    """裁剪 rows，避免 tool/落库体积过大。"""
    rows = result.get("rows") or []
    if len(rows) > RESULT_PREVIEW_ROWS:
        result = dict(result)
        result["rows"] = rows[:RESULT_PREVIEW_ROWS]
        result["preview_truncated"] = True
    return result


async def execute_query_data_tool(arguments: dict[str, Any] | str | None) -> str:
    if not nl2sql_enabled.get():
        return json.dumps({"error": "当前账号未开放数据查询工具"}, ensure_ascii=False)

    try:
        if isinstance(arguments, str):
            args = json.loads(arguments) if arguments.strip() else {}
        else:
            args = dict(arguments or {})
    except json.JSONDecodeError:
        return json.dumps({"error": "工具参数不是合法 JSON"}, ensure_ascii=False)

    question = str(args.get("question") or "").strip()
    sql = str(args.get("sql") or "").strip()
    row_limit = args.get("row_limit")
    try:
        limit = int(row_limit) if row_limit is not None else DEFAULT_ROW_LIMIT
    except (TypeError, ValueError):
        limit = DEFAULT_ROW_LIMIT

    if not sql and not question:
        return json.dumps(
            {"error": "请提供 question（或已确认的 sql）"},
            ensure_ascii=False,
        )

    generated = False
    retried = False
    api_key = get_nl2sql_api_key() if not sql else None
    gen_question = question

    if not sql:
        # 班级名解析：附加对照表后再生成
        db_map = DbSession()
        try:
            catalog = load_class_catalog(db_map)
            gen_question = enrich_question_with_classes(question, catalog)
        except Exception:
            gen_question = question
        finally:
            db_map.close()

        try:
            sql = await generate_sql(gen_question, api_key=api_key or "")
            generated = True
        except Nl2SqlRefuseError as e:
            return json.dumps(
                {
                    "ok": False,
                    "refused": True,
                    "error": str(e),
                    "question": question,
                    "metrics": None,
                },
                ensure_ascii=False,
            )
        except Nl2SqlGenerateError as e:
            return json.dumps({"ok": False, "error": str(e), "question": question}, ensure_ascii=False)

    try:
        class_ids = get_nl2sql_class_ids()
    except RuntimeError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    db = DbSession()
    try:
        try:
            result = run_sql(db, sql, class_ids=class_ids, row_limit=limit)
        except Nl2SqlValidationError as e:
            # 仅自动生成路径：把校验错误回灌，再生成一次
            if not generated or not question or not api_key:
                raise
            try:
                sql = await generate_sql(
                    gen_question or question,
                    api_key=api_key,
                    previous_sql=sql,
                    validation_error=str(e),
                )
                retried = True
                result = run_sql(db, sql, class_ids=class_ids, row_limit=limit)
            except Nl2SqlRefuseError as refuse_err:
                return json.dumps(
                    {
                        "ok": False,
                        "refused": True,
                        "error": str(refuse_err),
                        "question": question,
                        "retried": True,
                    },
                    ensure_ascii=False,
                )
            except (Nl2SqlGenerateError, Nl2SqlValidationError, Nl2SqlExecuteError) as retry_err:
                return json.dumps(
                    {
                        "ok": False,
                        "error": str(retry_err),
                        "question": question,
                        "sql": sql,
                        "generated": True,
                        "retried": True,
                    },
                    ensure_ascii=False,
                )

        result["question"] = question or None
        result["generated"] = generated
        result["retried"] = retried
        return json.dumps(_preview_result(result), ensure_ascii=False, default=str)
    except (Nl2SqlValidationError, Nl2SqlExecuteError) as e:
        return json.dumps(
            {
                "ok": False,
                "error": str(e),
                "question": question or None,
                "sql": sql,
                "generated": generated,
                "retried": retried,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"ok": False, "error": f"查询异常: {e}"}, ensure_ascii=False)
    finally:
        db.close()
