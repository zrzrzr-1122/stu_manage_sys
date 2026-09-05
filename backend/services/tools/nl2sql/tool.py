"""query_data 工具：自然语言/SQL → 校验 → 只读执行。"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from database import Session as DbSession
from dao import chat_dao
from services.tools.nl2sql.classes import enrich_question_with_classes, load_class_catalog
from services.tools.nl2sql.context import (
    get_nl2sql_api_key,
    get_nl2sql_audit_owner,
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

RESULT_PREVIEW_ROWS = 30
_OUR_CLASS_RE = re.compile(r"我们班|本班")

QUERY_DATA_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "query_data",
        "description": (
            "查询本校学生成绩相关统计与明细（只读，连接真实数据库）。"
            "用户问平均分、及格/不及格、优秀率、排名、名单等时必须调用本工具，禁止编造示例数据。"
            "优先根据数据范围说明直接生成单条 MySQL SELECT，填入 sql（可显著降低延迟）；"
            "若无法确定 SQL，则只填 question，由系统再生成。"
            "仅覆盖成绩域；天气请用 get_weather。"
            f"\n\n数据范围说明：\n{SCHEMA_FOR_PROMPT}"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "用户的中文数据查询问题",
                },
                "sql": {
                    "type": "string",
                    "description": "推荐：已确认的单条 MySQL SELECT；提供则跳过二次生成",
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
    rows = result.get("rows") or []
    if len(rows) > RESULT_PREVIEW_ROWS:
        result = dict(result)
        result["rows"] = rows[:RESULT_PREVIEW_ROWS]
        result["preview_truncated"] = True
    return result


def _write_audit(
    *,
    question: str | None,
    sql: str | None,
    class_ids: list[int] | None,
    ok: bool,
    refused: bool = False,
    generated: bool = False,
    retried: bool = False,
    row_count: int | None = None,
    latency_ms: int | None = None,
    error_message: str | None = None,
) -> None:
    owner_type, owner_id, conversation_id = get_nl2sql_audit_owner()
    if not owner_type or owner_id is None:
        return
    db = DbSession()
    try:
        chat_dao.add_nl2sql_log(
            db,
            owner_type=owner_type,
            owner_id=int(owner_id),
            conversation_id=conversation_id,
            question=question,
            sql_text=sql,
            class_ids=class_ids,
            ok=ok,
            refused=refused,
            generated=generated,
            retried=retried,
            row_count=row_count,
            latency_ms=latency_ms,
            error_message=error_message,
        )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


def _clarify_our_class(question: str, class_ids: list[int] | None) -> str | None:
    if not _OUR_CLASS_RE.search(question or ""):
        return None
    if class_ids is None:
        return "当前账号可见全校班级。请明确班级（如「一班」或 class_id），不要使用「我们班」。"
    if len(class_ids) == 0:
        return "当前账号无可见班级，无法查询。"
    if len(class_ids) > 1:
        return (
            f"您名下有多个班级 {class_ids}，请明确其中一个（如「一班」或 class_id={class_ids[0]}），"
            "不要单独使用「我们班」。"
        )
    return None


async def execute_query_data_tool(arguments: dict[str, Any] | str | None) -> str:
    started = time.perf_counter()
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

    try:
        class_ids = get_nl2sql_class_ids()
    except RuntimeError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    clarify = _clarify_our_class(question, class_ids)
    if clarify and not sql:
        _write_audit(
            question=question,
            sql=None,
            class_ids=class_ids if isinstance(class_ids, list) else None,
            ok=False,
            refused=True,
            error_message=clarify,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        return json.dumps(
            {"ok": False, "refused": True, "error": clarify, "question": question},
            ensure_ascii=False,
        )

    # 老师单班「我们班」：自动附加 class_id 提示
    if (
        question
        and _OUR_CLASS_RE.search(question)
        and isinstance(class_ids, list)
        and len(class_ids) == 1
    ):
        question = f"{question}（本班 class_id={class_ids[0]}）"

    generated = False
    retried = False
    api_key = get_nl2sql_api_key() if not sql else None
    gen_question = question

    if not sql:
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
            _write_audit(
                question=question,
                sql=None,
                class_ids=class_ids if isinstance(class_ids, list) else None,
                ok=False,
                refused=True,
                generated=True,
                error_message=str(e),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
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
            _write_audit(
                question=question,
                sql=None,
                class_ids=class_ids if isinstance(class_ids, list) else None,
                ok=False,
                generated=True,
                error_message=str(e),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            return json.dumps({"ok": False, "error": str(e), "question": question}, ensure_ascii=False)

    db = DbSession()
    try:
        try:
            result = run_sql(db, sql, class_ids=class_ids, row_limit=limit)
        except Nl2SqlValidationError as e:
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
                _write_audit(
                    question=question,
                    sql=sql,
                    class_ids=class_ids if isinstance(class_ids, list) else None,
                    ok=False,
                    refused=True,
                    generated=True,
                    retried=True,
                    error_message=str(refuse_err),
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
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
                _write_audit(
                    question=question,
                    sql=sql,
                    class_ids=class_ids if isinstance(class_ids, list) else None,
                    ok=False,
                    generated=True,
                    retried=True,
                    error_message=str(retry_err),
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
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
        latency_ms = int((time.perf_counter() - started) * 1000)
        _write_audit(
            question=question,
            sql=result.get("sql") or sql,
            class_ids=class_ids if isinstance(class_ids, list) else None,
            ok=True,
            generated=generated,
            retried=retried,
            row_count=result.get("row_count"),
            latency_ms=latency_ms,
        )
        return json.dumps(_preview_result(result), ensure_ascii=False, default=str)
    except (Nl2SqlValidationError, Nl2SqlExecuteError) as e:
        _write_audit(
            question=question,
            sql=sql,
            class_ids=class_ids if isinstance(class_ids, list) else None,
            ok=False,
            generated=generated,
            retried=retried,
            error_message=str(e),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
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
        _write_audit(
            question=question,
            sql=sql,
            class_ids=class_ids if isinstance(class_ids, list) else None,
            ok=False,
            generated=generated,
            retried=retried,
            error_message=str(e),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        return json.dumps({"ok": False, "error": f"查询异常: {e}"}, ensure_ascii=False)
    finally:
        db.close()
