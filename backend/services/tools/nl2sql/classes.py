"""班级名 / 编号 → student_base_info.class_id（= class_info.id）解析。"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from model.class_model import ClassInfo

_CN_NUM = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


@dataclass(frozen=True)
class ClassRef:
    id: int  # class_info.id / student.class_id
    code: str  # class_info.class_id 如 AI0720-01
    ordinal: int  # 按 id 排序后的序号（1-based）


def load_class_catalog(db: Session, *, limit: int = 50) -> list[ClassRef]:
    rows = (
        db.query(ClassInfo)
        .filter(ClassInfo.is_delete == 0)
        .order_by(ClassInfo.id.asc())
        .limit(limit)
        .all()
    )
    return [
        ClassRef(id=int(r.id), code=str(r.class_id), ordinal=i)
        for i, r in enumerate(rows, start=1)
    ]


def format_class_catalog_for_prompt(catalog: list[ClassRef]) -> str:
    if not catalog:
        return ""
    lines = [
        "班级对照（过滤时使用 student_base_info.class_id = 数字 id）：",
    ]
    for c in catalog:
        lines.append(f"- {c.ordinal}班 / {c.code} → class_id={c.id}")
    return "\n".join(lines)


def resolve_class_mentions(question: str, catalog: list[ClassRef]) -> list[ClassRef]:
    """从问句中解析提到的班级；无命中返回空列表。"""
    q = (question or "").strip()
    if not q or not catalog:
        return []

    by_id = {c.id: c for c in catalog}
    by_code = {c.code.lower(): c for c in catalog}
    by_ord = {c.ordinal: c for c in catalog}
    hit: dict[int, ClassRef] = {}

    # 精确班级编号
    for code, ref in by_code.items():
        if code and code in q.lower():
            hit[ref.id] = ref

    # 一班 / 二班 …
    for m in re.finditer(r"([一二两三四五六七八九十])\s*班", q):
        n = _CN_NUM.get(m.group(1))
        if n and n in by_ord:
            hit[by_ord[n].id] = by_ord[n]

    # 1班 / 第2班
    for m in re.finditer(r"第?\s*(\d{1,2})\s*班", q):
        n = int(m.group(1))
        if n in by_ord:
            hit[by_ord[n].id] = by_ord[n]
        elif n in by_id:
            hit[n] = by_id[n]

    # AI0720-01 类（已在 by_code；再兜底后缀）
    for m in re.finditer(r"AI\d+-0*(\d+)", q, flags=re.IGNORECASE):
        n = int(m.group(1))
        if n in by_ord:
            hit[by_ord[n].id] = by_ord[n]

    return list(hit.values())


def enrich_question_with_classes(question: str, catalog: list[ClassRef]) -> str:
    """为生成器附加班级映射提示。"""
    q = (question or "").strip()
    if not q:
        return q
    catalog_text = format_class_catalog_for_prompt(catalog)
    hits = resolve_class_mentions(q, catalog)
    parts = [q]
    if catalog_text:
        parts.append(catalog_text)
    if hits:
        mapped = "；".join(f"{h.ordinal}班/{h.code}→class_id={h.id}" for h in hits)
        parts.append(f"本题提到的班级：{mapped}。请用 student_base_info.class_id 过滤。")
    return "\n\n".join(parts)
