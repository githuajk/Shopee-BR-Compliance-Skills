#!/usr/bin/env python3
"""生成剩余 references/ 骨架文件。

每份文件带完整元信息头与所属模块的特有内容，不含无意义占位符。
用法：python3 tools/gen_references.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

META = """| 字段 | 值 |
|---|---|
| 文档 ID | `{doc_id}` |
| 所属模块 | `{module}` |
| 版本 | 0.1.0 |
| 状态 | **Draft — 骨架，内容待 {task} 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | {scope} |
| 相关文档 | {related} |
| 未决事项 | {open} |

---
"""

FILES = [
    # ---------- policy-research ----------
    ("shopee-br-policy-research", "source_registry.md", "SBRCA-REF-PR-001", "TASK-POLICY-01",
     "官方来源的登记结构、抓取状态与核查日期管理",
     "`contracts/evidence_reference.schema.json`、`research/sources.json`",
     "来源分层级的具体归类规则待确定", """
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
| `internal_risk` | 内部风控建议 | `flag` |
| `unverified` | 来源未核实 | `flag` |

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
"""),
    ("shopee-br-policy-research", "violation_codes.md", "SBRCA-REF-PR-002", "TASK-POLICY-01",
     "平台违规码目录的结构、字段含义与解析流程",
     "`research/violation_codes.json`、`tools/parse_violation_codes.py`",
     "违规码到规则前缀的映射关系待建立", """
## 1. 目录结构

`research/violation_codes.json` 是平台公开违规码的结构化目录。每条至少含：

| 字段 | 含义 |
|---|---|
| 代码 | 平台违规码（如 `SPX-...`） |
| 描述 | 违规行为说明 |
| 严重度 | 平台分级 |
| 是否扣分 | 是否计入处罚点 |
| 来源 | 抓取件路径 |

## 2. 用途

| 用途 | 说明 |
|---|---|
| 案件归档 | 平台通知中的违规码 → 关联内部规则 |
| 处罚点估算 | 扣分标识 → 累计分值 |
| 规则反向覆盖检查 | 已有违规码是否都有对应规则 |

## 3. 解析流程

```bash
env -u LD_LIBRARY_PATH python3 tools/parse_violation_codes.py
```

输入是 `research/raw/shopee_br_banimento_suspensao_anuncios.txt`（平台刊登违规指南页）。

## 4. 与规则的关系

违规码目录**不等于**规则库。

| | 违规码目录 | 规则库 |
|---|---|---|
| 来源 | 平台公开列举 | 平台规则 + 法律 + 内部风控 |
| 粒度 | 平台的处罚分类 | 内部可检测条件 |
| 用途 | 案件归档、扣分计算 | 审核判定 |

一个违规码可能对应多条规则；多条规则也可能落在同一违规码下。

## 5. 待 TASK-POLICY-01 确定

- [ ] 违规码 → 规则前缀的映射表
- [ ] 扣分值的可信来源（当前平台未公开完整分值表）
- [ ] 目录刷新频率
"""),
    ("shopee-br-policy-research", "citation_verification.md", "SBRCA-REF-PR-003", "TASK-POLICY-01",
     "引文逐字核验的流程、失败原因与处理",
     "`tools/verify_citations.py`",
     "核验基准的失效判定与再抓取策略待确定", """
## 1. 为什么逐字核验

项目历史上出现过**编造条文**的事故 —— 规则里引用了一段并不存在于原始法律中的话。逐字核验机制正是为此建立。

> 真实条文示例：巴西工业产权法 **Lei 9.279/1996 Art. 132, II** 规定的是"配件制造商为表明产品用途而使用他方标记"的正当使用情形 —— 兼容性描述**不等于**商标侵权。

## 2. 核验命令

```bash
env -u LD_LIBRARY_PATH python3 tools/verify_citations.py
```

逐条检查规则的 `source_excerpt` 是否**逐字**出现在 `research/raw/*.txt` 中。

## 3. 比对规则

| 规则 | 说明 |
|---|---|
| 空白 | 忽略换行与缩进差异 |
| 尾部标点 | 忽略末尾标点差异 |
| 大小写 | **敏感** —— 葡语大小写有意义 |
| 重音符号 | **敏感** —— `é` ≠ `e` |
| 内部措辞 | **必须完全一致** —— 少一个词即失败 |

## 4. 失败处理

| 失败原因 | 处理 |
|---|---|
| 抓取件缺失 | 重新抓取；抓不到则 `status` 改 `unverified` |
| 措辞不一致 | 修正规则引文（引文是**原文**，规则描述是**概括**） |
| 引文被截断 | 补全抓取件 |
| 规则描述被误当引文 | 把描述移出 `source_excerpt` |

**核验不通过的规则不得标记 `active`。**

## 5. 常见失败原因

1. 把规则的**概括描述**填进了 `source_excerpt` —— 概括必然不是逐字。
2. 抓取件里是 HTML 实体（`&quot;`）而引文里是直引号。
3. 葡语重音符号在复制过程中丢失。
4. 抓取件被后续抓取覆盖，旧引文失效。

## 6. 待 TASK-POLICY-01 确定

- [ ] 抓取件的版本化命名（避免覆盖导致旧引文失效）
- [ ] 核验报告的输出格式
"""),
    ("shopee-br-policy-research", "platform_policy_summary.md", "SBRCA-REF-PR-004", "TASK-POLICY-01",
     "平台政策要点摘要：禁限售类目、处罚机制、IP 四类",
     "`research/raw/`（抓取件原文）",
     "摘要内容须以逐字核验通过的抓取件为准", """
## 1. 本文档的地位

这是**面向人类阅读的摘要**，不是权威来源。

> **权威来源永远是 `research/raw/` 的抓取件。**
> 本文档任何表述若与抓取件冲突，以抓取件为准，并应提交更正。

## 2. 摘要结构

每个政策点按下列结构记录：

```markdown
### <政策主题>
- **来源**：<URL> ｜ **核查日期**：<ISO 日期> ｜ **层级**：platform_official
- **要点**：<概括>
- **原文摘录**：<逐字片段>
- **对应的规则**：<rule_id 列表>
```

## 3. 必覆盖的政策主题

| # | 主题 | 归属模块 |
|---|---|---|
| 1 | 禁售商品与受限商品类目 | `listing-audit` |
| 2 | 限制类目的许可要求 | `listing-audit` |
| 3 | 药品与健康类专项规则 | `listing-audit` |
| 4 | 刊登质量违规（标题、描述、类目、属性） | `listing-audit` |
| 5 | 重复刊登与多账号经营 | `duplicate-detection` |
| 6 | 违规商品的封禁 / 删除 / 限制触达 | `duplicate-detection` |
| 7 | 处罚点机制、申诉与恢复 | `duplicate-detection` |
| 8 | 知识产权四类与投诉流程 | `ip-review` |
| 9 | 授权与资质文件要求 | `ip-review` / `duplicate-detection` |

