"""判定引擎 —— 商品内容合规审核的核心。

输入：`contracts/skill_input.schema.json`（`SkillInput`）
输出：`contracts/audit_result.schema.json`（`AuditResult[]`）+
     `contracts/module_handoff.schema.json`（`ModuleHandoff`）

判定分三层，各层职责不重叠：

| 层 | 输入 | 产出 | 权威依据 |
|---|---|---|---|
| 规则层 | 商品 + 规则 | 命中 / 未命中 / 未评估 | `rules/**` + `data/schema/rule.schema.json` |
| 矩阵层 | 命中规则的严重度 + 声明动作 | `risk_level` / `action` / `verdict` | `contracts/risk_action_matrix.json` |
| 词库层 | 商品文案 | 筛查信号（**不产生结论**） | `lexicon/**` + `contracts/lexicon_rule_map.json` |

**关键词命中 ≠ 违规。** 词库命中只作为佐证写入 `evidence_refs` 与
`provenance.notes`；是否违规由规则层判定，是否阻断由矩阵层决定。
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from . import matrix as matrix_mod
from . import rules as rules_mod
from .conditions import MATCH, NO_MATCH, UNEVALUATED, ConditionError, evaluate_condition
from .fields import is_empty
from .lexicon import LexiconUnavailable, candidate_rules, load_rule_map, scan_product, summarise

MODULE_NAME = "shopee-br-listing-audit"
CONTRACT_VERSION = "1.0.0"

#: 错误阶段。
STAGE_RULE_LOADING = "rule_loading"
STAGE_RULE_EVALUATION = "rule_evaluation"
STAGE_LEXICON = "lexicon_scan"
STAGE_INPUT = "input"

#: 严重度排序（`PROJECT_RULES.md` §7.1）。
SEVERITY_ORDER = ("info", "low", "medium", "high", "critical")

#: verdict 聚合顺序（`contracts/risk_action_matrix.json` → verdict_aggregation）。
VERDICT_ORDER = ("PASS", "REVISE", "REVIEW", "BLOCK")

#: 动作粒度（同档位内更细粒度优先）。`block` / `freeze_relist` /
#: `escalate_legal` 同属 BLOCK 档。
ACTION_GRANULARITY = {
    "allow": 0,
    "flag_for_review": 1,
    "require_evidence": 2,
    "revise": 3,
    "block": 4,
    "freeze_relist": 5,
    "escalate_legal": 6,
}

#: 结构性算子 —— 命中即「字段事实」，不是文案推断。
STRUCTURAL_OPERATORS = frozenset({
    "field_missing",
    "has_field",
    "has_nonempty",
    "image_count_lt",
    "image_count_gte",
    "length_lt",
    "length_gte",
    "equals",
    "not_equals",
    "gt",
    "gte",
    "lt",
    "lte",
})

#: 权威来源层级 —— 可产生确定性结论。
AUTHORITATIVE_TIERS = frozenset({"platform_official", "law"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z")


class AuditError(Exception):
    """模块级致命错误 —— 规则库不可用等，模块必须显式失败。"""


# ---------------------------------------------------------------------------
# 引擎
# ---------------------------------------------------------------------------

class ListingAuditEngine:
    """商品内容合规审核引擎。"""

    def __init__(self, root: str | None = None, options: dict | None = None):
        self.root = root or self._repo_root()
        self.options = dict(options or {})
        self.errors: list[dict] = []
        self._error_counter = 0

        self.matrix, matrix_error = matrix_mod.load_matrix(self.root)
        if matrix_error:
            self._add_error(STAGE_RULE_LOADING, "error", matrix_error,
                            {"fallback": "conservative (allow/flag_for_review only)"})
        self._matrix_error = matrix_error

        self.rules = self._load_rules()
        self.lexicon_map = self._load_lexicon_map()
        self.scanner = self._load_scanner()

    # -- 装载 ---------------------------------------------------------------

    @staticmethod
    def _repo_root() -> str:
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(here, "..", "..", "..", ".."))

    def _load_rules(self) -> list[dict]:
        prefixes = self.options.get("rule_prefixes")
        if isinstance(prefixes, str):
            prefixes = (prefixes,)
        try:
            return rules_mod.load_rules(
                root=self.root,
                extra_rules=self.options.get("rules"),
                prefixes=tuple(prefixes) if prefixes else None,
            )
        except rules_mod.RuleLoadError as exc:
            self._add_error(STAGE_RULE_LOADING, "fatal", str(exc),
                            {"action": "module stops; no result is produced"})
            raise AuditError(str(exc)) from exc

    def _load_lexicon_map(self) -> dict[str, list[str]]:
        try:
            return load_rule_map(self.root)
        except LexiconUnavailable as exc:
            self._add_error(STAGE_LEXICON, "warning", str(exc),
                            {"effect": "lexical screening is reported as unevaluated"})
            return {}

    def _load_scanner(self):
        from .lexicon import _load_scanner as loader
        try:
            return loader(self.root)
        except LexiconUnavailable as exc:
            self._add_error(STAGE_LEXICON, "warning", str(exc),
                            {"effect": "lexical screening is reported as unevaluated"})
            return None

    # -- 错误 ---------------------------------------------------------------

    def _add_error(self, stage: str, severity: str, message: str,
                   context: dict | None = None) -> dict:
        self._error_counter += 1
        item = {
            "error_id": f"ERR-LISTING-{self._error_counter:04d}",
            "stage": stage,
            "severity": severity,
            "message": message,
        }
        if context:
            item["context"] = context
        self.errors.append(item)
        return item

    # -- 规则判定 -----------------------------------------------------------

    def evaluate_product(self, product: dict) -> dict:
        """评估单个商品。返回内部结构（不是契约对象）。"""
        product_id = str(product.get("product_id") or "<unknown>")

        fired: list[dict] = []
        unevaluated: list[dict] = []

        for rule in self.rules:
            outcome = self._evaluate_rule(product, rule)
            if outcome["status"] == "fired":
                fired.append(outcome)
            elif outcome["status"] == "unevaluated":
                unevaluated.append(outcome)

        # --- 词库筛查（信号层，不产生结论） ---
        hits: list[dict] = []
        lexicon_state = "evaluated"
        if self.scanner is not None:
            try:
                hits = scan_product(product, root=self.root, scanner=self.scanner)
            except Exception as exc:  # noqa: BLE001 - 词库故障不得中断整批
                lexicon_state = "unevaluated"
                self._add_error(STAGE_LEXICON, "warning",
                                f"lexicon scan failed for {product_id}: {exc}",
                                {"product_id": product_id})
        else:
            lexicon_state = "unevaluated"

        lexical_candidates = candidate_rules(
            hits, self.lexicon_map, rules_mod.OWNED_PREFIXES)

        return {
            "product_id": product_id,
            "product": product,
            "fired": fired,
            "unevaluated": unevaluated,
            "lexicon_hits": hits,
            "lexicon_state": lexicon_state,
            "lexical_candidates": lexical_candidates,
        }

    def _evaluate_rule(self, product: dict, rule: dict) -> dict:
        """评估单条规则。"""
        rule_id = rule["rule_id"]

        # --- 规则状态：非 active 的规则**不产出任何结论** ---
        # （`references/policy_currency.md` §1：draft / deprecated / suspended
        #  一律不产出结论；只有 active 才是可判定状态。）
        if rule.get("status") != "active":
            return {
                "status": "skipped",
                "rule": rule,
                "reason": (f"rule {rule_id} has status '{rule.get('status')}' and "
                           f"therefore produced no conclusion"),
                "missing_fields": [],
                "detail": None,
            }

        conditions = rule.get("trigger_conditions") or []
        if not conditions:
            return {
                "status": "unevaluated",
                "rule": rule,
                "reason": f"rule {rule_id} declares no trigger condition",
                "missing_fields": [],
                "detail": None,
            }

        details = []
        missing_fields: list[str] = []
        for condition in conditions:
            try:
                result = evaluate_condition(product, condition)
            except ConditionError as exc:
                self._add_error(STAGE_RULE_EVALUATION, "error",
                                f"rule {rule_id} could not be evaluated: {exc}",
                                {"rule_id": rule_id, "product_id": product.get("product_id")})
                return {
                    "status": "unevaluated",
                    "rule": rule,
                    "reason": f"rule {rule_id} could not be evaluated: {exc}",
                    "missing_fields": [],
                    "detail": None,
                }
            details.append(result)
            if result["status"] == UNEVALUATED:
                for required in condition.get("requires_input") or []:
                    if required not in missing_fields:
                        missing_fields.append(required)
                if not missing_fields:
                    missing_fields.append(str(condition.get("field") or "unknown"))

        if any(item["status"] == UNEVALUATED for item in details):
            return {
                "status": "unevaluated",
                "rule": rule,
                "reason": (f"required input field(s) are missing or empty for rule "
                           f"{rule_id}: {', '.join(missing_fields)}; the rule was NOT "
                           f"evaluated and is NOT counted as a pass"),
                "missing_fields": missing_fields,
                "detail": None,
            }

        if not all(item["status"] == MATCH for item in details):
            return {"status": "not_fired", "rule": rule, "reason": "",
                    "missing_fields": [], "detail": details}

        # --- 命中：查表定动作 ---
        risk_level = str(rule.get("severity") or "info")
        declared = str(rule.get("action") or "flag_for_review")
        action, downgrade_reason = self._resolve_action(rule, risk_level, declared)
        confidence = self._confidence(rule, details)

        return {
            "status": "fired",
            "rule": rule,
            "risk_level": risk_level,
            "declared_action": declared,
            "action": action,
            "downgrade_reason": downgrade_reason,
            "confidence": confidence,
            "reason": "",
            "missing_fields": [],
            "detail": details,
        }

    def _resolve_action(self, rule: dict, risk_level: str,
                        declared: str) -> tuple[str, str | None]:
        """把规则声明的动作解析成矩阵允许的动作。

        * **H2**：阻断类动作只能来自 `platform_official` / `law` 的
          `active` 规则；否则降级为 `flag_for_review`。
        * 矩阵不允许该组合 → 取该风险等级下最接近且**不弱于**声明动作
          的允许动作；找不到则取最强允许动作并记录冲突。
        """
        tier = (rule.get("source") or {}).get("tier")
        status = rule.get("status")

        # --- 规则状态：非 active 不产出结论 ---
        if status != "active":
            fallback = self._best_allowed(risk_level, ("flag_for_review", "allow"))
            return fallback, (
                f"rule status is '{status}' (not 'active'), so its declared action "
                f"'{declared}' was not applied; the rule was downgraded to "
                f"'{fallback}'"
            )

        # --- H2：来源层级限制 ---
        if declared in rules_mod.BLOCKING_ACTIONS and not rules_mod.blocking_allowed(rule):
            fallback = self._best_allowed(risk_level, ("require_evidence", "flag_for_review"))
            return fallback, (
                f"the declared action '{declared}' requires source.tier in "
                f"{{platform_official, law}} and status 'active'; this rule has "
                f"tier '{tier}' and status '{status}', so the action was downgraded "
                f"to '{fallback}' (hard constraint H2)"
            )

        # --- 矩阵允许性 ---
        if matrix_mod.is_allowed(self.matrix, risk_level, declared):
            return declared, None

        # 声明动作不被矩阵允许：取不弱于声明的最细允许动作
        alternatives = self._allowed_actions(risk_level)
        declared_rank = self._action_rank(declared)
        stronger = [item for item in alternatives
                    if self._action_rank(item) >= declared_rank]
        if stronger:
            chosen = min(stronger, key=self._action_rank)
            return chosen, (
                f"the declared action '{declared}' is not allowed for risk level "
                f"'{risk_level}' by contracts/risk_action_matrix.json; the "
                f"closest allowed action '{chosen}' was applied instead"
            )
        chosen = self._best_allowed(risk_level, ("block", "require_evidence",
                                                  "flag_for_review"))
        self._add_error(
            STAGE_RULE_EVALUATION, "error",
            f"no allowed action matches the declared action '{declared}' at risk "
            f"level '{risk_level}' for rule {rule.get('rule_id')}; the strongest "
            f"allowed action '{chosen}' was applied",
            {"rule_id": rule.get("rule_id"), "risk_level": risk_level,
             "declared_action": declared},
        )
        return chosen, (
            f"the declared action '{declared}' conflicts with "
            f"contracts/risk_action_matrix.json at risk level '{risk_level}'; "
            f"the strongest allowed action '{chosen}' was applied"
        )

    def _allowed_actions(self, risk_level: str) -> list[str]:
        allowed = []
        for entry in self.matrix.get("matrix", []):
            if entry.get("risk_level") == risk_level and entry.get("allowed"):
                allowed.append(str(entry.get("action")))
        return allowed

    def _best_allowed(self, risk_level: str, preference: tuple[str, ...]) -> str:
        """在允许的动作里按偏好取第一个；都不允许则取最强。"""
        allowed = self._allowed_actions(risk_level)
        for candidate in preference:
            if candidate in allowed:
                return candidate
        if allowed:
            return max(allowed, key=self._action_rank)
        return "flag_for_review"

    def _action_rank(self, action: str) -> tuple[int, int]:
        """动作的可比强度：(verdict 权重, 粒度)。"""
        verdict = matrix_mod.verdict_for(self.matrix, action)
        verdict_weight = VERDICT_ORDER.index(verdict) if verdict in VERDICT_ORDER else 1
        return (verdict_weight, ACTION_GRANULARITY.get(action, 0))

    def _confidence(self, rule: dict, details: list[dict]) -> str:
        """置信度。

        * `confirmed` —— 结构性字段事实 + 权威来源 + `active` 规则。
        * `likely` —— 权威来源的文案正则命中。
        * `signal` —— 非权威来源 / 非 `active` 规则 / 仅词库信号。
        """
        tier = (rule.get("source") or {}).get("tier")
        if rule.get("status") != "active" or tier not in AUTHORITATIVE_TIERS:
            return "signal"
        operators = {item.get("operator") for item in details}
        if operators and operators <= STRUCTURAL_OPERATORS:
            return "confirmed"
        return "likely"

    # -- 聚合 ---------------------------------------------------------------

    def build_result(self, evaluation: dict, request_id: str,
                     produced_at: str) -> dict | None:
        """把评估结果聚合成一条 `AuditResult`。

        聚合规则（`contracts/risk_action_matrix.json` → verdict_aggregation）：
        **verdict 取最重；action 保留最细粒度的那一条。**
        """
        product = evaluation["product"]
        product_id = evaluation["product_id"]
        fired = evaluation["fired"]
        unevaluated = evaluation["unevaluated"]

        unevaluated_entries = [
            {
                "rule_id": item["rule"]["rule_id"],
                "reason": item["reason"],
                "missing_fields": item["missing_fields"],
            }
            for item in unevaluated
        ]

        if not fired:
            if unevaluated_entries:
                # H3：无法评估 ⇒ 不得判通过。产出一条 REVIEW 结果，
                # 明确说明「未评估」而不是「通过」。
                reason = (
                    f"no rule fired for {product_id}, but {len(unevaluated_entries)} "
                    f"rule(s) could not be evaluated because required input was "
                    f"missing; the listing is therefore NOT confirmed compliant"
                )
                action = self._best_allowed("info", ("flag_for_review", "allow"))
                risk_level = "info"
                verdict = matrix_mod.verdict_for(self.matrix, action)
                rule_refs: list[dict] = []
                confidence = "signal"
            else:
                reason = (
                    f"all {len(self.rules)} applicable rule(s) were evaluated against "
                    f"{product_id} and none fired; no prohibited, restricted, "
                    f"medicine or listing-quality signal was found"
                )
                action = "allow"
                risk_level = "info"
                verdict = matrix_mod.verdict_for(self.matrix, action)
                rule_refs = []
                confidence = "confirmed"
            evidence_refs = self._build_evidence_refs(evaluation, product_id, fired)
            return self._assemble(
                request_id=request_id,
                produced_at=produced_at,
                product_id=product_id,
                verdict=verdict,
                risk_level=risk_level,
                action=action,
                reason=reason,
                rule_refs=rule_refs,
                evidence_refs=evidence_refs,
                confidence=confidence,
                requires_human_review=bool(unevaluated_entries),
                review_rationale=(
                    "some rules could not be evaluated because required input was "
                    "missing; a reviewer must complete the data before this listing "
                    "can be considered compliant" if unevaluated_entries else None),
                errors=[],
                unevaluated=unevaluated_entries,
                evaluation=evaluation,
            )

        # --- 有命中：取最重的风险等级与最细粒度的动作 ---
        risk_level = max((item["risk_level"] for item in fired),
                         key=lambda level: SEVERITY_ORDER.index(level))
        action = max((item["action"] for item in fired), key=self._action_rank)
        action, matrix_note = self._align_combo(risk_level, action)

        verdict = matrix_mod.verdict_for(self.matrix, action)
        confidence = min((item["confidence"] for item in fired),
                         key=lambda value: ("signal", "likely", "confirmed").index(value))

        rule_refs = [self._build_rule_ref(item) for item in fired]
        evidence_refs = self._build_evidence_refs(evaluation, product_id, fired)

        reasons = []
        for item in fired:
            rule = item["rule"]
            bits = [f"{rule['rule_id']} ({rule.get('title') or rule.get('category')})"]
            excerpt = self._first_excerpt(item["detail"])
            if excerpt:
                bits.append(f"matched in {item['detail'][0].get('field')}: {excerpt}")
            if item.get("downgrade_reason"):
                bits.append(item["downgrade_reason"])
            reasons.append("; ".join(bits))
        reason = (
            f"{len(fired)} rule(s) fired on {product_id}: " + " | ".join(reasons)
        )
        if matrix_note:
            reason += f" | {matrix_note}"

        requires_human_review, review_rationale = self._review_requirements(
            fired, unevaluated_entries, action, confidence, evaluation)

        errors = []
        for item in unevaluated:
            errors.append({
                "error_id": f"ERR-LISTING-UNEVAL-{item['rule']['rule_id']}",
                "stage": STAGE_RULE_EVALUATION,
                "severity": "warning",
                "message": item["reason"],
                "context": {"rule_id": item["rule"]["rule_id"],
                            "product_id": product_id,
                            "missing_fields": item["missing_fields"]},
            })

        return self._assemble(
            request_id=request_id,
            produced_at=produced_at,
            product_id=product_id,
            verdict=verdict,
            risk_level=risk_level,
            action=action,
            reason=reason,
            rule_refs=rule_refs,
            evidence_refs=evidence_refs,
            confidence=confidence,
            requires_human_review=requires_human_review,
            review_rationale=review_rationale,
            errors=errors,
            unevaluated=unevaluated_entries,
            evaluation=evaluation,
        )

    def _align_combo(self, risk_level: str, action: str) -> tuple[str, str | None]:
        """保证 `(risk_level, action)` 是矩阵允许的组合。

        确定性结论**不可被降级**（H2）—— 若组合不允许，保留动作并把
        风险等级对齐到该动作允许的最低等级，而不是把动作改弱。
        """
        if matrix_mod.is_allowed(self.matrix, risk_level, action):
            return action, None
        for level in SEVERITY_ORDER:
            if matrix_mod.is_allowed(self.matrix, level, action):
                note = (
                    f"risk level was aligned from '{risk_level}' to '{level}' so that "
                    f"action '{action}' stays a matrix-allowed combination "
                    f"(contracts/risk_action_matrix.json); the action itself was not "
                    f"weakened"
                )
                return action, note
        return self._best_allowed(risk_level, ("flag_for_review", "allow")), (
            f"action '{action}' is not allowed at risk level '{risk_level}' and no "
            f"matrix cell permits it; the listing was downgraded to a review flag"
        )

    def _review_requirements(self, fired: list[dict], unevaluated: list[dict],
                             action: str, confidence: str,
                             evaluation: dict) -> tuple[bool, str | None]:
        """`requires_human_review` 的判定（`PROJECT_RULES.md` §10）。"""
        reasons: list[str] = []
        if matrix_mod.always_human_review(self.matrix, action):
            reasons.append(f"action '{action}' always requires human review")
        for item in fired:
            rule = item["rule"]
            if rules_mod.is_ip_rule(rule):
                reasons.append(f"rule {rule['rule_id']} is an IP-category rule")
            if rule.get("requires_human_review"):
                reasons.append(f"rule {rule['rule_id']} requires human review")
            if rule.get("status") != "active":
                reasons.append(f"rule {rule['rule_id']} status is '{rule.get('status')}'")
            tier = (rule.get("source") or {}).get("tier")
            if tier in ("internal_risk", "unverified"):
                reasons.append(f"rule {rule['rule_id']} source tier is '{tier}'")
            if item.get("downgrade_reason"):
                reasons.append(item["downgrade_reason"])
        if confidence == "signal":
            reasons.append("confidence is 'signal' (keyword/screening level only)")
        if unevaluated:
            reasons.append(
                f"{len(unevaluated)} rule(s) could not be evaluated because input "
                f"was missing"
            )
        if evaluation.get("lexicon_state") == "unevaluated":
            reasons.append("lexical screening could not be run")
        if not reasons:
            return False, None
        return True, "manual review needed: " + "; ".join(reasons)

    # -- 引用构造 -----------------------------------------------------------

    def _build_rule_ref(self, item: dict) -> dict:
        rule = item["rule"]
        detail = item["detail"] or []
        first = detail[0] if detail else {}
        source = rule.get("source") or {}
        return {
            "rule_id": rule["rule_id"],
            "title": rule.get("title"),
            "matched_field": first.get("field"),
            "matched_excerpt": self._first_excerpt(detail),
            "source_tier": source.get("tier"),
            "source_url": source.get("url"),
        }

    @staticmethod
    def _first_excerpt(detail: list[dict]) -> str | None:
        for entry in detail:
            if entry.get("status") == MATCH and entry.get("excerpt"):
                return entry["excerpt"]
        return None

    def _build_evidence_refs(self, evaluation: dict, product_id: str,
                             fired: list[dict]) -> list[dict]:
        """证据引用。

        两类：
        1. **观测证据** —— 命中所在字段（`listing_field` / `image`），
           `provided: true`，`artifact_ref` 只存字段路径（硬约束 H5）。
        2. **待补证据** —— 规则 `evidence_required` 里未提供的类型，
           `provided: false`，`artifact_ref` 为 `null`。
        """
        refs: list[dict] = []
        seen: set[str] = set()

        for item in fired:
            rule = item["rule"]
            detail = item["detail"] or []
            for entry in detail:
                if entry.get("status") != MATCH:
                    continue
                field = str(entry.get("field") or "")
                evidence_type = "image" if field in ("image", "image_text") else "listing_field"
                evidence_id = f"EV-{rule['rule_id']}-{field}".replace(".", "-")
                if evidence_id in seen:
                    continue
                seen.add(evidence_id)
                refs.append({
                    "evidence_id": evidence_id,
                    "evidence_type": evidence_type,
                    "provided": True,
                    "artifact_ref": f"products/{product_id}/{field}",
                    "source_locator": field,
                    "collected_at": None,
                    "notes": (f"rule {rule['rule_id']} matched here: "
                              f"{entry.get('excerpt')}"),
                })

        for item in fired:
            rule = item["rule"]
            for evidence_type in rule.get("evidence_required") or []:
                evidence_id = f"EV-{rule['rule_id']}-REQ-{evidence_type}"
                if evidence_id in seen:
                    continue
                seen.add(evidence_id)
                refs.append({
                    "evidence_id": evidence_id,
                    "evidence_type": str(evidence_type),
                    "provided": False,
                    "artifact_ref": None,
                    "source_locator": None,
                    "collected_at": None,
                    "notes": (f"required to close {rule['rule_id']}; the module does "
                              f"not store credential contents (hard constraint H5)"),
                })

        # --- 词库筛查命中（佐证信号，非结论） ---
        for hit in evaluation.get("lexicon_hits", []):
            group_id = str(hit.get("group_id") or "unknown")
            term = str(hit.get("term") or "")
            evidence_id = f"EV-LEX-{group_id}-{term}".replace(" ", "-")
            if evidence_id in seen:
                continue
            seen.add(evidence_id)
            exempt = hit.get("exempt")
            notes = (f"lexicon screening hit '{term}' in group '{group_id}' "
                     f"(field {hit.get('field')}); a lexical hit is a signal, not a "
                     f"violation finding")
            if isinstance(exempt, dict):
                notes += (f"; exemption {exempt.get('id')} applied "
                          f"({exempt.get('reason')})")
            refs.append({
                "evidence_id": evidence_id,
                "evidence_type": "listing_field",
                "provided": True,
                "artifact_ref": f"products/{evaluation['product_id']}/{hit.get('field')}",
                "source_locator": str(hit.get("field")),
                "collected_at": None,
                "notes": notes,
            })

        return refs

    # -- 组装 ---------------------------------------------------------------

    def _assemble(self, *, request_id: str, produced_at: str, product_id: str,
                  verdict: str, risk_level: str, action: str, reason: str,
                  rule_refs: list[dict], evidence_refs: list[dict],
                  confidence: str, requires_human_review: bool,
                  review_rationale: str | None, errors: list[dict],
                  unevaluated: list[dict], evaluation: dict) -> dict:
        product = evaluation["product"]
        source_refs = []
        raw_ref = (product.get("source") or {}).get("raw_ref")
        if raw_ref:
            source_refs.append(str(raw_ref))
        path = (product.get("source") or {}).get("path")
        if path:
            source_refs.append(str(path))

        fired = evaluation["fired"]
        notes = self._provenance_notes(evaluation, fired)

        return {
            "result_id": f"RES-LISTING-{request_id}-{product_id}"[:120],
            "request_id": request_id,
            "module": MODULE_NAME,
            "target_ref": product_id,
            "verdict": verdict,
            "risk_level": risk_level,
            "action": action,
            "reason": reason,
            "rule_refs": rule_refs,
            "evidence_refs": evidence_refs,
            "confidence": confidence,
            "requires_human_review": requires_human_review,
            "review_rationale": review_rationale,
            "rule_version": self.rule_version(),
            "provenance": {
                "produced_at": produced_at,
                "producer": f"{MODULE_NAME}/{self.module_version()}",
                "source_refs": source_refs,
                "notes": notes,
            },
            "errors": errors,
            "unevaluated": unevaluated,
        }

    def _provenance_notes(self, evaluation: dict, fired: list[dict]) -> str:
        parts = [
            f"rules evaluated: {len(self.rules)}; fired: {len(fired)}; "
            f"unevaluated: {len(evaluation['unevaluated'])}",
        ]
        if fired:
            for item in fired:
                rule = item["rule"]
                source = rule.get("source") or {}
                excerpt = source.get("excerpt") or ""
                if len(excerpt) > 200:
                    excerpt = excerpt[:200] + "…"
                parts.append(
                    f"{rule['rule_id']} | tier={source.get('tier')} | "
                    f"status={rule.get('status')} | v{rule.get('version')} | "
                    f"last_verified={source.get('last_verified')} | "
                    f"source_excerpt={excerpt!r}"
                )
        summary = summarise(evaluation.get("lexicon_hits", []))
        parts.append(
            f"lexicon screening: {summary['total_hits']} hit(s) in "
            f"{len(summary['groups'])} group(s); {summary['exempted_hits']} exempted "
            f"({', '.join(summary['exemption_ids']) or 'none'})"
        )
        if evaluation.get("lexicon_state") == "unevaluated":
            parts.append("lexicon screening was NOT evaluated (scanner unavailable)")
        return " || ".join(parts)

    # -- 版本 ---------------------------------------------------------------

    @staticmethod
    def module_version() -> str:
        from . import __version__
        return __version__

    def rule_version(self) -> str:
        """规则集版本 —— 规则 ID + 版本 + 状态的稳定摘要。"""
        payload = json.dumps(
            [[rule["rule_id"], rule.get("version"), rule.get("status")]
             for rule in self.rules],
            ensure_ascii=False, sort_keys=True,
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        return f"sbr-listing-rules/{self.module_version()}+{digest}"
