"""Shopee BR 知识产权与授权风险筛查模块（`shopee-br-ip-review`）。

职责边界（见 `skills/shopee-br-ip-review/SKILL.md`）：

* 只做「知识产权**筛查**」这一件事：区分商标 / 版权 / 外观设计 / 专利四类风险，
  区分指示性使用与混淆性使用，核查品牌授权完整性。
* 产出 `AuditResult[]`（`contracts/audit_result.schema.json`）与
  `ModuleHandoff`（`contracts/module_handoff.schema.json`）。
* **绝不**作最终侵权认定（硬约束 H1）：所有结果恒为 `confidence="signal"` 且
  `requires_human_review=true`。关键词或 logo 命中只是**筛查信号**；仅权利人投诉、
  书面授权或平台投诉通知可确立侵权。
* **绝不**自动执行任何线上处置（发布 / 删除 / 冻结 / 申诉）。本模块只输出建议。

纯标准库实现（Python 3.11+）。可选依赖 `tools/scan_lexicon.py`（项目内共享词库
扫描器，只读）—— 缺失时降级为「词库维度未评估」，不影响规则层判定。
"""

from __future__ import annotations

__all__ = [
    "__version__",
    "MODULE_NAME",
    "REVIEWER_VERSION",
    "CONTRACT_VERSION",
    "review_products",
]

__version__ = "1.0.0"

#: 写入 `AuditResult.module` 与 `provenance.producer` 的模块名
MODULE_NAME = "shopee-br-ip-review"

#: 写入 `provenance.producer` 的版本标识
REVIEWER_VERSION = f"sbr-ip-review/{__version__}"

#: 契约版本（与 `contracts/*.schema.json` 一致）
CONTRACT_VERSION = "1.0.0"


def review_products(skill_input, options=None, rules=None):
    """对一个 `SkillInput` 做知识产权与授权风险筛查。

    参数
    ----
    skill_input:
        符合 `contracts/skill_input.schema.json` 的 dict。
    options:
        模块私有选项（见 SKILL.md §3）。未知键被忽略。
    rules:
        可选的规则列表（`contracts/rule_envelope.schema.json` 格式）。
        缺省时加载本模块拥有的 `rules/02_ip_trademark_copyright.json`。

    返回
    ----
    dict，含：
      * ``results``  —— `AuditResult[]`
      * ``handoff``  —— `ModuleHandoff`
      * ``errors``   —— 全部错误记录
      * ``signals``  —— 每个商品的判定明细（供测试与人工复核，非契约字段）
    """
    from .engine import review_products as _impl

    return _impl(skill_input=skill_input, options=options, rules=rules)