## 4. 已知的关键政策事实

> 以下均来自已核验的抓取件，**每次引用仍须逐字核验**。

| 事实 | 影响 |
|---|---|
| 封禁（`banimento`）在问题解决后**可恢复**；删除（`excluído`）**不可恢复**且计入处罚点 | 重发检查的结论分级完全不同 |
| 限制触达（`alcance limitado`）整改后**自动恢复** | 无需人工申诉 |
| 处罚点**每周一**归属，**一周后生效**，限制持续 14–28 天 | 冻结期限的计算依据 |
| 每条已认定违规**可申诉一次** | 申诉流程设计 |
| 平台明确区分「封禁」与「删除」，二者后果不同 | 案件状态机 |

## 5. 药品类特别说明

自 **2026-08-06** 起，Shopee 获 ANVISA 授权，**仅通过持牌药房/药店**销售 OTC 药品（MIP），依据 `Resolução-RE nº 3.056/2026`。

> ⚠️ 早期"所有药品一律禁售"的逻辑**已过时**，不得沿用。

## 6. 待 TASK-POLICY-01 确定

- [ ] 逐条摘要的正式撰写与逐字核验
- [ ] 摘要的失效与更新机制
"""),
    # ---------- listing-audit ----------
    ("shopee-br-listing-audit", "evidence_checklist.md", "SBRCA-REF-LA-002", "TASK-LISTING-01",
     "各类判定的证据要求与证据链构造",
     "`contracts/evidence_reference.schema.json`、`contracts/risk_action_matrix.json`",
     "各规则的 `evidence_required` 具体清单待确定", """
## 1. 证据引用的规则

**只存引用，不存内容。** 证据本体（图片、授权书扫描件）留在原处，JSON 里只记路径与元信息。

```json
{
  "evidence_id": "EV-LV-001-01",
  "evidence_type": "listing_field",
  "provided": true,
  "artifact_ref": "products/SKU-001/title",
  "source_locator": "title",
  "collected_at": "2026-10-27T00:00:00Z",
  "notes": "标题命中禁售词"
}
```

硬约束 **H5**：不得把凭证内容内嵌进 `artifact_ref` 或 `notes`。

## 2. 证据类型

| `evidence_type` | 用于 | `artifact_ref` 指向 |
|---|---|---|
| `listing_field` | 文本类命中 | 字段路径，如 `title` / `description` |
| `image` | 图片类命中 | 图片路径或 CDN 引用 |
| `authorization` | 授权材料 | 授权书文件路径 |
| `platform_notice` | 平台通知 | 通知原文路径 |
| `external_registry` | 商标/专利注册查询 | 查询结果记录路径 |
| `case_history` | 历史案件 | 案件 ID 引用 |
| `missing` | **缺失的必需输入** | 空 —— 配合 `not_evaluated` |

## 3. 证据链要求

一条 `block` 结论**必须**同时具备：

1. 命中的 `rule_id`
2. 规则要求的所有证据（`evidence_required`）
3. 逐字可核验的 `source.excerpt`
4. 规则 `status = active` 且 `source.tier ∈ {platform_official, law}`

缺任何一项 → 降级为 `flag` + `requires_human_review = true`。

## 4. `provided` 字段的三态

| 值 | 含义 |
|---|---|
| `true` | 证据存在且已取用 |
| `false` | 证据明确不存在 |
| 字段缺失 | **未知** —— 用 `evidence_type: missing` 表达，不要猜 |

## 5. 待 TASK-LISTING-01 确定

- [ ] 每条规则的 `evidence_required` 具体清单
- [ ] 图片类证据的取用方式（OCR 结果如何关联）
"""),
    ("shopee-br-listing-audit", "false_positive_control.md", "SBRCA-REF-LA-003", "TASK-LISTING-01",
     "误判控制：反例机制、词边界、歧义消解",
     "`references/audit_semantics.md`、`lexicon/term_groups.json`",
     "各规则的完整反例集待确定", """
## 1. 误判比漏判更贵

> 平台漏判会下架商品，误判会浪费人工复核工时并让正常商品无法上架。
> **默认策略偏保守**：宁可 `flag` 交给人，不轻易 `block`。

## 2. 反例是强制项

每条规则**必须**在测试中包含：

| 用例 | 断言 |
|---|---|
| 正例 | 命中，`verdict = flag` 或 `block` |
| **反例** | **不命中**，`verdict = pass` |

反例缺失的规则**不得**标记 `active`。

## 3. 葡语词边界（已知坑）

葡语的 `\b` **不可靠**：

```python
# 错误 —— 会吞掉 "Óculos" 的首字母
re.sub(r"\\s*at[óo]xico\\b\\s*", " ", s)

# 正确 —— 显式排除字母边界
re.sub(r"(?<![a-zA-Zà-ÿÀ-ß])at[óo]xico(?![a-zA-Zà-ÿÀ-ß])", " ", s)
```

> 同样的显式边界写法也适用于所有葡语关键词匹配。

## 4. 常见误判来源

| 来源 | 例子 | 处理 |
|---|---|---|
| 词边界 | `atóxico` 吞掉 `Óculos` 首字母 | 显式 lookaround |
| 品类词歧义 | `escova`（梳子）/（刷子） | 具体关键词优先 + override 表 |
| 品牌词出现在描述中 | "compatível com <Marca>" | 兼容性描述 ≠ 侵权（见 IP 模块） |
| 主观宣传用语 | "melhor do mercado" | 不属平台禁止的绝对化用语 |
| 商品名含地名/店名 | "Loja São Paulo" | 不触发品牌规则 |
| OCR 误识别 | 图片上的模糊字 | 降低置信度 → `flag` |

## 5. 词库规范化的顺序

```
原文
 → 小写
 → Unicode 规范化（NFC）
 → 重音符号折叠（仅用于匹配，输出保留原形）
 → 词边界匹配
```

**重音符号折叠只用于匹配**，不得改写输出文本。

## 6. 待 TASK-LISTING-01 确定

- [ ] 每条规则的正例/反例完整清单
- [ ] 品类歧义 override 表
- [ ] 各规则的最小证据要求
"""),
    ("shopee-br-listing-audit", "policy_currency.md", "SBRCA-REF-LA-004", "TASK-LISTING-01",
     "政策时效性管理：规则过期、失效与重新核验",
     "`references/audit_semantics.md` §3、`contracts/risk_action_matrix.json`",
     "过期规则的自动降级机制待实现", """
