---
name: shopee-br-reporting
description: Use when you need to turn Shopee Brazil compliance audit results into something a reviewer can act on — aggregating results from multiple modules into one verdict, citing the exact rule and source for every finding, and producing a structured JSON summary plus a human-readable Markdown report. Aggregates only; never creates new compliance conclusions.
---

# Shopee BR 审核结果汇总与报告生成

> 状态：**已实现**（`TASK-REPORT-01`）
> 契约版本：1.0.0
> 归属：`skills/shopee-br-reporting/**`、`tests/shopee-br-reporting/**`
> 实现：`skills/shopee-br-reporting/src/sbr_reporting/`（纯标准库，无第三方依赖）

---

## 1. 职责

| # | 职责 |
|---|---|
| 1 | 汇总多模块的 `AuditResult[]` |
| 2 | 按 `contracts/risk_action_matrix.json` 聚合 verdict 与 action |
| 3 | 为每条发现附上规则、来源、命中片段 |
| 4 | 生成结构化 JSON 汇总 + 人读 Markdown 报告 |
| 5 | **显式呈现未评估项与数据缺口** |

## 2. 非职责

- ❌ **不产生新的审核结论** —— 只汇总，不判断
- ❌ 不修改规则
- ❌ 不做合规判定
- ❌ 不把未评估项写成「通过」
- ❌ 不在报告中输出凭证内容
- ❌ **不执行任何平台动作** —— 不发布、不下架、不解冻、不申诉、不处理 IP 投诉
- ❌ 不假设 Skill 间自动调用（见 `AGENT_COLLABORATION.md` §4 / `PROJECT_RULES.md` §4.2）
- ❌ 不读取 `artifact_ref` 指向的凭证文件

## 3. 输入契约

使用 `contracts/skill_input.schema.json`（v1.0.0）：

| 字段 | 本模块用法 |
|---|---|
| `request_id` | 贯穿产出；每份结果与交接都必须回填 |
| `task_type` | 固定 `reporting` |
| `target` | 本次审核对象的引用（`audit_result_set`） |
| `products[]` | 可选 —— 用于在报告第 5 节显示 SKU 与店铺 |
| `options.results` | 待汇总的 `AuditResult[]`（内联） |
| `options.result_files` | 待汇总的结果文件路径列表（可重复） |
| `scope` | 范围限定（店铺、日期、商品集） |
| `provenance` | **强制** —— 原样透传并在结果中回填 |

### 3.1 结果来源的两种形态

`options.results`（内联）与 `options.result_files`（文件）都可独立使用，也可同时使用。

**结果文件的内部形态**（本模块定义，三种都接受）：

| 形态 | 说明 |
|---|---|
| `AuditResult[]` | 裸数组 |
| 单个 `AuditResult` | 单对象 |
| `{"results": [...]}` | 包裹对象（也接受 `audit_results` / `audit_result` 键） |

> **输入格式说明**：上游模块（`listing-audit` / `duplicate-detection` / `ip-review`）
> 在本任务开工时尚未就绪，因此本模块**按契约自行定义**了上述输入格式。
> 交付时 `shopee-br-listing-audit` 已就绪并通过集成验证（见 §10 的集成用例）：
> 它以 `target_ref = product_id` 聚合，`module` 为契约枚举内的模块名，
> `rule_refs[].source_tier` 已填 —— **本模块的输入适配与它直接兼容，无需改动**。
> 另两个模块就绪后若格式不一致，以 `contracts/audit_result.schema.json` 为准 ——
> 本模块对每条输入都做契约校验，不符合的会被跳过并记 `error`，不会污染聚合。

### 3.2 未知选项必须忽略

契约要求模块「只读取自己认识的键，未知键必须忽略而非报错」。
本模块只读 `options.results` 与 `options.result_files`，其余键一律忽略。

## 4. 输出契约

产出符合 `contracts/audit_result.schema.json`（v1.0.0）的 `AuditResult[]`
（逐目标结论 + 1 条整批结论），并额外产出：

