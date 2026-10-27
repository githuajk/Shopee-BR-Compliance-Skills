"""`shopee-br-reporting` —— Shopee BR 审核结果汇总与报告生成模块。

职责边界（见 `skills/shopee-br-reporting/SKILL.md`）：

* 只做**汇总**：把多模块的 `AuditResult[]` 按
  `contracts/risk_action_matrix.json` 聚合成逐目标结论。
* 产出结构化 JSON 汇总 + 人读 Markdown 报告 + `ModuleHandoff`。
* **不产生新的审核结论** —— 只汇总，不判断。
* **不执行任何平台动作** —— `freeze_relist` / `escalate_legal` 是
  `human_only`（硬约束 H6），本模块只提出建议。

纯标准库实现（Python 3.11+）。无第三方依赖。
"""

from __future__ import annotations

__all__ = [
    "__version__",
    "MODULE_NAME",
    "CONTRACT_VERSION",
    "run_reporting",
    "render_report",
    "aggregate",
    "build_summary",
    "build_handoff",
    "RiskMatrix",
    "RuleIndex",
    "load_matrix",
    "MatrixUnavailable",
]

__version__ = "1.0.0"

#: 模块名（写入 `AuditResult.module` 与 `ModuleHandoff.from_module`）
MODULE_NAME = "shopee-br-reporting"

#: 契约版本
CONTRACT_VERSION = "1.0.0"


def run_reporting(skill_input: dict, root: str | None = None,
                  out_dir: str | None = None) -> dict:
    """执行一次汇总与报告生成。返回产出包。"""
    from .pipeline import run_reporting as _impl

    return _impl(skill_input, root=root, out_dir=out_dir)


def render_report(summary: dict, matrix=None, products=None,
                  hard_constraint_notes=None) -> str:
    """渲染 Markdown 报告。"""
    from .render import render_report as _impl

    return _impl(summary, matrix, products, hard_constraint_notes)


def aggregate(results: list, matrix=None, request_id: str = "REQ-UNKNOWN",
              log=None):
    """聚合一批 `AuditResult`。"""
    from .aggregate import aggregate as _impl
    from .matrix import RiskMatrix as _RiskMatrix
    from .matrix import load_matrix as _load_matrix

    matrix = matrix if matrix is not None else _RiskMatrix(_load_matrix())
    return _impl(results, matrix, request_id, log)


def build_summary(per_target, batch, raw_results, loaded, matrix, rule_index,
                  request_id: str) -> dict:
    """构造结构化汇总。"""
    from .pipeline import build_summary as _impl

    return _impl(per_target, batch, raw_results, loaded, matrix, rule_index,
                 request_id)


def build_handoff(summary: dict, per_target, batch, request_id: str,
                  to_module: str = "shopee-br-compliance",
                  payload_ref: str | None = None) -> dict:
    """构造交接记录。"""
    from .pipeline import build_handoff as _impl

    return _impl(summary, per_target, batch, request_id, to_module, payload_ref)


def __getattr__(name):
    if name == "RiskMatrix":
        from .matrix import RiskMatrix
        return RiskMatrix
    if name == "RuleIndex":
        from .rules import RuleIndex
        return RuleIndex
    if name == "load_matrix":
        from .matrix import load_matrix
        return load_matrix
    if name == "MatrixUnavailable":
        from .matrix import MatrixUnavailable
        return MatrixUnavailable
    raise AttributeError(name)
