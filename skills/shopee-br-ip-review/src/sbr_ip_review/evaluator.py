"""规则求值 —— 把 `rules/02_ip_trademark_copyright.json` 的规则跑在商品上。

判定语义（与 `tools/verify_fixtures.py` 保持一致，但本模块**自有实现**，
不 import 只读工具 —— 模块必须能独立测试）：

* `trigger_conditions` 之间是 **AND** 关系。
* `requires_input` 声明的输入字段缺失/为空 → 该条件**不评估**；
  整条规则记入 `unevaluated[]`（硬约束 H3），**不产生 result**。
* `any_text` = 标题 + 详情 + 品牌 + 类目 + 型号 + 图片 OCR 文本。
* `image_text` = 所有图片的 `ocr_text` 拼接。
* `image` + `has_nonempty` = 至少一张图片的 `detected_logos` 非空。

**空值语义**（PROJECT_RULES §11.1）：`null` / 空串 / 空数组 / 空对象 一律视为缺失。
"""

from __future__ import annotations

import re

#: 规则求值用的算子集合（与 `contracts/rule_envelope.schema.json` 的枚举一致）
SUPPORTED_OPERATORS = frozenset({
    "contains_any", "contains_all", "not_contains_any", "regex", "equals",
    "not_equals", "gt", "gte", "length_lt", "lt", "lte", "image_count_lt",
    "image_count_gte", "has_field", "has_nonempty", "field_missing",
    "history_missing_nonempty",
})

#: `history` 中承载授权材料清单的键
AUTHORIZATION_KEYS = ("authorization_documents", "missing")


def is_empty(value) -> bool:
    """PROJECT_RULES §11.1：存在但为空 == 缺失。"""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def get_field(product: dict, field: str):
    """按规则字段名取值。未知字段返回 `None`（视为缺失）。"""
    if field == "any_text":
        parts = [
            product.get("title") or "",
            product.get("description") or "",
            product.get("brand") or "",
            product.get("category") or "",
            product.get("model") or "",
        ]
        for image in product.get("images") or []:
            if image.get("ocr_text"):
                parts.append(image["ocr_text"])
        return "\n".join(p for p in parts if p)
    if field == "image_text":
        texts = [i.get("ocr_text") or "" for i in product.get("images") or []]
        return "\n".join(t for t in texts if t)
    if field == "image":
        return product.get("images")
    return product.get(field)


def condition_matches(product: dict, condition: dict):
    """判断单条触发条件。

    返回 `(matched, unevaluable, detail)`：

    * `matched` —— 条件是否成立
    * `unevaluable` —— 是否因缺少依赖输入而**无法评估**（硬约束 H3）
    * `detail` —— 命中片段（人可读），无则为空串
    """
    field = condition.get("field")
    operator = condition.get("operator")
    value = condition.get("value")
    case_sensitive = bool(condition.get("case_sensitive", False))

    if operator not in SUPPORTED_OPERATORS:
        raise ValueError(f"未知算子: {operator}")

    # --- requires_input：任一依赖字段缺失 → 该条件不评估 ---
    for required in condition.get("requires_input") or []:
        if is_empty(get_field(product, required)):
            return False, True, ""

    actual = get_field(product, field)

    # --- 存在性语义 ---
    if operator == "field_missing":
        return is_empty(actual), False, ""
    if operator == "has_field":
        return (not is_empty(actual)), False, ""
    if operator == "has_nonempty":
        if field == "image":
            hit = any((i.get("detected_logos") or []) for i in actual or [])
            return hit, False, ("图片中检出第三方 logo" if hit else "")
        return (not is_empty(actual)), False, ""

    # --- 其余算子需要实际值；缺失 → 无法评估 ---
    if is_empty(actual):
        return False, True, ""

    if operator == "regex":
        flags = 0 if case_sensitive else re.IGNORECASE
        match = re.search(value, actual, flags)
        if not match:
            return False, False, ""
        return True, False, _excerpt(actual, match.start(), match.end())

    if operator in ("contains_any", "contains_all"):
        needles = value if isinstance(value, list) else [value]
        if isinstance(actual, dict):
            keys = set(actual.keys())
            hits = [n for n in needles if n in keys]
            if operator == "contains_any":
                return (bool(hits), False, ", ".join(map(str, hits)))
            return (len(hits) == len(needles), False, ", ".join(map(str, hits)))
        haystack = actual if isinstance(actual, list) else [actual]
        hay = {str(x) for x in haystack}
        found = []
        for needle in needles:
            for item in hay:
                if needle == item or (
                    isinstance(actual, str) and str(needle).lower() in actual.lower()
                ):
                    found.append(str(needle))
                    break
        if operator == "contains_any":
            return (bool(found), False, ", ".join(found))
        return (len(found) == len(needles), False, ", ".join(found))

    if operator == "not_contains_any":
        matched, unevaluable, detail = condition_matches(
            product, {**condition, "operator": "contains_any"})
        if unevaluable:
            return False, True, ""
        return (not matched), False, ""

    if operator == "equals":
        return (actual == value), False, ""
    if operator == "not_equals":
        return (actual != value), False, ""
    if operator == "gt":
        return (actual > value), False, ""
    if operator == "gte":
        return (actual >= value), False, ""
    if operator == "lt":
        return (actual < value), False, ""
    if operator == "lte":
        return (actual <= value), False, ""
    if operator == "length_lt":
        return (len(str(actual)) < int(value)), False, ""
    if operator == "length_gte":
        return (len(str(actual)) >= int(value)), False, ""
    if operator == "image_count_lt":
        return (len(actual or []) < int(value)), False, ""
    if operator == "image_count_gte":
        return (len(actual or []) >= int(value)), False, ""
    if operator == "history_missing_nonempty":
        if not isinstance(actual, dict):
            return False, True, ""
        gaps = actual.get(value)
        if gaps is None:
            return False, False, ""
        if isinstance(gaps, (list, tuple, set)):
            return (len(gaps) > 0, False, ", ".join(map(str, gaps)))
        return (not is_empty(gaps), False, str(gaps))

    raise ValueError(f"未知算子: {operator}")


