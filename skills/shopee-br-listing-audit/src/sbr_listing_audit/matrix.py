"""`contracts/risk_action_matrix.json` 查表 —— 动作**不由本模块决定**。

`PROJECT_RULES.md` §7 与 `contracts/risk_action_matrix.json` 是动作的唯一
权威来源。本模块只做三件事：

1. 查表：`risk_level × 声明动作` → 该组合是否被允许。
2. 查表：`动作` → `verdict`（聚合标签）。
3. 查表：`动作` → `always_human_review` / `executable_by`。

读不到契约时**回落到最保守的内置映射**（只允许 `allow` /
`flag_for_review`），并在错误记录里说明 —— 契约缺失不允许模块
自行发明动作。
"""

from __future__ import annotations

import json
import os
from typing import Any

#: 读不到契约时的回落矩阵 —— 只保留两个最保守的动作。
FALLBACK = {
    "actions": {
        "allow": {"verdict": "PASS", "always_human_review": False,
                  "executable_by": "automation"},
        "flag_for_review": {"verdict": "REVIEW", "always_human_review": True,
                            "executable_by": "human"},
    },
    "matrix": [],
}


class MatrixError(Exception):
    """风险动作矩阵缺失或不可解析。"""


def matrix_path(root: str | None = None) -> str:
    if root:
        return os.path.join(root, "contracts", "risk_action_matrix.json")
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    return os.path.join(repo_root, "contracts", "risk_action_matrix.json")


def load_matrix(root: str | None = None) -> tuple[dict, str | None]:
    """载入矩阵。返回 `(matrix, error_message)`。

    `error_message` 非 `None` 表示契约读不到，调用方应记录 error 并
    使用回落矩阵。
    """
    path = matrix_path(root)
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle), None
    except FileNotFoundError:
        return dict(FALLBACK), f"risk action matrix is missing: {path}"
    except (OSError, ValueError) as exc:
        return dict(FALLBACK), f"risk action matrix is unreadable: {path}: {exc}"


def is_allowed(matrix: dict, risk_level: str, action: str) -> bool:
    """该 `(risk_level, action)` 组合是否被矩阵允许。"""
    for entry in matrix.get("matrix", []):
        if entry.get("risk_level") == risk_level and entry.get("action") == action:
            return bool(entry.get("allowed"))
    # 矩阵没有这一格 → 不可用（回落矩阵下只有 allow 放行）
    return action == "allow"


def verdict_for(matrix: dict, action: str) -> str:
    """动作 → 聚合标签。未知动作按最重的 `REVIEW` 处理。"""
    spec = matrix.get("actions", {}).get(action)
    if not isinstance(spec, dict):
        return "REVIEW"
    return str(spec.get("verdict", "REVIEW"))


def always_human_review(matrix: dict, action: str) -> bool:
    spec = matrix.get("actions", {}).get(action)
    if not isinstance(spec, dict):
        return True
    return bool(spec.get("always_human_review", True))


def executable_by(matrix: dict, action: str) -> str:
    spec = matrix.get("actions", {}).get(action)
    if not isinstance(spec, dict):
        return "human"
    return str(spec.get("executable_by", "human"))


def pick_allowed_action(matrix: dict, risk_level: str,
                        preferred: str,
                        fallbacks: tuple[str, ...] = ()) -> str:
    """在矩阵允许的格子里挑选动作。

    优先用规则声明的动作；不允许则按 `fallbacks` 顺序退化。
    **任何情况下都不会返回矩阵未允许的组合。**
    """
    candidates = (preferred,) + tuple(fallbacks)
    for candidate in candidates:
        if candidate and is_allowed(matrix, risk_level, candidate):
            return candidate
    # 兜底：矩阵允许的最轻动作
    for level_action in (("info", "allow"), ("low", "allow"), ("low", "flag_for_review")):
        if is_allowed(matrix, level_action[0], level_action[1]):
            return level_action[1]
    return "flag_for_review"


def matrix_combo(matrix: dict, risk_level: str, action: str) -> dict | None:
    """取矩阵条目（用于报告与自检）。"""
    for entry in matrix.get("matrix", []):
        if entry.get("risk_level") == risk_level and entry.get("action") == action:
            return entry
    return None


def describe(matrix: dict, risk_level: str, action: str) -> dict[str, Any]:
    """描述一个判定组合的契约依据（写进 `reason` / `review_rationale`）。"""
    entry = matrix_combo(matrix, risk_level, action) or {}
    spec = matrix.get("actions", {}).get(action)
    spec = spec if isinstance(spec, dict) else {}
    return {
        "risk_level": risk_level,
        "action": action,
        "verdict": verdict_for(matrix, action),
        "allowed": bool(entry.get("allowed", False)),
        "note": entry.get("note"),
        "always_human_review": always_human_review(matrix, action),
        "executable_by": executable_by(matrix, action),
    }
