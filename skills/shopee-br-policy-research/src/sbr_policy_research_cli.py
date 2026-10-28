#!/usr/bin/env python3
"""命令行入口：Shopee BR 政策研究与来源核查（`shopee-br-policy-research`）。

```bash
# 全量来源核查（无需 SkillInput；三份契约产物写入 --out-dir）
env -u LD_LIBRARY_PATH python3 \
    skills/shopee-br-policy-research/src/sbr_policy_research_cli.py \
    --out-dir /tmp/pr-audit

# 带 SkillInput（task_type 必须为 policy_research）
env -u LD_LIBRARY_PATH python3 \
    skills/shopee-br-policy-research/src/sbr_policy_research_cli.py \
    --request-id REQ-PR-001 \
    --skill-input /tmp/pr-audit/skill_input.json \
    --out-dir /tmp/pr-out

# 只核查指定来源
... --targets br_anvisa_medicamentos_prescricao shopee_br_termos_de_servico
```

产出（写入 `--out-dir`）：

| 文件 | 契约 |
|---|---|
| `skill_input.json` | `contracts/skill_input.schema.json` |
| `audit_results.json` | `AuditResult[]`（来源核查结果） |
| `module_handoff.json` | `contracts/module_handoff.schema.json` |

**只读输入** —— 本脚本从不写回被读取的文件，也**不执行任何线上处置**
（重抓来源是维护流程，不是本入口的职责）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sbr_policy_research import (  # noqa: E402
    CONTRACT_VERSION,
    MODULE_NAME,
    RULE_VERSION,
    __version__,
    build_skill_input,
    run_policy_research,
)
from sbr_policy_research.errors import ContractError  # noqa: E402


def _write_artifacts(out_dir: str, bundle: dict) -> None:
    """写出三份契约产物（skill_input / audit_results / module_handoff）。"""
    os.makedirs(out_dir, exist_ok=True)
    for name, payload in (
        ("skill_input.json", bundle["skill_input"]),
        ("audit_results.json", bundle["results"]),
        ("module_handoff.json", bundle["handoff"]),
    ):
        with open(os.path.join(out_dir, name), "w",
                  encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="sbr_policy_research_cli",
        description="Audit Shopee Brazil policy research sources: registry "
                    "consistency, capture integrity, verbatim citations "
                    "(H4) and 503 source dispositions. Read-only; never "
                    "re-fetches or touches the platform.",
    )
    parser.add_argument("--request-id", default="REQ-POLICY-AUDIT",
                        help="unique request identifier (>= 4 chars)")
    parser.add_argument("--skill-input", default=None,
                        help="a skill_input.json "
                             "(task_type must be policy_research)")
    parser.add_argument("--out-dir", required=True,
                        help="directory for the outputs")
    parser.add_argument("--targets", action="append", default=[],
                        dest="target_list", metavar="SLUG",
                        help="limit the audit to specific source slugs / "
                             "rule ids (repeatable)")
    parser.add_argument("--no-strict", action="store_true",
                        help="citation failures and orphan captures become "
                             "results only (run still exits 0)")
    parser.add_argument("--to-module", default="shopee-br-compliance",
                        help="handoff target module "
                             "(default: shopee-br-compliance)")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress the summary")
    args = parser.parse_args(argv)

    options: dict = {
        "strict": not args.no_strict,
        "to_module": args.to_module,
    }
    if args.target_list:
        options["targets"] = list(args.target_list)

    try:
        if args.skill_input:
            try:
                with open(args.skill_input, encoding="utf-8") as handle:
                    skill_input = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                print(f"cannot read --skill-input {args.skill_input}: {exc}",
                      file=sys.stderr)
                return 2
            bundle = run_policy_research(skill_input, options=options)
        else:
            skill_input = build_skill_input(
                args.request_id,
                provenance_inputs=[
                    {"path": "research/", "kind": "source_document"}],
                options=options,
            )
            bundle = run_policy_research(skill_input, options=options)
    except ContractError as exc:
        print(f"contract error: {exc}", file=sys.stderr)
        return 2

    _write_artifacts(args.out_dir, bundle)

    if not args.quiet:
        findings = bundle.get("findings", {})
        verdicts: dict[str, int] = {}
        for result in bundle["results"]:
            verdicts[result["verdict"]] = verdicts.get(result["verdict"], 0) + 1
        print(f"module:  {MODULE_NAME}/{__version__}")
        print(f"rules:   {RULE_VERSION}  contract: {CONTRACT_VERSION}")
        print(f"sources: {findings.get('sources_total', 0)} "
              f"(captures ok {findings.get('captures_ok', 0)}, "
              f"quarantined {len(findings.get('quarantined', []))})")
        print(f"lib:     {findings.get('rules_total', 0)} "
              f"rules (citations ok {findings.get('citations_ok', 0)}/"
              f"{findings.get('rules_total', 0)})")
        print(f"verdicts: {verdicts or '{}'}")
        print(f"errors:  {len(bundle.get('errors', []))}")
        if bundle.get("errors"):
            for err in bundle["errors"][:10]:
                print(f"  - {err}")
        print(f"outputs: {args.out_dir}")

    return 0 if bundle.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
