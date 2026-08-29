"""
MySQL MCP Server for Cursor — read-only by default.

Env (optional, defaults match backend/database.py):
  MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
  MYSQL_ALLOW_WRITE=true  # allow INSERT/UPDATE/DELETE (still blocks DROP/TRUNCATE/ALTER)
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import pymysql
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mysql-yanjiusheng")

_WRITE_OK = os.getenv("MYSQL_ALLOW_WRITE", "false").lower() in ("1", "true", "yes")

_DANGEROUS = re.compile(
    r"\b(DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|FLUSH|LOAD\s+DATA|INTO\s+OUTFILE|"
    r"INTO\s+DUMPFILE|CALL|EXECUTE|PREPARE|SHUTDOWN|SET\s+GLOBAL)\b",
    re.IGNORECASE,
)
_WRITE = re.compile(r"\b(INSERT|UPDATE|DELETE|REPLACE)\b", re.IGNORECASE)


def _connect() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "123456"),
        database=os.getenv("MYSQL_DATABASE", "yanjiusheng"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def _assert_safe_sql(sql: str) -> None:
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    if len(statements) != 1:
        raise ValueError("Only a single SQL statement is allowed")
    stmt = statements[0]
    if _DANGEROUS.search(stmt):
        raise ValueError("DDL / privileged statements are not allowed")
    if not _WRITE_OK and _WRITE.search(stmt):
        raise ValueError(
            "Write operations are disabled. Set MYSQL_ALLOW_WRITE=true to enable "
            "INSERT/UPDATE/DELETE."
        )


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str, indent=2)


@mcp.tool()
def list_tables() -> str:
    """List all base tables in the current MySQL database."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT TABLE_NAME AS name, TABLE_ROWS AS approx_rows, TABLE_COMMENT AS comment
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
                """
            )
            return _json(cur.fetchall())


@mcp.tool()
def describe_table(table_name: str) -> str:
    """Describe columns of a table (name, type, null, key, default, comment)."""
    if not re.fullmatch(r"[A-Za-z0-9_]+", table_name):
        raise ValueError("Invalid table name")
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  COLUMN_NAME AS name,
                  COLUMN_TYPE AS type,
                  IS_NULLABLE AS nullable,
                  COLUMN_KEY AS `key`,
                  COLUMN_DEFAULT AS `default`,
                  EXTRA AS extra,
                  COLUMN_COMMENT AS comment
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
                """,
                (table_name,),
            )
            cols = cur.fetchall()
            if not cols:
                raise ValueError(f"Table not found: {table_name}")
            return _json(cols)


@mcp.tool()
def query(sql: str, limit: int = 100) -> str:
    """
    Run a SQL query against MySQL. Read-only (SELECT) by default.
    Results are capped by limit (max 500).
    """
    _assert_safe_sql(sql)
    limit = max(1, min(int(limit), 500))
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description is None:
                return _json({"affected_rows": cur.rowcount})
            rows = cur.fetchmany(limit)
            return _json({"row_count": len(rows), "rows": rows, "truncated": len(rows) >= limit})


@mcp.tool()
def ping() -> str:
    """Check MySQL connectivity and return current database name."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DATABASE() AS db, VERSION() AS version, NOW() AS now")
            return _json(cur.fetchone())


if __name__ == "__main__":
    mcp.run(transport="stdio")
