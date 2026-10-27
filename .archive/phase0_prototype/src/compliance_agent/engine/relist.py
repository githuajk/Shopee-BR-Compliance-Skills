"""Relist detection: does this candidate listing reuse a product that has
already been removed, banned, or suspended?

The requirement is "违规商品重发" — a seller re-publishing a product that was
already actioned. The trap is that the relist looks *different*: the title is
rewritten, the SKU is changed, the images are swapped. A rule that only
compares SKUs or PIDs misses those. This module therefore matches on several
independent axes:

1. **Platform PID** — the same Shopee item id re-published. Strongest signal.
2. **Supplier SKU** — the same upstream item code.
3. **Internal SKU** — the same seller-side SKU.
4. **Product URL history** — the same listing URL.
5. **Content fingerprint** — normalised title/description similarity plus the
   image hash set, so a renamed copy of the same product is caught.

A match never means "the relist is guilty". It means the new listing inherits
the historical case: it is frozen pending human review.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models import Case, Product, norm_sku, norm_text
from .duplicates import _normalize_title, _trigrams, dice, jaccard

# Statuses that mean "this product was actioned by the platform".
ACTIONED_CASE_STATUSES = {"blocked", "relist_frozen", "escalated", "rejected"}
ACTIONED_DECISIONS = {"block", "freeze_relist", "escalate_legal"}

# Statuses where a relist must NOT be auto-frozen: the case is still being
# worked. A suspended product that the operator has corrected and sent back
# for review is exactly this state — freezing it would wrongly block the
# remediation the operator is asking the platform to review.
IN_REVIEW_CASE_STATUSES = {"under_review", "awaiting_evidence", "open"}


@dataclass
class RelistMatch:
    product_id: str
    case_id: str
    historical_product_id: str | None
    match_basis: list = field(default_factory=list)
    similarity: float = 0.0
    verdict: str = "relist_candidate"
    historical_violation: str | None = None

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "case_id": self.case_id,
            "historical_product_id": self.historical_product_id,
            "match_basis": self.match_basis,
            "similarity": round(self.similarity, 4),
            "verdict": self.verdict,
            "historical_violation": self.historical_violation,
        }


def _image_hashes(product: Product) -> set:
    out = set()
    for img in product.images or []:
        for key in ("phash", "sha256", "url", "image_id"):
            v = img.get(key)
            if v:
                out.add(f"{key}:{v}")
    return out


class RelistIndex:
    """Index historical cases/products so a relist can be detected."""

    def __init__(self, title_threshold: float = 0.62):
        self.title_threshold = title_threshold
        self.products: dict[str, Product] = {}
        self.cases: list[Case] = []
        self._by_pid: dict[str, list[str]] = {}
        self._by_sku: dict[str, list[str]] = {}
        self._by_supplier: dict[str, list[str]] = {}
        self._by_url: dict[str, list[str]] = {}
        self._tokens: dict[str, set] = {}
        self._tris: dict[str, set] = {}
        self._images: dict[str, set] = {}
        self._inverted: dict[str, set] = {}

    # ---- indexing --------------------------------------------------------
    def add_product(self, product: Product):
        pid = product.product_id
        self.products[pid] = product
        toks = set(_normalize_title(product.title))
        self._tokens[pid] = toks
        self._tris[pid] = _trigrams(" ".join(sorted(toks)))
        for t in toks:
            self._inverted.setdefault(t, set()).add(pid)
        if product.platform_pid:
            self._by_pid.setdefault(product.platform_pid, []).append(pid)
        sku = norm_sku(product.internal_sku)
        if sku:
            self._by_sku.setdefault(sku, []).append(pid)
        sup = norm_sku(product.supplier_sku or "")
        if sup:
            self._by_supplier.setdefault(sup, []).append(pid)
        if product.product_url:
            self._by_url.setdefault(product.product_url.strip(), []).append(pid)
        self._images[pid] = _image_hashes(product)

    def add_case(self, case: Case):
        self.cases.append(case)

    # ---- matching --------------------------------------------------------
    def _is_actioned(self, case: Case) -> bool:
        """True when the case represents an enforced platform action.

        A case that is still `under_review` / `awaiting_evidence` / `open`
        is NOT enforced, even if it carries `frozen: true` — the operator is
        actively remediating it. Freezing a relist in that state would block
        the very correction under review.
        """
        if case.status in IN_REVIEW_CASE_STATUSES:
            return False
        if case.status in ACTIONED_CASE_STATUSES:
            return True
        return bool(case.frozen)

    def _case_violation(self, case: Case) -> str | None:
        return case.violation_type or (case.rule_ids[0] if case.rule_ids else None)

    def candidates(self, product: Product) -> set[str]:
        cands: set[str] = set()
        if product.platform_pid:
            cands |= set(self._by_pid.get(product.platform_pid, []))
        sku = norm_sku(product.internal_sku)
        cands |= set(self._by_sku.get(sku, []))
        sup = norm_sku(product.supplier_sku or "")
        cands |= set(self._by_supplier.get(sup, []))
        if product.product_url:
            cands |= set(self._by_url.get(product.product_url.strip(), []))
        toks = self._tokens.get(product.product_id, set())
        if toks:
            postings = sorted(
                (len(self._inverted.get(t, ())), t) for t in toks if self._inverted.get(t)
            )
            for _, t in postings[:10]:
                cands |= self._inverted[t]
        cands.discard(product.product_id)
        return cands

    def check(self, product: Product) -> list[RelistMatch]:
        """Return relist candidates for one product.

        A case can reference products that are not present in the history
        product set (the operator may only have kept the case record). In
        that case we match the candidate's identity keys against the case's
        own product_ids, so a frozen case still freezes its relist.
        """
        matches: list[RelistMatch] = []
        actioned_cases = [c for c in self.cases if self._is_actioned(c)]

        # 1) match against known historical products
        for hist_pid in self.candidates(product):
            hist = self.products.get(hist_pid)
            if hist is None:
                continue
            basis, score = self._match_basis(product, hist)
            if not basis:
                continue
            for case in actioned_cases:
                if product.product_id in (case.product_ids or []) or \
                        hist_pid in (case.product_ids or []):
                    matches.append(RelistMatch(
                        product_id=product.product_id,
                        case_id=case.case_id,
                        historical_product_id=hist_pid,
                        match_basis=basis,
                        similarity=score,
                        verdict=("relist_confirmed_identity"
                                 if score >= 0.95 else "relist_candidate"),
                        historical_violation=self._case_violation(case),
                    ))
                    break

        # 2) match against a frozen case whose product record is missing
        known = {m.case_id for m in matches}
        for case in actioned_cases:
            if case.case_id in known:
                continue
            basis, score = self._match_case_ids(product, case)
            if not basis:
                continue
            matches.append(RelistMatch(
                product_id=product.product_id,
                case_id=case.case_id,
                historical_product_id=None,
                match_basis=basis,
                similarity=score,
                verdict=("relist_confirmed_identity"
                         if score >= 0.95 else "relist_candidate"),
                historical_violation=self._case_violation(case),
            ))

        seen = set()
        out = []
        for m in sorted(matches, key=lambda x: -x.similarity):
            key = (m.case_id, m.historical_product_id)
            if key in seen:
                continue
            seen.add(key)
            out.append(m)
        return out

    def _match_basis(self, product: Product, hist: Product) -> tuple[list, float]:
        basis: list[str] = []
        score = 0.0
        if (product.platform_pid and product.platform_pid == hist.platform_pid):
            basis.append("platform_pid")
            score = 1.0
        if (norm_sku(product.internal_sku) and
                norm_sku(product.internal_sku) == norm_sku(hist.internal_sku)):
            basis.append("internal_sku")
            score = max(score, 0.95)
        if (norm_sku(product.supplier_sku or "") and
                norm_sku(product.supplier_sku or "") == norm_sku(hist.supplier_sku or "")):
            basis.append("supplier_sku")
            score = max(score, 0.95)
        if (product.product_url and product.product_url.strip() ==
                (hist.product_url or "").strip()):
            basis.append("product_url")
            score = max(score, 0.90)

        jac = jaccard(self._tokens.get(product.product_id, set()),
                      self._tokens.get(hist.product_id, set()))
        dic = dice(self._tris.get(product.product_id, set()),
                   self._tris.get(hist.product_id, set()))
        img_overlap = jaccard(self._images.get(product.product_id, set()),
                              self._images.get(hist.product_id, set()))
        content = 0.5 * dic + 0.3 * jac + 0.2 * img_overlap
        if content >= self.title_threshold:
            basis.append("content_fingerprint")
            if content > score:
                score = content
        return basis, score

    def _match_case_ids(self, product: Product, case: Case) -> tuple[list, float]:
        """Match a candidate against a case's product_ids with no product record.

        We can only compare identity keys that live on the case itself. The
        case stores product ids; the candidate's own ``platform_pid`` /
        ``supplier_sku`` are compared against the id strings, which is a
        conservative identity test.
        """
        basis: list[str] = []
        score = 0.0
        ids = set(case.product_ids or [])
        if not ids:
            return basis, score
        cand_ids = {product.product_id}
        if product.platform_pid:
            cand_ids.add(product.platform_pid)
        if product.internal_sku:
            cand_ids.add(product.internal_sku)
            cand_ids.add(norm_sku(product.internal_sku))
        if product.supplier_sku:
            cand_ids.add(product.supplier_sku)
            cand_ids.add(norm_sku(product.supplier_sku))
        overlap = ids & cand_ids
        if overlap:
            basis.append("case_product_id")
            score = 1.0
        return basis, score


def load_history(cases: list[Case], products: list[Product]) -> RelistIndex:
    idx = RelistIndex()
    for p in products:
        idx.add_product(p)
    for c in cases:
        idx.add_case(c)
    return idx
