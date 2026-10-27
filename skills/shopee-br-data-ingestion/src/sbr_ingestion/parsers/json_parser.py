"""JSON / JSONL 解析。

* JSON —— 支持顶层数组、包裹对象（`products` / `items` / `data` / `records`
  / `results` / `list`）与单对象。
* JSONL —— 逐行解析；**单行非法只记 error 并继续**（带行号）。

单行非法时不会中断整批 —— 这是「绝不静默丢弃」的具体落法：
合法的行照常产出，非法行进 `errors[]`。
"""

from __future__ import annotations

import json

from .base import ParseError, ParsedDocument

#: 包裹对象里常见的记录数组键
WRAPPER_KEYS = ("products", "items", "data", "records", "results", "list",
                "rows", "entries", "produtos", "itens")


def _extract_records(payload) -> list | None:
    """从已解析的 JSON 结构里找出记录数组。"""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in WRAPPER_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return value
        # 顶层就是单条记录
        return [payload]
    return None


def parse_json(path: str, options: dict | None = None) -> ParsedDocument:
    """解析 JSON 文件。"""
    options = options or {}
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        raise ParseError(f"cannot read file: {exc}", {"path": path}) from exc

    text = raw.decode("utf-8-sig", errors="replace")
    doc = ParsedDocument(kind="json")

    stripped = text.strip()
    if not stripped:
        doc.add_error("error", "file is empty", {"path": path})
        return doc

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        # 可能是 JSONL（多行 JSON）—— 逐行再试一次
        lines = [ln for ln in stripped.splitlines() if ln.strip()]
        if len(lines) > 1:
            doc.kind = "jsonl"
            doc.meta["fallback"] = "jsonl"
            for number, line in enumerate(lines, start=1):
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as line_exc:
                    doc.add_failure("warning",
                                    f"line {number} is not valid JSON: {line_exc.msg}",
                                    {"line": number})
                    continue
                if not isinstance(item, dict):
                    doc.add_failure("warning",
                                    f"line {number} is not a JSON object and was skipped",
                                    {"line": number, "type": type(item).__name__})
                    continue
                doc.records.append(item)
                doc.locators.append(f"line {number}")
            doc.meta["records_total"] = len(doc.records)
            return doc
        doc.add_error("error", f"invalid JSON: {exc.msg}", {"path": path, "line": exc.lineno})
        return doc

    records = _extract_records(payload)
    if records is None:
        doc.add_error("error",
                      "JSON top-level value is neither an array nor an object "
                      "containing a record array",
                      {"path": path})
        return doc

    for index, item in enumerate(records):
        if not isinstance(item, dict):
            doc.add_failure("warning",
                            f"record {index + 1} is not a JSON object and was skipped",
                            {"record_index": index + 1, "type": type(item).__name__})
            continue
        doc.records.append(item)
        doc.locators.append(f"record {index + 1}")

    doc.meta["records_total"] = len(doc.records)
    if isinstance(payload, dict):
        doc.meta["wrapper_keys"] = [k for k in WRAPPER_KEYS if isinstance(payload.get(k), list)]
    return doc


def parse_jsonl(path: str, options: dict | None = None) -> ParsedDocument:
    """解析 JSONL（每行一个 JSON 对象）。"""
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        raise ParseError(f"cannot read file: {exc}", {"path": path}) from exc

    text = raw.decode("utf-8-sig", errors="replace")
    doc = ParsedDocument(kind="jsonl")
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            doc.add_failure("warning", f"line {number} is not valid JSON: {exc.msg}",
                            {"line": number})
            continue
        if not isinstance(item, dict):
            doc.add_failure("warning",
                            f"line {number} is not a JSON object and was skipped",
                            {"line": number, "type": type(item).__name__})
            continue
        doc.records.append(item)
        doc.locators.append(f"line {number}")
    doc.meta["records_total"] = len(doc.records)
    return doc
