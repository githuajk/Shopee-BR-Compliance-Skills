"""重复刊登检测引擎（同店 + 跨店）。

三条**互相独立**的信号，每条单独报告，便于人工判断「真同款」与
「不同商品」：

===============  ========  ==========================================
信号             强度      含义
===============  ========  ==========================================
identity         **强**    同一规范化供应商 SKU / 同一平台 PID
content          中        标题 trigram Dice + token Jaccard + 正文 Jaccard
image            弱        图片指纹集合的 Jaccard
===============  ========  ==========================================

**候选生成**走倒排索引（按标题 token，按逆文档频率排序），不做 O(n²)
的全量比对。

**结论一律是「候选」。** 平台判定「重复」的阈值不公开 —— 相似度阈值
是**我方参数**，不是平台标准。因此：

* 同店（same shop）→ 平台政策更严（同一个商品无实质差异地刊登多次），
  命中 `SBR-DUP-001`；
* 跨店（cross store）→ 同一商品出现在不同店铺，命中 `SBR-DUP-002`，
  但跨店同款**本身不是违规** —— 同一供应商给多个店铺供货是正常业务。

> ⚠️ 图片指纹目前是**引用级**（image_id / url / local_path），不是感知
> 哈希。同一张图重新压缩后引用会变 —— 详见 `references/duplicate_signals.md`。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .normalize import (
    dice,
    image_fingerprints,
    jaccard,
    norm_sku,
    text_tokens,
    title_tokens,
    trigrams,
)

__all__ = [
    "DuplicateIndex",
    "DuplicateMatch",
    "DEFAULT_SIMILARITY_THRESHOLD",
    "STRONG_SIMILARITY_THRESHOLD",
    "NEAR_SIMILARITY_THRESHOLD",
]

#: 判定为「同一商品」的相似度阈值（我方参数，不是平台标准）。
DEFAULT_SIMILARITY_THRESHOLD = 0.62

#: 身份轴已成立时，内容相似度达到该值即可确认候选。
STRONG_SIMILARITY_THRESHOLD = 0.35

#: 「接近但需要人看」的边界带下沿。
NEAR_SIMILARITY_THRESHOLD = 0.45

#: 内容信号的权重。缺哪一项就按剩余权重归一 —— 缺数据不等于相似度为 0。
_CONTENT_WEIGHTS = {
    "title_dice": 0.40,
    "title_jaccard": 0.30,
    "description_jaccard": 0.20,
    "image_jaccard": 0.10,
}


@dataclass
class DuplicateMatch:
    """一对商品之间的重复判定结果。"""

    product_id: str
    other_product_id: str
    same_shop: bool
    score: float
    signals: dict = field(default_factory=dict)
    axes: list = field(default_factory=list)
    verdict: str = "candidate"

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "other_product_id": self.other_product_id,
            "same_shop": self.same_shop,
            "score": round(self.score, 4),
            "signals": self.signals,
            "axes": list(self.axes),
            "verdict": self.verdict,
        }

    def describe(self) -> str:
        """人类可读的证据描述（进 `matched_excerpt`）。"""
        shop = "same store" if self.same_shop else "cross store"
        axes = ", ".join(self.axes) if self.axes else "no shared axis"
        return (f"{shop} duplicate candidate with {self.other_product_id} "
                f"(similarity {self.score:.2f}; matched on {axes})")


class DuplicateIndex:
    """跨商品的重复候选索引。"""

    def __init__(self, threshold: float = DEFAULT_SIMILARITY_THRESHOLD):
        self.threshold = threshold
        self.products: list[dict] = []
        self._by_id: dict[str, dict] = {}
        self._tokens: dict[str, set[str]] = {}
        self._tris: dict[str, set[str]] = {}
        self._desc: dict[str, set[str]] = {}
        self._images: dict[str, set[str]] = {}
        self._sku: dict[str, list[str]] = {}
        self._pid: dict[str, list[str]] = {}
        self._inverted: dict[str, set[str]] = {}

    # ---- 索引 ----

    def add(self, product: dict) -> None:
        pid = product.get("product_id") or ""
        if not pid:
            return
        self.products.append(product)
        self._by_id[pid] = product
        tokens = set(title_tokens(product.get("title")))
        self._tokens[pid] = tokens
        self._tris[pid] = trigrams(" ".join(sorted(tokens)))
        self._desc[pid] = set(text_tokens(product.get("description")))
        self._images[pid] = image_fingerprints(product)
        for token in tokens:
            self._inverted.setdefault(token, set()).add(pid)
        sku = norm_sku(product.get("supplier_sku") or product.get("internal_sku"))
        if sku:
            self._sku.setdefault(sku, []).append(pid)
        pid_value = product.get("platform_pid")
        if pid_value:
            self._pid.setdefault(str(pid_value), []).append(pid)

    # ---- 候选生成 ----

    def _candidates(self, product: dict) -> set[str]:
        """用倒排索引取候选商品 id。"""
        pid = product.get("product_id") or ""
        candidates: set[str] = set()

        tokens = self._tokens.get(pid, set())
        if tokens:
            postings = []
            for token in tokens:
                bucket = self._inverted.get(token)
                if bucket:
                    postings.append((len(bucket), token, bucket))
            postings.sort()
            for _, _, bucket in postings[:12]:
                candidates |= bucket

        sku = norm_sku(product.get("supplier_sku") or product.get("internal_sku"))
        candidates |= set(self._sku.get(sku, []))
        pid_value = product.get("platform_pid")
        if pid_value:
            candidates |= set(self._pid.get(str(pid_value), []))

        candidates.discard(pid)
        return candidates

    # ---- 比较 ----

    def compare(self, left: dict, right: dict) -> DuplicateMatch:
        """比较两个商品。"""
        left_id = left.get("product_id") or ""
        right_id = right.get("product_id") or ""
        signals: dict[str, Any] = {}
        axes: list[str] = []
        score = 0.0
        verdict = "candidate"

        # --- 1. 身份轴 ---
        left_supplier = norm_sku(left.get("supplier_sku"))
        right_supplier = norm_sku(right.get("supplier_sku"))
        if left_supplier and right_supplier and left_supplier == right_supplier:
            signals["same_supplier_sku"] = True
            axes.append("supplier_sku")
            score = 1.0
            verdict = "likely_duplicate"
        left_internal = norm_sku(left.get("internal_sku"))
        right_internal = norm_sku(right.get("internal_sku"))
        if left_internal and right_internal and left_internal == right_internal:
            signals["same_internal_sku"] = True
            axes.append("internal_sku")
            score = 1.0
            verdict = "likely_duplicate"
        left_pid = left.get("platform_pid")
        right_pid = right.get("platform_pid")
        if left_pid and right_pid and str(left_pid) == str(right_pid):
            signals["same_platform_pid"] = True
            axes.append("platform_pid")
            score = 1.0
            verdict = "likely_duplicate"

        # --- 2. 内容轴 ---
        left_tokens = self._tokens.get(left_id, set())
        right_tokens = self._tokens.get(right_id, set())
        title_dice = dice(self._tris.get(left_id, set()),
                          self._tris.get(right_id, set()))
        title_jaccard = jaccard(left_tokens, right_tokens)
        signals["title_dice"] = round(title_dice, 4)
        signals["title_jaccard"] = round(title_jaccard, 4)

        left_desc = self._desc.get(left_id, set())
        right_desc = self._desc.get(right_id, set())
        if left_desc and right_desc:
            signals["description_jaccard"] = round(jaccard(left_desc, right_desc), 4)
        else:
            signals["description_jaccard"] = None

        left_images = self._images.get(left_id, set())
        right_images = self._images.get(right_id, set())
        if left_images and right_images:
            signals["image_jaccard"] = round(jaccard(left_images, right_images), 4)
        else:
            signals["image_jaccard"] = None

        weighted = 0.0
        weight_total = 0.0
        for name, weight in _CONTENT_WEIGHTS.items():
            value = signals.get(name)
            if value is None:
                continue
            weighted += value * weight
            weight_total += weight
        content_score = (weighted / weight_total) if weight_total else 0.0
        signals["content_score"] = round(content_score, 4)

        if content_score > score:
            score = content_score
        if content_score >= self.threshold and verdict == "candidate":
            verdict = "likely_duplicate"
        elif score >= NEAR_SIMILARITY_THRESHOLD and verdict == "candidate":
            verdict = "needs_review"

        if content_score >= self.threshold and "content_fingerprint" not in axes:
            axes.append("content_fingerprint")

        return DuplicateMatch(
            product_id=left_id,
            other_product_id=right_id,
            same_shop=(left.get("shop_id") == right.get("shop_id")),
            score=score,
            signals=signals,
            axes=axes,
            verdict=verdict,
        )

    # ---- 检索 ----

    def find_all(self, min_score: float | None = None,
                 cross_store: bool = True) -> list[DuplicateMatch]:
        """返回全部重复候选（每对只保留一个方向）。"""
        floor = self.threshold if min_score is None else min_score
        matches: list[DuplicateMatch] = []
        for product in self.products:
            for candidate_id in self._candidates(product):
                other = self._by_id.get(candidate_id)
                if other is None:
                    continue
                match = self.compare(product, other)
                if match.score < floor:
                    continue
                if not cross_store and match.same_shop:
                    continue
                matches.append(match)

        seen: set[tuple[str, ...]] = set()
        unique: list[DuplicateMatch] = []
        for match in sorted(matches, key=lambda m: (-m.score, m.product_id,
                                                    m.other_product_id)):
            key = tuple(sorted((match.product_id, match.other_product_id)))
            if key in seen:
                continue
            seen.add(key)
            unique.append(match)
        return unique
