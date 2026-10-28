| 字段 | 值 |
|---|---|
| 任务 ID | `TASK-LISTING-01` |
| 归属模块 | `shopee-br-listing-audit` |
| 并行组 | `G3` |
| 状态 | completed |
| 契约版本 | 1.0.0 |
| 回填日期 | 2026-10-28 |
| 负责 Agent | <你的标识> |
| 工作区 | `/tmp/sbrca_work/TASK-LISTING-01/` |
| 开始时间 | （待填） |

> **本任务包是自包含的。** 你不需要阅读本项目的其它历史文档即可开工。
> 开工前只需读：本文件 + `PROJECT_RULES.md` + `AGENT_COLLABORATION.md` + `contracts/` 全部。

---

## 1. 目标

建立商品内容合规审核能力：检查标题、详情、属性、图片与宣传内容中的禁售、受限、刊登质量与药品健康类风险，产出可追溯的结论。

完成后 `shopee-br-listing-audit` 模块可独立运行、产出符合契约的审核结果，且自带可执行的测试。

## 2. 范围

### 2.1 允许修改的路径（白名单）

```
skills/shopee-br-listing-audit/**
tests/shopee-br-listing-audit/**
rules/01_prohibited_restricted_items.json
rules/05_medicines_health.json
rules/03_listing_violations.json
tools/scan_lexicon.py
```

> 词库文件（`lexicon/**` 六件）自 1.8.0 起单一归属 `shopee-br-data-ingestion`；
> 本任务只读消费词库。

**越界即任务失败。** 若确需修改白名单外的路径 → 停止并在 §12.5 提交契约变更建议，**不要自行修改**。

### 2.2 只读路径

```
contracts/**
data/schema/**
lexicon/term_groups.json
lexicon/exemptions.json
research/**
```

全局只读（所有模块通用）：`contracts/**`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、
`manifest.json`、`tasks/**`、`tests/test_plan.md`、`tests/fixtures/**`、`docs/**`、
`tools/**`、`scripts/**`、`.archive/**`。

> 路径所有权由 `contracts/file_ownership.json` 定义，这是唯一权威来源。

### 2.3 明确不做

- 不修改公共契约与他人拥有的文件
- 不实现其他模块的职责
- 不假定平台提供 Skill 间自动调用能力
- 不编造平台政策、法律条文或测试结果
- 不自动执行任何线上处置（发布/删除/冻结/申诉）

## 3. 前置条件

| 依赖任务 | 状态 | 依赖它什么 |
|---|---|---|
| `TASK-POLICY-01` | pending | 见 tasks/task_registry.json |
| `TASK-INGEST-01` | pending | 见 tasks/task_registry.json |

**开工前确认所有依赖已完成。** 未完成则等待，不要基于假设开工。

## 4. 输入契约

使用 `contracts/skill_input.schema.json`（v1.0.0）。

| 字段 | 本模块怎么用 |
|---|---|
| `request_id` | 贯穿全部产出；每份结果与交接都必须回填 |
| `task_type` | 决定执行哪个流程分支 |
| `target` | 本次审核对象的引用 |
| `products[]` | **核心输入** —— 待审核商品；每项符合 `data/schema/product.schema.json` |
| `cases[]` | 历史案件（仅 `shopee-br-listing-audit` 关注） |
| `rules[]` | 参与判定的规则；缺省时从本模块拥有的规则文件加载 |
| `scope` | 范围限定（店铺、日期、商品集） |
| `options` | 模块私有选项 |
| `provenance` | **强制** —— 数据来源；本模块必须原样传递并在结果中回填 |

## 5. 输出契约

产出符合 `contracts/audit_result.schema.json`（v1.0.0）的 `AuditResult[]`。