| 产物 | 位置 | 说明 |
|---|---|---|
| 结构化汇总 | `out/<request_id>/audit_summary.json` | 按商品 / 按规则 / 按模块 / 按严重度分组 |
| 人读报告 | `out/<request_id>/audit_report.md` | 6 节结构 + 硬约束清单（见 §6） |
| 聚合结果 | `out/<request_id>/audit_results.json` | `AuditResult[]` |
| 交接记录 | `out/<request_id>/module_handoff.json` | `contracts/module_handoff.schema.json` |

汇总结果的 `module` 固定为 `shopee-br-reporting`，`action` 为聚合后的最细粒度动作。

### 4.1 交接记录的必填项

`assumptions` 与 `known_gaps` **必须填写**（契约 `minItems: 1`）。
即使某一项确实为空，也必须写明「本次无 XX」并解释原因 —— 不得留空数组。

## 5. 规则与来源要求

本模块**不定义审核规则，也不引入新的来源判断**。它只维护三类规范：

| 资产 | 位置 | 要求 |
|---|---|---|
| 报告结构 | `references/report_structure.md` | 六节固定；第 2 节（数据缺口）必须存在且独立 |
| 聚合规则 | `references/aggregation_rules.md` | 严格遵循 `contracts/risk_action_matrix.json` 的 `verdict_aggregation` |
| 证据引用 | `references/evidence_citation.md` | 规则的 `source.url` / `source.last_verified` / `source.tier` 原样透传，不改写、不补充 |

**来源层级的呈现**：报告中每条发现都要显示来源层级（`平台规则` / `法律规定` /
`内部风控建议` / `待核实` / `AI 推断` / `技术调研结论`）—— 这是章程 §1.2 的要求。

**引文**：本模块不新增引文。若报告需要展示规则原文，只**引用** `rule_refs[].source_url`
指向的原文，**不得**自行转述或简化平台政策表述。

### 5.1 动作的来源限制

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

### 5.2 规则状态与时效

只有 `status = active` 的规则能产生 `block`。过期规则降级为 `stale`，只产出 `flag`。
本模块**不重新判定**规则状态 —— 它只透传规则库里的元信息，并把阻断类动作的
来源层级交由 H2 校验。

## 6. 聚合规则

严格遵循 `contracts/risk_action_matrix.json`：

### 6.1 verdict 聚合

```
verdict = max(所有清洗后 action 所隐含的 verdict)
顺序: PASS < REVISE < REVIEW < BLOCK
```

**verdict 永远由 action 推导**，绝不采用输入自报的 verdict 覆盖 —— 否则
`internal_risk` 规则自报 `verdict=BLOCK` 就能绕过 H2。

### 6.2 action 粒度保留

`rule: "max_with_action_detail"` —— verdict 取最重，但 **action 保留最细粒度的那一条**。

| 例 | 输入 | 正确输出 |
|---|---|---|
| 1 | `flag_for_review` + `require_evidence` | `verdict=REVIEW`, `action=require_evidence`（不退化为笼统的 flag） |
| 2 | `require_evidence` + `block` | `verdict=BLOCK`, `action=block` |
| 3 | `allow` + `revise` | `verdict=REVISE`, `action=revise` |
| 4 | `block` + `escalate_legal` | `verdict=BLOCK`, `action=escalate_legal` |

### 6.3 确定性结论不可被降级

`action ∈ {block, freeze_relist, escalate_legal}` 的结论**只增不减** —— 任何来源的结果都不能把它降为 `flag_for_review`。

## 7. 报告结构

```markdown
# Shopee BR 合规审核报告

## 1. 摘要
   范围、商品数、结论分布、发现数、未评估数

## 2. 数据缺口与未评估项        ← 与「通过」明确分区
   哪些规则没跑、因为什么缺什么字段、需要补什么数据

## 3. 需决策的发现
   逐条：商品 → 规则 → 依据（引文 + 来源链接）→ 建议动作 → 责任人

## 4. 待复核的发现
   表格：发现 / 商品 / 规则 / 严重度 / 动作 / 置信度

## 5. 逐商品结果
   表格：商品 / SKU / 店铺 / 结论 / 动作 / 命中规则

## 6. 已查阅规则
   表格：规则 / 类别 / 严重度 / 动作 / 来源层级 / 核查日期

## 硬约束
   H1–H6 的执行自检
```

**关键**：第 2 节必须存在且独立。「未评估」绝不能混进「通过」。

## 8. 硬约束

