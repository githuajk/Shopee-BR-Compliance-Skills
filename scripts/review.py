#!/usr/bin/env python3
"""CLI for the Shopee BR compliance agent.

Usage:
    python3 scripts/review.py --input <file> [--shop-id SHOP] [--out DIR]
    python3 scripts/review.py --input a.xlsx --input b.csv --shop-id SHOP1
    python3 scripts/review.py --rules rules/ --out out/

Outputs (written into --out):
    review_result.json   machine-readable result (schema: review_result.schema.json)
    review_report.md     human-readable report
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from compliance_agent.engine.loader import load_rules  # noqa: E402
from compliance_agent.engine.reviewer import Reviewer, write_result  # noqa: E402
from compliance_agent.ingest.parsers import parse_file  # noqa: E402
from compliance_agent.models import Case, Product  # noqa: E402
from compliance_agent.report.markdown import write_report  # noqa: E402


def load_cases(path: str) -> list[Case]:
    """Load historical cases from a JSON file (cases.json format)."""
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    items = payload.get("cases", payload) if isinstance(payload, dict) else payload
    out = []
    for d in items:
        out.append(Case(
            case_id=d["case_id"],
            shop_id=d.get("shop_id", ""),
            product_ids=d.get("product_ids", []),
            violation_type=d.get("violation_type", ""),
            status=d.get("status", "open"),
            frozen=d.get("frozen", False),
            rule_ids=d.get("rule_ids", []),
            platform_notice=d.get("platform_notice"),
            case_type=d.get("case_type", "listing_review"),
            evidence=d.get("evidence", []),
            approvals=d.get("approvals", []),
        ))
    return out


def load_history_products(path: str) -> list[Product]:
    """Load historical product records from a JSON file."""
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    items = payload.get("products", payload) if isinstance(payload, dict) else payload
    out = []
    for d in items:
        out.append(Product(
            product_id=d["product_id"],
            internal_sku=d.get("internal_sku", d["product_id"]),
            supplier_sku=d.get("supplier_sku"),
            shop_id=d.get("shop_id", ""),
            platform_pid=d.get("platform_pid"),
            title=d.get("title", ""),
            description=d.get("description", ""),
            category=d.get("category"),
            brand=d.get("brand"),
            price=d.get("price"),
            images=d.get("images", []),
            product_url=d.get("product_url"),
        ))
    return out


def main():
    ap = argparse.ArgumentParser(description="Shopee BR compliance review")
    ap.add_argument("--input", action="append", required=True,
                    help="input file (xlsx/csv/tsv/json/jsonl/txt/md/docx/pdf/image)")
    ap.add_argument("--shop-id", action="append", default=[],
                    help="shop id for the corresponding --input (repeatable)")
    ap.add_argument("--rules", default=os.path.join(ROOT, "rules"),
                    help="rules directory or file")
    ap.add_argument("--cases", help="historical cases JSON")
    ap.add_argument("--history-products", help="historical products JSON")
    ap.add_argument("--out", default=os.path.join(ROOT, "out"),
                    help="output directory")
    ap.add_argument("--run-id", help="explicit run id")
    args = ap.parse_args()

    shop_ids = args.shop_id or ["UNKNOWN"] * len(args.input)
    if len(shop_ids) < len(args.input):
        shop_ids += ["UNKNOWN"] * (len(args.input) - len(shop_ids))

    products: list[Product] = []
    errors: list[dict] = []
    scope_sources = []
    for path, shop in zip(args.input, shop_ids):
        res = parse_file(path, shop_id=shop)
        products.extend(res.products)
        errors.extend(e.to_dict() for e in res.errors)
        scope_sources.append({
            "path": os.path.abspath(path),
            "shop_id": shop,
            "format": os.path.splitext(path)[1].lstrip("."),
            "products_parsed": len(res.products),
            "errors": len(res.errors),
            "meta": res.meta,
        })
        print(f"parsed {path}: {len(res.products)} products, {len(res.errors)} errors")

    rules = load_rules(args.rules)
    print(f"loaded {len(rules)} rules from {args.rules}")

    history_cases = load_cases(args.cases) if args.cases else []
    history_products = load_history_products(args.history_products) if args.history_products else []
    if args.cases:
        print(f"loaded {len(history_cases)} historical cases")
    if args.history_products:
        print(f"loaded {len(history_products)} historical products")

    reviewer = Reviewer(rules, history_products=history_products,
                        history_cases=history_cases)
    result = reviewer.review(products, run_id=args.run_id,
                             scope={"sources": scope_sources,
                                    "rules_dir": os.path.abspath(args.rules)})
    result["errors"] = errors + result.get("errors", [])
    result["summary"]["parse_errors"] = len(result["errors"])

    os.makedirs(args.out, exist_ok=True)
    json_path = os.path.join(args.out, "review_result.json")
    md_path = os.path.join(args.out, "review_report.md")
    write_result(result, json_path)
    write_report(result, md_path, {r.rule_id: r for r in rules})

    s = result["summary"]
    print("\n--- summary ---")
    print(f"products reviewed : {s['products_reviewed']}")
    print(f"products flagged  : {s['products_flagged']}")
    print(f"products blocked  : {s['products_blocked']}")
    print(f"findings total    : {s['findings_total']}")
    print(f"parse errors      : {s['parse_errors']}")
    print(f"\nJSON  : {json_path}")
    print(f"report: {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