| 字段 | 本模块的取值 |
|---|---|
| `module` | 固定为 `shopee-br-listing-audit` |
| `verdict` | `PASS` / `REVISE` / `REVIEW` / `BLOCK` |
| `risk_level` | `info` / `low` / `medium` / `high` / `critical` |
| `action` | 由 `contracts/risk_action_matrix.json` 查表决定，**不得自行决定** |
| `reason` | 一句话说明**为什么**，须能回溯到具体规则与证据 |
| `rule_refs[]` | 命中的规则；每条含 `rule_id` + `source`（tier/url/excerpt/last_verified） |
| `evidence_refs[]` | 证据引用；**只存路径，不存内容**（硬约束 H5） |
| `confidence` | `signal` / `likely` / `confirmed` |
| `requires_human_review` | 由矩阵与硬约束决定 |
| `unevaluated[]` | 因输入缺失而未评估的项（硬约束 H3） |
| `provenance` | 原样传递输入的溯源信息 |

> **枚举权威来源**：`contracts/audit_result.schema.json`（冻结）。
> 上述取值即该 Schema 的 `enum` 值，**不得**自造其它拼写。
> `verdict` 是对外汇报的聚合标签（4 值）；`action` 是执行动作（7 值）。两者正交，**不是**一一映射。

同时产出 `contracts/module_handoff.schema.json` 格式的交接记录：
`assumptions` 与 `known_gaps` **必须填写**（无则填空数组，但需在 `notes` 说明）。

## 6. 规则与来源要求

### 6.1 规则归属

| 项 | 值 |
|---|---|
| 本模块拥有的规则前缀 | `PI`, `RI`, `MED`, `LV` |
| 可写的规则文件 | rules/01_prohibited_restricted_items.json
rules/05_medicines_health.json |

### 6.2 来源层级与动作限制

| `source.tier` | 允许的最高动作 |
|---|---|
| `platform_official` | `block` |
| `law` | `block` |
| `technical` | `flag_for_review` |
| `internal_risk` | `flag_for_review` |
| `unverified` | `flag_for_review` |
| `ai_inference` | `flag_for_review` |

**不得**把 `internal_risk` 标为 `platform_official`。硬约束 **H2**：阻断类动作只能来自
`platform_official` / `law` 的 `active` 规则。

> 上表来自 `contracts/risk_action_matrix.json` 的 H2 条款，取值与冻结契约一致，**不得**自造。
> `technical` / `internal_risk` / `unverified` / `ai_inference` 四档最高只能到 `flag_for_review`。

### 6.3 引文必须逐字可核验

```bash
env -u LD_LIBRARY_PATH python3 tools/verify_citations.py
```

引文核验不通过 → 规则不得标记 `active`；改为 `unverified` 并在 §12.3 说明。

### 6.4 规则状态与时效

只有 `status = active` 的规则能产生 `block`。过期规则降级为 `stale`，只产出 `flag`。

## 7. 硬约束自检

实现时逐条确认，并在 §12.6 勾选：

| ID | 约束 | 本任务如何满足 |
|---|---|---|
| H1 | IP 类结论恒为 `signal` + 强制人工复核 | 本模块不产生 IP 类结论（如产生则适用） |
| H2 | `block`/`freeze_relist`/`escalate_legal` 只来自 `platform_official`/`law` 的 `active` 规则；确定性结论不可被降级 | 查 `contracts/risk_action_matrix.json` 决定动作，不自行判断 |
| H3 | 输入缺失 → 该规则不评估 + 必须上报 `unevaluated`；**不得当作通过** | 实现 `requires_input` 检查，缺失字段记入 `unevaluated[]` |
| H4 | `source.excerpt` 必须逐字出现在 `research/raw/` 抓取件中 | 跑 `tools/verify_citations.py` 并贴出输出 |
| H5 | `artifact_ref` 只存引用，不内嵌凭证内容 | 证据只写路径与元信息 |
| H6 | `freeze_relist`/`escalate_legal` 为 `human_only` | 只建议，不自动执行 |

## 8. 失败处理

| 失败情形 | 本模块的行为 | 产出 |
|---|---|---|
| 输入文件不可读 | 记 error，**不中断整批** | `errors[]` |
| 必需字段缺失 | 该规则标记未评估 | `unevaluated[]` + `errors[]` |
| 规则引文核验失败 | 规则改 `unverified`，只产出 `flag_for_review` | 规则 `status` 变更 |
| 依赖模块不可用 | 标记该维度未评估 | `assumptions` / `known_gaps` |
| 无法判定 | **不猜测** | 标记需人工复核 |
| 规则文件缺失或不可解析 | 记 error 并停止该模块 | `errors[]` + 交接 `known_gaps` |

