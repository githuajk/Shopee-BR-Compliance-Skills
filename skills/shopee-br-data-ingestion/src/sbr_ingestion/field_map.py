"""列名 → 规范字段的别名表与映射。

设计约束（`references/field_mapping.md`）：

* 别名覆盖 **中 / 葡 / 英** 三语。
* 归一化后比较；**存储保留原值**。
* **歧义别名不猜** —— 记 error，人工确认（`sku` / `codigo` / `ref` 等）。
* **未知列不丢弃** —— 落入 `attributes`。
* **必需列缺失** —— 该记录标记不完整并进 `errors[]`，**不静默跳过**。
"""

from __future__ import annotations

from .normalize import clean_text, normalize_key

#: 规范字段 → 别名列表（自然写法，导入时统一归一化）
FIELD_ALIASES: dict[str, list[str]] = {
    "product_id": [
        "product_id", "productid", "product id", "item_id", "itemid",
        "listing_id", "id_produto", "id do produto", "produto_id",
        "商品编号", "商品标识", "商品内部编号",
    ],
    "internal_sku": [
        "internal_sku", "internalsku", "internal sku", "sku_interno",
        "sku interno", "seller_sku", "sku do vendedor", "seller sku",
        "主商品货号", "商品货号", "货号", "主货号", "卖家货号",
    ],
    "supplier_sku": [
        "supplier_sku", "suppliersku", "supplier sku", "fornecedor_sku",
        "sku_fornecedor", "sku do fornecedor", "供应商货号", "供货商货号",
        "供应商sku",
    ],
    "shop_id": [
        "shop_id", "shopid", "shop id", "loja_id", "id_loja", "id da loja",
        "店铺id", "店铺 id", "店铺编号",
    ],
    "shop_name": [
        "shop_name", "shopname", "shop name", "nome_loja", "nome da loja",
        "loja", "店铺名", "店铺名称",
    ],
    "platform_pid": [
        "platform_pid", "platformpid", "platform pid", "pid",
        "shopee_product_id", "id_anuncio", "id do anuncio", "商品id",
        "商品 id", "平台商品id", "商品id平台",
    ],
    "title": [
        "title", "nome", "nome do produto", "nome_do_produto", "product name",
        "produto", "商品名称", "标题", "商品标题", "品名",
    ],
    "description": [
        "description", "descricao", "descrição do produto", "descricao do produto",
        "detalhes", "detalhe", "detalhado", "商品描述", "描述", "详情",
        "商品详情", "详情描述",
    ],
    "category": [
        "category", "categoria", "categoria do produto", "类目", "分类",
        "商品类目",
    ],
    "category_source": [
        "category_source", "categoria_origem", "类目来源", "类目来源方",
        "类目归属",
    ],
    "brand": [
        "brand", "marca", "marca do produto", "品牌", "品牌名",
    ],
    "model": [
        "model", "modelo", "型号", "型号名称", "产品型号",
    ],
    "price": [
        "price", "preco", "preço", "valor", "价格", "售价", "商品价格",
    ],
    "currency": [
        "currency", "moeda", "货币", "币种",
    ],
    "images": [
        "images", "image_urls", "image_url", "imagens", "图片", "图片链接",
        "图片url", "主图", "图片地址", "图片url列表",
    ],
    "variations": [
        "variations", "variacao", "variacoes", "变体", "规格", "规格名",
        "sku_variations",
    ],
    "product_url": [
        "product_url", "url", "link", "produto_url", "url do produto",
        "商品链接", "链接", "商品url",
    ],
    "case_ids": [
        "case_ids", "case_id", "casos", "caso_ids", "案件id", "历史案件",
        "关联案件",
    ],
    "notes": [
        "notes", "note", "observacao", "observações", "observacoes", "备注",
        "说明", "失败原因", "failure_reason", "motivo da falha",
    ],
}

