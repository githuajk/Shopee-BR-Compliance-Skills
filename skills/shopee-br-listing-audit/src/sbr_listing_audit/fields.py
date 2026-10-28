"""字段取与「存在但为空」的判定。

`PROJECT_RULES.md` §11.1 规定四种字段状态，其中 `missing`（本次无数据）
在类型化字段上表现为 `null` / 空串 / 空数组 / 空对象。**空值等同于缺失**，
这是硬约束 H3（输入缺失不等于合规）的判定基础。

字段取值语义与 `tools/verify_fixtures.py` 的 `get_field()` **完全一致** ——
共享夹具的 `must_fire` / `must_not_fire` / `must_be_unevaluated` 声明就是
本模块的判定契约，两处语义必须相同，否则夹具与模块会各说各话。
"""

from __future__ import annotations

#: `data/schema/rule.schema.json` 允许的字段枚举。
FIELDS = (
    "title",
    "description",
    "attributes",
    "category",
    "brand",
    "model",
    "price",
    "image",
    "image_text",
    "variations",
    "seller_name",
    "supplier_sku",
    "shop_id",
    "product_url",
    "history",
    "any_text",
)


def is_empty(value) -> bool:
    """空值判定。**存在但为空 == 缺失**（`PROJECT_RULES.md` §11.1）。

    * `None` → 缺失
    * 字符串 → 去空白后为空即缺失
    * 列表 / 元组 / 字典 / 集合 → 长度为 0 即缺失
    * 数字 `0` / `False` → **不是**缺失（0 是有效取值）
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def any_text(product: dict) -> str:
    """标题 + 详情 + 品牌 + 类目 + 型号 + 图片 OCR 的合并文本。

    词库与正则规则作用在**全部可见文案**上：标题仅约 6% 命中，详情约 94%
    （见 `references/lexicon_scanning.md` §3.3）。
    """
    parts = [
        product.get("title") or "",
        product.get("description") or "",
        product.get("brand") or "",
        product.get("category") or "",
        product.get("model") or "",
    ]
    for image in product.get("images") or []:
        if isinstance(image, dict) and image.get("ocr_text"):
            parts.append(image["ocr_text"])
    return "\n".join(part for part in parts if part)


def get_field(product: dict, field: str):
    """按 `data/schema/rule.schema.json` 的字段枚举取值。

    未知字段一律返回 `None`（= 缺失），**不猜测**。
    """
    if field == "title":
        return product.get("title")
    if field == "description":
        return product.get("description")
    if field == "attributes":
        return product.get("attributes")
    if field == "category":
        return product.get("category")
    if field == "brand":
        return product.get("brand")
    if field == "model":
        return product.get("model")
    if field == "price":
        return product.get("price")
    if field == "image":
        return product.get("images")
    if field == "image_text":
        texts = [i.get("ocr_text") or "" for i in product.get("images") or []
                 if isinstance(i, dict)]
        return " \n".join(text for text in texts if text)
    if field == "variations":
        return product.get("variations")
    if field == "seller_name":
        return product.get("shop_name")
    if field == "supplier_sku":
        return product.get("supplier_sku")
    if field == "shop_id":
        return product.get("shop_id")
    if field == "product_url":
        return product.get("product_url")
    if field == "history":
        return product.get("history")
    if field == "any_text":
        return any_text(product)
    return None