## 1. 规则的时效状态

| `status` | 含义 | 是否产出结论 |
|---|---|---|
| `active` | 已核验且在有效期内 | ✅ |
| `stale` | 超过核查有效期 | ⚠️ 只产出 `flag`，不产出 `block` |
| `unverified` | 引文未核验通过 | ⚠️ 只产出 `flag` |
| `deprecated` | 已被政策取代 | ❌ 不产出结论 |
| `draft` | 编写中 | ❌ 不产出结论 |

**只有 `active` 才能产生 `block`** —— 硬约束 **H2**。

## 2. 有效期的判定

| 层级 | 有效期 | 依据 |
|---|---|---|
| `platform_official` | 90 天 | `source.last_verified` |
| `law` | 180 天 | `source.last_verified` |
| `internal_risk` | 无 | 内部策略 |

## 3. 政策变更的处理

```
检测到政策变更
  ↓
抓取新版本 → research/raw/<slug>.<date>.txt
  ↓
逐字核验受影响规则的引文
  ↓
更新规则的 source.last_verified / source.excerpt
  ↓
若语义实质变化 → 规则 version +1，status 置 draft
  ↓
重新执行受影响规则的测试
```

> **不覆盖历史抓取件。** 旧引文的可核验性依赖于旧抓取件仍在。

## 4. 已知需要特别留意的政策

| 政策 | 变化 | 影响 |
|---|---|---|
| OTC 药品 | 2026-08-06 起仅限持牌药房/药店销售 | 旧的"药品一律禁售"规则**必须废弃** |
| 封禁 vs 删除 | 删除不可恢复且计处罚点 | 重发结论分级 |

## 5. 待 TASK-LISTING-01 确定

- [ ] `stale` 规则的降级行为的具体实现
- [ ] 政策变更检测的触发方式（人工触发 vs 自动）
"""),
    # ---------- duplicate-detection ----------
    ("shopee-br-duplicate-detection", "relist_axes.md", "SBRCA-REF-DUP-001", "TASK-DUP-01",
     "违规重发检查的判定维度与结论分级",
     "`contracts/risk_action_matrix.json`、`references/relist_axes.md`",
     "各轴的组合结论矩阵待确定", """
## 1. 六个判定轴

重发检查沿六个轴展开，**每个轴独立判定**：

| 轴 | 问题 | 数据来源 |
|---|---|---|
| A. 历史状态 | 该商品历史是否被封禁/删除/限制触达 | 历史案件 |
| B. 平台处罚点 | 店铺累计扣分与限制状态 | 平台通知 |
| C. 案件未结 | 是否存在**未结**的违规案件 | 案件库 |
| D. 标题/SKU 变换 | 改标题或改 SKU 后重发 | 商品历史字段 |
| E. 跨店同款 | 其它店铺是否有同款 | 跨店铺商品集 |
| F. 授权状态 | 授权是否过期或不覆盖本商品 | 授权材料 |

## 2. 平台状态的后果差异（关键）

| 平台处置 | 可否恢复 | 计入处罚点 | 重发结论 |
|---|---|---|---|
| 封禁 `banimento` | ✅ 问题解决后可恢复 | 视违规类型 | `flag` + 复核 |
| 删除 `excluído` | ❌ **不可恢复** | ✅ | `block` |
| 限制触达 `alcance limitado` | ✅ 整改后**自动恢复** | 视情况 | `flag` + 复核 |

> **删除 vs 封禁的区分是本模块最关键的判定。** 误判会导致错误冻结或错误放行。

## 3. 结论分级

| 条件 | `verdict` | `action` |
|---|---|---|
| 历史为删除（不可恢复） | `block` | `freeze_relist` |
| 历史为封禁且问题未结 | `flag` | `require_evidence` |
| 标题/SKU 变换后与历史违规商品匹配 | `flag` | `revise` |
| 跨店同款且已有违规记录 | `flag` | `require_evidence` |
| 授权缺失或不覆盖 | `flag` | `require_evidence` |
| 处罚点已达限制阈值 | `flag` | `flag_for_review` |
| 无任何命中 | `pass` | `allow` |

`freeze_relist` 是 **human_only** 动作（硬约束 **H6**）—— 系统只建议，不自动冻结。

## 4. 未结案件的判定

> 原型实现曾在此处出错：早期逻辑要求案件必须有关联的商品历史记录，导致只引用 `product_ids` 的案件被漏掉。
>
> 正确做法：**直接用案件引用的 `product_ids` 匹配**，不要求历史商品记录存在。

## 5. 待 TASK-DUP-01 确定

- [ ] 处罚点阈值来源（平台未公开完整分值表）
- [ ] 标题/SKU 变换的相似度判定方法
- [ ] 跨店同款的匹配信号权重
"""),
    ("shopee-br-duplicate-detection", "duplicate_signals.md", "SBRCA-REF-DUP-002", "TASK-DUP-01",
     "重复刊登的信号设计与权重",
     "`references/relist_axes.md`",
     "各信号的权重与阈值待基准测试确定", """
## 1. 信号分层

| 层 | 信号 | 确定性 |
|---|---|---|
| 强 | 相同 `platform_pid` | 确定 |
| 强 | 相同 `internal_sku` + 相同店铺 | 确定 |
| 强 | 相同图片指纹（pHash/感知哈希） | 高 |
| 中 | 标题规范化后完全相同 | 高 |
| 中 | 标题相似度 ≥ 阈值 + 同店铺 | 中 |
| 弱 | 标题相似度 ≥ 阈值 + 跨店铺 + 同类目 | 弱 |
| 弱 | 相同 `supplier_sku` + 同类目 | 弱 |

## 2. 结论

| 强度 | 同店铺 | 跨店铺 | 结论 |
|---|---|---|---|
| 强 | `block`（重复刊登） | `flag`（跨店同款，需评估） | |
| 中 | `flag` | `flag` | |
| 弱 | `flag` | `pass`（仅记录） | |

**跨店铺同款本身不是违规** —— 同一供应商向多个店铺供货是正常业务。只有**叠加违规历史**时才升级。

## 3. 文本规范化（用于标题比较）

```
标题 → 小写 → Unicode NFC → 去重音（仅比较用）
     → 去除营销噪声词（promo、frete、novo）
     → 去除标点 → 压缩空白
     → 词元排序 → 指纹
```

> ⚠️ 规范化**只用于比较**，不得写回商品数据。

## 4. 图片指纹

用感知哈希（pHash / dHash）而非字节哈希 —— 同一张图重新压缩后字节哈希会变。

