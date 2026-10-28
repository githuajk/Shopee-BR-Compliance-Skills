"""模块登记表 —— 主 Skill **显式**驱动各专业模块的依据。

> **目标平台不保证 Skill 之间存在自动调用能力**（`PROJECT_RULES.md` §4.2）。
> 因此本模块**不假设**能「调用」另一个 Skill。它做的是：
>
> 1. **读取**目标模块的 `SKILL.md`（文本）—— 见 `modules.read_module_skill_md`
> 2. 依该文件声明的输入/输出契约**构造**输入（`contracts/skill_input.schema.json`）
> 3. 依该文件声明的输出契约**驱动**该模块的命令行入口，取得 `AuditResult[]`
> 4. 依 `contracts/audit_result.schema.json` **校验**
> 5. 记录 `ModuleHandoff`（含 `assumptions` / `known_gaps`）

本文件登记的是**第 3 步的命令行接口** —— 它是各模块真实存在的 CLI 入口，
与其 `SKILL.md` 声明的职责一一对应。

纯标准库实现。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

#: 主 Skill 的模块名（写入 `AuditResult.module`）
MODULE_NAME = "shopee-br-compliance"

#: 契约版本
CONTRACT_VERSION = "1.0.0"


@dataclass(frozen=True)
class ModuleSpec:
    """一个可被本模块驱动的专业模块。"""

    #: 模块名（契约 `AuditResult.module` 枚举内的值）
    name: str
    #: 命令行入口（相对仓库根）
    cli_rel: str
    #: 构造该模块输入时的 `task_type`
    task_type: str
    #: 在链路中的角色
    role: str
    #: 该模块消费 `products[]`
    reads_products: bool = False
    #: 该模块消费 `cases[]`
    reads_cases: bool = False
    #: 该模块消费输入文件（ingestion 专用）
    reads_files: bool = False
    #: 该模块的规则前缀（用于说明文档，非判定依据）
    rule_prefixes: tuple = ()
    #: 该模块是否产生规则级结论（`rule_refs`）
    produces_rule_refs: bool = False


#: 参与编排的全部模块（按链路的自然顺序登记）
MODULE_SPECS: tuple[ModuleSpec, ...] = (
    ModuleSpec(
        name="shopee-br-data-ingestion",
        cli_rel=os.path.join("skills", "shopee-br-data-ingestion", "src",
                             "sbr_ingestion_cli.py"),
        task_type="ingestion",
        role="ingestion",
        reads_files=True,
    ),
    ModuleSpec(
        name="shopee-br-listing-audit",
        cli_rel=os.path.join("skills", "shopee-br-listing-audit", "src",
                             "sbr_listing_audit_cli.py"),
        task_type="listing_audit",
        role="content_audit",
        reads_products=True,
        rule_prefixes=("PI", "RI", "MED", "LV"),
        produces_rule_refs=True,
    ),
    ModuleSpec(
        name="shopee-br-duplicate-detection",
        cli_rel=os.path.join("skills", "shopee-br-duplicate-detection", "src",
                             "sbr_duplicate_detection_cli.py"),
        task_type="duplicate_detection",
        role="duplicate",
        reads_products=True,
        reads_cases=True,
        rule_prefixes=("DUP", "RL", "AU", "AC"),
        produces_rule_refs=True,
    ),
    ModuleSpec(
        name="shopee-br-ip-review",
        cli_rel=os.path.join("skills", "shopee-br-ip-review", "src",
                             "sbr_ip_review_cli.py"),
        task_type="ip_review",
        role="ip",
        reads_products=True,
        rule_prefixes=("IP",),
        produces_rule_refs=True,
    ),
    ModuleSpec(
        name="shopee-br-reporting",
        cli_rel=os.path.join("skills", "shopee-br-reporting", "src",
                             "sbr_reporting_cli.py"),
        task_type="reporting",
        role="reporting",
    ),
)

#: 按名字索引
SPECS_BY_NAME: dict[str, ModuleSpec] = {spec.name: spec for spec in MODULE_SPECS}

#: 本模块**不驱动**的模块（独立任务，需要时单独执行）
STANDALONE_MODULES = ("shopee-br-policy-research",)

#: 链路的固定阶段顺序（`references/execution_workflow.md` §2）
STAGE_ORDER = ("ingestion", "content_audit", "ip", "duplicate", "reporting")


def spec_for(name: str) -> ModuleSpec | None:
    """按名字取模块登记项。未知模块 → `None`。"""
    return SPECS_BY_NAME.get(str(name or "").strip())


def skill_md_rel(name: str) -> str:
    """模块说明文件的仓库相对路径。"""
    return os.path.join("skills", name, "SKILL.md")
