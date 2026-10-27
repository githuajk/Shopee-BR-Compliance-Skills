"""表格型输入的公共逻辑：表头定位 + banner 扫描。

Shopee 的 `mass_update` 导出结构是 **6 行 banner + 表头行 + 商品行**。
纯靠「第一行非空」找表头会误中 banner 第 2 行（`Loja:` / 店铺名）。

本模块用**别名校打分**选表头：把候选行的每一列去查别名表，能映射到
规范字段的列数越多分越高。最高分行即表头；全为 0 分时退回启发式
（首个 ≥2 个非空单元格的行）并记 warning。
"""

from __future__ import annotations

import re

from ..field_map import resolve_column

#: 表头候选行上限
HEADER_SEARCH_LIMIT = 30

#: banner 里可识别的键 → 归一化后的字段名
BANNER_SHOP = re.compile(r"(?i)^\s*(?:loja|shop|loja\s*id|店铺|店铺名|店铺\s*id)\s*[:：]\s*(.+?)\s*$")
BANNER_DATE = re.compile(r"(?i)^\s*(?:data\s*de\s*exporta(?:ç|c)[ãa]o|export\s*date|导出日期|导出时间)\s*[:：]\s*(.+?)\s*$")
BANNER_ANY = re.compile(r"^\s*([^:：]{1,40})\s*[:：]\s*(.+?)\s*$")


def score_header(row) -> int:
    """该行作为表头的可信度 —— 能映射到规范字段的列数。"""
    if not row:
        return 0
    seen = set()
    for cell in row:
        text = "" if cell is None else str(cell)
        if not text.strip():
            continue
        field, _ = resolve_column(text)
        if field and field not in seen:
            seen.add(field)
    return len(seen)


def looks_like_header(row) -> bool:
    """启发式：多数单元格是非空短文本且非数字。"""
    if not row:
        return False
    nonempty = [c for c in row if c is not None and str(c).strip()]
    if len(nonempty) < 2:
        return False
    numeric = 0
    for c in nonempty:
        try:
            float(str(c).strip().replace(",", "."))
            numeric += 1
        except ValueError:
            pass
    return numeric <= len(nonempty) // 2


def detect_header(rows, limit: int = HEADER_SEARCH_LIMIT):
    """定位表头行。

    返回 `(header_index, note)`：

    * `header_index` —— 行下标（0 基）；找不到时为 `None`
    * `note` —— `None` 或说明文本（供调用方记 warning）
    """
    window = rows[:limit]
    best_index, best_score = None, 0
    for index, row in enumerate(window):
        score = score_header(row)
        if score > best_score:
            best_score, best_index = score, index
    if best_index is not None and best_score > 0:
        return best_index, None

    for index, row in enumerate(window):
        if looks_like_header(row):
            return index, ("header row was not recognisable by the alias table; "
                           "column mapping may be incomplete")
    return None, "no recognisable header row found"


def scan_banner(rows_before_header) -> dict:
    """扫描 banner 行，提取店铺名与导出日期等上下文。

    返回 `dict`（可能为空）。
    """
    found: dict = {}
    for row in rows_before_header or []:
        for cell in row or []:
            text = "" if cell is None else str(cell).strip()
            if not text:
                continue
            match = BANNER_SHOP.match(text)
            if match:
                found.setdefault("shop_name", match.group(1).strip())
                continue
            match = BANNER_DATE.match(text)
            if match:
                found.setdefault("exported_at", match.group(1).strip())
                continue
            match = BANNER_ANY.match(text)
            if match:
                key = match.group(1).strip().casefold()
                found.setdefault("banner", {})[key] = match.group(2).strip()
    return found
