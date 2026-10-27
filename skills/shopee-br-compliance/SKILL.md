---
name: shopee-br-compliance
description: Use when you need a complete Shopee Brazil product compliance review across title, description, attributes, images, prohibited/restricted categories, duplicates across shops, relisted violations, and IP or authorisation risk — and you need one integrated verdict with cited rules and an explicit list of what could not be evaluated. Orchestrates the specialised modules; makes no compliance determination of its own.
---

# Shopee BR 合规审核主 Skill

> 状态：**骨架 — 待 `TASK-MAIN-01` 填充**
> 契约版本：1.0.0
> 归属：`skills/shopee-br-compliance/**`、`tests/shopee-br-compliance/**`

---

## 1. 职责

| # | 职责 |
|---|---|
| 1 | 根据目标与选项决定**适用哪些模块** |
| 2 | 按契约构造每个模块的输入 |
| 3 | **显式读取**各模块的 `SKILL.md` 并按其说明驱动执行 |
| 4 | 汇总各模块结果，按 `risk_action_matrix` 整合 |
| 5 | 输出最终结论、待办事项与数据缺口 |

## 2. 非职责

- ❌ **不自己实现业务规则** —— 规则在各专业模块
- ❌ **不假设 Skill 之间存在自动调用能力**（见 §4）
- ❌ **不做任何写平台操作** —— 不发布、不改线上、不下架、不解冻、不申诉
- ❌ 不产生新的审核结论 —— 只整合
- ❌ 不代用户做业务决定

## 3. 能力边界（阶段一）

| 能力 | 状态 |
|---|---|
| 只读分析 | ✅ |
| 规则检查 | ✅ |
| 结果生成 | ✅ |
| 人工审批 | ✅（生成审批请求，不代批） |
| 发布 / 改线上 / 下架 / 解冻 / 申诉 / 处理 IP 投诉 | ❌ **不在范围**（需单独评估批准） |

---

## 4. ★ 调用语义（关键）

> **目标平台不保证 Skill 之间存在自动调用能力。**

因此本 Skill **不得**假设能直接「调用」子模块。它被设计为**显式读取模块说明文件的工作流**：

```
┌──────────────────────────────────────────────────────────────┐
│ 1. 读取 skills/<module>/SKILL.md        ← 显式读文件          │
│ 2. 依 contracts/skill_input.schema.json 构造输入            │
│ 3. 依该 SKILL.md 的「输出契约」执行并取得 AuditResult[]      │
│ 4. 依 contracts/audit_result.schema.json 校验               │
│ 5. 记录 module_handoff（含 assumptions / known_gaps）        │
└──────────────────────────────────────────────────────────────┘
```

**任何「自动调用」「函数调用子 Skill」式的表述都视为契约违规。**

当平台**确实**提供了自动调用能力时，可在执行层替换第 3 步的驱动方式，但**契约、字段、判定语义一律不变**。

---

## 5. 模块清单与分流决策表

| 模块 | 负责 | 何时必须调用 |
|---|---|---|
| `shopee-br-data-ingestion` | 多格式读取 → 统一模型 | 输入是文件/导出（几乎总是） |
| `shopee-br-policy-research` | 来源核验与规则素材 | 需要新规则或核验引文时 |
| `shopee-br-listing-audit` | 禁售/受限/listing 质量 | 商品内容审核（核心） |
| `shopee-br-duplicate-detection` | 重复/跨店/重发/授权/处罚点 | 有多商品或多店铺时 |
| `shopee-br-ip-review` | 商标/版权/外观/专利/授权 | 商品内容审核（核心） |
| `shopee-br-reporting` | 汇总与报告 | 需要人读报告时 |

### 5.1 分流决策表

