"""成绩域受控资产与口径（NL2SQL MVP）。"""
from __future__ import annotations

from typing import Any

# 物理表白名单（小写）
ALLOWED_TABLES: frozenset[str] = frozenset(
    {
        "student_base_info",
        "ai0720score",
    }
)

# 表 → (软删列, 存活值)；validate 层强制注入
SOFT_DELETE_COLUMNS: dict[str, tuple[str, int]] = {
    "student_base_info": ("is_delete", 0),
    "ai0720score": ("is_deleted", 0),
}

# 表 → 软删条件文案（提示用）
SOFT_DELETE_HINTS: dict[str, str] = {
    "student_base_info": "is_delete = 0",
    "ai0720score": "is_deleted = 0",
}

# 含班级维度的表（老师范围校验 / 注入用）
TABLES_WITH_CLASS_ID: frozenset[str] = frozenset({"student_base_info"})

# 成绩表无 class_id，需 join student；策略上要求 scoped 查询涉及 score 时必须能关联到 class
SCORE_TABLE = "ai0720score"
STUDENT_TABLE = "student_base_info"

DEFAULT_ROW_LIMIT = 200
MAX_ROW_LIMIT = 500

# 禁止出现在 SELECT/WHERE 等位置的敏感列（即使表在白名单）
SENSITIVE_COLUMNS: frozenset[str] = frozenset({"password_md5", "password", "passwd"})

METRICS: dict[str, Any] = {
    "fail": "score < 60",
    "pass": "score >= 60",
    "excellent": "score >= 90",
    "exam_order": {
        "1": "第一次考核",
        "2": "第二次考核",
    },
}

SCHEMA_FOR_PROMPT = """
可查询表（只读）：
1) student_base_info(stu_id, stu_name, class_id, sex, age, major, education, is_delete)
   - 仅使用 is_delete = 0 的行；禁止 password 等敏感字段
2) ai0720score(id, stu_id, stu_name, exam_order, score, is_deleted)
   - 仅使用 is_deleted = 0 的行
   - exam_order: 1=第一次考核, 2=第二次考核
口径：不及格 score<60；及格 score>=60；优秀 score>=90。
按班级统计时请 JOIN student_base_info 并使用 class_id（数字 id，不是班级编号字符串）。
用户说「一班/二班」时，以系统附加的班级对照为准。
禁止无 ON 条件的多表关联。
禁止访问其它表；禁止 INSERT/UPDATE/DELETE/DDL；就业/薪资等非成绩域请拒答。
""".strip()
