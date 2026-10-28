# SBRCA-P1-003 数据规范与 JSON Schema 规范

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-P1-003` |
| 版本 | 1.0.0 |
| 状态 | **Draft — 待用户审批** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | SBRCA 全部 JSON 数据结构、Schema、字段命名、ID 体系、缺失语义 |
| 相关文档 | `SBRCA-P1-001` 总章程 §3、`SBRCA-P1-002` 架构 §3.2、`SBRCA-P0-003` 需求追踪清单 |

---

## 1. 格式政策（重申）

| 用途 | 唯一允许格式 |
|---|---|
| 结构化数据、规则、配置、审核记录、测试数据、Schema、接口数据、结构化报告 | **JSON** |
| 文档、SOP、需求规格、调研报告、架构、操作手册、提示词、变更说明 | **Markdown** |

**禁止**作为内部正式数据源：YAML、JSONL、CSV、TXT、XML。

**豁免**：源码（`.py`）、二进制素材（`.xlsx` `.jpg` 等）、外部输入文件（导入后即转换，原始文件保留在外部位置并以 `source.path` 引用，**不复制进项目目录**）。

> **理由**：章程 §2.1 禁止将敏感业务数据复制到公共目录。真实导出文件留在原位，项目内只存规范化 JSON（必要时脱敏）。

---

## 2. JSON 通用规范

| 项 | 规定 | 校验方式 |
|---|---|---|
| 编码 | UTF-8，无 BOM | 脚本检查 |
| 语法 | 标准 JSON。**禁止**注释、尾随逗号、单引号、未转义控制字符 | `json.load` 严格模式 |
| 缩进 | 2 空格 | 风格检查 |
| 键顺序 | 语义分组优先：标识 → 内容 → 关系 → 元数据 | 人工评审 |
| 日期 | ISO 8601 `YYYY-MM-DD`；时间戳 `YYYY-MM-DDTHH:MM:SS+00:00` | Schema `format` |
| 货币 | 数值 + 独立 `currency` 字段（ISO 4217，默认 `BRL`） | Schema |
| 空值 | 见 §4 四态 | Schema |
| 敏感字段 | 不进普通日志；不落版本库的明文 | 扫描脚本 |

---

## 3. 字段命名规范

| 规则 | 说明 |
|---|---|
| `snake_case` | 全部 JSON 字段 |
| 布尔用 `is_` / `has_` / `requires_` 前缀 | 如 `is_enforceable`、`has_nonempty` |
| 集合用复数 | `rules`、`evidence`、`findings` |
| ID 用 `_id` 后缀 | `rule_id`、`case_id` |
| 引用外键用 `<target>_id` | `canonical_listing_id` |
| 枚举值全小写下划线 | `flag_for_review`、`relist_frozen` |
| 时间用 `_at` 后缀 | `created_at`、`last_verified`（日期例外） |
| 布尔枚举不用 `1`/`0` | 用 `true`/`false` 或枚举字符串 |
| 禁止保留前缀 | 不用 `tmp_`、`test_`、`new_` 开头命名正式数据 |

---

## 4. 缺失 / 未知 / 不适用 / 待核实 —— 四态语义

章程 §2.3 明确要求这四种状态**必须有明确表示**且**不得混同**。本项目定义：

| 状态 | 语义 | JSON 表示 | 示例 |
|---|---|---|---|
| **缺失（missing）** | 该值存在于模型但本次没有数据 | 字段值为 `null` | 没有品牌 → `"brand": null` |
| **未知（unknown）** | 值存在但无法确定（如图片未做视觉分析） | 显式标记对象 `{"state": "unknown", "reason": "..."}` | 品牌未核实 → `{"state":"unknown","reason":"no_authorisation_document"}` |
| **不适用（not_applicable）** | 该字段对此对象无意义 | 显式标记对象 `{"state": "not_applicable"}` | 商品无变体 → `{"state":"not_applicable"}` |
| **待核实（pending_verification）** | 已判定有风险但结论待人工/外部确认 | 显式标记对象 `{"state":"pending_verification","assigned_to":"...","due":"..."}` | IP 待品牌方回复 |

**禁止**：
- 用 `""` / `0` / `[]` / `{}` 表达「无」而与其他态混同。
- 用 `null` 同时表达「缺失」与「不适用」。
- 省略必填字段来表达「没有」。

**Schema 表达**（标准做法）：

```json
{
  "type": ["string", "null"],
  "description": "缺失时为 null"
}
```

三态字段：

```json
{
  "oneOf": [
    {"type": "string"},
    {
      "type": "object",
      "required": ["state"],
      "properties": {
        "state": {"enum": ["unknown", "not_applicable", "pending_verification"]},
        "reason": {"type": "string"},
        "assigned_to": {"type": "string"},
        "due": {"type": "string", "format": "date"}
      }
    }
  ]
}
```

> **当前实现的差距**：`data/schema/product.schema.json` 中多数可空字段只用 `["type","null"]`，尚未引入三态对象。Phase 2 需按本节升级（影响 `REQ-DATA-005`）。

---

## 5. ID 体系

| 类型 | 格式 | 示例 | 说明 |
|---|---|---|---|
| 规则 | `SBR-<类别>-<序号>` | `SBR-PI-001` | 类别见 §5.1 |
| 商品 | `SBRP-<shop_id>-<pid>` | `SBRP-SHOP1-900001` | 稳定；不随标题变化 |
| 案件 | `SBRC-<6+位数字>` | `SBRC-000101` | 顺序分配 |
| 发现 | `F-<5 位>` | `F-00001` | 单次审核内唯一 |
| 需求 | `REQ-<类别>-<序号>` | `REQ-BIZ-001` | 见 `SBRCA-P0-003` |
| 治理文档 | `SBRCA-P<phase>-<seq>_<name>` | `SBRCA-P1-002_architecture` | |
| ADR | `ADR-<4 位>` | `ADR-0001` | |
| 审核运行 | `RUN-<10 位十六进制>` | `RUN-c908489447` | |
| 证据类型 | `<domain>_<subject>` | `anvisa_registration` | 规则 `evidence_required` 引用 |

### 5.1 规则类别前缀

| 前缀 | 类别 | 对应 `rule.category` |
|---|---|---|
| `PI` | Prohibited Item | `prohibited_item` |
| `RI` | Restricted Item | `restricted_item` |
| `IP` | Intellectual Property | `ip_trademark` / `ip_copyright` / `ip_design` |
| `LV` | Listing Violation | `listing_violation` / `consumer_protection` |
| `DUP` | Duplicate | `duplicate_listing` / `cross_store_duplicate` |
| `RL` | Relist / Freeze | `relist_freeze` |
| `AU` | Authorization | `authorization` |
| `AC` | Account | `account_penalty` |
| `MED` | Medicines & Health | `prohibited_item` / `restricted_item` |

### 5.2 ID 稳定性规则（章程 §2.5）

- **规则重命名不得导致历史记录失去关联。** 改名必须在 ADR 登记，并提供旧 ID → 新 ID 映射；历史 `case_ids` / `rule_ids` 引用保留旧 ID 直到迁移完成。
- 商品 ID 基于 `shop_id + platform_pid`；**不得**基于标题或 SKU（两者都会变）。
- 词条在 `lexicon/` 中以词形为主键，规则引用时用组名 + 词形，不使用行号。

---

## 6. Schema 规范

### 6.1 通用要求

| 项 | 规定 |
|---|---|
| `$schema` | `https://json-schema.org/draft/2020-12/schema` |
| `$id` | `https://shopee-br-compliance-agent.local/schema/<name>.schema.json` |
| 标题 | 每个属性有 `description`（说明**为什么**，不只是是什么） |
| 封闭性 | 默认 `additionalProperties: false`，避免"影子字段" |
| 必填 | 标识与语义必需字段进 `required`；可空但存在的字段不进 |
| 枚举 | 所有受控取值用 `enum`，不写自由字符串 |
| 引用 | 用 `$ref` 指向同目录 Schema |
| 数值边界 | 价格/数量给 `minimum` / `maximum` |
| 字符串长度 | 给 `minLength` / `maxLength` |