| 输入情形 | 调用链 |
|---|---|
| 单个商品 + 文件 | ingestion → listing-audit → ip-review → reporting |
| 单个商品 + 已规范化 JSON | listing-audit → ip-review → reporting |
| 多商品同店 | ingestion → listing-audit → ip-review → **duplicate-detection** → reporting |
| 多商品多店 | ingestion → listing-audit → ip-review → **duplicate-detection（同一次请求内）** → reporting |
| 只需重复/重发检查 | ingestion → duplicate-detection → reporting |
| 需要新规则或核验引文 | policy-research（独立） |
| 只需汇总既有结果 | reporting（独立） |

### 5.2 执行顺序（固定）

```
ingestion → { listing-audit , ip-review , duplicate-detection } → reporting → 整合
```

**中间三个可并行**（互不依赖，路径不重叠）。`duplicate-detection` 需要 `ingestion` 的结果与 `cases[]`。

---

## 6. 规则与来源要求

主 Skill **不定义任何业务规则，也不引入新的来源判断**。它只负责：

| 资产 | 位置 | 要求 |
|---|---|---|
| 分流决策 | `references/routing.md` | 按 `tests/test_plan.md` 与 `contracts/` 决定调用哪些模块 |
| 显式工作流 | `references/execution_workflow.md` | 逐步说明如何读模块说明、构造输入、取得并校验输出 |
| 整合规则 | `references/integration_rules.md` | 聚合语义；**确定性动作只增不减** |
| 降级行为 | `references/degradation.md` | 模块不可用时如何如实报告「未执行」 |
| `docs/SOP_COMPLIANCE_REVIEW.md` | **统一审核 SOP**（合并历史全部方法） |

**来源层级的传递**：主 Skill 在整合各模块结果时，**原样保留**每条 `rule_refs[].source_tier` 与 `source_url`。它**不得**替模块重新判定来源层级，也**不得**把 `internal_risk` 提升为 `platform_official`。

**引文**：主 Skill 不新增引文，不转述平台政策。

**规则集版本**：整合结果的 `rule_version` 取各模块所用规则集版本的**共同基准**；若各模块版本不同，在 `provenance.notes` 中说明。

## 7. 输入契约

使用 `contracts/skill_input.schema.json`（v1.0.0）：

| 字段 | 本 Skill 用法 |
|---|---|
| `request_id` | 贯穿全部模块 |
| `task_type` | 固定 `orchestration` |
| `target` | `product_batch` / `data_source` / `case_history` / `audit_result_set` |
| `products[]` | 由 ingestion 填充，或调用方直接提供 |
| `cases[]` | 历史案件（重发检测必需） |
| `scope` | 生效范围，向各模块透传 |
| `options.modules` | 显式指定要调用的模块（缺省按 §5.1 决策表） |
| `options.skip_ingestion` | `true` 时跳过 ingestion（输入已是规范模型） |
| `provenance` | **由 ingestion 填充**，本 Skill 透传 |

## 8. 输出契约

产出符合 `contracts/audit_result.schema.json`（v1.0.0）的 `AuditResult[]`（逐商品最终结论），并保留：

- 每个商品的 `rule_refs[]` —— 合并全部模块的命中规则（**保留各模块的 source_tier**）
- `evidence_refs[]` —— 合并全部模块的证据要求
- `errors[]` / `unevaluated[]` —— 合并各模块的缺口
- `provenance` —— 整合者标识 + 契约版本

**整合规则**：

| 规则 | 说明 |
|---|---|
| 动作只增不减 | `block`/`freeze_relist`/`escalate_legal` 不被任何模块降级（硬约束 H2） |
| verdict 取最重 | 按 `risk_action_matrix.verdict_aggregation` |
| action 保留最细粒度 | 同上 |
| 缺口不得消失 | 任一模块的 `unevaluated` 必须出现在最终结果中 |
| IP 结论保持 signal | 不得因合并而升为 `confirmed`（硬约束 H1） |

## 9. 硬约束

| ID | 本 Skill 如何满足 |
|---|---|
| H1 | 合并时保留 `confidence="signal"` |
| **H2** | 整合单向：确定性动作只增不减 |
| H3 | 合并 `unevaluated[]`，不丢弃任何模块的缺口 |
| H4 | 规则来源与核查日期原样透传 |
| H5 | 证据只引用，不内嵌内容 |
| H6 | 不提供任何执行 `freeze_relist`/`escalate_legal` 的入口 —— 只生成建议 |

