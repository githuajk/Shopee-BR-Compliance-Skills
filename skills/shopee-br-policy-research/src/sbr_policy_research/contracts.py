"""契约常量与 `SkillInput` / `AuditResult` / `ModuleHandoff` 构造器。

所有构造器产出的是**已按 `contracts/*.schema.json` 约束填好必填字段**
的字典，引擎再逐条追加。模块名 / 契约版本在此集中定义，避免散在
各层里漂移。
"""

from __future__ import annotations

from datetime import datetime, timezone

#: 模块名（写入 `AuditResult.module` 与 `ModuleHandoff.from_module`）
MODULE_NAME = "shopee-br-policy-research"

#: 契约版本
CONTRACT_VERSION = "1.0.0"

#: 规则素材版本标识（写入 `AuditResult.rule_version`）
RULE_VERSION = "sbr-policy-assets/1.0.0"

__version__ = "1.0.0"


def now_iso() -> str:
    """ISO 8601 UTC 时间戳（秒级）。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_skill_input(request_id: str,
                      provenance_inputs: list[dict],
                      options: dict | None = None,
                      target_kind: str = "source_document",
                      target_ref: str | None = "research/") -> dict:
    """构造一份最小可用的 `SkillInput`（`task_type: policy_research`）。

    `provenance_inputs` 每项至少含 `path`（schema 必填）；`options` 里
    本模块认识的键是 `targets`（slug 过滤）/ `strict`（默认 True）/
    `to_module`，未知键忽略。
    """
    return {
        "request_id": request_id,
        "task_type": "policy_research",
        "target": {
            "kind": target_kind,
            "ref": target_ref,
            "count": None,
        },
        "products": [],
        "cases": [],
        "rules": [],
        "scope": {},
        "options": dict(options or {}),
        "provenance": {
            "inputs": list(provenance_inputs),
            "produced_at": now_iso(),
            "producer": f"{MODULE_NAME}/{__version__}",
        },
    }


def build_audit_result(request_id: str, target_ref: str,
                       verdict: str, risk_level: str, action: str,
                       reason: str, *,
                       rule_refs: list[dict] | None = None,
                       confidence: str = "confirmed",
                       requires_human_review: bool = False,
                       evidence_refs: list[dict] | None = None,
                       source_refs: list[str] | None = None,
                       notes: str | None = None,
                       review_rationale: str | None = None) -> dict:
    """一条来源核查结果（`contracts/audit_result.schema.json` 全量必填）。"""
    result = {
        "result_id": f"AR-{request_id}-{target_ref}",
        "request_id": request_id,
        "module": MODULE_NAME,
        "target_ref": target_ref,
        "verdict": verdict,
        "risk_level": risk_level,
        "action": action,
        "reason": reason,
        "rule_refs": list(rule_refs or []),
        "evidence_refs": list(evidence_refs or []),
        "confidence": confidence,
        "requires_human_review": bool(requires_human_review),
        "rule_version": RULE_VERSION,
        "provenance": {
            "produced_at": now_iso(),
            "producer": f"{MODULE_NAME}/{__version__}",
        },
    }
    if source_refs:
        result["provenance"]["source_refs"] = list(source_refs)
    if notes is not None:
        result["provenance"]["notes"] = notes
    if review_rationale is not None:
        result["review_rationale"] = review_rationale
    return result


def build_handoff(request_id: str, results: list[dict],
                 assumptions: list[str], known_gaps: list[str],
                 to_module: str = "shopee-br-compliance",
                 requires_human_review: bool = False,
                 unevaluated: list[dict] | None = None,
                 notes: str | None = None) -> dict:
    """`ModuleHandoff` —— `assumptions` 与 `known_gaps` **必填且非空**。"""
    if not assumptions:
        assumptions = ["本模块的核查结论均基于仓库内研究资产，未重新抓取线上页面。"]
    if not known_gaps:
        known_gaps = ["无已知缺口。"]
    return {
        "handoff_id": f"HO-PR-{request_id}",
        "from_module": MODULE_NAME,
        "to_module": to_module,
        "request_id": request_id,
        "payload_ref": {
            "artifact_ref": "audit_results.json",
            "inline": {"notes": notes} if notes else None,
            "record_count": len(results),
        },
        "contract_version": CONTRACT_VERSION,
        "produced_at": now_iso(),
        "assumptions": list(assumptions),
        "known_gaps": list(known_gaps),
        "unevaluated": list(unevaluated or []),
        "requires_human_review": bool(requires_human_review),
    }
