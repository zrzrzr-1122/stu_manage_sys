"""评测结果等价比较。"""
from __future__ import annotations

from typing import Any


def _norm_row(row: dict) -> dict:
    return {str(k).lower(): v for k, v in row.items()}


def _approx_eq(a: Any, b: Any, tol: float) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return a == b


def check_expected(actual_rows: list[dict], expected: dict) -> tuple[bool, str]:
    """返回 (ok, reason)。"""
    if not expected:
        return True, "no_expected"
    compare = expected.get("compare")
    tol = float(expected.get("tolerance") or 0.01)
    rows = [_norm_row(r) for r in actual_rows]

    if compare == "rows_set":
        keys = [str(k).lower() for k in (expected.get("keys") or [])]
        if not keys:
            return False, "rows_set missing keys"
        want = [_norm_row(r) for r in expected.get("rows") or []]

        def _key(r: dict) -> tuple:
            return tuple(r.get(k) for k in keys)

        got_set = sorted(_key(r) for r in rows)
        want_set = sorted(_key(r) for r in want)
        if got_set != want_set:
            return False, f"set mismatch got={got_set} want={want_set}"
        return True, "equiv_ok"

    if compare == "rows_approx":
        want = [_norm_row(r) for r in expected.get("rows") or []]
        if len(rows) != len(want):
            return False, f"row_count {len(rows)} != {len(want)}"
        for got, exp in zip(rows, want):
            for k, v in exp.items():
                if k not in got:
                    return False, f"missing field {k}"
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    if not _approx_eq(got[k], v, tol):
                        return False, f"{k}: {got[k]} !~ {v}"
                elif got[k] != v:
                    return False, f"{k}: {got[k]} != {v}"
        return True, "equiv_ok"

    if compare in ("scalar_approx", "scalar_exact"):
        field = str(expected.get("field") or "").lower()
        if not rows:
            return False, "empty result"
        got = rows[0].get(field)
        want = expected.get("value")
        if compare == "scalar_exact":
            try:
                if int(got) != int(want):  # type: ignore[arg-type]
                    return False, f"{field}: {got} != {want}"
            except (TypeError, ValueError):
                return False, f"{field}: {got} != {want}"
        elif not _approx_eq(got, want, tol):
            return False, f"{field}: {got} !~ {want}"
        return True, "equiv_ok"

    return False, f"unknown compare: {compare}"
