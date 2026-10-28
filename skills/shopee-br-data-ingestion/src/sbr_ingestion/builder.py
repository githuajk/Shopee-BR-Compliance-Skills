"""原始记录 → `Product`（`data/schema/product.schema.json`）。

关键规则（`references/field_mapping.md` §3）：

* **保留原值** —— 规范化只用于比较，存储用原文。
* **未知列不丢弃** —— 进 `attributes`。
* **歧义别名不猜** —— 记 error 并等人工确认。
* **必需字段缺失** —— 该记录标记不完整并进 `errors[]`，**不静默跳过**。
* **四态语义** —— 字段存在但本次无数据 → `missing`（`null`）；
  值存在但无法确定 → `unknown`；该对象无此概念 → `not_applicable`；
  待外部确认 → `pending_verification`。

标识符的补全顺序（**可追溯**，全部记 warning）：

| 字段 | 顺序 |
|---|---|
| `product_id` | 显式列 → `SBRP-<shop_id>-<platform_pid>` → `SBRP-<shop_id>-<internal_sku>` → 缺失报错 |
| `shop_id` | 显式列 → `options.default_shop_id` → banner 店铺名（slug）→ 缺失报错 |
"""

from __future__ import annotations

import hashlib
import re

from .errors import (
    merge_field_states,
    state_missing,
    state_not_applicable,
    state_pending_verification,
    state_unknown,
)
from .field_map import coerce_attribute, map_columns
from .normalize import (
    clean_text,
    collapse_whitespace,
    parse_number,
    split_list,
    truncate,
)

#: `title` 的最大长度（`data/schema/product.schema.json`）
TITLE_MAX = 200

#: `description` 的最大长度（超出部分截断并记 warning）
DESCRIPTION_MAX = 8000

#: 属性名的最大长度
ATTRIBUTE_KEY_MAX = 80

#: `product_id` 的最小长度（契约要求 ≥ 4）
PRODUCT_ID_MIN = 4

_SLUG_CLEAN = re.compile(r"[^0-9A-Za-z\-]+")

#: 记录预览里每个字段的最大长度
PREVIEW_FIELD_MAX = 80

#: 记录预览里最多展示的字段数
PREVIEW_FIELDS_MAX = 8


