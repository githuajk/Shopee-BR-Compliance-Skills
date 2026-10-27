"""判定引擎：把商品集 + 历史案件变成符合契约的 `AuditResult[]`。

流程：

1. **装载规则** —— 从 `rules/03`（DUP 部分）与 `rules/04`（RL/AU/AC）
   取本模块拥有的规则；`SkillInput.rules[]` 可覆盖同名规则。
2. **建索引** —— 重复索引（商品之间）与重发索引（商品 × 案件）。
3. **算结论** —— 每个商品一组判定：
   * 重复：同店 → `__DUPLICATE_SIGNAL__`；跨店 → `__CROSS_STORE_DUPLICATE_SIGNAL__`；
   * 重发：命中**已处置**案件 → `__RELIST_SIGNAL__` + `__REMOVED_LISTING_SIGNAL__`；
     命中**处理中**案件 → `__OPEN_CASE_SIGNAL__`；
   * 授权 / 处罚点 / 申诉：直接由 `history` 求值。
4. **查表定动作** —— `contracts/risk_action_matrix.json` 决定动作与
   verdict，硬约束 H2 负责降级。
5. **产出** —— `AuditResult[]` + `ModuleHandoff`。

**绝不静默丢弃**：每个商品都有结果；输入缺失进 `unevaluated[]` + `errors[]`。

## 「不适用」与「未评估」的区别

这是本模块最重要的一个设计决定：

* **不适用（not applicable）** —— 该规则检查的维度**根本没有出现在输入
  里**（例如商品没有授权材料清单，就没有「授权缺口」可言）。规则被跳过，
  **不**记 `unevaluated`。
* **未评估（unevaluated）** —— 该规则**本可以**判定，但输入缺了它需要的
  数据（例如没有案件历史，就无法判断这是不是违规重发；跨店比对需要多个
  店铺的商品集）。必须记 `unevaluated`（硬约束 H3）。

判错方向的后果不一样：把「不适用」记成「未评估」会让所有商品都变成
REVIEW，把噪音塞进报告；把「未评估」记成「不适用」等于把「没查」说成
「查过了，没问题」—— 那是硬约束 H3 明令禁止的。
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from .duplicates import DuplicateIndex
from .errors import (
    ErrorLog,
    STAGE_INPUT,
    STAGE_MATRIX,
    STAGE_RULE_EVALUATION,
    STAGE_RULE_LOADING,
)
from .matrix import RiskMatrix
from .relist import (
    CASE_ACTIONED,
    CASE_IN_REMEDIATION,
    CASE_RESOLVED,
    RELATION_INHERITS,
    RELATION_SUBJECT,
    RelistIndex,
    case_state,
)
from .rules import RuleSet, evaluate_rule, load_rules, sentinel_tokens

__all__ = [
    "MODULE_NAME",
    "CONTRACT_VERSION",
    "RULE_VERSION",
    "detect_duplicates",
    "utc_now_iso",
]

MODULE_NAME = "shopee-br-duplicate-detection"
CONTRACT_VERSION = "1.0.0"
RULE_VERSION = "sbr-dup-rules/1.0.0"

#: 哨兵记号 —— 引擎算出的结论，通过注入让规则决定严重度/动作/证据。
SENTINEL_SAME_SHOP = "__DUPLICATE_SIGNAL__"
SENTINEL_CROSS_SHOP = "__CROSS_STORE_DUPLICATE_SIGNAL__"
SENTINEL_RELIST = "__RELIST_SIGNAL__"
SENTINEL_REMOVED = "__REMOVED_LISTING_SIGNAL__"
SENTINEL_OPEN_CASE = "__OPEN_CASE_SIGNAL__"

#: 触发这些规则所需的**商品字段**（缺失即未评估）。
_REQUIRED_PRODUCT_FIELDS = {
    "SBR-DUP-001": ("title", "shop_id"),
    "SBR-DUP-002": ("title", "shop_id"),
    "SBR-DUP-003": ("title", "shop_id"),
    "SBR-RL-001": (),
    "SBR-RL-002": (),
    "SBR-AU-001": (),
    "SBR-AC-001": (),
    "SBR-AC-002": (),
}

#: 规则所检查的**维度**是否出现在输入里。维度缺席 = 不适用（非未评估）。
_DIMENSION_KEYS = {
    "SBR-AU-001": ("authorization_documents", "missing"),
    "SBR-AC-001": ("penalty_points", "pontos_de_penalidade"),
    "SBR-AC-002": ("appeal_pending", "appeal_deadline"),
}

#: 规则所检查的维度**被声明了**但**值为空/为零**时，该维度仍算出现过
#: —— 只是没有缺口。规则会正常求值并判定「不命中」。
#
#: 例：`history = {"missing": []}` —— 授权清单存在且没有缺口 → SBR-AU-001
#: 正常求值并**不命中**（这不是「未评估」）。
_DIMENSION_EMPTY_IS_PRESENT = {
    "SBR-AU-001": True,
    "SBR-AC-001": False,
    "SBR-AC-002": False,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", "..", ".."))


# ---------------------------------------------------------------------------
# 输入准备
# ---------------------------------------------------------------------------

def _link_cases(product: dict, cases: list[dict]) -> list[dict]:
    """找出与该商品关联的案件。

    关联方式有二：商品自带 `case_ids`，或案件的 `product_ids` 引用了该
    商品。两种都认 —— 案件可能只引用商品 id 而商品侧没有回填。
    """
    product_id = product.get("product_id") or ""
    linked: list[dict] = []
    for case in cases:
        case_id = case.get("case_id")
        if not case_id:
            continue
        if case_id in (product.get("case_ids") or []):
            linked.append(case)
            continue
        if product_id and product_id in (case.get("product_ids") or []):
            linked.append(case)
    return linked


def _merge_case_history(product: dict, linked_cases: list[dict]) -> dict:
    """把案件侧的事实并入商品的 history 视图。

    只并入**可从案件直接读出**的事实，不推断任何数值：

    * `appeal_deadline` —— 平台通知里写明的申诉截止日；
    * `appeal_pending` —— 案件带申诉截止日且**尚未结案**。

    处罚点分值**不从案件推断** —— 平台未公开分值，案件里也没有。
    """
    history = product.get("history")
    merged: dict = dict(history) if isinstance(history, dict) else {}
    for case in linked_cases:
        notice = case.get("platform_notice") or {}
        deadline = notice.get("appeal_deadline")
        if deadline and case_state(case) != CASE_RESOLVED:
            merged.setdefault("appeal_deadline", deadline)
            merged.setdefault("appeal_pending", True)
    return merged


def _evaluation_view(product: dict, linked_cases: list[dict]) -> dict:
    """规则求值用的商品视图 —— 原始商品的副本 + 并入的案件事实。

    副本是必须的：规则不得改写输入数据。
    """
    view = dict(product)
    view["history"] = _merge_case_history(product, linked_cases)
    return view


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _dimension_present(view: dict, rule_id: str) -> bool:
    """规则所检查的维度是否出现在输入里。"""
    keys = _DIMENSION_KEYS.get(rule_id)
    if not keys:
        return True
    history = view.get("history")
    if not isinstance(history, dict):
        return False
    return any(key in history for key in keys)


# ---------------------------------------------------------------------------
# 结论构造
# ---------------------------------------------------------------------------

def _rule_ref(rule: dict, matched_field: str | None, excerpt: str) -> dict:
    return {
        "rule_id": rule["rule_id"],
        "title": rule.get("title"),
        "matched_field": matched_field,
        "matched_excerpt": excerpt,
        "source_tier": rule.get("source_tier"),
        "source_url": rule.get("source_url") or None,
    }


def _evidence_ref(evidence_id: str, evidence_type: str, provided: bool,
                  artifact_ref: str | None = None, notes: str | None = None,
                  source_locator: str | None = None) -> dict:
    ref = {
        "evidence_id": evidence_id,
        "evidence_type": evidence_type,
        "provided": provided,
    }
    if artifact_ref is not None:
        ref["artifact_ref"] = artifact_ref
    if source_locator is not None:
        ref["source_locator"] = source_locator
    if notes is not None:
        ref["notes"] = notes
    return ref


def _case_evidence(case: dict, evidence_type: str) -> tuple[bool, str | None]:
    """案件里是否已提供某类证据。**只取引用，不取内容**（硬约束 H5）。"""
    for item in case.get("evidence") or []:
        if not isinstance(item, dict):
            continue
        if item.get("evidence_type") == evidence_type and item.get("provided"):
            return True, item.get("artifact_ref")
    return False, None


def _is_ip_case(case: dict) -> bool:
    """案件是否是 IP 投诉（`case_type` 判定）。

    只看 `case_type` —— `violation_type` 指向 IP 规则**不**等于这是 IP
    投诉：`SBRC-000201` 的 violation_type 是 `SBR-IP-002`，但它是
    `listing_review` 型的「商品已删除」案件，重发它应当被冻结。
    """
    return case.get("case_type") == "ip_complaint"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def detect_duplicates(skill_input: dict, options: dict | None = None,
                      root: str | None = None) -> dict:
    """执行重复刊登与违规重发检查。

    参数
    ----
    skill_input:
        符合 `contracts/skill_input.schema.json` 的输入。
    options:
        模块私有选项。识别 `cross_store`（默认 true）、`similarity_threshold`
        （默认 0.62）、`relist_content_threshold`（默认 0.62）。未知键忽略。
    root:
        仓库根（用于定位 `rules/` 与 `contracts/`）。缺省自动推导。

    返回
    ----
    dict，含 ``skill_input`` / ``results`` / ``handoff`` / ``products`` /
    ``cases`` / ``errors`` / ``duplicates`` / ``relists``。
    """
    options = options or {}
    root = root or _repo_root()
    batch_log = ErrorLog()

    # 选项有两个来源：调用方显式传入的，以及 `SkillInput.options` 里的。
    # 契约允许模块私有选项放在 `SkillInput.options` —— 显式传入的优先。
    merged_options: dict = {}
    input_options = skill_input.get("options")
    if isinstance(input_options, dict):
        merged_options.update(input_options)
    merged_options.update(options)
    options = merged_options

    request_id = skill_input.get("request_id") or "REQ-UNKNOWN"
    input_provenance = skill_input.get("provenance") or {}

    cross_store = bool(options.get("cross_store", True))
    threshold = float(options.get("similarity_threshold", 0.62))
    relist_threshold = float(options.get("relist_content_threshold", 0.62))

    # --- 0. 输入容器体检（批次级）---
    if not isinstance(skill_input.get("products"), list):
        batch_log.fatal(
            STAGE_INPUT,
            "the input does not carry a products array; the check cannot run",
            {"request_id": request_id},
        )
        return _stop_module(skill_input, batch_log, [], [],
                            cross_store, threshold, relist_threshold)
    raw_cases = skill_input.get("cases")
    if raw_cases is None:
        raw_cases = []
    if not isinstance(raw_cases, list):
        batch_log.error(
            STAGE_INPUT,
            "the input does not carry a cases array; it is treated as empty, "
            "so the relist rules cannot be evaluated",
            {"request_id": request_id},
        )
        raw_cases = []

    products = list(skill_input.get("products") or [])
    cases = list(raw_cases)

    # --- 1. 规则 ---
    rules = load_rules(root=root, envelopes=skill_input.get("rules"),
                       error_log=batch_log)
    rule_set = RuleSet(rules)
    if not rule_set.rules:
        batch_log.fatal(
            STAGE_RULE_LOADING,
            "no rules could be loaded for this module; the check cannot run",
            {"prefixes": ["DUP", "RL", "AU", "AC"]},
        )
        return _stop_module(skill_input, batch_log, products, cases,
                            cross_store, threshold, relist_threshold)

    # --- 2. 风险矩阵 ---
    matrix = RiskMatrix.load(root)
    if matrix.load_error:
        batch_log.error(STAGE_MATRIX, matrix.load_error,
                        {"path": "contracts/risk_action_matrix.json"})

    # --- 3. 商品字段体检（缺失 → 相应规则未评估）---
    for product in products:
        for required in ("product_id", "internal_sku", "shop_id", "title"):
            value = product.get(required)
            if value is None or (isinstance(value, str) and not value.strip()):
                batch_log.warning(
                    STAGE_INPUT,
                    f"product is missing the required field {required!r}; "
                    f"rules that need it are reported as unevaluated",
                    {"product_id": product.get("product_id"), "field": required},
                )

    # --- 4. 索引 ---
    duplicate_index = DuplicateIndex(threshold=threshold)
    for product in products:
        duplicate_index.add(product)

    relist_index = RelistIndex(content_threshold=relist_threshold)
    for product in products:
        relist_index.add_product(product)
    for case in cases:
        relist_index.add_case(case)

    duplicate_matches = duplicate_index.find_all()
    shops = {p.get("shop_id") for p in products
             if _has_value(p.get("shop_id"))}

    # 跨店比对的可行性：至少两个店铺的商品集才可能发现跨店同款。
    cross_store_feasible = cross_store and len(shops) >= 2

    produced_at = utc_now_iso()
    results: list[dict] = []

    # --- 4b. 重发关联（先算，因为重发对会从重复候选里剔除）---
    all_relists: dict[str, list] = {}
    for product in products:
        all_relists[product.get("product_id") or ""] = relist_index.check(product)

    # 「案件对象 → 它的副本」构成一对**重发对**。当案件已被平台实际处置时，
    # 这一对的事实是「违规重发」，不是「同店重复」—— 报重复会把同一个事实
    # 算两遍。案件已结（resolved）或仍在整改中时，重发不成立，这一对仍按
    # 重复处理。
    relist_pairs: set[frozenset[str]] = set()
    for product in products:
        product_id = product.get("product_id") or ""
        for relist in all_relists.get(product_id, []):
            if relist.relation != RELATION_INHERITS:
                continue
            if relist.case_state != CASE_ACTIONED:
                continue
            if relist.historical_product_id:
                relist_pairs.add(frozenset({product_id,
                                            relist.historical_product_id}))

    for product in products:
        product_id = product.get("product_id") or ""
        product_log = ErrorLog()
        linked_cases = _link_cases(product, cases)
        view = _evaluation_view(product, linked_cases)

        # --- 4a. 重复候选 ---
        own_duplicates = [m for m in duplicate_matches
                          if product_id in (m.product_id, m.other_product_id)
                          and frozenset({m.product_id,
                                         m.other_product_id}) not in relist_pairs]

        # --- 4b. 重发候选 ---
        own_relists = all_relists.get(product_id, [])

        # --- 4c. 注入哨兵 ---
        injected: set[str] = set()
        match_notes: dict[str, str] = {}

        for match in own_duplicates:
            if match.same_shop:
                injected.add(SENTINEL_SAME_SHOP)
                match_notes.setdefault(SENTINEL_SAME_SHOP, match.describe())
            elif cross_store:
                injected.add(SENTINEL_CROSS_SHOP)
                match_notes.setdefault(SENTINEL_CROSS_SHOP, match.describe())

        # 重发只认「继承」关系 —— 商品自己挂在案件上（subject）不是重发。
        inherits = [r for r in own_relists if r.relation == RELATION_INHERITS]
        subjects = [r for r in own_relists if r.relation == RELATION_SUBJECT]
        actioned_relists = [r for r in inherits if r.case_state == CASE_ACTIONED]
        remediation_relists = [r for r in inherits
                               if r.case_state == CASE_IN_REMEDIATION]
        remediation_subjects = [r for r in subjects
                                if r.case_state == CASE_IN_REMEDIATION]

        # 已处置的继承关系 → 违规重发 + 平台已删除（应冻结）
        if actioned_relists:
            injected.add(SENTINEL_RELIST)
            injected.add(SENTINEL_REMOVED)
            match_notes.setdefault(SENTINEL_RELIST, actioned_relists[0].describe())
            match_notes.setdefault(SENTINEL_REMOVED, actioned_relists[0].describe())

        # 未结的案件（继承关系或案件对象本身）→ 案件未结，只提示复核
        if remediation_relists or remediation_subjects:
            injected.add(SENTINEL_OPEN_CASE)
            source = (remediation_relists or remediation_subjects)[0]
            match_notes.setdefault(SENTINEL_OPEN_CASE, source.describe())

        # --- 4d. 逐规则求值 ---
        rule_refs: list[dict] = []
        fired: list[dict] = []
        unevaluated: list[dict] = []
        identity_axes = {"platform_pid", "supplier_sku", "internal_sku",
                         "case_product_id"}
        has_identity_finding = False
        ip_case_id = None

        for rule in rule_set:
            rule_id = rule["rule_id"]

            # (a) 维度是否适用
            if not _dimension_present(view, rule_id):
                continue

            # (b) 规则需要的商品字段是否齐备
            required = _REQUIRED_PRODUCT_FIELDS.get(rule_id, ())
            missing = [field for field in required
                       if not _has_value(view.get(field))]
            if missing:
                reason = (f"the input does not carry {', '.join(missing)}; "
                          f"this rule could not be evaluated "
                          f"(hard constraint H3)")
                unevaluated.append({
                    "rule_id": rule_id,
                    "reason": reason,
                    "missing_fields": missing,
                })
                product_log.warning(STAGE_RULE_EVALUATION, reason,
                                    {"rule_id": rule_id, "product_id": product_id,
                                     "missing_fields": missing})
                continue

            # (c) 重发类规则需要案件历史
            if rule_id in ("SBR-RL-001", "SBR-RL-002") and not cases:
                reason = ("the request carries no case history, so the relist "
                          "status of this listing could not be determined "
                          "(hard constraint H3) — this is not evidence that "
                          "the listing is not a relist")
                unevaluated.append({
                    "rule_id": rule_id,
                    "reason": reason,
                    "missing_fields": ["cases"],
                })
                product_log.warning(STAGE_RULE_EVALUATION, reason,
                                    {"rule_id": rule_id, "product_id": product_id,
                                     "missing_fields": ["cases"]})
                continue

            # (d) 跨店规则需要多店铺商品集
            if rule_id == "SBR-DUP-002" and not cross_store_feasible:
                if not cross_store:
                    reason = ("cross-store comparison was switched off by "
                              "options.cross_store, so the cross-store "
                              "duplicate rule was not evaluated")
                    missing_fields = ["options.cross_store"]
                else:
                    reason = ("the batch carries fewer than two shops, so no "
                              "cross-store comparison was possible; a "
                              "cross-store duplicate could not be ruled out "
                              "(hard constraint H3)")
                    missing_fields = ["shop_id"]
                unevaluated.append({
                    "rule_id": rule_id,
                    "reason": reason,
                    "missing_fields": missing_fields,
                })
                product_log.warning(STAGE_RULE_EVALUATION, reason,
                                    {"rule_id": rule_id, "product_id": product_id,
                                     "missing_fields": missing_fields})
                continue

            matched, cannot_evaluate, why = evaluate_rule(rule, view, injected)
            if cannot_evaluate:
                unevaluated.append({
                    "rule_id": rule_id,
                    "reason": why or "the input does not carry the data "
                                     "this rule inspects",
                    "missing_fields": [],
                })
                product_log.warning(
                    STAGE_RULE_EVALUATION,
                    f"{rule_id} could not be evaluated: "
                    f"{why or 'input data is missing'}",
                    {"rule_id": rule_id, "product_id": product_id},
                )
                continue
            if not matched:
                continue

            sentinel = next((s for s in sentinel_tokens(rule) if s in injected),
                            None)
            excerpt = match_notes.get(sentinel) if sentinel else None
            if excerpt is None:
                excerpt = _describe_text_match(rule, view)
            rule_refs.append(_rule_ref(rule, _matched_field(rule, view), excerpt))
            fired.append(rule)

            # IP 投诉案件：本模块不做 IP 判定（硬约束 H1 + 非职责）。
            for relist in own_relists:
                case = next((c for c in cases
                             if c.get("case_id") == relist.case_id), None)
                if case and _is_ip_case(case):
                    ip_case_id = relist.case_id

        # 身份轴命中 → 结论更确定
        for match in own_duplicates:
            if set(match.axes) & identity_axes:
                has_identity_finding = True
        for relist in own_relists:
            if set(relist.match_basis) & identity_axes:
                has_identity_finding = True

        # --- 4e. 动作查表 ---
        action = "allow"
        risk_level = "info"
        severity_order = ["info", "low", "medium", "high", "critical"]
        downgrades: list[str] = []
        for rule in fired:
            resolved = matrix.resolve(rule.get("severity", "medium"),
                                      rule.get("action", "flag_for_review"),
                                      rule.get("source_tier", "unverified"),
                                      rule.get("status", "active"))
            if resolved["downgraded"] and resolved["reason"]:
                downgrades.append(f"{rule['rule_id']}: {resolved['reason']}")
            action = matrix.heavier(action, resolved["action"])
            if severity_order.index(rule.get("severity", "medium")) > \
                    severity_order.index(risk_level):
                risk_level = rule.get("severity", "medium")

        # IP 投诉案件：冻结类动作降级为人工复核。
        if ip_case_id:
            if action in ("freeze_relist", "escalate_legal", "block"):
                downgrades.append(
                    f"case {ip_case_id} is an IP complaint; this module does "
                    f"not produce IP findings (hard constraint H1), so the "
                    f"blocking action is downgraded to flag_for_review")
                action = "flag_for_review"
            if risk_level in ("high", "critical"):
                risk_level = "medium"

        if not fired and unevaluated:
            action = "flag_for_review"
            risk_level = "info"

        verdict = matrix.verdict_for(action)
        requires_human_review = matrix.always_human_review(action)
        if unevaluated:
            requires_human_review = True

        # --- 4f. 置信度 ---
        if ip_case_id:
            confidence = "signal"
        elif has_identity_finding:
            confidence = "confirmed"
        elif fired:
            confidence = "likely"
        elif unevaluated:
            confidence = "signal"
        else:
            confidence = "likely"

        # --- 4g. 证据 ---
        evidence_refs = _build_evidence(fired, own_duplicates, own_relists,
                                        linked_cases, view, product_id)

        reason = _build_reason(product_id, fired, rule_refs, unevaluated,
                               downgrades, ip_case_id)

        results.append({
            "result_id": f"RES-DUP-{request_id}-{product_id or 'UNKNOWN'}",
            "request_id": request_id,
            "module": MODULE_NAME,
            "target_ref": product_id or "unknown-product",
            "verdict": verdict,
            "risk_level": risk_level,
            "action": action,
            "reason": reason,
            "rule_refs": rule_refs,
            "evidence_refs": evidence_refs,
            "confidence": confidence,
            "requires_human_review": requires_human_review,
            "review_rationale": _build_review_rationale(
                action, unevaluated, fired, ip_case_id),
            "rule_version": RULE_VERSION,
            "provenance": {
                "produced_at": produced_at,
                "producer": f"{MODULE_NAME}/{_version()}",
                "source_refs": [entry.get("path")
                                for entry in input_provenance.get("inputs") or []
                                if entry.get("path")],
                "notes": _build_provenance_notes(
                    input_provenance, rule_set, products, cases, shops,
                    cross_store, threshold, relist_threshold),
            },
            "errors": list(product_log.items),
            "unevaluated": unevaluated,
        })

    # --- 5. 交接 ---
    relist_candidates = _all_relists(relist_index, products)

    # 批次级错误（规则装载失败、矩阵读不到）必须让每个商品都看得见 ——
    # 绝不静默丢弃（契约 §8）。
    for result in results:
        result["errors"] = list(batch_log.items) + list(result["errors"])

    handoff = _build_handoff(request_id, results, products, cases, batch_log,
                             shops, cross_store, cross_store_feasible,
                             duplicate_matches, relist_candidates)

    return {
        "skill_input": skill_input,
        "results": results,
        "handoff": handoff,
        "products": products,
        "cases": cases,
        "errors": batch_log.items,
        "duplicates": [m.to_dict() for m in duplicate_matches],
        "relists": [m.to_dict() for m in relist_candidates],
    }


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _version() -> str:
    from . import __version__
    return __version__


def _stop_module(skill_input: dict, batch_log: ErrorLog, products: list[dict],
                 cases: list[dict], cross_store: bool, threshold: float,
                 relist_threshold: float) -> dict:
    """规则库不可用时的停摆路径。

    契约 §8：「规则文件缺失或不可解析 → 记 error 并停止该模块」。
    产出仍然符合契约 —— 每件商品一条结果，`verdict=REVIEW`、
    `action=flag_for_review`，绝不 `PASS`。
    """
    request_id = skill_input.get("request_id") or "REQ-UNKNOWN"
    produced_at = utc_now_iso()
    results = []
    for product in products:
        product_id = product.get("product_id") or "unknown-product"
        results.append({
            "result_id": f"RES-DUP-{request_id}-{product_id}",
            "request_id": request_id,
            "module": MODULE_NAME,
            "target_ref": product_id,
            "verdict": "REVIEW",
            "risk_level": "info",
            "action": "flag_for_review",
            "reason": (f"{product_id} could not be checked: the rule library "
                       f"for this module could not be loaded, so no duplicate, "
                       f"relist, authorisation or penalty rule could be "
                       f"evaluated; this is not evidence that the listing is "
                       f"compliant (hard constraint H3)"),
            "rule_refs": [],
            "evidence_refs": [],
            "confidence": "signal",
            "requires_human_review": True,
            "review_rationale": ("the rule library is unavailable; a human must "
                                 "check this listing manually"),
            "rule_version": RULE_VERSION,
            "provenance": {
                "produced_at": produced_at,
                "producer": f"{MODULE_NAME}/{_version()}",
                "source_refs": [entry.get("path")
                                for entry in (skill_input.get("provenance") or {})
                                .get("inputs") or [] if entry.get("path")],
                "notes": "the module stopped before evaluation: rule library "
                         "unavailable",
            },
            "errors": list(batch_log.items),
            "unevaluated": [{
                "rule_id": rule_id,
                "reason": "the rule library could not be loaded, so this rule "
                          "was not evaluated (hard constraint H3)",
                "missing_fields": ["rules"],
            } for rule_id in ("SBR-DUP-001", "SBR-DUP-002", "SBR-DUP-003",
                              "SBR-RL-001", "SBR-RL-002", "SBR-AU-001",
                              "SBR-AC-001", "SBR-AC-002")],
        })

    handoff = {
        "handoff_id": f"HO-DUP-{request_id}",
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
        "assumptions": [
            "The rule library for this module could not be loaded, so no "
            "duplicate, relist, authorisation or penalty rule was evaluated; "
            "the results therefore describe the stoppage, not the listings.",
        ],
        "known_gaps": [
            "The whole duplicate/relist check is missing for this batch "
            "(rule library unavailable). Every listing in the batch needs a "
            "manual duplicate/relist check.",
        ],
        "unevaluated": results[0]["unevaluated"] if results else [],
        "requires_human_review": True,
    }

    return {
        "skill_input": skill_input,
        "results": results,
        "handoff": handoff,
        "products": products,
        "cases": cases,
        "errors": batch_log.items,
        "duplicates": [],
        "relists": [],
    }


def _matched_field(rule: dict, view: dict) -> str | None:
    for cond in rule.get("trigger_conditions") or []:
        field = cond.get("field")
        if field:
            return field
    return None


def _describe_text_match(rule: dict, view: dict) -> str:
    """非哨兵规则的证据描述 —— 说明命中了哪个字段的什么内容。"""
    field = _matched_field(rule, view)
    history = view.get("history") if isinstance(view.get("history"), dict) else {}
    if field == "history":
        gaps = history.get("missing")
        if gaps:
            return (f"history.missing lists {len(gaps)} unresolved "
                    f"authorisation gap(s): {', '.join(str(g) for g in gaps)}")
        points = history.get("penalty_points")
        if points is not None:
            return f"history records penalty_points = {points}"
        if "appeal_deadline" in history:
            return (f"history records an appeal deadline of "
                    f"{history['appeal_deadline']}")
        return "the rule matched on the product's history block"
    if field == "title":
        return f"the title matched the rule pattern: {view.get('title')}"
    return f"the rule matched on field {field!r}"


def _build_evidence(fired: list[dict], duplicates: list, relists: list,
                    linked_cases: list[dict], view: dict,
                    product_id: str) -> list[dict]:
    """证据引用 —— **只存引用与元信息，绝不内嵌凭证内容**（硬约束 H5）。"""
    refs: list[dict] = []
    counter = 0

    def _next_id() -> str:
        nonlocal counter
        counter += 1
        return f"EV-DUP-{product_id or 'UNKNOWN'}-{counter:02d}"

    for rule in fired:
        for evidence_type in rule.get("evidence_required") or []:
            provided = False
            artifact_ref = None
            notes = None
            for case in linked_cases:
                if case.get("case_id"):
                    ok, ref = _case_evidence(case, evidence_type)
                    if ok:
                        provided, artifact_ref = True, ref
                        notes = f"provided by case {case['case_id']}"
                        break
            if not provided and evidence_type == "case_id" and linked_cases:
                provided = True
                artifact_ref = linked_cases[0].get("case_id")
                notes = "the linked case record itself"
            if not provided and evidence_type == "original_case_id" \
                    and linked_cases:
                provided = True
                artifact_ref = linked_cases[0].get("case_id")
                notes = "the case the relist inherits from"
            if not provided and evidence_type == "canonical_listing_id":
                for match in duplicates:
                    other = (match.other_product_id
                             if match.product_id == product_id
                             else match.product_id)
                    artifact_ref = f"products/{other}"
                    notes = ("candidate canonical listing; a human must decide "
                             "which listing survives")
                    break
            if not provided and evidence_type == "variant_rationale":
                notes = ("why the differing titles/SKUs are genuine variants "
                         "rather than copies")
            if not provided and evidence_type == "master_sku_assignment":
                notes = "the master SKU assignment across the operator's shops"
            if not provided and evidence_type == "product_url_history":
                for relist in relists:
                    if relist.historical_product_id:
                        artifact_ref = f"products/{relist.historical_product_id}"
                        notes = ("the listing URL history of the historical "
                                 "product the relist inherits from")
                        break
            if not provided and evidence_type == "supplier_invoice":
                notes = "the supplier invoice proving the goods are the same item"
            if not provided and evidence_type == "penalty_points_summary":
                points = history_value(view, "penalty_points")
                if points is not None:
                    provided = True
                    artifact_ref = f"products/{product_id}/history#penalty_points"
                    notes = ("the penalty point count recorded in the product "
                             "history")
            if not provided and evidence_type == "appeal_record":
                deadline = history_value(view, "appeal_deadline")
                if deadline:
                    notes = (f"an appeal is due by {deadline}; the appeal record "
                             f"is not attached")
            if not provided and evidence_type == "platform_notice":
                for case in linked_cases:
                    notice = case.get("platform_notice")
                    if notice:
                        artifact_ref = (f"cases/{case.get('case_id')}"
                                        f"/platform_notice")
                        notes = "the verbatim platform notification"
                        break
            if not provided and evidence_type == "remediation_evidence":
                for case in linked_cases:
                    ok, ref = _case_evidence(case, "remediation_evidence")
                    if ok:
                        provided, artifact_ref = True, ref
                        notes = f"provided by case {case.get('case_id')}"
                        break
                if not provided:
                    notes = ("the remediation evidence for the linked case")
            if not provided and evidence_type == "approval_record":
                for case in linked_cases:
                    if case.get("approvals"):
                        artifact_ref = f"cases/{case.get('case_id')}/approvals"
                        notes = "the approval trail of the linked case"
                        break
                if not provided:
                    notes = "the approval record for the linked case"
            refs.append(_evidence_ref(_next_id(), evidence_type, provided,
                                      artifact_ref, notes))
    return refs


def history_value(view: dict, key: str):
    history = view.get("history")
    if isinstance(history, dict):
        return history.get(key)
    return None

def _build_reason(product_id: str, fired: list[dict], rule_refs: list[dict],
                  unevaluated: list[dict], downgrades: list[str],
                  ip_case_id: str | None) -> str:
    """一句话说明「命中了什么、依据是什么」，可回溯到规则与证据。"""
    if not fired:
        if unevaluated:
            missing = sorted({f for item in unevaluated
                              for f in item.get("missing_fields") or []})
            detail = (f"missing: {', '.join(missing)}" if missing
                      else "the input does not carry the data these rules "
                           "inspect")
            return (f"No duplicate or relist finding for {product_id}, but the "
                    f"check is incomplete: {len(unevaluated)} rule(s) could not "
                    f"be evaluated ({detail}) — the absence of a finding must "
                    f"not be read as compliance (hard constraint H3)")
        return (f"No duplicate or relist finding for {product_id}: no rule in "
                f"the duplicate/relist/authorisation/penalty set matched this "
                f"listing within the evaluated scope")

    primary = rule_refs[0] if rule_refs else {}
    excerpt = primary.get("matched_excerpt") or ""
    source = primary.get("source_url") or ""
    parts = [
        f"{product_id} matched {len(fired)} rule(s): "
        f"{', '.join(ref['rule_id'] for ref in rule_refs)}"
    ]
    if excerpt:
        parts.append(excerpt)
    if source:
        parts.append(f"source: {source}")
    if ip_case_id:
        parts.append(f"the linked case {ip_case_id} is an IP complaint, so "
                     f"this module only flags it for human review and leaves "
                     f"the IP determination to the IP module "
                     f"(hard constraint H1)")
    if downgrades:
        parts.append("downgraded: " + "; ".join(downgrades))
    return ". ".join(parts)


def _build_review_rationale(action: str, unevaluated: list[dict],
                            fired: list[dict], ip_case_id: str | None):
    if not (unevaluated or fired or ip_case_id):
        return None if action == "allow" else \
            "the action requires a human decision before it is carried out"
    pieces = []
    if unevaluated:
        pieces.append(f"{len(unevaluated)} rule(s) could not be evaluated "
                      f"(missing input); see unevaluated[]")
    if ip_case_id:
        pieces.append("an IP complaint case is linked; the IP determination "
                      "belongs to the IP module")
    if action == "freeze_relist":
        pieces.append("freeze_relist is a human_only action (hard constraint "
                      "H6): the system recommends it, a human carries it out")
    if not pieces:
        pieces.append("a human must confirm the match before the action is "
                      "taken")
    return "; ".join(pieces)


def _build_provenance_notes(input_provenance: dict, rule_set: RuleSet,
                            products: list[dict], cases: list[dict],
                            shops: set, cross_store: bool, threshold: float,
                            relist_threshold: float) -> str:
    refs = [entry.get("path") for entry in input_provenance.get("inputs") or []
            if entry.get("path")]
    produced = input_provenance.get("produced_at")
    max_version = max((rule.get("version", 1) for rule in rule_set), default=1)
    return (
        f"input provenance: {produced or 'unknown'}; "
        f"source_refs={len(refs)}; "
        f"rules applied: {len(rule_set)} (max version {max_version}); "
        f"{len(products)} product(s), {len(cases)} case(s), "
        f"{len(shops)} shop(s); "
        f"cross_store={cross_store}, "
        f"similarity_threshold={threshold}, "
        f"relist_content_threshold={relist_threshold}"
    )


def _all_relists(relist_index: RelistIndex, products: list[dict]) -> list:
    out = []
    seen = set()
    for product in products:
        for match in relist_index.check(product):
            key = (match.product_id, match.case_id)
            if key in seen:
                continue
            seen.add(key)
            out.append(match)
    return out


def _build_handoff(request_id: str, results: list[dict], products: list[dict],
                   cases: list[dict], batch_log: ErrorLog, shops: set,
                   cross_store: bool, cross_store_feasible: bool,
                   duplicate_matches: list, relist_matches: list) -> dict:
    """`contracts/module_handoff.schema.json` 格式的交接记录。"""
    unevaluated = []
    for result in results:
        for item in result.get("unevaluated") or []:
            unevaluated.append(item)

    assumptions = [
        "Duplicate detection compares only the products supplied in this "
        "request; a listing held outside this batch cannot be seen, so a "
        "'no duplicate' conclusion is scoped to the batch.",
        "Similarity thresholds are this module's own parameters, not published "
        "platform thresholds: the platform does not publish the score at "
        "which it calls two listings duplicates.",
        "A case whose status is open / under_review / awaiting_evidence is "
        "treated as still under remediation, so a relist of it is NOT frozen - "
        "freezing would block the correction the seller is submitting.",
        "A case whose status is blocked / relist_frozen / escalated / rejected "
        "(or any case explicitly marked frozen) is treated as already "
        "actioned by the platform; a relist of it is recommended for "
        "freeze_relist, which is a human_only action.",
        "A case whose status is approved / closed and that is not frozen is "
        "treated as resolved: it produces no relist finding.",
        "Case-linked facts that are readable on the case itself (the appeal "
        "deadline in platform_notice) are merged into the product history "
        "view for rule evaluation; no value is inferred that is not written "
        "down.",
        "Penalty point values are never inferred: the platform does not "
        "publish the point scale, so only 'a penalty point is recorded' is "
        "asserted.",
        "Rules whose dimension is absent from the input (for example a "
        "product with no authorisation inventory) are skipped as "
        "not-applicable; they are NOT reported as unevaluated, because "
        "nothing was left undecided about them.",
    ]
    if not cross_store:
        assumptions.append(
            "Cross-store comparison was switched off by options.cross_store; "
            "the cross-store duplicate rule was therefore not evaluated.")

    gaps = []
    if not cases:
        gaps.append(
            "The input carries no case history, so the relist rules "
            "(SBR-DUP-003 / SBR-RL-001 / SBR-RL-002) were NOT evaluated. "
            "This is not evidence that the listing is not a relist.")
    if len(shops) < 2:
        gaps.append(
            "The batch carries a single shop, so no cross-store comparison "
            "was possible; duplicates against listings in other shops of the "
            "operator are outside this scope and SBR-DUP-002 is reported as "
            "unevaluated.")
    if not cross_store:
        gaps.append(
            "Cross-store duplicate detection was disabled for this request "
            "(options.cross_store = false); SBR-DUP-002 is reported as "
            "unevaluated.")
    if not cross_store_feasible and len(shops) >= 2 and cross_store:
        gaps.append(
            "Cross-store comparison was possible but produced no candidate.")
    if unevaluated:
        gaps.append(
            f"{len(unevaluated)} rule evaluation(s) were skipped because the "
            f"input did not carry the required data; see unevaluated[] on the "
            f"individual results.")
    if batch_log.items:
        gaps.append(
            f"{len(batch_log.items)} batch-level error/warning record(s) were "
            f"produced during the run; see errors[].")
    gaps.append(
        "Image comparison uses reference-level fingerprints (image_id / url / "
        "local_path), not perceptual hashes: the same image re-encoded by the "
        "platform produces a different reference and is therefore not "
        "detected.")
    gaps.append(
        "No platform API was called and no listing was published, removed, "
        "frozen or unfrozen by this run.")
    if not gaps:
        gaps.append("No known gaps were recorded for this batch.")

    requires_human_review = any(r.get("requires_human_review") for r in results)

    return {
        "handoff_id": f"HO-DUP-{request_id}",
        "from_module": MODULE_NAME,
        "to_module": "shopee-br-compliance",
        "request_id": request_id,
        "payload_ref": {
            "artifact_ref": None,
            "inline": {
                "audit_results": results,
                "duplicate_candidates": [m.to_dict() for m in duplicate_matches],
                "relist_candidates": [m.to_dict() for m in relist_matches],
            },
            "record_count": len(results),
        },
        "contract_version": CONTRACT_VERSION,
        "produced_at": utc_now_iso(),
        "assumptions": assumptions,
        "known_gaps": gaps,
        "unevaluated": unevaluated,
        "requires_human_review": requires_human_review,
    }
