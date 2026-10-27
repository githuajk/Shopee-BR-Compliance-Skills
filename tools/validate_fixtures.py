#!/usr/bin/env python3
"""Validate the embedded fixtures in data/samples/test_cases.json.

The sample file is a *wrapper* (cases + products + history), so it cannot be
validated against product.schema.json / case.schema.json directly. This
script extracts each embedded record and validates it against the schema it
is supposed to satisfy.

Usage: python3 tools/validate_fixtures.py
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from validate_json import Validator  # noqa: E402

SCHEMA_DIR = os.path.join(ROOT, "data", "schema")


def load(name):
    with open(os.path.join(SCHEMA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    product_schema = load("product.schema.json")
    case_schema = load("case.schema.json")
    pv = Validator(product_schema, base_dir=SCHEMA_DIR)
    cv = Validator(case_schema, base_dir=SCHEMA_DIR)

    path = os.path.join(ROOT, "data", "samples", "test_cases.json")
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)

    errors = []
    n_products = n_cases = 0
    for tc in doc.get("cases", []):
        cid = tc.get("case_id", "?")
        for p in tc.get("products", []):
            n_products += 1
            rec = dict(p)
            rec.setdefault("source", {"kind": "manual"})
            errs = pv.validate(rec)
            if errs:
                errors.append(f"{cid} product {rec.get('product_id')}: " + "; ".join(errs))
        for c in tc.get("history_cases", []):
            n_cases += 1
            errs = cv.validate(c)
            if errs:
                errors.append(f"{cid} case {c.get('case_id')}: " + "; ".join(errs))
        # the wrapper itself must have the expected shape
        for req in ("case_id", "scenario", "expect", "products"):
            if req not in tc:
                errors.append(f"{cid}: missing wrapper key {req!r}")
        exp = tc.get("expect", {})
        for req in ("product_status", "min_findings", "must_include_rules",
                    "must_not_include_rules"):
            if req not in exp:
                errors.append(f"{cid}: missing expect key {req!r}")

    # --- 共享夹具（tests/fixtures/）——
    # 这些文件由集成 Agent 拥有，供各模块只读消费（tests/test_plan.md §5.1）。
    # 商品记录必须符合 product.schema.json；案件记录必须符合 case.schema.json。
    #
    # 夹具文件里的 `targets` / `targets_exempted` / `note` 是**夹具注解**，
    # 供 tools/verify_fixtures.py 消费，不是商品/案件契约的一部分。
    # Schema 是 additionalProperties=false —— 校验前剥离注解，注解本身的
    # 正确性由 verify_fixtures.py 负责。
    ANNOTATIONS = {"targets", "targets_exempted", "note"}

    def strip_annotations(rec):
        return {k: v for k, v in rec.items() if k not in ANNOTATIONS}

    fix_dir = os.path.join(ROOT, "tests", "fixtures")
    if os.path.isdir(fix_dir):
        for fn in sorted(os.listdir(fix_dir)):
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(fix_dir, fn)
            with open(fp, encoding="utf-8") as f:
                fdoc = json.load(f)
            # 商品数组（normal / violation）
            for p in fdoc.get("products", []):
                n_products += 1
                rec = strip_annotations(dict(p))
                rec.setdefault("source", {"kind": "manual"})
                errs = pv.validate(rec)
                if errs:
                    errors.append(f"{fn} product {rec.get('product_id')}: "
                                  + "; ".join(errs))
            # 用例数组（edge / ip / injection / missing_data）
            for c in fdoc.get("cases", []):
                cid = c.get("case_id", "?")
                p = c.get("product")
                if p is not None:
                    n_products += 1
                    rec = strip_annotations(dict(p))
                    rec.setdefault("source", {"kind": "manual"})
                    errs = pv.validate(rec)
                    if errs:
                        errors.append(f"{fn} {cid} product: " + "; ".join(errs))
            # 案件文件：顶层 cases 数组本身就是案件记录
            if fn == "case_history.json":
                for case_rec in fdoc.get("cases", []):
                    n_cases += 1
                    errs = cv.validate(strip_annotations(case_rec))
                    if errs:
                        errors.append(f"{fn} case {case_rec.get('case_id')}: "
                                      + "; ".join(errs))

    print(f"validated {n_products} products, {n_cases} cases across "
          f"{len(doc.get('cases', []))} scenarios + shared fixtures")
    if errors:
        print(f"\n{len(errors)} errors:")
        for e in errors:
            print("  -", e)
        return 1
    print("all fixtures valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
