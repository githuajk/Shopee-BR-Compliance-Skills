"""聚合：把多模块的 `AuditResult[]` 按冻结契约聚合成逐目标结论。

**本模块不产生新的审核结论。** 它只做四件事：

1. **按矩阵清洗**每条输入（硬约束 H2 + 风险等级 × 动作的允许组合）；
2. 按 `verdict_aggregation` 聚合 verdict（取最重）与 action（保留最细粒度）；
3. **并集** `unevaluated[]` / `errors[]` / `rule_refs[]` / `evidence_refs[]`；
4. 产出符合 `contracts/audit_result.schema.json` 的 `AuditResult`。

## 核心不变式：verdict 永远由 action 推导

`contracts/risk_action_matrix.json` 的 `actions` 段为每个动作定义了唯一的
verdict（`allow`→PASS、`flag_for_review`/`require_evidence`→REVIEW、
`revise`→REVISE、`block`/`freeze_relist`/`escalate_legal`→BLOCK）。

因此本模块**只从清洗后的 action 推导 verdict**，绝不采用输入自报的 verdict
作为覆盖项 —— 否则一条 `internal_risk` 规则自报 `verdict=BLOCK` 就能绕过
硬约束 H2（动作被降到 `flag_for_review`，verdict 却仍是 BLOCK）。

输入自报 verdict 与 action 不一致时，记一条 `warning`（**如实暴露**），
但结论仍以矩阵为准。

聚合语义的唯一权威是 `contracts/risk_action_matrix.json`。
"""

from __future__ import annotations

from .errors import STAGE_AGGREGATE, ErrorLog
from .matrix import AUTHORITATIVE_TIERS, RiskMatrix

#: 契约 `verdict` 的完整枚举（`contracts/audit_result.schema.json`）
VERDICTS = ("PASS", "REVISE", "REVIEW", "BLOCK")

#: 契约 `confidence` 的完整枚举
CONFIDENCES = ("signal", "likely", "confirmed")

#: 契约 `risk_level` 的完整枚举
RISK_LEVELS = ("info", "low", "medium", "high", "critical")

#: 契约 `action` 的完整枚举
ACTIONS = ("allow", "flag_for_review", "require_evidence", "revise",
           "block", "freeze_relist", "escalate_legal")

#: 置信度从弱到强 —— 聚合取**最弱**（signal 不会被合并成 confirmed，H1）
_CONFIDENCE_RANK = {"signal": 0, "likely": 1, "confirmed": 2}

#: 报告中「需决策」的动作
DECISION_ACTIONS = ("block", "freeze_relist", "escalate_legal", "revise")

#: 报告中「待复核」的动作
REVIEW_ACTIONS = ("flag_for_review", "require_evidence")

#: human_only 动作（硬约束 H6）
HUMAN_ONLY_ACTIONS = ("freeze_relist", "escalate_legal")


class SanitizedResult:
    """一条输入结果经契约矩阵清洗后的状态。"""

    def __init__(self, record: dict) -> None:
        self.record = record
        self.original_action = record.get("action")
        self.original_verdict = record.get("verdict")
        self.action = record.get("action")
        self.verdict = record.get("verdict")
        self.risk_level = record.get("risk_level")
        self.adjustments: list[str] = []
        self.tiers = _collect_tiers(record)

    @property
    def result_id(self) -> str:
        return str(self.record.get("result_id") or "")

    @property
    def module(self) -> str:
        return str(self.record.get("module") or "")

    @property
    def target_ref(self) -> str:
        return str(self.record.get("target_ref") or "")

    @property
    def confidence(self) -> str:
        value = self.record.get("confidence")
        return value if value in CONFIDENCES else "likely"

    @property
    def adjusted(self) -> bool:
        return bool(self.adjustments)


def _collect_tiers(record: dict) -> list[str]:
    """结果引用到的全部来源层级。"""
    tiers: list[str] = []
    for ref in record.get("rule_refs") or []:
        tier = ref.get("source_tier")
        if tier and tier not in tiers:
            tiers.append(tier)
    return tiers


def _band(matrix: RiskMatrix, action) -> str:
    """动作所在的 verdict 档。"""
    return matrix.verdict_for_action(str(action))


