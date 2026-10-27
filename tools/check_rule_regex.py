#!/usr/bin/env python3
"""校验规则库中每条正则触发条件是否可编译，并检查逻辑自洽性。

规则的正则写在 JSON 里，Schema 校验只能确认它是字符串 —— 编译不过的正则
在评估时才会抛异常，整条规则不可用，而且往往要到线上数据才暴露。

同时检查两类逻辑缺陷：
  1. 自指 requires_input —— `field_missing(X)` 却声明 `requires_input=[X]`，
     字段缺失时规则被判未评估，规则永不可满足。
  2. 数值算子作用于文本字段 —— `description lt 120` 意为「字符串 < 数字」，
     比较时抛 TypeError。

用法：python3 tools/check_rule_regex.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "rules")

# 需要数值比较的算子（值必须是数字）
NUMERIC_OPS = {"lt", "gt", "lte", "gte"}
# 文本长度算子（作用在文本字段上）
LENGTH_OPS = {"length_lt", "length_gte"}
# 合理的文本字段（用于自洽检查）
TEXT_FIELDS = {
    "title", "description", "attributes", "category", "brand", "model",
    "image_text", "seller_name", "supplier_sku", "shop_id", "product_url",
    "history", "any_text",
}


def main():
    errors = []
    n_rules = n_regex = 0

    for path in sorted(glob.glob(os.path.join(RULES, "*.json"))):
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        rel = os.path.relpath(path, ROOT)
        for rule in doc.get("rules", []):
            n_rules += 1
            rid = rule.get("rule_id", "?")
            for cond in rule.get("trigger_conditions", []):
                op = cond.get("operator")
                field = cond.get("field")
                val = cond.get("value")

                # --- 1. 正则可编译性 ---
                if op == "regex":
                    n_regex += 1
                    try:
                        re.compile(val)
                    except re.error as e:
                        errors.append(
                            f"{rid}: 正则无法编译 ({e}) —— 评估时会抛异常。"
                            f"pattern: {val[:120]!r}")

                # --- 2. 自指 requires_input ---
                req = cond.get("requires_input") or []
                if op == "field_missing" and field in req:
                    errors.append(
                        f"{rid}: requires_input 自指 —— `field_missing({field})` "
                        f"与 requires_input={req} 指向同一字段：字段缺失即被判未评估，"
                        f"规则永不可满足")
                if op == "image_count_lt" and "image" in req:
                    errors.append(
                        f"{rid}: requires_input 自指 —— `image_count_lt({val})` "
                        f"要求 images 非空才评估，但非空时计数已 >= 1，永不小于 {val}，"
                        f"规则永不可满足")
                if op == "image_count_gte" and "image" in req:
                    errors.append(
                        f"{rid}: requires_input 自指 —— `image_count_gte({val})` "
                        f"要求 images 非空才评估，与算子语义冲突")

                # --- 3. 数值算子 vs 文本字段 ---
                if op in NUMERIC_OPS and field in TEXT_FIELDS:
                    errors.append(
                        f"{rid}: 数值算子 `{op}` 作用于文本字段 `{field}` —— "
                        f"比较时抛 TypeError。应改用 length_* 算子或改为数值字段")
                if op in LENGTH_OPS and field not in TEXT_FIELDS:
                    errors.append(
                        f"{rid}: 长度算子 `{op}` 作用于非文本字段 `{field}`")

                # --- 4. 算子与值类型 ---
                if op in NUMERIC_OPS and not isinstance(val, (int, float)):
                    errors.append(f"{rid}: 数值算子 `{op}` 的值不是数字: {val!r}")
                if op in LENGTH_OPS and not isinstance(val, (int, float)):
                    errors.append(f"{rid}: 长度算子 `{op}` 的值不是数字: {val!r}")

    print(f"检查 {n_rules} 条规则、{n_regex} 条正则")
    if errors:
        print(f"\n{len(errors)} 个问题：")
        for e in errors:
            print("  -", e)
        return 1
    print("全部规则的正则可编译，且无逻辑自指缺陷。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
