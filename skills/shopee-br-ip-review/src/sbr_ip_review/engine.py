"""知识产权与授权风险筛查的编排层。

职责：把 `rules.py`（规则装载）、`evaluator.py`（条件求值）、
`matrix.py`（契约矩阵）组装成符合冻结契约的产出。

**硬约束（本模块的立身之本）**

* **H1** —— IP 四类的结论**恒为** `confidence="signal"` 且
  `requires_human_review=true`。关键词或 logo 命中只是**筛查信号**；
  仅权利人投诉、书面授权或平台投诉通知可确立侵权。本模块**绝不**
  输出 `confirmed` 或 `likely` 的 IP 结论。
* **H2** —— 阻断类动作只能来自 `platform_official` / `law` 的
  `active` 规则。
* **H3** —— 缺失必需输入必须记入 `unevaluated[]`，**不得**判通过。
* **H5** —— `evidence_refs` 只存路径，不存凭证内容。
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from . import evaluator, matrix as matrix_mod, rules as rules_mod

#: 模块名（写入 `AuditResult.module`）
MODULE_NAME = "shopee-br-ip-review"

#: 写入 `provenance.producer` 的版本标识
REVIEWER_VERSION = "sbr-ip-review/1.0.0"

#: 契约版本（与 `contracts/*.schema.json` 一致）
CONTRACT_VERSION = "1.0.0"

#: 阻断类动作 —— 只能来自权威来源的 active 规则
BLOCKING_ACTIONS = ("block", "freeze_relist", "escalate_legal")

#: 指示性使用豁免（SBR-IP-006）覆盖的规则 —— 品牌宣称类。
#:
#: Lei 9.279/1996 Art. 132, II：商标权人**不得**阻止配件制造商使用商标
#: **指明产品用途**。「Compatível com Ford Focus 2015-2020」是指示性使用，
#: 不是把商标当商品品牌宣称。
#:
#: **不**包含 `SBR-IP-002`（假货宣称）—— 「réplica compatível com」既是
#: 指示性用词也是假货宣称，假货风险不受 Art. 132 保护。
NOMINATIVE_USE_EXEMPTED = ("SBR-IP-001",)

#: 动作强度序（用于聚合时取最重）
_ACTION_RANK = {
    "allow": 0,
    "flag_for_review": 1,
    "require_evidence": 2,
    "revise": 3,
    "escalate_legal": 4,
    "freeze_relist": 5,
    "block": 6,
}

#: 风险等级序
_RISK_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


class RuleLoadError(Exception):
    """规则库读不到 —— 该模块必须停止并显式失败。

    绝不能把「规则没读到」当成「没发现问题」。
    """


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _risk_level(severity: str | None) -> str:
    value = (severity or "").lower()
    return value if value in _RISK_RANK else "low"


def _product_id(product: dict, index: int) -> str:
    for key in ("product_id", "internal_sku", "platform_pid"):
        value = product.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return f"PRODUCT-{index + 1:04d}"


def _target_ref(product: dict, product_id: str) -> str:
    source = product.get("source")
    if isinstance(source, dict):
        path = source.get("path")
        if isinstance(path, str) and path:
            return path
    return product_id


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def review_products(skill_input: dict, options: dict | None = None,
                    rules: list[dict] | None = None) -> dict:
    """对一个 `SkillInput` 做 IP 与授权风险筛查。

    返回
    ----
    dict：
      * ``results``  —— `AuditResult[]`
      * ``handoff``  —— `ModuleHandoff`
      * ``errors``   —— 错误记录
      * ``signals``  —— 每个商品的判定明细（非契约字段，供人工复核）
    """
    options = dict(options or {})
    skill_input = skill_input or {}
    request_id = skill_input.get("request_id") or "REQ-IP-UNKNOWN"
    produced_at = _utc_now_iso()

    action_matrix = matrix_mod.ActionMatrix.load(options.get("root"))
    views, load_errors = rules_mod.load_rules(rules=rules, root=options.get("root"))
    errors: list[dict] = []
    for item in load_errors:
        errors.append({
            "error_id": f"ERR-IP-{len(errors) + 1:04d}",
            "stage": item.get("stage", "rule_loading"),
            "severity": item.get("severity", "error"),
            "message": item.get("message", ""),
            "context": item.get("context", {}),
        })
    if not views:
        # 规则读不到 → 必须显式失败，不能报「无风险」
        raise RuleLoadError(
            "no IP rules could be loaded; the module must stop rather than "
            "report 'no risk found'")

    products = skill_input.get("products") or []
    results: list[dict] = []
    signals: list[dict] = []

    for index, product in enumerate(products):
        product_id = _product_id(product, index)
        try:
            result, detail = _review_one(product, product_id, request_id,
                                         produced_at, views, action_matrix)
        except Exception as exc:                      # noqa: BLE001
            errors.append({
                "error_id": f"ERR-IP-{len(errors) + 1:04d}",
                "stage": "review",
                "severity": "error",
                "message": f"{type(exc).__name__}: {exc}",
                "context": {"product_id": product_id},
            })
            continue
        results.append(result)
        signals.append(detail)

    handoff = _build_handoff(request_id, results, produced_at)
    return {
        "results": results,
        "handoff": handoff,
        "errors": errors,
        "signals": signals,
    }


# ---------------------------------------------------------------------------
# 单商品判定
# ---------------------------------------------------------------------------

def _review_one(product: dict, product_id: str, request_id: str,
                produced_at: str, views: list, action_matrix) -> tuple[dict, dict]:
    fired: list[dict] = []
    unevaluated: list[dict] = []

    for view in views:
        rule = view.as_envelope()
        try:
            matched, unevaluable, details, missing_fields = evaluator.evaluate_rule(
                product, rule)
        except ValueError as exc:
            # 未知算子 —— 该规则不可执行，如实记录而不是静默跳过
            unevaluated.append({
                "rule_id": view.rule_id,
                "reason": f"rule could not be evaluated: {exc}",
                "missing_fields": [],
            })
            continue
        if unevaluable:
            unevaluated.append({
                "rule_id": view.rule_id,
                "reason": (
                    f"rule could not be evaluated because required input is "
                    f"missing: {', '.join(missing_fields) or 'unknown field'}"
                ),
                "missing_fields": list(missing_fields),
            })
            continue
        if not matched:
            continue
        fired.append({"rule": rule, "view": view, "details": details})

    # --- 指示性使用豁免（SBR-IP-006）覆盖品牌宣称命中（SBR-IP-001）---
    #
    # Lei 9.279/1996 Art. 132, II：商标权人**不得**阻止配件制造商使用
    # 商标**指明产品用途**。「Compatível com Ford Focus 2015-2020」是指示性
    # 使用，不是把商标当商品品牌宣称 —— 不构成侵权。
    #
    # SBR-IP-006 的触发条件是「兼容性上下文」**且**「出现品牌词」，
    # 因此它命中恰恰说明这个品牌词出现在指示性语境里。此时品牌宣称
    # 规则必须让位。
    #
    # **不**豁免 SBR-IP-002（假货宣称）—— 「réplica Nike compatível com」
    # 既是指示性用词也是假货宣称，假货风险不受 Art. 132 保护。
    nominative = [item for item in fired if item["view"].rule_id == "SBR-IP-006"]
    exemption_notes: list[str] = []
    if nominative:
        suppressed = []
        kept = []
        for item in fired:
            if item["view"].rule_id in NOMINATIVE_USE_EXEMPTED:
                suppressed.append(item["view"].rule_id)
            else:
                kept.append(item)
        fired = kept
        if suppressed:
            exemption_notes.append(
                "指示性使用豁免（Lei 9.279/1996 Art. 132, II）：兼容性上下文成立，"
                f"品牌宣称规则 {', '.join(suppressed)} 不构成侵权依据")

    # --- 动作与风险等级 ---
    risk_level = "info"
    action = "allow"
    downgrade_reasons: list[str] = []

    for item in fired:
        view = item["view"]
        level = _risk_level(view.severity)
        if _RISK_RANK[level] > _RISK_RANK[risk_level]:
            risk_level = level
        declared = view.action
        capped, cap_reason = action_matrix.cap_for_source(
            declared, view.source_tier, view.status)
        if cap_reason:
            downgrade_reasons.append(f"{view.rule_id}: {cap_reason}")
        resolved, resolve_note = action_matrix.resolve(level, capped)
        if resolve_note:
            downgrade_reasons.append(f"{view.rule_id}: {resolve_note}")
        if _ACTION_RANK.get(resolved, 0) > _ACTION_RANK.get(action, 0):
            action = resolved

    if not fired:
        risk_level = "info"
        action = "allow"

    # --- 硬约束 H3：无法评估的维度不得被当作「通过」---
    # 有规则因缺输入而无法评估时，这个商品的 IP 维度是**未评估**，
    # 不是「没问题」。动作必须升级到人工复核，verdict 不得是 PASS。
    if unevaluated:
        if _ACTION_RANK.get(action, 0) < _ACTION_RANK.get("flag_for_review", 0):
            action = "flag_for_review"
        if risk_level == "info":
            risk_level = "low"
        downgrade_reasons.append(
            f"{len(unevaluated)} rule(s) could not be evaluated because the "
            f"required input was missing; the IP dimension is unassessed, "
            f"not cleared (hard constraint H3)")

    # --- 置信度：IP 恒为 signal（硬约束 H1）---
    confidence = "signal"

    # --- 人工复核：IP 恒为 true（硬约束 H1）---
    review_reasons: list[str] = []
    if fired:
        review_reasons.append(
            "IP-category findings are screening signals only; only a rights-holder "
            "complaint, a written authorisation, or a platform complaint notice "
            "can establish infringement")
    if unevaluated:
        review_reasons.append(
            f"{len(unevaluated)} rule(s) could not be evaluated because input "
            f"was missing")
    if downgrade_reasons:
        review_reasons.extend(downgrade_reasons)
    if action_matrix.always_human_review(action):
        review_reasons.append(f"action '{action}' always requires human review")
    requires_human_review = True     # H1：IP 结论恒需人工复核

    reason = _build_reason(product_id, fired, unevaluated, action,
                           risk_level, downgrade_reasons, exemption_notes)

    rule_refs = []
    for item in fired:
        view = item["view"]
        details = item["details"]
        first = details[0] if details else {}
        rule_refs.append({
            "rule_id": view.rule_id,
            "title": view.title,
            "matched_field": first.get("field"),
            "matched_excerpt": first.get("excerpt"),
            "source_tier": view.source_tier,
        })

    result = {
        "result_id": f"RES-IP-{request_id}-{product_id}",
        "request_id": request_id,
        "module": MODULE_NAME,
        "target_ref": _target_ref(product, product_id),
        "verdict": action_matrix.verdict_for(action),
        "risk_level": risk_level,
        "action": action,
        "reason": reason,
        "rule_refs": rule_refs,
        "evidence_refs": [],
        "confidence": confidence,
        "requires_human_review": requires_human_review,
        "review_rationale": "manual review needed: " + "; ".join(review_reasons)
                            if review_reasons else None,
        "rule_version": rules_mod.rule_version(views),
        "provenance": {
            "produced_at": produced_at,
            "producer": REVIEWER_VERSION,
            "source_refs": [_target_ref(product, product_id)],
            "notes": _provenance_notes(product, fired, unevaluated),
        },
        "errors": [],
        "unevaluated": unevaluated,
    }

    detail = {
        "product_id": product_id,
        "fired": [item["view"].rule_id for item in fired],
        "unevaluated": unevaluated,
        "authorization": evaluator.authorization_inventory(product),
        "action": action,
        "risk_level": risk_level,
        "downgrade_reasons": downgrade_reasons,
        "details": {item["view"].rule_id: item["details"] for item in fired},
    }
    return result, detail


def _build_reason(product_id: str, fired: list, unevaluated: list,
                  action: str, risk_level: str, downgrade_reasons: list,
                  exemption_notes: list | None = None) -> str:
    parts = []
    if fired:
        ids = ", ".join(item["view"].rule_id for item in fired)
        parts.append(f"{len(fired)} IP screening signal(s) matched ({ids})")
    else:
        parts.append("no IP screening signal matched")
    parts.append(f"action '{action}' at risk level '{risk_level}'")
    if unevaluated:
        parts.append(f"{len(unevaluated)} rule(s) not evaluable (missing input)")
    for note in exemption_notes or []:
        parts.append(note)
    if downgrade_reasons:
        parts.append("action downgraded: " + "; ".join(downgrade_reasons))
    parts.append("IP findings are screening signals, not an infringement finding")
    return "; ".join(parts)


def _provenance_notes(product: dict, fired: list, unevaluated: list) -> str:
    notes = []
    auth = evaluator.authorization_inventory(product)
    if not auth["known"]:
        notes.append("no authorisation inventory present — authorisation "
                     "status is unknown, not 'missing'")
    elif auth["missing"]:
        notes.append(f"authorisation gaps recorded: {', '.join(auth['missing'])}")
    else:
        notes.append(f"authorisation documents recorded: {len(auth['provided'])}")
    if fired:
        notes.append(f"{len(fired)} screening signal(s) recorded")
    if unevaluated:
        notes.append(f"{len(unevaluated)} rule(s) not evaluable")
    return "; ".join(notes)


# ---------------------------------------------------------------------------
# 模块交接
# ---------------------------------------------------------------------------

def _build_handoff(request_id: str, results: list[dict], produced_at: str) -> dict:
    """`contracts/module_handoff.schema.json` 格式的交接记录。

    该 Schema 的必需字段是：`handoff_id` / `from_module` / `to_module` /
    `request_id` / `contract_version` / `produced_at` / `assumptions` /
    `known_gaps`。自造的 `summary` / `notes` 字段不在 Schema 里 ——
    契约用 `additionalProperties: false`，多写字段会让校验不过。
    """
    unevaluated: list[dict] = []
    for result in results:
        for item in result.get("unevaluated") or []:
            unevaluated.append(item)

    assumptions = [
        "IP findings are screening signals only. A keyword or logo match is "
        "not an infringement finding: only a rights-holder complaint, a "
        "written authorisation, or a platform complaint notice can establish "
        "infringement (hard constraint H1).",
        "Every result carries confidence='signal' and "
        "requires_human_review=true. This module never produces a "
        "deterministic IP conclusion.",
        "The module performs no online action — no publication, deletion, "
        "freeze or appeal is executed here; only recommendations are emitted.",
        "The authorisation dimension is read from the 'history' field of the "
        "supplied products. An absent authorisation inventory means the "
        "authorisation status is unknown, not 'missing'.",
    ]
    known_gaps: list[str] = []
    if unevaluated:
        known_gaps.append(
            f"{len(unevaluated)} rule evaluation(s) could not be completed "
            f"because the required input was missing; those dimensions are "
            f"unassessed, not cleared.")
    if not results:
        known_gaps.append(
            "No products were supplied, so no IP dimension was evaluated.")

    return {
        "handoff_id": f"HO-IP-{request_id}",
        "from_module": MODULE_NAME,
        "to_module": "shopee-br-compliance",
        "request_id": request_id,
        "payload_ref": {
            "artifact_ref": None,
            "inline": {"audit_results": results},
            "record_count": len(results),
        },
        "contract_version": CONTRACT_VERSION,
        "produced_at": produced_at,
        "assumptions": assumptions,
        "known_gaps": known_gaps,
        "unevaluated": unevaluated,
        "requires_human_review": True,
    }
