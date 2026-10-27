"""Shopee BR 重复刊登与违规重发检查模块（`shopee-br-duplicate-detection`）。

职责边界（见 `skills/shopee-br-duplicate-detection/SKILL.md`）：

* 只做四件事 —— 同店重复检测、跨店同款关联、违规重发检测（含冻结建议）、
  授权缺口与处罚点/申诉时限检查；
* 产出 `AuditResult[]`（`contracts/audit_result.schema.json`）与
  `ModuleHandoff`（`contracts/module_handoff.schema.json`）；
* **不产生 IP 类结论**（硬约束 H1）—— 关联到 IP 投诉案件时只提示人工复核；
* **绝不自动执行线上处置**（硬约束 H6）—— `freeze_relist` 只建议。

纯标准库实现（Python 3.11+）。无第三方依赖。
"""

from __future__ import annotations

__all__ = [
    "__version__",
    "detect_duplicates",
    "detect_from_files",
    "MODULE_NAME",
    "CONTRACT_VERSION",
    "RULE_VERSION",
]

__version__ = "1.0.0"

#: 写入 provenance / rule_version 的标识
MODULE_NAME = "shopee-br-duplicate-detection"
CONTRACT_VERSION = "1.0.0"
RULE_VERSION = "sbr-dup-rules/1.0.0"


def detect_duplicates(skill_input: dict, options: dict | None = None,
                      root: str | None = None) -> dict:
    """执行重复刊登与违规重发检查。

    参数
    ----
    skill_input:
        符合 `contracts/skill_input.schema.json` 的输入。
    options:
        模块私有选项。识别 `cross_store`（默认 true）、`similarity_threshold`
        （默认 0.62）、`relist_content_threshold`（默认 0.62）。未知键忽略
        （契约要求）。
    root:
        仓库根（用于定位 `rules/` 与 `contracts/`）。缺省自动推导。

    返回
    ----
    dict，含 ``skill_input`` / ``results`` / ``handoff`` / ``products`` /
    ``cases`` / ``errors`` / ``duplicates`` / ``relists``。
    """
    from .engine import detect_duplicates as _impl

    return _impl(skill_input, options=options, root=root)


def detect_from_files(skill_input_path: str, out_dir: str,
                      options: dict | None = None,
                      root: str | None = None) -> dict:
    """读入 `skill_input.json`，写出三份契约产物。

    写出（到 ``out_dir``）：

    * ``skill_input.json`` —— 原样回写，便于追溯；
    * ``audit_results.json`` —— `AuditResult[]`；
    * ``module_handoff.json`` —— `ModuleHandoff`。

    **只读输入** —— 本函数从不写回被读取的文件。
    """
    import json
    import os

    from .engine import detect_duplicates as _impl

    with open(skill_input_path, encoding="utf-8") as handle:
        skill_input = json.load(handle)

    bundle = _impl(skill_input, options=options, root=root)

    os.makedirs(out_dir, exist_ok=True)
    written = {
        "skill_input.json": bundle["skill_input"],
        "audit_results.json": bundle["results"],
        "module_handoff.json": bundle["handoff"],
    }
    for name, payload in written.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    return bundle
