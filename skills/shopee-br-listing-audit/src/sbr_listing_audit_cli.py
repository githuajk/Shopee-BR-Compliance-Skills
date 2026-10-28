#!/usr/bin/env python3
"""命令行入口：把商品批次跑成合规审核结果。

```bash
env -u LD_LIBRARY_PATH python3 skills/shopee-br-listing-audit/src/sbr_listing_audit_cli.py \
    --request-id REQ-LISTING-001 \
    --skill-input /tmp/in/skill_input.json \
    --out-dir /tmp/listing-out
```

产出（写入 `--out-dir`）：

| 文件 | 契约 |
|---|---|
| `audit_results.json` | `AuditResult[]`（`contracts/audit_result.schema.json`） |
| `audit_result.json` | 单条 `AuditResult`（同上；该 Schema 的 `type` 是 object） |
| `module_handoff.json` | `contracts/module_handoff.schema.json` |

**只读输入** —— 本脚本从不写回被读取的文件，也不执行任何线上处置。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sbr_listing_audit import __version__, audit_listing  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="sbr_listing_audit_cli",
        description="Audit Shopee BR product listings against the PI/RI/MED/LV "
                    "rule library and emit contract-shaped results (no online "
                    "enforcement is performed).",
    )
    parser.add_argument("--skill-input", required=True,
                        help="path to a SkillInput JSON file "
                             "(contracts/skill_input.schema.json)")
    parser.add_argument("--request-id", default=None,
                        help="override the request_id carried by the input")
    parser.add_argument("--out-dir", required=True,
                        help="directory for the outputs")
    parser.add_argument("--rule-prefix", action="append", default=None,
                        help="restrict the evaluation to a rule prefix; repeatable")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress the summary")
    args = parser.parse_args(argv)

    try:
        with open(args.skill_input, encoding="utf-8") as handle:
            skill_input = json.load(handle)
    except FileNotFoundError:
        print(f"input file does not exist: {args.skill_input}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"input file is unreadable: {args.skill_input}: {exc}",
              file=sys.stderr)
        return 2

    if args.request_id:
        skill_input["request_id"] = args.request_id

    options = {}
    if args.rule_prefix:
        options["rule_prefixes"] = tuple(args.rule_prefix)

    bundle = audit_listing(skill_input, options=options)

    os.makedirs(args.out_dir, exist_ok=True)
    results = bundle["results"]
    written = {
        "audit_results.json": results,
        "audit_result.json": (results[0] if results else None),
        "module_handoff.json": bundle["handoff"],
    }
    for name, payload in written.items():
        target = os.path.join(args.out_dir, name)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    if not args.quiet:
        verdicts: dict[str, int] = {}
        for result in results:
            verdicts[result["verdict"]] = verdicts.get(result["verdict"], 0) + 1
        distribution = ", ".join(
            f"{key}={verdicts[key]}" for key in sorted(verdicts))
        print(f"module:   shopee-br-listing-audit/{__version__}")
        print(f"products: {len(skill_input.get('products') or [])}")
        print(f"results:  {len(results)} ({distribution or 'none'})")
        print(f"errors:   {len(bundle['errors'])}")
        print(f"outputs:  {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