| ID | 本模块如何满足 |
|---|---|
| H1 | 汇总时置信度**取最弱**（`signal` 不会被合并成 `confirmed`）；IP 结论在报告中标为「信号」而非结论 |
| H2 | 清洗阶段校验来源层级：`internal_risk` / `unverified` / `ai_inference` / `technical` / 无层级的阻断类动作一律降为 `flag_for_review`，并记 `error` |
| H3 | 未评估项独立成节，**不计入通过**；目标含 `unevaluated` 时 verdict 不得为 `PASS`，自动升为 `REVIEW` |
| H4 | 本模块不新增引文；报告中引用的规则来源链接与核查日期原样透传 |
| **H5** | 报告中不输出凭证内容；`artifact_ref` 只作为引用 ID 出现，且本模块从不读取被引用的文件 |
| H6 | 报告中 `freeze_relist`/`escalate_legal` 明确标注「需人工执行」；本模块不提供任何执行入口 |

### 8.1 规则级结论与契约级 verdict 的区分

本模块**不产生**规则级结论 —— 它只做两件事，且**必须分开呈现**：

| 概念 | 含义 | 载体 |
|---|---|---|
| **规则级结论** | 某条规则是否命中、命中了商品的哪个字段 | `rule_refs[]`（含 `rule_id` / `matched_field` / `matched_excerpt` / `source_tier`） |
| **契约级 verdict** | 对外汇报的聚合标签（4 值） | `verdict` 字段（`PASS` / `REVISE` / `REVIEW` / `BLOCK`） |

规则级结论**不得**被当作契约级 verdict —— `pass` / `flag` / `not_evaluated` /
`signal` 都**不是**契约 verdict 的取值。报告第 3/4 节展示规则级细节，
第 5 节的「结论」列才是契约级 verdict。

## 9. 失败处理

| 情形 | 行为 | 产出 |
|---|---|---|
| 部分模块结果缺失 | 正常汇总，标注缺失模块 | `known_gaps` + 报告说明 |
| 结果文件不可读 | 报文件名，**不中断整批** | `error`（severity=error） |
| 结果不符合契约 | 报具体违规字段 | `error`（severity=error）+ 跳过该条 |
| 无任何结果 | 不生成空报告 | `error`（severity=error） |
| 报告输出目录不可写 | 明确报错 | `error`（severity=fatal） |
| 契约矩阵缺失或不可解析 | 停止本模块，不自造映射 | `error`（severity=fatal） |
| 结果无 `target_ref` | 跳过并记 error | `error`（severity=error） |
| 依赖模块不可用 | 标记该维度未评估 | `assumptions` / `known_gaps` |

> **绝不静默丢弃。** 每条输入要么产出结论，要么产出错误说明。

## 10. 测试案例与验收标准

测试文件：`tests/shopee-br-reporting/run_tests.py`（162 项断言）。

| 类别 | 用例 | 断言 |
|---|---|---|
| 聚合 | `flag_for_review` + `require_evidence` | verdict=REVIEW，action=`require_evidence` |
| 聚合 | `require_evidence` + `block` | verdict=BLOCK，action=`block` |
| 聚合 | `allow` + `revise` | verdict=REVISE，action=`revise` |
| 聚合 | `block` + `escalate_legal` | verdict=BLOCK，action=`escalate_legal` |
| 不降级 | `block` + `allow` | action 仍为 `block` |
| 缺口 | 含未评估项 | 报告第 2 节存在；未评估项不计入通过数；verdict 升为 REVIEW |
| 契约 | 正常输入 | 输出通过 `audit_result` 与 `module_handoff` 校验 |
| 契约 | 缺失必需字段 | `unevaluated[]` 非空，**不产生** `PASS` |
| 正例 | 典型命中 | `verdict` 与 `action` 符合矩阵 |
| **反例** | 正常商品 | **不命中**，`verdict = PASS` |
| 边界 | 字段存在但为空 | 等同缺失 → 未评估 |
| 失败路径 | 输入不可读 | 记 error，不中断整批 |
| 硬约束 | H2 尝试用 `internal_risk` 产生 `block` | 被拒，降为 `flag_for_review` |
| 硬约束 | H3 缺字段 | 报 `unevaluated`，不计为通过 |
| 硬约束 | H1 合并 | `signal` 不升为 `confirmed` |
| 硬约束 | H5 凭证 | 报告不含凭证内容 |
| 硬约束 | H6 human_only | 报告标注「需人工执行」 |
| 敏感 | 结果含 `artifact_ref` | 报告不含凭证内容 |
| 完整性 | 多模块结果 | 每条 result 都能在报告 §3/§4/§5 中找到 |
| 报告 | 六节结构 | 顺序固定；第 2 节独立；空值显示「无」 |
| 端到端 | CLI 产出四份文件 | 均可被契约校验 |
| 集成 | 真实 `shopee-br-listing-audit` 产出 | 39 条真实结果可直接消费，0 错误 |
| 引文 | 全库核验 | `tools/verify_citations.py` 0 failed |

