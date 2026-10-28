"""Rule evaluation engine.

A rule is a list of trigger conditions. All conditions must hold for the rule
to fire (AND semantics) — the condition list is read as "the listing must
satisfy all of these to be in violation".

Enforcement discipline
----------------------
* A rule may only produce a blocking decision when it is `active` AND its
  source tier is authoritative (`platform_official` or `law`). Internal
  hypotheses (`internal_risk`) and drafts can only raise a review flag.
* An IP finding derived from a keyword or logo hit is a **signal**, never a
  finding of infringement. The engine marks `confidence` accordingly and
  always requires human review.
"""
from __future__ import annotations

import re
from typing import Iterable

from ..models import Finding, Product, Rule, norm_text
from .loader import AhoCorasick, compile_regex

# Decision strength, for resolving a product's final status.
DECISION_RANK = {
    "allow": 0,
    "info": 0,
    "flag_for_review": 1,
    "require_evidence": 2,
    "freeze_relist": 3,
    "block": 4,
    "escalate_legal": 5,
}

# Decisions a rule with a non-authoritative source is allowed to produce.
NON_AUTHORITATIVE_DECISIONS = {"allow", "flag_for_review"}


class Match:
    """The outcome of evaluating one condition against one field."""

    def __init__(self, ok: bool, excerpt: str | None = None, field: str | None = None):
        self.ok = ok
        self.excerpt = excerpt
        self.field = field


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return [str(value)]


def eval_condition(product: Product, cond: dict) -> Match:
    """Evaluate one trigger condition against a product.

    A condition on a field that the INPUT never carried cannot fire. The
    rule author may say "a listing with no images violates [606]", but a
    spreadsheet that simply has no image column is not evidence of that
    violation — it is missing data. The rule library therefore has to say
    which fields it needs, and the engine reports the gap instead of
    inventing a finding.
    """
    field_name = cond.get("field")
    op = cond.get("operator")
    value = cond.get("value")
    case_sensitive = bool(cond.get("case_sensitive", False))

    raw = product.field_value(field_name)
    applies_to = cond.get("applies_to") or ["all"]
    if applies_to != ["all"] and field_name not in applies_to and "any_text" not in applies_to:
        # condition scoped to other fields: evaluate on any_text instead
        raw = product.all_text

    # ---- missing-data guard -------------------------------------------
    # `requires_input` names the fields that must actually have been
    # supplied. If one of them is absent from the product record, the
    # condition is not evaluated and the gap is reported.
    required = cond.get("requires_input") or []
    if required:
        missing = [f for f in required if product.field_value(f) in (None, "", [], {})]
        if missing:
            return Match(False, f"missing input field(s): {', '.join(missing)}",
                         field_name)

    if op == "field_missing":
        present = raw not in (None, "", [], {})
        return Match(not present, None, field_name)

    if op == "has_field":
        present = raw not in (None, "", [], {})
        return Match(present, None, field_name)

    if op == "has_nonempty":
        """True when the named sub-key of the field holds at least one hit.

        Distinct from ``has_field``: an image list whose entries all have an
        empty ``detected_logos`` array must NOT satisfy this. Used by the
        logo rules so a product with analysed-but-clean images is not
        flagged.

        ``value`` names the sub-key to inspect (``detected_logos``,
        ``ocr_text``, ...). When the field's entries are plain strings
        instead of objects, the entries themselves are the hits.
        """
        key = str(value) if value is not None else None
        if raw in (None, "", [], {}):
            return Match(False, None, field_name)
        if isinstance(raw, list):
            if not raw:
                return Match(False, None, field_name)
            hits = []
            for item in raw:
                if isinstance(item, dict):
                    if key is None:
                        # no sub-key named: any populated sub-field counts
                        for k, v in item.items():
                            if k == "watermark":
                                if v:
                                    hits.append("watermark")
                            elif v:
                                hits.append(f"{k}:{v}")
                    else:
                        v = item.get(key)
                        if key == "watermark":
                            if v:
                                hits.append("watermark")
                        elif v:
                            hits.append(str(v))
                elif str(item).strip():
                    hits.append(str(item))
            return Match(bool(hits), "; ".join(hits[:5]), field_name)
        return Match(bool(str(raw).strip()), None, field_name)

    if op in ("image_count_lt", "image_count_gte"):
        n = len(raw or [])
        target = int(value)
        ok = n < target if op == "image_count_lt" else n >= target
        return Match(ok, f"{n} images", field_name)

    if op in ("gt", "gte", "lt", "lte"):
        try:
            num = float(raw)
            tgt = float(value)
        except (TypeError, ValueError):
            return Match(False, f"non-numeric {raw!r}", field_name)
        ok = {"gt": num > tgt, "gte": num >= tgt,
              "lt": num < tgt, "lte": num <= tgt}[op]
        return Match(ok, f"{num} vs {tgt}", field_name)

    text = "" if raw is None else (raw if isinstance(raw, str) else str(raw))

    if op == "equals":
        return Match(text == str(value), text[:200], field_name)
    if op == "not_equals":
        return Match(text != str(value), text[:200], field_name)

    if op == "regex":
        try:
            rx = compile_regex(str(value), case_sensitive)
        except re.error as e:
            return Match(False, f"invalid regex: {e}", field_name)
        m = rx.search(text)
        return Match(bool(m), (m.group(0) if m else None), field_name)

    if op == "contains_all":
        terms = _as_list(value)
        hay = text if case_sensitive else norm_text(text)
        miss = [t for t in terms if (t if case_sensitive else norm_text(t)) not in hay]
        if miss:
            return Match(False, f"missing {miss[:3]}", field_name)
        idx = min(
            (hay.find(t if case_sensitive else norm_text(t)) for t in terms),
            default=0)
        return Match(True, text[max(0, idx - 30): idx + 60], field_name)

    if op in ("contains_any", "not_contains_any"):
        terms = _as_list(value)
        hay = text if case_sensitive else norm_text(text)
        hit = None
        for t in terms:
            needle = t if case_sensitive else norm_text(t)
            if needle and needle in hay:
                hit = t
                break
        ok = bool(hit) if op == "contains_any" else (hit is None)
        if hit is None:
            return Match(ok, None, field_name)
        idx = hay.find(hit if case_sensitive else norm_text(hit))
        return Match(ok, text[max(0, idx - 40): idx + len(hit) + 40], field_name)

    return Match(False, f"unknown operator {op!r}", field_name)


