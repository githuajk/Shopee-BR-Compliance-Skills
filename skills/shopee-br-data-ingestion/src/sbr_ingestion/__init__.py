"""Shopee BR 多格式资料读取与标准化模块（`shopee-br-data-ingestion`）。

职责边界（见 `skills/shopee-br-data-ingestion/SKILL.md`）：

* 只做「把外部文件读成规范数据」这一件事。
* 产出 `SkillInput`（`contracts/skill_input.schema.json`）、
  `AuditResult[]`（`contracts/audit_result.schema.json`）与
  `ModuleHandoff`（`contracts/module_handoff.schema.json`）。
* **不产生任何合规结论**：本模块不定义规则前缀，最高动作只能是
  `flag_for_review`（硬约束 H2）。
* **绝不修改原始输入**：只读打开，不写回，不改权限，不移动。

纯标准库实现（Python 3.11+）。无 openpyxl / pypdf 依赖：
XLSX 与 DOCX 用 `zipfile` + `xml.etree.ElementTree` 直读 OOXML；
PDF 优先用可选的 `pypdf`，缺失时降级到内置的最小文本层提取器。
"""

from __future__ import annotations

__all__ = [
    "__version__",
    "PARSER_VERSION",
    "ingest_paths",
    "ingest_file",
]

__version__ = "1.0.0"

#: 写入 provenance / rule_version 的解析器版本标识
PARSER_VERSION = f"sbr-ingestion/{__version__}"


def ingest_paths(paths, request_id, options=None, scope=None, target=None):
    """读取一组外部文件，返回规范化结果包。

    参数
    ----
    paths:
        文件路径列表（字符串或 `os.PathLike`）。
    request_id:
        本次请求标识，贯穿全部产出。
    options:
        模块私有选项。支持 `default_shop_id` / `default_currency` /
        `default_currency` / `strict`。未知键被忽略（契约要求）。
    scope:
        生效范围，原样写入 `SkillInput.scope`。
    target:
        目标对象描述；缺省由本模块生成。

    返回
    ----
    dict，含三个契约产物：
      * ``skill_input`` —— 符合 `contracts/skill_input.schema.json`
      * ``results``     —— `AuditResult[]`
      * ``handoff``     —— 符合 `contracts/module_handoff.schema.json`
    """
    from .pipeline import ingest_paths as _impl

    return _impl(
        paths=paths,
        request_id=request_id,
        options=options,
        scope=scope,
        target=target,
    )


def ingest_file(path, request_id, options=None):
    """读取单个文件，返回与 `ingest_paths` 相同结构的子集。"""
    from .pipeline import ingest_paths as _impl

    return _impl(
        paths=[path],
        request_id=request_id,
        options=options,
        scope=None,
        target=None,
    )
