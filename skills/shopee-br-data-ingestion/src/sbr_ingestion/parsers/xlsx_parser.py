"""XLSX / XLSM 解析（纯标准库：`zipfile` + `xml.etree.ElementTree`）。

无 openpyxl 依赖。直读 OOXML：

```
xl/workbook.xml           → sheet 名称与 r:id
xl/_rels/workbook.xml.rels→ r:id → 目标部件路径
xl/sharedStrings.xml      → 共享字符串表
xl/worksheets/sheetN.xml  → 单元格
```

单元格类型：

| `t` 属性 | 含义 |
|---|---|
| `s` | 共享字符串索引 |
| `inlineStr` | 内联字符串（`<is><t>`） |
| `str` | 公式结果字符串 |
| `b` | 布尔（`0`/`1`） |
| 缺省 | 数字 |

列号从 `r` 属性（如 `C7`）的字母部分解析；缺 `r` 时按出现顺序补列。
"""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET

from .base import ParseError, ParsedDocument
from .tabular import detect_header, scan_banner

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

_CELL_REF = re.compile(r"^([A-Za-z]+)(\d+)$")


def col_to_index(letters: str) -> int:
    """`A` → 0，`B` → 1，…… `AA` → 26。"""
    index = 0
    for ch in letters.upper():
        index = index * 26 + (ord(ch) - ord("A") + 1)
    return index - 1


