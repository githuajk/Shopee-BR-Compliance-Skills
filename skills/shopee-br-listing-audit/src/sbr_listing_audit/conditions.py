"""触发条件求值 —— 规则层唯一的判定入口。

语义与 `tools/verify_fixtures.py` 的 `cond_matches()` **逐条对齐**，
因为共享夹具的 `must_fire` / `must_not_fire` / `must_be_unevaluated`
就是本模块的对外判定契约。

返回三态而不是布尔：

* `MATCH` —— 条件成立
* `NO_MATCH` —— 条件不成立（**这不等于「通过」**，只是本条件没命中）
* `UNEVALUATED` —— 因依赖字段缺失而**无法评估**（硬约束 H3）

`unevaluated` 绝不降级为 `no_match`：缺输入不是合规。
"""

from __future__ import annotations

import re
from typing import Any

from .fields import get_field, is_empty

MATCH = "match"
NO_MATCH = "no_match"
UNEVALUATED = "unevaluated"

#: 命中片段在上下文里保留的前后长度（字符）。
EXCERPT_PAD = 40

#: 命中片段的最大长度（字符）—— 防止把整段详情塞进结果。
EXCERPT_MAX = 160


class ConditionError(Exception):
    """规则里的算子或正则无法求值 —— 视为规则错误，不得静默当作不命中。"""


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "\n".join(str(item) for item in value)
    if isinstance(value, dict):
        return "\n".join(f"{k}: {v}" for k, v in value.items())
    return str(value)


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConditionError(f"operand {value!r} is not an integer") from exc


def _excerpt(text: str, start: int, end: int) -> str:
    """命中片段的可读上下文（带省略号，限长）。"""
    lo = max(0, start - EXCERPT_PAD)
    hi = min(len(text), end + EXCERPT_PAD)
    prefix = "…" if lo > 0 else ""
    suffix = "…" if hi < len(text) else ""
    body = text[lo:hi].replace("\n", " ").strip()
    return (prefix + body + suffix)[:EXCERPT_MAX]


