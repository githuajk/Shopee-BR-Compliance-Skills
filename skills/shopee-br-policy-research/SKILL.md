---
name: shopee-br-policy-research
description: Use when you need to establish the authoritative basis for a Shopee Brazil compliance rule — fetching or refreshing official Seller Education Hub / Help Center policy pages, verifying that a rule's quoted source text really appears in the captured source, or maintaining the source registry and platform violation-code catalogue. Produces cited, date-stamped rule material; never produces per-listing audit verdicts.
---

# Shopee BR 官方政策研究与来源核查

> 状态：**已实现**（`TASK-POLICY-01`）
> 契约版本：1.0.0
> 归属：`skills/shopee-br-policy-research/**`、`tests/shopee-br-policy-research/**`、`research/**`

---

## 1. 职责

| # | 职责 |
|---|---|
| 1 | 抓取/刷新官方来源并保留原始抓取件（`research/raw/*.txt`） |
| 2 | 核验规则引文**逐字**出现在抓取件中（硬约束 H4） |
| 3 | 维护来源清单（`research/sources.json`）与平台违规码目录（`research/violation_codes.json`） |
| 4 | 标注来源层级 `source.tier` 与核查日期 `last_verified` |
| 5 | 核对来源清单、抓取件与抓取报告三者一致 |

## 2. 非职责

- ❌ 不对具体商品做审核判定
- ❌ 不定义审核规则（规则由各专业模块拥有）
- ❌ 不修改 `rules/**`（只读引用）
- ❌ 不做抓取之外的内容改写

## 3. 输入契约

本模块的输入是**外部政策页面**与**已有的规则库**，不是 `SkillInput`。

| 输入 | 位置 | 说明 |
|---|---|---|
| 政策页面 URL | `research/sources.json` → `url` | 待抓取或待核验的官方页面 |
| 现有规则 | `rules/*.json`（只读） | 用于核验其 `source_excerpt` 是否成立 |

## 4. 输出契约

本模块**不产出** `AuditResult[]` —— 它产出**规则素材**（供各专业模块引用）。

| 产出 | 位置 | 契约 |
|---|---|---|
| 原始抓取件 | `research/raw/<slug>.txt` | 抓取原文，含 `# title:` / `# url:` 头 |
| 来源清单 | `research/sources.json` | 每条含 `slug` / `title` / `publisher` / `url` / `tier` / `scope` |
| 违规码目录 | `research/violation_codes.json` | 每条含 `code` / `description` / `severity_pt` / `severity` / `generates_penalty_point` / `category` / `platform_code` |
| 抓取报告 | `research/raw/_fetch_report.json`、`research/raw/_edu_fetch_report.json` | 每次抓取的 HTTP 状态与实际字符数 |

**供规则引用的字段**（`contracts/rule_envelope.schema.json` 的 `source`）：

| 字段 | 含义 |
|---|---|
| `tier` | `platform_official` / `law` / `internal_risk` / `unverified` / `ai_inference` / `technical` |
| `url` | 指向具体页面的 URL |
| `excerpt` | **原文引文**，必须逐字出现在 `research/raw/` 的抓取件中 |
| `last_verified` | 核查日期（ISO 8601） |
| `article_id` | 平台文章编号（如 5139），便于定位 |
| `platform_code` | 平台违规码（如 `[337]`） |

## 5. 规则与来源要求

### 5.1 来源层级与动作上限

| `source.tier` | 含义 | 允许的最高动作 |
|---|---|---|
| `platform_official` | Shopee 官方页面明确写出 | `block` |
| `law` | 巴西联邦法律明文 | `block` |
| `technical` | 技术调研结论 | `flag_for_review` |
| `internal_risk` | 内部风控建议 | `flag_for_review` |
| `unverified` | 未验证假设 | `flag_for_review` |
| `ai_inference` | AI 模型推断 | `flag_for_review` |

**硬约束 H2**：只有 `platform_official` / `law` 的 `active` 规则能产生
`block` / `freeze_relist` / `escalate_legal`。

### 5.2 引文必须逐字可核验

```bash
env -u LD_LIBRARY_PATH python3 tools/verify_citations.py
```

**核验不通过 → 规则不得标记 `active`**。改为 `unverified` 并在交付说明中记录。
**不要**把引文改写成「看起来对」的版本。

### 5.3 禁止事项

