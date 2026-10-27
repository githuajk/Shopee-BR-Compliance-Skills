"""Domain models and the canonical in-memory representation.

Everything the agent processes is normalised into :class:`Product` and
:class:`Case` before any rule runs, regardless of the input format.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Any

# Project root: <root>/src/compliance_agent/models.py -> <root>
ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))

# Portuguese-aware letter class. `\b` in Python regex does NOT treat accented
# vowels as word characters in all cases; a pattern like `r'\bat[óo]xico\b'`
# can match inside `Óculos`. We never rely on `\b` next to accented letters.
PT_LETTERS = "a-zA-Zà-ÿÀ-ß"


def norm_text(s: str) -> str:
    """Lowercase + strip accents. Used for keyword matching (not for output)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def pt_word_boundary(word: str) -> str:
    """Build a regex-safe word-boundary around a Portuguese word.

    Usage: ``re.compile(r'(?<![a-zA-Zà-ÿÀ-ß])' + pt_word_boundary('atoxico'))``
    """
    return r"(?<![a-zA-Zà-ÿÀ-ß])" + word + r"(?![a-zA-Zà-ÿÀ-ß])"


def norm_sku(s: str) -> str:
    """Normalise a SKU for comparison: uppercase, alphanumerics only."""
    if not s:
        return ""
    return re.sub(r"[^A-Z0-9]", "", s.upper())


@dataclass
class Product:
    product_id: str
    internal_sku: str
    shop_id: str
    title: str = ""
    description: str = ""
    attributes: dict = field(default_factory=dict)
    category: str | None = None
    brand: str | None = None
    model: str | None = None
    price: float | None = None
    currency: str = "BRL"
    images: list = field(default_factory=list)
    variations: list = field(default_factory=list)
    platform_pid: str | None = None
    supplier_sku: str | None = None
    product_url: str | None = None
    shop_name: str | None = None
    source: dict = field(default_factory=dict)
    case_ids: list = field(default_factory=list)
    history: dict = field(default_factory=dict)
    notes: str = ""

    # ---- derived helpers -------------------------------------------------
    @property
    def all_text(self) -> str:
        """Every text field concatenated, for whole-listing keyword scans."""
        parts = [self.title or "", self.description or "", self.brand or "",
                 self.model or "", self.category or ""]
        for k, v in (self.attributes or {}).items():
            parts.append(f"{k} {v}")
        return "\n".join(p for p in parts if p)

    @property
    def image_text(self) -> str:
        """OCR text from product images."""
        return "\n".join(
            (img.get("ocr_text") or "") for img in (self.images or [])
        ).strip()

    def field_value(self, name: str):
        """Fetch a rule-targetable field by name."""
        if name == "title":
            return self.title
        if name == "description":
            return self.description
        if name == "attributes":
            return json.dumps(self.attributes or {}, ensure_ascii=False)
        if name == "category":
            return self.category
        if name == "brand":
            return self.brand
        if name == "model":
            return self.model
        if name == "price":
            return self.price
        if name == "image":
            return self.images or []
        if name == "image_text":
            return self.image_text
        if name == "variations":
            return self.variations or []
        if name == "seller_name":
            return self.shop_name
        if name == "supplier_sku":
            return self.supplier_sku
        if name == "shop_id":
            return self.shop_id
        if name == "product_url":
            return self.product_url
        if name == "history":
            # The history block carries case/evidence metadata. It is
            # flattened to text so rules can match on keys and values
            # (e.g. an authorisation inventory, a penalty-point count).
            return json.dumps(self.history or {}, ensure_ascii=False)
        if name == "any_text":
            return self.all_text
        return None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v not in (None, [], {}, "") or k in
                ("product_id", "internal_sku", "shop_id", "title")}


@dataclass
class Rule:
    rule_id: str
    title: str
    category: str
    description: str
    trigger_conditions: list
    severity: str
    decision: str
    evidence_required: list
    human_review_required: bool
    source_url: str
    last_verified: str
    status: str
    version: int
    source_tier: str = "unverified"
    source_excerpt: str = ""
    applies_to: list = field(default_factory=list)
    notes: str = ""
    tags: list = field(default_factory=list)
    references: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Rule":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    @property
    def is_enforceable(self) -> bool:
        """Only `active` rules from an authoritative source may block.

        A rule whose source is `unverified` (an internal hypothesis) or which
        is still `draft` may only raise a review flag — never a block.
        """
        return (
            self.status == "active"
            and self.source_tier in ("platform_official", "law")
        )


@dataclass
class Finding:
    finding_id: str
    product_id: str
    rule_id: str
    severity: str
    decision: str
    explanation: str
    rule_title: str = ""
    category: str = ""
    shop_id: str | None = None
    matched_field: str | None = None
    matched_excerpt: str | None = None
    source_url: str | None = None
    source_tier: str | None = None
    human_review_required: bool = False
    evidence_required: list = field(default_factory=list)
    confidence: str = "signal"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Case:
    case_id: str
    shop_id: str
    product_ids: list
    violation_type: str
    status: str = "open"
    frozen: bool = False
    evidence: list = field(default_factory=list)
    approvals: list = field(default_factory=list)
    case_type: str = "listing_review"
    rule_ids: list = field(default_factory=list)
    platform_notice: dict | None = None
    freeze_reason: str | None = None
    freeze_until: str | None = None
    evidence_gaps: list = field(default_factory=list)
    assessment: dict | None = None
    duplicate_of: str | None = None
    related_case_ids: list = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
