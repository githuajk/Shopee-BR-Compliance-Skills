| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-RP-003` |
| 所属模块 | ``shopee-br-reporting`` |
| 版本 | 0.1.0 |
| 状态 | **Draft — 骨架，内容待 TASK-REPORT-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 证据与来源在报告中的引用格式 |
| 相关文档 | `contracts/evidence_reference.schema.json`、`contracts/rule_envelope.schema.json` |
| 未决事项 | 引用的展示格式待确定 |

---

## 1. 只引用，不改写

报告展示规则时，**只引用** `source.url` 指向的原文。

**不得**自行转述或简化平台政策表述 —— 那会让报告成为"第二手规则源"，破坏可追溯性。

## 2. 每条发现必须可追溯

```
发现
 ├─ 规则：SBR-PI-001「标题含禁售类目关键词」
 ├─ 来源：platform_official ｜ <url> ｜ 核查于 2026-10-27
 ├─ 证据：EV-PI-001-01（listing_field / title）
 ├─ 命中片段：「<原文片段>」
 └─ 商品：SKU-001
```

四个要素缺一不可：**规则、来源、证据、商品**。

## 3. 来源层级的展示

每条发现都要显示来源层级：

| 层级 | 报告中显示 |
|---|---|
| `platform_official` | 平台规则 |
| `law` | 法律规定 |
| `internal_risk` | 内部风控建议 |
| `unverified` | **待核实** |

> 层级由规则定义，报告**只透传**，不重新判定。

## 4. 证据引用的呈现

| 字段 | 呈现 |
|---|---|
| `evidence_id` | 显示，便于追溯 |
| `evidence_type` | 显示 |
| `artifact_ref` | 显示为路径 |
| `provided: false` | 显示为「缺失」 |
| `evidence_type: missing` | 显示在第 2 节（数据缺口） |

## 5. 硬约束 **H5**

证据引用**只含路径与元信息**。报告**不得**内嵌授权书内容、证件号、联系方式等凭证信息。

## 6. 待 TASK-REPORT-01 确定

- [ ] 展示格式的最终形态
- [ ] 长引文的截断策略
