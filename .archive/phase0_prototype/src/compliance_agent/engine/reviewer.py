"""The review orchestrator: run every check over a set of products and produce
one JSON result plus one Markdown report.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

from ..models import Case, Finding, Product, Rule
from .duplicates import DuplicateIndex, find_cross_store_duplicates
from .evaluator import evaluate_product, product_action, product_status
from .loader import load_rules
from .relist import RelistIndex

DUPLICATE_SENTINEL = "__DUPLICATE_SIGNAL__"
CROSS_STORE_SENTINEL = "__CROSS_STORE_DUPLICATE_SIGNAL__"
RELIST_SENTINEL = "__RELIST_SIGNAL__"
OPEN_CASE_SENTINEL = "__OPEN_CASE_SIGNAL__"
REMOVED_LISTING_SENTINEL = "__REMOVED_LISTING_SIGNAL__"

# Case statuses that mean the platform already acted (vs. still under review).
ENFORCED_CASE_STATUSES = {"blocked", "relist_frozen", "escalated", "rejected"}
OPEN_CASE_STATUSES = {"open", "under_review", "awaiting_evidence"}


class Reviewer:
    def __init__(self, rules: list[Rule] | None = None,
                 history_products: list[Product] | None = None,
                 history_cases: list[Case] | None = None):
        self.rules = rules if rules is not None else load_rules()
        self.history_products = history_products or []
        self.history_cases = history_cases or []

    # ---------------------------------------------------------------- run
    def review(self, products: list[Product],
               run_id: str | None = None,
               scope: dict | None = None) -> dict:
        run_id = run_id or f"RUN-{uuid.uuid4().hex[:10]}"
        errors: list[dict] = []
        findings: list[Finding] = []
        seq = iter(range(1, 10 ** 7))

        # --- duplicate engine (within + cross store) ---
        dup_index = DuplicateIndex()
        for p in products:
            dup_index.add(p)
        dup_matches = dup_index.find_all(min_score=0.5)
        dup_by_product: dict[str, list] = {}
        for m in dup_matches:
            dup_by_product.setdefault(m.product_id, []).append(m)
            dup_by_product.setdefault(m.other_product_id, []).append(m)

        # --- relist engine ---
        relist_index = RelistIndex()
        for p in self.history_products:
            relist_index.add_product(p)
        for c in self.history_cases:
            relist_index.add_case(c)
        for p in products:
            relist_index.add_product(p)
        relist_by_product: dict[str, list] = {}
        for p in products:
            for m in relist_index.check(p):
                relist_by_product.setdefault(p.product_id, []).append(m)

        # --- case association (open / enforced) ---
        case_by_product: dict[str, list] = {}
        for c in self.history_cases:
            for pid in (c.product_ids or []):
                case_by_product.setdefault(pid, []).append(c)

        # --- per-product rule evaluation ---
        product_findings: dict[str, list[Finding]] = {}
        data_gaps: dict[str, set] = {}
        for p in products:
            # inject sentinel signals so the duplicate/relist rules can fire
            injected = Product(**{**p.__dict__})
            injected.description = (p.description or "") + "\n"
            signals = []
            for m in dup_by_product.get(p.product_id, []):
                if m.same_shop:
                    signals.append(DUPLICATE_SENTINEL)
                else:
                    signals.append(CROSS_STORE_SENTINEL)
            if relist_by_product.get(p.product_id):
                signals.append(RELIST_SENTINEL)
            product_cases = case_by_product.get(p.product_id, [])
            for c in product_cases:
                if c.status in ENFORCED_CASE_STATUSES:
                    signals.append(REMOVED_LISTING_SENTINEL)
                elif c.status in OPEN_CASE_STATUSES:
                    signals.append(OPEN_CASE_SENTINEL)
            if signals:
                injected.description += " " + " ".join(sorted(set(signals)))

            fs = evaluate_product(injected, self.rules, seq)
            # map the sentinel matches back to their real evidence
            for f in fs:
                if f.matched_excerpt and DUPLICATE_SENTINEL in f.matched_excerpt:
                    f.matched_field = "duplicate_engine"
                    f.matched_excerpt = _describe_duplicate(
                        dup_by_product.get(p.product_id, []), same_shop=True)
                if f.matched_excerpt and CROSS_STORE_SENTINEL in f.matched_excerpt:
                    f.matched_field = "duplicate_engine"
                    f.matched_excerpt = _describe_duplicate(
                        dup_by_product.get(p.product_id, []), same_shop=False)
                if f.matched_excerpt and RELIST_SENTINEL in f.matched_excerpt:
                    f.matched_field = "relist_engine"
                    f.matched_excerpt = _describe_relist(
                        relist_by_product.get(p.product_id, []))
                if f.matched_excerpt and OPEN_CASE_SENTINEL in f.matched_excerpt:
                    f.matched_field = "case_engine"
                    f.matched_excerpt = _describe_cases(product_cases, enforced=False)
                if f.matched_excerpt and REMOVED_LISTING_SENTINEL in f.matched_excerpt:
                    f.matched_field = "case_engine"
                    f.matched_excerpt = _describe_cases(product_cases, enforced=True)
            product_findings[p.product_id] = fs
            findings.extend(fs)

        # --- data gaps: rules that could not be evaluated -----------------
        # A rule whose required input fields are absent was SKIPPED, not
        # passed. The operator must know which checks did not run.
        skipped_rules: dict[str, list] = {}
        for r in self.rules:
            required = set()
            for cond in r.trigger_conditions:
                required.update(cond.get("requires_input") or [])
            if not required:
                continue
            present_anywhere = any(
                p.field_value(f) not in (None, "", [], {}) for f in required
                for p in products)
            if not present_anywhere and products:
                skipped_rules[r.rule_id] = sorted(required)
        for rid, fields in skipped_rules.items():
            errors.append({
                "stage": "rule_evaluation",
                "message": (f"rule {rid} was not evaluated: the input carried none "
                            f"of the required field(s) {', '.join(fields)}"),
                "source": None,
                "severity": "warning",
                "context": {"rule_id": rid, "required_fields": fields},
            })

        # --- IP downgrade when a compatibility statement is present ---
        compat_rules = {r.rule_id for r in self.rules if "compatibility" in (r.tags or [])}
        for f in findings:
            if f.rule_id in compat_rules:
                continue
            for p in products:
                if p.product_id != f.product_id:
                    continue
                if _has_compat_context(p):
                    if f.category in ("ip_trademark", "ip_copyright", "ip_design"):
                        f.confidence = "signal"
                        f.human_review_required = True
                        f.explanation += (
                            " NOTE: a compatibility statement ('compatível com') is "
                            "present; Brazilian law permits nominative use of a mark "
                            "to identify the compatible product, so this may be a "
                            "false positive. Verify whether the mark is used as a "
                            "brand claim before acting.")

        # --- product-level roll-up ---
        product_rows = []
        by_category: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        by_decision: dict[str, int] = {}
        for p in products:
            fs = product_findings.get(p.product_id, [])
            for f in fs:
                by_category[f.category] = by_category.get(f.category, 0) + 1
                by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
                by_decision[f.decision] = by_decision.get(f.decision, 0) + 1
            product_rows.append({
                "product_id": p.product_id,
                "shop_id": p.shop_id,
                "internal_sku": p.internal_sku,
                "title": p.title,
                "status": product_status(fs),
                "finding_ids": [f.finding_id for f in fs],
                "recommended_action": product_action(fs),
                "case_id": None,
            })

        flagged = sum(1 for r in product_rows if r["status"] in ("flag", "block", "frozen"))
        blocked = sum(1 for r in product_rows if r["status"] == "block")
        awaiting = sum(1 for r in product_rows if r["status"] in ("flag", "frozen"))

        result = {
            "run_id": run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": scope or {},
            "summary": {
                "products_reviewed": len(products),
                "products_flagged": flagged,
                "products_blocked": blocked,
                "products_awaiting_review": awaiting,
                "findings_total": len(findings),
                "by_category": by_category,
                "by_severity": by_severity,
                "by_decision": by_decision,
                "rules_evaluated": len(self.rules),
                "parse_errors": len(errors),
            },
            "findings": [f.to_dict() for f in findings],
            "products": product_rows,
            "errors": errors,
            "report_path": None,
        }
        return result


def _has_compat_context(product: Product) -> bool:
    text = (product.all_text or "").lower()
    markers = ["compatível com", "compativel com", "compatible con",
               "para iphone", "para samsung", "para o modelo",
               "aplicável em", "aplicavel em"]
    return any(m in text for m in markers)


def _describe_duplicate(matches, same_shop: bool) -> str:
    parts = []
    for m in matches:
        if m.same_shop != same_shop:
            continue
        scope = "same store" if m.same_shop else "cross-store"
        sig = []
        if m.signals.get("same_sku"):
            sig.append("identical SKU")
        if m.signals.get("same_platform_pid"):
            sig.append("identical platform PID")
        if m.signals.get("title_trigram_dice"):
            sig.append(f"title similarity {m.signals['title_trigram_dice']:.2f}")
        parts.append(
            f"{scope}: {m.product_id} ↔ {m.other_product_id} "
            f"(score {m.score:.2f}, {', '.join(sig) or 'content similarity'})")
    return "; ".join(parts) or "duplicate signal"


def _describe_relist(matches) -> str:
    parts = []
    for m in matches:
        parts.append(
            f"matches historical case {m.case_id} "
            f"(basis: {', '.join(m.match_basis)}, similarity {m.similarity:.2f}"
            + (f", prior violation: {m.historical_violation}"
               if m.historical_violation else "") + ")")
    return "; ".join(parts) or "relist signal"


def _describe_cases(cases, enforced: bool) -> str:
    parts = []
    for c in cases:
        if enforced and c.status not in ENFORCED_CASE_STATUSES:
            continue
        if not enforced and c.status not in OPEN_CASE_STATUSES:
            continue
        parts.append(
            f"case {c.case_id} status={c.status} "
            f"violation={c.violation_type or 'n/a'}"
            + (f" frozen={c.frozen}" if c.frozen else ""))
    return "; ".join(parts) or ("enforced case" if enforced else "open case")


def write_result(result: dict, path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return path
