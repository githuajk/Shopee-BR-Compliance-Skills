# TASK-INGEST-01 交付说明

> 任务：`TASK-INGEST-01` —— 多格式资料读取与标准化
> 模块：`shopee-br-data-ingestion`
> 契约版本：1.0.0
> 交付日期：2026-10-27

---

## 1. 文件清单

| 路径 | 动作 | 说明 |
|---|---|---|
| `skills/shopee-br-data-ingestion/SKILL.md` | 修改 | 七要素齐全；状态由「骨架」改为「已实现」；补调用签名、options 语义、输出结构、失败处理、实测基线 |
| `skills/shopee-br-data-ingestion/references/format_matrix.md` | 修改 | 填实：9 种格式的解析方式与限制、失败模式与产出、编码回退、xlsx banner 定位、原始输入不可变、图片为何不产出商品 |
| `skills/shopee-br-data-ingestion/references/field_mapping.md` | 修改 | 填实：19 个规范字段 / 144 条查找项的完整别名表、6 个歧义别名、三态语义、标识符推导规则 |
| `skills/shopee-br-data-ingestion/references/provenance.md` | 修改 | 填实：7 个溯源字段的确切含义、digest 约定、records_parsed/failed 语义、parser_version 与 rule_version 之分 |
| `skills/shopee-br-data-ingestion/references/lexicon_format.md` | 修改 | 填实：6 个词库文件、37 组 / 856 词结构、5 条匹配约定、豁免与无法规避品类、改写映射、变位表、维护节奏 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/__init__.py` | 新增 | 公开 API（`ingest_paths` / `ingest_file`）、版本标识 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/pipeline.py` | 新增 | 管线编排、格式识别、溯源填充、AuditResult / ModuleHandoff 构造 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/builder.py` | 新增 | 字段映射后的规范化：必填校验、标识符推导、截断、价格解析、图片/变体构造 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/field_map.py` | 新增 | 别名表（144 项）、歧义别名（6 项）、三态字段跟踪（10 项） |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/normalize.py` | 新增 | 键归一化、文本清洗、空白折叠 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/errors.py` | 新增 | `ErrorLog`：错误记录与失败记录的统一容器 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/parsers/base.py` | 新增 | `ParsedDocument` 基类、sha256、ISO 时间戳 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/parsers/xlsx_parser.py` | 新增 | OOXML 直读（zipfile + ElementTree）、banner 与表头定位 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/parsers/csv_parser.py` | 新增 | csv 读取、分隔符/编码嗅探 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/parsers/json_parser.py` | 新增 | JSON（数组/包裹对象）与 JSONL（逐行容错） |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/parsers/text_parser.py` | 新增 | TXT/MD 分块 + 前置元数据 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/parsers/docx_parser.py` | 新增 | DOCX 段落与表格 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/parsers/pdf_parser.py` | 新增 | 可选 pypdf + 内置最小文本层提取器降级 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/parsers/image_parser.py` | 新增 | 图片登记为待 OCR / 视觉分析 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/parsers/tabular.py` | 新增 | 表格型记录的公共处理 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion/parsers/__init__.py` | 新增 | 格式分派 |
| `skills/shopee-br-data-ingestion/src/sbr_ingestion_cli.py` | 新增 | 命令行入口 |
| `tests/shopee-br-data-ingestion/run_tests.py` | 新增 | 193 项断言，覆盖 L1–L4 + 注入安全 + 共享夹具 + CLI 端到端 |

**代码规模**：实现 2,965 行（18 个文件），测试 991 行。

## 2. 测试结果

### 2.1 模块自有测试

```bash
$ env -u LD_LIBRARY_PATH python3 tests/shopee-br-data-ingestion/run_tests.py
```

实际输出（摘要）：

```
==============================================================
shopee-br-data-ingestion 模块测试
仓库根: /config/dianshang/Shopee-BR-Compliance-Skills
运行时间: 2026-10-27T08:31:32.745694+00:00
==============================================================

=== L1 单元测试 ===
=== L2 契约测试 ===
=== L3 格式测试 ===
=== L4 硬约束测试 ===
=== 注入安全测试（输入文档中的指令只是数据） ===
=== 共享夹具兼容性（只读） ===
=== CLI 端到端 ===

==============================================================
PASSED: 193   FAILED: 0
全部测试通过。
```

**退出码 0。**

### 2.2 CLI 端到端

```bash
$ env -u LD_LIBRARY_PATH python3 skills/shopee-br-data-ingestion/src/sbr_ingestion_cli.py \
    --request-id REQ-INGEST-001 --out-dir /tmp/ingest-out \
    --default-shop-id SHOP1 data/samples/demo_mass_update.xlsx
```

实际输出：

```
parser:  sbr-ingestion/1.0.0
inputs:  1
records: 15 product(s)
errors:  15
verdict: PASS  action: allow  risk_level: info
outputs: /tmp/ingest-out
```

### 2.3 产出对契约的校验

```bash
$ env -u LD_LIBRARY_PATH python3 tools/validate_json.py \
    --schema contracts/skill_input.schema.json /tmp/ingest-out/skill_input.json
0 errors, 0 warnings

$ env -u LD_LIBRARY_PATH python3 tools/validate_json.py \
    --schema contracts/audit_result.schema.json /tmp/ingest-out/audit_result.json
0 errors, 0 warnings

$ env -u LD_LIBRARY_PATH python3 tools/validate_json.py \
    --schema contracts/module_handoff.schema.json /tmp/ingest-out/module_handoff.json
0 errors, 0 warnings
```

