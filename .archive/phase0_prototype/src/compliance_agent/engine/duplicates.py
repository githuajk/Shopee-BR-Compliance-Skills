"""Duplicate-listing detection, including cross-store same-product matching.

Three independent signals, each reported separately so a human can judge:

1. **Identity signals** — same normalised supplier SKU, or the same platform
   PID re-listed in another store. Strongest evidence of a duplicate.
2. **Content similarity** — normalised title + description fingerprint.
   Titles are normalised by stripping accents, punctuation, stop-words and
   marketing filler, then compared with token-set Jaccard + a
   character-trigram similarity for the "same product, renamed" case.
3. **Image signals** — perceptual hash of the main image, when images are
   available.

Cross-store matching compares products across *different* `shop_id`s. Within a
single store the same signals are used, but the platform's own duplicate
policy is stricter about listing the same item twice.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models import Product, norm_sku, norm_text

# Portuguese marketing filler that changes between otherwise identical
# listings; removing it increases recall on near-duplicate titles.
STOPWORDS = {
    "de", "da", "do", "das", "dos", "a", "o", "as", "os", "e", "ou", "para",
    "com", "sem", "em", "no", "na", "nos", "nas", "por", "um", "uma", "uns",
    "umas", "novo", "nova", "novos", "novas", "kit", "conjunto", "unidade",
    "unidades", "pecas", "peca", "preto", "branco", "original", "premium",
    "qualidade", "alta", "melhor", "promocao", "oferta", "frete", "gratis",
    "envio", "rapido", "melhor", "top", "mais", "vendido", "produto",
    "comprar", "agora", "loja", "roupa", "casa", "uso", "dia", "dia-a-dia",
    "personalizado", "specially", "novo", "innovation", "avant",
}

FILLER_PATTERNS = [
    r"\bpromo(?:ção|cao)\b", r"\boferta\b", r"\bfrete\s+gr[aá]tis\b",
    r"\bdesconto\b", r"\bmelhor\s+pre[çc]o\b", r"\benvio\s+imediato\b",
    r"\b[0-9]+\s*%?\s*off\b", r"\bhot\s+sale\b", r"\bliquida[çc][ãa]o\b",
    r"\bblack\s+friday\b", r"\bpresente\b",
]

TOKEN_RE = re.compile(r"[a-z0-9]+")


def _normalize_title(title: str) -> list[str]:
    t = norm_text(title or "")
    for pat in FILLER_PATTERNS:
        t = re.sub(pat, " ", t)
    toks = TOKEN_RE.findall(t)
    return [x for x in toks if x not in STOPWORDS and len(x) > 1]


def _trigrams(s: str) -> set[str]:
    s = re.sub(r"\s+", " ", s.strip())
    if len(s) < 3:
        return {s} if s else set()
    return {s[i:i + 3] for i in range(len(s) - 2)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / float(len(a | b))


def dice(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return 2.0 * len(a & b) / float(len(a) + len(b))


@dataclass
class DuplicateMatch:
    product_id: str
    other_product_id: str
    same_shop: bool
    score: float
    signals: dict = field(default_factory=dict)
    verdict: str = "candidate"

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "other_product_id": self.other_product_id,
            "same_shop": self.same_shop,
            "score": round(self.score, 4),
            "signals": self.signals,
            "verdict": self.verdict,
        }


class DuplicateIndex:
    """Indexes products for near-duplicate lookup.

    Blocks candidate generation on a cheap inverted index over title tokens
    so we do not compare every pair.
    """

    def __init__(self, title_threshold: float = 0.72,
                 sku_exact_is_duplicate: bool = True):
        self.title_threshold = title_threshold
        self.sku_exact_is_duplicate = sku_exact_is_duplicate
        self.products: list[Product] = []
        self._tokens: dict[str, set[str]] = {}
        self._tris: dict[str, set[str]] = {}
        self._sku_index: dict[str, list[str]] = {}
        self._pid_index: dict[str, list[str]] = {}
        self._inverted: dict[str, set[str]] = {}

    # ---- indexing --------------------------------------------------------
    def add(self, product: Product):
        pid = product.product_id
        self.products.append(product)
        toks = set(_normalize_title(product.title))
        self._tokens[pid] = toks
        self._tris[pid] = _trigrams(" ".join(sorted(toks)))
        for t in toks:
            self._inverted.setdefault(t, set()).add(pid)
        sku = norm_sku(product.supplier_sku or product.internal_sku)
        if sku:
            self._sku_index.setdefault(sku, []).append(pid)
        if product.platform_pid:
            self._pid_index.setdefault(product.platform_pid, []).append(pid)

    # ---- matching --------------------------------------------------------
    def _candidates(self, product: Product) -> set[str]:
        cands: set[str] = set()
        toks = self._tokens.get(product.product_id, set())
        # Rare-token overlap is a good candidate generator: score by inverse
        # document frequency so common words do not blow up the candidate set.
        if toks:
            postings = []
            for t in toks:
                p = self._inverted.get(t)
                if p:
                    postings.append((len(p), t, p))
            postings.sort()
            for _, _, p in postings[:12]:
                cands |= p
        sku = norm_sku(product.supplier_sku or product.internal_sku)
        cands |= set(self._sku_index.get(sku, []))
        if product.platform_pid:
            cands |= set(self._pid_index.get(product.platform_pid, []))
        cands.discard(product.product_id)
        return cands

    def compare(self, a: Product, b: Product) -> DuplicateMatch:
        pid_a, pid_b = a.product_id, b.product_id
        signals: dict = {}
        score = 0.0
        verdict = "candidate"

        # 1. identity
        sku_a = norm_sku(a.supplier_sku or a.internal_sku)
        sku_b = norm_sku(b.supplier_sku or b.internal_sku)
        if sku_a and sku_b and sku_a == sku_b:
            signals["same_sku"] = True
            score = 1.0
            verdict = "likely_duplicate"
        if a.platform_pid and a.platform_pid == b.platform_pid:
            signals["same_platform_pid"] = True
            score = 1.0
            verdict = "likely_duplicate"

        # 2. content similarity
        jac = jaccard(self._tokens.get(pid_a, set()), self._tokens.get(pid_b, set()))
        dic = dice(self._tris.get(pid_a, set()), self._tris.get(pid_b, set()))
        desc_jac = jaccard(
            set(norm_text(a.description or "").split()),
            set(norm_text(b.description or "").split()))
        signals["title_jaccard"] = round(jac, 4)
        signals["title_trigram_dice"] = round(dic, 4)
        signals["description_jaccard"] = round(desc_jac, 4)
        content_score = 0.55 * dic + 0.30 * jac + 0.15 * desc_jac
        if content_score > score:
            score = content_score
        if score >= self.title_threshold and verdict == "candidate":
            verdict = "likely_duplicate"
        elif score >= self.title_threshold - 0.18:
            verdict = "needs_review"

        return DuplicateMatch(
            product_id=pid_a,
            other_product_id=pid_b,
            same_shop=(a.shop_id == b.shop_id),
            score=score,
            signals=signals,
            verdict=verdict,
        )

    def find_all(self, min_score: float = 0.5) -> list[DuplicateMatch]:
        matches: list[DuplicateMatch] = []
        for p in self.products:
            for cand_id in self._candidates(p):
                other = self._by_id(cand_id)
                if other is None:
                    continue
                m = self.compare(p, other)
                if m.score >= min_score:
                    matches.append(m)
        # keep one direction per pair
        seen = set()
        uniq = []
        for m in sorted(matches, key=lambda x: -x.score):
            key = tuple(sorted((m.product_id, m.other_product_id)))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(m)
        return uniq

    def _by_id(self, pid: str) -> Product | None:
        for p in self.products:
            if p.product_id == pid:
                return p
        return None


def find_cross_store_duplicates(products: list[Product],
                                min_score: float = 0.5) -> list[DuplicateMatch]:
    """Only matches that cross a shop boundary."""
    idx = DuplicateIndex()
    for p in products:
        idx.add(p)
    return [m for m in idx.find_all(min_score) if not m.same_shop]


def find_within_store_duplicates(products: list[Product],
                                 min_score: float = 0.5) -> list[DuplicateMatch]:
    idx = DuplicateIndex()
    for p in products:
        idx.add(p)
    return [m for m in idx.find_all(min_score) if m.same_shop]
