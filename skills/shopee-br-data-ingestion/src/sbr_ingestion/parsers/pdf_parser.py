"""PDF 解析（优雅降级）。

优先级：

1. **`pypdf` 可用** → 用它提取文本层（最稳）。
2. **`pypdf` 不可用** → 退到内置的最小提取器：
   直接扫 `stream ... endstream` 块，解 `FlateDecode`（`zlib`），
   再从内容流里取 `Tj` / `TJ` 的文本算子。
3. **两者都拿不到文本层** → 报「需 OCR」，severity=warning，**不中断整批**。

> 本项目运行环境是 PEP 668 托管环境，**不 pip install**。
> 内置提取器只保证覆盖「常规文字型 PDF」，复杂排版/字体子集编码可能
> 提取不全 —— 此时宁可少提，不可编造。
"""

from __future__ import annotations

import re
import zlib

from .base import ParseError, ParsedDocument

_STREAM = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
_FLATE = re.compile(rb"/FlateDecode")
#: 文本算子：`(...) Tj` / `[...] TJ` / `<hex> Tj`。
#: 允许算子与 `)` 之间有空白与其它简单 token（如 `Td`）。
_TJ_LITERAL = re.compile(rb"\((?P<body>(?:\\.|[^\\()])*)\)\s*(?:-?[\d.]+\s+)*Tj")
_TJ_ARRAY = re.compile(rb"\[(?P<body>(?:[^\[\]\\]|\\.)*)\]\s*(?:-?[\d.]+\s+)*TJ")
_TJ_HEX = re.compile(rb"<(?P<body>[0-9A-Fa-f\s]*)>\s*(?:-?[\d.]+\s+)*Tj")
_ESCAPES = {
    b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f",
    b"(": b"(", b")": b")", b"\\": b"\\",
}


def _unescape(raw: bytes) -> str:
    out = bytearray()
    index = 0
    while index < len(raw):
        char = raw[index:index + 1]
        if char == b"\\" and index + 1 < len(raw):
            nxt = raw[index + 1:index + 2]
            if nxt in _ESCAPES:
                out += _ESCAPES[nxt]
                index += 2
                continue
            if nxt.isdigit():
                octal = raw[index + 1:index + 4]
                digits = b""
                for d in octal:
                    if not (0x30 <= d <= 0x37):
                        break
                    digits += bytes([d])
                if digits:
                    out.append(int(digits, 8) & 0xFF)
                    index += 1 + len(digits)
                    continue
            out += nxt
            index += 2
            continue
        out += char
        index += 1
    return out.decode("utf-8", errors="replace")


def _extract_from_stream(data: bytes) -> str:
    """从内容流里提取文本。**每个文本算子输出一行**（便于后续分块）。"""
    lines: list[str] = []
    for match in _TJ_LITERAL.finditer(data):
        lines.append(_unescape(match.group("body")))
    for match in _TJ_ARRAY.finditer(data):
        body = match.group("body")
        parts = [_unescape(piece.group("body"))
                 for piece in re.finditer(rb"\((?P<body>(?:\\.|[^\\()])*)\)", body)]
        lines.append("".join(parts))
    for match in _TJ_HEX.finditer(data):
        hex_body = re.sub(rb"\s", b"", match.group("body"))
        if len(hex_body) % 2:
            hex_body += b"0"
        try:
            lines.append(bytes.fromhex(hex_body.decode("ascii"))
                         .decode("utf-16-be", errors="replace"))
        except ValueError:
            continue
    return "\n".join(lines)


def _builtin_extract(path: str) -> tuple[str, list[str]]:
    """内置提取器。返回 `(文本, 警告列表)`。"""
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        raise ParseError(f"cannot read file: {exc}", {"path": path}) from exc

    if not raw.startswith(b"%PDF"):
        raise ParseError("not a valid PDF file (missing %PDF header)", {"path": path})

    warnings: list[str] = []
    pieces: list[str] = []
    for match in _STREAM.finditer(raw):
        blob = match.group(1)
        header = raw[max(0, match.start() - 400):match.start()]
        if _FLATE.search(header):
            try:
                blob = zlib.decompress(blob)
            except zlib.error:
                try:
                    blob = zlib.decompressobj().decompress(blob)
                except zlib.error:
                    warnings.append("a FlateDecode stream could not be decompressed and was skipped")
                    continue
        elif b"/Filter" in header:
            continue  # 未知的过滤器（如 DCTDecode）—— 图片流，跳过
        text = _extract_from_stream(blob)
        if text:
            pieces.append(text)

    text = "\n".join(p for p in pieces if p.strip())
    if not text.strip():
        warnings.append("no extractable text layer found")
    return text, warnings


def _pypdf_extract(path: str):
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return None
    try:
        reader = PdfReader(path)
        chunks = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunks)
    except Exception as exc:  # noqa: BLE001 - 提取失败必须降级而不是崩
        return None


def parse_pdf(path: str, options: dict | None = None) -> ParsedDocument:
    """解析 PDF（提取文本层）。"""
    options = options or {}
    doc = ParsedDocument(kind="pdf")

    extractor = "builtin"
    text = _pypdf_extract(path)
    if text is not None:
        extractor = "pypdf"
    else:
        text, warnings = _builtin_extract(path)
        for message in warnings:
            doc.add_error("warning", message, {"path": path})

    doc.meta["extractor"] = extractor
    if not text.strip():
        doc.add_error(
            "warning",
            "PDF has no extractable text layer — OCR is required "
            "(convert to text first, or run the OCR/visual-analysis step)",
            {"path": path, "extractor": extractor},
        )
        doc.meta["records_total"] = 0
        return doc

    # 按空行分块：每个块是一条候选记录
    blocks, current = [], []
    for line in text.splitlines():
        if line.strip():
            current.append(line.strip())
        elif current:
            blocks.append("\n".join(current))
            current = []
    if current:
        blocks.append("\n".join(current))

    doc.meta["block_count"] = len(blocks)
    for index, block in enumerate(blocks, start=1):
        lines = block.splitlines()
        doc.records.append({
            "__meta__": {"title": lines[0].strip()},
            "__body__": lines[1:],
            "__description__": "\n".join(lines[1:]).strip(),
        })
        doc.locators.append(f"page-block {index}")

    doc.meta["records_total"] = len(doc.records)
    return doc
