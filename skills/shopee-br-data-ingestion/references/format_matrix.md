| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-DI-001` |
| 所属模块 | `shopee-br-data-ingestion` |
| 版本 | 1.0.0 |
| 状态 | **Active — 已实现** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 各输入格式的解析方法、限制与失败模式 |
| 相关文档 | `contracts/skill_input.schema.json`、`data/schema/product.schema.json`、`skills/shopee-br-data-ingestion/src/sbr_ingestion/parsers/` |
| 未决事项 | 无 |

---

## 1. 格式矩阵

| 格式 | 扩展名 | 解析方式 | 能得到 | 已知限制 |
|---|---|---|---|---|
| XLSX / XLSM | `.xlsx` `.xlsm` | `zipfile` + `ElementTree` 直读 OOXML | 全字段 | 旧版 `.xls` **不支持**；多行 banner 需自动定位表头 |
| XLS | `.xls` | — | — | **不支持** → 报「请先导出为 XLSX/CSV」 |
| CSV / TSV | `.csv` `.tsv` | `csv` + 分隔符/编码嗅探 | 全字段 | 编码可能非 UTF-8；单行非法不中断整批 |
| JSON | `.json` | `json` | 全字段 | 需识别数组 / 包裹对象两种形态 |
| JSONL | `.jsonl` | 逐行 `json` | 全字段 | 任一行损坏 → 报行号，继续处理其余行 |
| TXT / MD | `.txt` `.md` | 分块 + `Title:`/`SKU:` 前置元数据 | 自由文本 | Markdown 标题行是结构标记，不作记录 |
| DOCX | `.docx` | `zipfile` + `word/document.xml` | 自由文本 + 表格 | 复杂排版丢失 |
| PDF | `.pdf` | 可选 `pypdf`，缺失时降级到内置最小文本层提取器 | 自由文本 | 扫描件无文本层 → 需 OCR；表格结构可能丢失 |
| 图片 | `.png` `.jpg` `.jpeg` `.webp` `.gif` `.bmp` `.tif` `.tiff` | 登记为待办 | 无 | 需 OCR + 视觉分析；**不猜**图片里有什么 |

## 2. 统一处理管线

```
文件路径
  ↓ detect_kind()        扩展名 → 格式；不支持则明确报错
  ↓ sha256_file()        只读哈希（溯源）
  ↓ parse_file()         格式专属解析器 → ParsedDocument
  ↓ _record_to_mapping() 统一成 {column: value}
  ↓ build_product()      字段映射 + 清洗 + 契约化
  ↓ SkillInput / AuditResult / ModuleHandoff
```

**每一层失败都产出记录，不静默丢弃。**

## 3. 各格式的失败模式与产出

| 情形 | 产出 | 严重度 | 行为 |
|---|---|---|---|
| 文件不存在 | `error` | error | `records_parsed=0, records_failed=1`，`digest=null`（契约允许） |
| 路径不是普通文件 | `error` | error | 同上 |
| 格式不支持 | `error` | error | 明确说明 + 建议转换格式 |
| xlsx 是损坏的 zip | `error` | error | 报「not a valid xlsx (zip) file」 |
| csv 表头不可识别 | `error` | error | **列出所见表头**，便于人工对齐 |
| csv 单行字段缺失 | `error` | warning | 报行号 + 缺失字段 + 记录预览 |
| jsonl 某行非法 | `error` | warning | 报行号，继续处理其余行 |
| txt 块无标题 | `error` | warning | 不静默丢弃该块 |
| docx 损坏 | `error` | error | 报 zip / XML 错误 |
| pdf 无文本层（扫描件） | `error` | warning | 报「需 OCR」→ **不产生 PASS** |
| 图片 | `follow_up` | warning | 登记 `needs: [ocr, visual_analysis]` |
| 记录缺必填字段 | `error` | error | 报缺失字段 + 记录预览；记录**不**进 products |

## 4. 编码嗅探与回退

CSV / TXT / MD 依次尝试：

```
utf-8-sig → utf-8 → cp1252 → latin-1
```

- 全部失败 → 报「无法用任何受支持的编码解码」
- `latin-1` 永不失败（字节↔字符一一映射），但可能产生乱码 → 因此**优先**用它之前的编码
- 命中 `cp1252` 时重音字符正确还原（`ç` `ã` `é`）—— 测试逐字核对

> 实测坑：早期用 `\b` 做词边界，在 `à`/`ç`/`ã` 下不可靠。
> 本模块的规范化用 `(?<!\w)` / `(?!\w)`。

## 5. xlsx 的 banner 与表头定位

Shopee 导出的 mass_update 文件常带多行说明 banner。表头定位策略：

1. 逐行扫描，找出**同时包含至少一个已知别名**的行 → 视为表头
2. 表头之前的内容全部丢弃（banner）
3. 表头之后的数据行按列名成对映射
4. 找不到这样的行 → 报「no recognisable title column」并**列出前几行内容**

`--sheet` 可指定工作表名；未指定时取第一个含数据的工作表。

## 6. 原始输入不可变

**本模块从不写回被读取的文件。** 只读打开（`rb`），不改权限、不移动、不重命名。

测试断言：读入前后文件的**字节内容**与 **mtime** 都必须不变。

## 7. 图片为何「不产出商品」

图片**不产生商品数据**。本模块只登记一条待办：

- `images[]` 里放 `{image_id, local_path, url, ocr_text: null, detected_logos: [], watermark: null}`
- `ocr_text` / `detected_logos` **留空** —— **不猜**图片里有什么

> `data/schema/product.schema.json` 的 `images[].ocr_text` 允许 `null`，
> `detected_logos` 允许 `[]` —— 用「显式未评估」而不是伪造内容。
> 下游 IP 模块据此把图片类规则记为**未评估**（H3），
> 而不是「没查到 logo 就当通过」。

## 8. 实测基线

```bash
env -u LD_LIBRARY_PATH python3 tests/shopee-br-data-ingestion/run_tests.py
```

**189 项断言全部通过**，覆盖每种声明支持的格式的成功路径与失败路径。
