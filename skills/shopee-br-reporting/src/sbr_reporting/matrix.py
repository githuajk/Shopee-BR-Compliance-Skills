"""`contracts/risk_action_matrix.json` 的读取与解释。

**本模块不定义任何聚合语义。** verdict 顺序、action 粒度、风险等级与动作的
允许组合、硬约束清单 —— 全部来自冻结契约。

矩阵读不到或不可解析时**不猜**：抛 `MatrixUnavailable`，由管线记 `fatal`
错误并停止本模块（`tasks/TASK-REPORT-01.md` §8「规则文件缺失或不可解析 →
记 error 并停止该模块」）。

纯标准库实现。
"""

from __future__ import annotations

import json
import os

#: 阻断类动作 —— 只能由 `platform_official` / `law` 的 `active` 规则产生（H2）
DETERMINISTIC_ACTIONS = ("block", "freeze_relist", "escalate_legal")

#: 有权产生阻断类动作的来源层级（H2）
AUTHORITATIVE_TIERS = ("platform_official", "law")

#: 非权威层级 —— 最高只能到 `flag_for_review`（H2）
NON_AUTHORITATIVE_TIERS = ("internal_risk", "unverified", "ai_inference", "technical")

#: 全部合法来源层级（`contracts/rule_envelope.schema.json` 的枚举）
ALL_TIERS = AUTHORITATIVE_TIERS + NON_AUTHORITATIVE_TIERS

#: 契约矩阵的相对路径
MATRIX_REL = os.path.join("contracts", "risk_action_matrix.json")

#: 矩阵缺失时的兜底（仅在契约文件不可读时用于**保守降级**，不是聚合依据）
_FALLBACK = {
    "verdict_aggregation": {"order": ["PASS", "REVISE", "REVIEW", "BLOCK"]},
    "actions": {
        "allow": {"verdict": "PASS", "always_human_review": False},
        "flag_for_review": {"verdict": "REVIEW", "always_human_review": True},
        "require_evidence": {"verdict": "REVIEW", "always_human_review": True},
        "revise": {"verdict": "REVISE", "always_human_review": True},
        "block": {"verdict": "BLOCK", "always_human_review": True},
        "freeze_relist": {"verdict": "BLOCK", "always_human_review": True},
        "escalate_legal": {"verdict": "BLOCK", "always_human_review": True},
    },
    "risk_levels": {},
    "matrix": [],
    "hard_constraints": [],
}


class MatrixUnavailable(Exception):
    """契约矩阵缺失或不可解析 —— 本模块必须停止，不得自造映射。"""


def find_repo_root(start: str | None = None) -> str:
    """向上查找含 `contracts/risk_action_matrix.json` 的目录。

    找不到时返回按包位置推导的仓库根（`skills/shopee-br-reporting/src/sbr_reporting`
    上溯三级），让调用方仍能得到**确定的**路径去报错，而不是静默使用别的映射。
    """
    here = os.path.abspath(start or os.path.dirname(os.path.abspath(__file__)))
    probe = here
    for _ in range(8):
        if os.path.exists(os.path.join(probe, MATRIX_REL)):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    return os.path.abspath(os.path.join(here, "..", "..", ".."))


def matrix_path(root: str | None = None) -> str:
    """契约矩阵的绝对路径。"""
    return os.path.join(root or find_repo_root(), MATRIX_REL)