def evaluate_rule(product: dict, rule: dict):
    """求值单条规则。

    返回 `(fired, unevaluable, details, missing_fields)`：

    * `fired` —— 是否命中
    * `unevaluable` —— 是否因缺输入而无法评估
    * `details` —— `[{field, operator, excerpt}]`，命中片段
    * `missing_fields` —— 导致无法评估的依赖字段名
    """
    missing_fields: list[str] = []
    details: list[dict] = []
    unevaluable = False

    for condition in rule.get("trigger_conditions") or []:
        for required in condition.get("requires_input") or []:
            if is_empty(get_field(product, required)) and required not in missing_fields:
                missing_fields.append(required)
        matched, condition_unevaluable, detail = condition_matches(product, condition)
        if condition_unevaluable:
            unevaluable = True
            # 记录**条件自己依赖的字段** —— 否则复核者只看到
            # 「missing: unknown field」，不知道到底缺什么。
            field = condition.get("field")
            if field and field not in missing_fields:
                missing_fields.append(field)
            continue
        if not matched:
            return False, unevaluable, details, missing_fields
        details.append({
            "field": condition.get("field"),
            "operator": condition.get("operator"),
            "excerpt": detail,
        })

    if unevaluable:
        return False, True, details, missing_fields
    return True, False, details, missing_fields


def authorization_inventory(product: dict) -> dict:
    """读取 `history` 里的授权材料清单。

    返回 `{"provided": [...], "missing": [...], "known": bool}`。
    `known=False` 表示**根本没有授权清单** —— 无法判断是否已授权
    （既不能判「已授权」，也不能判「未授权」，只能记为未评估）。
    """
    history = product.get("history")
    if not isinstance(history, dict):
        return {"provided": [], "missing": [], "known": False}
    has_any = any(key in history for key in AUTHORIZATION_KEYS)
    provided = history.get("authorization_documents") or []
    missing = history.get("missing") or []
    if not isinstance(provided, list):
        provided = [provided]
    if not isinstance(missing, list):
        missing = [missing]
    return {
        "provided": [str(x) for x in provided],
        "missing": [str(x) for x in missing],
        "known": has_any,
    }


def _excerpt(text: str, start: int, end: int, pad: int = 40) -> str:
    low = max(0, start - pad)
    high = min(len(text), end + pad)
    prefix = "…" if low > 0 else ""
    suffix = "…" if high < len(text) else ""
    return prefix + text[low:high].replace("\n", " ") + suffix
