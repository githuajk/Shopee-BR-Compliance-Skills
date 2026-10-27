"""结果装载：把多来源的 `AuditResult[]` 读成一张统一的表。

输入形态（本模块自己定义，因为上游模块尚未就绪 —— 见 `SKILL.md` §3）：

| 来源 | 说明 |
|---|---|
| `options.results` | 内联的 `AuditResult[]`（或单个对象） |
| `options.result_files` | 结果文件路径列表；每个文件可以是 `AuditResult[]`、单个 `AuditResult`，或 `{"results": [...]}` 包裹 |

**失败不中断整批**：单个文件不可读 / 不可解析 → 记 `error` 并继续处理其它来源。
"""

from __future__ import annotations

import json
import os

from .errors import (
    STAGE_LOAD,
    STAGE_VALIDATE,
    ErrorLog,
)


class LoadedResults:
    """装载结果。"""

    def __init__(self) -> None:
        #: 通过契约校验的结果
        self.accepted: list[dict] = []
        #: 未通过契约校验的结果（已跳过，附原因）
        self.rejected: list[dict] = []
        #: 已读取的来源（文件路径或 `<inline>`）
        self.sources: list[str] = []
        #: 读取到的原始结果条数
        self.total_seen = 0

    @property
    def source_modules(self) -> list[str]:
        seen: list[str] = []
        for item in self.accepted:
            module = item.get("module")
            if module and module not in seen:
                seen.append(module)
        return seen


def _extract_records(payload) -> list[dict]:
    """从一个已解析的 JSON 文档里抽出 `AuditResult` 记录列表。

    支持三种形态：裸数组、单个对象、`{"results": [...]}` 包裹。
    """
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("results", "audit_results", "audit_result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
            if isinstance(value, dict):
                return [value]
        return [payload]
    return []


def load_results(result_files=None, inline=None, validator=None, error_log: ErrorLog | None = None) -> LoadedResults:
    """装载并校验结果。

    参数
    ----
    result_files:
        结果文件路径列表。
    inline:
        内联的 `AuditResult[]` 或单个对象。
    validator:
        `contracts/ContractValidator`；缺省则**不做**契约校验（调用方负责）。
    error_log:
        错误收集器；缺省则建一个内部的。
    """
    log = error_log if error_log is not None else ErrorLog()
    loaded = LoadedResults()

    def _accept(records, origin: str) -> None:
        for index, record in enumerate(records):
            loaded.total_seen += 1
            if validator is not None:
                problems = validator.validate(record)
                if problems:
                    loaded.rejected.append({
                        "origin": origin,
                        "index": index,
                        "result_id": record.get("result_id"),
                        "module": record.get("module"),
                        "problems": problems[:6],
                    })
                    log.error(
                        STAGE_VALIDATE,
                        (f"result from {origin} (index {index}) does not satisfy "
                         f"contracts/audit_result.schema.json and was skipped: "
                         + "; ".join(problems[:3])),
                        {"origin": origin, "index": index,
                         "result_id": record.get("result_id"),
                         "problems": problems[:6]},
                    )
                    continue
            loaded.accepted.append(record)

    # --- 内联结果 ---
    if inline is not None:
        records = _extract_records(inline)
        if not records:
            log.error(STAGE_LOAD, "options.results contained no AuditResult object",
                      {"origin": "<inline>"})
        else:
            loaded.sources.append("<inline>")
            _accept(records, "<inline>")

    # --- 结果文件 ---
    for path in (result_files or []):
        loaded.sources.append(path)
        if not os.path.exists(path):
            log.error(STAGE_LOAD, f"result file does not exist: {path}",
                      {"path": path})
            continue
        if not os.path.isfile(path):
            log.error(STAGE_LOAD, f"result path is not a regular file: {path}",
                      {"path": path})
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError) as exc:
            log.error(STAGE_LOAD, f"result file could not be read: {path} ({exc})",
                      {"path": path, "error": str(exc)})
            continue
        records = _extract_records(payload)
        if not records:
            log.error(STAGE_LOAD,
                      f"result file contains no AuditResult object: {path}",
                      {"path": path})
            continue
        _accept(records, path)

    return loaded
