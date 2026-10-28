"""错误记录的统一容器。

契约：`contracts/audit_result.schema.json` 的 `errors[]`：

| 字段 | 说明 |
|---|---|
| `error_id` | 唯一标识 |
| `stage` | 出错阶段 |
| `severity` | `warning` / `error` / `fatal` |
| `message` | 人类可读消息 |
| `context` | 结构化上下文（可选） |

**绝不静默丢弃**：每条输入要么产出结论，要么产出错误说明。
"""

from __future__ import annotations

SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"
SEVERITY_FATAL = "fatal"

#: 出错阶段
STAGE_ROUTE = "routing"
STAGE_INVOKE = "module_invocation"
STAGE_LOAD = "input_load"
STAGE_VALIDATE = "contract_validation"
STAGE_INTEGRATE = "integration"
STAGE_REPORT = "reporting"
STAGE_OUTPUT = "output_write"

_SEVERITIES = (SEVERITY_WARNING, SEVERITY_ERROR, SEVERITY_FATAL)


class ErrorLog:
    """错误记录收集器。错误 ID 在本日志内唯一。"""

    def __init__(self) -> None:
        self._items: list[dict] = []
        self._counter = 0

    def add(self, stage: str, severity: str, message: str, context=None) -> dict:
        if severity not in _SEVERITIES:
            severity = SEVERITY_ERROR
        self._counter += 1
        item = {
            "error_id": f"SBRC-E{self._counter:04d}",
            "stage": stage,
            "severity": severity,
            "message": message,
        }
        if context is not None:
            item["context"] = context
        self._items.append(item)
        return item

    def warning(self, stage: str, message: str, context=None) -> dict:
        return self.add(stage, SEVERITY_WARNING, message, context)

    def error(self, stage: str, message: str, context=None) -> dict:
        return self.add(stage, SEVERITY_ERROR, message, context)

    def fatal(self, stage: str, message: str, context=None) -> dict:
        return self.add(stage, SEVERITY_FATAL, message, context)

    @property
    def items(self) -> list[dict]:
        return list(self._items)

    @property
    def has_fatal(self) -> bool:
        return any(i["severity"] == "fatal" for i in self._items)

    def count(self, severity: str) -> int:
        return sum(1 for i in self._items if i["severity"] == severity)