```
1. 缩放到 32×32 灰度
2. 计算 DCT
3. 取左上 8×8 低频系数
4. 与中位数比较 → 64 位指纹
5. 汉明距离 ≤ 阈值 → 判定相似
```

## 5. 待 TASK-DUP-01 确定

- [ ] 标题相似度算法与阈值
- [ ] 图片指纹阈值
- [ ] 营销噪声词表
"""),
    ("shopee-br-duplicate-detection", "case_workflow.md", "SBRCA-REF-DUP-003", "TASK-DUP-01",
     "历史案件的状态机与重发放行流程",
     "`data/schema/case.schema.json`",
     "冻结解除的前置条件待用户裁定", """
## 1. 案件状态机

```
open ──→ investigating ──→ actioned ──→ closed
  │            │              │
  │            └──→ rejected  │
  └──────────────────────────┴──→ closed
```

| 状态 | 含义 | 是否阻塞重发 |
|---|---|---|
| `open` | 新建，待分派 | ✅ 阻塞 |
| `investigating` | 审核中 | ✅ 阻塞 |
| `actioned` | 已执行处置（冻结/整改） | ✅ 阻塞 |
| `rejected` | 申诉成立，撤销处置 | ❌ 不阻塞 |
| `closed` | 已结案 | ⚠️ 见下 |

## 2. 冻结与解冻

`frozen` 与案件状态**独立**。案件关闭**不等于**冻结解除。

| 冻结原因 | 解除条件 |
|---|---|
| `ip_infringement` | **仅品牌方撤诉**（或监管机构书面同意） |
| `regulatory` | 原机构书面同意 |
| `listing_violation` | 整改完成 + 平台恢复 |
| `duplicate_listing` | 整改完成 + 平台恢复 |

> ⚠️ **已知风险**：审批通过 ≠ 解封成功。IP 类冻结即使内部审批完成，账号仍可能处于冻结状态，直到品牌方撤诉。
> 案件必须记录**平台侧实际状态**，不能只记内部审批结果。

## 3. 重发放行检查

```
对每个待重发商品：
  1. 按 product_id 查历史案件（不要求历史商品记录存在）
  2. 有 open/investigating/actioned 案件 → 阻塞
  3. 有 closed 但 frozen=true 案件 → 阻塞（检查解除条件）
  4. 处罚点累计达阈值 → 阻塞
  5. 标题/SKU 与违规商品匹配 → 需整改
  6. 全部通过 → 放行
```

## 4. 待 TASK-DUP-01 确定

- [ ] 冻结解除的前置条件确认（IP 类需撤诉）
- [ ] 处罚点阈值
- [ ] 案件状态迁移的审批要求
"""),
    ("shopee-br-duplicate-detection", "penalty_mechanics.md", "SBRCA-REF-DUP-004", "TASK-DUP-01",
     "处罚点机制：归属、生效、限制时长与申诉",
     "`research/raw/`（抓取件原文）",
     "具体分值表平台未公开，需标注为待核实", """
## 1. 机制

| 环节 | 规则 |
|---|---|
| 归属 | 处罚点**每周一**归属到店铺 |
| 生效 | 归属后**一周**生效 |
| 限制时长 | **14–28 天**（视违规严重度） |
| 申诉 | 每条已认定违规**可申诉一次** |

## 2. 已核验的关键区分

| 处置 | 可恢复 | 计处罚点 |
|---|---|---|
| 封禁 `banimento` | ✅ 解决后可恢复 | 视违规类型 |
| 删除 `excluído` | ❌ 不可恢复 | ✅ |
| 限制触达 `alcance limitado` | ✅ 整改后自动恢复 | 视情况 |

## 3. 分值表

> ⚠️ **平台未公开完整的处罚点分值表。** 这是已知的资料缺口。
>
> 因此：本模块**不得**自行编造分值。可用的替代方案：
> - 只使用 `research/violation_codes.json` 中的**是否扣分**标识
> - 分值留空并标记为待核实
> - 阈值判断改用「是否已触发限制」这一可观测事实

## 4. 待 TASK-DUP-01 确定

- [ ] 分值表缺口的上报方式
- [ ] 阈值的替代判据
"""),
    # ---------- ip-review ----------
    ("shopee-br-ip-review", "ip_categories.md", "SBRCA-REF-IP-001", "TASK-IP-01",
     "知识产权四类的区分与各自的检测路径",
     "`contracts/risk_action_matrix.json`、`rules/02_ip_trademark_copyright.json`",
     "外观设计与专利的检测路径待补充", """
## 1. 四类权利

| 类别 | 保护对象 | 检测方式 | 权威查询源 |
|---|---|---|---|
| 商标 | 标识（文字/图形） | 品牌词匹配 + INPI 查册 | INPI |
| 版权 | 作品（图像/文本/音乐） | 图片相似度 + 版权标识检测 | 创作者权利登记 |
| 外观设计 | 产品外观（工业设计） | 设计相似度 | INPI 外观设计登记 |
| 专利 | 发明/实用新型 | 权利要求比对 | INPI 专利登记 |

## 2. 结论的强制语义

> 硬约束 **H1**：**任何** IP 类结论恒为 `signal`，且**必须** `requires_human_review = true`。

理由：把"疑似侵权"直接认定为"侵权"，既缺乏法律依据，也可能造成错误下架与商誉损害。

```
IP 命中 → verdict = signal
       → action = require_evidence 或 escalate_legal
       → requires_human_review = true
       → 永远不产生 block
```

## 3. 商标的两种使用

| 使用 | 判定 | 依据 |
|---|---|---|
| 指示性使用 | ✅ 合法 | Lei 9.279/1996 **Art. 132, II** |
| 混淆性使用 | ⚠️ 风险 | 可能构成侵权 |

> **Art. 132, II** 规定：配件制造商为表明产品用途（兼容性），可在产品上使用他方标记。**兼容性描述 ≠ 商标侵权。**

## 4. 版权检测的边界

图片相似度**只说明可能存在复制关系**，不说明谁有权。版权归属需人工确认。

## 5. 待 TASK-IP-01 确定

- [ ] 外观设计与专利的检测路径（当前缺规则）
- [ ] INPI 查询的接口或人工流程
- [ ] 品牌词与普通词（如"Original"、"Premium"）的排除表
"""),
    ("shopee-br-ip-review", "nominative_use.md", "SBRCA-REF-IP-002", "TASK-IP-01",
     "指示性使用与混淆性使用的区分标准",
     "Lei 9.279/1996 Art. 132, II（`research/raw/br_lei_propriedade_industrial_9279.txt`）",
     "各场景的判定细则待补充", """
## 1. 区分标准

