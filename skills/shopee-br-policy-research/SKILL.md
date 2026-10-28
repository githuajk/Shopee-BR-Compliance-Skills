---
name: shopee-br-policy-research
description: Use when you need to establish the authoritative basis for a Shopee Brazil compliance rule — fetching or refreshing official Seller Education Hub / Help Center policy pages, verifying that a rule's quoted source text really appears in the captured source, or maintaining the source registry and platform violation-code catalogue. Produces cited, date-stamped rule material; never produces per-listing audit verdicts.
---

# Shopee BR 官方政策研究与来源核查

> 状态：**骨架 — 待 `TASK-POLICY-01` 填充**
> 契约版本：1.0.0
> 归属：`research/**`、`skills/shopee-br-policy-research/**`、`tests/shopee-br-policy-research/**`

---

## 1. 职责

| # | 职责 |
|---|---|
| 1 | 抓取/刷新 Shopee 巴西站官方来源，保留原始抓取件于 `research/raw/` |
| 2 | 维护来源清单 `research/sources.json`（URL、层级、抓取状态） |
| 3 | 维护平台违规码目录 `research/violation_codes.json`（代码、严重度、是否扣分） |
| 4 | 核验规则引文**逐字**出现在抓取件中 |
| 5 | 向其他模块提供带来源与核查日期的规则素材 |

## 2. 非职责

- ❌ 不对具体商品做审核判定
- ❌ 不定义审核结果格式（那是 `contracts/`）
- ❌ 不代替各审核模块写业务规则
- ❌ 不抓取需要登录态的页面（凭证管理未确认，见 `SBRCA-P0-004` Q-H）

## 3. 输入契约

使用 `contracts/skill_input.schema.json`（v1.0.0）：

| 字段 | 本模块用法 |
|---|---|
| `request_id` | 贯穿产出 |
| `task_type` | 固定 `policy_research` |
| `target.kind` | `rule_library` / `source_document` |
| `options.sources` | 待抓取的来源 slug 列表（可选，缺省=全部登记来源） |
| `options.refresh` | `true`=强制重抓，`false`=仅补缺失（默认） |
| `provenance` | **原样透传**到产出 |

## 4. 输出契约

产出符合 `contracts/audit_result.schema.json`（v1.0.0）的 `AuditResult[]`：

- `module` 固定为 `shopee-br-policy-research`
- `target_ref` = 来源 slug 或规则 ID
- `rule_refs[].source_tier` = 采集到的来源层级
- `errors[]` = 抓取失败、解析失败
- `unevaluated[]` = 未能核验的来源

## 5. 规则与来源要求

### 5.1 来源层级

见 `PROJECT_RULES.md` §8.3。本模块负责**正确标注**层级：

| 层级 | 判定标准 |
|---|---|
| `platform_official` | 抓取自 `seller.shopee.com.br` / `help.shopee.com.br` / `seller.br.shopee.cn` 的正文 |
| `law` | 抓取自 Planalto / INPI / gov.br 的法条正文 |
| `internal_risk` | 内部建议、运营经验 —— 不是平台要求 |
| `unverified` | 无法核实的说法 |

### 5.2 引文核验（硬约束 H4）

**每条引文必须逐字出现在 `research/raw/*.txt` 中。**

```bash
env -u LD_LIBRARY_PATH python3 tools/verify_citations.py
```

核验不通过时**不得**把规则标记为 `active` —— 改为 `unverified` 并说明。

### 5.3 抓取技术要点（已实测）

| 要点 | 说明 |
|---|---|
| Seller Centre 是 SPA | 正文在 `/help/api/v3/article/detail/?article_id=<id>`，直连返回 `not allowed language` |
| 必须渲染 | `tools/render_page.py` 用无头 Chromium 执行 SPA 后取 DOM |
| Chromium 路径限制 | `TMPDIR` 与 `--user-data-dir` 必须短（`/tmp`），否则 `Socket path too long` 启动即死 |
| 必须校验落地 | `Page.navigate` 后校验 `location.href`（`/json/list` 会报过期 URL） |
| Help Center 是服务端渲染 | 普通 HTTP 即可，快约 20 倍 |

## 6. 失败处理

| 情形 | 行为 | 产出 |
|---|---|---|
| 页面不可达 | 不重试超过 2 次，记录 HTTP 状态 | `error`（severity=error） |
| SPA 渲染超时 | 记录等待时长与已得字符数 | `error` + `known_gaps` |
| 引文核验失败 | 规则标 `unverified` | `warning` + 说明 |
| 平台页面改版致旧抓取件失效 | 标 `last_verified` 过期，提示需重抓 | `warning` |
| 需登录态的页面 | 明确拒绝抓取 | `error` + 说明需用户提供凭证方案 |

## 7. 测试案例与验收标准

| 类别 | 用例 | 断言 |
|---|---|---|
| 抓取 | 抓取一个未抓过的官方页面 | 产出 `research/raw/<slug>.txt` 且非空 |
| 抓取 | 重复抓取已缓存来源 | 命中缓存，不重复下载 |
| 抓取 | 抓取不存在的 URL | 产出 `error`，不崩溃 |
| 核验 | 对现存 50 条规则跑核验 | 100% 通过 |
| 核验 | 构造一条引文错误的规则 | 核验失败并被报告 |
| 目录 | 解析违规码目录 | `research/violation_codes.json` 条数与源页面一致 |
| 层级 | 内部建议 | 标 `internal_risk` 而非 `platform_official` |

## 8. 依赖

- **依赖**：无（可与 `shopee-br-data-ingestion` 并行）
- **期待下游**：`listing-audit` / `ip-review` / `duplicate-detection` / `reporting` 使用本模块产出的来源与引文
- **对其他模块的影响**：本模块的层级标注直接决定其他模块哪些规则能产生阻断类动作

## 12. 文件所有权

本模块的路径所有权由 `contracts/file_ownership.json` 定义（`ownership_version` 1.6.0）。

**可写路径（白名单）—— 越界即任务失败：**

```
skills/shopee-br-policy-research/**
tests/shopee-br-policy-research/**
research/sources.json
research/violation_codes.json
research/edu_articles.json
research/raw/**
tools/check_sources.py
```

**只读路径：**

```
contracts/**
data/schema/**
rules/**
tools/verify_citations.py
tools/validate_json.py
tools/render_page.py
tools/cdp_client.py
tools/fetch_sources.py
tools/fetch_edu_articles.py
tools/fetch_edu_article.py
tools/parse_violation_codes.py
tools/dump_page_text.py
tools/inspect_page.py
tools/capture_api.py
```

**本模块拥有的规则前缀：** 无（本模块不定义审核规则）

> 不拥有任何审核规则前缀。它为其他模块提供来源与引文核验能力，规则作者身份属各专业模块。

公共契约（`contracts/**`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、`manifest.json`、`tasks/**`、`tests/test_plan.md`、`tests/fixtures/**`、`docs/**`、`tools/**`、`scripts/**`、`.archive/**`）对所有模块 Agent **只读**。
需要修改时提交契约变更建议，不要自行改动。

## 13. 待填内容

- [ ] `references/source_registry.md` —— 来源清单与抓取状态说明
- [ ] `references/violation_codes.md` —— 违规码目录结构与解读
- [ ] `references/citation_verification.md` —— 引文核验流程与常见失败原因
- [ ] `references/platform_policy_summary.md` —— 政策要点摘要（禁限售类目、处罚机制、IP 四类）
- [ ] `tests/shopee-br-policy-research/run_tests.py`

## 14. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1.0 | 2026-10-27 | 骨架创建（待 TASK-POLICY-01 填充） |
