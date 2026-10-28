#!/usr/bin/env python3
"""命令行入口：把多模块的审核结果汇总成 JSON 汇总 + Markdown 报告。

```bash
env -u LD_LIBRARY_PATH python3 skills/shopee-br-reporting/src/sbr_reporting_cli.py \
    --request-id REQ-REPORT-001 \
    --out-dir /tmp/report-out \
    --result-file /tmp/audit-out/audit_results.json \
    --skill-input /tmp/ingest-out/skill_input.json
```

产出（写入 `--out-dir`）：

| 文件 | 契约 |
|---|---|
| `audit_summary.json` | 结构化汇总（按目标 / 规则 / 模块 / 严重度分组） |
| `audit_report.md` | 六节 Markdown 报告 |
| `audit_results.json` | `AuditResult[]`（逐目标 + 整批） |
| `module_handoff.json` | `contracts/module_handoff.schema.json` |

**只读输入** —— 本脚本从不写回被读取的文件。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sbr_reporting import run_reporting  # noqa: E402


def _load_json(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _base_input(request_id: str, result_files: list[str]) -> dict:
    """最小 `SkillInput` —— 结果文件是本模块的输入来源。"""
    return {
        "request_id": request_id,
        "task_type": "reporting",
        "target": {"kind": "audit_result_set", "ref": None, "count": None},
        "products": [],
        "cases": [],
        "rules": [],
        "scope": {},
        "options": {"result_files": list(result_files)},
        "provenance": {
            "inputs": [{"path": p, "kind": "audit_result_set"} for p in result_files],
            "produced_at": "",
            "producer": "sbr_reporting_cli",
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="sbr_reporting_cli",
        description="Aggregate Shopee BR compliance AuditResults into a "
                    "contract-conformant summary and a Markdown report.",
    )
    parser.add_argument("--request-id", required=True,
                        help="unique request identifier (>= 4 chars)")
    parser.add_argument("--out-dir", required=True,
                        help="directory for the outputs")
    parser.add_argument("--result-file", action="append", default=[],
                        dest="result_files",
                        help="a file holding AuditResult[] (repeatable)")
    parser.add_argument("--skill-input", default=None,
                        help="a SkillInput JSON file (for products[] and provenance)")
    parser.add_argument("--to-module", default="shopee-br-compliance",
                        help="handoff target module (default: shopee-br-compliance)")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress the summary")
    args = parser.parse_args(argv)

    skill_input = _base_input(args.request_id, args.result_files)
    if args.skill_input:
        loaded = _load_json(args.skill_input)
        if not isinstance(loaded, dict):
            raise SystemExit(f"--skill-input must contain a JSON object: {args.skill_input}")
        skill_input.update(loaded)
        skill_input["request_id"] = loaded.get("request_id") or args.request_id
        skill_input["task_type"] = "reporting"
        options = dict(skill_input.get("options") or {})
        options["result_files"] = list(args.result_files)
        skill_input["options"] = options

    bundle = run_reporting(skill_input, out_dir=args.out_dir)
    if bundle.get("handoff"):
        bundle["handoff"]["to_module"] = args.to_module
        handoff_path = os.path.join(args.out_dir, "module_handoff.json")
        if os.path.exists(handoff_path):
            with open(handoff_path, "w", encoding="utf-8") as handle:
                json.dump(bundle["handoff"], handle, ensure_ascii=False, indent=2)
                handle.write("\n")

    if not args.quiet:
        summary = bundle.get("summary") or {}
        print(f"request:  {args.request_id}")
        print(f"targets:  {summary.get('target_count', 0)}")
        print(f"results:  {summary.get('input_result_count', 0)} from "
              f"{len(summary.get('source_modules') or [])} module(s)")
        print(f"verdict:  {summary.get('batch_verdict')}  "
              f"action: {summary.get('batch_action')}  "
              f"risk_level: {summary.get('batch_risk_level')}")
        print(f"gaps:     {summary.get('unevaluated_count', 0)} unevaluated, "
              f"{summary.get('error_count', 0)} error(s)")
        print(f"errors:   {len(bundle.get('errors') or [])}")
        print(f"outputs:  {args.out_dir}")

    return 0 if bundle.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
