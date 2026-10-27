# PROJECT_RULES.md — SBRCA 公共工程规范

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-PROJ-001` |
| 版本 | 1.0.0 |
| 状态 | **Frozen — 已冻结，任何 Agent 不得自行修改** |
| 冻结日期 | 2026-10-27 |
| 适用范围 | `shopee-br-compliance-agent/` 全部 Skills、模块、任务、测试 |
| 相关文档 | `AGENTS.md`、`contracts/`、`manifest.json`、`tasks/task_registry.json`、`tests/test_plan.md` |

---

## 0. 契约变更规则

> **公共契约经审查后冻结。任何 Agent 不得自行修改公共契约。**

发现契约问题时：

1. **不得直接修改** `PROJECT_RULES.md`、`AGENTS.md`、`contracts/**`、`manifest.json`、`tasks/task_registry.json`、`tasks/task_template.md`、`tests/test_plan.md`。
2. 在自己的任务交付中提交**变更建议**，格式见 `tasks/task_template.md` §「契约变更建议」。
3. 由**集成 Agent** 审查并决定是否采纳；采纳后由集成 Agent 统一修改并提升版本号。

**违反此规则的任务直接判定为不通过。**

---

## 1. 项目定位

本项目是**一套可供不同 Agent、不同模型使用的 Skills 集合**，不是一个需要立即部署的完整软件服务。

| 原则 | 含义 |
|---|---|
| 高内聚、低耦合 | 一个模块只做一件事；模块之间通过契约通信，不共享内部状态 |
| 契约优先 | 先冻结契约，再并行开发；实现服从契约而非相反 |
| 模块独立开发 | 每个模块可由不同 Agent 在独立分支/目录独立开发与测试 |
| 公共规范统一维护 | 规范、Schema、ID 体系由公共契约定义，不在模块内各自发明 |
| 任务输入输出明确 | 每个任务有明确的输入、输出、验收标准 |
| 文件所有权清晰 | 每个路径有唯一 owner，不允许多 Agent 默认并发修改同一文件 |
| 可独立测试与集成验收 | 模块可单独测试；集成有统一验收标准 |
| **不依赖模型内部记忆** | 任何 Agent 不得假定自己能访问其他 Agent 的上下文或平台的隐式记忆；一切通过文件契约传递 |

---

## 2. 文件格式政策

| 用途 | 格式 |
|---|---|
| 正式规则、配置、结构化数据、测试数据、Schema、任务注册表、清单 | **JSON** |
| 项目文档、Skill 指令、模块说明、调研报告、测试说明、任务说明 | **Markdown** |
| Skill 平台元数据（`SKILL.md` frontmatter） | 平台强制格式（YAML frontmatter）—— **唯一豁免** |
| 程序源代码 | 平台标准扩展名（`.py` 等） |
| 外部输入 | Excel / CSV / PDF / Word / 图片 / JSON 等，**读取后统一转换为项目数据模型** |

**禁止**作为项目内部正式数据源：YAML、JSONL、CSV、TXT、XML。

> **注意**：`SKILL.md` 的 YAML frontmatter 是平台强制格式，不属于"用 YAML 做数据源"。

---

## 3. 目录结构与所有权

### 3.1 目录

```
shopee-br-compliance-agent/
├── PROJECT_RULES.md              ★ 公共规范（冻结）
├── AGENTS.md                     ★ Agent 协作规则（冻结）
├── manifest.json                 ★ 项目清单（冻结）
├── contracts/                    ★ 公共契约（冻结）
│   ├── README.md
│   ├── skill_input.schema.json
│   ├── audit_result.schema.json
│   ├── risk_action_matrix.json
│   ├── evidence_reference.schema.json
│   ├── rule_envelope.schema.json
│   └── module_handoff.schema.json
├── tasks/
│   ├── task_registry.json        ★ 任务注册表（冻结）
│   ├── task_template.md          ★ 任务模板（冻结）
│   └── <TASK_ID>.md              各任务说明（各 Agent 拥有）
├── skills/
│   ├── shopee-br-policy-research/
│   ├── shopee-br-listing-audit/
│   ├── shopee-br-duplicate-detection/
│   ├── shopee-br-ip-review/
│   ├── shopee-br-data-ingestion/
│   ├── shopee-br-reporting/
│   └── shopee-br-compliance/            ★ 主 Skill
├── tests/
│   ├── test_plan.md              ★ 统一测试计划（冻结）
│   ├── fixtures/                        共享测试夹具（集成 Agent 拥有）
│   └── <module>/                        各模块自有测试（各模块拥有）
├── rules/                        规则库（按模块 owner 划分）
├── lexicon/                      词库
├── data/schema/                  Schema（公共，冻结）
├── research/                     调研材料
└── docs/                         项目文档
```

> **第一阶段原型（`src/compliance_agent/`）已于 2026-10-27 归档入库**于
> `.archive/phase0_prototype/`（见 `.archive/README.md` §2.1 的结论变更记录），
> 本项目不依赖原型参考实现 —— 模块行为以 `contracts/**` 为唯一权威依据。
> 活跃工作区不设 `src/` 目录，也不预留。

### 3.2 文件所有权矩阵

**规则：每个路径有唯一 owner。其他 Agent 只读。**

| 路径 | Owner | 其他 Agent 权限 |
|---|---|---|
| `PROJECT_RULES.md` `AGENTS.md` `manifest.json` | 集成 Agent | 只读 |
| `contracts/**` | 集成 Agent | 只读 |
| `tasks/task_registry.json` `tasks/task_template.md` `tests/test_plan.md` | 集成 Agent | 只读 |
| `tasks/<自己的 TASK_ID>.md` | 任务执行 Agent | 只写自己的 |
| `skills/<module>/**` | 该模块 Agent | 只写自己的 |
| `tests/<module>/**` | 该模块 Agent | 只写自己的 |
| `rules/<module 归属文件>.json` | 该模块 Agent | 只读其他 |
| `lexicon/**` | `shopee-br-data-ingestion` | 只读 |
| `data/schema/**` | 集成 Agent | 只读（需改则提建议） |
| `research/**` | `shopee-br-policy-research` | 只读（其他可提交抓取请求） |
| `tests/fixtures/**` | 集成 Agent | 只读（需改则提建议） |

> 第一阶段原型的 `src/**` 已核实不存在（`.archive/README.md` §2.1），故不在所有权矩阵中预留。

### 3.3 规则文件归属

| 文件 | rule_id 前缀 | 条数 | Owner 模块 |
|---|---|---|---|
| `rules/01_prohibited_restricted_items.json` | `PI` `RI` | 17 | `shopee-br-listing-audit` |
| `rules/02_ip_trademark_copyright.json` | `IP` | 8 | `shopee-br-ip-review` |
| `rules/03_listing_violations_duplicates.json` | `LV` `DUP` | 17 | `shopee-br-listing-audit`（`LV`）/`shopee-br-duplicate-detection`（`DUP`）|
| `rules/04_cases_relist_authorization.json` | `RL` `AU` `AC` | 5 | `shopee-br-duplicate-detection` |
| `rules/05_medicines_health.json` | `MED` | 3 | `shopee-br-listing-audit` |

> `03_listing_violations_duplicates.json` 混有两个模块的规则前缀。**拆分动作由集成 Agent 在集成阶段执行**（避免两个 Agent 并发改同一文件）。各模块在各自任务中只提交拆分建议，不直接改该文件。

---

## 4. 契约总览

### 4.1 契约文件

| 文件 | 定义 |
|---|---|
| `contracts/skill_input.schema.json` | 所有 Skill 的**统一输入格式** |
| `contracts/audit_result.schema.json` | 所有 Skill 的**统一输出格式**（审核结果） |
| `contracts/risk_action_matrix.json` | **风险等级 × 处理动作**映射 |
| `contracts/evidence_reference.schema.json` | **证据引用**结构 |
| `contracts/rule_envelope.schema.json` | **规则信封**（规则项的统一外层格式） |
| `contracts/module_handoff.schema.json` | 模块间**交接**格式 |

### 4.2 调用约定（重要）

> 目标平台**不保证** Skill 之间存在自动调用能力。

因此主 Skill `shopee-br-compliance` **不得假设**能自动调用子模块。它必须被设计为**显式读取**各模块说明文件的工作流：

```
主 Skill 读取 skills/<module>/SKILL.md
  → 依据契约构造输入
  → 依据契约读取/请求输出
  → 依据 risk_action_matrix 整合
```

任何"自动调用"表述都视为契约违规。模块之间的实际执行由编排方（人或调度 Agent）按契约驱动。

### 4.3 数据流

```
[外部文件] ──► shopee-br-data-ingestion ──► SkillInput (契约)
                                                      │
        ┌─────────────┬──────────────┬───────────────┼─────────────┐
        ▼             ▼              ▼               ▼             ▼
  policy-research  listing-audit  duplicate-det   ip-review   (各自独立)
        │             │              │               │
        └─────────────┴──────┬───────┴───────────────┘
                             ▼
                  AuditResult[] (契约, 逐模块)
                             ▼
                    shopee-br-reporting ──► 报告
                             ▼
                    shopee-br-compliance (主 Skill 整合) ──► 最终结论
```

---

## 5. 统一输入格式

所有 Skill 接收 `SkillInput`（`contracts/skill_input.schema.json`）。

核心字段：

| 字段 | 说明 |
|---|---|
| `request_id` | 本次请求的唯一标识，用于串联多模块结果 |
| `task_type` | `policy_research` / `listing_audit` / `duplicate_detection` / `ip_review` / `ingestion` / `reporting` / `orchestration` |
| `target` | 目标对象（商品批次 / 规则库 / 数据源 / 案件库） |
| `products` | 商品数组（结构同 `data/schema/product.schema.json`） |
| `cases` | 历史案件数组（结构同 `data/schema/case.schema.json`） |
| `rules` | 规则数组（结构同 `contracts/rule_envelope.schema.json`） |
| `scope` | 生效范围（店铺、类目、时间窗） |
| `options` | 模块特定开关 |
| `provenance` | **溯源**：输入文件路径 + 内容哈希 + 解析时间 + 解析器版本 |

**`provenance` 是强制的** —— 没有溯源的输入不得进入审核链路。

---

## 6. 统一审核结果格式

所有 Skill 产出 `AuditResult[]`（`contracts/audit_result.schema.json`）。

每条结果必含：

| 字段 | 说明 |
|---|---|
| `result_id` | 唯一标识 |
| `request_id` | 关联到输入 |
| `module` | 产出该结果的模块名 |
| `target_ref` | 目标对象 ID（商品 ID / 规则 ID / 案件 ID） |
| `verdict` | 结论（见 §7） |
| `risk_level` | 风险等级（见 §7） |
| `action` | 处理动作（见 §7） |
| `reason` | 人类可读理由 |
| `rule_refs` | 命中规则引用（见 §8） |
| `evidence_refs` | 证据引用（见 §9） |
| `confidence` | `signal` / `likely` / `confirmed` |
| `requires_human_review` | 是否需人工复核 |
| `rule_version` | 规则集版本 |
| `provenance` | 结果溯源（模块版本、生成时间） |

### 6.1 三条硬约束

| # | 约束 |
|---|---|
| H1 | **IP 类结论恒为 `confidence: "signal"` 且 `requires_human_review: true`** —— 关键词或 logo 命中只是筛查信号；仅权利人投诉、书面授权或平台投诉通知可确立侵权 |
| H2 | **确定性控制不可被 AI 结论绕过** —— `action: "block"` / `"freeze_relist"` / `"escalate_legal"` 只能由 `source_tier ∈ {platform_official, law}` 的 `active` 规则产生；AI 结论（`source_tier: "ai_inference"`）最高只能到 `action: "flag_for_review"` |
| H3 | **输入缺失不等于合规** —— 规则依赖的输入字段不存在时，该规则不评估且必须产出 `unevaluated` 条目，不得静默视为通过 |

---

## 7. 风险等级与处理动作

**风险等级与处理动作分开定义**（二者正交，不构成映射函数）。映射由 `contracts/risk_action_matrix.json` 定义。

### 7.1 风险等级 `risk_level`

| 值 | 含义 |
|---|---|
| `info` | 提示性，不构成风险 |
| `low` | 低风险，可能被平台提示 |
| `medium` | 中风险，可能被下架但通常不扣分 |
| `high` | 高风险，扣分或下架 |
| `critical` | 极严重，扣分 + 可能冻结账号 |

### 7.2 处理动作 `action`

| 值 | 含义 |
|---|---|
| `allow` | 通过 |
| `flag_for_review` | 提示人工复核 |
| `require_evidence` | 需补齐指定证据后复审 |
| `revise` | 需修改内容后复审 |
| `block` | 不得上架 |
| `freeze_relist` | 冻结重发，直至案件了结 |
| `escalate_legal` | 转交法务 / PI |

### 7.3 结论 `verdict`

| 值 | 含义 |
|---|---|
| `PASS` | 通过 |
| `REVISE` | 需修改 |
| `REVIEW` | 需人工复核 |
| `BLOCK` | 阻断 |

> `verdict` 是对外汇报的聚合标签；`action` 是执行动作。映射见 `risk_action_matrix.json`。
> 聚合：`allow`→`PASS`；`flag_for_review`/`require_evidence`/`revise`→`REVIEW`（`require_evidence` 与 `revise` 可保留细粒度）；`block`/`freeze_relist`/`escalate_legal`→`BLOCK`。

---

## 8. 规则 ID 与规则信封

### 8.1 规则 ID

格式：`SBR-<类别前缀>-<3~4 位序号>`（现存规则为 3 位，如 `SBR-PI-001`）

| 前缀 | 类别 | 主责模块 |
|---|---|---|
| `PI` | Prohibited Item 禁售 | `shopee-br-listing-audit` |
| `RI` | Restricted Item 受限 | `shopee-br-listing-audit` |
| `MED` | Medicines & Health 药品 | `shopee-br-listing-audit` |
| `LV` | Listing Violation listing 违规 | `shopee-br-listing-audit` |
| `IP` | Intellectual Property | `shopee-br-ip-review` |
| `DUP` | Duplicate 重复 | `shopee-br-duplicate-detection` |
| `RL` | Relist / Freeze 重发冻结 | `shopee-br-duplicate-detection` |
| `AU` | Authorization 授权 | `shopee-br-duplicate-detection` |
| `AC` | Account 账号 | `shopee-br-duplicate-detection` |

**ID 稳定性**：规则 ID 一经发布不得复用或改指。规则重命名不得导致历史记录失去关联 —— 历史 `rule_refs` 保留旧 ID 直到迁移完成。

### 8.2 规则信封 `rule_envelope`

`contracts/rule_envelope.schema.json` 定义规则的**统一外层**：

| 字段 | 必填 | 说明 |
|---|---|---|
| `rule_id` | ✅ | 稳定 ID |
| `title` | ✅ | |
| `category` | ✅ | |
| `description` | ✅ | |
| `severity` | ✅ | 风险等级 |
| `action` | ✅ | 处理动作 |
| `source` | ✅ | `{ tier, url, excerpt, last_verified, article_id? }` |
| `status` | ✅ | `active` / `draft` / `deprecated` / `suspended` |
| `version` | ✅ | 整数 |
| `evidence_required` | ✅ | 证据类型数组 |
| `requires_human_review` | ✅ | |
| `applies_to` | | 适用范围 |
| `notes` | | |

### 8.3 来源要求（强约束）

| `source.tier` | 含义 | 可否产生 `block` 类动作 |
|---|---|---|
| `platform_official` | Shopee 官方页面明确写出 | ✅ |
| `law` | 巴西联邦法律明文 | ✅ |
| `internal_risk` | 内部风控建议 | ❌ |
| `unverified` | 未验证假设 | ❌ |
| `ai_inference` | AI 模型推断 | ❌ |
| `technical` | 技术调研结论 | ❌ |

**`source.excerpt` 必须逐字出现在 `research/raw/` 的抓取件中。** 校验工具：`tools/verify_citations.py`。**引文核验不通过 → 任务不通过。**

---

## 9. 证据引用

`contracts/evidence_reference.schema.json`：

| 字段 | 说明 |
|---|---|
| `evidence_id` | 唯一标识 |
| `evidence_type` | 类型键（如 `anvisa_registration`、`supplier_invoice`、`product_photographs`） |
| `provided` | 是否已提供 |
| `artifact_ref` | **引用**（路径或外部工单号），**不存内容** |
| `source_locator` | 原始定位（如 `row 42`、`line 7`） |
| `collected_at` | 采集时间（ISO 8601） |
| `notes` | |

**安全约束**：`artifact_ref` 只存引用，**禁止**内嵌完整凭证或授权文件内容。

---

## 10. 人工复核要求

| 条件 | `requires_human_review` |
|---|---|
| IP 类结论（`source.tier` 为 `law`/`platform_official` 但类别是 IP） | 恒为 `true` |
| `action ∈ {block, freeze_relist, escalate_legal}` | 恒为 `true` |
| `action = require_evidence` | `true` |
| 规则 `status != "active"` 或 `source.tier ∈ {internal_risk, unverified}` | `true` |
| `confidence == "signal"` | `true` |
| 输入字段缺失导致未评估 | `true` |

**自动化不得代替人工做以下决定**：解除违规冻结、处理重大 IP 投诉、修改核心规则、直接修改生产数据、变更权限配置、合并受保护主分支、删除重要历史记录。

---

## 11. 错误处理

### 11.1 四类错误状态

| 状态 | 语义 | JSON 表示 |
|---|---|---|
| `missing` | 字段存在但本次无数据 | `null` |
| `unknown` | 值存在但无法确定 | `{"state":"unknown","reason":"..."}` |
| `not_applicable` | 该对象无此字段 | `{"state":"not_applicable"}` |
| `pending_verification` | 有风险但待外部确认 | `{"state":"pending_verification","assigned_to":"...","due":"..."}` |

**禁止**用 `""` / `0` / `[]` / `{}` 混同上述四种。

### 11.2 错误记录

每个 Skill 必须在输出中携带 `errors[]`：

| 字段 | 说明 |
|---|---|
| `error_id` | 唯一标识 |
| `stage` | 出错阶段 |
| `severity` | `warning` / `error` / `fatal` |
| `message` | 人类可读消息 |
| `context` | 结构化上下文（可选） |

**规则**：
- **禁止静默丢弃任何输入。** 无法解析的记录必须产生一条 `error`。
- `fatal` 错误使该模块无法产出结果，必须显式失败而非返回空结果。
- **未评估规则**必须以 `stage: "rule_evaluation"` 的 `warning` 错误上报（契约 H3）。

---

## 12. 模块交接

`contracts/module_handoff.schema.json`：

| 字段 | 说明 |
|---|---|
| `handoff_id` | 唯一标识 |
| `from_module` / `to_module` | 交接双方 |
| `request_id` | 关联请求 |
| `payload_ref` | 载荷引用（`artifact_ref` 或内联对象） |
| `contract_version` | 契约版本 |
| `produced_at` | 产出时间 |
| `assumptions` | **该模块做出的假设**（关键：下游必须知道） |
| `known_gaps` | 已知缺口 |
| `unevaluated` | 未评估项 |

`assumptions` 与 `known_gaps` 是必填 —— 模块必须诚实声明自己的局限，不得让下游误以为结果完整。

---

## 13. 任务交付标准

每个任务交付必须包含：

### 13.1 交付物

1. **文件清单** —— 逐个列出新增/修改/删除的路径
2. **测试结果** —— 实际执行的命令与输出（**未执行的测试不得标记为通过**）
3. **未解决问题** —— 已知缺陷、未实现部分、存疑判断
4. **依赖说明** —— 对其他模块的依赖、对其他模块的期待
5. **契约变更建议**（如有）—— 按 `tasks/task_template.md` 格式

### 13.2 质量门槛

| 门 | 检查 |
|---|---|
| Q1 | 只修改了授权路径内的文件 |
| Q2 | 所有新增/修改的 JSON 通过对应 Schema 校验 |
| Q3 | 所有引文逐字核验通过 |
| Q4 | 自有测试实际执行且全部通过 |
| Q5 | 未修改任何公共契约文件 |
| Q6 | 未修改其他模块拥有的文件 |
| Q7 | `SKILL.md` 含 frontmatter、职责/非职责、输入输出契约、来源要求、失败处理、测试与验收 |
| Q8 | 交付说明完整（§13.1 五项齐全） |

---

## 14. 命名规范

| 类别 | 规则 | 示例 |
|---|---|---|
| 通用 | 英文小写 + 下划线 | `shopee-br-listing-audit` |
| Skill 目录 | `shopee-br-<domain>` | `shopee-br-ip-review` |
| Skill 指令 | 固定名 `SKILL.md` | — |
| 引用文档 | `references/<topic>.md` | `references/rule_sources.md` |
| 规则 ID | `SBR-<前缀>-<3~4 位>` | `SBR-PI-001` |
| 证据类型 | `<domain>_<subject>` | `anvisa_registration` |
| 任务 ID | `TASK-<模块>-<序号>` | `TASK-LISTING-01` |
| 契约版本 | `1.0.0` 语义化 | — |

**禁止**：含义不明的临时文件名（`tmp_x.md`、`new.json`）；用文件名日期代替版本管理。

---

## 15. 禁止事项

| # | 禁止 |
|---|---|
| N1 | 自行修改公共契约（`PROJECT_RULES.md` `AGENTS.md` `contracts/**` `manifest.json` `tasks/task_registry.json` `tasks/task_template.md` `tests/test_plan.md`） |
| N2 | 修改非自己拥有的文件 |
| N3 | 编造平台政策、法律条文、来源引文、测试结果 |
| N4 | 声称执行了未实际执行的测试 |
| N5 | 用 YAML / JSONL / CSV / TXT / XML 作内部正式数据源 |
| N6 | 假设 Skill 之间存在自动调用能力 |
| N7 | 依赖模型内部记忆或不可访问的上下文 —— 一切通过文件契约传递 |
| N8 | 在 IP 类结论中使用「侵权」表述而无投诉/授权/通知支撑 |
| N9 | 把输入缺失当作合规通过 |
| N10 | 使用平台未公开的数值（如处罚点分值）作为事实 |

---

## 16. 变更记录

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| 1.0.0 | 2026-10-27 | 初版并冻结 | 技术负责人（Agent） |