def rule_fires(rule: Rule, product: Product) -> tuple[bool, str | None, str | None]:
    """Return (fired, matched_field, excerpt)."""
    matched_field = None
    excerpt = None
    for cond in rule.trigger_conditions:
        m = eval_condition(product, cond)
        if not m.ok:
            return False, None, None
        if matched_field is None:
            matched_field = m.field
            excerpt = m.excerpt
    return True, matched_field, excerpt


def evaluate_product(product: Product, rules: Iterable[Rule],
                     finding_seq=None) -> list[Finding]:
    """Run every rule against one product; return the findings."""
    findings: list[Finding] = []
    seq = finding_seq if finding_seq is not None else iter(range(1, 10 ** 6))
    for rule in rules:
        fired, field, excerpt = rule_fires(rule, product)
        if not fired:
            continue
        decision = rule.decision
        confidence = "confirmed"
        # Authority guard: only authoritative + active rules may block.
        if not rule.is_enforceable and decision not in NON_AUTHORITATIVE_DECISIONS:
            decision = "flag_for_review"
        # IP categories are never auto-confirmed from text matching.
        if rule.category in ("ip_trademark", "ip_copyright", "ip_design"):
            confidence = "signal"
            if decision in ("block", "escalate_legal"):
                decision = "escalate_legal"
            rule_human = True
        else:
            rule_human = rule.human_review_required
        findings.append(Finding(
            finding_id=f"F-{next(seq):05d}",
            product_id=product.product_id,
            rule_id=rule.rule_id,
            rule_title=rule.title,
            category=rule.category,
            severity=rule.severity,
            decision=decision,
            matched_field=field,
            matched_excerpt=excerpt,
            explanation=_explain(rule, product, field, excerpt),
            source_url=rule.source_url,
            source_tier=rule.source_tier,
            human_review_required=rule_human,
            evidence_required=list(rule.evidence_required),
            confidence=confidence,
        ))
    return findings


def _explain(rule: Rule, product: Product, field, excerpt) -> str:
    parts = [rule.description]
    if field:
        parts.append(f"Matched on `{field}`.")
    if excerpt:
        snippet = excerpt.strip().replace("\n", " ")
        if len(snippet) > 180:
            snippet = snippet[:180] + "…"
        parts.append(f"Excerpt: “{snippet}”.")
    if rule.source_tier == "internal_risk":
        parts.append("Source tier: internal risk suggestion — not a platform mandate; "
                     "requires human confirmation before any action.")
    if rule.source_tier == "unverified":
        parts.append("Source tier: unverified — hypothesis pending confirmation.")
    return " ".join(parts)


def product_status(findings: list[Finding]) -> str:
    """Derive the product's overall status from its findings.

    Precedence rationale: the most severe *reason* governs. A product that
    both re-lists a banned item AND carries an IP infringement is an IP
    escalation (it needs a legal owner), not merely a relist freeze. The
    freeze only surfaces as the product status when it is the only
    actionable finding — otherwise it is still visible in the finding list
    and in the recommended action.
    """
    if not findings:
        return "pass"
    decisions = {f.decision for f in findings}
    # Precedence, from most specific operational outcome to least:
    #
    # 1. A relist freeze means "this listing is the SAME product the platform
    #    already actioned" — that is a harder fact than anything the text
    #    scan found, and it is the thing the operator must act on first.
    # 2. A hard prohibition (block) means the item may not be sold at all.
    # 3. An IP escalation needs a legal owner.
    # 4. A review flag needs a human look.
    if "freeze_relist" in decisions:
        return "frozen"
    if "block" in decisions:
        return "block"
    if "escalate_legal" in decisions:
        return "block"
    if "require_evidence" in decisions or "flag_for_review" in decisions:
        return "flag"
    return "pass"


def product_action(findings: list[Finding]) -> str:
    """A short human-readable recommended action."""
    if not findings:
        return "no action"
    order = ["escalate_legal", "block", "freeze_relist", "require_evidence",
             "flag_for_review"]
    for d in order:
        hits = [f for f in findings if f.decision == d]
        if hits:
            rules = ", ".join(sorted({f.rule_id for f in hits}))
            label = {
                "escalate_legal": "Route to legal/IP review before any action",
                "block": "Do not publish — block and remediate",
                "freeze_relist": "Freeze re-listing until the violation is resolved",
                "require_evidence": "Request the listed evidence, then re-review",
                "flag_for_review": "Send to human review",
            }[d]
            extra = ""
            if d != "freeze_relist" and any(f.decision == "freeze_relist" for f in findings):
                extra = " + freeze re-listing"
            return f"{label} ({rules}){extra}"
    return "no action"


__all__ = [
    "AhoCorasick", "DECISION_RANK", "Finding", "Match", "Product", "Rule",
    "eval_condition", "evaluate_product", "product_action", "product_status",
    "rule_fires",
]
