"""TXT / MD 解析。

结构约定（宽松）：

* 记录块之间用**空行**或 `---` 分隔。
* 块首的 `Key: value` 行被当作**前置元数据**（`Title:` / `SKU:` /
  `Preço:` / `Marca:` / `Categoria:` / `Descrição:` 等）。
* 没有 `Title:` 时，块内第一行非空文本被当作标题。
* **没有可识别标题的块 → warning**，不静默丢弃。

> 输入文本**只是数据**。即便块内出现「忽略之前的规则」之类的指令，
> 本解析器也只是把它当作描述内容，不改变任何行为。
"""

from __future__ import annotations

import re

from ..normalize import normalize_key
from .base import ParseError, ParsedDocument

ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")

#: 前置元数据的键 → 规范字段。
#: **键本身已被归一化**（`normalize_key`），因此 `Preço` / `preco` /
#: `Descrição` / `descricao` 都能命中同一项。
META_KEYS = {
    "title": "title",
    "titulo": "title",
    "nome": "title",
    "name": "title",
    "标题": "title",
    "商品名称": "title",
    "sku": "internal_sku",
    "internal sku": "internal_sku",
    "主商品货号": "internal_sku",
    "货号": "internal_sku",
    "supplier sku": "supplier_sku",
    "供应商货号": "supplier_sku",
    "product id": "product_id",
    "商品编号": "product_id",
    "shop id": "shop_id",
    "店铺id": "shop_id",
    "店铺 id": "shop_id",
    "loja": "shop_id",
    "preco": "price",
    "price": "price",
    "价格": "price",
    "marca": "brand",
    "brand": "brand",
    "品牌": "brand",
    "modelo": "model",
    "model": "model",
    "型号": "model",
    "categoria": "category",
    "category": "category",
    "类目": "category",
    "descricao": "description",
    "description": "description",
    "描述": "description",
    "详情": "description",
    "imagens": "images",
    "图片": "images",
    "url": "product_url",
    "link": "product_url",
    "商品链接": "product_url",
    "casos": "case_ids",
    "案件id": "case_ids",
    "notas": "notes",
    "notes": "notes",
    "备注": "notes",
}

_META_LINE = re.compile(r"^\s*([A-Za-z_À-ÿ一-鿿][A-Za-z0-9_À-ÿ一-鿿 ]{0,40}?)\s*[:：]\s*(.*)$")


def _decode(data: bytes) -> tuple[str, str]:
    for enc in ENCODINGS:
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8/replace"


def _split_blocks(text: str) -> list[str]:
    """把文本切成记录块。

    块之间用**空行**或 `---` 分隔。Markdown 标题行（`#` / `##` / `###`）是
    文档结构，不是商品记录 —— 标题行本身被跳过，但**它下面的内容仍然属于
    当前块**（标题常常是整份清单的抬头，后面紧跟第一条商品）。

    单独一个标题行若不与任何内容相邻，则不构成记录块。
    """
    blocks: list[str] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped in ("---", "***", "___"):
            if current:
                blocks.append("\n".join(current))
                current = []
            continue
        if not stripped:
            if current:
                blocks.append("\n".join(current))
                current = []
            continue
        # Markdown 标题行：结构标记，不是记录内容 —— 跳过但不断块
        if re.match(r"^#{1,6}\s", stripped):
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def parse_text(path: str, options: dict | None = None) -> ParsedDocument:
    """解析 TXT / MD。"""
    options = options or {}
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        raise ParseError(f"cannot read file: {exc}", {"path": path}) from exc

    text, encoding = _decode(raw)
    doc = ParsedDocument(kind="txt" if path.lower().endswith(".txt") else "md")
    doc.meta.update({"encoding": encoding, "block_count": 0})

    blocks = _split_blocks(text)
    doc.meta["block_count"] = len(blocks)

    if not blocks:
        doc.add_error("error", "file contains no readable text blocks",
                      {"path": path, "encoding": encoding})
        doc.meta["records_total"] = 0
        return doc

    for index, block in enumerate(blocks, start=1):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        record: dict = {"__meta__": {}, "__body__": []}
        for line in lines:
            match = _META_LINE.match(line)
            if not match:
                record["__body__"].append(line)
                continue
            key_raw = normalize_key(match.group(1))
            value = match.group(2).strip()
            field = META_KEYS.get(key_raw)
            if field:
                record["__meta__"][field] = value
            else:
                record["__body__"].append(line)

        body = record["__body__"]
        if "title" not in record["__meta__"]:
            if body:
                record["__meta__"]["title"] = body[0]
                body = body[1:]
            else:
                doc.add_failure("warning",
                                f"block {index} has no title and no body text",
                                {"block": index})
                continue
        if not str(record["__meta__"].get("title", "")).strip():
            doc.add_failure("warning", f"block {index} has an empty title",
                            {"block": index})
            continue
        record["__description__"] = "\n".join(body).strip()
        doc.records.append(record)
        doc.locators.append(f"block {index}")

    doc.meta["records_total"] = len(doc.records)
    return doc