def slugify(text: str) -> str:
    """把任意文本压成安全的 ID 片段。"""
    cleaned = _SLUG_CLEAN.sub("-", text.strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned[:48]


def _preview(data: dict) -> dict:
    """记录的可读预览 —— 用于让「解析失败」的具体内容可见。

    只截断长度，不改写内容：预览的目的是让人能核对「读到的到底是什么」，
    例如编码回退是否正确把 cp1252 的 `ç` 解成了 `ç` 而不是乱码。
    """
    if not isinstance(data, dict):
        return {}
    out: dict = {}
    for key, value in list(data.items())[:PREVIEW_FIELDS_MAX]:
        if value is None:
            continue
        text = value if isinstance(value, str) else str(value)
        if len(text) > PREVIEW_FIELD_MAX:
            text = text[:PREVIEW_FIELD_MAX] + "…"
        out[str(key)] = text
    return out


def _record_to_mapping(record: dict) -> dict:
    """把解析器产出的记录统一成 `{column: value}` 形态。

    * 表格型记录（`__row__` + `__headers__`）→ 按列名成对
    * JSON / JSONL 记录 → 原样
    * 自由文本记录（`__meta__` + `__body__`）→ 元数据 + 正文
    """
    if "__row__" in record:
        headers = record.get("__headers__") or []
        row = _row_to_cells(record.get("__row__") or [], headers)
        return {str(h): (row[i] if i < len(row) else None)
                for i, h in enumerate(headers) if h is not None and str(h).strip()}
    if "__meta__" in record:
        merged = dict(record.get("__meta__") or {})
        body = record.get("__body__") or []
        description = record.get("__description__")
        if description is None:
            description = "\n".join(body)
        if description:
            merged.setdefault("description", description)
        return merged
    return dict(record)


def _row_to_cells(row, headers) -> list:
    """把一行原始单元格对齐到表头宽度。

    pt-BR 的 CSV 常用 `,` 作小数分隔符（`349,90`）。当分隔符也是 `,`
    时，一行会被切出**多于表头**的格子。此时把多出来的尾部格子用
    `,` 重新拼回最后一列 —— 否则价格会被切成 `349` 与 `90` 两列，
    静默丢掉小数部分。
    """
    row = list(row)
    if len(row) <= len(headers):
        return row
    overflow = len(row) - len(headers)
    tail = ",".join(str(c) for c in row[len(headers) - overflow:])
    return row[:len(headers) - 1] + [tail]


def _build_images(value) -> list[dict]:
    """把图片列规范成 `images[]`。

    * 列表（JSON 里的图片对象数组）→ 逐项补齐缺失键
    * 文本（URL 列表）→ 每项一个占位图片记录
    """
    images: list[dict] = []
    if isinstance(value, list):
        for index, item in enumerate(value, start=1):
            if not isinstance(item, dict):
                text = clean_text(item)
                if not text:
                    continue
                images.append({
                    "image_id": f"img-{index}",
                    "url": text if text.lower().startswith(("http://", "https://")) else None,
                    "local_path": None if text.lower().startswith(("http://", "https://")) else text,
                    "ocr_text": None,
                    "detected_logos": [],
                    "watermark": None,
                })
                continue
            url = clean_text(item.get("url"))
            local = clean_text(item.get("local_path"))
            ocr = clean_text(item.get("ocr_text"))
            logos = item.get("detected_logos")
            watermark = item.get("watermark")
            images.append({
                "image_id": clean_text(item.get("image_id")) or f"img-{index}",
                "url": url,
                "local_path": local,
                "ocr_text": ocr,
                "detected_logos": [str(x) for x in logos] if isinstance(logos, list) else [],
                "watermark": watermark if isinstance(watermark, bool) else None,
            })
        return images

    for index, raw in enumerate(split_list(value), start=1):
        text = clean_text(raw)
        if not text:
            continue
        is_url = text.lower().startswith(("http://", "https://"))
        images.append({
            "image_id": f"img-{index}",
            "url": text if is_url else None,
            "local_path": None if is_url else text,
            "ocr_text": None,
            "detected_logos": [],
            "watermark": None,
        })
    return images


def _build_variations(value) -> list[dict]:
    """把变体列规范成 `variations[]`。

    * 列表（JSON 里的变体对象数组）→ 逐项补齐缺失键
    * 文本（`变体名: 选项1|选项2`）→ 解析
    """
    variations: list[dict] = []
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            name = clean_text(item.get("name"))
            options = item.get("options")
            option_list = [str(o) for o in options] if isinstance(options, list) else []
            if not name or not option_list:
                continue
            variations.append({"name": name, "options": option_list})
        return variations

    text = clean_text(value)
    if not text:
        return []
    for chunk in split_list(text):
        normalized = chunk.replace("：", ":")
        if ":" not in normalized:
            continue
        name, _, options_text = normalized.partition(":")
        options = [o.strip() for o in split_list(options_text) if o.strip()]
        if not name.strip() or not options:
            continue
        variations.append({"name": name.strip(), "options": options})
    return variations


def build_product(record: dict, context: dict) -> tuple[dict | None, list[dict]]:
    """把一条原始记录转换成 `Product`。

    返回 `(product, issues)`：

    * `product` —— 成功时是完整的 `Product`；失败时 `None`
    * `issues` —— `[{severity, message, context}]`，供调用方写进 `errors[]`
    """
    issues: list[dict] = []
    mapping = _record_to_mapping(record)
    mapped = map_columns(list(mapping.keys()), list(mapping.values()))
    data = mapped["data"]

    for item in mapped["ambiguous"]:
        issues.append({
            "severity": "warning",
            "message": (f"column {item['column']!r} is ambiguous "
                        f"({', '.join(item['candidates'])}); the value was kept in "
                        f"attributes and NOT mapped to a canonical field"),
            "context": {"column": item["column"], "candidates": item["candidates"]},
        })
    for item in mapped["duplicate"]:
        issues.append({
            "severity": "warning",
            "message": (f"column {item['column']!r} maps to {item['field']!r} which was "
                        f"already filled by {item['first_column']!r}; the duplicate was dropped"),
            "context": {"column": item["column"], "field": item["field"]},
        })

    attributes: dict = {}
    for key, value in mapped["attributes"].items():
        safe_key = str(key).strip()[:ATTRIBUTE_KEY_MAX]
        attributes[safe_key] = coerce_attribute(value)

    # --- 标识 ---
    product_id = clean_text(data.get("product_id"))
    internal_sku = clean_text(data.get("internal_sku"))
    shop_id = clean_text(data.get("shop_id"))
    title = clean_text(data.get("title"))
    platform_pid = clean_text(data.get("platform_pid"))
    shop_name = clean_text(data.get("shop_name")) or context.get("shop_name")

    missing: list[str] = []

    derived: list[str] = []

    if not shop_id:
        default_shop = context.get("default_shop_id")
        if default_shop:
            shop_id = default_shop
            derived.append(f"shop_id={default_shop!r} (default applied)")
        elif shop_name:
            shop_id = slugify(shop_name)
            derived.append(f"shop_id={shop_id!r} (derived from the shop name)")
        else:
            missing.append("shop_id")

    if not product_id:
        if shop_id and platform_pid:
            product_id = f"SBRP-{slugify(shop_id)}-{slugify(platform_pid)}"
            derived.append(f"product_id={product_id!r} (derived from shop_id + platform_pid)")
        elif shop_id and internal_sku:
            product_id = f"SBRP-{slugify(shop_id)}-{slugify(internal_sku)}"
            derived.append(f"product_id={product_id!r} (derived from shop_id + internal_sku)")
        elif shop_id and title:
            digest = hashlib.sha256(title.encode("utf-8")).hexdigest()[:10]
            product_id = f"SBRP-{slugify(shop_id)}-{digest}"
            derived.append(
                f"product_id={product_id!r} (derived from shop_id + a content hash of the title)")
        else:
            missing.append("product_id")

    if not internal_sku:
        if product_id:
            internal_sku = product_id
            derived.append(
                f"internal_sku={internal_sku!r} (no seller SKU in the source; "
                f"the stable product id is used instead)")
        else:
            missing.append("internal_sku")

    if not title:
        missing.append("title")

    if missing:
        issues.append({
            "severity": "error",
            "message": (f"record is missing required field(s): {', '.join(missing)}; "
                        f"the record was NOT dropped silently — it is reported here"),
            "context": {
                "missing_fields": missing,
                "locator": context.get("locator"),
                # 记录预览：让「无法解析」的具体内容可见 —— 也让编码回退
                # 是否正确（如 cp1252 的重音字符）可被直接核对。
                "record_preview": _preview(data),
            },
        })
        return None, issues

    if len(product_id) < PRODUCT_ID_MIN:
        synthesized = f"SBRP-{slugify(shop_id)}-{slugify(internal_sku)}-{slugify(product_id)}"
        derived.append(f"product_id={synthesized!r} (too short; synthetic id used)")
        product_id = synthesized

    if derived:
        issues.append({
            "severity": "warning",
            "message": ("identifier(s) were not present in the record and were "
                        "derived deterministically: " + "; ".join(derived)),
            "context": {"locator": context.get("locator"), "derived": derived},
        })

    # --- 文本字段 ---
    description = clean_text(data.get("description"))
    if description:
        description = collapse_whitespace(description)
    if description and len(description) > DESCRIPTION_MAX:
        description = description[:DESCRIPTION_MAX]
        issues.append({
            "severity": "warning",
            "message": f"description exceeded {DESCRIPTION_MAX} characters and was truncated",
            "context": {"locator": context.get("locator")},
        })

    if title and len(title) > TITLE_MAX:
        title = title[:TITLE_MAX]
        issues.append({
            "severity": "warning",
            "message": f"title exceeded {TITLE_MAX} characters and was truncated",
            "context": {"locator": context.get("locator")},
        })

    history: dict = {}

    brand = clean_text(data.get("brand"))
    if brand is None:
        merge_field_states(history, "brand", state_missing())
    else:
        merge_field_states(history, "brand", state_pending_verification(
            assigned_to="shopee-br-listing-audit",
            due=None,
            reason="brand value came from the seller; platform-side verification pending",
        ))

    category = clean_text(data.get("category"))
    if category is None:
        merge_field_states(history, "category", state_missing())
    else:
        source = clean_text(data.get("category_source"))
        merge_field_states(history, "category", state_pending_verification(
            assigned_to="shopee-br-listing-audit",
            due=None,
            reason=f"category path as published (declared by {source or 'unknown'})",
        ))

    if description is None:
        merge_field_states(history, "description", state_missing())
    else:
        merge_field_states(history, "description", state_pending_verification(
            assigned_to="shopee-br-listing-audit",
            due=None,
            reason="description imported; length/content rules pending evaluation",
        ))

    # --- 价格 ---
    price = None
    currency = clean_text(data.get("currency")) or context.get("default_currency") or "BRL"
    raw_price = data.get("price")
    if raw_price is None:
        merge_field_states(history, "price", state_missing())
    else:
        number, ambiguous = parse_number(raw_price)
        if number is None:
            merge_field_states(history, "price", state_unknown(
                f"price value {raw_price!r} could not be interpreted as a number"))
            issues.append({
                "severity": "warning",
                "message": f"price {raw_price!r} could not be interpreted as a number",
                "context": {"locator": context.get("locator"), "raw": raw_price},
            })
        else:
            price = number
            if ambiguous:
                merge_field_states(history, "price", state_pending_verification(
                    assigned_to="shopee-br-data-ingestion",
                    due=None,
                    reason=f"price {raw_price!r} uses an ambiguous thousands separator",
                ))
                issues.append({
                    "severity": "warning",
                    "message": (f"price {raw_price!r} has an ambiguous separator; "
                                f"interpreted as {number}"),
                    "context": {"locator": context.get("locator"), "raw": raw_price},
                })
            else:
                merge_field_states(history, "price", state_pending_verification(
                    assigned_to="shopee-br-listing-audit",
                    due=None,
                    reason="price parsed successfully",
                ))

    # --- 图片 / 变体 ---
    images = _build_images(data.get("images"))
    if not images:
        merge_field_states(history, "images", state_missing())
    else:
        merge_field_states(history, "images", state_pending_verification(
            assigned_to="shopee-br-ip-review",
            due=None,
            reason="image URLs were imported; OCR and logo detection not performed",
        ))

    variations = _build_variations(data.get("variations"))
    if not variations:
        merge_field_states(history, "variations", state_missing())
    else:
        merge_field_states(history, "variations", state_pending_verification(
            assigned_to="shopee-br-duplicate-detection",
            due=None,
            reason="variation structure parsed from the input",
        ))

    model = clean_text(data.get("model"))
    if model is None:
        merge_field_states(history, "model", state_missing())

    supplier_sku = clean_text(data.get("supplier_sku"))
    if supplier_sku is None:
        merge_field_states(history, "supplier_sku", state_missing())

    product_url = clean_text(data.get("product_url"))
    if product_url is None:
        merge_field_states(history, "product_url", state_missing())

    # --- 结构化的附加数据（JSON 里的 history / case_ids 等）---
    extra = {k: v for k, v in record.items() if not k.startswith("__")}
    for key in ("history", "case_ids"):
        if key in extra:
            history.setdefault(key, extra.pop(key))
    for key, value in extra.items():
        if key in data or key in attributes:
            continue
        if isinstance(value, (dict, list)):
            history.setdefault(key, value)
        else:
            attributes.setdefault(str(key)[:ATTRIBUTE_KEY_MAX], coerce_attribute(value))

    case_ids = split_list(data.get("case_ids"))
    if case_ids:
        history.setdefault("case_ids", case_ids)

    notes = clean_text(data.get("notes"))

    product = {
        "product_id": product_id,
        "internal_sku": internal_sku,
        "shop_id": shop_id,
        "title": title,
        "description": description or "",
        "attributes": attributes,
        "category": category,
        "category_declared_by": _category_declared_by(data),
        "brand": brand,
        "model": model,
        "price": price,
        "currency": currency,
        "images": images,
        "variations": variations,
        "product_url": product_url,
        "history": history,
        "case_ids": case_ids,
        "source": {
            "kind": context.get("kind", "manual"),
            "path": context.get("path"),
            "imported_at": context.get("imported_at"),
            "raw_ref": context.get("locator"),
        },
    }
    if shop_name:
        product["shop_name"] = shop_name
    if supplier_sku:
        product["supplier_sku"] = supplier_sku
    if platform_pid:
        product["platform_pid"] = platform_pid
    if notes:
        product["notes"] = notes

    return product, issues


def _category_declared_by(data: dict) -> str:
    """类目来源方。无法判定时返回 `unknown`（契约默认值）。"""
    raw = clean_text(data.get("category_source"))
    if raw:
        folded = raw.casefold()
        if folded in ("platform", "plataforma", "平台"):
            return "platform"
        if folded in ("seller", "vendedor", "卖家"):
            return "seller"
    return "unknown"


def build_products(records, contexts) -> tuple[list[dict], list[dict], list[dict]]:
    """批量转换。

    返回 `(products, failed, issues)`：

    * `products` —— 成功的 `Product` 列表
    * `failed` —— `[{locator, missing_fields}]`，缺失必填字段的记录
    * `issues` —— 全部记录级问题（含成功记录上的 warning）
    """
    products: list[dict] = []
    failed: list[dict] = []
    issues: list[dict] = []

    for record, context in zip(records, contexts):
        product, record_issues = build_product(record, context)
        issues.extend(record_issues)
        if product is not None:
            products.append(product)
        else:
            missing: list[str] = []
            for item in record_issues:
                if item["severity"] == "error":
                    missing = item.get("context", {}).get("missing_fields", missing)
            failed.append({"locator": context.get("locator"), "missing_fields": missing})

    return products, failed, issues
