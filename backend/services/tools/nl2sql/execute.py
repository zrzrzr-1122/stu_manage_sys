"""只读执行受控 SQL。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.tools.nl2sql.schema import DEFAULT_ROW_LIMIT, METRICS, SENSITIVE_COLUMNS
from services.tools.nl2sql.validate import ValidationResult, validate_sql


class Nl2SqlExecuteError(Exception):
    pass


def execute_validated(
    db: Session,
    validated: ValidationResult,
) -> dict[str, Any]:
    try:
        # MySQL 8+: 单语句最大执行时间（毫秒）
        db.execute(text("SET SESSION MAX_EXECUTION_TIME=5000"))
    except Exception:
        pass
    try:
        result = db.execute(text(validated.sql))
        keys = list(result.keys())
        rows = result.fetchmany(validated.limit + 1)
        truncated = len(rows) > validated.limit
        rows = rows[: validated.limit]
        data = [dict(zip(keys, row)) for row in rows]
        # JSON 友好 + 抹除敏感列（含 SELECT *）
        safe_keys = [k for k in keys if str(k).lower() not in SENSITIVE_COLUMNS]
        for item in data:
            for k in list(item.keys()):
                if str(k).lower() in SENSITIVE_COLUMNS:
                    item.pop(k, None)
                    continue
                v = item[k]
                if hasattr(v, "isoformat"):
                    item[k] = v.isoformat()
                elif isinstance(v, (bytes, bytearray)):
                    item[k] = v.decode("utf-8", errors="replace")
        return {
            "ok": True,
            "sql": validated.sql,
            "tables": sorted(validated.tables),
            "row_count": len(data),
            "truncated": truncated,
            "columns": safe_keys,
            "rows": data,
            "metrics": METRICS,
            "scope_note": "已按白名单表只读执行；请确认含软删过滤条件。",
        }
    except Exception as e:
        raise Nl2SqlExecuteError(f"执行失败: {e}") from e


def run_sql(
    db: Session,
    sql: str,
    *,
    class_ids: list[int] | None = None,
    row_limit: int = DEFAULT_ROW_LIMIT,
) -> dict[str, Any]:
    validated = validate_sql(sql, class_ids=class_ids, row_limit=row_limit)
    return execute_validated(db, validated)
