"""Shopee BR 商品内容合规审核模块（`shopee-br-listing-audit`）。

职责边界（见 `skills/shopee-br-listing-audit/SKILL.md`）：

* 只做「商品内容是否触碰禁售 / 受限 / 药品健康 / 刊登质量规则」这一件事。
* 产出 `AuditResult[]`（`contracts/audit_result.schema.json`）与
  `ModuleHandoff`（`contracts/module_handoff.schema.json`）。
* 规则前缀 `PI` / `RI` / `MED` / `LV` —— **不碰** IP（`SBR-IP-*`）、
  重复（`SBR-DUP-*`）与案件（`SBR-RL-*` / `SBR-AU-*` / `SBR-AC-*`）。
* **动作不由本模块决定** —— 一律查 `contracts/risk_action_matrix.json`。
* 纯标准库实现（Python 3.11+）。无第三方依赖。

**关键词命中 ≠ 违规。** 词库命中只是信号；是否违规由规则层判定，
是否阻断由矩阵层决定。
"""

from __future__ import annotations

__all__ = [
    "__version__",
    "AUDIT_RULE_VERSION",
    "audit_listing",
    "ListingAuditEngine",
    "AuditError",
]

__version__ = "1.0.0"

#: 写入 `AuditResult.rule_version` 的模块规则集标识前缀。
AUDIT_RULE_VERSION = f"sbr-listing-rules/{__version__}"


def audit_listing(skill_input: dict, options: dict | None = None,
                  root: str | None = None) -> dict:
    """审核一批商品。

    参数
    ----
    skill_input:
        符合 `contracts/skill_input.schema.json` 的输入。
    options:
        模块私有选项：`rule_prefixes` / `rules`。未知键被忽略。
    root:
        仓库根路径；缺省自动推导。

    返回
    ----
    dict，含 ``results``（`AuditResult[]`）、``handoff``、``errors``、
    ``evaluations``。
    """
    from .pipeline import audit_listing as _impl
    return _impl(skill_input, options=options, root=root)


def __getattr__(name: str):
    """惰性导出引擎与异常（避免包导入期就加载词库）。"""
    if name in ("ListingAuditEngine", "AuditError"):
        from . import engine
        return getattr(engine, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
