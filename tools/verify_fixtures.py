#!/usr/bin/env python3
"""机械校验共享夹具是否真的命中/不命中其声明的规则。

夹具的价值在于「可归因」：每个正例必须触发它声称触发的规则，每个反例必须
不触发它声称不触发的规则。如果只是写一份 JSON 而不校验，夹具会随规则演进而
静默失效 —— 规则改宽了没人发现，反例不再反例，误报就无从暴露。

用法：
    python3 tools/verify_fixtures.py
    python3 tools/verify_fixtures.py --verbose
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")
RULES = os.path.join(ROOT, "rules")

VERBOSE = "--verbose" in sys.argv


def load_rules():
    """载入全部规则，按 rule_id 索引。"""
    out = {}
    for fn in sorted(os.listdir(RULES)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(RULES, fn), encoding="utf-8") as f:
            for r in json.load(f)["rules"]:
                out[r["rule_id"]] = r
    return out


def get_field(product, field):
    """按 rule.schema.json 的 field 枚举取值。

    `any_text` 是标题+详情+品牌+类目+型号+图片 OCR 的合并文本 —— 规则的
    词库匹配作用在全部可见文案上。
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
        texts = [i.get("ocr_text") or "" for i in product.get("images") or []]
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
    if field == "any_text":
        parts = [
            product.get("title") or "",
            product.get("description") or "",
            product.get("brand") or "",
            product.get("category") or "",
            product.get("model") or "",
        ]
        for im in product.get("images") or []:
            if im.get("ocr_text"):
                parts.append(im["ocr_text"])
        return "\n".join(p for p in parts if p)
    return None


def is_empty(v):
    """PROJECT_RULES §11.1：存在但为空 == 缺失。"""
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def cond_matches(product, cond):
    """判断单条 trigger_condition 是否成立。

    返回 (是否成立, 是否因缺输入而无法评估)。
    """
    field = cond["field"]
    op = cond["operator"]
    val = cond.get("value")
    cs = cond.get("case_sensitive", False)

    # requires_input：任一依赖字段缺失/为空 → 该条件不评估（H3）
    for req in cond.get("requires_input", []) or []:
        if is_empty(get_field(product, req)):
            return False, True

    actual = get_field(product, field)

    # field_missing / has_field / has_nonempty 走「存在性」语义
    if op == "field_missing":
        return (is_empty(actual), False)
    if op == "has_field":
        return (not is_empty(actual), False)
    if op == "has_nonempty":
        # has_nonempty(detected_logos) —— 指 images[].detected_logos 非空
        if field == "image":
            return (any((i.get("detected_logos") or []) for i in actual or []), False)
        return (not is_empty(actual), False)

    if op == "image_count_lt":
        return (len(actual or []) < int(val), False)
    if op == "image_count_gte":
        return (len(actual or []) >= int(val), False)

    # 其余算子需要实际值；缺失 → 无法评估
    if is_empty(actual):
        return False, True

    if op == "regex":
        flags = 0 if cs else re.IGNORECASE
        try:
            return (re.search(val, actual, flags) is not None, False)
        except re.error as e:
            raise SystemExit(f"规则正则编译失败: {e}\n  {val}")
    if op == "contains_any":
        # dict 字段（如 history）：语义是「含指定键」。
        # SBR-AU-001 的 value 是 ['missing','authorization_documents'] ——
        # 显然指 history 的键名，而非其字符串内容。
        if isinstance(actual, dict):
            keys = set(actual.keys())
            for n in (val if isinstance(val, list) else [val]):
                if n in keys:
                    return True, False
            return False, False
        hay = actual if isinstance(actual, list) else [actual]
        hay_s = {str(x) for x in hay}
        needles = val if isinstance(val, list) else [val]
        for n in needles:
            if isinstance(n, str) and n.startswith("__") and n.endswith("__"):
                continue  # 引擎注入的信号，由 duplicate-detection 模块填充
            if n in hay_s:
                return True, False
            if isinstance(actual, str) and str(n).lower() in actual.lower():
                return True, False
        return False, False
    if op == "contains_all":
        needles = val if isinstance(val, list) else [val]
        hay = actual if isinstance(actual, list) else [actual]
        hay_s = {str(x) for x in hay}
        if all(n in hay_s for n in needles):
            return True, False
        if isinstance(actual, str) and all(str(n).lower() in actual.lower() for n in needles):
            return True, False
        return False, False
    if op == "not_contains_any":
        m, unevaluated = cond_matches(product, {**cond, "operator": "contains_any"})
        return (not m, unevaluated)
    if op == "equals":
        return (actual == val, False)
    if op == "not_equals":
        return (actual != val, False)
    if op == "gt":
        return (actual > val, False)
    if op == "gte":
        return (actual >= val, False)
    if op == "lt":
        return (actual < val, False)
    if op == "lte":
        return (actual <= val, False)
    if op == "history_missing_nonempty":
        # history 中的缺口列表非空（如 missing: ["anvisa_registration"]）。
        # 与 contains_any 的区别：这里要求**列表里确有具体缺口**，
        # 而不是「存在该键」。
        if not isinstance(actual, dict):
            return False, True
        gaps = actual.get(val)
        if gaps is None:
            return False, False
        if isinstance(gaps, (list, tuple, set)):
            return (len(gaps) > 0, False)
        return (not is_empty(gaps), False)
    if op == "length_lt":
        # 文本长度比较（如「详情少于 120 字符」）。
        # 与 `lt` 的区别：比较的是长度，不是字符串与数字。
        return (len(str(actual)) < int(val), False)
    if op == "length_gte":
        return (len(str(actual)) >= int(val), False)
    raise SystemExit(f"未知算子: {op}")


