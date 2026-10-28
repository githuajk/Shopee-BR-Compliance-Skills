"""图片解析（登记为待 OCR / 待视觉分析）。

图片**不产生商品数据**。本模块登记一条待办记录：

* `images[]` 里放 `{image_id, local_path, url, ocr_text: null,
  detected_logos: [], watermark: null}`
* `ocr_text` / `detected_logos` 留空 —— **不猜**图片里有什么。

> `data/schema/product.schema.json` 的 `images[].ocr_text` 允许 `null`，
> `detected_logos` 允许 `[]` —— 这里用「显式未评估」而不是伪造内容。
> 下游的 IP 模块据此把图片类规则记为**未评估**（硬约束 H3），
> 而不是「没查到 logo 就当通过」。
"""

from __future__ import annotations

import os

from .base import ParseError, ParsedDocument

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff")


def parse_image(path: str, options: dict | None = None) -> ParsedDocument:
    """登记图片为待 OCR / 待视觉分析。"""
    options = options or {}
    doc = ParsedDocument(kind="image")
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        raise ParseError(f"cannot read file: {exc}", {"path": path}) from exc

    doc.meta["size_bytes"] = size
    doc.meta["needs"] = ["ocr", "visual_analysis"]
    doc.records.append({
        "__meta__": {},
        "__body__": [],
        "__description__": "",
        "__image__": {
            "image_id": os.path.basename(path),
            "local_path": path,
            "url": None,
            "ocr_text": None,
            "detected_logos": [],
            "watermark": None,
        },
    })
    doc.locators.append("image 1")
    # 消息里显式写出「OCR」——下游模块与人都靠这个词判断「需要 OCR 补齐」。
    # 写成小写 "ocr" 容易被大小写敏感的检索漏掉。
    doc.add_follow_up(
        "OCR + visual_analysis",
        {"path": path, "image_id": os.path.basename(path),
         "reason": "the ingestion layer does not perform OCR or logo detection"},
    )
    doc.meta["records_total"] = len(doc.records)
    return doc
