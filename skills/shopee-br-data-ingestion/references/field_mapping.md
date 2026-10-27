| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-DI-002` |
| 所属模块 | `shopee-br-data-ingestion` |
| 版本 | 1.0.0 |
| 状态 | **Active — 已实现** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 字段别名表与列映射规则 |
| 相关文档 | `data/schema/product.schema.json`、`skills/shopee-br-data-ingestion/src/sbr_ingestion/field_map.py` |
| 未决事项 | 无 |

---

## 1. 映射目标

所有输入最终映射到 `data/schema/product.schema.json` 的 `Product` 结构。

**必需字段**（`field_map.REQUIRED_FIELDS`，缺任一 → 该记录进 `errors[]`）：

| 字段 | 含义 |
|---|---|
| `product_id` | 内部唯一标识 |
| `internal_sku` | 卖家自己的 SKU / 主商品货号 |
| `shop_id` | 所属店铺 |
| `title` | 商品标题 |

**可选字段**：`description` / `attributes` / `category` / `brand` / `model` / `price` /
`currency` / `images` / `variations` / `product_url` / `supplier_sku` /
`platform_pid` / `shop_name` / `case_ids` / `notes`。

## 2. 别名表（19 个规范字段 / 144 条查找项）

别名表在 `field_map.FIELD_ALIASES`，归一化后的查找表在 `field_map.LOOKUP`（144 项）。

| 规范字段 | 别名（归一化后） |
|---|---|
| `product_id` | `product_id` `productid` `product id` `item_id` `itemid` `listing_id` `id_produto` `id do produto` `produto_id` `商品编号` `商品标识` `商品内部编号` |
| `internal_sku` | `internal_sku` `internalsku` `internal sku` `sku_interno` `sku interno` `seller_sku` `sku do vendedor` `seller sku` `主商品货号` `商品货号` `货号` `主货号` `卖家货号` |
| `supplier_sku` | `supplier_sku` `suppliersku` `supplier sku` `fornecedor_sku` `sku_fornecedor` `sku do fornecedor` `供应商货号` `供货商货号` `供应商sku` |
| `shop_id` | `shop_id` `shopid` `shop id` `loja_id` `id_loja` `id da loja` `店铺id` `店铺 id` `店铺编号` |
| `shop_name` | `shop_name` `shopname` `shop name` `nome_loja` `nome da loja` `loja` `店铺名` `店铺名称` |
| `platform_pid` | `platform_pid` `platformpid` `platform pid` `pid` `shopee_product_id` `id_anuncio` `id do anuncio` `商品id` `商品 id` `平台商品id` `商品id平台` |
| `title` | `title` `nome` `nome do produto` `nome_do_produto` `product name` `produto` `商品名称` `标题` `商品标题` `品名` |
| `description` | `description` `descricao` `descrição do produto` `descricao do produto` `detalhes` `detalhe` `detalhado` `商品描述` `描述` `详情` `商品详情` `详情描述` |
| `category` | `category` `categoria` `categoria do produto` `类目` `分类` `商品类目` |
| `category_source` | `category_source` `categoria_origem` `类目来源` `类目来源方` `类目归属` |
| `brand` | `brand` `marca` `marca do produto` `品牌` `品牌名` |
| `model` | `model` `modelo` `型号` `型号名称` `产品型号` |
| `price` | `price` `preco` `preço` `valor` `价格` `售价` `商品价格` |
| `currency` | `currency` `moeda` `货币` `币种` |
| `images` | `images` `image_urls` `image_url` `imagens` `图片` `图片链接` `图片url` `主图` `图片地址` `图片url列表` |
| `variations` | `variations` `variacao` `variacoes` `变体` `规格` `规格名` `sku_variations` |
| `product_url` | `product_url` `url` `link` `produto_url` `url do produto` `商品链接` `链接` `商品url` |
| `case_ids` | `case_ids` `case_id` `casos` `caso_ids` `案件id` `历史案件` `关联案件` |
| `notes` | `notes` `note` `observacao` `observações` `observacoes` `备注` `说明` `失败原因` `failure_reason` `motivo da falha` |

## 3. 歧义别名（**不猜**）

以下裸别名在 Shopee 生态里同时指多个字段，**不能自动判定**：

| 别名 | 可能的归属 |
|---|---|
| `sku` | `product_id` / `internal_sku` / `supplier_sku` |
| `codigo` | `product_id` / `internal_sku` |
| `code` | `product_id` / `internal_sku` |
| `ref` | `product_id` / `internal_sku` |
| `referencia` | `product_id` / `internal_sku` |
| `货号` | `product_id` / `internal_sku` / `supplier_sku` |

**处理方式**：命中歧义别名时**不映射**，相关字段记入 `errors[]`（severity=error），
并列出歧义候选交人工确认。**绝不默认挑一个** —— 猜错会把 `supplier_sku`
当成 `product_id`，直接影响后续的重复刊登判定。

> ⚠️ 已知坑（历史）：早期实现把裸 `sku` 静默映射到 `product_id`，
> 语义错误且无声。现在它进 `AMBIGUOUS_ALIASES`，必须人工确认。

## 4. 映射规则

| 规则 | 说明 |
|---|---|
| 规范化后比较 | 空格、下划线、大小写、连字符、变音符号统一后再匹配 |
| 歧义别名 | 命中 `AMBIGUOUS_ALIASES` → **不猜**，记 error 并列出候选 |
| 未知列 | 保留为 `attributes` 附加项，**不丢弃** |
| 必需列缺失 | 该记录标记不完整，**不静默跳过**（H3） |
| 保留原值 | 规范化只影响**比较**，**存储保留原值** |
| 状态跟踪字段 | `STATE_TRACKED_FIELDS` 记录「有值 / 显式为空 / 缺失」三态 —— 空 ≠ 缺失 |

### 4.1 三态语义（与契约 §11.1 一致）

`STATE_TRACKED_FIELDS` = `brand` `model` `category` `description` `price` `currency`
`supplier_sku` `product_url` `images` `variations`

这三个字段在 `Product` 里都可为 `null`，但**「显式为空」与「缺失」不是一回事**：

| 输入形态 | 语义 | 下游影响 |
|---|---|---|
| 字段有值 | 正常 | 可评估 |
| 字段存在但为空（`""` / `[]` / `null`） | **missing** —— 视同缺失 | 依赖它的规则记为**未评估** |
| 字段完全不存在 | **missing** | 同上 |

> `category` 为 `null` 与 `category` 键不存在，在下游**等价**——
> 都让 `SBR-LV-008`（类目缺失）判为未评估，而不是「类目正常」。

### 4.2 标识符推导

| 情形 | 行为 |
|---|---|
| `product_id` 太短（< 4 字符，契约要求 ≥ 4） | 合成 `SBRP-<shop>-<sku>-<id>`，记 warning |
| `internal_sku` 缺失但 `product_id` 存在 | 用 `product_id` 顶上，记 warning 说明是推导值 |
| `shop_id` 缺失且未提供 `default_shop_id` | 记 error（**不**默默补齐） |

> **`default_shop_id` 是「显式提供」不是「默默补齐」。**
> 提供了 → 记 warning 说明来源；没提供 → 记 error。
> 两者都不产生静默的假数据。

## 5. 实测基线

```bash
env -u LD_LIBRARY_PATH python3 tests/shopee-br-data-ingestion/run_tests.py
```

覆盖：xlsx 6 行 banner + 表头定位、csv 编码回退、json/jsonl 包裹与逐行、
txt/md 元数据块、docx 表格、pdf 文本层与扫描件、图片登记、歧义别名、
三态语义、原始输入不可变。**189 项断言全部通过。**