#: 语义有歧义的裸别名 —— **不猜**，必须人工确认。
#: 历史上 `sku` 曾被误映射到 `product_id`，导致语义错误。
AMBIGUOUS_ALIASES: dict[str, list[str]] = {
    "sku": ["product_id", "internal_sku", "supplier_sku"],
    "codigo": ["product_id", "internal_sku"],
    "code": ["product_id", "internal_sku"],
    "ref": ["product_id", "internal_sku"],
    "referencia": ["product_id", "internal_sku"],
    "货号": ["product_id", "internal_sku", "supplier_sku"],
}

#: 规范字段的先后顺序（映射冲突时的优先级只用于展示，不用于猜测）
FIELD_ORDER = list(FIELD_ALIASES.keys())

#: `Product`（`data/schema/product.schema.json`）的必填字段
REQUIRED_FIELDS = ("product_id", "internal_sku", "shop_id", "title")

#: 会记录四态状态的可选字段
STATE_TRACKED_FIELDS = (
    "brand", "model", "category", "description", "price", "currency",
    "supplier_sku", "product_url", "images", "variations",
)


def _build_lookup() -> tuple[dict[str, str], dict[str, list[str]]]:
    lookup: dict[str, str] = {}
    ambiguous: dict[str, list[str]] = {}
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            key = normalize_key(alias)
            if not key:
                continue
            if key in lookup and lookup[key] != field:
                ambiguous.setdefault(key, [lookup[key]]).append(field)
                continue
            lookup[key] = field
    for alias, candidates in AMBIGUOUS_ALIASES.items():
        ambiguous[normalize_key(alias)] = list(candidates)
    return lookup, ambiguous


LOOKUP, AMBIGUOUS = _build_lookup()


def resolve_column(header: str) -> tuple[str | None, list[str]]:
    """解析单个列名。

    返回 `(field, candidates)`：

    * `field` 非 `None` —— 唯一命中的规范字段
    * `field` 为 `None` 且 `candidates` 非空 —— 歧义，需人工确认
    * `field` 为 `None` 且 `candidates` 为空 —— 未知列
    """
    key = normalize_key(header)
    if not key:
        return None, []
    if key in AMBIGUOUS:
        return None, list(AMBIGUOUS[key])
    field = LOOKUP.get(key)
    if field:
        return field, []
    return None, []


def map_columns(headers, row_values) -> dict:
    """把一行原始单元格映射成规范字段。

    返回 `dict`：

    * `data` —— 规范字段 → 原始值（未清洗）
    * `attributes` —— 未知列 → 原始值（**不丢弃**）
    * `ambiguous` —— `[{column, candidates}]`
    * `duplicate` —— `[{column, field}]`（同字段被多列命中）
    """
    data: dict = {}
    attributes: dict = {}
    ambiguous: list[dict] = []
    duplicate: list[dict] = []
    seen_fields: dict[str, str] = {}

    for index, header in enumerate(headers):
        raw_header = "" if header is None else str(header)
        if not raw_header.strip():
            continue
        value = row_values[index] if index < len(row_values) else None
        field, candidates = resolve_column(raw_header)
        if field:
            if field in seen_fields:
                duplicate.append({"column": raw_header, "field": field,
                                  "first_column": seen_fields[field]})
                continue
            seen_fields[field] = raw_header
            data[field] = value
        elif candidates:
            ambiguous.append({"column": raw_header, "candidates": candidates})
            attributes[raw_header] = value
        else:
            attributes[raw_header] = value
    return {"data": data, "attributes": attributes,
            "ambiguous": ambiguous, "duplicate": duplicate}


def coerce_attribute(value):
    """把未知列的原始值转成 `attributes` 允许的类型。

    `data/schema/product.schema.json` 的 `attributes` 允许
    `string | number | boolean | null`。
    """
    text = clean_text(value)
    if text is None:
        return None
    lowered = text.casefold()
    if lowered in ("true", "false"):
        return lowered == "true"
    try:
        if text.lstrip("+-").replace(".", "", 1).isdigit():
            return float(text) if ("." in text) else int(text)
    except ValueError:  # pragma: no cover - 防御
        pass
    return text