### 6.2 现有 Schema 清单

| Schema | 覆盖 | 状态 |
|---|---|---|
| `rule.schema.json` | 单条规则 | ✅ |
| `rule_collection.schema.json` | 规则文件（rules 数组 + 溯源元数据） | ✅ |
| `product.schema.json` | 商品主档 | ⚠️ 需补三态（§4） |
| `case.schema.json` | 案件 | ⚠️ 需补三态 |
| `review_result.schema.json` | 审核结果 | ⚠️ 需补 `engine_version` / `ruleset_version`（章程 §5.6） |
| `lexicon.schema.json` | 词库 | ✅ |

### 6.3 校验器

`tools/validate_json.py` 为**仅标准库**实现（托管环境 PEP 668 无法保证 pip 安装），支持项目用到的 draft 2020-12 子集：

`type` `required` `additionalProperties` `properties` `patternProperties` `items` `prefixItems` `minItems` `maxItems` `minLength` `maxLength` `pattern` `enum` `const` `minimum` `maximum` `exclusiveMinimum` `exclusiveMaximum` `multipleOf` `oneOf` `anyOf` `allOf` `not` `$ref`（本地指针 + 同目录文件） `format`（uri/date，告警级） `if/then/else` `propertyNames` `contains` `minProperties` `maxProperties` `uniqueItems`

**缺口**：`$dynamicRef`、`unevaluatedProperties`、分布式 Schema 引用未实现。若将来使用需先扩展校验器并记 ADR。

> 依赖决策见 `SBRCA-P0-004` CONF-004。若批准引入 `jsonschema` 库，此校验器退化为**开发期交叉验证**工具（两套实现对比结果必须一致）。