| # | 禁止 |
|---|---|
| 1 | 引用平台**未公开的数值**作为事实（处罚点分值、OKlist 名单等） |
| 2 | 把 2026-09-15 前的政策当现状（注意 **2026-08-06** 的非处方药政策变更） |
| 3 | 把 `internal_risk` 建议表述为平台要求 |
| 4 | 编造政策条文或来源引文 |

> **关于处罚点**：平台页面明文写了「是否产生处罚点」与严重度（Alta/Média/Baixa），
> 这些**可以**引用；但具体的点数分值不可引用 —— 平台未公开。

## 6. 失败处理

| 情形 | 行为 | 产出 |
|---|---|---|
| 页面抓取失败（HTTP 5xx / 超时） | 如实登记 `capture_status: failed` | `sources.json` 标注 + 抓取报告记录 |
| 抓取到的内容过短（占位） | 报「疑似占位或抓取失败」 | `check_sources.py` 报错 |
| 引文在抓取件中找不到 | 规则改 `unverified` | `verify_citations.py` 报错 |
| 规则引用了抓取失败的来源 | **报错** —— 引文无法核验 | `check_sources.py` 报错 |
| 规则引用了未登记的来源 | 报错 | `check_sources.py` 报错 |
| 抓取报告与实际文件不一致 | 警告「报告已过期」 | `check_sources.py` 警告 |

## 7. 测试案例与验收标准

```bash
env -u LD_LIBRARY_PATH python3 tests/shopee-br-policy-research/run_tests.py
```

| 类别 | 断言 |
|---|---|
| 来源清单 | 每条来源有 tier / url / scope；tier 取值合法 |
| 抓取件 | 每条来源有对应抓取件；非空；非占位内容 |
| 一致性 | 抓取报告的字符数与实际文件一致 |
| 孤儿检测 | `research/raw/` 下无未登记的抓取件 |
| 引用完整性 | 规则的 `source_url` 已登记（按 article id 匹配，容忍域名变体） |
| 失败来源 | 抓取失败的来源**不支撑任何规则** |
| 违规码 | 106 条码有 code / description / severity / penalty 标记 |
| 引文 | 全库 50/50 逐字核验通过 |
| 禁用数值 | 规则与词库中无平台未公开的处罚点分值 |

## 8. 依赖

- **依赖**：无（可与 `shopee-br-data-ingestion` 并行）
- **期待下游**：各专业模块用本模块的 `source` 字段填规则信封
- **对其他模块的影响**：本模块决定规则的**来源可信度** —— 引文核验不过的规则不得 `active`

## 9. 工作区与抓取

工作目录 `research/`。抓取件以 `<slug>.txt` 命名，文件头两行是来源标记：

```
# title: <页面标题> | <站点名>
# url: <页面 URL>
```

**URL 域名变体**：同一篇文章在平台上有 `seller.br.shopee.cn` 与
`seller.shopee.com.br` 两个域名。校验按 **article id** 匹配，不按整条 URL。

## 10. 文件所有权

本模块的路径所有权由 `contracts/file_ownership.json` 定义（`ownership_version` 1.8.0）。

**可写路径（白名单）—— 越界即任务失败：**

```
skills/shopee-br-policy-research/**
tests/shopee-br-policy-research/**
research/sources.json
research/violation_codes.json
research/edu_articles.json
research/raw/**
```

**只读路径：**

```
contracts/**
data/schema/**
rules/**
tools/verify_citations.py
tools/validate_json.py
tools/check_sources.py
```

**本模块拥有的规则前缀：** 无。

> 不拥有任何审核规则前缀。它为其他模块提供来源与引文核验能力，
> 规则作者身份属各专业模块。

公共契约（`contracts/**`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、`manifest.json`、`tasks/**`、`tests/test_plan.md`、`tests/fixtures/**`、`docs/**`、`tools/**`、`scripts/**`、`.archive/**`）对所有模块 Agent **只读**。
需要修改时提交契约变更建议，不要自行改动。

## 11. 待填内容

- [x] `references/source_registry.md` —— 来源清单与抓取状态说明
- [x] `references/violation_codes.md` —— 违规码目录结构与解读
- [x] `references/citation_verification.md` —— 引文核验流程与常见失败原因
- [x] `references/platform_policy_summary.md` —— 政策要点摘要
- [x] `tests/shopee-br-policy-research/run_tests.py`

## 12. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-10-27 | **实现完成**（`TASK-POLICY-01`）：来源清单核对工具、17 条来源登记、106 条违规码目录、4 份参考文档填实 |
| 0.1.0 | 2026-10-27 | 骨架创建（待 TASK-POLICY-01 填充） |