### 2.4 全项目校验

```bash
$ env -u LD_LIBRARY_PATH bash scripts/check_all.sh
```

实际输出（摘要）：

```
PASSED: 298   FAILED: 0      框架自检全部通过。
契约校验 — 通过 19，失败 0
PASSED: 266   FAILED: 0      词库校验通过：37 组 / 856 词 / 37 条映射 / 50 条规则
0 errors, 0 warnings
0 errors, 0 warnings
50/50 excerpts verified verbatim, 0 failed
检查 50 条规则、36 条正则
全部规则的正则可编译，且无逻辑自指缺陷。
validated 90 products, 10 cases across 8 scenarios + shared fixtures
校验 108 条夹具-规则断言：58 应命中、50 应不命中
PASSED: 589   FAILED: 0      任务包与所有权一致性全部通过。
ALL CHECKS PASSED
```

**退出码 0。**

### 2.5 未执行的测试

| 测试 | 原因 |
|---|---|
| `pypdf` 路径的 PDF 解析 | 环境未安装 pypdf。**内置降级提取器已测**（含 FlateDecode 解压与文本算子），pypdf 分支未覆盖 |
| 真实 Shopee 导出文件的全量回归 | 仓库内只有 `data/samples/demo_mass_update.xlsx` 一个真实样本（15 条）。其余用合成输入 |
| 性能基准（万级商品耗时） | 章程 §6.1 要求先有基线再定阈值，本任务未做基准 —— 不臆造性能数字 |

## 3. 未解决问题

| # | 问题 | 影响 | 建议 |
|---|---|---|---|
| 1 | `pypdf` 分支未测试 | 若环境装了 pypdf，走的是另一条提取路径 | 装上 pypdf 后补一条对比测试（两条路径的输出应等价） |
| 2 | 旧版 `.xls` 不支持 | 用户若只有 `.xls` 导出，需先转 | 已在错误信息中明确提示；如需支持需引入额外依赖 |
| 3 | 图片**不**做 OCR / logo 检测 | 图片类规则（`SBR-IP-005` / `SBR-IP-008`）在下游会记为**未评估** | 这是设计选择（H3 优先）。若要覆盖，需另建视觉分析模块 |
| 4 | 表格型输入的列名依赖别名表 | 遇到别名表外的列名会进 `attributes` 而非规范字段 | 别名表 144 项已覆盖主流写法；新词库/新导出格式出现时需补 |
| 5 | 单条 `AuditResult` 覆盖整批 | 一个文件里有多种失败时，结果粒度是文件级而非记录级 | 契约定义 `AuditResult` 可带 `target_ref`；如需记录级粒度，建议下游模块各自产出记录级 result |
| 6 | `demo_mass_update.xlsx` 不带 `shop_id` | 不给 `default_shop_id` 时 15 条全部记 error | 这是**正确行为**（H3：缺字段不等于合规）。运营侧应在导出时带店铺列 |

## 4. 依赖说明

- **我依赖的**：无。可与 `shopee-br-policy-research` 并行。
- **我期待下游提供的**：
  - 全部审核模块使用我产出的 `products[]` 与 `provenance`
  - 下游若需要新的输入字段，**先**告诉我补别名表，而不是各自在规则里硬解
- **我对其他模块的影响**：本模块的字段映射决定了其他模块能拿到什么字段 ——
  缺字段会让它们**未评估**而非**通过**。`STATE_TRACKED_FIELDS` 的 10 个字段是下游的评估依赖面。

## 5. 契约变更建议

**无。** 实现过程中未发现需要修改冻结契约的问题。

一条**使用说明**（非变更请求）：`contracts/audit_result.schema.json` 的 `type` 是
`object`（单条），但多个模块都会产出 `AuditResult[]`。CLI 因此同时写
`audit_result.json`（单条，可直接校验）与 `audit_results.json`（数组）。
若后续模块也写 CLI 产出，建议沿用同一约定。

## 6. 自我约束核查

- [x] 只改了白名单内的文件（`skills/shopee-br-data-ingestion/**`、`tests/shopee-br-data-ingestion/**`）
- [x] 未修改公共契约（`contracts/**`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、`manifest.json`、`tasks/**`、`tests/test_plan.md`）
- [x] 未修改他人拥有的文件（`rules/**`、`research/**`、`lexicon/**`、`tests/fixtures/**`、`docs/**`、`tools/**`、`scripts/**`）
- [x] 引文核验通过（本模块不引用政策文本；全库 50/50 保持通过）
- [x] 自有测试实际执行（193 项全通过，输出见 §2.1）
- [x] `SKILL.md` 七要素齐全（frontmatter、职责/非职责、输入契约、输出契约、规则与来源要求、失败处理、测试与验收）
- [x] `references/` 内容已填实（无占位符）
- [x] 硬约束 H1–H6 已逐条自查（L4 段有对应断言）
- [x] 原始输入不可变（测试断言字节与 mtime 不变）
- [x] 未修改 `lexicon/**`（虽在白名单内，但本任务未触碰词库）