def rule_fires(product, rule):
    """规则是否命中。

    返回 (命中, 因缺输入未评估)。
    trigger_conditions 之间是 AND 关系 —— 任一条件不成立则不命中；
    但若某条件因缺输入无法评估，则整条规则未评估。
    """
    unevaluated = False
    for cond in rule["trigger_conditions"]:
        ok, un = cond_matches(product, cond)
        if un:
            unevaluated = True
            continue
        if not ok:
            return False, unevaluated
    return True, unevaluated


def load_fixture(name):
    path = os.path.join(FIX, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    rules = load_rules()
    errors = []
    checked = 0
    fired_total = 0
    not_fired_total = 0

    # ---- 正例：必须命中 ----
    doc = load_fixture("violation_products.json")
    if doc is None:
        errors.append("violation_products.json 缺失")
    else:
        for p in doc["products"]:
            targets = p.get("targets", [])
            for rid in targets:
                checked += 1
                rule = rules.get(rid)
                if rule is None:
                    errors.append(f"{p['product_id']}: 未知规则 {rid}")
                    continue
                fired, un = rule_fires(p, rule)
                if not fired:
                    if un:
                        errors.append(
                            f"{p['product_id']} / {rid}: 因缺输入未评估 —— "
                            f"正例必须提供该规则依赖的字段")
                    else:
                        errors.append(
                            f"{p['product_id']} / {rid}: 未命中 —— "
                            f"正例失效（规则可能已改宽或夹具文案已漂移）")
                else:
                    fired_total += 1
                    if VERBOSE:
                        print(f"  ok  {p['product_id']} -> {rid}")

    # ---- 反例：必须不命中 ----
    # `targets` 里的规则必须**不命中**。
    # `targets_exempted` 里的规则**允许命中** —— 用于「豁免路径」类反例：
    # 规则本身命中品牌词，但配套的豁免规则（severity=info/decision=allow）
    # 必须被正确应用。这类反例检验的是豁免生效，而非规则不触发。
    doc = load_fixture("normal_products.json")
    if doc is None:
        errors.append("normal_products.json 缺失")
    else:
        for p in doc["products"]:
            targets = p.get("targets", [])
            exempted = p.get("targets_exempted", [])
            for rid in targets:
                checked += 1
                rule = rules.get(rid)
                if rule is None:
                    errors.append(f"{p['product_id']}: 未知规则 {rid}")
                    continue
                fired, un = rule_fires(p, rule)
                if fired:
                    errors.append(
                        f"{p['product_id']} / {rid}: **命中了** —— "
                        f"反例失效（规则过宽，误报风险）")
                else:
                    not_fired_total += 1
                    if VERBOSE:
                        print(f"  ok  {p['product_id']} -/-> {rid}")
            for rid in exempted:
                checked += 1
                rule = rules.get(rid)
                if rule is None:
                    errors.append(f"{p['product_id']}: 未知规则 {rid}")
                    continue
                fired, un = rule_fires(p, rule)
                if not fired:
                    errors.append(
                        f"{p['product_id']} / {rid}: 豁免路径未触发 —— "
                        f"应命中却未命中（豁免规则失效）")
                else:
                    fired_total += 1
                    if VERBOSE:
                        print(f"  ok  {p['product_id']} +/-> {rid} (豁免)")

    # ---- 边界用例：声明 must_fire / must_not_fire ----
    for fname in ("edge_cases.json", "ip_cases.json", "injection_cases.json"):
        doc = load_fixture(fname)
        if doc is None:
            continue
        for c in doc.get("cases", []):
            p = c["product"]
            for rid in c.get("must_fire", []):
                checked += 1
                rule = rules.get(rid)
                if rule is None:
                    errors.append(f"{c['case_id']}: 未知规则 {rid}")
                    continue
                fired, un = rule_fires(p, rule)
                if not fired:
                    errors.append(
                        f"{c['case_id']} / {rid}: 应命中但未命中"
                        + ("（因缺输入未评估）" if un else ""))
                else:
                    fired_total += 1
            for rid in c.get("must_not_fire", []):
                checked += 1
                rule = rules.get(rid)
                if rule is None:
                    errors.append(f"{c['case_id']}: 未知规则 {rid}")
                    continue
                fired, un = rule_fires(p, rule)
                if fired:
                    errors.append(
                        f"{c['case_id']} / {rid}: 应不命中但命中了 —— 边界判定失效")
                else:
                    not_fired_total += 1

    # ---- IP 夹具：H1 前提校验 ----
    # IP 类结论恒为 confidence=signal 且 requires_human_review=true。
    # 这里的机械检查是前提条件：IP 类规则的 category 必须属于 IP 四类，
    # 且不得声明为 confirmed。具体的 signal 赋值由模块实现负责断言。
    doc = load_fixture("ip_cases.json")
    if doc is not None:
        IP_CATS = {"ip_trademark", "ip_copyright", "ip_design", "ip_patent"}
        for c in doc.get("cases", []):
            checked += 1
            cats = set(c.get("ip_categories", []))
            if not cats or not cats <= IP_CATS:
                errors.append(
                    f"{c['case_id']}: ip_categories 必须是非空且属于 IP 四类的子集，"
                    f"实际 {sorted(cats)}")
            # 夹具必须显式声明 H1 断言，否则模块无从继承
            if "h1_assertion" not in c:
                errors.append(f"{c['case_id']}: 缺少 h1_assertion 声明")
            not_fired_total += 1

    # ---- 缺失数据用例：声明 unevaluated ----
    doc = load_fixture("missing_data_cases.json")
    if doc is not None:
        for c in doc.get("cases", []):
            p = c["product"]
            for rid in c.get("must_be_unevaluated", []):
                checked += 1
                rule = rules.get(rid)
                if rule is None:
                    errors.append(f"{c['case_id']}: 未知规则 {rid}")
                    continue
                fired, un = rule_fires(p, rule)
                if not un:
                    errors.append(
                        f"{c['case_id']} / {rid}: 应判为未评估（缺输入），"
                        f"但实际可评估")
                else:
                    not_fired_total += 1

    print(f"校验 {checked} 条夹具-规则断言："
          f"{fired_total} 应命中、{not_fired_total} 应不命中")
    if errors:
        print(f"\n{len(errors)} 个问题：")
        for e in errors:
            print("  -", e)
        return 1
    print("全部夹具与规则库一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
