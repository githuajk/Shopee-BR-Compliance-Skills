#!/usr/bin/env python3
"""命令行入口：重复刊登与违规重发检查。

```bash
env -u LD_LIBRARY_PATH python3 skills/shopee-br-duplicate-detection/src/sbr_duplicate_detection_cli.py \
    --request-id REQ-DUP-001 \
    --skill-input /tmp/ingest-out/skill_input.json \
    --out-dir /tmp/dup-out
```

产出（写入 `--out-dir`）：

| 文件 | 契约 |
|---|---|
| `skill_input.json` | `contracts/skill_input.schema.json` |
| `audit_results.json` | `AuditResult[]` |
| `module_handoff.json` | `contracts/module_handoff.schema.json` |

**只读输入** —— 本脚本从不写回被读取的文件，也**不执行任何线上处置**
（发布/删除/冻结/申诉）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sbr_duplicate_detection import (  # noqa: E402
    CONTRACT_VERSION,
    MODULE_NAME,
    RULE_VERSION,
    __version__,
    detect_from_files,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="sbr_duplicate_detection_cli",
        description="Detect duplicate listings and prohibited relists on Shopee "
                    "Brazil. Produces candidates for human judgement; never "
                    "performs an online action.",
    )
    parser.add_argument("--skill-input", required=True,
                        help="path to a skill_input.json (contracts/skill_input.schema.json)")
    parser.add_argument("--out-dir", required=True,
                        help="directory for the outputs")
    parser.add_argument("--no-cross-store", action="store_true",
                        help="disable cross-store comparison (options.cross_store=false)")
    parser.add_argument("--similarity-threshold", type=float, default=None,
                        help="duplicate similarity threshold (default 0.62)")
    parser.add_argument("--relist-content-threshold", type=float, default=None,
                        help="relist content-fingerprint threshold (default 0.62)")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress the summary")
    args = parser.parse_args(argv)

    options: dict = {}
    if args.no_cross_store:
        options["cross_store"] = False
    if args.similarity_threshold is not None:
        options["similarity_threshold"] = args.similarity_threshold
    if args.relist_content_threshold is not None:
        options["relist_content_threshold"] = args.relist_content_threshold

    bundle = detect_from_files(args.skill_input, args.out_dir, options=options)

    if not args.quiet:
        results = bundle["results"]
        verdicts: dict[str, int] = {}
        actions: dict[str, int] = {}
        for result in results:
            verdicts[result["verdict"]] = verdicts.get(result["verdict"], 0) + 1
            actions[result["action"]] = actions.get(result["action"], 0) + 1
        print(f"module:  {MODULE_NAME}/{__version__}")
        print(f"rules:   {RULE_VERSION}  contract: {CONTRACT_VERSION}")
        print(f"products: {len(results)} result(s)")
        print(f"errors:  {len(bundle['errors'])}")
        print(f"verdicts: {verdicts}")
        print(f"actions:  {actions}")
        print(f"outputs: {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
