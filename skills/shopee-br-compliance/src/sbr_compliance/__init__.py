"""`shopee-br-compliance` —— Shopee BR 合规审核**主 Skill**（编排层）。

职责边界（见 `skills/shopee-br-compliance/SKILL.md`）：

* 只做**编排**：分流 → 显式读取并驱动各专业模块 → 整合 → 汇总 → 交接；
* **不实现任何业务规则** —— 规则在各专业模块（`PI`/`RI`/`MED`/`LV`/`IP`/
  `DUP`/`RL`/`AU`/`AC`）；
* **不假设 Skill 之间存在自动调用能力** —— 目标平台不保证这一点，因此
  工作流被设计为「读模块说明 → 构造输入 → 驱动该模块的命令行入口 →
  校验 → 交接」的显式约定（`PROJECT_RULES.md` §4.2）；
* **不做任何写平台操作** —— 不发布、不改线上、不下架、不解冻、不申诉；
* 产出符合 `contracts/audit_result.schema.json`（v1.0.0）的 `AuditResult[]`
  与符合 `contracts/module_handoff.schema.json`（v1.0.0）的 `ModuleHandoff`。

纯标准库实现（Python 3.11+）。无第三方依赖。
"""

from __future__ import annotations

__all__ = [
    "__version__",
    "MODULE_NAME",
    "CONTRACT_VERSION",
    "run_compliance",
    "render_report",
    "decide",
    "aggregate",
    "read_module_skill_md",
    "RiskMatrix",
    "load_matrix",
    "MatrixUnavailable",
]

__version__ = "1.0.0"

#: 写入 `AuditResult.module` 与 `ModuleHandoff.from_module`
MODULE_NAME = "shopee-br-compliance"

#: 契约版本（与 `contracts/*.schema.json` 一致）
CONTRACT_VERSION = "1.0.0"


def run_compliance(skill_input: dict, *, root: str | None = None,
                   out_dir: str | None = None,
                   input_paths: list | None = None) -> dict:
    """执行一次完整的合规审核编排。

    参数
    ----
    skill_input:
        符合 `contracts/skill_input.schema.json` 的输入。
    root:
        仓库根路径；缺省自动推导。
    out_dir:
        产出目录。缺省不落盘（只在返回值里给出内容）。
    input_paths:
        交给 `shopee-br-data-ingestion` 的外部文件路径。

    返回
    ----
    dict，含 ``results`` / ``summary`` / ``handoff`` / ``report`` / ``errors``
    / ``routing`` / ``runs`` / ``written``。
    """
    from .pipeline import run_compliance as _impl

    return _impl(skill_input, root=root, out_dir=out_dir,
                  input_paths=input_paths)


def render_report(summary: dict, matrix=None, products=None) -> str:
    """渲染人读 Markdown 报告。"""
    from .render import render_report as _impl

    return _impl(summary, matrix, products)


def decide(options=None, products=None, cases=None, input_paths=None):
    """分流：决定本次执行哪些模块。"""
    from .routing import decide as _impl

    return _impl(options, products, cases, input_paths)


def aggregate(results: list, matrix=None, request_id: str = "REQ-UNKNOWN",
              log=None):
    """把一批上游 `AuditResult` 聚合成逐目标结论。"""
    from .integration import aggregate as _impl
    from .matrix import RiskMatrix as _RiskMatrix
    from .matrix import load_matrix as _load_matrix

    matrix = matrix if matrix is not None else _RiskMatrix(_load_matrix())
    return _impl(results, matrix, request_id, log)


def read_module_skill_md(root: str, module_name: str):
    """显式读取某个模块的说明文件。"""
    from .driver import read_module_skill_md as _impl

    return _impl(root, module_name)


def __getattr__(name: str):
    if name in ("RiskMatrix", "load_matrix", "MatrixUnavailable"):
        from . import matrix as _matrix
        return getattr(_matrix, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