> **绝不静默丢弃。** 每条输入要么产出结论，要么产出错误说明。

## 9. 测试计划

测试文件位置：`tests/shopee-br-listing-audit/`

| 类别 | 用例 | 断言 | 状态 |
|---|---|---|---|
| 契约 | 正常输入 | 输出通过 `audit_result.schema.json` 校验 | |
| 契约 | 缺失必需字段 | `unevaluated[]` 非空，**不产生** `PASS` | |
| 正例 | 典型命中 | `verdict` 与 `action` 符合矩阵 | |
| **反例** | 正常商品 | **不命中**，`verdict = PASS` | |
| 边界 | 字段存在但为空 | 等同缺失 → 未评估 | |
| 失败路径 | 输入不可读 | 记 error，不中断整批 | |
| 硬约束 | H2 尝试用 `internal_risk` 产生 `block` | 被拒，降为 `flag_for_review` | |
| 硬约束 | H3 缺字段 | 报 `unevaluated`，不计为通过 | |

**每条规则必须有正例与反例。** 反例缺失的规则不得标记 `active`。

测试必须**实际执行**并把输出贴进 §12.2。

## 10. 验收标准

- [ ] 本模块的 `SKILL.md` 七要素齐全（frontmatter、职责/非职责、输入契约、输出契约、规则与来源要求、失败处理、测试案例与验收标准）
- [ ] `references/` 下每个声明的文件都存在且有实质内容
- [ ] 自有测试实际执行并贴出输出
- [ ] 所有引文逐字核验通过（`tools/verify_citations.py`）
- [ ] 只改了 §2.1 白名单内的文件
- [ ] 未修改公共契约
- [ ] 未修改他人拥有的文件
- [ ] 所有 JSON 通过 Schema 校验
- [ ] 硬约束 H1–H6 逐条自查并勾选
- [ ] §12.3 已列出未解决问题（含仍为占位符的 references 内容）

## 11. 交付物

| 交付物 | 位置 |
|---|---|
| 模块说明 | `skills/shopee-br-listing-audit/SKILL.md`（七要素齐全） |
| 参考文档 | `skills/shopee-br-listing-audit/references/*.md`（**填实内容，不留占位符**） |
| 测试 | `tests/shopee-br-listing-audit/run_tests.py` + 测试数据 |
- 规则更新 | rules/01_prohibited_restricted_items.json
rules/05_medicines_health.json
- 交接记录 | `contracts/module_handoff.schema.json` 格式 |

## 12. 交付说明

> 交付时按 `AGENT_COLLABORATION.md` §8 填写以下六段。**不得留空。**

### 12.1 文件清单

| 路径 | 动作 | 说明 |
|---|---|---|
| | 新增/修改/删除 | |

### 12.2 测试结果

实际执行的命令与输出：

```
<命令>
<输出摘要>
```

未执行的测试及原因：

| 测试 | 原因 |
|---|---|

### 12.3 未解决问题

| # | 问题 | 影响 | 建议 |
|---|---|---|---|

### 12.4 依赖说明

- 我依赖的：
- 我期待下游提供的：
- 我对其他模块的影响：

### 12.5 契约变更建议（如有）

- **问题**：
- **证据**：
- **建议变更**：
- **影响面**：
- **严重度**：blocking / non-blocking

> 若无，请在 §12.3 写明"无契约变更建议"。

### 12.6 自我约束核查

- [ ] 只改了白名单内的文件
- [ ] 未修改公共契约
- [ ] 未修改他人拥有的文件
- [ ] 引文核验通过
- [ ] 自有测试实际执行
- [ ] SKILL.md 七要素齐全
- [ ] references/ 内容已填实（无占位符）
- [ ] 硬约束 H1–H6 已逐条自查
