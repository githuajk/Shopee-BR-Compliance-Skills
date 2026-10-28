"""`contracts/risk_action_matrix.json` 的查表适配器。

**动作不是本模块自己决定的。** 规则命中之后，动作由「风险等级 × 动作」
矩阵查表得出；矩阵不允许的组合一律降级。再叠加硬约束 **H2**：

    block / freeze_relist / escalate_legal
    只能来自 source.tier ∈ {platform_official, law} 的 active 规则。

`technical` / `internal_risk` / `unverified` / `ai_inference` 四档最高只能
到 `flag_for_review`。

> 矩阵文件读不到时**不猜** —— 回落到内置的保守映射（只允许 `allow` /
> `flag_for_review`），并让调用方把这件事报成 error。
"""

from __future__ import annotations

import json
import os
from typing import Any

__all__ = [
    "RiskMatrix",
    "MAX_ACTION_BY_TIER",
    "BLOCKING_ACTIONS",
    "MATRIX_PATH",
]

MATRIX_PATH = os.path.join("contracts", "risk_action_matrix.json")

#: 来源层级 → 允许的最高动作（硬约束 H2）。与冻结契约一致。
MAX_ACTION_BY_TIER = {
    "platform_official": "block",
    "law": "block",
    "technical": "flag_for_review",
    "internal_risk": "flag_for_review",
    "unverified": "flag_for_review",
    "ai_inference": "flag_for_review",
}

#: 阻断类动作 —— 只能由权威来源的 active 规则产生。
BLOCKING_ACTIONS = {"block", "freeze_relist", "escalate_legal"}

#: 来源层级 → 允许的动作**类别**。
#:
#: ``blocking`` 类包含 block / freeze_relist / escalate_legal 三者 ——
#: tier 的上限说的是「能不能阻断」，不是「阻断到哪一档」。用严重度排序
#: 比较 tier 上限会把 ``platform_official`` 的 ``freeze_relist`` 误降级成
#: ``block``。
_TIER_CLASS = {
    "platform_official": "blocking",
    "law": "blocking",
    "technical": "review",
    "internal_risk": "review",
    "unverified": "review",
    "ai_inference": "review",
}

#: 动作严重度排序（用于取「最细粒度/最重」的那一条）。
_ACTION_SEVERITY = {
    "allow": 0,
    "flag_for_review": 1,
    "require_evidence": 2,
    "revise": 3,
    "block": 4,
    "freeze_relist": 5,
    "escalate_legal": 6,
}

_FALLBACK = {
    "actions": {
        "allow": {"verdict": "PASS", "always_human_review": False},
        "flag_for_review": {"verdict": "REVIEW", "always_human_review": True},
    },
    "matrix": [],
}


def _repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", "..", ".."))


class RiskMatrix:
    """风险等级 × 动作的查表器。"""

    def __init__(self, document: dict | None = None, load_error: str | None = None):
        self.document = document if document is not None else _FALLBACK
        self.load_error = load_error
        self.actions = self.document.get("actions") or {}
        self._matrix = self.document.get("matrix") or []

    # ---- 装载 ----

    @classmethod
    def load(cls, root: str | None = None) -> "RiskMatrix":
        root = root or _repo_root()
        path = os.path.join(root, MATRIX_PATH)
        try:
            with open(path, encoding="utf-8") as handle:
                return cls(json.load(handle))
        except (OSError, ValueError) as exc:
            return cls(None, load_error=f"could not read {MATRIX_PATH}: {exc}")

    # ---- 查表 ----

    def verdict_for(self, action: str) -> str:
        """动作 → 对外汇报的聚合标签。"""
        spec = self.actions.get(action) or {}
        return spec.get("verdict", "REVIEW")

    def always_human_review(self, action: str) -> bool:
        spec = self.actions.get(action) or {}
        return bool(spec.get("always_human_review", True))

    def executable_by(self, action: str) -> str:
        spec = self.actions.get(action) or {}
        return spec.get("executable_by", "human")

    def is_allowed(self, risk_level: str, action: str) -> bool:
        """矩阵是否允许该组合。"""
        for entry in self._matrix:
            if entry.get("risk_level") == risk_level and entry.get("action") == action:
                return bool(entry.get("allowed"))
        # 矩阵里没有这一格 —— 保守视为不允许。
        return action == "allow"

    def tier_ceiling(self, tier: str) -> str:
        """来源层级允许的最高动作。"""
        return MAX_ACTION_BY_TIER.get(tier, "flag_for_review")

    def tier_may_block(self, tier: str) -> bool:
        """该来源层级是否允许阻断类动作（硬约束 H2）。"""
        return _TIER_CLASS.get(tier) == "blocking"

    def resolve(self, risk_level: str, action: str, tier: str,
                status: str = "active") -> dict:
        """把「规则声明的动作」解析成「允许执行的动作」。

        返回 ``{action, downgraded, reason, verdict, requires_human_review}``。

        降级顺序：

        1. 矩阵不允许该 (risk_level, action) 组合 → 降到 `flag_for_review`；
        2. 硬约束 H2 —— 来源层级不够权威 → 降到 `flag_for_review`；
        3. 规则不是 `active` → 降到 `flag_for_review`。
        """
        notes: list[str] = []
        resolved = action

        if not self.is_allowed(risk_level, resolved):
            notes.append(
                f"the risk matrix does not allow action={action!r} at "
                f"risk_level={risk_level!r}")
            resolved = "flag_for_review"

        ceiling = self.tier_ceiling(tier)
        if resolved in BLOCKING_ACTIONS and not self.tier_may_block(tier):
            notes.append(
                f"source tier {tier!r} may not exceed {ceiling!r} "
                f"(hard constraint H2)")
            resolved = ceiling

        if status != "active" and _ACTION_SEVERITY.get(resolved, 0) > \
                _ACTION_SEVERITY.get("flag_for_review", 0):
            notes.append(
                f"rule status is {status!r}; only active rules may take "
                f"blocking actions")
            resolved = "flag_for_review"

        # 兜底：阻断类动作必须是权威来源 + active 规则。
        if resolved in BLOCKING_ACTIONS:
            if tier not in ("platform_official", "law"):
                notes.append(
                    f"action {resolved!r} requires source tier "
                    f"platform_official/law, got {tier!r} (hard constraint H2)")
                resolved = "flag_for_review"
            elif status != "active":
                notes.append(
                    f"action {resolved!r} requires an active rule, got {status!r}")
                resolved = "flag_for_review"

        if not self.is_allowed(risk_level, resolved):
            notes.append(
                f"downgraded action {resolved!r} is still not allowed at "
                f"risk_level={risk_level!r}")
            resolved = "flag_for_review"

        return {
            "action": resolved,
            "downgraded": resolved != action,
            "reason": "; ".join(notes),
            "verdict": self.verdict_for(resolved),
            "requires_human_review": self.always_human_review(resolved),
        }

    @staticmethod
    def heavier(left: str, right: str) -> str:
        """取更重的动作（聚合多条命中时用）。"""
        if _ACTION_SEVERITY.get(right, 0) > _ACTION_SEVERITY.get(left, 0):
            return right
        return left

    @staticmethod
    def is_human_only(action: str) -> bool:
        return action in ("freeze_relist", "escalate_legal")
