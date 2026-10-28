| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-RP-003` |
| 所属模块 | `shopee-br-reporting` |
| 版本 | 1.0.0 |
| 状态 | **Active — 已实现** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 证据与来源在报告中的引用格式 |
| 相关文档 | `contracts/evidence_reference.schema.json`、`contracts/rule_envelope.schema.json` |
| 实现 | `skills/shopee-br-reporting/src/sbr_reporting/render.py`、`rules.py` |

---

## 1. 只引用，不改写

报告展示规则时，**只引用** `source.url` 指向的原文。

**不得**自行转述或简化平台政策表述 —— 那会让报告成为"第二手规则源"，破坏可追溯性。

本模块**不新增任何引文**。它没有 `source.excerpt` 字段，也不写引文到报告里。
报告里出现的唯一「原文」是上游模块在 `rule_refs[].matched_excerpt` 里给出的
**命中片段**（商品文本里的命中部分，不是政策原文）。

| 片段类型 | 出处 | 报告中的呈现 |
|---|---|---|
| 政策原文 | `rule.source.excerpt`（规则库） | **不呈现** —— 本模块不新增引文 |
| 命中片段 | `rule_refs[].matched_excerpt` | 第 3 节「命中片段」列 |

## 2. 每条发现必须可追溯

```
发现
 ├─ 规则：SBR-PI-002「标题含禁售类目关键词」
 ├─ 来源：平台规则 ｜ <url> ｜ 核查于 2026-10-27
 ├─ 证据：EV-PI-001-01（listing_field / title）
 ├─ 命中片段：「<原文片段>」
 └─ 商品：SKU-001
```

四个要素缺一不可：**规则、来源、证据、商品**。

报告第 3 节的「命中规则与来源」表给出规则 / 标题 / 命中字段 / 命中片段 /
来源层级 / 来源链接；「证据引用」表给出证据 ID / 类型 / 已提供 / 引用 /
定位 / 备注。

## 3. 来源层级的展示

每条发现都要显示来源层级：

| 层级 | 报告中显示 |
|---|---|
| `platform_official` | 平台规则 |
| `law` | 法律规定 |
| `internal_risk` | 内部风控建议 |
| `unverified` | **待核实** |
| `ai_inference` | AI 推断 |
| `technical` | 技术调研结论 |

> 层级由规则定义，报告**只透传**，不重新判定。
> 本模块**不得**把 `internal_risk` 提升为 `platform_official`。

来源层级的取值顺序：

1. `rule_refs[].source_tier`（上游模块给的，最新）；
2. 规则库里的 `source_tier`；
3. 都没有 → `—`。

## 4. 证据引用的呈现

| 字段 | 呈现 |
|---|---|
| `evidence_id` | 显示，便于追溯 |
| `evidence_type` | 显示（证据类型键，原样） |
| `provided` | `是` / `否` |
| `artifact_ref` | 显示为路径 |
| `source_locator` | 显示（`row 42`、`line 7` 等） |
| `notes` | 显示 |
| `collected_at` | 不进报告（汇总 JSON 里保留） |

`provided: false` 的证据出现在**两个地方**：

1. 报告第 2 节的「待补齐的证据」表（按目标聚合）；
2. 报告第 3 节该目标的「证据引用」表（`已提供` 列显示「否」）。

`evidence_type: missing` 的证据项**只**出现在第 2 节 —— 它描述的是
「缺什么」，不是「命中了什么」。

## 5. 硬约束 **H5**

证据引用**只含路径与元信息**。报告**不得**内嵌授权书内容、证件号、
联系方式等凭证信息。

本模块的具体做法：

| 动作 | 说明 |
|---|---|
| `artifact_ref` | 原样透传（路径或外部工单号） |
| 引用文件的内容 | **从不读取** —— 本模块没有任何读取引用文件的代码路径 |
| `evidence_refs` 对象 | 只保留契约允许的 7 个字段，不加字段 |
| 报告渲染 | 只输出 ID / 类型 / 已提供 / 引用 / 定位 / 备注 |

`tests/shopee-br-reporting/run_tests.py` 的 H5 段断言：

- 报告里出现 `artifact_ref` 的路径；
- 报告里**不出现**凭证特征（`BEGIN CERTIFICATE`、`sk-`）；
- `evidence_refs` 对象的键集合 ⊆ 契约的 7 个字段。

## 6. 核查日期的透传

`last_verified` 来自规则库（`rules/*.json`），**原样透传**到报告第 6 节。
本模块**不**重新判断规则是否过期 —— 规则状态由各规则作者模块维护。

若上游模块在 `rule_refs[]` 里给了不同的 `source_url`，报告**以上游为准**
（上游可能刚更新过），但**不覆盖** `source_tier` —— 除非上游没给。

## 7. 长引文的截断策略

本模块**不产生**长引文。唯一的原文片段是 `matched_excerpt`，它来自商品文本，
通常在一句话以内。实现上：

| 位置 | 截断 |
|---|---|
| 报告第 3 节「命中片段」列 | 不截断（但转义 `\|` 与换行） |
| 报告第 4 节「理由」列 | 截断到 160 字符 |
| 报告第 2 节「被契约拒绝的结果」表 | 截断到 160 字符 |

完整的 `reason` 与 `matched_excerpt` 始终保留在 `audit_summary.json` 与
`audit_results.json` 里 —— 报告是摘要，不是唯一载体。

## 8. 本模块不做的事

| 不做 | 原因 |
|---|---|
| 不抓取来源页面 | 来源核验归 `shopee-br-policy-research` |
| 不校验引文是否逐字存在 | `tools/verify_citations.py` 负责；本模块只透传 `source_url` |
| 不重新判定来源层级 | 层级是规则的属性，不是报告的属性 |
| 不读取 `artifact_ref` 指向的文件 | H5 |
| 不转述平台政策 | 保持单一规则源 |