def _replacement_action(matrix: RiskMatrix, risk_level: str, action: str) -> str:
    """在 (风险等级, 动作) 组合被矩阵禁止时，给出**合法且不更宽松**的动作。

    规则：

    1. 只考虑矩阵允许该风险等级的动作；
    2. 优先保持原动作的 verdict 档（同档内取**最不激进**的那个）；
    3. 同档无解时降到**更轻**的档，取该档里最不激进的动作；
    4. 更轻的档也没有时回落到 `flag_for_review` —— 它在每个风险等级都被允许。

    **永不升档**：本函数只可能降低结论的强制性。
    """
    original_band = matrix.verdict_rank.get(_band(matrix, action), 0)
    allowed = matrix.allowed_actions_for(risk_level)
    # `allowed_actions_for` 按粒度从细到粗排列；反转后取第一个即最不激进。
    same_band = [a for a in reversed(allowed)
                 if matrix.verdict_rank.get(_band(matrix, a), 0) == original_band]
    if same_band:
        return same_band[0]
    lighter = [a for a in reversed(allowed)
               if matrix.verdict_rank.get(_band(matrix, a), 0) < original_band]
    if lighter:
        # 取「刚好低一档」里最不激进的动作。
        target_band = max(matrix.verdict_rank.get(_band(matrix, a), 0)
                          for a in lighter)
        candidates = [a for a in lighter
                      if matrix.verdict_rank.get(_band(matrix, a), 0) == target_band]
        return candidates[0]
    return "flag_for_review"


def sanitize(record: dict, matrix: RiskMatrix, log: ErrorLog) -> SanitizedResult:
    """按契约矩阵清洗一条输入结果。

    * **H2** —— 阻断类动作必须能追溯到 `platform_official` / `law` 的来源；
      否则降为 `flag_for_review` 并记 `error`。
    * **矩阵组合** —— (风险等级, 动作) 不被允许时换成合法且不更宽松的动作。
    * **verdict 一致性** —— 自报 verdict 与动作不符时记 `warning`。
    """
    item = SanitizedResult(record)
    action = item.action if item.action in ACTIONS else "flag_for_review"

    # --- H2：来源层级 ---
    if matrix.is_deterministic(action):
        tiers = item.tiers
        authoritative = [t for t in tiers if t in AUTHORITATIVE_TIERS]
        if not tiers:
            item.adjustments.append(
                (f"action {action!r} was rejected: the result cites no rule with a "
                 f"source tier, so H2 cannot confirm an authoritative basis; "
                 f"downgraded to 'flag_for_review'"))
        elif not authoritative:
            item.adjustments.append(
                (f"action {action!r} was rejected: the cited rule tier(s) "
                 f"{', '.join(tiers)} are not authoritative "
                 f"(H2 allows only platform_official / law); "
                 f"downgraded to 'flag_for_review'"))
        else:
            non_auth = [t for t in tiers if t not in AUTHORITATIVE_TIERS]
            if non_auth:
                item.adjustments.append(
                    (f"action {action!r} was kept: at least one cited rule is "
                     f"authoritative, but the result also cites non-authoritative "
                     f"tier(s) {', '.join(non_auth)}"))

    if item.adjustments:
        item.action = "flag_for_review"
        log.error(STAGE_AGGREGATE, item.adjustments[0], {
            "result_id": item.result_id,
            "module": item.module,
            "target_ref": item.target_ref,
            "original_action": item.original_action,
            "adjusted_action": item.action,
            "source_tiers": item.tiers,
        })

    # --- 矩阵组合 ---
    risk_level = item.risk_level if item.risk_level in RISK_LEVELS else "info"
    item.risk_level = risk_level
    if not matrix.is_allowed(risk_level, item.action):
        replacement = _replacement_action(matrix, risk_level, item.action)
        note = (f"combination risk_level={risk_level!r} + action={item.action!r} is "
                f"not allowed by contracts/risk_action_matrix.json; replaced with "
                f"{replacement!r}")
        item.adjustments.append(note)
        item.action = replacement
        log.warning(STAGE_AGGREGATE, note, {
            "result_id": item.result_id,
            "module": item.module,
            "target_ref": item.target_ref,
            "risk_level": risk_level,
            "original_action": item.original_action,
            "adjusted_action": replacement,
        })

    # --- verdict 一致性（只警告，不覆盖） ---
    declared = item.original_verdict
    if declared in VERDICTS:
        implied = _band(matrix, item.action)
        if declared != implied:
            log.warning(
                STAGE_AGGREGATE,
                (f"the result declares verdict {declared!r} but its action "
                 f"{item.action!r} implies {implied!r} in "
                 f"contracts/risk_action_matrix.json; the matrix-derived verdict "
                 f"is used"),
                {"result_id": item.result_id,
                 "module": item.module,
                 "target_ref": item.target_ref,
                 "declared_verdict": declared,
                 "matrix_verdict": implied},
            )

    return item


