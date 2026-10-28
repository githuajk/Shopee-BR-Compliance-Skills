"""错误记录（契约 `AuditResult.errors[]`）。

契约要求：**绝不静默丢弃**。每条输入要么产出结论，要么产出错误说明。
错误分三级：

* ``warning`` —— 该条规则因输入缺失而未评估（硬约束 H3）。
* ``error`` —— 输入不可读 / 规则文件不可解析等局部问题（不中断整批）。
* ``fatal`` —— 规则库或契约不可用，整个模块停摆。
"""

from __future__ import annotations

__all__ = [
    "ErrorLog",
    "SEVERITY_WARNING",
    "SEVERITY_ERROR",
    "SEVERITY_FATAL",
    "STAGE_INPUT",
    "STAGE_RULE_LOADING",
    "STAGE_RULE_EVALUATION",
    "STAGE_MATRIX",
]

SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"
SEVERITY_FATAL = "fatal"

STAGE_INPUT = "input"
STAGE_RULE_LOADING = "rule_loading"
STAGE_RULE_EVALUATION = "rule_evaluation"
STAGE_MATRIX = "risk_matrix"


class ErrorLog:
    """按顺序累积错误记录，生成唯一的 ``error_id``。"""

    def __init__(self) -> None:
        self.items: list[dict] = []
        self._counter = 0

    def add(self, stage: str, severity: str, message: str, context=None) -> dict:
        self._counter += 1
        entry = {
            "error_id": f"ERR-DUP-{self._counter:04d}",
            "stage": stage,
            "severity": severity,
            "message": message,
            "context": context,
        }
        self.items.append(entry)
        return entry

    def warning(self, stage: str, message: str, context=None) -> dict:
        return self.add(stage, SEVERITY_WARNING, message, context)

    def error(self, stage: str, message: str, context=None) -> dict:
        return self.add(stage, SEVERITY_ERROR, message, context)

    def fatal(self, stage: str, message: str, context=None) -> dict:
        return self.add(stage, SEVERITY_FATAL, message, context)

    @property
    def has_fatal(self) -> bool:
        return any(item["severity"] == SEVERITY_FATAL for item in self.items)

    def by_severity(self, severity: str) -> list[dict]:
        return [item for item in self.items if item["severity"] == severity]
