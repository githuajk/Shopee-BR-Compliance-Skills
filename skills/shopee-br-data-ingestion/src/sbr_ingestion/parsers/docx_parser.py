"""DOCX 解析（纯标准库：`zipfile` + `xml.etree.ElementTree`）。

读取 `word/document.xml`：

* 段落（`<w:p>`）→ 文本行
* 表格（`<w:tbl>`）→ 首个表格按首行当表头、其余行当记录

复杂排版（浮动文本框、嵌入对象）会丢失 —— 记 warning。
"""

from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET

from .base import ParseError, ParsedDocument

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _cell_text(cell: ET.Element) -> str:
    parts = [t.text or "" for t in cell.iter(f"{{{NS_W}}}t")]
    return "".join(parts).strip()


def _row_cells(row: ET.Element) -> list[str]:
    return [_cell_text(tc) for tc in row.findall(f"{{{NS_W}}}tc")]


def parse_docx(path: str, options: dict | None = None) -> ParsedDocument:
    """解析 DOCX。"""
    options = options or {}
    try:
        zf = zipfile.ZipFile(path, "r")
    except zipfile.BadZipFile as exc:
        raise ParseError(f"not a valid docx (zip) file: {exc}", {"path": path}) from exc
    except OSError as exc:
        raise ParseError(f"cannot read file: {exc}", {"path": path}) from exc

    with zf:
        if "word/document.xml" not in zf.namelist():
            raise ParseError("not a valid docx (zip) file: word/document.xml is missing",
                             {"path": path})
        try:
            with zf.open("word/document.xml") as handle:
                data = handle.read()
        except KeyError as exc:  # pragma: no cover - 上面的检查已覆盖
            raise ParseError(f"not a valid docx (zip) file: {exc}") from exc
        try:
            root = ET.fromstring(data)
        except ET.ParseError as exc:
            raise ParseError(f"not a valid docx (zip) file (malformed XML): {exc}") from exc

    doc = ParsedDocument(kind="docx")
    body = root.find(f"{{{NS_W}}}body")
    if body is None:
        doc.add_error("error", "docx body element is missing", {"path": path})
        return doc

    table_count = 0
    paragraph_lines: list[str] = []
    for child in body:
        tag = child.tag.split("}")[-1]
        if tag == "p":
            text = "".join(t.text or "" for t in child.iter(f"{{{NS_W}}}t")).strip()
            if text:
                paragraph_lines.append(text)
        elif tag == "tbl":
            table_count += 1
            rows = child.findall(f"{{{NS_W}}}tr")
            if not rows:
                continue
            headers = _row_cells(rows[0])
            for offset, row in enumerate(rows[1:], start=1):
                cells = _row_cells(row)
                if not any(cells):
                    continue
                doc.records.append({"__row__": cells, "__headers__": headers,
                                   "__sheet__": f"table{table_count}"})
                doc.locators.append(f"table {table_count} row {offset + 1}")

    doc.meta["table_count"] = table_count
    doc.meta["paragraph_count"] = len(paragraph_lines)

    if not doc.records:
        # 没有表格：把段落按空行分块，当作自由文本记录
        blocks, current = [], []
        for line in paragraph_lines:
            current.append(line)
        if current:
            blocks.append("\n".join(current))
        for index, block in enumerate(blocks, start=1):
            doc.records.append({"__meta__": {}, "__body__": [block],
                                "__description__": block})
            doc.locators.append(f"paragraph {index}")
        if not doc.records:
            doc.add_error("warning",
                          "docx contains no paragraphs and no table rows",
                          {"path": path})
        else:
            doc.add_error("warning",
                          "docx has no tables; paragraphs were taken as free text "
                          "and need manual field mapping",
                          {"paragraph_count": len(paragraph_lines)})

    doc.meta["records_total"] = len(doc.records)
    return doc