def _merge_rule_refs(records: list[dict]) -> tuple[list[dict], list[str]]:
    """按 `rule_id` 去重合并 `rule_refs[]`。返回 `(refs, conflicts)`。

    同一规则被多个模块引用时保留其来源信息；来源不一致时**如实记录冲突**，
    不擅自取舍（`references/aggregation_rules.md` §5）。
    """
    merged: dict[str, dict] = {}
    order: list[str] = []
    conflicts: list[str] = []
    for record in records:
        for ref in record.get("rule_refs") or []:
            rule_id = ref.get("rule_id")
            if not rule_id:
                continue
            if rule_id not in merged:
                merged[rule_id] = dict(ref)
                order.append(rule_id)
                continue
            existing = merged[rule_id]
            for key, value in ref.items():
                if existing.get(key) in (None, "") and value not in (None, ""):
                    existing[key] = value
            for key in ("source_tier", "source_url"):
                if (existing.get(key) and ref.get(key)
                        and existing[key] != ref[key]):
                    conflicts.append(
                        f"rule {rule_id}: {key} differs between modules "
                        f"({existing[key]!r} vs {ref[key]!r})")
    return [merged[rid] for rid in order], conflicts


def _merge_evidence_refs(records: list[dict]) -> list[dict]:
    """按 `evidence_id` 去重合并 `evidence_refs[]`。

    **只存引用**（硬约束 H5）：`artifact_ref` 原样透传，不复制内容。
    """
    merged: dict[str, dict] = {}
    order: list[str] = []
    for record in records:
        for ref in record.get("evidence_refs") or []:
            evidence_id = ref.get("evidence_id")
            if not evidence_id:
                continue
            if evidence_id not in merged:
                merged[evidence_id] = dict(ref)
                order.append(evidence_id)
                continue
            existing = merged[evidence_id]
            # `provided=true` 优先（已有凭证引用胜过「缺失」）
            if ref.get("provided") and not existing.get("provided"):
                existing.update({k: v for k, v in ref.items() if v not in (None, "")})
    return [merged[eid] for eid in order]


def _merge_unevaluated(records: list[dict]) -> list[dict]:
    """`unevaluated[]` 的并集 —— **绝不因其它模块通过而清除**（H3）。"""
    seen: set[tuple[str, str]] = set()
    items: list[dict] = []
    for record in records:
        for entry in record.get("unevaluated") or []:
            key = (str(entry.get("rule_id")), str(entry.get("reason")))
            if key in seen:
                continue
            seen.add(key)
            merged = dict(entry)
            missing = list(entry.get("missing_fields") or [])
            if missing:
                merged["missing_fields"] = missing
            items.append(merged)
    return items


def _merge_errors(records: list[dict]) -> list[dict]:
    """`errors[]` 的并集 —— 每条上游错误都保留（含原始 `error_id` 以便追溯）。"""
    seen: set[str] = set()
    items: list[dict] = []
    for record in records:
        for entry in record.get("errors") or []:
            error_id = str(entry.get("error_id") or "")
            key = error_id or f"{entry.get('stage')}|{entry.get('message')}"
            if key in seen:
                continue
            seen.add(key)
            items.append(dict(entry))
    return items


def _band_default(matrix: RiskMatrix, verdict: str) -> str:
    """某个 verdict 档的**默认动作** —— 取该档内最不激进的那个。

    档内没有候选动作时使用（例如「因未评估而升级为 REVIEW」）。
    """
    candidates = [a for a in matrix.action_order if _band(matrix, a) == verdict]
    return candidates[0] if candidates else "flag_for_review"


def _slug(text: str) -> str:
    safe = "".join(ch if (ch.isalnum() or ch in "-_") else "-" for ch in text)
    return safe.strip("-")[:60] or "target"


