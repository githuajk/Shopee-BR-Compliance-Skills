#!/usr/bin/env python3
"""命令行入口：Shopee BR 合规审核主 Skill（编排层）。

```bash
env -u LD_LIBRARY_PATH python3 skills/shopee-br-compliance/src/sbr_compliance_cli.py \
    --request-id REQ-COMPLIANCE-001 \
    --out-dir /tmp/compliance-out \
    data/samples/demo_mass_update.xlsx
```

两种输入形态：

| 形态 | 参数 | 说明 |
|---|---|---|
| 文件 | `--input FILE...` | 先经 ingestion 规范化，再驱动其余模块 |
| 已规范化 | `--skill-input FILE` | 跳过 ingestion，直接驱动专业模块 |

也可用 `--product-file` 提供历史案件（`cases[]`）与 `--result-file` 提供
**既有** `AuditResult[]`（此时只做整合与汇总，不再重跑专业模块）。

产出（写入 `--out-dir`）：

| 文件 | 契约 |
|---|---|
| `audit_results.json` | `AuditResult[]`（逐商品 + 整批） |
| `audit_result.json` | 单条 `AuditResult` |
| `audit_summary.json` | 结构化汇总 |
| `audit_report.md` | 人读 Markdown 报告（六节） |
| `module_handoff.json` | `contracts/module_handoff.schema.json` |
| `routing_plan.json` | 分流决定 |
| `module_runs.json` | 每个模块的执行轨迹 |

**只读输入** —— 本脚本从不写回被读取的文件，**也不执行任何线上处置**。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sbr_compliance import (  # noqa: E402
    CONTRACT_VERSION,
    MODULE_NAME,
    __version__,
    run_compliance,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sbr_compliance_cli",
        description="Orchestrate a full Shopee Brazil compliance review: "
                    "route the request, drive the specialist modules through "
                    "their own entry points, integrate their results under "
                    "the frozen contract matrix, and report the gaps "
                    "(no online enforcement is performed).",
    )
    parser.add_argument("--request-id", default=None,
                        help="request identifier (>= 4 chars); taken from the "
                             "input when omitted")
    parser.add_argument("--out-dir", required=True,
                        help="directory for the outputs")
    parser.add_argument("--input", action="append", default=[],
                        dest="input_paths",
                        help="external file(s) to read through "
                             "shopee-br-data-ingestion (repeatable)")
    parser.add_argument("--skill-input", default=None,
                        help="a SkillInput JSON file (products[] already "
                             "normalised; skips ingestion)")
    parser.add_argument("--product-file", default=None,
                        help="a JSON file with products[] to use as the batch")
    parser.add_argument("--case-file", default=None,
                        help="a JSON file with cases[] (historical cases)")
    parser.add_argument("--result-file", action="append", default=[],
                        dest="result_files",
                        help="an existing AuditResult[] file to integrate "
                             "(repeatable); specialist modules are not re-run")
    parser.add_argument("--modules", default=None,
                        help="comma-separated module names to run "
                             "(default: decided by the routing table)")
    parser.add_argument("--root", default=None,
                        help="repository root; derived from the module "
                             "location when omitted")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress the summary")
    return parser


def _load_json(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _extract(payload, key: str) -> list:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _build_skill_input(args, request_id: str) -> tuple[dict, list]:
    """构造本模块的 `SkillInput`。返回 `(skill_input, input_paths)`。"""
    products: list = []
    cases: list = []
    scope: dict = {}
    provenance_inputs: list = []
    options: dict = {}

    if args.skill_input:
        document = _load_json(args.skill_input)
        if not isinstance(document, dict):
            raise SystemExit(f"--skill-input must contain a JSON object: "
                             f"{args.skill_input}")
        products.extend(document.get("products") or [])
        cases.extend(document.get("cases") or [])
        scope.update(document.get("scope") or {})
        provenance_inputs.append({"path": args.skill_input,
                                  "kind": "product_batch"})
        if not request_id:
            request_id = str(document.get("request_id") or "")

    if args.product_file:
        document = _load_json(args.product_file)
        products.extend(_extract(document, "products"))
        provenance_inputs.append({"path": args.product_file,
                                  "kind": "product_batch"})

    if args.case_file:
        document = _load_json(args.case_file)
        cases.extend(_extract(document, "cases"))
        provenance_inputs.append({"path": args.case_file,
                                  "kind": "case_history"})

    for path in args.input_paths:
        provenance_inputs.append({"path": path, "kind": "data_source"})

    if args.modules:
        options["modules"] = [m.strip() for m in args.modules.split(",")
                              if m.strip()]

    skill_input = {
        "request_id": request_id or "REQ-COMPLIANCE-UNSPECIFIED",
        "task_type": "orchestration",
        "target": {"kind": "product_batch"},
        "products": products,
        "cases": cases,
        "rules": [],
        "scope": scope,
        "options": options,
        "provenance": {
            "inputs": provenance_inputs or [{"path": "<none>",
                                             "kind": "product_batch"}],
            "produced_at": "",
            "producer": f"sbr_compliance_cli/{__version__}",
        },
    }
    return skill_input, list(args.input_paths)


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    if not args.request_id and not args.skill_input:
        print("错误：需要 --request-id 或 --skill-input 之一", file=sys.stderr)
        return 2

    try:
        skill_input, input_paths = _build_skill_input(args, args.request_id or "")
    except (OSError, ValueError) as exc:
        print(f"错误：输入不可读：{exc}", file=sys.stderr)
        return 2

    request_id = skill_input["request_id"]

    if args.result_files:
        # 只整合既有结果 —— 不重跑专业模块
        from sbr_compliance.integration import aggregate
        from sbr_compliance.matrix import RiskMatrix, load_matrix

        root = args.root or _default_root()
        matrix = RiskMatrix(load_matrix(os.path.join(root, "contracts",
                                                     "risk_action_matrix.json")))
        upstream: list = []
        for path in args.result_files:
            try:
                upstream.extend(_extract(_load_json(path), "results"))
            except (OSError, ValueError) as exc:
                print(f"错误：结果文件不可读：{path}（{exc}）", file=sys.stderr)
                return 2
        bundle = _integrate_only(request_id, upstream, matrix, args, skill_input)
    else:
        bundle = run_compliance(skill_input, root=args.root,
                                out_dir=args.out_dir,
                                input_paths=input_paths)

    if not args.quiet:
        summary = bundle.get("summary") or {}
        print(f"module:   {MODULE_NAME}/{__version__}  contract: {CONTRACT_VERSION}")
        print(f"request:  {request_id}")
        routing = bundle.get("routing") or {}
        print(f"route:    {' → '.join(routing.get('modules') or []) or '(无)'}")
        print(f"targets:  {summary.get('target_count', 0)}")
        print(f"results:  {summary.get('input_result_count', 0)} upstream result(s)")
        print(f"verdict:  {summary.get('batch_verdict')}  "
              f"action: {summary.get('batch_action')}  "
              f"risk_level: {summary.get('batch_risk_level')}")
        print(f"gaps:     {summary.get('unevaluated_count', 0)} unevaluated, "
              f"{summary.get('error_count', 0)} error(s)")
        print(f"errors:   {len(bundle.get('errors') or [])}")
        print(f"outputs:  {args.out_dir}")

    return 0 if bundle.get("ok") else 1


def _default_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", "..", ".."))


def _integrate_only(request_id: str, upstream: list, matrix, args,
                    skill_input: dict) -> dict:
    """只整合既有结果（不重跑专业模块）。"""
    from sbr_compliance.pipeline import _build_handoff, _build_summary
    from sbr_compliance.integration import aggregate
    from sbr_compliance.errors import ErrorLog
    from sbr_compliance.render import render_report
    import datetime

    log = ErrorLog()
    produced_at = datetime.datetime.now(datetime.timezone.utc).isoformat(
    ).replace("+00:00", "Z")
    per_target, batch = aggregate(upstream, matrix, request_id, log)
    if not per_target:
        log.error("integration", "no usable AuditResult to integrate", {})
        return {"ok": False, "errors": log.items, "results": [], "summary": None,
                "handoff": None, "report": None, "routing": None, "runs": [],
                "written": []}

    class _Decision:
        explicit = False

        def to_dict(self):
            return {"stages": [], "modules": [], "reasons": {},
                    "skipped": {}, "explicit": False}

        def note(self):
            return "本次执行模块：(仅整合既有结果，未重跑专业模块)"

    decision = _Decision()
    summary = _build_summary(per_target, batch, upstream, [], decision, matrix,
                             request_id, produced_at)
    notes = decision.note()
    source_refs = list(args.result_files)
    for result in per_target + [batch]:
        result["provenance"] = {
            "produced_at": produced_at,
            "producer": f"{MODULE_NAME}/{__version__}",
            "source_refs": source_refs,
            "notes": notes,
        }
        result.pop("_conflicts", None)
        result.pop("_counts", None)
    summary["source_refs"] = source_refs
    summary["notes"] = notes
    handoff = _build_handoff(summary, per_target, batch, decision, [],
                             request_id, produced_at)
    report = render_report(summary, matrix, skill_input.get("products") or [])

    written: list = []
    os.makedirs(args.out_dir, exist_ok=True)
    for name, payload in (
            ("audit_results.json", per_target + [batch]),
            ("audit_result.json", per_target[0] if per_target else None),
            ("audit_summary.json", summary),
            ("module_handoff.json", handoff),
            ("routing_plan.json", decision.to_dict()),
    ):
        if payload is None:
            continue
        path = os.path.join(args.out_dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        written.append(path)
    report_path = os.path.join(args.out_dir, "audit_report.md")
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(report)
    written.append(report_path)

    return {
        "ok": not log.has_fatal,
        "errors": log.items,
        "results": per_target + [batch],
        "summary": summary,
        "handoff": handoff,
        "report": report,
        "routing": decision.to_dict(),
        "runs": [],
        "written": written,
    }


if __name__ == "__main__":
    sys.exit(main())
