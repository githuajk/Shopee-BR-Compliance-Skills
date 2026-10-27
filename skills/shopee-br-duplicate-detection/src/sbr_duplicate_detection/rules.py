"""规则装载与触发条件求值。

本模块**不拥有**规则文本的最终解释权 —— 规则住在 `rules/` 下，由
`shopee-br-listing-audit` / `shopee-br-duplicate-detection` 各自拥有。
本文件只做三件事：

1. **装载** —— 从 `rules/03_listing_violations_duplicates.json` 取 `DUP`
   前缀、从 `rules/04_cases_relist_authorization.json` 取 `RL`/`AU`/`AC`
   前缀；`SkillInput.rules[]` 里的规则信封可覆盖同名规则。
2. **归一** —— 规则库用 `decision`/`source_tier`/`source_excerpt`，规则信封
   用 `action`/`source.{tier,excerpt}`，这里统一成内部结构。
3. **求值** —— 按 `data/schema/rule.schema.json` 的算子语义判断规则是否
   命中，并区分「不命中」与「因缺输入而无法评估」（硬约束 H3）。

**哨兵触发（sentinel）**：重复/重发类规则无法用文本模式表达 —— 判定结果
来自跨记录比较。因此规则里写的是一个占位记号（如 `__DUPLICATE_SIGNAL__`），
由本模块的检测引擎在算出结论后注入，再交给规则决定严重度、动作与所需
证据。**注入由引擎负责，规则文本不被改写。**
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from .errors import (
    STAGE_RULE_LOADING,
    SEVERITY_ERROR,
    SEVERITY_FATAL,
    SEVERITY_WARNING,
)
from .normalize import flatten_value, norm_text

__all__ = [
    "OWNED_PREFIXES",
    "RULE_FILES",
    "load_rules",
    "RuleSet",
    "evaluate_rule",
    "get_field",
    "sentinel_tokens",
    "normalize_rule",
]

#: 本模块拥有的规则前缀。
OWNED_PREFIXES = ("DUP", "RL", "AU", "AC")

#: 前缀 → 规则文件（仓库根相对）。`rules/03` 里混有 `LV` 前缀（归
#: listing-audit），本模块只取 `DUP` 部分，**不改写该文件**。
RULE_FILES = {
    "DUP": "rules/03_listing_violations_duplicates.json",
    "RL": "rules/04_cases_relist_authorization.json",
    "AU": "rules/04_cases_relist_authorization.json",
    "AC": "rules/04_cases_relist_authorization.json",
}

_SENTINEL_RE = re.compile(r"^__[A-Z0-9_]+__$")


def _repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    # .../skills/shopee-br-duplicate-detection/src/sbr_duplicate_detection/rules.py
    return os.path.abspath(os.path.join(here, "..", "..", "..", ".."))


def sentinel_tokens(rule: dict) -> list[str]:
    """取规则触发条件里出现的哨兵记号。"""
    out: list[str] = []
    for cond in rule.get("trigger_conditions") or []:
        value = cond.get("value")
        if isinstance(value, str) and _SENTINEL_RE.match(value):
            out.append(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and _SENTINEL_RE.match(item):
                    out.append(item)
    return out


def normalize_rule(raw: dict) -> dict:
    """把规则库条目或规则信封统一成内部结构。"""
    source = raw.get("source") or {}
    tier = raw.get("source_tier") or source.get("tier") or "unverified"
    url = raw.get("source_url") or source.get("url") or ""
    excerpt = raw.get("source_excerpt")
    if excerpt is None:
        excerpt = source.get("excerpt")
    last_verified = raw.get("last_verified") or source.get("last_verified")
    action = raw.get("action") or raw.get("decision") or "flag_for_review"
    return {
        "rule_id": raw.get("rule_id"),
        "title": raw.get("title"),
        "category": raw.get("category"),
        "description": raw.get("description"),
        "severity": raw.get("severity", "medium"),
        "action": action,
        "status": raw.get("status", "active"),
        "version": raw.get("version", 1),
        "evidence_required": list(raw.get("evidence_required") or []),
        "human_review_required": bool(raw.get("human_review_required",
                                             raw.get("requires_human_review", True))),
        "trigger_conditions": list(raw.get("trigger_conditions") or []),
        "source_tier": tier,
        "source_url": url,
        "source_excerpt": excerpt,
        "last_verified": last_verified,
        "notes": raw.get("notes"),
    }


def load_rules(root: str | None = None, envelopes=None,
               error_log=None) -> list[dict]:
    """装载本模块拥有的规则。

    ``envelopes`` —— `SkillInput.rules[]` 提供的规则信封（可选）。同
    `rule_id` 的信封**覆盖**文件里的规则（调用方有权用自己的版本覆盖），
    其它前缀的规则被忽略（不是本模块的职责）。
    """
    root = root or _repo_root()
    rules: dict[str, dict] = {}

    for prefix, rel in RULE_FILES.items():
        path = os.path.join(root, rel)
        try:
            with open(path, encoding="utf-8") as handle:
                doc = json.load(handle)
        except FileNotFoundError:
            if error_log is not None:
                error_log.fatal(
                    STAGE_RULE_LOADING,
                    f"rule file is missing: {rel}",
                    {"path": rel, "prefix": prefix},
                )
            continue
        except (OSError, ValueError) as exc:
            if error_log is not None:
                error_log.fatal(
                    STAGE_RULE_LOADING,
                    f"rule file could not be parsed: {rel}: {exc}",
                    {"path": rel, "prefix": prefix},
                )
            continue
        for raw in doc.get("rules") or []:
            rule_id = raw.get("rule_id") or ""
            if not rule_id.startswith(f"SBR-{prefix}-"):
                continue  # 不是本模块的前缀 —— 不评价、不改写
            rules[rule_id] = normalize_rule(raw)

    for envelope in envelopes or []:
        rule_id = envelope.get("rule_id")
        if not rule_id:
            continue
        if not any(rule_id.startswith(f"SBR-{p}-") for p in OWNED_PREFIXES):
            continue
        rules[rule_id] = normalize_rule(envelope)

    return [rules[key] for key in sorted(rules)]


class RuleSet:
    """本模块可用的规则集合。"""

    def __init__(self, rules: list[dict]) -> None:
        self.rules = list(rules)
        self.by_id = {rule["rule_id"]: rule for rule in self.rules}

    def get(self, rule_id: str) -> dict | None:
        return self.by_id.get(rule_id)

    def ids(self) -> list[str]:
        return sorted(self.by_id)

    def prefix_of(self, rule_id: str) -> str:
        parts = rule_id.split("-")
        return parts[1] if len(parts) > 1 else ""

    def __iter__(self):
        return iter(self.rules)

    def __len__(self) -> int:
        return len(self.rules)


# ---------------------------------------------------------------------------
# 字段取值
# ---------------------------------------------------------------------------

def get_field(product: dict, field: str) -> Any:
    """按 `data/schema/rule.schema.json` 的 `field` 枚举取值。

    `any_text` 是标题 + 详情 + 品牌 + 类目 + 型号 + 图片 OCR 的合并文本。
    """
    if field == "title":
        return product.get("title")
    if field == "description":
        return product.get("description")
    if field == "attributes":
        return product.get("attributes")
    if field == "category":
        return product.get("category")
    if field == "brand":
        return product.get("brand")
    if field == "model":
        return product.get("model")
    if field == "price":
        return product.get("price")
    if field == "image":
        return product.get("images")
    if field == "image_text":
        texts = [i.get("ocr_text") or "" for i in product.get("images") or []
                 if isinstance(i, dict)]
        return " \n".join(t for t in texts if t)
    if field == "variations":
        return product.get("variations")
    if field == "supplier_sku":
        return product.get("supplier_sku")
    if field == "shop_id":
        return product.get("shop_id")
    if field == "product_url":
        return product.get("product_url")
    if field == "history":
        return product.get("history")
    if field == "seller_name":
        return product.get("shop_name")
    if field == "any_text":
        parts = [
            product.get("title") or "",
            product.get("description") or "",
            product.get("brand") or "",
            product.get("category") or "",
            product.get("model") or "",
        ]
        for image in product.get("images") or []:
            if isinstance(image, dict) and image.get("ocr_text"):
                parts.append(image["ocr_text"])
        return "\n".join(p for p in parts if p)
    return None


def is_empty(value) -> bool:
    """存在但为空 == 缺失（PROJECT_RULES §11.1）。"""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


# ---------------------------------------------------------------------------
# 算子
# ---------------------------------------------------------------------------

def _match_contains_any(actual, needles) -> bool:
    """`contains_any` 语义。

    * 容器（list）→ 元素完全匹配，或字符串子串包含；
    * 字典（`history`）→ 键名匹配，**或**摊平后的文本里出现该词 ——
      处罚点/申诉这类状态既可能写成 `history.appeal_pending` 键，也可能
      写在自由文本里，两种都要认；
    * 字符串 → 子串包含（忽略大小写）。
    """
    if isinstance(actual, dict):
        keys = set(actual.keys())
        flat = flatten_value(actual).lower()
        for needle in needles:
            if needle in keys:
                return True
            if str(needle).lower() in flat:
                return True
        return False
    if isinstance(actual, (list, tuple, set)):
        elements = {str(x) for x in actual}
        for needle in needles:
            if needle in elements:
                return True
            if isinstance(actual, (list, tuple)) and any(
                    str(needle).lower() in str(x).lower() for x in actual):
                return True
        return False
    text = str(actual).lower()
    return any(str(needle).lower() in text for needle in needles)


def _condition_matches(product: dict, cond: dict, injected: set[str]):
    """判断单条触发条件。

    返回 ``(是否成立, 是否因缺输入而无法评估)``。
    """
    field = cond.get("field") or ""
    operator = cond.get("operator") or ""
    value = cond.get("value")
    case_sensitive = bool(cond.get("case_sensitive", False))

    for required in cond.get("requires_input") or []:
        if is_empty(get_field(product, required)):
            return False, True

    actual = get_field(product, field)

    # --- 存在性语义 ---
    if operator == "field_missing":
        return is_empty(actual), False
    if operator == "has_field":
        return not is_empty(actual), False
    if operator == "has_nonempty":
        if field == "image":
            return any((i.get("detected_logos") or []) for i in actual or []
                       if isinstance(i, dict)), False
        return not is_empty(actual), False

    # --- 注入的哨兵记号 ---
    if isinstance(value, str) and _SENTINEL_RE.match(value):
        return (value in injected), False
    if isinstance(value, list):
        sentinels = [v for v in value if isinstance(v, str) and _SENTINEL_RE.match(v)]
        if sentinels:
            others = [v for v in value if v not in sentinels]
            if not any(s in injected for s in sentinels):
                return False, False
            if not others:
                return True, False
            # 哨兵 + 普通词：普通词仍需成立
            if is_empty(actual):
                return False, True
            return _match_contains_any(actual, others), False

    # --- 计数语义 ---
    if operator == "image_count_lt":
        return len(actual or []) < int(value), False
    if operator == "image_count_gte":
        return len(actual or []) >= int(value), False

    # --- 其余算子需要实际值；缺失即无法评估 ---
    if is_empty(actual):
        return False, True

    if operator == "regex":
        haystack = actual
        if isinstance(haystack, (dict, list, tuple)):
            haystack = flatten_value(haystack)
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            return re.search(str(value), str(haystack), flags) is not None, False
        except re.error:
            return False, True

    if operator == "contains_any":
        needles = value if isinstance(value, list) else [value]
        return _match_contains_any(actual, needles), False

    if operator == "contains_all":
        needles = value if isinstance(value, list) else [value]
        if isinstance(actual, dict):
            keys = set(actual.keys())
            flat = flatten_value(actual).lower()
            return all(n in keys or str(n).lower() in flat for n in needles), False
        if isinstance(actual, (list, tuple, set)):
            elements = {str(x) for x in actual}
            return all(n in elements for n in needles), False
        text = str(actual).lower()
        return all(str(n).lower() in text for n in needles), False

    if operator == "not_contains_any":
        matched, unevaluated = _condition_matches(
            product, {**cond, "operator": "contains_any"}, injected)
        return (not matched, unevaluated)

    if operator == "equals":
        return actual == value, False
    if operator == "not_equals":
        return actual != value, False
    if operator == "gt":
        return _numeric(actual, value, lambda a, b: a > b), False
    if operator == "gte":
        return _numeric(actual, value, lambda a, b: a >= b), False
    if operator == "lt":
        return _numeric(actual, value, lambda a, b: a < b), False
    if operator == "lte":
        return _numeric(actual, value, lambda a, b: a <= b), False
    if operator == "history_missing_nonempty":
        if not isinstance(actual, dict):
            return False, True
        gaps = actual.get(value)
        if gaps is None:
            return False, False
        if isinstance(gaps, (list, tuple, set)):
            return len(gaps) > 0, False
        return not is_empty(gaps), False
    if operator == "length_lt":
        return len(str(actual)) < int(value), False
    if operator == "length_gte":
        return len(str(actual)) >= int(value), False

    return False, True


def _numeric(actual, expected, compare) -> bool:
    """数值比较。类型不可比时不猜 —— 判为不成立。"""
    if isinstance(actual, bool) or isinstance(expected, bool):
        return False
    if not isinstance(actual, (int, float)) or not isinstance(expected, (int, float)):
        return False
    return bool(compare(actual, expected))


def evaluate_rule(rule: dict, product: dict, injected: set[str] | None = None):
    """判断一条规则是否命中。

    返回 ``(是否命中, 是否未评估, 未评估原因)``。
    """
    injected = injected or set()
    conditions = rule.get("trigger_conditions") or []
    if not conditions:
        return False, True, "rule declares no trigger condition"

    unevaluated = False
    reasons: list[str] = []
    for cond in conditions:
        matched, cannot_evaluate = _condition_matches(product, cond, injected)
        if cannot_evaluate:
            unevaluated = True
            field = cond.get("field")
            reasons.append(
                f"input does not carry the data the rule inspects "
                f"(field={field}, operator={cond.get('operator')})")
            continue
        if not matched:
            return False, False, ""
    if unevaluated:
        return False, True, "; ".join(reasons)
    return True, False, ""
