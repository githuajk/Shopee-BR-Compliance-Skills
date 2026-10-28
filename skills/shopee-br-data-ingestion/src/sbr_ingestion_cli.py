#!/usr/bin/env python3
"""命令行入口：把外部文件读成规范数据。

```bash
env -u LD_LIBRARY_PATH python3 skills/shopee-br-data-ingestion/src/sbr_ingestion_cli.py \
    --request-id REQ-INGEST-001 \
    --out-dir /tmp/ingest-out \
    data/samples/demo_mass_update.xlsx
```

产出（写入 `--out-dir`）：

| 文件 | 契约 |
|---|---|
| `skill_input.json` | `contracts/skill_input.schema.json` |
| `audit_result.json` | `contracts/audit_result.schema.json`（**单条** —— 该 Schema 的 `type` 是 object） |
| `audit_results.json` | `AuditResult[]` 完整数组 |
| `module_handoff.json` | `contracts/module_handoff.schema.json` |
| `products.json` | `data/schema/product.schema.json` 的数组 |

**只读输入** —— 本脚本从不写回被读取的文件。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sbr_ingestion import PARSER_VERSION, ingest_paths  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="sbr_ingestion_cli",
        description="Read Shopee product data from external files into the "
                    "project's unified product model (never modifies the input).",
    )
    parser.add_argument("paths", nargs="+", help="input file(s) to read")
    parser.add_argument("--request-id", required=True,
                        help="unique request identifier (>= 4 chars)")
    parser.add_argument("--out-dir", required=True, help="directory for the outputs")
    parser.add_argument("--default-shop-id", default=None,
                        help="shop_id to use for records that have none")
    parser.add_argument("--default-currency", default=None,
                        help="currency to use for records that have none")
    parser.add_argument("--sheet", default=None,
                        help="worksheet name to read (xlsx only)")
    parser.add_argument("--quiet", action="store_true", help="suppress the summary")
    args = parser.parse_args(argv)

    options = {
        "default_shop_id": args.default_shop_id,
        "default_currency": args.default_currency,
        "sheet": args.sheet,
    }
    options = {k: v for k, v in options.items() if v is not None}

    bundle = ingest_paths(args.paths, request_id=args.request_id, options=options)

    os.makedirs(args.out_dir, exist_ok=True)
    # `contracts/audit_result.schema.json` 定义的是**单条** AuditResult
    # （type: object）。因此 `audit_result.json` 写单条（契约可直接校验），
    # 完整数组另存 `audit_results.json`。
    written = {
        "skill_input.json": bundle["skill_input"],
        "audit_result.json": (bundle["results"][0] if bundle["results"] else None),
        "audit_results.json": bundle["results"],
        "module_handoff.json": bundle["handoff"],
        "products.json": bundle["products"],
    }
    for name, payload in written.items():
        target = os.path.join(args.out_dir, name)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    if not args.quiet:
        result = bundle["results"][0]
        print(f"parser:  {PARSER_VERSION}")
        print(f"inputs:  {len(args.paths)}")
        print(f"records: {len(bundle['products'])} product(s)")
        print(f"errors:  {len(bundle['errors'])}")
        print(f"verdict: {result['verdict']}  action: {result['action']}  "
              f"risk_level: {result['risk_level']}")
        print(f"outputs: {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
