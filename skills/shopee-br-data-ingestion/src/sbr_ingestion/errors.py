"""错误记录与四态字段语义。

两条独立的机制：

1. **错误记录**（`contracts/audit_result.schema.json` 的 `errors[]`）
   —— 每条无法解析 / 缺字段 / 映射歧义的输入都必须留痕，**绝不静默丢弃**。
2. **四态字段语义**（`PROJECT_RULES.md` §11.1）
   —— `missing` / `unknown` / `not_applicable` / `pending_verification`，
   禁止用 `""` / `0` / `[]` / `{}` 混同。

四态在产品模型里的落点：

| 状态 | 类型化字段（`brand` / `category` / ...） | 状态记录 |
|---|---|---|
| `missing` | `null` | `history._field_states[field] = "missing"` |
| `unknown` | `null` | `history._field_states[field] = {"state":"unknown","reason":...}` |
| `not_applicable` | `null` | `history._field_states[field] = {"state":"not_applicable"}` |
| `pending_verification` | 保留原值 | `history._field_states[field] = {"state":"pending_verification","assigned_to":...,"due":...}` |

> `data/schema/product.schema.json` 把 `brand` / `model` / `category` 定义为
> `string | null`，**不允许**塞进状态对象；因此状态对象统一落在
> `history._field_states`（`history` 允许任意键值），类型化字段用 `null`
> 表示「本次无数据」。这一张力已写入 `DELIVERY.md` §5 契约变更建议。
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 错误阶段
# ---------------------------------------------------------------------------

STAGE_PARSE = "parse"
STAGE_FIELD_MAPPING = "field_mapping"
STAGE_NORMALIZE = "normalize"
STAGE_RULE_EVALUATION = "rule_evaluation"
STAGE_PROVENANCE = "provenance"

# ---------------------------------------------------------------------------
# 严重度
# ---------------------------------------------------------------------------

SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"
SEVERITY_FATAL = "fatal"

ERROR_ID_PREFIX = "ERR-INGEST"


class ErrorLog:
    """收集错误记录，保证每条都有唯一 `error_id`。"""

    def __init__(self, prefix: str = ERROR_ID_PREFIX):
        self._prefix = prefix
        self._items: list[dict] = []

    def add(self, stage: str, severity: str, message: str, context=None) -> dict:
        item = {
            "error_id": f"{self._prefix}-{len(self._items) + 1:04d}",
            "stage": stage,
            "severity": severity,
            "message": message,
        }
        if context:
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

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    @property
    def has_fatal(self) -> bool:
        return any(i["severity"] == SEVERITY_FATAL for i in self._items)


# ---------------------------------------------------------------------------
# 四态字段语义
# ---------------------------------------------------------------------------

STATE_MISSING = "missing"
STATE_UNKNOWN = "unknown"
STATE_NOT_APPLICABLE = "not_applicable"
STATE_PENDING_VERIFICATION = "pending_verification"


def state_missing() -> None:
    """`missing` —— 字段存在但本次无数据。契约表示为 `null`。"""
    return None


def state_unknown(reason: str) -> dict:
    """`unknown` —— 值存在但无法确定。"""
    return {"state": STATE_UNKNOWN, "reason": reason}


def state_not_applicable() -> dict:
    """`not_applicable` —— 该对象没有此概念。"""
    return {"state": STATE_NOT_APPLICABLE}


def state_pending_verification(assigned_to: str, due=None, reason: str | None = None) -> dict:
    """`pending_verification` —— 有值但待外部确认。"""
    obj = {"state": STATE_PENDING_VERIFICATION, "assigned_to": assigned_to, "due": due}
    if reason:
        obj["reason"] = reason
    return obj


def merge_field_states(history: dict, field: str, state) -> None:
    """把字段状态写进 `history._field_states`（不改其它 history 键）。"""
    states = history.setdefault("_field_states", {})
    if not isinstance(states, dict):
        states = {}
        history["_field_states"] = states
    states[field] = state
