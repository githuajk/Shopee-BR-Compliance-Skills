"""管线：分流 → 显式驱动各模块 → 整合 → 汇总 → 交接。

产出（符合冻结契约）：

* `AuditResult[]` —— 逐商品最终结论 + 整批结论
  （`contracts/audit_result.schema.json`）
* `ModuleHandoff` —— 交接记录（`contracts/module_handoff.schema.json`）
* `AuditSummary` —— 结构化汇总（按目标 / 规则 / 模块 / 严重度分组）
* Markdown 报告 —— 人读版（六节结构 + 硬约束自检）

**绝不静默丢弃**：每个模块要么产出结论，要么在 `errors[]` / `known_gaps`
里有明确记录。

纯标准库实现。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from .contracts import audit_result_validator, module_handoff_validator
from .driver import ModuleRun, run_module, skill_md_digest
from .errors import (
    STAGE_INTEGRATE,
    STAGE_OUTPUT,
    STAGE_REPORT,
    STAGE_ROUTE,
    ErrorLog,
)
from .integration import VERDICTS, aggregate
from .matrix import MatrixUnavailable, RiskMatrix, load_matrix
from .registry import MODULE_NAME, spec_for
from .render import render_report
from .routing import decide

CONTRACT_VERSION = "1.0.0"
MODULE_VERSION = "1.0.0"
PRODUCER = f"{MODULE_NAME}/{MODULE_VERSION}"

#: 输出文件名
RESULTS_FILE = "audit_results.json"
RESULT_FILE = "audit_result.json"
SUMMARY_FILE = "audit_summary.json"
REPORT_FILE = "audit_report.md"
HANDOFF_FILE = "module_handoff.json"
ROUTE_FILE = "routing_plan.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_compliance(skill_input: dict, *, root: str | None = None,
                   out_dir: str | None = None,
                   input_paths: list | None = None) -> dict:
    """执行一次完整的合规审核编排。

    参数
    ----
    skill_input:
        符合 `contracts/skill_input.schema.json` 的输入。
    root:
        仓库根（用于读契约与驱动各模块的 CLI）。缺省自动推导。
    out_dir:
        产出目录。缺省不落盘（只在返回值里给出内容）。
    input_paths:
        交给 `shopee-br-data-ingestion` 的外部文件路径。

    返回
    ----
    dict，含 `results` / `summary` / `handoff` / `report` / `errors` /
    `runs` / `routing` / `written`。
    """
    root = root or _default_root()
    log = ErrorLog()
    produced_at = utc_now_iso()

    request_id = str(skill_input.get("request_id") or "")
    options = dict(skill_input.get("options") or {})
    products = list(skill_input.get("products") or [])
    cases = list(skill_input.get("cases") or [])
    scope = dict(skill_input.get("scope") or {})
    rules = list(skill_input.get("rules") or [])
    provenance = dict(skill_input.get("provenance") or {})
    input_paths = list(input_paths or [])

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
            "routing": None,
            "runs": [],
            "written": [],
        }

    # --- 分流（两阶段） ---
    # 第一阶段只判断 ingestion；ingestion 跑完后才知道商品长什么样，
    # 三个专业维度的取舍必须基于**真实的** products[]。
    ingestion_decision = decide(options, products, cases, input_paths,
                                 stage="ingestion")
    decision = ingestion_decision
    for stage, reason in decision.skipped.items():
        if stage.startswith("unknown:"):
            log.error(STAGE_ROUTE, reason, {"stage": stage})
    log_trail = [decision.note()]

    # --- 执行 ---
    runs: list[ModuleRun] = []
    ingested_products: list[dict] = list(products)
    ingested_cases: list[dict] = list(cases)
    effective_provenance = dict(provenance)
    result_files: list[str] = []
    module_dirs: dict[str, str] = {}

    work_root = out_dir or os.path.join(root, ".sbr-compliance-work")
    os.makedirs(work_root, exist_ok=True)

    stage_modules = {
        "ingestion": "shopee-br-data-ingestion",
        "content_audit": "shopee-br-listing-audit",
        "ip": "shopee-br-ip-review",
        "duplicate": "shopee-br-duplicate-detection",
        "reporting": "shopee-br-reporting",
    }

    def _execute(stage: str):
        """驱动一个阶段，返回 `ModuleRun`。"""
        module_name = stage_modules[stage]
        spec = spec_for(module_name)
        if spec is None:
            log.error(STAGE_ROUTE, f"module {module_name} is not registered",
                      {"stage": stage})
            return None
        stage_dir = os.path.join(work_root, stage)
        module_dirs[module_name] = stage_dir

        if stage == "ingestion":
            run = run_module(spec, root, request_id=request_id,
                              out_dir=stage_dir, input_paths=input_paths,
                              log=log)
            if run.ok:
                skill_input_path = run.artifacts.get("skill_input.json")
                if skill_input_path:
                    try:
                        with open(skill_input_path, encoding="utf-8") as handle:
                            ingested = json.load(handle)
                        ingested_products[:] = list(ingested.get("products") or [])
                        ingested_cases[:] = list(ingested.get("cases") or [])
                        effective_provenance.update(ingested.get("provenance") or {})
                    except (OSError, ValueError) as exc:
                        log.error(STAGE_INTEGRATE,
                                  f"the ingestion output skill_input.json could "
                                  f"not be read: {exc}",
                                  {"module": module_name})
                result_files.extend(
                    path for name, path in run.artifacts.items()
                    if name in ("audit_results.json", "audit_result.json")
                )
            return run

        if stage == "reporting":
            return run_module(spec, root, request_id=request_id,
                              out_dir=stage_dir, result_files=result_files,
                              skill_input_path=None, log=log)

        # 内容审核 / IP / 重复检测：构造 SkillInput 并驱动
        payload = {
            "request_id": request_id,
            "task_type": spec.task_type,
            "target": {"kind": "product_batch"},
            "products": ingested_products,
            "cases": ingested_cases,
            "rules": rules,
            "scope": scope,
            "options": {},
            "provenance": effective_provenance or {
                "inputs": [{"path": "<orchestrated>",
                            "kind": "product_batch"}],
                "produced_at": produced_at,
                "producer": PRODUCER,
            },
        }
        skill_input_path = os.path.join(stage_dir, "skill_input.json")
        os.makedirs(stage_dir, exist_ok=True)
        with open(skill_input_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        run = run_module(spec, root, request_id=request_id,
                          out_dir=stage_dir,
                          skill_input_path=skill_input_path, log=log)
        if run.ok:
            result_files.extend(
                path for name, path in run.artifacts.items()
                if name in ("audit_results.json", "audit_result.json")
            )
        return run

    def _record(run) -> None:
        runs.append(run)
        log_trail.extend(run.trail)
        if not run.ok:
            log.error(STAGE_ROUTE,
                      f"the {run.module_name} dimension was NOT executed: "
                      f"{run.reason}",
                      {"module": run.module_name})

    # --- 阶段一：ingestion ---
    if "ingestion" in decision.stages:
        if not input_paths:
            log.warning(STAGE_ROUTE,
                        "ingestion was selected but no input file was given; "
                        "the ingestion stage was skipped and the existing "
                        "products[] were used as-is",
                        {"stage": "ingestion"})
        else:
            _record(_execute("ingestion"))

    # --- 阶段二：基于**真实的** products[] 重新分流 ---
    decision = decide(options, ingested_products, ingested_cases, input_paths,
                      stage="specialists")
    if not decision.explicit:
        log_trail.append(decision.note())
    for stage, reason in decision.skipped.items():
        if stage.startswith("unknown:"):
            log.error(STAGE_ROUTE, reason, {"stage": stage})

    for stage in decision.stages:
        run = _execute(stage)
        if run is not None:
            _record(run)

    # --- 整合：只整合**通过契约校验**的上游结果 ---
    upstream_results: list[dict] = []
    upstream_sources: list[str] = []
    for run in runs:
        if not run.ok:
            continue
        if run.module_name == "shopee-br-reporting":
            # reporting 的产出是**汇总**，不是上游判定 —— 不再二次聚合，
            # 但它的人读报告要带进最终产物。
            continue
        upstream_results.extend(run.results)
        for name, path in run.artifacts.items():
            if name in ("audit_results.json", "audit_result.json"):
                upstream_sources.append(path)

    if not upstream_results:
        log.error(STAGE_INTEGRATE,
                  "no module produced a contract-conformant AuditResult; no "
                  "integrated conclusion can be produced (this is NOT a pass)",
                  {"runs": [{"module": r.module_name, "ok": r.ok,
                             "reason": r.reason} for r in runs]})
        return {
            "ok": False,
            "errors": log.items,
            "results": [],
            "summary": None,
            "handoff": None,
            "report": None,
            "routing": decision.to_dict(),
            "runs": [_run_view(r) for r in runs],
            "written": [],
        }

    per_target, batch = aggregate(upstream_results, matrix, request_id, log)

    # --- 汇总 ---
    summary = _build_summary(per_target, batch, upstream_results, runs,
                              decision, matrix, request_id, produced_at)

    # --- provenance ---
    source_refs = list(upstream_sources)
    for run in runs:
        if run.ok:
            source_refs.append(os.path.join(
                "skills", run.module_name, "SKILL.md"))
    notes = "; ".join(log_trail)
    if summary["rejected_result_count"]:
        notes += (f"; {summary['rejected_result_count']} upstream result(s) "
                  f"rejected by the contract and excluded")
    if summary["conflicts"]:
        notes += (f"; {len(summary['conflicts'])} cross-module rule source "
                  f"conflict(s) recorded verbatim")
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
    handoff = _build_handoff(summary, per_target, batch, decision, runs,
                              request_id, produced_at)
    handoff_validator = module_handoff_validator(root)
    handoff_problems = handoff_validator.validate(handoff)
    if handoff_problems:
        log.error("contract_validation",
                  "the module handoff does not satisfy "
                  "contracts/module_handoff.schema.json: "
                  + "; ".join(handoff_problems[:3]),
                  {"problems": handoff_problems[:6]})

    # --- 校验自己的产出 ---
    validator = audit_result_validator(root)
    for result in per_target + [batch]:
        problems = validator.validate(result)
        if problems:
            log.error("contract_validation",
                      "the integrated result does not satisfy "
                      "contracts/audit_result.schema.json: "
                      + "; ".join(problems[:3]),
                      {"result_id": result.get("result_id"),
                       "problems": problems[:6]})

    # --- 报告 ---
    report = render_report(summary, matrix, ingested_products)

    # --- 落盘 ---
    written: list[str] = []
    if out_dir:
        try:
            os.makedirs(out_dir, exist_ok=True)
            written = _write_outputs(out_dir, summary, report, per_target, batch,
                                      handoff, decision, runs, log)
        except OSError as exc:
            log.fatal(STAGE_OUTPUT,
                      f"the output directory is not writable: {out_dir} ({exc})",
                      {"out_dir": out_dir, "error": str(exc)})

    return {
        "ok": not log.has_fatal,
        "errors": log.items,
        "results": per_target + [batch],
        "summary": summary,
        "handoff": handoff,
        "report": report,
        "routing": decision.to_dict(),
        "runs": [_run_view(r) for r in runs],
        "products": ingested_products,
        "written": written,
    }


def _default_root() -> str:
    """推导仓库根。

    用 `matrix.find_repo_root()` —— 它**向上查找**含
    `contracts/risk_action_matrix.json` 的目录，而不是按固定层数上溯。
    固定层数在这里是错的：`src/sbr_compliance/` 上溯四级到的是
    `skills/shopee-br-compliance/`（模块目录），不是仓库根。
    """
    from .matrix import find_repo_root
    return find_repo_root()


def _run_view(run: ModuleRun) -> dict:
    """一次模块执行的对外视图。"""
    return {
        "module": run.module_name,
        "ok": run.ok,
        "reason": run.reason,
        "result_count": len(run.results),
        "rejected_count": len(run.rejected),
        "out_dir": run.out_dir,
        "trail": list(run.trail),
        "artifacts": dict(run.artifacts),
    }


def _build_summary(per_target, batch, upstream_results, runs, decision,
                   matrix: RiskMatrix, request_id: str,
                   produced_at: str) -> dict:
    """构造结构化汇总。"""
    counts = {v: sum(1 for r in per_target if r.get("verdict") == v)
              for v in VERDICTS}

    by_module: dict[str, dict] = {}
    rejected_count = 0
    for run in runs:
        rejected_count += len(run.rejected)
        entry = by_module.setdefault(run.module_name, {
            "module": run.module_name,
            "executed": run.ok,
            "result_count": 0,
            "targets": [],
            "actions": [],
            "reason": run.reason,
        })
        if not run.ok:
            continue
        for record in run.results:
            entry["result_count"] += 1
            target = str(record.get("target_ref") or "")
            if target and target not in entry["targets"]:
                entry["targets"].append(target)
            action = record.get("action")
            if action and action not in entry["actions"]:
                entry["actions"].append(action)

    by_rule: dict[str, dict] = {}
    for record in upstream_results:
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
            })
            target = str(record.get("target_ref") or "")
            if target and target not in entry["targets"]:
                entry["targets"].append(target)
            module = str(record.get("module") or "")
            if module and module not in entry["modules"]:
                entry["modules"].append(module)

    unevaluated: list[dict] = []
    seen_unevaluated: set[tuple[str, str]] = set()
    for record in upstream_results:
        for entry in record.get("unevaluated") or []:
            key = (str(entry.get("rule_id")), str(entry.get("reason")))
            if key in seen_unevaluated:
                continue
            seen_unevaluated.add(key)
            item = dict(entry)
            item["module"] = record.get("module")
            item["target_ref"] = record.get("target_ref")
            unevaluated.append(item)

    missing_evidence: list[dict] = []
    seen_evidence: set[tuple[str, str]] = set()
    for record in upstream_results:
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

    deterministic_count = sum(
        1 for r in per_target if r.get("action") in ("block", "freeze_relist",
                                                    "escalate_legal"))
    human_only_count = sum(
        1 for r in per_target if r.get("action") in ("freeze_relist",
                                                    "escalate_legal"))

    return {
        "request_id": request_id,
        "produced_at": produced_at,
        "contract_version": CONTRACT_VERSION,
        "module": MODULE_NAME,
        "producer": PRODUCER,
        "rule_version": batch.get("rule_version") or "unknown",
        "source_modules": sorted({str(r.get("module")) for r in upstream_results
                                  if r.get("module")}),
        "input_result_count": len(upstream_results),
        "target_count": len(per_target),
        "batch_verdict": batch.get("verdict"),
        "batch_action": batch.get("action"),
        "batch_risk_level": batch.get("risk_level"),
        "verdict_counts": counts,
        "needs_human_review_count": sum(1 for r in per_target
                                        if r.get("requires_human_review")),
        "missing_evidence_count": len(missing_evidence),
        "unevaluated_count": len(unevaluated),
        "unevaluated_target_count": len({u["target_ref"] for u in unevaluated
                                         if u.get("target_ref")}),
        "error_count": len(batch.get("errors") or []),
        "deterministic_count": deterministic_count,
        "human_only_count": human_only_count,
        "rejected_result_count": rejected_count,
        "conflicts": conflicts,
        "executed_modules": [r.module_name for r in runs if r.ok],
        "not_executed_modules": [{"module": r.module_name, "reason": r.reason}
                                 for r in runs if not r.ok],
        "routing": decision.to_dict(),
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
        "unevaluated": unevaluated,
        "missing_evidence": missing_evidence,
    }


def _build_handoff(summary: dict, per_target: list[dict], batch: dict,
                   decision, runs, request_id: str,
                   produced_at: str) -> dict:
    """构造交接记录。`assumptions` 与 `known_gaps` **必填**。"""
    assumptions = [
        ("Aggregation follows contracts/risk_action_matrix.json verbatim: the "
         "verdict is derived from the heaviest sanitised action, and the action "
         "keeps the most specific (finest-grained) action of that verdict band."),
        ("This module creates no compliance finding of its own. Every verdict, "
         "action, rule reference and evidence reference it emits is carried "
         "over from the specialist modules it drove; the rule semantics, source "
         "tiers and verification dates are passed through unchanged."),
        ("The specialist modules were driven through their own command-line "
         "entry points after their SKILL.md files were read explicitly; the "
         "platform does not guarantee automatic Skill-to-Skill calls, so the "
         "workflow is a file-level convention, not a runtime call."),
        ("Evidence references are passed through as references only; no "
         "credential content is copied into the integrated result or the report "
         "(hard constraint H5)."),
        ("A module that could not be executed is reported as NOT EXECUTED with "
         "the reason; its review dimension is never counted as compliant "
         "(hard constraint H3)."),
        ("No platform action was taken and none is proposed as executable: "
         "freeze_relist and escalate_legal are human_only (hard constraint H6)."),
    ]
    if decision.explicit:
        assumptions.append(
            "The module set was chosen by the caller (options.modules); the "
            "dimensions left out are the caller's responsibility, not a "
            "finding of compliance.")

    gaps: list[str] = []
    for run in runs:
        if not run.ok:
            gaps.append(
                f"{run.module_name} was NOT executed ({run.reason}); the "
                f"dimension it covers was not assessed and must not be read as "
                f"'checked and clean'.")
    for stage, reason in decision.skipped.items():
        if stage.startswith("unknown:"):
            continue
        gaps.append(f"the {stage} dimension was not selected: {reason}")
    if summary.get("unevaluated_count"):
        gaps.append(
            f"{summary['unevaluated_count']} rule evaluation(s) could not be "
            f"completed because required input was missing; they are listed in "
            f"the report's data-gap section and are NOT counted as passes.")
    if summary.get("missing_evidence_count"):
        gaps.append(
            f"{summary['missing_evidence_count']} evidence item(s) are still "
            f"missing; the affected targets cannot be closed out until they are "
            f"provided.")
    if summary.get("rejected_result_count"):
        gaps.append(
            f"{summary['rejected_result_count']} upstream result(s) were "
            f"rejected by contracts/audit_result.schema.json and are therefore "
            f"missing from this aggregate.")
    if summary.get("conflicts"):
        gaps.append(
            f"{len(summary['conflicts'])} cross-module rule source conflict(s) "
            f"were found; they are recorded verbatim and were not resolved by "
            f"this module.")
    if len(summary.get("source_modules") or []) < 2:
        gaps.append(
            "Only one upstream module contributed results"
            + (f" ({summary['source_modules'][0]})"
               if summary.get("source_modules") else "")
            + "; the other review dimensions were not executed in this batch "
              "and must not be read as 'checked and clean'.")
    if not gaps:
        gaps.append("No known gaps were recorded for this batch.")

    return {
        "handoff_id": f"HO-COMPLIANCE-{request_id}"[:120],
        "from_module": MODULE_NAME,
        "to_module": "human-review",
        "request_id": request_id,
        "payload_ref": {
            "artifact_ref": None,
            "inline": {
                "batch_verdict": batch.get("verdict"),
                "batch_action": batch.get("action"),
                "batch_risk_level": batch.get("risk_level"),
                "target_count": len(per_target),
                "verdict_counts": summary.get("verdict_counts"),
                "unevaluated_count": summary.get("unevaluated_count"),
                "executed_modules": summary.get("executed_modules"),
            },
            "record_count": len(per_target),
        },
        "contract_version": CONTRACT_VERSION,
        "produced_at": produced_at,
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


def _write_outputs(out_dir: str, summary: dict, report: str, per_target: list[dict],
                   batch: dict, handoff: dict, decision, runs,
                   log: ErrorLog) -> list[str]:
    """写出契约产物。"""
    written: list[str] = []
    payloads = {
        RESULTS_FILE: per_target + [batch],
        RESULT_FILE: (per_target[0] if per_target else None),
        SUMMARY_FILE: summary,
        HANDOFF_FILE: handoff,
        ROUTE_FILE: decision.to_dict(),
    }
    for name, payload in payloads.items():
        if payload is None:
            continue
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        written.append(path)
    report_path = os.path.join(out_dir, REPORT_FILE)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(report)
    written.append(report_path)

    runs_path = os.path.join(out_dir, "module_runs.json")
    with open(runs_path, "w", encoding="utf-8") as handle:
        json.dump([_run_view(r) for r in runs], handle, ensure_ascii=False,
                  indent=2)
        handle.write("\n")
    written.append(runs_path)
    return written
