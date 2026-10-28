"""`shopee-br-policy-research` 的错误类型。

纯标准库实现（Python 3.11+），无第三方依赖。
"""

from __future__ import annotations


class PolicyResearchError(Exception):
    """本模块所有错误的基类。"""


class ContractError(PolicyResearchError):
    """输入不符合 `contracts/skill_input.schema.json` 的约定。"""


class AssetMissing(PolicyResearchError):
    """必需的研究资产（sources.json / raw/ / rules/）缺失或不可读。"""