def aggregate_target(target_ref: str, records: list[dict], matrix: RiskMatrix,
                     request_id: str, log: ErrorLog) -> dict:
    """把**同一个目标**（商品）上的多条结果聚合成一条 `AuditResult`。"""
    sanitized = [sanitize(r, matrix, log) for r in records]

    # --- verdict：由清洗后的 action 推导（见模块 docstring 的不变式） ---
    bands = [_band(matrix, s.action) for s in sanitized]
    verdict = matrix.max_verdict(bands)

    # --- action：保留最细粒度的那一条 ---
    candidates = [s.action for s in sanitized
                  if _band(matrix, s.action) == verdict]
    action = matrix.most_specific(candidates) or _band_default(matrix, verdict)

    # --- risk_level：取最严重 ---
    risk_level = matrix.max_risk([s.risk_level for s in sanitized])

    # --- 组合合法性 ---
    if not matrix.is_allowed(risk_level, str(action)):
        replacement = _replacement_action(matrix, risk_level, str(action))
        log.warning(
            STAGE_AGGREGATE,
            (f"aggregated combination risk_level={risk_level!r} + action={action!r} "
             f"is not allowed by contracts/risk_action_matrix.json; replaced with "
             f"{replacement!r}"),
            {"target_ref": target_ref, "risk_level": risk_level,
             "action": action, "replacement": replacement},
        )
        action = replacement
        verdict = _band(matrix, action)

    # --- 未评估项（H3）：不得判为通过 ---
    unevaluated = _merge_unevaluated(records)
    if unevaluated and verdict == "PASS":
        verdict = "REVIEW"
        action = _band_default(matrix, "REVIEW")
        if not matrix.is_allowed(risk_level, action):
            action = "flag_for_review"

    # --- 置信度：取最弱（IP 结论不得因合并升为 confirmed，H1） ---
    confidence = min((s.confidence for s in sanitized),
                     key=lambda c: _CONFIDENCE_RANK.get(c, 1),
                     default="likely")

    rule_refs, conflicts = _merge_rule_refs(records)
    evidence_refs = _merge_evidence_refs(records)
    errors = _merge_errors(records)

    # --- 调整记录：如实进 errors[] ---
    for item in sanitized:
        for note in item.adjustments:
            errors.append({
                "error_id": f"SBRR-ADJ-{item.result_id[-12:]}",
                "stage": STAGE_AGGREGATE,
                "severity": "warning",
                "message": note,
                "context": {"result_id": item.result_id, "module": item.module,
                            "target_ref": target_ref},
            })

    # --- 需人工复核 ---
    requires_human_review = bool(
        matrix.always_human_review(action)
        or unevaluated
        or confidence == "signal"
        or any(s.record.get("requires_human_review") for s in sanitized)
        or any(e.get("severity") in ("error", "fatal") for e in errors)
    )

    result = {
        "result_id": f"RES-REPORT-{request_id}-{_slug(target_ref)}",
        "request_id": request_id,
        "module": "shopee-br-reporting",
        "target_ref": target_ref,
        "verdict": verdict,
        "risk_level": risk_level,
        "action": action,
        "reason": _build_reason(target_ref, sanitized, rule_refs, evidence_refs,
                                unevaluated, verdict, action),
        "rule_refs": rule_refs,
        "evidence_refs": evidence_refs,
        "confidence": confidence,
        "requires_human_review": requires_human_review,
        "review_rationale": _build_review_rationale(
            action, unevaluated, confidence, sanitized) if requires_human_review else None,
        "rule_version": _build_rule_version(sanitized),
        "provenance": {
            "produced_at": "",
            "producer": "",
            "source_refs": [],
            "notes": "",
        },
        "errors": errors,
        "unevaluated": unevaluated,
    }
    result["_conflicts"] = conflicts
    return result


def _build_reason(target_ref, sanitized, rule_refs, evidence_refs, unevaluated,
                  verdict, action) -> str:
    """一句话说明「为什么」—— 必须能回溯到具体规则与证据。"""
    modules = []
    for item in sanitized:
        if item.module and item.module not in modules:
            modules.append(item.module)
    rule_ids = [r.get("rule_id") for r in rule_refs if r.get("rule_id")]
    parts = [
        f"aggregated {len(sanitized)} module result(s) for {target_ref} "
        f"({', '.join(modules) if modules else 'no module'})"
    ]
    if rule_ids:
        parts.append("hit rule(s) " + ", ".join(rule_ids))
    else:
        parts.append("no rule was hit")
    parts.append(f"contract verdict {verdict} with action {action}")
    missing_evidence = sorted({e.get("evidence_type") for e in evidence_refs
                                if not e.get("provided") and e.get("evidence_type")})
    if missing_evidence:
        parts.append("evidence still missing: " + ", ".join(missing_evidence))
    if unevaluated:
        parts.append(f"{len(unevaluated)} rule(s) could not be evaluated")
    return "; ".join(parts)


def _build_review_rationale(action, unevaluated, confidence, sanitized) -> str:
    parts = []
    if unevaluated:
        rules = ", ".join(str(u.get("rule_id")) for u in unevaluated[:6])
        parts.append(f"{len(unevaluated)} rule(s) were not evaluated ({rules})")
    if confidence == "signal":
        parts.append("the weakest confidence in this batch is 'signal' "
                     "(screening hit only, not an established fact)")
    if action in HUMAN_ONLY_ACTIONS:
        parts.append(f"action {action!r} is human_only and must be executed by a person")
    elif action in DECISION_ACTIONS or action in REVIEW_ACTIONS:
        parts.append(f"action {action!r} requires a human decision")
    adjusted = [s for s in sanitized if s.adjustments]
    if adjusted:
        parts.append(f"{len(adjusted)} input result(s) were adjusted to satisfy "
                     f"contracts/risk_action_matrix.json")
    return "; ".join(parts) if parts else "manual review requested"


