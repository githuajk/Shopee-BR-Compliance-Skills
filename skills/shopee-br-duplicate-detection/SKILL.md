---
name: shopee-br-duplicate-detection
description: Use when you need to find duplicate or relisted Shopee Brazil listings — same-store duplicates, the same product across multiple shops, or a previously removed or suspended item re-published under a changed title or SKU. Also covers authorisation-evidence gaps, penalty points and appeal deadlines. Produces candidates for human judgement, never automatic takedowns.
---

# Shopee BR 重复刊登与违规重发检查

> 状态：**骨架 — 待 `TASK-DUP-01` 填充**
> 契约版本：1.0.0
> 规则前缀：`DUP` `RL` `AU` `AC`
> 归属：`skills/shopee-br-duplicate-detection/**`、`tests/shopee-br-duplicate-detection/**`

---

## 1. 职责

| # | 职责 | 规则前缀 |
|---|---|---|
| 1 | 同店重复刊登检测 | `DUP` |
| 2 | 跨店铺同款关联 | `DUP` |
| 3 | 历史违规重发检测与冻结建议 | `RL` |
| 4 | 品牌授权资料完整性与缺口识别 | `AU` |
| 5 | 店铺处罚点与申诉时限检查 | `AC` |

## 2. 非职责

- ❌ 不做 IP 侵权判定
- ❌ 不做商品内容合规判定
- ❌ 不解析原始文件
- ❌ **不自动下架、不自动合并、不自动解冻** —— 只产出候选与建议
- ❌ 不推断平台未公开的处罚分值

## 3. 输入契约

使用 `contracts/skill_input.schema.json`（v1.0.0）：

| 字段 | 本模块用法 |
|---|---|
| `request_id` | 贯穿产出 |
| `task_type` | 固定 `duplicate_detection` |
| `products[]` | 全部字段（身份 + 内容 + 图片） |
| `cases[]` | **历史案件** —— 重发检测的关键输入 |
| `options.cross_store` | 是否做跨店比对（缺省 true） |
| `options.similarity_threshold` | 相似度阈值（缺省按模块默认） |
| `provenance` | 原样透传 |

> **跨店比对必须在同一次请求内进行** —— 跨店关联依赖同一份索引，分两次调用无法发现跨店同款。

## 4. 输出契约

产出符合 `contracts/audit_result.schema.json`（v1.0.0）的 `AuditResult[]`：

- `module` 固定为 `shopee-br-duplicate-detection`
- `target_ref` = 被判定的商品 ID
- `rule_refs[].matched_excerpt` = **可读的证据描述**（双方 ID、匹配轴、相似度），不是内部 token
- `evidence_refs[]` = 需要的证据（`canonical_listing_id`、`variant_rationale` 等）
- `action` 可能为 `freeze_relist`（human_only）

## 5. 规则与来源要求

### 5.1 规则文件

| 文件 | 前缀 | 条数 |
|---|---|---|
| `rules/04_cases_relist_authorization.json` | `RL` `AU` `AC` | 5 |
| `rules/03_listing_violations_duplicates.json` 的 `DUP` 部分 | `DUP` | 3 |

> `rules/03` 待集成阶段拆分 —— **本模块在拆分前不得直接修改该文件**。

### 5.2 平台依据

| 平台码 | 内容 | 严重度 | 扣分 |
|---|---|---|---|
| [401] | 复制他人 listing | Baixa | 否 |
| [302] | 重复 listing | Baixa | 否 |

平台判定「重复」的标准是**同一商品无实质差异地多次刊登**（标题、描述、照片、变体都没差异）。**变体（颜色/尺码）应放在一个 listing 的变体选项里，不要开多个 listing。**

### 5.3 处罚点机制（来自 article/16316）

| 事实 | 对本模块的影响 |
|---|---|
| 处罚点每周一统一归属 | 申诉需在归属前准备 |
| 入档后一周开始执行限制，限 14–28 天 | 影响是否值得在窗口期上架 |
| 费用在处罚开始两周后扣 | — |
| 上月 GMV < R$2.500 不收该费用 | 需 `history.penalty_points` 才知道 |
| **每个已认定违规只能申诉一次** | 申诉前必须准备充分 |
| 驳回后补材料也不能撤销处罚点 | 但被下架的 listing 可申请恢复 |

> **处罚点具体分值平台未公开** —— 不得推断，不得写入规则。

## 6. 重复检测三信号

| 信号 | 强度 | 说明 |
|---|---|---|
| 身份 | **强** | 同一规范化供应商 SKU，或同一平台 PID 出现在另一店铺 |
| 内容 | 中 | 标题 token Jaccard + 字符 trigram Dice + 详情 Jaccard |
| 图片 | 弱 | 主图哈希集合 |

**候选生成**用倒排索引（按标题 token，逆文档频率排序），避免 O(n²) 全量比对。

**结论一律是「候选」** —— 平台阈值不公开，相似度阈值是我方参数。运营判断用「真同款 vs 不同商品」。

## 7. 重发检测五轴

重发的陷阱在于**它看起来不一样**：标题改了、SKU 换了、图片换了。

