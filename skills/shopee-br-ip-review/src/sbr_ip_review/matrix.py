"""风险动作矩阵查表 + 硬约束 H2 执行。

`action` **不是**本模块自己决定的 —— 它由 `contracts/risk_action_matrix.json`
查表得到。本模块只做两件事：

1. 查表：给定 `risk_level` 与期望动作，矩阵决定该组合是否允许、对应哪个 `verdict`。
2. 执行 H2：`block` / `freeze_relist` / `escalate_legal` 只能由
   `source.tier ∈ {platform_official, law}` 且 `status == "active"` 的规则产生；
   其它层级的规则最高只能到 `flag_for_review`。
"""

from __future__ import annotations

import json
import os

#: 阻断类动作 —— 只能来自权威来源的 active 规则
BLOCKING_ACTIONS = frozenset({"block", "freeze_relist", "escalate_legal"})

#: 权威来源层级（可产生阻断类动作）
AUTHORITATIVE_TIERS = frozenset({"platform_official", "law"})

#: 各来源层级允许的最高动作（与 `contracts/risk_action_matrix.json` 的 H2 条款一致）
MAX_ACTION_BY_TIER = {
    "platform_official": "block",
    "law": "block",
    "technical": "flag_for_review",
    "internal_risk": "flag_for_review",
    "unverified": "flag_for_review",
    "ai_inference": "flag_for_review",
}

#: 动作降级顺序（用于矩阵不允许某个组合时逐级回退）
_ACTION_FALLBACK = {
    "escalate_legal": ["escalate_legal", "block", "require_evidence", "flag_for_review", "revise", "allow"],
    "freeze_relist": ["freeze_relist", "block", "require_evidence", "flag_for_review", "allow"],
    "block": ["block", "require_evidence", "flag_for_review", "allow"],
    "require_evidence": ["require_evidence", "flag_for_review", "revise", "allow"],
    "revise": ["revise", "flag_for_review", "allow"],
    "flag_for_review": ["flag_for_review", "allow"],
    "allow": ["allow"],
}

#: 矩阵文件缺失时的保守回退（只允许放行与提示复核）
_FALLBACK_MATRIX = {
    "actions": {
        "allow": {"verdict": "PASS", "always_human_review": False},
        "flag_for_review": {"verdict": "REVIEW", "always_human_review": True},
        "require_evidence": {"verdict": "REVIEW", "always_human_review": True},
        "revise": {"verdict": "REVISE", "always_human_review": True},
        "block": {"verdict": "BLOCK", "always_human_review": True},
        "freeze_relist": {"verdict": "BLOCK", "always_human_review": True},
        "escalate_legal": {"verdict": "BLOCK", "always_human_review": True},
    },
    "matrix": [],
}


def repo_root() -> str:
    """仓库根目录（`skills/<module>/src/<package>/matrix.py` → 上溯四级）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", "..", ".."))


class ActionMatrix:
    """`contracts/risk_action_matrix.json` 的只读封装。"""

    def __init__(self, document: dict, source: str | None = None):
        self.document = document or _FALLBACK_MATRIX
        self.source = source
        self._cells = {
            (row.get("risk_level"), row.get("action")): bool(row.get("allowed"))
            for row in (self.document.get("matrix") or [])
        }

    @classmethod
    def load(cls, root: str | None = None) -> "ActionMatrix":
        path = os.path.join(root or repo_root(), "contracts", "risk_action_matrix.json")
        try:
            with open(path, encoding="utf-8") as handle:
                return cls(json.load(handle), source=path)
        except (OSError, ValueError):
            # 契约读不到时回落到保守矩阵 —— 只允许 allow / flag_for_review。
            return cls(_FALLBACK_MATRIX, source=None)

    # ------------------------------------------------------------------ 查表
    def allows(self, risk_level: str, action: str) -> bool:
        """矩阵是否允许该 `risk_level × action` 组合。"""
        if (risk_level, action) in self._cells:
            return self._cells[(risk_level, action)]
        # 矩阵里没有这一格 —— 保守起见按不允许处理。
        return False

    def verdict_for(self, action: str) -> str:
        """动作 → 对外汇报的聚合结论（`verdict`）。"""
        spec = (self.document.get("actions") or {}).get(action) or {}
        return spec.get("verdict", "REVIEW")

    def always_human_review(self, action: str) -> bool:
        spec = (self.document.get("actions") or {}).get(action) or {}
        return bool(spec.get("always_human_review"))

    def executable_by(self, action: str) -> str:
        spec = (self.document.get("actions") or {}).get(action) or {}
        return spec.get("executable_by", "human")

    def resolve(self, risk_level: str, action: str) -> tuple[str, str | None]:
        """把期望动作收敛成矩阵允许的动作。

        返回 `(action, note)`；`note` 非空表示发生过降级，降级原因必须
        出现在结果的 `reason` / `review_rationale` 里（绝不静默降级）。
        """
        if self.allows(risk_level, action):
            return action, None
        for candidate in _ACTION_FALLBACK.get(action, [action]):
            if self.allows(risk_level, candidate):
                return candidate, (
                    f"矩阵不允许 {risk_level}×{action}，已降级为 {candidate}"
                )
        # 理论上不可达（每个风险等级都允许 allow）。
        return "flag_for_review", f"矩阵未允许 {risk_level}×{action}，已降级为 flag_for_review"

    # -------------------------------------------------------------- 硬约束 H2
    @staticmethod
    def cap_for_source(action: str, tier: str | None, status: str | None) -> tuple[str, str | None]:
        """按来源层级与规则状态封顶动作（硬约束 H2）。

        `block` / `freeze_relist` / `escalate_legal` 只允许来自
        `platform_official` / `law` 的 `active` 规则；其它一律封顶到
        `flag_for_review`。
        """
        if action not in BLOCKING_ACTIONS:
            return action, None
        if tier in AUTHORITATIVE_TIERS and status == "active":
            return action, None
        reason = (
            f"硬约束 H2：{action} 只能来自 platform_official/law 的 active 规则"
            f"（实际 tier={tier or 'unknown'}, status={status or 'unknown'}），已降级为 flag_for_review"
        )
        return "flag_for_review", reason

    @staticmethod
    def tier_ceiling(tier: str | None) -> str:
        """来源层级允许的最高动作。"""
        return MAX_ACTION_BY_TIER.get(tier or "unverified", "flag_for_review")
