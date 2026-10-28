"""管线：结果 → 聚合 → 汇总 → 报告。

产出三份契约产物：

* `AuditResult[]` —— 逐目标结论 + 整批结论（`contracts/audit_result.schema.json`）
* `AuditSummary` —— 结构化汇总（按目标 / 规则 / 模块 / 严重度分组）
* `ModuleHandoff` —— 交接记录（`contracts/module_handoff.schema.json`）

**绝不静默丢弃**：每条输入要么进入聚合，要么在 `errors[]` 里有记录。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from .aggregate import (
    ACTIONS,
    CONFIDENCES,
    DECISION_ACTIONS,
    REVIEW_ACTIONS,
    RISK_LEVELS,
    VERDICTS,
    aggregate,
)
from .contracts import audit_result_validator, module_handoff_validator
from .errors import STAGE_OUTPUT, ErrorLog
from .loader import load_results
from .matrix import MatrixUnavailable, RiskMatrix, load_matrix
from .render import render_report
from .rules import RuleIndex

MODULE_NAME = "shopee-br-reporting"
CONTRACT_VERSION = "1.0.0"
MODULE_VERSION = "1.0.0"
PRODUCER = f"{MODULE_NAME}/{MODULE_VERSION}"

#: 输出的文件名
SUMMARY_FILE = "audit_summary.json"
REPORT_FILE = "audit_report.md"
RESULTS_FILE = "audit_results.json"
HANDOFF_FILE = "module_handoff.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_summary(per_target: list[dict], batch: dict, raw_results: list[dict],
                  loaded, matrix: RiskMatrix, rule_index: RuleIndex,
                  request_id: str) -> dict:
    """构造结构化汇总。

    分组维度：按目标 / 按规则 / 按模块 / 按严重度。
    """
    counts = {v: sum(1 for r in per_target if r.get("verdict") == v) for v in VERDICTS}

    # --- 按规则 ---
    by_rule: dict[str, dict] = {}
    for record in raw_results:
        for ref in record.get("rule_refs") or []:
            rule_id = ref.get("rule_id")
            if not rule_id:
                continue
            entry = by_rule.setdefault(rule_id, {
                "rule_id": rule_id,
                "title": ref.get("title"),
                "source_tier": ref.get("source_tier"),
                "source_url": ref.get("source_url"),
                "targets": [],
                "modules": [],
                "actions": [],
            })
            target = str(record.get("target_ref") or "")
            if target and target not in entry["targets"]:
                entry["targets"].append(target)
            module = str(record.get("module") or "")
            if module and module not in entry["modules"]:
                entry["modules"].append(module)
            action = record.get("action")
            if action and action not in entry["actions"]:
                entry["actions"].append(action)

    # --- 按模块 ---
    by_module: dict[str, dict] = {}
    for record in raw_results:
        module = str(record.get("module") or "unknown")
        entry = by_module.setdefault(module, {
            "module": module,
            "result_count": 0,
            "targets": [],
            "verdicts": {v: 0 for v in VERDICTS},
            "actions": [],
            "unevaluated_count": 0,
            "error_count": 0,
        })
        entry["result_count"] += 1
        target = str(record.get("target_ref") or "")
        if target and target not in entry["targets"]:
            entry["targets"].append(target)
        verdict = record.get("verdict")
        if verdict in entry["verdicts"]:
            entry["verdicts"][verdict] += 1
        action = record.get("action")
        if action and action not in entry["actions"]:
            entry["actions"].append(action)
        entry["unevaluated_count"] += len(record.get("unevaluated") or [])
        entry["error_count"] += len(record.get("errors") or [])

    # --- 按严重度 ---
    by_severity: dict[str, dict] = {}
    for record in raw_results:
        level = record.get("risk_level")
        if not level:
            continue
        entry = by_severity.setdefault(level, {
            "risk_level": level,
            "result_count": 0,
            "targets": [],
            "actions": [],
        })
        entry["result_count"] += 1
        target = str(record.get("target_ref") or "")
        if target and target not in entry["targets"]:
            entry["targets"].append(target)
        action = record.get("action")
        if action and action not in entry["actions"]:
            entry["actions"].append(action)

    # --- 未评估项（并集） ---
    unevaluated: list[dict] = []
    seen_unevaluated: set[tuple[str, str]] = set()
    for record in raw_results:
        for entry in record.get("unevaluated") or []:
            key = (str(entry.get("rule_id")), str(entry.get("reason")))
            if key in seen_unevaluated:
                continue
            seen_unevaluated.add(key)
            item = dict(entry)
            item["module"] = record.get("module")
            item["target_ref"] = record.get("target_ref")
            unevaluated.append(item)

    # --- 待补齐证据 ---
    missing_evidence: list[dict] = []
    seen_evidence: set[tuple[str, str]] = set()
    for record in raw_results:
        target = str(record.get("target_ref") or "")
        for ref in record.get("evidence_refs") or []:
            if ref.get("provided"):
                continue
            key = (target, str(ref.get("evidence_id")))
            if key in seen_evidence:
                continue
            seen_evidence.add(key)
            missing_evidence.append({
                "target_ref": target,
                "evidence_id": ref.get("evidence_id"),
                "evidence_type": ref.get("evidence_type"),
                "artifact_ref": ref.get("artifact_ref"),
                "module": record.get("module"),
            })

    conflicts = list(batch.get("_conflicts") or [])
    for result in per_target:
        conflicts.extend(result.get("_conflicts") or [])
    conflicts = sorted(set(conflicts))

    # --- 需决策 / 待复核的发现 ---
    decision_findings = []
    review_findings = []
    for result in per_target:
        action = result.get("action")
        entry = {
            "target_ref": result.get("target_ref"),
            "verdict": result.get("verdict"),
            "risk_level": result.get("risk_level"),
            "action": action,
            "action_label": _action_label(action),
            "confidence": result.get("confidence"),
            "reason": result.get("reason"),
            "review_rationale": result.get("review_rationale"),
            "rule_refs": result.get("rule_refs") or [],
            "evidence_refs": result.get("evidence_refs") or [],
            "human_only": action in ("freeze_relist", "escalate_legal"),
        }
        if action in DECISION_ACTIONS:
            decision_findings.append(entry)
        elif action in REVIEW_ACTIONS:
            review_findings.append(entry)

    deterministic_count = sum(
        1 for r in per_target if r.get("action") in ("block", "freeze_relist", "escalate_legal"))
    human_only_count = sum(
        1 for r in per_target if r.get("action") in ("freeze_relist", "escalate_legal"))

    rule_meta = rule_index.lookup(batch.get("rule_refs") or [])

    return {
        "request_id": request_id,
        "produced_at": utc_now_iso(),
        "contract_version": CONTRACT_VERSION,
        "module": MODULE_NAME,
        "producer": PRODUCER,
        "rule_version": batch.get("rule_version") or "unknown",
        "source_modules": sorted({str(r.get("module")) for r in raw_results
                                  if r.get("module")}),
        "input_result_count": len(raw_results),
        "target_count": len(per_target),
        "batch_verdict": batch.get("verdict"),
        "batch_action": batch.get("action"),
        "batch_risk_level": batch.get("risk_level"),
        "verdict_counts": counts,
        "needs_human_review_count": sum(1 for r in per_target
                                        if r.get("requires_human_review")),
        "rule_count": len(rule_meta),
        "missing_evidence_count": len(missing_evidence),
        "unevaluated_count": len(unevaluated),
        "unevaluated_target_count": len({u["target_ref"] for u in unevaluated
                                         if u.get("target_ref")}),
        "error_count": len(batch.get("errors") or []),
        "deterministic_count": deterministic_count,
        "human_only_count": human_only_count,
        "rejected_results": list(loaded.rejected),
        "conflicts": conflicts,
        "per_target": [
            {
                "target_ref": r.get("target_ref"),
                "verdict": r.get("verdict"),
                "risk_level": r.get("risk_level"),
                "action": r.get("action"),
                "confidence": r.get("confidence"),
                "requires_human_review": r.get("requires_human_review"),
                "reason": r.get("reason"),
                "review_rationale": r.get("review_rationale"),
                "rule_refs": r.get("rule_refs") or [],
                "evidence_refs": r.get("evidence_refs") or [],
                "unevaluated": r.get("unevaluated") or [],
                "errors": r.get("errors") or [],
            }
            for r in per_target
        ],
        "by_rule": sorted(by_rule.values(), key=lambda e: e["rule_id"]),
        "by_module": sorted(by_module.values(), key=lambda e: e["module"]),
        "by_severity": [by_severity[k] for k in RISK_LEVELS if k in by_severity],
        "rules": rule_meta,
        "unevaluated": unevaluated,
        "missing_evidence": missing_evidence,
        "decision_findings": decision_findings,
        "review_findings": review_findings,
    }


def _action_label(action) -> str:
    from .render import ACTION_LABELS, HUMAN_ONLY_ACTIONS
    label = ACTION_LABELS.get(str(action), str(action))
    if action in HUMAN_ONLY_ACTIONS:
        label += "（需人工执行）"
    return label


def build_handoff(summary: dict, per_target: list[dict], batch: dict,
                  request_id: str, to_module: str = "shopee-br-compliance",
                  payload_ref: str | None = None) -> dict:
    """构造交接记录。`assumptions` 与 `known_gaps` **必填**。"""
    assumptions = [
        ("Aggregation follows contracts/risk_action_matrix.json verbatim: the "
         "verdict is the heaviest one declared by the contract, and the action "
         "keeps the most specific (finest-grained) action of that verdict band."),
        ("This module creates no new compliance finding. Every verdict, action "
         "and risk level it emits is derived from the input results by the "
         "contract matrix."),
        ("The rule library under rules/ is read-only for this module; rule "
         "category, severity, source tier and verification date are passed "
         "through unchanged."),
        ("Evidence references are passed through as references only; no "
         "credential content is copied into the report or the summary "
         "(hard constraint H5)."),
        ("A result whose declared verdict disagrees with the action implied by "
         "the contract matrix is reported as a warning; the heavier of the two "
         "is kept and the disagreement is recorded in provenance.notes."),
    ]
    if summary.get("rejected_results"):
        assumptions.append(
            f"{len(summary['rejected_results'])} input result(s) were rejected by "
            f"contracts/audit_result.schema.json and excluded from the aggregation; "
            f"they are listed in the report section 2 and in the summary.")

    gaps = [
        ("This module only aggregates. It cannot tell whether a rule that was "
         "not hit by any module would have hit: rules whose input fields were "
         "missing are reported as unevaluated, not as passed."),
    ]
    if summary.get("unevaluated_count"):
        gaps.append(
            f"{summary['unevaluated_count']} rule evaluation(s) could not be "
            f"completed because input data was missing; they are listed in the "
            f"report section 2 and are not counted as passes.")
    if summary.get("missing_evidence_count"):
        gaps.append(
            f"{summary['missing_evidence_count']} evidence item(s) are still "
            f"missing; the affected targets cannot be closed out until they are "
            f"provided.")
    if summary.get("conflicts"):
        gaps.append(
            f"{len(summary['conflicts'])} cross-module rule source conflict(s) "
            f"were found; they are recorded verbatim and were not resolved by "
            f"this module.")
    if summary.get("rejected_results"):
        gaps.append(
            f"{len(summary['rejected_results'])} input result(s) were rejected by "
            f"the contract and are therefore missing from this aggregate.")
    if len(summary.get("source_modules") or []) < 2:
        gaps.append(
            "Only one upstream module contributed results"
            + (f" ({summary['source_modules'][0]})" if summary.get("source_modules")
               else "")
            + "; the other review dimensions were not executed in this batch and "
              "must not be read as 'checked and clean'.")
    gaps.append(
        "No platform action was taken and none is proposed as executable: "
        "freeze_relist and escalate_legal are human_only (hard constraint H6).")

    return {
        "handoff_id": f"HO-REPORT-{request_id}",
        "from_module": MODULE_NAME,
        "to_module": to_module,
        "request_id": request_id,
        "payload_ref": {
            "artifact_ref": payload_ref,
            "inline": {
                "batch_verdict": batch.get("verdict"),
                "batch_action": batch.get("action"),
                "batch_risk_level": batch.get("risk_level"),
                "target_count": len(per_target),
                "verdict_counts": summary.get("verdict_counts"),
                "unevaluated_count": summary.get("unevaluated_count"),
                "decision_count": len(summary.get("decision_findings") or []),
                "review_count": len(summary.get("review_findings") or []),
            },
            "record_count": len(per_target),
        },
        "contract_version": CONTRACT_VERSION,
        "produced_at": summary.get("produced_at") or utc_now_iso(),
        "assumptions": assumptions,
        "known_gaps": gaps,
        "unevaluated": [
            {
                "rule_id": u.get("rule_id"),
                "reason": u.get("reason"),
                "missing_fields": list(u.get("missing_fields") or []),
            }
            for u in (summary.get("unevaluated") or [])
        ],
        "requires_human_review": bool(summary.get("needs_human_review_count")),
    }


def run_reporting(skill_input: dict, root: str | None = None,
                  out_dir: str | None = None) -> dict:
    """执行一次汇总与报告生成。

    参数
    ----
    skill_input:
        符合 `contracts/skill_input.schema.json` 的输入。
    root:
        仓库根（用于读契约与规则库）。缺省自动探测。
    out_dir:
        报告输出目录。缺省不落盘（只在返回值里给出内容）。
    """
    from .matrix import find_repo_root

    root = root or find_repo_root()
    log = ErrorLog()
    request_id = str(skill_input.get("request_id") or "")
    options = skill_input.get("options") or {}

    produced_at = utc_now_iso()

    # --- 契约矩阵：读不到则停止本模块 ---
    try:
        matrix = RiskMatrix(load_matrix(os.path.join(root, "contracts",
                                                       "risk_action_matrix.json")))
    except MatrixUnavailable as exc:
        log.fatal("contract_matrix", str(exc), {"root": root})
        return {
            "ok": False,
            "errors": log.items,
            "results": [],
            "summary": None,
            "handoff": None,
            "report": None,
        }

    # --- 装载结果 ---
    validator = audit_result_validator(root)
    loaded = load_results(
        result_files=options.get("result_files") or [],
        inline=options.get("results"),
        validator=validator,
        error_log=log,
    )

    if not loaded.accepted:
        log.error("input_load",
                  "no AuditResult satisfied contracts/audit_result.schema.json; "
                  "no report can be produced",
                  {"sources": loaded.sources, "rejected": len(loaded.rejected)})
        return {
            "ok": False,
            "errors": log.items,
            "results": [],
            "summary": None,
            "handoff": None,
            "report": None,
        }

    # --- 聚合 ---
    per_target, batch = aggregate(loaded.accepted, matrix, request_id, log)

    # --- 汇总 ---
    rule_index = RuleIndex.load(root)
    summary = build_summary(per_target, batch, loaded.accepted, loaded, matrix,
                            rule_index, request_id)
    summary["produced_at"] = produced_at

    # --- 补全 provenance ---
    source_refs = list(loaded.sources)
    notes = (f"aggregated {len(loaded.accepted)} result(s) from "
             f"{len(loaded.source_modules)} module(s) into {len(per_target)} target(s); "
             f"aggregation follows contracts/risk_action_matrix.json")
    if loaded.rejected:
        notes += (f"; {len(loaded.rejected)} result(s) rejected by the contract "
                  f"and excluded")
    if summary["conflicts"]:
        notes += (f"; {len(summary['conflicts'])} cross-module rule source "
                  f"conflict(s) recorded")
    for result in per_target + [batch]:
        result["provenance"] = {
            "produced_at": produced_at,
            "producer": PRODUCER,
            "source_refs": source_refs,
            "notes": notes,
        }
        result.pop("_conflicts", None)
        result.pop("_counts", None)
    summary["source_refs"] = source_refs
    summary["notes"] = notes

    # --- 交接 ---
    handoff = build_handoff(summary, per_target, batch, request_id)
    handoff_validator = module_handoff_validator(root)
    handoff_problems = handoff_validator.validate(handoff)
    if handoff_problems:
        log.error("contract_validation",
                  "the module handoff does not satisfy "
                  "contracts/module_handoff.schema.json: "
                  + "; ".join(handoff_problems[:3]),
                  {"problems": handoff_problems[:6]})

    # --- 渲染 ---
    products = _products_index(skill_input)
    report = render_report(summary, matrix, products)

    # --- 落盘 ---
    written: list[str] = []
    if out_dir:
        try:
            os.makedirs(out_dir, exist_ok=True)
            written = _write_outputs(out_dir, summary, report, per_target, batch,
                                      handoff, log)
        except OSError as exc:
            log.fatal(STAGE_OUTPUT,
                      f"the report output directory is not writable: {out_dir} ({exc})",
                      {"out_dir": out_dir, "error": str(exc)})

    return {
        "ok": not log.has_fatal,
        "errors": log.items,
        "results": per_target + [batch],
        "summary": summary,
        "handoff": handoff,
        "report": report,
        "written": written,
    }


def _products_index(skill_input: dict) -> dict:
    """`product_id -> {internal_sku, shop_id, title}` 的可选索引。"""
    index: dict[str, dict] = {}
    for product in skill_input.get("products") or []:
        product_id = product.get("product_id")
        if not product_id:
            continue
        index[str(product_id)] = {
            "internal_sku": product.get("internal_sku"),
            "shop_id": product.get("shop_id"),
            "title": product.get("title"),
        }
    return index


def _write_outputs(out_dir: str, summary: dict, report: str, per_target: list[dict],
                   batch: dict, handoff: dict, log: ErrorLog) -> list[str]:
    """写出四份产物。"""
    written: list[str] = []
    payloads = {
        SUMMARY_FILE: summary,
        RESULTS_FILE: per_target + [batch],
        HANDOFF_FILE: handoff,
    }
    for name, payload in payloads.items():
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        written.append(path)
    report_path = os.path.join(out_dir, REPORT_FILE)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(report)
    written.append(report_path)
    return written
