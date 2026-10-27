"""违规重发检测引擎。

重发的陷阱在于**它看起来不一样**：标题改了、SKU 换了、图片换了。
只按 SKU 或 PID 比对的重发检测会漏掉最常见的那种形态。因此本引擎沿
**五条轴**独立匹配：

==================  ========  ==========================================
轴                  强度      数据来源
==================  ========  ==========================================
``platform_pid``    强        同一平台商品 ID
``supplier_sku``    强        同一上游货号
``internal_sku``    强        同一卖家 SKU
``product_url``     中        同一 listing 链接
``content_fingerprint``  中   标题/详情相似度 + 图片指纹
==================  ========  ==========================================

## 两种「关联」关系

匹配到案件后，必须分清两种关系 —— 它们触发的规则不同：

``subject``
    商品**自己**就是案件的对象（`case.product_ids` 里有它）。这是「这件
    listing 正挂在案件上」，不是重发。

``inherits``
    商品是**另一个**listing 的副本，而那个 listing 是案件的对象。新的
    listing 继承了旧案件的记录 —— 这才是重发。

## 案件三态决定处置

| 案件状态 | 三态 | 重发处置 |
|---|---|---|
| `open` / `under_review` / `awaiting_evidence` | `in_remediation` | **不冻结** —— 只提示复核 |
| `blocked` / `relist_frozen` / `escalated` / `rejected` | `actioned` | 冻结建议（`freeze_relist`，human_only） |
| `approved` / `closed`（未冻结） | `resolved` | 不产出结论 |

**状态优先于 `frozen` 标记。** `under_review` + `frozen: true` 表示卖家
正在整改 —— 此时冻结重发会挡住正要提交的整改，因此不算已处置。
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
    "RelistIndex",
    "RelistMatch",
    "ACTIONED_CASE_STATUSES",
    "IN_REVIEW_CASE_STATUSES",
    "CASE_IN_REMEDIATION",
    "CASE_ACTIONED",
    "CASE_RESOLVED",
    "RELATION_SUBJECT",
    "RELATION_INHERITS",
    "case_state",
    "is_case_actioned",
    "CONTENT_MATCH_THRESHOLD",
]

#: 平台已实际处置的案件状态 → 重发应被冻结。
ACTIONED_CASE_STATUSES = {"blocked", "relist_frozen", "escalated", "rejected"}

#: 案件仍在处理中 → 重发**不**冻结（否则会挡住卖家正在提交的整改）。
IN_REVIEW_CASE_STATUSES = {"open", "under_review", "awaiting_evidence"}

#: 案件已结（approved / closed）且未冻结 → 处置已结束，放行。
_CLOSED_CASE_STATUSES = {"approved", "closed"}

#: 案件三态。
CASE_IN_REMEDIATION = "in_remediation"
CASE_ACTIONED = "actioned"
CASE_RESOLVED = "resolved"

#: 关联关系。
RELATION_SUBJECT = "subject"
RELATION_INHERITS = "inherits"

#: 内容指纹轴的相似度阈值（我方参数）。
CONTENT_MATCH_THRESHOLD = 0.62


@dataclass
class RelistMatch:
    """一个商品与一个历史案件之间的重发关联。"""

    product_id: str
    case_id: str
    historical_product_id: str | None
    relation: str = RELATION_INHERITS
    match_basis: list = field(default_factory=list)
    similarity: float = 0.0
    verdict: str = "relist_candidate"
    historical_violation: str | None = None
    case_status: str | None = None
    case_frozen: bool = False
    actioned: bool = False
    case_state: str = CASE_IN_REMEDIATION

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "case_id": self.case_id,
            "historical_product_id": self.historical_product_id,
            "relation": self.relation,
            "match_basis": list(self.match_basis),
            "similarity": round(self.similarity, 4),
            "verdict": self.verdict,
            "historical_violation": self.historical_violation,
            "case_status": self.case_status,
            "case_frozen": self.case_frozen,
            "actioned": self.actioned,
            "case_state": self.case_state,
        }

    def describe(self) -> str:
        basis = ", ".join(self.match_basis) if self.match_basis else "no shared axis"
        state = {
            CASE_ACTIONED: "already actioned by the platform",
            CASE_IN_REMEDIATION: "still under remediation",
            CASE_RESOLVED: "resolved and released",
        }.get(self.case_state, self.case_state)
        subject = ("the listing is the subject of the case"
                   if self.relation == RELATION_SUBJECT
                   else f"it copies listing {self.historical_product_id or 'unknown'}")
        return (f"linked to case {self.case_id}: {subject}; "
                f"matched on {basis}; the case is {state}: {self.case_status}")


def case_state(case: dict) -> str:
    """案件三态判定。

    * ``in_remediation`` —— 卖家正在整改（open / under_review /
      awaiting_evidence）。重发**不**冻结：冻结会挡住正要提交的整改。
    * ``actioned`` —— 平台已实际处置（blocked / relist_frozen / escalated /
      rejected），或案件显式带 ``frozen: true``。重发应被冻结。
    * ``resolved`` —— 已结（approved / closed）且未冻结。处置已结束，
      重发不构成违规。

    **状态优先于 `frozen` 标记。** ``under_review`` + ``frozen: true`` 表示
    卖家正在整改 —— 此时冻结重发会挡住正要提交的整改，因此不算已处置。
    """
    status = case.get("status")
    if status in IN_REVIEW_CASE_STATUSES:
        return CASE_IN_REMEDIATION
    if status in ACTIONED_CASE_STATUSES:
        return CASE_ACTIONED
    if status in _CLOSED_CASE_STATUSES:
        return CASE_ACTIONED if case.get("frozen") else CASE_RESOLVED
    return CASE_ACTIONED if case.get("frozen") else CASE_IN_REMEDIATION


def is_case_actioned(case: dict) -> bool:
    """案件是否已被平台实际处置（= 三态里的 ``actioned``）。"""
    return case_state(case) == CASE_ACTIONED


def _case_violation(case: dict) -> str | None:
    if case.get("violation_type"):
        return case["violation_type"]
    rule_ids = case.get("rule_ids") or []
    return rule_ids[0] if rule_ids else None


class RelistIndex:
    """历史案件 + 商品的重发索引。"""

    def __init__(self, content_threshold: float = CONTENT_MATCH_THRESHOLD):
        self.content_threshold = content_threshold
        self.products: dict[str, dict] = {}
        self.cases: list[dict] = []
        self._tokens: dict[str, set[str]] = {}
        self._tris: dict[str, set[str]] = {}
        self._desc: dict[str, set[str]] = {}
        self._images: dict[str, set[str]] = {}
        self._by_pid: dict[str, list[str]] = {}
        self._by_internal_sku: dict[str, list[str]] = {}
        self._by_supplier_sku: dict[str, list[str]] = {}
        self._by_url: dict[str, list[str]] = {}
        self._inverted: dict[str, set[str]] = {}

    # ---- 索引 ----

    def add_product(self, product: dict) -> None:
        pid = product.get("product_id") or ""
        if not pid:
            return
        self.products[pid] = product
        tokens = set(title_tokens(product.get("title")))
        self._tokens[pid] = tokens
        self._tris[pid] = trigrams(" ".join(sorted(tokens)))
        self._desc[pid] = set(text_tokens(product.get("description")))
        self._images[pid] = image_fingerprints(product)
        for token in tokens:
            self._inverted.setdefault(token, set()).add(pid)
        platform_pid = product.get("platform_pid")
        if platform_pid:
            self._by_pid.setdefault(str(platform_pid), []).append(pid)
        internal = norm_sku(product.get("internal_sku"))
        if internal:
            self._by_internal_sku.setdefault(internal, []).append(pid)
        supplier = norm_sku(product.get("supplier_sku"))
        if supplier:
            self._by_supplier_sku.setdefault(supplier, []).append(pid)
        url = (product.get("product_url") or "").strip()
        if url:
            self._by_url.setdefault(url, []).append(pid)

    def add_case(self, case: dict) -> None:
        self.cases.append(case)

    # ---- 候选生成 ----

    def _candidates(self, product: dict) -> set[str]:
        pid = product.get("product_id") or ""
        candidates: set[str] = set()
        platform_pid = product.get("platform_pid")
        if platform_pid:
            candidates |= set(self._by_pid.get(str(platform_pid), []))
        internal = norm_sku(product.get("internal_sku"))
        if internal:
            candidates |= set(self._by_internal_sku.get(internal, []))
        supplier = norm_sku(product.get("supplier_sku"))
        if supplier:
            candidates |= set(self._by_supplier_sku.get(supplier, []))
        url = (product.get("product_url") or "").strip()
        if url:
            candidates |= set(self._by_url.get(url, []))
        tokens = self._tokens.get(pid, set())
        if tokens:
            postings = sorted(
                (len(self._inverted.get(token, ())), token)
                for token in tokens if self._inverted.get(token)
            )
            for _, token in postings[:10]:
                candidates |= self._inverted[token]
        candidates.discard(pid)
        return candidates

    # ---- 轴匹配 ----

    def _match_basis(self, product: dict, historical: dict) -> tuple[list[str], float]:
        basis: list[str] = []
        score = 0.0

        product_pid = product.get("platform_pid")
        historical_pid = historical.get("platform_pid")
        if product_pid and historical_pid and str(product_pid) == str(historical_pid):
            basis.append("platform_pid")
            score = 1.0

        internal = norm_sku(product.get("internal_sku"))
        historical_internal = norm_sku(historical.get("internal_sku"))
        if internal and historical_internal and internal == historical_internal:
            basis.append("internal_sku")
            score = max(score, 0.95)

        supplier = norm_sku(product.get("supplier_sku"))
        historical_supplier = norm_sku(historical.get("supplier_sku"))
        if supplier and historical_supplier and supplier == historical_supplier:
            basis.append("supplier_sku")
            score = max(score, 0.95)

        url = (product.get("product_url") or "").strip()
        historical_url = (historical.get("product_url") or "").strip()
        if url and historical_url and url == historical_url:
            basis.append("product_url")
            score = max(score, 0.90)

        content = self._content_score(product, historical)
        if content >= self.content_threshold:
            basis.append("content_fingerprint")
            score = max(score, content)
        return basis, score

    def _content_score(self, product: dict, historical: dict) -> float:
        left_id = product.get("product_id") or ""
        right_id = historical.get("product_id") or ""
        title_dice = dice(self._tris.get(left_id, set()), self._tris.get(right_id, set()))
        title_jaccard = jaccard(self._tokens.get(left_id, set()),
                                self._tokens.get(right_id, set()))
        left_desc = self._desc.get(left_id, set())
        right_desc = self._desc.get(right_id, set())
        desc_jaccard = jaccard(left_desc, right_desc) if (left_desc and right_desc) else None
        left_images = self._images.get(left_id, set())
        right_images = self._images.get(right_id, set())
        image_jaccard = (jaccard(left_images, right_images)
                         if (left_images and right_images) else None)

        weighted = 0.40 * title_dice + 0.30 * title_jaccard
        total = 0.70
        if desc_jaccard is not None:
            weighted += 0.20 * desc_jaccard
            total += 0.20
        if image_jaccard is not None:
            weighted += 0.10 * image_jaccard
            total += 0.10
        return weighted / total if total else 0.0

    def _match_case_ids(self, product: dict, case: dict) -> tuple[list[str], float]:
        """没有历史商品记录时，用案件自己引用的 `product_ids` 做身份匹配。

        这是原型实现踩过的坑：早期逻辑要求案件必须有关联的商品历史记录，
        于是只引用 `product_ids` 的案件被整个漏掉。
        """
        basis: list[str] = []
        score = 0.0
        ids = set(case.get("product_ids") or [])
        if not ids:
            return basis, score
        candidates = {product.get("product_id") or ""}
        for key in ("platform_pid", "internal_sku", "supplier_sku"):
            value = product.get(key)
            if value:
                candidates.add(str(value))
                candidates.add(norm_sku(str(value)))
        overlap = ids & candidates
        if overlap:
            basis.append("case_product_id")
            score = 1.0
        return basis, score

    # ---- 检索 ----

    def check(self, product: dict) -> list[RelistMatch]:
        """返回该商品与历史案件之间的全部关联。"""
        matches: list[RelistMatch] = []
        pid = product.get("product_id") or ""

        # (1) 商品自己是案件的对象 → subject
        for case in self.cases:
            if pid and pid in set(case.get("product_ids") or []):
                matches.append(self._build_match(
                    product, case, pid, ["case_product_id"], 1.0,
                    relation=RELATION_SUBJECT))

        # (2) 商品是某个 listing 的副本，而那个 listing 是案件的对象
        for historical_id in self._candidates(product):
            historical = self.products.get(historical_id)
            if historical is None:
                continue
            basis, score = self._match_basis(product, historical)
            if not basis:
                continue
            for case in self.cases:
                case_product_ids = set(case.get("product_ids") or [])
                if historical_id in case_product_ids:
                    matches.append(self._build_match(
                        product, case, historical_id, basis, score,
                        relation=RELATION_INHERITS))
                    break

        # (3) 案件只引用了 id、没有对应的商品记录 → 用 id 做身份匹配
        known = {(m.case_id, m.relation) for m in matches}
        for case in self.cases:
            if (case.get("case_id"), RELATION_INHERITS) in known:
                continue
            # 商品自己就是案件的对象 → 那是 subject，不是继承。
            if pid and pid in set(case.get("product_ids") or []):
                continue
            basis, score = self._match_case_ids(product, case)
            if not basis:
                continue
            matches.append(self._build_match(
                product, case, None, basis, score, relation=RELATION_INHERITS))

        seen: set[tuple[str, str]] = set()
        output: list[RelistMatch] = []
        for match in sorted(matches,
                            key=lambda m: (-m.similarity, m.case_id, m.relation)):
            key = (match.case_id, match.relation)
            if key in seen:
                continue
            seen.add(key)
            output.append(match)
        return output

    def _build_match(self, product: dict, case: dict, historical_id: str | None,
                     basis: list[str], score: float,
                     relation: str = RELATION_INHERITS) -> RelistMatch:
        state = case_state(case)
        actioned = state == CASE_ACTIONED
        if relation == RELATION_SUBJECT:
            verdict = ("relist_subject_actioned" if state == CASE_ACTIONED
                       else "relist_subject_open")
        elif state == CASE_ACTIONED and score >= 0.95:
            verdict = "relist_confirmed_identity"
        elif state == CASE_ACTIONED:
            verdict = "relist_actioned_case"
        elif state == CASE_RESOLVED:
            verdict = "relist_resolved_case"
        else:
            verdict = "relist_open_case"
        return RelistMatch(
            product_id=product.get("product_id") or "",
            case_id=case.get("case_id") or "",
            historical_product_id=historical_id,
            relation=relation,
            match_basis=list(basis),
            similarity=score,
            verdict=verdict,
            historical_violation=_case_violation(case),
            case_status=case.get("status"),
            case_frozen=bool(case.get("frozen")),
            actioned=actioned,
            case_state=state,
        )

    # ---- 便捷入口 ----

    def actioned_cases(self) -> list[dict]:
        return [case for case in self.cases if is_case_actioned(case)]

    def remediation_cases(self) -> list[dict]:
        return [case for case in self.cases
                if case_state(case) == CASE_IN_REMEDIATION]