def _build_rule_version(sanitized) -> str:
    versions = sorted({str(s.record.get("rule_version")) for s in sanitized
                       if s.record.get("rule_version")})
    return ", ".join(versions) if versions else "unknown"


def aggregate(results: list[dict], matrix: RiskMatrix, request_id: str,
              log: ErrorLog | None = None) -> tuple[list[dict], dict]:
    """把一批 `AuditResult` 聚合成逐目标结论。

    返回 `(per_target_results, batch_result)`。
    """
    log = log if log is not None else ErrorLog()
    buckets: dict[str, list[dict]] = {}
    for record in results:
        target = str(record.get("target_ref") or "").strip()
        if not target:
            log.error(STAGE_AGGREGATE,
                      "a result has no target_ref and cannot be attributed to a "
                      "product; it was skipped",
                      {"result_id": record.get("result_id"),
                       "module": record.get("module")})
            continue
        buckets.setdefault(target, []).append(record)

    per_target: list[dict] = []
    for target in sorted(buckets):
        per_target.append(aggregate_target(target, buckets[target], matrix,
                                            request_id, log))

    batch = _aggregate_batch(per_target, results, matrix, request_id, log)
    return per_target, batch


def _aggregate_batch(per_target: list[dict], raw_results: list[dict],
                     matrix: RiskMatrix, request_id: str, log: ErrorLog) -> dict:
    """整批结论 —— 供报告 §1 摘要与下游主 Skill 使用。"""
    actions = [r["action"] for r in per_target]
    bands = [_band(matrix, a) for a in actions]
    verdict = matrix.max_verdict(bands)
    action = matrix.most_specific([a for a in actions
                                   if _band(matrix, a) == verdict])
    if action is None:
        action = _band_default(matrix, verdict)
    risk_level = matrix.max_risk([r["risk_level"] for r in per_target])

    unevaluated = _merge_unevaluated(raw_results)
    if unevaluated and verdict == "PASS":
        verdict = "REVIEW"
        action = _band_default(matrix, "REVIEW")

    confidence = min((r["confidence"] for r in per_target),
                     key=lambda c: _CONFIDENCE_RANK.get(c, 1), default="likely")

    rule_refs, conflicts = _merge_rule_refs(raw_results)
    evidence_refs = _merge_evidence_refs(raw_results)
    errors = _merge_errors(raw_results)

    requires_human_review = bool(
        matrix.always_human_review(action)
        or unevaluated
        or confidence == "signal"
        or any(r.get("requires_human_review") for r in per_target)
    )

    counts = {v: sum(1 for r in per_target if r["verdict"] == v) for v in VERDICTS}
    result = {
        "result_id": f"RES-REPORT-{request_id}-batch",
        "request_id": request_id,
        "module": "shopee-br-reporting",
        "target_ref": f"batch-{request_id}",
        "verdict": verdict,
        "risk_level": risk_level,
        "action": action,
        "reason": _build_batch_reason(per_target, counts, verdict, action,
                                       unevaluated, rule_refs),
        "rule_refs": rule_refs,
        "evidence_refs": evidence_refs,
        "confidence": confidence,
        "requires_human_review": requires_human_review,
        "review_rationale": _build_review_rationale(
            action, unevaluated, confidence, []) if requires_human_review else None,
        "rule_version": _build_rule_version(
            [SanitizedResult(r) for r in raw_results]),
        "provenance": {
            "produced_at": "",
            "producer": "",
            "source_refs": [],
            "notes": "",
        },
        "errors": errors,
        "unevaluated": unevaluated,
    }
    result["_conflicts"] = conflicts
    result["_counts"] = counts
    return result


def _build_batch_reason(per_target, counts, verdict, action, unevaluated,
                        rule_refs) -> str:
    parts = [f"aggregated {len(per_target)} target(s)"]
    distribution = ", ".join(f"{v}={counts[v]}" for v in VERDICTS if counts.get(v))
    if distribution:
        parts.append("verdict distribution " + distribution)
    rule_ids = sorted({r.get("rule_id") for r in rule_refs if r.get("rule_id")})
    if rule_ids:
        parts.append(f"{len(rule_ids)} distinct rule(s) hit")
    parts.append(f"batch verdict {verdict} with action {action}")
    if unevaluated:
        parts.append(f"{len(unevaluated)} unevaluated rule(s) carried over")
    return "; ".join(parts)