## 11. 依赖

- **依赖**：`TASK-POLICY-01`（来源信息用于 §6 表格）、`contracts/risk_action_matrix.json`（聚合语义）、`rules/**`（规则元信息，只读）
- **期待下游**：`shopee-br-compliance`（主 Skill）消费本模块的汇总结果
- **对其他模块的影响**：本模块定义了报告的呈现结构，其他模块的 `matched_excerpt` 必须是人可读描述（不是内部 token）

### 11.1 上游模块需要提供的输入格式

本模块**声明**期望的输入（`AGENT_COLLABORATION.md` §5.2）：

| 字段 | 期望 |
|---|---|
| `result_id` | ≥ 4 字符，全局唯一 |
| `request_id` | 与本批一致 |
| `module` | 契约枚举内的模块名 |
| `target_ref` | 商品 ID（同一商品的多条结果靠它聚合） |
| `verdict` | `PASS` / `REVISE` / `REVIEW` / `BLOCK` |
| `risk_level` | `info` / `low` / `medium` / `high` / `critical` |
| `action` | 契约枚举内的 7 个动作之一 |
| `rule_refs[].source_tier` | **必填** —— 阻断类动作靠它满足 H2 |
| `rule_refs[].matched_excerpt` | 人可读的命中片段（不是内部 token） |
| `evidence_refs[].artifact_ref` | 只放路径或工单号，**不放凭证内容** |
| `unevaluated[]` | 缺输入而未评估的规则（缺了就别静默当通过） |

## 12. 文件所有权

本模块的路径所有权由 `contracts/file_ownership.json` 定义（`ownership_version` 1.8.0）。

**可写路径（白名单）—— 越界即任务失败：**

```
skills/shopee-br-reporting/**
tests/shopee-br-reporting/**
```

**只读路径：**

```
contracts/**
data/schema/**
rules/**
skills/*/SKILL.md
```

**本模块拥有的规则前缀：** 无（本模块不定义审核规则）

> 不定义规则、不引入来源判断。只做聚合、证据引用与报告渲染。

公共契约（`contracts/**`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、`manifest.json`、`tasks/**`、`tests/test_plan.md`、`tests/fixtures/**`、`docs/**`、`tools/**`、`scripts/**`、`.archive/**`）对所有模块 Agent **只读**。
需要修改时提交契约变更建议，不要自行改动。

## 13. 待填内容

- [x] `references/report_structure.md` —— 报告六节结构与各节内容规范
- [x] `references/aggregation_rules.md` —— 聚合算法与边界情形
- [x] `references/evidence_citation.md` —— 证据引用与来源呈现规范
- [x] `tests/shopee-br-reporting/run_tests.py` —— 162 项断言

**尚待上游就绪后补充**（非本任务范围）：

- [ ] `shopee-br-duplicate-detection` / `shopee-br-ip-review` 的真实产出接入 ——
      交付时这两个模块仍在并行开发中；本模块的输入适配对它们同样适用
      （按 `contracts/audit_result.schema.json` 校验 + 按 `target_ref` 聚合），
      但**未做实测验证**
- [ ] 与主 Skill `shopee-br-compliance` 的端到端联调（属 `TASK-MAIN-01`）

## 14. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1.0 | 2026-10-27 | 骨架创建（待 TASK-REPORT-01 填充） |
| 1.0.0 | 2026-10-27 | `TASK-REPORT-01` 实现：聚合引擎（矩阵驱动）、契约校验、报告渲染、CLI、162 项测试；三份 references 填实 |
