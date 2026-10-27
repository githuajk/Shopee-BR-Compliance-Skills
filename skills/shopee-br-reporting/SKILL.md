---
name: shopee-br-reporting
description: Use when you need to turn Shopee Brazil compliance audit results into something a reviewer can act on — aggregating results from multiple modules into one verdict, citing the exact rule and source for every finding, and producing a structured JSON summary plus a human-readable Markdown report. Aggregates only; never creates new compliance conclusions.
---

# Shopee BR 审核结果汇总与报告生成

> 状态：**骨架 — 待 `TASK-REPORT-01` 填充**
> 契约版本：1.0.0
> 归属：`skills/shopee-br-reporting/**`、`tests/shopee-br-reporting/**`

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

## 3. 输入契约

使用 `contracts/skill_input.schema.json`（v1.0.0）：

| 字段 | 本模块用法 |
|---|---|
| `request_id` | 贯穿产出 |
| `task_type` | 固定 `reporting` |
| `options.results` | 待汇总的 `AuditResult[]`（内联） |
| `options.result_files` | 待汇总的结果文件路径列表 |
| `options.format` | `json` / `markdown` / `both`（缺省 both） |
| `options.include_unevaluated` | 是否展开未评估项（缺省 true） |
| `provenance` | 原样透传 |

## 4. 输出契约

产出符合 `contracts/audit_result.schema.json`（v1.0.0）的 `AuditResult[]`（汇总后的逐商品结论），并额外产出：

| 产物 | 位置 | 说明 |
|---|---|---|
| 结构化汇总 | `out/<request_id>/audit_summary.json` | 按商品 / 按规则 / 按模块 / 按严重度分组 |
| 人读报告 | `out/<request_id>/audit_report.md` | 6 节结构（见 §6） |

汇总结果的 `module` 固定为 `shopee-br-reporting`，`action` 为聚合后的最细粒度动作。

## 5. 规则与来源要求

本模块**不定义审核规则，也不引入新的来源判断**。它只维护三类规范：

| 资产 | 位置 | 要求 |
|---|---|---|
| 报告结构 | `references/report_structure.md` | 六节固定；第 2 节（数据缺口）必须存在且独立 |
| 聚合规则 | `references/aggregation_rules.md` | 严格遵循 `contracts/risk_action_matrix.json` 的 `verdict_aggregation` |
| 证据引用 | `references/evidence_citation.md` | 规则的 `source.url` / `source.last_verified` / `source.tier` 原样透传，不改写、不补充 |

**来源层级的呈现**：报告中每条发现都要显示来源层级（`regra da plataforma` / `lei brasileira` / `sugestão de risco interno` / `hipótese não verificada`）—— 这是章程 §1.2 的要求。

**引文**：本模块不新增引文。若报告需要展示规则原文，只**引用** `rule_refs[].source_url` 指向的原文，**不得**自行转述或简化平台政策表述。

## 6. 聚合规则

严格遵循 `contracts/risk_action_matrix.json`：

### 5.1 verdict 聚合

```
verdict = max(所有结果的 verdict)   顺序: PASS < REVISE < REVIEW < BLOCK
```

### 5.2 action 粒度保留

`rule: "max_with_action_detail"` —— verdict 取最重，但 **action 保留最细粒度的那一条**。

| 例 | 输入 | 正确输出 |
|---|---|---|
| 1 | `flag_for_review` + `require_evidence` | `verdict=REVIEW`, `action=require_evidence`（不退化为笼统的 flag） |
| 2 | `require_evidence` + `block` | `verdict=BLOCK`, `action=block` |
| 3 | `allow` + `revise` | `verdict=REVISE`, `action=revise` |

### 5.3 确定性结论不可被降级

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
```

**关键**：第 2 节必须存在且独立。「未评估」绝不能混进「通过」。

## 8. 硬约束

| ID | 本模块如何满足 |
|---|---|
| H1 | 汇总时保留原 `confidence`；IP 结论在报告中标为「信号」而非结论 |
| H2 | 聚合时**只增不减**确定性动作 |
| H3 | 未评估项独立成节，**不计入通过** |
| H4 | 报告中引用的规则来源链接与核查日期原样透传 |
| **H5** | 报告中不输出凭证内容；`artifact_ref` 只作为引用 ID 出现 |
| H6 | 报告中 `freeze_relist`/`escalate_legal` 明确标注「需人工执行」 |

## 9. 失败处理

| 情形 | 行为 | 产出 |
|---|---|---|
| 部分模块结果缺失 | 正常汇总，标注缺失模块 | `known_gaps` + 报告说明 |
| 结果文件不可读 | 报文件名 | `error`（severity=error） |
| 结果不符合契约 | 报具体违规字段 | `error`（severity=error）+ 跳过该条 |
| 无任何结果 | 不生成空报告 | `error`（severity=error） |
| 报告输出目录不可写 | 明确报错 | `error`（severity=fatal） |

## 10. 测试案例与验收标准

| 类别 | 用例 | 断言 |
|---|---|---|
| 聚合 | `flag` + `require_evidence` | verdict=REVIEW，action=`require_evidence` |
| 聚合 | `require_evidence` + `block` | verdict=BLOCK，action=`block` |
| 聚合 | `allow` + `revise` | verdict=REVISE，action=`revise` |
| 不降级 | `block` + `allow` | action 仍为 `block` |
| 缺口 | 含未评估项 | 报告第 2 节存在；未评估项不计入通过数 |
| 契约 | 正常输入 | 输出通过 `audit_result` 校验 |
| 敏感 | 结果含 `artifact_ref` | 报告不含凭证内容 |
| 完整性 | 多模块结果 | 每条 result 都能在报告 §3/§4/§5 中找到 |

## 11. 依赖

- **依赖**：`TASK-POLICY-01`（来源信息用于 §6 表格）
- **期待下游**：`shopee-br-compliance`（主 Skill）消费本模块的汇总结果
- **对其他模块的影响**：本模块定义了报告的呈现结构，其他模块的 `matched_excerpt` 必须是人可读描述（不是内部 token）

## 12. 文件所有权

本模块的路径所有权由 `contracts/file_ownership.json` 定义（`ownership_version` 1.0.0）。

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

- [ ] `references/report_structure.md` —— 报告六节结构与各节内容规范
- [ ] `references/aggregation_rules.md` —— 聚合算法与边界情形
- [ ] `references/evidence_citation.md` —— 证据引用与来源呈现规范
- [ ] `tests/shopee-br-reporting/run_tests.py`

## 14. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1.0 | 2026-10-27 | 骨架创建（待 TASK-REPORT-01 填充） |