| 依据 | 说明 |
|---|---|
| `platform_pid` | 同一平台商品 ID |
| `supplier_sku` | 同一上游货号 |
| `internal_sku` | 同一卖家 SKU |
| `product_url` | 同一 listing 链接 |
| `content_fingerprint` | 标题/详情相似度 + 图片哈希 |

**改标题或换 SKU 不会产生一个干净的 listing** —— 它继承原案件的记录。

### 7.1 案件状态决定是否冻结

| 案件状态 | 视为已处置 | 理由 |
|---|---|---|
| `open` / `under_review` / `awaiting_evidence` | ❌ **否** | 卖家正在整改申请复核；冻结会**挡住正要提交的整改** |
| `blocked` / `relist_frozen` / `escalated` / `rejected` | ✅ 是 | 平台已实际处置 |
| 其他 + `frozen: true` | ✅ 是 | 显式冻结标记 |

## 8. 硬约束

| ID | 本模块如何满足 |
|---|---|
| H1 | 不产生 IP 结论 |
| H2 | `freeze_relist` 只来自 `platform_official` 且 `active` 的规则 + 已处置案件 |
| H3 | 缺 `cases[]` → 重发类规则未评估；缺 `shop_id` → 跨店比对未评估 |
| H4 | 引文逐字核验（当前 5/5 + DUP 3 条待拆分后核验） |
| H5 | 授权材料只存引用 |
| **H6** | `freeze_relist` 为 `human_only` —— 本模块**不提供**任何解冻执行入口 |

## 9. 失败处理

| 情形 | 行为 | 产出 |
|---|---|---|
| 无 `cases[]` | 重发检测无法进行 | `unevaluated` + warning（**不视为无重发**） |
| 单个店铺 | 跨店比对跳过 | 正常输出 + `known_gaps` 说明 |
| 相似度处于边界 | 标记需人工 | `flag_for_review` + `review_rationale` |
| 两商品疑似同款但 SKU 不同 | 仍产出候选，附全部匹配轴 | `flag_for_review` |
| 处罚点数据缺失 | 无法评估 | `unevaluated` + warning |

## 10. 测试案例与验收标准

| 类别 | 用例 | 断言 |
|---|---|---|
| 同店重复 | 同店两个相同商品 | 命中 `DUP`，产出双方 ID |
| 跨店同款 | 两店相同供应商 SKU + 相似标题 | 命中跨店规则，标 `same_shop: false` |
| 非重复 | 两个不同商品 | **不命中** |
| 重发 | 换标题 + 换 SKU 重发已下架商品 | 命中 `RL`，`action=freeze_relist` |
| 重发 | 未改动的重发 | 命中 `RL` |
| **不冻结** | 案件 `under_review`（整改中） | **不冻结**，仅 `flag_for_review` |
| 授权 | 授权材料缺项 | 命中 `AU`，列出缺失 |
| 处罚点 | 有 `penalty_points` | 命中 `AC` |
| H6 | 任意 `freeze_relist` | `requires_human_review=true` |
| H3 | 无 `cases[]` | `unevaluated` 含重发规则，**不判无重发** |
| 契约 | 正常输入 | 输出通过 `audit_result` 校验 |

## 11. 依赖

- **依赖**：`TASK-POLICY-01`（来源与引文）、`TASK-INGEST-01`（商品与历史案件）
- **期待下游**：`shopee-br-reporting` 消费本模块结果
- **对其他模块的影响**：重发冻结需与其他模块结果合并后统一呈现（避免同一商品出现多条冻结建议）

## 15. 文件所有权

本模块的路径所有权由 `contracts/file_ownership.json` 定义（`ownership_version` 1.6.0）。

**可写路径（白名单）—— 越界即任务失败：**

```
skills/shopee-br-duplicate-detection/**
tests/shopee-br-duplicate-detection/**
rules/04_cases_relist_authorization.json
```

**只读路径：**

```
contracts/**
data/schema/**
rules/03_listing_violations_duplicates.json
research/**
lexicon/term_groups.json
lexicon/non_avoidable.json
```

**本模块拥有的规则前缀：** `DUP, RL, AU, AC`

> DUP=重复刊登、RL=违规重发、AU=授权、AC=处罚点。rules/03 中 DUP 前缀归本模块；LV 前缀归 listing-audit —— 两者均只提拆分建议，不并发改写。

公共契约（`contracts/**`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、`manifest.json`、`tasks/**`、`tests/test_plan.md`、`tests/fixtures/**`、`docs/**`、`tools/**`、`scripts/**`、`.archive/**`）对所有模块 Agent **只读**。
需要修改时提交契约变更建议，不要自行改动。

## 16. 待填内容

- [ ] `references/duplicate_signals.md` —— 三信号与阈值参数
- [ ] `references/relist_axes.md` —— 五轴匹配与案件状态机
- [ ] `references/case_workflow.md` —— 案件生命周期与冻结/解冻流程
- [ ] `references/penalty_mechanics.md` —— 处罚点与申诉时限
- [ ] `tests/shopee-br-duplicate-detection/run_tests.py`

## 17. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1.0 | 2026-10-27 | 骨架创建（待 TASK-DUP-01 填充） |