| 要素 | 指示性使用（合法） | 混淆性使用（风险） |
|---|---|---|
| 目的 | 表明产品**用途/兼容/来源** | 借用品牌**吸引力** |
| 位置 | 必要且适度 | 显眼、突出 |
| 表述 | "兼容 `<Marca>` <型号>" | "`<Marca>` 原厂" / "官方授权"（无授权时） |
| 附加说明 | 有"非授权"说明更好 | 无 |
| 商标位置 | 非主导 | 主导 |

## 2. 合法表述样例

```
Compatível com <Marca> <Modelo>
适配 <Marca> <Modelo>
Peça de reposição para <Marca> <Modelo>
```

## 3. 高风险表述样例

```
<Marca> Original
<Marca> Oficial
<Marca> Certificado
复制 <Marca> 包装 / <Marca> style
```

## 4. 判定流程

```
检测到品牌词
  ↓
判断上下文：是「兼容性/用途」还是「品质/来源」？
  ↓
用途 → 指示性使用 → verdict = pass（或 info + 提示需标注"非授权"）
来源/品质 → 混淆性使用 → verdict = signal + 人工复核
```

## 5. 特别注意

> 指示性使用**合法不等于可以随便写**。使用他人标记时仍应：
> - 以必要限度为限
> - 不使消费者误以为存在授权关系
> - 在能说明时注明"非授权配件"

## 6. 待 TASK-IP-01 确定

- [ ] 判定表的具体词法实现
- [ ] "非授权"标注的强制性判断
"""),
    ("shopee-br-ip-review", "authorization_checklist.md", "SBRCA-REF-IP-003", "TASK-IP-01",
     "品牌授权材料的核查项与有效性判定",
     "`data/schema/case.schema.json` 的 `evidence` 字段",
     "授权链（上游→下游）的验证要求待补充", """
## 1. 核查项

| # | 核查项 | 不满足的后果 |
|---|---|---|
| 1 | 授权书存在 | `require_evidence` |
| 2 | 授权方是**商标权利人**或有权授权方 | `escalate_legal` |
| 3 | 授权覆盖**本商品品牌** | `require_evidence` |
| 4 | 授权覆盖**本商品类目** | `require_evidence` |
| 5 | 授权在**销售期内** | `require_evidence` |
| 6 | 授权覆盖**销售地区**（含巴西） | `require_evidence` |
| 7 | 授权覆盖**销售主体**（店铺） | `require_evidence` |
| 8 | 授权链完整（多级分销时逐级可查） | `escalate_legal` |
| 9 | 授权书真实性可验证 | `escalate_legal` |

## 2. 授权不完整的表达

**不等于侵权。** 它意味着**无法证明有权销售**。

```
授权材料缺失/不完整
  → verdict = signal
  → action = require_evidence
  → requires_human_review = true
  → 不得直接判定侵权
```

## 3. 授权与商标检测的关系

| 情形 | 商标检测 | 授权核查 | 结论 |
|---|---|---|---|
| 品牌词 + 有授权 | 可能命中 | 通过 | `pass` |
| 品牌词 + 无授权 | 可能命中 | 不通过 | `signal` + 复核 |
| 品牌词 + 指示性使用 | 命中 | 不需要 | `pass` |
| 品牌词 + 混淆性使用 | 命中 | — | `signal` + 复核 |

## 4. 证据记录

授权材料按 `contracts/evidence_reference.schema.json`：

```json
{
  "evidence_id": "EV-AU-001",
  "evidence_type": "authorization",
  "provided": true,
  "artifact_ref": "authorizations/SKU-001/authorization.pdf",
  "source_locator": "case.evidence",
  "collected_at": "2026-10-27T00:00:00Z",
  "notes": "授权方与权利人不一致，待核"
}
```

硬约束 **H5**：只存路径，**不内嵌**授权书内容或凭证。

## 5. 待 TASK-IP-01 确定

- [ ] 授权链验证的具体要求
- [ ] 授权书 OCR/人工录入的分工
"""),
    ("shopee-br-ip-review", "dissolution_flow.md", "SBRCA-REF-IP-004", "TASK-IP-01",
     "IP 类冻结的解除流程：只有品牌方撤诉才能解封",
     "`data/schema/case.schema.json`、`docs/SBRCA-P0-003_requirement_register.json`",
     "撤诉流程的外部对接方式待确定", """
## 1. 核心事实

> **IP 类账号冻结，只有品牌方撤诉才能解封。**
>
> 内部审批通过、整改完成、申诉成立 —— **都不等于解封**。

| 处置来源 | 解封条件 |
|---|---|
| 品牌方投诉 | **品牌方撤诉**（或出具同意函） |
| 监管机构（ANVISA 等） | 原机构书面同意 |
| 平台自行认定 | 平台撤销认定 |

## 2. 流程

```
IP 投诉 → 平台冻结账号/商品
   ↓
内部核实 → 确认侵权（或否认）
   ↓
若确认 → 联系品牌方/权利人 → 协商撤诉或取得授权
   ↓
取得撤诉证明/授权文件 → 提交平台
   ↓
平台恢复 → 记录实际恢复日期
```

## 3. 状态记录要求

案件必须区分两个状态：

| 字段 | 含义 |
|---|---|
| 内部审批状态 | 内部是否认定侵权、是否已处置 |
| **平台侧实际状态** | **账号/商品在平台侧是否真的恢复** |

> ⚠️ 原型的解冻逻辑只要求「案件关闭 + 人工审批」。这不足以证明解封。
> 本模块必须以**平台侧实际状态**为准。

## 4. 证据

| 证据 | 说明 |
|---|---|
| 撤诉证明 | 品牌方的书面撤诉/同意函 |
| 授权文件 | 若走授权途径 |
| 平台恢复截图/记录 | 证明实际恢复 |

## 5. 待 TASK-IP-01 确定

- [ ] 撤诉流程的外部对接方式（人工/接口）
- [ ] 平台侧状态的记录粒度
"""),
    # ---------- data-ingestion ----------
    ("shopee-br-data-ingestion", "format_matrix.md", "SBRCA-REF-DI-001", "TASK-INGEST-01",
     "各输入格式的解析方法、限制与失败模式",
     "`contracts/skill_input.schema.json`、`data/schema/product.schema.json`",
     "各格式的实测限制待补全", """
## 1. 格式矩阵

