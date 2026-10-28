"""`shopee-br-policy-research` —— Shopee BR 官方政策研究与来源核查模块。

职责边界（见 `skills/shopee-br-policy-research/SKILL.md`）：

* 抓取/刷新官方来源并保留原始抓取件（`research/raw/*.txt`，不可变证据）；
* 核验规则引文**逐字**出现在抓取件中（硬约束 H4）；
* 维护来源清单与平台违规码目录；抓取失败的来源做**正式处置**
  （`dispositions` 记录，503 缺口示例：`br_anvisa_medicamentos_prescricao`）；
* 产出 `AuditResult[]`（来源核查结果）与 `ModuleHandoff`
  （`assumptions` / `known_gaps` 必填）；
* **不对具体商品做审核判定**（listing-audit / ip-review 的职责）；
* **只读** `research/` / `rules/`，绝不写回，不执行线上动作（H6）。

实现层于 2026-10-28 补齐（src/ 包 + CLI + 自有 L9 测试），与其余 6 个
模块形态一致。纯标准库实现（Python 3.11+）。无第三方依赖。
"""

from __future__ import annotations

from .contracts import (
    CONTRACT_VERSION,
    MODULE_NAME,
    RULE_VERSION,
    __version__,
    build_audit_result,
    build_handoff,
    build_skill_input,
)
from .engine import run_from_files, run_policy_research

__all__ = [
    "__version__",
    "MODULE_NAME",
    "CONTRACT_VERSION",
    "RULE_VERSION",
    "run_policy_research",
    "run_from_files",
    "build_skill_input",
    "build_audit_result",
    "build_handoff",
]
