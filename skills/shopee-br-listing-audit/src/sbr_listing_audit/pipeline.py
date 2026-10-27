"""批次编排 —— `SkillInput` → `AuditResult[]` + `ModuleHandoff`。

本层只做编排与契约封装，判定逻辑全在 `engine.py`。

**绝不静默丢弃**：每条输入商品要么产出结论，要么产出错误说明。
输入不可读（商品缺 `product_id` / `title`）→ 记 error 并继续处理
其余商品，不中断整批。
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from . import matrix as matrix_mod
from .engine import (
    CONTRACT_VERSION,
    MODULE_NAME,
    AuditError,
    ListingAuditEngine,
    _utc_now,
)
from .rules import OWNED_PREFIXES

#: 批次级结果的目标引用前缀。
BATCH_TARGET = "listing-audit-batch"


def _provenance_digest(provenance: dict) -> str:
    payload = json.dumps(provenance, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def audit_listing(skill_input: dict, options: dict | None = None,
                  root: str | None = None) -> dict:
    """执行一次商品内容合规审核。

    参数
    ----
    skill_input:
        符合 `contracts/skill_input.schema.json` 的输入。
    options:
        模块私有选项。支持 `rule_prefixes`（限定规则前缀）与 `rules`
        （显式规则集，覆盖文件加载）。未知键被忽略。
    root:
        仓库根路径；缺省自动推导。

    返回
    ----
    dict，含：
      * ``results``   —— `AuditResult[]`
      * ``handoff``   —— `ModuleHandoff`
      * ``errors``    —— 全部错误记录
      * ``evaluations`` —— 逐商品的中间评估（供调试与测试）
    """
    options = dict(options or {})
    request_id = str(skill_input.get("request_id") or "")
    products = skill_input.get("products") or []
    provenance = skill_input.get("provenance") or {}

    engine = ListingAuditEngine(root=root, options=options)
    produced_at = _utc_now()

    results: list[dict] = []
    evaluations: list[dict] = []
    errors: list[dict] = list(engine.errors)

    for index, product in enumerate(products):
        if not isinstance(product, dict):
            errors.append(_error(
                f"ERR-LISTING-INPUT-{index:04d}", "input", "error",
                f"product at index {index} is not an object; it was not dropped "
                f"silently",
                {"index": index},
            ))
            results.append(_degraded_result(
                request_id=request_id,
                produced_at=produced_at,
                target_ref=f"input-index-{index}",
                reason=(f"the product at index {index} is not a JSON object and "
                        f"could not be audited"),
                error=_error(
                    f"ERR-LISTING-INPUT-{index:04d}", "input", "error",
                    f"product at index {index} is not an object; it was not dropped "
                    f"silently",
                    {"index": index},
                ),
                engine=engine,
            ))
            continue
        if not str(product.get("product_id") or "").strip():
            error = _error(
                f"ERR-LISTING-INPUT-{index:04d}", "input", "error",
                f"product at index {index} has no product_id; it was not dropped "
                f"silently",
                {"index": index,
                 "title": str(product.get("title") or "")[:80]},
            )
            errors.append(error)
            results.append(_degraded_result(
                request_id=request_id,
                produced_at=produced_at,
                target_ref=f"input-index-{index}",
                reason=(f"the product at index {index} carries no product_id and "
                        f"could not be audited"),
                error=error,
                engine=engine,
            ))
            continue
        if not str(product.get("title") or "").strip():
            error = _error(
                f"ERR-LISTING-INPUT-{index:04d}", "input", "error",
                f"product {product.get('product_id')} has an empty title; it cannot "
                f"be audited and was not dropped silently",
                {"product_id": product.get("product_id")},
            )
            errors.append(error)
            results.append(_degraded_result(
                request_id=request_id,
                produced_at=produced_at,
                target_ref=str(product.get("product_id")),
                reason=(f"product {product.get('product_id')} has an empty title; "
                        f"a listing without a title cannot be audited and was NOT "
                        f"counted as compliant"),
                error=error,
                engine=engine,
            ))
            continue

        evaluation = engine.evaluate_product(product)
        evaluations.append(evaluation)
        result = engine.build_result(evaluation, request_id, produced_at)
        if result is not None:
            results.append(result)

    # --- 引擎级错误并入批次错误 ---
    for item in engine.errors:
        if item not in errors:
            errors.append(item)

    handoff = _build_handoff(
        request_id=request_id,
        produced_at=produced_at,
        products=products,
        results=results,
        evaluations=evaluations,
        errors=errors,
        provenance=provenance,
        engine=engine,
    )

    return {
        "results": results,
        "handoff": handoff,
        "errors": errors,
        "evaluations": evaluations,
    }


def _error(error_id: str, stage: str, severity: str, message: str,
           context: dict | None = None) -> dict:
    item = {
        "error_id": error_id,
        "stage": stage,
        "severity": severity,
        "message": message,
    }
    if context:
        item["context"] = context
    return item


def _degraded_result(*, request_id: str, produced_at: str, target_ref: str,
                     reason: str, error: dict, engine: ListingAuditEngine) -> dict:
    """输入不可读时的**降级结论**。

    不是「没有结论」，而是「明确判定为不可评估 → 人工复核」。
    这保证 **每条输入要么产出结论，要么产出错误说明**（`SKILL.md` §7）。
    """
    action = engine._best_allowed("info", ("flag_for_review", "allow"))
    risk_level = "info"
    verdict = matrix_mod.verdict_for(engine.matrix, action)
    return {
        "result_id": f"RES-LISTING-{request_id}-{target_ref}"[:120],
        "request_id": request_id,
        "module": MODULE_NAME,
        "target_ref": target_ref,
        "verdict": verdict,
        "risk_level": risk_level,
        "action": action,
        "reason": reason,
        "rule_refs": [],
        "evidence_refs": [],
        "confidence": "signal",
        "requires_human_review": True,
        "review_rationale": ("the input record is unreadable, so no rule could be "
                             "evaluated; it must not be read as a compliant listing"),
        "rule_version": engine.rule_version(),
        "provenance": {
            "produced_at": produced_at,
            "producer": f"{MODULE_NAME}/{engine.module_version()}",
            "source_refs": [],
            "notes": "degraded result: the input record was not auditable",
        },
        "errors": [error],
        "unevaluated": [],
    }


def _build_handoff(*, request_id: str, produced_at: str, products: list,
                   results: list, evaluations: list, errors: list,
                   provenance: dict, engine: ListingAuditEngine) -> dict:
    """交接记录（`contracts/module_handoff.schema.json`）。

    `assumptions` 与 `known_gaps` **必填** —— 下游必须知道结论建立在
    什么前提上、哪些维度没跑。
    """
    unevaluated: list[dict] = []
    for evaluation in evaluations:
        for item in evaluation["unevaluated"]:
            unevaluated.append({
                "rule_id": item["rule"]["rule_id"],
                "reason": item["reason"],
                "missing_fields": item["missing_fields"],
            })

    assumptions = [
        "Detection is keyword- and field-based: a rule firing means the listing "
        "text matches a documented platform pattern, not that the physical item is "
        "what the text claims. Every finding needs a human to confirm the actual "
        "product.",
        "The action for each finding comes from contracts/risk_action_matrix.json; "
        "this module never invents an action, and a combination the matrix does not "
        "allow is downgraded rather than invented.",
        "Lexical screening (lexicon/**) is a signal layer only: a lexicon hit never "
        "produces a finding on its own and is recorded as evidence, not as a "
        "violation.",
        "Only rules with the PI / RI / MED / LV prefixes owned by this module are "
        "evaluated; IP (SBR-IP-*), duplicate (SBR-DUP-*) and case (SBR-RL-*/"
        "SBR-AU-*/SBR-AC-*) rules are out of scope and are left to their modules.",
        "SBR-LV-014 (inappropriate use of variations) is 'draft' in the rule "
        "library, so it never produces a conclusion and is reported as a known "
        "gap.",
    ]
    if engine.options.get("rule_prefixes"):
        assumptions.append(
            "The caller restricted the evaluation to rule prefix(es): "
            f"{engine.options['rule_prefixes']!r}."
        )

    gaps: list[str] = []
    if unevaluated:
        gaps.append(
            f"{len(unevaluated)} rule evaluation(s) were skipped because required "
            f"input was missing; those dimensions are NOT confirmed compliant."
        )
    if errors:
        gaps.append(
            f"{len(errors)} error(s) were recorded during the audit; see errors[] "
            f"for the affected records."
        )
    skipped = [rule for rule in engine.rules if rule.get("status") != "active"]
    if skipped:
        gaps.append(
            f"{len(skipped)} rule(s) are not 'active' and produced no conclusion: "
            + ", ".join(sorted(rule["rule_id"] for rule in skipped)) + "."
        )
    without_images = [evaluation for evaluation in evaluations
                      if not (evaluation["product"].get("images") or [])]
    if without_images:
        gaps.append(
            f"{len(without_images)} product(s) carry no image data; image-based "
            f"checks (image quality, OCR text, logos) were not evaluated for them."
        )
    if engine._matrix_error:
        gaps.append(
            "contracts/risk_action_matrix.json could not be read; the conservative "
            "fallback matrix (allow / flag_for_review only) was used, so no "
            "blocking action could be produced."
        )
    if not gaps:
        gaps.append("No known gaps were recorded for this batch.")

    requires_human_review = any(result.get("requires_human_review")
                                for result in results)

    return {
        "handoff_id": f"HO-LISTING-{request_id}"[:120],
        "from_module": MODULE_NAME,
        "to_module": "shopee-br-compliance",
        "request_id": request_id,
        "payload_ref": {
            "artifact_ref": None,
            "inline": {
                "audit_results": results,
                "provenance": provenance,
                "rule_version": (results[0].get("rule_version") if results
                                 else engine.rule_version()),
                "input_digest": _provenance_digest(provenance),
                "owned_rule_prefixes": list(OWNED_PREFIXES),
            },
            "record_count": len(results),
        },
        "contract_version": CONTRACT_VERSION,
        "produced_at": produced_at,
        "assumptions": assumptions,
        "known_gaps": gaps,
        "unevaluated": unevaluated,
        "requires_human_review": requires_human_review,
    }
