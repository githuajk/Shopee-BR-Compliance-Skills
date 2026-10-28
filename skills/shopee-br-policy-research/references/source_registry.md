| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-PR-001` |
| 所属模块 | ``shopee-br-policy-research`` |
| 版本 | 0.1.0 |
| 状态 | **Draft — 骨架，内容待 TASK-POLICY-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 官方来源的登记结构、抓取状态与核查日期管理 |
| 相关文档 | `contracts/evidence_reference.schema.json`、`research/sources.json` |
| 未决事项 | 来源分层级的具体归类规则待确定 |

---

## 1. 来源登记的三要素

每条正式规则必须能回答：**这条规则从哪来、什么时候核过、原文说了什么。**

| 要素 | 字段 | 要求 |
|---|---|---|
| 出处 | `source.url` | 必须指向可公开访问的原文页面 |
| 核查日期 | `source.last_verified` | ISO 8601 日期；超过有效期需重新核验 |
| 原文 | `source.excerpt` | **逐字**片段，必须能在 `research/raw/` 的抓取件中找到 |

> 硬约束 **H4**：`source.excerpt` 必须逐字出现在 `research/raw/*.txt` 中。
> 核验命令：`env -u LD_LIBRARY_PATH python3 tools/verify_citations.py`

## 2. 来源层级

| tier | 含义 | 可产生的最高动作 |
|---|---|---|
| `platform_official` | Shopee 官方文档（Edu Hub、卖家中心） | `block` |
| `law` | 巴西法律、ANVISA 法规 | `block` |
| `internal_risk` | 内部风控建议 | `flag_for_review` |
| `unverified` | 来源未核实 | `flag_for_review` |

**不得**把 `internal_risk` 标为 `platform_official`。这直接对应硬约束 **H2**。

## 3. 核查有效期

| 层级 | 建议有效期 | 超期处理 |
|---|---|---|
| `platform_official` | 90 天 | 重新抓取；未完成则 `last_verified` 保持原值并标 `stale` |
| `law` | 180 天 | 同上 |
| `internal_risk` | 无 | 随内部策略调整 |

## 4. 抓取流程

Shopee 卖家教育中心是**客户端渲染的 SPA**，直接 HTTP 抓取只得到空壳。必须用无头浏览器渲染后取 DOM 文本。

```bash
# 批量渲染（需先有 articles 清单）
env -u LD_LIBRARY_PATH python3 tools/fetch_edu_articles.py research/edu_articles.json
```

产物落在 `research/raw/<slug>.txt`（正文）与 `research/raw/<slug>.html`（原始页面，中间产物）。

## 5. 抓取纪律

- **不得**凭记忆编写平台政策表述 —— 必须来自抓取件。
- 抓取件**只增不改**；政策更新时新增带日期的版本文件，不覆盖历史抓取件。
- 抓取失败的 URL 记入失败清单，**不得**静默跳过。
- 引用法律条文时标注条款号与法律年份。

## 6. 待 TASK-POLICY-01 确定

- [ ] 抓取件的文件命名规范（含版本/日期）
- [ ] 政策更新后的版本比对方式
- [ ] 失败抓取的处理流程
