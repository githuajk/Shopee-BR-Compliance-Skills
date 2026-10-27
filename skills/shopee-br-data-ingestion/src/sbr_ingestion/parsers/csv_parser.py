"""CSV / TSV 解析。

* 分隔符嗅探（`,` / `;` / `\t` / `|`）
* 编码嗅探与回退（UTF-8 → UTF-8-SIG → cp1252 → latin-1）
* 表头行定位（跳过 Shopee 导出常见的 banner 行）
"""

from __future__ import annotations

import csv
import io

from .base import ParseError, ParsedDocument
from .tabular import detect_header, scan_banner

ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
DELIMITERS = (",", ";", "\t", "|")


def sniff_delimiter(sample: str) -> str:
    """按各分隔符在**首行**的出现次数选分隔符（并列时按 `,` 优先）。"""
    first_line = sample.splitlines()[0] if sample.splitlines() else ""
    best, best_count = ",", 0
    for delim in DELIMITERS:
        count = first_line.count(delim)
        if count > best_count:
            best, best_count = delim, count
    return best


def decode_bytes(data: bytes) -> tuple[str, str]:
    """按候选编码解码。返回 `(文本, 实际编码)`；全失败抛 `ParseError`。"""
    for enc in ENCODINGS:
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise ParseError("file could not be decoded with any supported encoding "
                     f"({', '.join(ENCODINGS)})")


def parse_csv(path: str, options: dict | None = None) -> ParsedDocument:
    """解析 CSV / TSV。"""
    options = options or {}
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        raise ParseError(f"cannot read file: {exc}", {"path": path}) from exc

    text, encoding = decode_bytes(raw)
    delimiter = options.get("delimiter") or sniff_delimiter(text)
    if delimiter not in DELIMITERS:
        delimiter = ","

    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters="".join(DELIMITERS))
        if dialect.delimiter != delimiter:
            delimiter = dialect.delimiter
    except csv.Error:
        pass  # 嗅探失败就用上面的启发式结果

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [row for row in reader]

    doc = ParsedDocument(kind="csv")
    doc.meta.update({"encoding": encoding, "delimiter": delimiter,
                     "row_count": len(rows)})

    header_index, note = detect_header(rows)
    if header_index is None:
        doc.add_error("error", "no recognisable header row found in the first "
                                f"{min(len(rows), 30)} rows",
                      {"row_count": len(rows), "delimiter": delimiter,
                       "seen_rows": [r[:8] for r in rows[:5]]})
        return doc
    if note:
        doc.add_error("warning", note,
                      {"row": header_index + 1, "headers": rows[header_index][:12]})

    headers = [c.strip() if isinstance(c, str) else c for c in rows[header_index]]
    doc.meta["header_row"] = header_index + 1
    doc.meta["headers"] = headers
    banner = scan_banner(rows[:header_index])
    if banner:
        doc.meta["banner"] = banner

    for offset, row in enumerate(rows[header_index + 1:], start=1):
        row_number = header_index + 1 + offset
        if not any((c or "").strip() for c in row):
            continue
        doc.records.append({"__row__": row, "__headers__": headers})
        doc.locators.append(f"row {row_number}")

    doc.meta["records_total"] = len(doc.records)
    return doc