def load_matrix(path: str | None = None) -> dict:
    """载入契约矩阵。读不到或不可解析 → `MatrixUnavailable`。"""
    target = path or matrix_path()
    try:
        with open(target, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise MatrixUnavailable(f"risk action matrix not found: {target}") from exc
    except (OSError, ValueError) as exc:
        raise MatrixUnavailable(f"risk action matrix is unreadable: {target} ({exc})") from exc
    if not isinstance(data, dict) or "actions" not in data:
        raise MatrixUnavailable(f"risk action matrix has no 'actions' section: {target}")
    return data


class RiskMatrix:
    """契约矩阵的只读视图。

    * `verdict_order` —— 来自 `verdict_aggregation.order`，用于取最重的 verdict。
    * `action_order` —— `actions` 段的**声明顺序**。契约把动作按
      「笼统 → 具体」排列（`allow` → `flag_for_review` → `require_evidence` →
      `revise` → `block` → `freeze_relist` → `escalate_legal`），
      因此声明顺序即**粒度顺序**：`max_with_action_detail` 保留最细粒度的那一条
      就是取声明顺序最靠后的动作。
    * `allowed_pairs` —— 风险等级 × 动作的允许组合。
    """

    def __init__(self, data: dict) -> None:
        self.data = data
        aggregation = data.get("verdict_aggregation") or {}
        order = aggregation.get("order") or _FALLBACK["verdict_aggregation"]["order"]
        self.verdict_order = [str(v) for v in order]
        self.verdict_rank = {v: i for i, v in enumerate(self.verdict_order)}
        self.actions = dict(data.get("actions") or _FALLBACK["actions"])
        self.action_order = list(self.actions.keys())
        self.granularity = {a: i for i, a in enumerate(self.action_order)}
        self.risk_levels = dict(data.get("risk_levels") or {})
        self.risk_order = list(self.risk_levels.keys())
        self.risk_rank = {r: i for i, r in enumerate(self.risk_order)}
        self.allowed_pairs = {
            (m.get("risk_level"), m.get("action")): bool(m.get("allowed"))
            for m in (data.get("matrix") or [])
        }
        self.hard_constraint_ids = [h.get("id") for h in (data.get("hard_constraints") or [])]

    # -- verdict -------------------------------------------------------
    def verdict_for_action(self, action: str) -> str:
        """动作对应的契约 verdict。未知动作 → `REVIEW`（最保守）。"""
        spec = self.actions.get(action) or {}
        return str(spec.get("verdict") or "REVIEW")

    def max_verdict(self, verdicts) -> str:
        """取最重的 verdict。空集合 → `PASS`。未知 verdict 按最保守处理。"""
        best = None
        for verdict in verdicts:
            rank = self.verdict_rank.get(verdict)
            if rank is None:
                rank = len(self.verdict_order)
            if best is None or rank > self.verdict_rank.get(best, -1):
                best = verdict
        return best or "PASS"

    def canonical_action(self, verdict: str) -> str:
        """某个 verdict 档位的兜底动作（矩阵未给出候选时使用）。

        取该档位中**粒度最细**的动作，使输出永远落在契约允许的组合内。
        """
        candidates = [a for a in self.action_order if self.verdict_for_action(a) == verdict]
        if candidates:
            return candidates[-1]
        return "flag_for_review"

    # -- action --------------------------------------------------------
    def granularity_of(self, action: str) -> int:
        """动作粒度。未知动作 → -1（永不入选）。"""
        return self.granularity.get(action, -1)

    def most_specific(self, actions) -> str | None:
        """候选动作中最细粒度的一条。空 → `None`。"""
        best = None
        for action in actions:
            rank = self.granularity_of(action)
            if rank < 0:
                continue
            if best is None or rank > self.granularity_of(best):
                best = action
        return best

    def is_deterministic(self, action: str) -> bool:
        """是否阻断类动作（H2 / H6）。"""
        return action in DETERMINISTIC_ACTIONS

    def always_human_review(self, action: str) -> bool:
        """矩阵声明的「该动作是否恒需人工复核」。"""
        spec = self.actions.get(action) or {}
        return bool(spec.get("always_human_review"))

    def executable_by(self, action: str) -> str:
        """执行方（`automation` / `human` / `human_only`）。"""
        spec = self.actions.get(action) or {}
        return str(spec.get("executable_by") or "human")

    # -- risk ----------------------------------------------------------
    def risk_rank_of(self, risk_level: str) -> int:
        return self.risk_rank.get(risk_level, -1)

    def max_risk(self, risk_levels) -> str:
        best = None
        for level in risk_levels:
            rank = self.risk_rank_of(level)
            if rank < 0:
                continue
            if best is None or rank > self.risk_rank_of(best):
                best = level
        return best or "info"

    def is_allowed(self, risk_level: str, action: str) -> bool:
        """该 (风险等级, 动作) 组合是否被矩阵允许。未知组合 → 不允许。"""
        return bool(self.allowed_pairs.get((risk_level, action), False))

    def allowed_actions_for(self, risk_level: str) -> list[str]:
        """某风险等级下被允许的动作（按粒度从细到粗）。"""
        return [a for a in reversed(self.action_order)
                if self.is_allowed(risk_level, a)]

    def lower_risk_for(self, risk_level: str, action: str) -> str | None:
        """在动作不变的前提下，能容纳该动作的最高风险等级。"""
        for level in reversed(self.risk_order):
            if self.is_allowed(level, action):
                return level
        return None