def evaluate_condition(product: dict, condition: dict) -> dict:
    """求值单条触发条件。

    返回 `{"status", "field", "operator", "matched", "excerpt"}`。
    `matched` / `excerpt` 在非文本算子下为 `None`。
    """
    field = str(condition.get("field") or "")
    operator = str(condition.get("operator") or "")
    operand = condition.get("value")
    case_sensitive = bool(condition.get("case_sensitive", False))

    detail = {
        "status": NO_MATCH,
        "field": field,
        "operator": operator,
        "matched": None,
        "excerpt": None,
    }

    # --- H3 前置：requires_input 声明的依赖字段缺失 → 无法评估 ---
    for required in condition.get("requires_input") or []:
        if is_empty(get_field(product, str(required))):
            detail["status"] = UNEVALUATED
            return detail

    actual = get_field(product, field)

    # --- 存在性语义：不依赖取值本身 ---
    if operator == "field_missing":
        detail["status"] = MATCH if is_empty(actual) else NO_MATCH
        if detail["status"] == MATCH:
            detail["matched"] = f"field '{field}' is missing or empty"
            detail["excerpt"] = detail["matched"]
        return detail
    if operator == "has_field":
        detail["status"] = MATCH if not is_empty(actual) else NO_MATCH
        if detail["status"] == MATCH:
            detail["matched"] = f"field '{field}' is present"
            detail["excerpt"] = detail["matched"]
        return detail
    if operator == "has_nonempty":
        if field == "image":
            hit = any(
                isinstance(image, dict) and bool(image.get("detected_logos"))
                for image in (actual or [])
            )
            detail["status"] = MATCH if hit else NO_MATCH
            if hit:
                detail["matched"] = "image(s) carry detected logo candidates"
                detail["excerpt"] = detail["matched"]
            return detail
        detail["status"] = MATCH if not is_empty(actual) else NO_MATCH
        if detail["status"] == MATCH:
            detail["matched"] = f"field '{field}' is present"
            detail["excerpt"] = detail["matched"]
        return detail

    # --- 计数语义 ---
    if operator == "image_count_lt":
        if actual is None:
            detail["status"] = UNEVALUATED
            return detail
        count = len(actual or [])
        detail["status"] = MATCH if count < _as_int(operand) else NO_MATCH
        detail["matched"] = f"{count} image(s) < required {operand}"
        detail["excerpt"] = detail["matched"]
        return detail
    if operator == "image_count_gte":
        if actual is None:
            detail["status"] = UNEVALUATED
            return detail
        count = len(actual or [])
        detail["status"] = MATCH if count >= _as_int(operand) else NO_MATCH
        detail["matched"] = f"{count} image(s) >= required {operand}"
        detail["excerpt"] = detail["matched"]
        return detail

    # --- 其余算子需要实际值；缺失 → 无法评估（H3）---
    if is_empty(actual):
        detail["status"] = UNEVALUATED
        return detail

    if operator == "regex":
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(str(operand), flags)
        except re.error as exc:
            raise ConditionError(
                f"rule regex does not compile: {exc}; pattern={operand!r}"
            ) from exc
        text = _as_text(actual)
        match = pattern.search(text)
        if match:
            detail["status"] = MATCH
            detail["matched"] = match.group(0)
            detail["excerpt"] = _excerpt(text, match.start(), match.end())
        return detail

    if operator == "contains_any":
        hit = _contains_any(actual, operand)
        detail["status"] = MATCH if hit else NO_MATCH
        if hit:
            detail["matched"] = _matched_terms(actual, operand)
            detail["excerpt"] = detail["matched"]
        return detail

    if operator == "contains_all":
        hit = _contains_all(actual, operand)
        detail["status"] = MATCH if hit else NO_MATCH
        if hit:
            detail["matched"] = _matched_terms(actual, operand)
            detail["excerpt"] = detail["matched"]
        return detail

    if operator == "not_contains_any":
        detail["status"] = NO_MATCH if _contains_any(actual, operand) else MATCH
        if detail["status"] == MATCH:
            detail["matched"] = "none of the listed values are present"
            detail["excerpt"] = detail["matched"]
        return detail

    if operator == "equals":
        detail["status"] = MATCH if actual == operand else NO_MATCH
        if detail["status"] == MATCH:
            detail["matched"] = _as_text(actual)
            detail["excerpt"] = detail["matched"]
        return detail
    if operator == "not_equals":
        detail["status"] = MATCH if actual != operand else NO_MATCH
        if detail["status"] == MATCH:
            detail["matched"] = _as_text(actual)
            detail["excerpt"] = detail["matched"]
        return detail

    if operator == "gt":
        detail["status"] = MATCH if _numeric(actual) > _numeric(operand) else NO_MATCH
        return detail
    if operator == "gte":
        detail["status"] = MATCH if _numeric(actual) >= _numeric(operand) else NO_MATCH
        return detail
    if operator == "lt":
        detail["status"] = MATCH if _numeric(actual) < _numeric(operand) else NO_MATCH
        return detail
    if operator == "lte":
        detail["status"] = MATCH if _numeric(actual) <= _numeric(operand) else NO_MATCH
        return detail

    if operator == "length_lt":
        length = len(_as_text(actual))
        detail["status"] = MATCH if length < _as_int(operand) else NO_MATCH
        detail["matched"] = f"length {length} < {operand}"
        detail["excerpt"] = detail["matched"]
        return detail
    if operator == "length_gte":
        length = len(_as_text(actual))
        detail["status"] = MATCH if length >= _as_int(operand) else NO_MATCH
        detail["matched"] = f"length {length} >= {operand}"
        detail["excerpt"] = detail["matched"]
        return detail

    if operator == "history_missing_nonempty":
        if not isinstance(actual, dict):
            detail["status"] = UNEVALUATED
            return detail
        gaps = actual.get(operand)
        if gaps is None:
            detail["status"] = NO_MATCH
            return detail
        if isinstance(gaps, (list, tuple, set)):
            detail["status"] = MATCH if len(gaps) > 0 else NO_MATCH
        else:
            detail["status"] = NO_MATCH if is_empty(gaps) else MATCH
        if detail["status"] == MATCH:
            detail["matched"] = f"history['{operand}'] is non-empty"
            detail["excerpt"] = detail["matched"]
        return detail

    raise ConditionError(f"unknown operator: {operator!r}")


def _numeric(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError) as exc:
        raise ConditionError(f"value {value!r} is not numeric") from exc


def _needles(operand: Any) -> list[str]:
    if isinstance(operand, list):
        return [str(item) for item in operand]
    return [str(operand)]


def _contains_any(actual: Any, operand: Any) -> bool:
    """`contains_any` 的语义。

    * `actual` 是字典 → 语义是「含指定**键**」（`history` 类字段）。
    * `actual` 是列表 → 元素命中即成立。
    * `actual` 是字符串 → 子串命中即成立（忽略大小写）。
    """
    needles = _needles(operand)
    if isinstance(actual, dict):
        keys = set(actual.keys())
        return any(needle in keys for needle in needles)
    if isinstance(actual, (list, tuple)):
        haystack = {str(item) for item in actual}
        return any(needle in haystack for needle in needles)
    text = str(actual).lower()
    return any(needle.lower() in text for needle in needles)


def _contains_all(actual: Any, operand: Any) -> bool:
    needles = _needles(operand)
    if isinstance(actual, dict):
        keys = set(actual.keys())
        return all(needle in keys for needle in needles)
    if isinstance(actual, (list, tuple)):
        haystack = {str(item) for item in actual}
        return all(needle in haystack for needle in needles)
    text = str(actual).lower()
    return all(needle.lower() in text for needle in needles)


def _matched_terms(actual: Any, operand: Any) -> str:
    needles = _needles(operand)
    if isinstance(actual, dict):
        present = [needle for needle in needles if needle in actual]
        return "key(s): " + ", ".join(present) if present else "key(s) present"
    if isinstance(actual, (list, tuple)):
        haystack = {str(item) for item in actual}
        present = [needle for needle in needles if needle in haystack]
        return "value(s): " + ", ".join(present) if present else "value(s) present"
    text = str(actual)
    lower = text.lower()
    present = [needle for needle in needles if needle.lower() in lower]
    return "term(s): " + ", ".join(present) if present else "term(s) present"