## 10. 失败处理

| 情形 | 行为 | 产出 |
|---|---|---|
| ingestion 失败 | **不继续** —— 无数据无法审核 | `error`（severity=fatal） |
| 某专业模块失败 | 其余模块继续，标注该模块缺失 | `error` + `known_gaps` |
| 某模块不可用（Skill 未安装） | 明确说明该检查**未执行**，不得当作通过 | `unevaluated` |
| 某模块无结果 | 记录为空，不得当作「无风险」 | `known_gaps` |
| `cases[]` 缺失 | 跳过重发检测，明确标注 | `unevaluated`（重发规则） |
| 契约校验失败 | 拒绝整合该模块结果 | `error` |
| 无任何模块产出 | 不生成空结论 | `error`（severity=fatal） |

**关键**：「模块不可用」必须显式报告为**未执行**，绝不能让它看起来像「检查过没问题」。

## 11. 测试案例与验收标准

| 类别 | 用例 | 断言 |
|---|---|---|
| 端到端 | 单商品 xlsx → 最终结论 | 全流程通过，产出 JSON + Markdown |
| 端到端 | 多店 xlsx → 跨店同款被识别 | 跨店比对在同一次请求内完成 |
| 分流 | 只有 `products[]`（无文件） | 跳过 ingestion |
| 分流 | 只有既有 `AuditResult[]` | 只调 reporting |
| 降级 | listing-audit 不可用 | 明确标注未执行，**不判通过** |
| 不降级 | `block` + `flag_for_review` | 最终 action 仍为 `block` |
| 缺口 | 某模块报 `unevaluated` | 最终结果含该 `unevaluated` |
| H1 | IP 结论 | 合并后仍为 `signal` |
| 契约 | 正常流程 | 输出通过 `audit_result` 校验 |
| 表述 | 全文 | 无「自动调用子 Skill」式表述 |

## 12. 依赖

- **依赖**：`TASK-LISTING-01`、`TASK-IP-01`、`TASK-DUP-01`、`TASK-REPORT-01`、`TASK-INGEST-01`
- **期待下游**：集成 Agent 做跨模块一致性验收
- **对其他模块的影响**：本模块定义了整合顺序与降级行为 —— 各模块必须能在**没有其他模块产物**的情况下独立产出合规结果

## 15. 文件所有权

本模块的路径所有权由 `contracts/file_ownership.json` 定义（`ownership_version` 1.3.0）。

**可写路径（白名单）—— 越界即任务失败：**

```
skills/shopee-br-compliance/**
tests/shopee-br-compliance/**
```

**只读路径：**

```
contracts/**
data/schema/**
rules/**
skills/*/SKILL.md
docs/parallel_execution_plan.md
docs/SOP_COMPLIANCE_REVIEW.md
lexicon/**
```

**本模块拥有的规则前缀：** 无（本模块不定义审核规则）

> 主 Skill：任务分流、显式读取模块说明、整合结果。不定义业务规则。

公共契约（`contracts/**`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、`manifest.json`、`tasks/**`、`tests/test_plan.md`、`tests/fixtures/**`、`docs/**`、`tools/**`、`scripts/**`、`.archive/**`）对所有模块 Agent **只读**。
需要修改时提交契约变更建议，不要自行改动。

## 16. 待填内容

- [ ] `references/routing.md` —— 分流决策表与边界情形
- [ ] `references/execution_workflow.md` —— 显式工作流的逐步说明
- [ ] `references/integration_rules.md` —— 整合与冲突处理
- [ ] `references/degradation.md` —— 模块缺失时的降级行为
- [ ] `tests/shopee-br-compliance/run_tests.py`

## 17. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1.0 | 2026-10-27 | 骨架创建（待 TASK-MAIN-01 填充） |