---

## 7. 规则对象规范

### 7.1 必备字段（章程 §3.1 + 现有 Schema）

`rule_id` `title` `category` `description` `trigger_conditions` `severity` `decision` `evidence_required` `human_review_required` `source_url` `last_verified` `status` `version`

### 7.2 溯源字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `source_tier` | 是 | `platform_official` / `law` / `internal_risk` / `unverified` |
| `source_excerpt` | 是 | 原文引文。**必须逐字出现在 `research/raw/` 的抓取件中** |
| `applies_to` | 否 | 适用范围（品类/卖家类型） |
| `notes` | 否 | 设计说明、已知局限 |
| `tags` | 否 | 便于检索 |

### 7.3 引文核验（`REQ-LEG-001`）

`tools/verify_citations.py` 把每条规则的 `source_excerpt` 与 `research/raw/*.txt` 做**逐字比对**（空白与句末标点归一化，其余字符严格）。

**当前状态：50/50 通过。**

该工具曾抓到真实编造：初版 `SBR-IP-006` 引用「Art. 125. Não constitui uso indevido…」—— 该葡语在 Planalto 原文中**不存在**；真实条文是 **Lei 9.279/1996 Art. 132, II**。

### 7.4 规则集合的溯源元数据

每个规则文件顶层携带：`schema_version` `library` `source_tier` `source_url` `source_excerpt` `last_verified` `notes`。这使**文件级**也可追溯。

---

## 8. 词库规范

```json
{
  "schema_version": "1.0",
  "name": "...",
  "description": "...",
  "last_verified": "2026-10-27",
  "usage": "...",
  "groups": {
    "<group_name>": ["<pattern>", "..."]
  }
}
```

| 规则 | 说明 |
|---|---|
| 组名 | 英文小写下划线，语义为「筛查桶」 |
| 词条 | 葡语为主；**大小写与重音不敏感**（加载时 NFKD 折叠） |
| 风险等级 | 若需分级，组名承载（`proibido_*` / `ip_*` / `violacao_*`） |
| **语义** | **命中即信号，不是违规判定**。处置强度由规则决定，不由词库决定 |
| 词库不承载 | 平台来源、严重度、决策、证据要求 —— 那是 `rules/` 的职责 |

**当前规模**：25 组 / 179 词。历史 2026-09 词库（17 类 / 1,320 词文档版）的数据文件已丢失，见 `SBRCA-P0-002` §3.3 与 `Q-G`。

---

## 9. 审核结果规范

见 `data/schema/review_result.schema.json` 与 `SBRCA-P1-002` §3.6。

**Phase 2 需补**：
- `engine_version`（软件版本）
- `ruleset_version`（规则集内容哈希）
- `input_digest`（输入文件哈希，保证可追溯到具体文件版本）

---

## 10. 案件库规范（Phase 2）

`data/cases/*.json`，每文件：

```json
{
  "schema_version": "1.0",
  "shop_id": "SHOP1",
  "cases": [ { "case_id": "...", "product_ids": [...], "...": "..." } ]
}
```

案件必备字段见 `case.schema.json`：`case_id` `shop_id` `product_ids` `violation_type` `status` `frozen` `evidence` `approvals`。

**证据对象**：

```json
{"evidence_type": "anvisa_registration", "provided": false, "artifact_ref": null, "notes": "", "collected_at": null}
```

`artifact_ref` 只存**引用**（路径或外部工单号），**不存凭证内容**（`REQ-SEC-002`）。

---

## 11. 命名与合规检查（待实现，Phase 2）

| 检查 | 规则 |
|---|---|
| 扩展名白名单 | 正式数据 `.json`，文档 `.md`；其余扩展名需在豁免清单中登记 |
| 命名风格 | 小写下划线；治理文档匹配 `SBRCA-P<phase>-<seq>_<name>` |
| JSON 语法 | 严格 `json.load`（禁注释/尾逗号） |
| UTF-8 | 无 BOM |
| Schema 覆盖 | 每个核心数据目录有对应 Schema |
| 唯一 ID | 同一集合内 ID 不重复 |
| 引用完整 | 所有 `*_id` 引用可解析到存在对象 |
| 敏感字段 | 扫描 `password` `token` `secret` `api_key` `authorization` 等键名 |

---

## 12. 尚未确定事项

| ID | 事项 | 影响 |
|---|---|---|
| CONF-003 | 是否允许 SQLite 派生索引 | §1、§8 |
| Q-B | 店主 10 条原则的固化层级 | §8 词库 vs 规则边界 |
| Q-G | 词库重建来源 | §8 |
| — | 三态对象在 Product/Case Schema 中的具体落地 | §4（Phase 2 任务） |

## 13. 变更记录

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| 1.0.0 | 2026-10-27 | 初稿 | 技术负责人（Agent） |