def index_to_col(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def _read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        with zf.open("xl/sharedStrings.xml") as handle:
            data = handle.read()
    except KeyError:
        return []
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ParseError(f"sharedStrings.xml is not valid XML: {exc}") from exc
    strings = []
    for si in root.findall(f"{{{NS_MAIN}}}si"):
        parts = [t.text or "" for t in si.iter(f"{{{NS_MAIN}}}t")]
        strings.append("".join(parts))
    return strings


def _sheet_parts(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    """返回 `[(sheet 名, 部件路径)]`。"""
    try:
        with zf.open("xl/workbook.xml") as handle:
            wb_data = handle.read()
        with zf.open("xl/_rels/workbook.xml.rels") as handle:
            rel_data = handle.read()
    except KeyError as exc:
        raise ParseError(f"not a valid xlsx file (missing {exc.args[0]})") from exc

    try:
        wb_root = ET.fromstring(wb_data)
        rel_root = ET.fromstring(rel_data)
    except ET.ParseError as exc:
        raise ParseError(f"not a valid xlsx file (malformed XML): {exc}") from exc

    rels = {}
    for rel in rel_root.findall(f"{{{NS_PKG_REL}}}Relationship"):
        rid = rel.get("Id")
        target = rel.get("Target") or ""
        if not rid:
            continue
        if target.startswith("/"):
            target = target.lstrip("/")
        elif not target.startswith("xl/"):
            target = "xl/" + target
        rels[rid] = target

    sheets = []
    for index, sheet in enumerate(wb_root.iter(f"{{{NS_MAIN}}}sheet")):
        name = sheet.get("name") or f"sheet{index + 1}"
        rid = sheet.get(f"{{{NS_REL}}}id")
        target = rels.get(rid)
        if not target:
            # 回退：按序号猜路径
            target = f"xl/worksheets/sheet{index + 1}.xml"
        sheets.append((name, target))
    if not sheets:
        raise ParseError("not a valid xlsx file (no worksheet found)")
    return sheets


def _cell_value(cell: ET.Element, shared: list[str]):
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        node = cell.find(f"{{{NS_MAIN}}}is")
        if node is None:
            return ""
        return "".join(t.text or "" for t in node.iter(f"{{{NS_MAIN}}}t"))
    value_node = cell.find(f"{{{NS_MAIN}}}v")
    raw = value_node.text if value_node is not None else None
    if raw is None:
        return ""
    if cell_type == "s":
        try:
            return shared[int(raw)]
        except (ValueError, IndexError):
            return raw
    if cell_type == "b":
        return raw == "1"
    if cell_type in ("str", "e"):
        return raw
    try:
        number = float(raw)
    except ValueError:
        return raw
    if number.is_integer() and "." not in raw and "e" not in raw.lower():
        return int(number)
    return number


def _read_sheet(zf: zipfile.ZipFile, part: str, shared: list[str]) -> list[list]:
    try:
        with zf.open(part) as handle:
            data = handle.read()
    except KeyError as exc:
        raise ParseError(f"worksheet part {part} is missing from the package") from exc
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ParseError(f"worksheet {part} is not valid XML: {exc}") from exc

    rows: list[list] = []
    sheet_data = root.find(f"{{{NS_MAIN}}}sheetData")
    if sheet_data is None:
        return rows
    for row in sheet_data.findall(f"{{{NS_MAIN}}}row"):
        cells: dict[int, object] = {}
        next_index = 0
        for cell in row.findall(f"{{{NS_MAIN}}}c"):
            ref = cell.get("r") or ""
            match = _CELL_REF.match(ref)
            if match:
                col = col_to_index(match.group(1))
            else:
                col = next_index
            cells[col] = _cell_value(cell, shared)
            next_index = col + 1
        if not cells:
            rows.append([])
            continue
        width = max(cells) + 1
        rows.append([cells.get(i, "") for i in range(width)])
    return rows


def parse_xlsx(path: str, options: dict | None = None) -> ParsedDocument:
    """解析 XLSX / XLSM。"""
    options = options or {}
    try:
        zf = zipfile.ZipFile(path, "r")
    except zipfile.BadZipFile as exc:
        raise ParseError(f"not a valid xlsx (zip) file: {exc}", {"path": path}) from exc
    except OSError as exc:
        raise ParseError(f"cannot read file: {exc}", {"path": path}) from exc

    with zf:
        if "xl/workbook.xml" not in zf.namelist():
            raise ParseError("not a valid xlsx (zip) file: xl/workbook.xml is missing",
                             {"path": path})
        try:
            shared = _read_shared_strings(zf)
            sheets = _sheet_parts(zf)
        except ParseError:
            raise

        wanted = options.get("sheet")
        doc = ParsedDocument(kind="xlsx")
        doc.meta["sheets"] = [name for name, _ in sheets]

        for sheet_name, part in sheets:
            if wanted and sheet_name != wanted:
                continue
            try:
                rows = _read_sheet(zf, part, shared)
            except ParseError as exc:
                doc.add_error("warning", f"sheet {sheet_name!r} could not be read: {exc.message}",
                              {"sheet": sheet_name})
                continue
            doc.meta.setdefault("sheet_used", sheet_name)
            doc.meta.setdefault("row_count", len(rows))

            header_index, note = detect_header(rows)
            if header_index is None:
                doc.add_error(
                    "error",
                    f"no recognisable header row found in sheet {sheet_name!r}",
                    {"sheet": sheet_name, "row_count": len(rows)},
                )
                continue
            if note:
                doc.add_error("warning", f"sheet {sheet_name!r}: {note}",
                              {"sheet": sheet_name})

            headers = [str(c).strip() if c is not None else "" for c in rows[header_index]]
            doc.meta.setdefault("header_row", header_index + 1)
            doc.meta.setdefault("headers", headers)
            doc.meta.setdefault("sheet_name", sheet_name)
            banner = scan_banner(rows[:header_index])
            if banner:
                doc.meta.setdefault("banner", banner)

            for offset, row in enumerate(rows[header_index + 1:], start=1):
                excel_row = header_index + 1 + offset
                if not any(str(c).strip() for c in row if c is not None):
                    continue
                doc.records.append({"__row__": row, "__headers__": headers,
                                   "__sheet__": sheet_name})
                doc.locators.append(f"{sheet_name}!row {excel_row}")
            break  # 默认只取第一个可解析的工作表

        doc.meta["records_total"] = len(doc.records)
        return doc