| 格式 | 解析方式 | 能得到 | 限制 |
|---|---|---|---|
| XLSX / XLS | 读取工作表 → 列映射 | 全字段 | 多行表头需指定表头行 |
| CSV | 分隔符嗅探 + 编码嗅探 | 全字段 | 编码可能非 UTF-8 |
| JSON | 直接解析 | 全字段 | 需识别数组/包裹对象 |
| JSONL | 逐行解析 | 全字段 | 任一行损坏则整体失败 |
| TXT / MD | 纯文本 | 自由文本 | 无结构，需人工映射 |
| DOCX | 段落 + 表格 | 自由文本 + 表格 | 复杂排版丢失 |
| PDF | 文本层提取 | 自由文本 | 扫描件需 OCR；表格结构可能丢失 |
| PNG / JPG / JPEG / WEBP | OCR + 视觉分析 | 图片文本 | OCR 置信度有限 |
| 商品链接 | 抓取 | 商品页字段 | 需登录态 |
| 平台违规通知 | 抓取/文本解析 | 通知字段 | 格式随平台变化 |
| 授权材料 | 文本/图像解析 | 授权字段 | 需人工复核真实性 |

## 2. 统一处理管线

```
原始输入
  ↓ ① 格式识别
  ↓ ② 解析（按格式选方法）
  ↓ ③ 字段映射（别名表）
  ↓ ④ 规范化（大小写、重音、空白）
  ↓ ⑤ 校验（Schema）
  ↓ ⑥ 溯源记录
规范化记录 + 溯源信息
```

## 3. 失败处理

| 失败 | 行为 |
|---|---|
| 文件不可读 | 记 error，**不中断整批** |
| 格式无法识别 | 记 error + 说明尝试过的方法 |
| 必需字段缺失 | 记 error，该记录标记为不完整 |
| 解析部分失败 | 保留已解析部分 + 记 error |
| 编码错误 | 尝试常见编码回退，全失败则记 error |

> **绝不静默丢弃。** 每条输入要么产出规范化记录，要么产出错误说明。

## 4. 原始输入保护

- **不得覆盖或修改原始输入文件。**
- 解析产物写到独立输出目录。
- 每条记录携带来源溯源（源文件、原始行号/单元格、解析时间）。

## 5. 待 TASK-INGEST-01 确定

- [ ] 各格式的实测限制
- [ ] 字段别名表的完整内容
"""),
    ("shopee-br-data-ingestion", "field_mapping.md", "SBRCA-REF-DI-002", "TASK-INGEST-01",
     "字段别名表与列映射规则",
     "`data/schema/product.schema.json`",
     "别名表的完整清单待补全", """
## 1. 映射目标

所有输入最终映射到 `data/schema/product.schema.json` 的 `Product` 结构。核心字段：

| 字段 | 含义 | 必需 |
|---|---|---|
| `product_id` | 内部唯一标识 | ✅ |
| `shop_id` | 所属店铺 | ✅ |
| `title` | 商品标题 | ✅ |
| `description` | 商品详情 | |
| `attributes` | 平台属性字典 | |
| `category` | 类目 | |
| `brand` | 品牌 | |
| `images` | 图片列表 | |
| `product_url` | 商品链接 | |
| `supplier_sku` | 供应商货号 | |
| `internal_sku` | 内部 SKU | |
| `case_ids` | 关联历史案件 | |

## 2. 别名表

中葡英三语的列名变体都要覆盖，例如：

| 目标字段 | 别名（含变体） |
|---|---|
| `title` | `title` / `nome` / `nome do produto` / `商品名称` / `标题` |
| `description` | `description` / `descricao` / `descrição` / `商品描述` / `详情` |
| `product_id` | `product_id` / `item_id` / `sku` / `商品ID` / `货号` |
| `brand` | `brand` / `marca` / `品牌` |
| `category` | `category` / `categoria` / `类目` |
| `images` | `images` / `image_urls` / `图片` / `主图` |
| `price` | `price` / `preco` / `价格` |

## 3. 映射规则

| 规则 | 说明 |
|---|---|
| 规范化后比较 | 空格、下划线、大小写、连字符统一后再匹配 |
| 歧义别名 | 出现多个候选 → **不猜**，记 error |
| 未知列 | 保留为 `attributes` 附加项，**不丢弃** |
| 必需列缺失 | 该记录标记不完整，**不静默跳过** |
| 保留原值 | 规范化只影响比较，**存储保留原值** |

> ⚠️ 已知坑：早期实现把 `_` 归一化成空格，但别名表里用的是空格写法 —— 两边必须统一。
> 另：`sku` 这个裸别名曾被误映射到 `product_id`，导致语义错误 —— 裸 `sku` 必须人工确认。

## 4. 待 TASK-INGEST-01 确定

- [ ] 完整别名表
- [ ] 歧义别名的处理清单
"""),
    ("shopee-br-data-ingestion", "provenance.md", "SBRCA-REF-DI-003", "TASK-INGEST-01",
     "数据溯源：每条记录从哪来",
     "`contracts/skill_input.schema.json` 的 `provenance` 字段",
     "溯源字段的最终形态待确认", """
## 1. 为什么必须溯源

审核结论要能被复核，就必须能回答：**这条商品数据是从哪个文件的哪一行来的？**

## 2. 溯源内容

| 字段 | 含义 |
|---|---|
| 源文件路径 | 绝对路径 |
| 源格式 | xlsx / csv / json / pdf / image / ... |
| 工作表或分片 | xlsx 的 sheet 名；JSONL 的分片 |
| 原始位置 | 行号 / 单元格范围 / 字符区间 |
| 解析时间 | ISO 8601 |
| 解析器版本 | 解析代码的版本标识 |
| 店铺 | `shop_id` |
| 解析统计 | 该文件解析出的记录数、跳过数、错误数 |

## 3. 溯源的传递

`provenance` 沿流水线**逐层传递**：

```
ingestion 的 provenance
  → SkillInput.provenance
  → AuditResult.provenance
  → 报告中的来源说明
```

> 主 Skill 在整合时**原样保留**各模块的 `provenance`，不得覆盖。

## 4. 报告中的呈现

每条发现要能点回原始来源：

```
发现：标题命中禁售词
  → 规则：SBR-PI-001
  → 商品：SKU-001
  → 来源：data/samples/demo_mass_update.xlsx
        sheet=mass_update  行=8  列=商品名称
```

## 5. 待 TASK-INGEST-01 确定

- [ ] 溯源字段的最终结构
- [ ] 报告中的呈现细节
"""),
    ("shopee-br-data-ingestion", "lexicon_format.md", "SBRCA-REF-DI-004", "TASK-INGEST-01",
     "词库文件的格式与消费方式",
     "`data/schema/lexicon.schema.json`、`lexicon/term_groups.json`",
     "词库格式的最终形态待确认", """
## 1. 词库不是规则

