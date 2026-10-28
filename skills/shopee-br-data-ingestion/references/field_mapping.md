| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-DI-002` |
| 所属模块 | ``shopee-br-data-ingestion`` |
| 版本 | 0.1.0 |
| 状态 | **Draft — 骨架，内容待 TASK-INGEST-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 字段别名表与列映射规则 |
| 相关文档 | `data/schema/product.schema.json` |
| 未决事项 | 别名表的完整清单待补全 |

---

## 1. 映射目标

所有输入最终映射到 `data/schema/product.schema.json` 的 `Product` 结构。核心字段：

| 字段 | 含义 | 必需 |
|---|---|---|
| `product_id` | 内部唯一标识 | ✅ |
| `shop_id` | 所属店铺 | ✅ |
| `title` | 商品标题 | ✅ |
| `description` | 商品详情 | |
| `attributes` | 平台属性字典 | |
| `category` | 类目 | |
| `brand` | 品牌 | |
| `images` | 图片列表 | |
| `product_url` | 商品链接 | |
| `supplier_sku` | 供应商货号 | |
| `internal_sku` | 内部 SKU | |
| `case_ids` | 关联历史案件 | |

## 2. 别名表

中葡英三语的列名变体都要覆盖，例如：

| 目标字段 | 别名（含变体） |
|---|---|
| `title` | `title` / `nome` / `nome do produto` / `商品名称` / `标题` |
| `description` | `description` / `descricao` / `descrição` / `商品描述` / `详情` |
| `product_id` | `product_id` / `item_id` / `sku` / `商品ID` / `货号` |
| `brand` | `brand` / `marca` / `品牌` |
| `category` | `category` / `categoria` / `类目` |
| `images` | `images` / `image_urls` / `图片` / `主图` |
| `price` | `price` / `preco` / `价格` |

## 3. 映射规则

| 规则 | 说明 |
|---|---|
| 规范化后比较 | 空格、下划线、大小写、连字符统一后再匹配 |
| 歧义别名 | 出现多个候选 → **不猜**，记 error |
| 未知列 | 保留为 `attributes` 附加项，**不丢弃** |
| 必需列缺失 | 该记录标记不完整，**不静默跳过** |
| 保留原值 | 规范化只影响比较，**存储保留原值** |

> ⚠️ 已知坑：早期实现把 `_` 归一化成空格，但别名表里用的是空格写法 —— 两边必须统一。
> 另：`sku` 这个裸别名曾被误映射到 `product_id`，导致语义错误 —— 裸 `sku` 必须人工确认。

## 4. 待 TASK-INGEST-01 确定

- [ ] 完整别名表
- [ ] 歧义别名的处理清单
