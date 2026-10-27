"""格式识别与解析器分发。

支持的输入格式与失败行为见 `references/format_matrix.md`。
"""

from __future__ import annotations

import os

from .base import ParseError, ParsedDocument, UnsupportedFormat
from .csv_parser import parse_csv
from .docx_parser import parse_docx
from .image_parser import IMAGE_EXTENSIONS, parse_image
from .json_parser import parse_json, parse_jsonl
from .pdf_parser import parse_pdf
from .text_parser import parse_text
from .xlsx_parser import parse_xlsx

#: 扩展名 → 格式标识（与 `data/schema/product.schema.json` 的
#: `source.kind` 枚举一致）
EXTENSION_KIND = {
    ".xlsx": "xlsx",
    ".xlsm": "xlsx",
    ".csv": "csv",
    ".tsv": "csv",
    ".json": "json",
    ".jsonl": "jsonl",
    ".txt": "txt",
    ".md": "md",
    ".docx": "docx",
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".gif": "image",
    ".bmp": "image",
    ".tif": "image",
    ".tiff": "image",
}

#: 明确**不支持**的旧格式 —— 报明确错误，不静默跳过
UNSUPPORTED_EXTENSIONS = {
    ".xls": "legacy Excel (.xls) is not supported — export to XLSX or CSV first",
    ".xlb": "legacy Excel (.xlb) is not supported — export to XLSX or CSV first",
    ".ods": "OpenDocument (.ods) is not supported — export to XLSX or CSV first",
    ".rtf": "RTF is not supported — export to DOCX or plain text first",
    ".pages": "Apple Pages (.pages) is not supported — export to XLSX/DOCX/PDF first",
}


def detect_kind(path: str) -> str:
    """按扩展名识别格式。未知扩展名抛 `UnsupportedFormat`。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in UNSUPPORTED_EXTENSIONS:
        raise UnsupportedFormat(UNSUPPORTED_EXTENSIONS[ext],
                                {"path": path, "extension": ext})
    if ext in EXTENSION_KIND:
        return EXTENSION_KIND[ext]
    raise UnsupportedFormat(
        f"unsupported file format {ext or '(no extension)'} — supported: "
        + ", ".join(sorted(EXTENSION_KIND)),
        {"path": path, "extension": ext},
    )


def parse_file(path: str, options: dict | None = None) -> ParsedDocument:
    """识别格式并解析。格式级失败抛 `ParseError`。"""
    options = options or {}
    kind = detect_kind(path)
    if kind == "xlsx":
        return parse_xlsx(path, options)
    if kind == "csv":
        return parse_csv(path, options)
    if kind == "json":
        return parse_json(path, options)
    if kind == "jsonl":
        return parse_jsonl(path, options)
    if kind in ("txt", "md"):
        return parse_text(path, options)
    if kind == "docx":
        return parse_docx(path, options)
    if kind == "pdf":
        return parse_pdf(path, options)
    if kind == "image":
        return parse_image(path, options)
    raise UnsupportedFormat(f"no parser registered for format {kind!r}", {"path": path})


__all__ = [
    "EXTENSION_KIND",
    "IMAGE_EXTENSIONS",
    "UNSUPPORTED_EXTENSIONS",
    "ParseError",
    "ParsedDocument",
    "UnsupportedFormat",
    "detect_kind",
    "parse_file",
]