| | 词库 | 规则 |
|---|---|---|
| 内容 | 词与词组 | 条件 + 动作 + 来源 + 证据要求 |
| 用途 | **产生信号** | **产生结论** |
| 单独命中 | 只能 `flag` | 可 `block` |

> 词库命中**本身永远不是违规判定**。它只说明"这里有值得看的东西"。

## 2. 格式

```json
{
  "schema_version": "1.0",
  "name": "shopee-br-risk-lexicon",
  "description": "...",
  "last_verified": "2026-10-27",
  "usage": "screening_only",
  "groups": [
    {
      "group_id": "G-PI-01",
      "label": "禁售类目关键词",
      "risk_hint": "prohibited",
      "terms": ["termo proibido", "outro termo"]
    }
  ]
}
```

| 字段 | 含义 |
|---|---|
| `group_id` | 稳定组标识 |
| `label` | 组名（中文或葡语） |
| `risk_hint` | 风险提示方向，**不是结论** |
| `terms` | 词与词组 |

## 3. 匹配

- 匹配在**规范化后**的文本上进行（见 `false_positive_control.md` §5）
- 词组按**最长优先**匹配
- 一个词可属于多个组 → 产生多条信号
- 命中必须记录**具体位置**（字段 + 偏移），不能只记"命中了"

## 4. 规模

> ⚠️ 词库的历史数据文件已丢失（原 1,320 词 / 36,372 词规模），现存仅 Markdown 文档。
> 规模假设（十万条）**尚未有数据支撑**，需先基准测试再定。

大规模检索可用 Aho–Corasick 等多模式匹配算法建立索引，但**规则原始数据仍以 JSON 保存**。

## 5. 待 TASK-INGEST-01 确定

- [ ] 词库格式的最终确认
- [ ] 重建词库的来源与流程
"""),
    # ---------- reporting ----------
    ("shopee-br-reporting", "report_structure.md", "SBRCA-REF-RP-001", "TASK-REPORT-01",
     "报告的六节固定结构",
     "`contracts/audit_result.schema.json`",
     "各节的具体渲染形态待确定", """
## 1. 六节固定结构

```
## 1. 摘要
## 2. 数据缺口与未评估项
## 3. 需决策的发现
## 4. 待复核的发现
## 5. 逐商品结果
## 6. 已查阅规则
```

**顺序固定，不得调整。** 机器消费方依赖这个结构。

## 2. 各节内容

| 节 | 内容 | 空时的表现 |
|---|---|---|
| 1. 摘要 | 范围、商品数、结论分布、需人工处理数 | 必须有 |
| 2. 数据缺口 | 所有 `not_evaluated` 及其缺失字段 | **必须显示"无"**，不得省略 |
| 3. 需决策的发现 | `action` 为 `block`/`revise`/`escalate_legal` 的 | 显示"无" |
| 4. 待复核的发现 | `action` 为 `flag_for_review`/`require_evidence` 的 | 显示"无" |
| 5. 逐商品结果 | 每个商品一条，含所有结论 | 必须有 |
| 6. 已查阅规则 | 本次用到的规则及其来源层级与核查日期 | 必须有 |

> ⚠️ **第 2 节是硬性要求。** 它把"未评估"与"通过"明确分区。
> 省略第 2 节会让读者误以为没问题的商品是通过了审核。

## 3. 空值表达

| 情况 | 表达 |
|---|---|
| 无数据缺口 | `无` |
| 无需决策的发现 | `无` |
| 无待复核发现 | `无` |

**不得**用空白或 `-` 省略。

## 4. 硬约束节

报告末尾**必须**包含已执行的硬约束清单：

```markdown
## 硬约束
- H1 IP 类结论恒为 signal 且需人工复核 — ✅
- H2 阻断类动作仅来自 platform_official/law 的 active 规则 — ✅
- H3 输入缺失标记未评估，不计为通过 — ✅
- H4 引文逐字核验 — ✅ (50/50)
- H5 证据只存引用 — ✅
- H6 冻结与法务升级为人工专属 — ✅
```

## 5. 待 TASK-REPORT-01 确定

- [ ] 摘要的具体指标
- [ ] 逐商品结果的表格字段
"""),
    ("shopee-br-reporting", "aggregation_rules.md", "SBRCA-REF-RP-002", "TASK-REPORT-01",
     "多模块结果的聚合语义",
     "`contracts/risk_action_matrix.json` 的 `verdict_aggregation`",
     "聚合的具体实现待确定", """
## 1. 聚合的唯一权威

`contracts/risk_action_matrix.json` → `verdict_aggregation` 字段。

**本模块不定义聚合规则**，只执行矩阵里写明的规则。

## 2. 确定性动作只增不减

> 硬约束 **H2** 的推论：整批的结论**不得弱于**任一模块的结论。

```
若模块 A 给出 block，整批结论必须包含 block
若模块 A 给出 flag，整批结论不得被另一模块的 pass 覆盖
```

**不允许**用"多数投票"或"取平均"稀释确定性结论。

## 3. 风险等级聚合

按矩阵定义的策略（通常是取最严重等级），但**动作与等级是正交的** —— 最高风险等级不一定对应最严格动作，矩阵决定二者关系。

## 4. `unevaluated` 的合并

```
整批的 unevaluated = 所有模块的 unevaluated 之并
```

> **绝不因其它模块通过而清除。** 某个模块说"这个商品我没评"，整批结果就说"这个商品在这个维度未评估"。

## 5. `rule_refs` 合并

按 `rule_id` 去重。同一规则被多个模块引用时，保留其 `source` 信息（应一致）；不一致时在 `provenance.notes` 标注。

## 6. 常见聚合错误

| 错误 | 正确做法 |
|---|---|
| 只取"最严重的那一条" | 保留全部，聚合动作 |
| 用通过覆盖未评估 | 未评估必须保留 |
| 把不同商品的发现混在一起 | 按 `product_id` 聚合 |
| 动作被风险等级覆盖 | 查矩阵，不自行推断 |

## 7. 待 TASK-REPORT-01 确定

- [ ] 聚合的具体实现
- [ ] 跨模块规则冲突的处理
"""),
    ("shopee-br-reporting", "evidence_citation.md", "SBRCA-REF-RP-003", "TASK-REPORT-01",
     "证据与来源在报告中的引用格式",
     "`contracts/evidence_reference.schema.json`、`contracts/rule_envelope.schema.json`",
     "引用的展示格式待确定", """
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
"""),
    # ---------- compliance (main) ----------
    ("shopee-br-compliance", "routing.md", "SBRCA-REF-CO-001", "TASK-MAIN-01",
     "任务分流：输入什么，就执行哪些模块",
     "`docs/parallel_execution_plan.md`、`skills/*/SKILL.md`",
     "分流决策的完整形态待确定", """
