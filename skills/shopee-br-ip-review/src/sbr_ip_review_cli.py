#!/usr/bin/env python3
"""shopee-br-ip-review 命令行入口。

用法
----
    python3 skills/shopee-br-ip-review/src/sbr_ip_review_cli.py \
        --request-id REQ-IP-001 --out-dir out/ip \
        skills/shopee-br-data-ingestion/.../products.json

输入
----
一个符合 `contracts/skill_input.schema.json` 的 JSON 文件，或一个含
`products[]` 的 JSON 文件（自动包成 SkillInput）。

产出（写入 `--out-dir`）
------------------------

| 文件 | 契约 |
|---|---|
| `audit_result.json` | `contracts/audit_result.schema.json`（**单条**） |
| `audit_results.json` | 同上，多条（数组） |
| `module_handoff.json` | `contracts/module_handoff.schema.json` |
| `signals.json` | 判定明细（非契约字段，供人工复核） |

退出码
------
`0` 正常；`1` 参数或输入错误；`2` 规则库读不到（必须显式失败）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sbr_ip_review import engine  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sbr_ip_review_cli.py",
        description="Shopee BR 知识产权与授权风险筛查")
    parser.add_argument("inputs", nargs="+",
                        help="SkillInput 或含 products[] 的 JSON 文件")
    parser.add_argument("--request-id", default=None,
                        help="请求 ID；缺省从输入的 request_id 取")
    parser.add_argument("--out-dir", required=True, help="产出目录")
    parser.add_argument("--root", default=None,
                        help="仓库根路径；缺省由模块位置推导")
    parser.add_argument("--indent", type=int, default=2,
                        help="JSON 缩进（默认 2）")
    return parser


def _load_input(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise ValueError(f"{path}: top level must be an object")
    if "products" not in document:
        raise ValueError(f"{path}: no 'products' key found")
    return document


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    options: dict = {"root": args.root}

    products: list[dict] = []
    request_id = args.request_id
    for path in args.inputs:
        try:
            document = _load_input(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"错误：无法读取输入 {path}：{exc}", file=sys.stderr)
            return 1
        if request_id is None:
            request_id = document.get("request_id")
        products.extend(document.get("products") or [])

    if request_id is None:
        request_id = "REQ-IP-UNSPECIFIED"

    skill_input = {
        "request_id": request_id,
        "task_type": "ip_review",
        "target": "cli",
        "products": products,
        "cases": [],
        "rules": [],
        "scope": {},
        "options": {},
        "provenance": {
            "produced_at": engine._utc_now_iso(),
            "producer": engine.REVIEWER_VERSION,
            "source_refs": list(args.inputs),
        },
    }

    try:
        bundle = engine.review_products(skill_input, options=options)
    except engine.RuleLoadError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    os.makedirs(args.out_dir, exist_ok=True)
    results = bundle["results"]

    written = {
        # `contracts/audit_result.schema.json` 定义的是**单条** AuditResult
        # （type=object），所以主产出是单条；多条另存数组文件。
        "audit_result.json": results[0] if results else None,
        "audit_results.json": results,
        "module_handoff.json": bundle["handoff"],
        "signals.json": bundle["signals"],
    }
    for name, payload in written.items():
        if payload is None:
            continue
        with open(os.path.join(args.out_dir, name), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=args.indent)
            handle.write("\n")

    if bundle["errors"]:
        with open(os.path.join(args.out_dir, "errors.json"), "w",
                  encoding="utf-8") as handle:
            json.dump(bundle["errors"], handle, ensure_ascii=False,
                      indent=args.indent)
            handle.write("\n")

    counts: dict[str, int] = {}
    for result in results:
        counts[result["action"]] = counts.get(result["action"], 0) + 1
    print(f"已筛查 {len(results)} 个商品 → {args.out_dir}")
    for action in sorted(counts):
        print(f"  {action}: {counts[action]}")
    print("  全部结论 confidence=signal 且 requires_human_review=true"
          "（硬约束 H1：IP 结论恒为筛查信号）")
    if bundle["errors"]:
        print(f"  错误 {len(bundle['errors'])} 条 → errors.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
