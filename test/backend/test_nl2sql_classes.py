"""班级名解析单测（不依赖真实库数据形状时用假 catalog）。"""
from __future__ import annotations

from services.tools.nl2sql.classes import (
    ClassRef,
    enrich_question_with_classes,
    format_class_catalog_for_prompt,
    resolve_class_mentions,
)


def _catalog() -> list[ClassRef]:
    return [
        ClassRef(id=1, code="AI0720-01", ordinal=1),
        ClassRef(id=2, code="AI0720-02", ordinal=2),
        ClassRef(id=3, code="AI0720-03", ordinal=3),
    ]


def test_resolve_yi_ban():
    hits = resolve_class_mentions("一班第一次考核平均分？", _catalog())
    assert [h.id for h in hits] == [1]


def test_resolve_digit_ban():
    hits = resolve_class_mentions("对比1班和2班", _catalog())
    assert {h.id for h in hits} == {1, 2}


def test_resolve_code():
    hits = resolve_class_mentions("AI0720-03 的及格率", _catalog())
    assert [h.id for h in hits] == [3]


def test_enrich_includes_mapping():
    text = enrich_question_with_classes("一班平均分", _catalog())
    assert "class_id=1" in text
    assert "AI0720-01" in text


def test_format_catalog():
    text = format_class_catalog_for_prompt(_catalog())
    assert "1班" in text
    assert "class_id=2" in text