## 1. 分流原则

> **最小充分原则**：只执行本次输入真正需要的模块。

理由：每个模块都会产生结论，多跑一个模块就多一份误判风险与复核工时。

## 2. 决策表

| 输入特征 | 执行模块 |
|---|---|
| 纯文本输入（标题/详情） | `listing-audit` |
| 含图片 | `listing-audit` + `ip-review` |
| 含品牌名 | `ip-review` |
| 含多店铺商品 | `duplicate-detection` |
| 含历史案件/违规记录 | `duplicate-detection` |
| 含店铺处罚状态 | `duplicate-detection` |
| 含品牌授权材料 | `ip-review` + `duplicate-detection` |
| 输入是文件（Excel/CSV/PDF/图片） | 先 `data-ingestion` |
| 任何情况 | 最后 `reporting` |
| 源政策需重新核验 | `policy-research` |

## 3. 合并规则

| 同时命中 | 执行 |
|---|---|
| 多店铺 + 图片 | `listing-audit` + `ip-review` + `duplicate-detection` |
| 文件 + 多店铺 | `data-ingestion` → 三个专业模块 → `reporting` |
| 仅需出报告 | `reporting`（复用已有结果） |

## 4. `policy-research` 的特殊地位

它**不是**每次都跑。它只在以下情况执行：

- 规则引文核验失败
- 规则的 `last_verified` 过期
- 用户要求核查政策原文
- 新增规则需要来源

## 5. 分流结果必须记录

分流决定写入 `provenance.notes`：

```
本次执行模块：data-ingestion → listing-audit → ip-review → duplicate-detection → reporting
未执行：policy-research（规则引文核验通过且未过期）
```

## 6. 待 TASK-MAIN-01 确定

- [ ] 决策表的完整形态
- [ ] 是否支持用户手动指定模块
"""),
    ("shopee-br-compliance", "integration_rules.md", "SBRCA-REF-CO-003", "TASK-MAIN-01",
     "主 Skill 的整合规则",
     "`contracts/risk_action_matrix.json`、`contracts/module_handoff.schema.json`",
     "整合的具体实现待确定", """
## 1. 整合输入

```
各模块的 AuditResult[]
各模块的 ModuleHandoff[]
```

## 2. 整合步骤

```
1. 校验每份 AuditResult 通过 audit_result.schema.json
   └─ 校验失败 → 该模块结果无效，进入降级，不合入

2. 按 product_id 分组

3. 每组内按 verdict_aggregation 聚合
   └─ 确定性动作只增不减

4. 合并 unevaluated（并集，绝不清除）

5. 合并 rule_refs（按 rule_id 去重）

6. 合并 evidence_refs（按 evidence_id 去重）

7. provenance.notes 记录：执行了哪些模块、跳过了哪些、原因

8. 产出最终 AuditResult
```

## 3. 冲突处理

| 冲突 | 处理 |
|---|---|
| 同商品，两模块给不同风险等级 | 按矩阵聚合，取更严格动作 |
| 同商品，一模块 pass 一模块 flag | flag 胜（确定性动作不降级） |
| 同商品，一模块 not_evaluated 一模块 pass | **两者都保留** —— 该维度未评估 |
| 同规则，来源信息不一致 | 以 `platform_official` 优先，并在 notes 标注 |
| 同商品，两模块给互相矛盾的 block | 保留两条，不合并 —— 由人工裁决 |

## 4. 不得做的事

| 不得 | 为什么 |
|---|---|
| 用"多数模块通过"覆盖单个模块的 block | 稀释确定性结论 |
| 因聚合而删除 `unevaluated` | 掩盖数据缺口 |
| 主 Skill 重新判定来源层级 | 越权 |
| 主 Skill 自行转述平台政策 | 破坏可追溯性 |
| 把未校验的模块结果合入 | 契约失效 |

## 5. 整合后的 `rule_version`

取各模块所用规则集版本的**共同基准**；不一致时在 `provenance.notes` 说明。

## 6. 待 TASK-MAIN-01 确定

- [ ] 整合的具体实现
- [ ] 规则版本不一致的处理细节
"""),
    ("shopee-br-compliance", "degradation.md", "SBRCA-REF-CO-004", "TASK-MAIN-01",
     "模块不可用时的降级行为",
     "`contracts/module_handoff.schema.json`",
     "降级的具体输出形态待确定", """
## 1. 核心原则

> **宁可如实报告"未执行"，不可假装"通过"。**

模块不可用时，**绝不能**把它的职责当成"没问题"。

## 2. 降级情形

| 情形 | 行为 |
|---|---|
| 模块 SKILL.md 不可读 | 标记该模块未执行，产出 error |
| 模块产出未通过 Schema 校验 | 该模块结果作废，标记未执行 + error |
| 模块依赖的工具缺失 | 标记未执行，列出缺失工具 |
| 模块产出为空但无 error | 视为异常，标记未执行 |
| 规则引文核验失败 | 规则改 `unverified`，只产出 `flag` |
| 输入数据缺失 | 产出 `not_evaluated`，**不是**降级 |

## 3. 输出形态

```json
{
  "errors": [
    {
      "code": "MODULE_UNAVAILABLE",
      "module": "shopee-br-ip-review",
      "message": "模块产出未通过 audit_result Schema 校验",
      "detail": "..."
    }
  ],
  "unevaluated": [
    {
      "product_id": "SKU-001",
      "rule_id": "SBR-IP-001",
      "missing_fields": ["brand"],
      "reason": "模块 shopee-br-ip-review 未执行"
    }
  ]
}
```

## 4. 报告中的呈现

降级**必须**在报告第 2 节（数据缺口）体现：

```markdown
## 2. 数据缺口与未评估项
- SKU-001：SBR-IP-001 未评估 —— 模块 shopee-br-ip-review 未执行（产出校验失败）
- SKU-002：缺少 brand 字段，未评估 SBR-IP-001
```

**不得**在摘要里把这些商品算作"通过"。

## 5. 摘要中的计数

```
总计 15 个商品
  通过 9    待复核 4    需决策 2
  未评估 3  ← 单独列出，不计入通过
```

## 6. 待 TASK-MAIN-01 确定

- [ ] 错误码的完整清单
- [ ] 降级是否允许部分执行
"""),

]


def main():
    written = 0
    for module, fname, doc_id, task, scope, related, open_item, body in FILES:
        d = os.path.join(ROOT, "skills", module, "references")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, fname)
        content = META.format(doc_id=doc_id, module=f"`{module}`", task=task,
                              scope=scope, related=related, open=open_item) + body
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        written += 1
    print(f"已生成 {written} 份 references 文件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
