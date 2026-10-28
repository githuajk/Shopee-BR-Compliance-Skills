"""解析器基类与公共工具。

所有解析器共享的约定：

* **只读打开**原始输入（`rb` / `r`），绝不写回。
* 每个解析器返回 `ParsedDocument`：

  * `records` —— 原始记录列表（dict 或 str）
  * `errors` —— 解析级错误（`{severity, message, context}`）
  * `locators` —— 与 `records` 一一对应的原始定位
  * `meta` —— 解析统计信息（sheet 名、编码、表头行号……）
* 记录级失败**不中断**整批：能继续就继续，不能继续就记 error。
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ParsedDocument:
    """一个输入文件的解析结果。

    三个计数互相独立，不要混淆：

    * `records` —— 成功解析出的记录
    * `failed` —— **没能**产出记录的失败条数（写进溯源的 `records_failed`）
    * `errors` —— 全部问题（严重度 + 消息），无论是否导致记录丢失

    `follow_up` 是**需要下游补做**的事项（如 OCR / 视觉分析）——
    它既不是失败，也不该被当作「已完成」。
    """

    kind: str
    records: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    locators: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    failed: int = 0
    follow_up: list = field(default_factory=list)

    @property
    def records_parsed(self) -> int:
        return len(self.records)

    @property
    def records_failed(self) -> int:
        return self.failed

    def add_error(self, severity: str, message: str, context=None) -> None:
        item = {"severity": severity, "message": message}
        if context:
            item["context"] = context
        self.errors.append(item)

    def add_failure(self, severity: str, message: str, context=None) -> None:
        """记录一次**失败**（没能产出记录）。"""
        self.failed += 1
        self.add_error(severity, message, context)

    def add_follow_up(self, item: str, context=None) -> None:
        """登记一个需要下游补做的事项。"""
        self.follow_up.append(item)
        payload = {"needs": list(self.follow_up)}
        if context:
            payload.update(context)
        self.add_error("warning",
                       f"downstream follow-up required: {item}", payload)

    def locator(self, index: int) -> str:
        if 0 <= index < len(self.locators):
            return self.locators[index]
        return f"record {index + 1}"


class ParseError(Exception):
    """格式级失败 —— 整个文件无法解析。"""

    def __init__(self, message: str, context=None):
        super().__init__(message)
        self.message = message
        self.context = context or {}


class UnsupportedFormat(ParseError):
    """格式不被支持。"""


def utc_now_iso() -> str:
    """当前 UTC 时间，ISO 8601（秒精度，带 `Z`）。"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: str) -> str:
    """文件的 SHA-256 十六进制摘要（**只读**）。"""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 256), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_stat(path: str) -> dict:
    """记录文件的 mtime 与 size（用于不可变性断言）。"""
    st = os.stat(path)
    return {
        "size": st.st_size,
        "mtime_ns": st.st_mtime_ns,
    }
