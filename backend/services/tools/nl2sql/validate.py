"""NL2SQL SQL 策略校验（只读、白名单、可选班级范围）。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

from services.tools.nl2sql.schema import (
    ALLOWED_TABLES,
    DEFAULT_ROW_LIMIT,
    MAX_ROW_LIMIT,
    SCORE_TABLE,
    SENSITIVE_COLUMNS,
    SOFT_DELETE_COLUMNS,
    STUDENT_TABLE,
)


class Nl2SqlValidationError(Exception):
    pass


_FORBIDDEN_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.Command,
    exp.TruncateTable,
    exp.Grant,
    exp.Revoke,
)


@dataclass
class ValidationResult:
    sql: str
    tables: set[str] = field(default_factory=set)
    limit: int = DEFAULT_ROW_LIMIT


def _strip_trailing_semicolon(sql: str) -> str:
    return sql.strip().rstrip(";").strip()


def _collect_tables(node: exp.Expression) -> set[str]:
    names: set[str] = set()
    for table in node.find_all(exp.Table):
        name = (table.name or "").strip()
        if name:
            names.add(name.lower())
    return names


def _ensure_single_select(sql: str) -> exp.Expression:
    if ";" in sql.rstrip().rstrip(";"):
        raise Nl2SqlValidationError("禁止多语句 SQL")
    try:
        statements = sqlglot.parse(sql, read="mysql")
    except Exception as e:
        raise Nl2SqlValidationError(f"SQL 解析失败: {e}") from e
    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise Nl2SqlValidationError("仅允许单条 SELECT 语句")
    root = statements[0]
    if isinstance(root, _FORBIDDEN_TYPES):
        raise Nl2SqlValidationError("仅允许只读 SELECT 查询")
    # WITH ... SELECT / SELECT / UNION
    if not isinstance(root, (exp.Select, exp.Union, exp.With)):
        # Some parsers wrap differently
        if root.find(exp.Select) is None:
            raise Nl2SqlValidationError("仅允许 SELECT / WITH…SELECT")
    for bad in _FORBIDDEN_TYPES:
        if root.find(bad) is not None:
            raise Nl2SqlValidationError("检测到非只读操作，已拦截")
    return root


def _has_limit(node: exp.Expression) -> bool:
    return node.find(exp.Limit) is not None


def _inject_or_cap_limit(node: exp.Expression, limit: int) -> exp.Expression:
    """为最外层 SELECT 补 LIMIT；已有则压到不超过 max。"""
    select = node
    if isinstance(node, exp.With):
        select = node.this
    if isinstance(select, exp.Union):
        # wrap union
        wrapped = exp.select("*").from_(exp.Subquery(this=node.copy(), alias="_nl2sql_u"))
        wrapped = wrapped.limit(limit)
        return wrapped
    if isinstance(select, exp.Select):
        existing = select.args.get("limit")
        if existing is None:
            return select.limit(limit)
        # try read literal
        try:
            lit = existing.expression
            val = int(lit.this) if isinstance(lit, exp.Literal) else limit
            if val > limit:
                select = select.copy()
                select.set("limit", exp.Limit(expression=exp.Literal.number(limit)))
            return select
        except Exception:
            select = select.copy()
            select.set("limit", exp.Limit(expression=exp.Literal.number(limit)))
            return select
    wrapped = exp.select("*").from_(exp.Subquery(this=node.copy(), alias="_nl2sql_q"))
    return wrapped.limit(limit)


def _student_table_alias(node: exp.Expression) -> str | None:
    for table in node.find_all(exp.Table):
        if (table.name or "").lower() == STUDENT_TABLE:
            return table.alias_or_name
    return None


def _immediate_table_aliases(select: exp.Select) -> list[tuple[str, str]]:
    """当前 SELECT 直接 FROM/JOIN 的 (表名小写, alias)，不含子查询内表。"""
    out: list[tuple[str, str]] = []
    from_ = select.args.get("from_") or select.args.get("from")
    if from_ is not None and isinstance(from_.this, exp.Table):
        t = from_.this
        name = (t.name or "").strip().lower()
        if name:
            out.append((name, t.alias_or_name))
    for join in select.args.get("joins") or []:
        t = join.this
        if isinstance(t, exp.Table):
            name = (t.name or "").strip().lower()
            if name:
                out.append((name, t.alias_or_name))
    return out


def _soft_delete_cond_for_select(select: exp.Select) -> exp.Expression | None:
    parts: list[exp.Expression] = []
    for table_name, alias in _immediate_table_aliases(select):
        spec = SOFT_DELETE_COLUMNS.get(table_name)
        if not spec:
            continue
        col, alive = spec
        parts.append(exp.column(col, table=alias).eq(exp.Literal.number(alive)))
    if not parts:
        return None
    combined: exp.Expression = parts[0]
    for p in parts[1:]:
        combined = exp.and_(combined, p)
    return combined


def _inject_soft_delete(node: exp.Expression) -> exp.Expression:
    """对每个引用白名单表的 SELECT 强制 AND 软删条件。"""
    node = node.copy()
    for select in node.find_all(exp.Select):
        cond = _soft_delete_cond_for_select(select)
        if cond is None:
            continue
        existing = select.args.get("where")
        if existing is not None and existing.this is not None:
            select.set("where", exp.Where(this=exp.and_(existing.this, cond)))
        else:
            select.set("where", exp.Where(this=cond))
    return node


def _reject_sensitive_columns(node: exp.Expression) -> None:
    for col in node.find_all(exp.Column):
        name = (col.name or "").strip().lower()
        if name in SENSITIVE_COLUMNS:
            raise Nl2SqlValidationError(f"禁止访问敏感字段: {name}")
    # SELECT * 可能带出敏感列：成绩域允许 *，执行层再抹除；此处仅拦显式引用


def _reject_cartesian_joins(node: exp.Expression) -> None:
    for join in node.find_all(exp.Join):
        kind = (join.args.get("kind") or "").upper()
        if kind == "CROSS":
            raise Nl2SqlValidationError("禁止 CROSS JOIN / 笛卡尔积")
        if join.args.get("on") is None and join.args.get("using") is None:
            # INNER/LEFT 等无条件，或逗号连接
            raise Nl2SqlValidationError("禁止无连接条件的多表关联（笛卡尔积）")


def _scope_expression(node: exp.Expression, class_ids: list[int]) -> exp.Expression:
    """在引用 student_base_info 的查询上 AND class_id IN (...)。"""
    tables = _collect_tables(node)
    if STUDENT_TABLE not in tables:
        if SCORE_TABLE in tables:
            raise Nl2SqlValidationError(
                "老师权限下查询成绩必须 JOIN student_base_info，以便按班级过滤"
            )
        raise Nl2SqlValidationError("当前查询无法施加班级数据范围，已拦截")

    alias = _student_table_alias(node) or STUDENT_TABLE
    cond = exp.column("class_id", table=alias).isin(
        *[exp.Literal.number(i) for i in class_ids]
    )

    if isinstance(node, exp.With):
        inner = node.this
        if not isinstance(inner, exp.Select):
            raise Nl2SqlValidationError("暂不支持对该 WITH 查询施加班级范围")
        inner = inner.copy().where(cond)
        out = node.copy()
        out.set("this", inner)
        return out

    if isinstance(node, exp.Select):
        return node.copy().where(cond)

    if isinstance(node, exp.Union):
        raise Nl2SqlValidationError("老师权限下暂不支持 UNION 查询")

    raise Nl2SqlValidationError("无法为当前 SQL 施加班级范围")


def validate_sql(
    sql: str,
    *,
    class_ids: list[int] | None = None,
    row_limit: int = DEFAULT_ROW_LIMIT,
) -> ValidationResult:
    """
    class_ids:
      - None: 全校
      - []: 无权限
      - [..]: 老师范围，强制外包 class_id 过滤
    """
    if not sql or not sql.strip():
        raise Nl2SqlValidationError("SQL 不能为空")
    if class_ids is not None and len(class_ids) == 0:
        raise Nl2SqlValidationError("当前账号无可见班级，无法查询")

    cleaned = _strip_trailing_semicolon(sql)
    # 粗拦注释注入多语句
    if re.search(r";\s*\S", cleaned):
        raise Nl2SqlValidationError("禁止多语句 SQL")

    limit = max(1, min(int(row_limit or DEFAULT_ROW_LIMIT), MAX_ROW_LIMIT))
    root = _ensure_single_select(cleaned)
    tables = _collect_tables(root)
    if not tables:
        raise Nl2SqlValidationError("未识别到查询表")
    unknown = tables - ALLOWED_TABLES
    if unknown:
        raise Nl2SqlValidationError(f"非白名单表: {', '.join(sorted(unknown))}")

    _reject_sensitive_columns(root)
    _reject_cartesian_joins(root)

    root = _inject_soft_delete(root)

    if class_ids is not None:
        root = _scope_expression(root, class_ids)

    root = _inject_or_cap_limit(root, limit)
    final_sql = root.sql(dialect="mysql")
    return ValidationResult(sql=final_sql, tables=tables, limit=limit)
