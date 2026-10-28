---
name: shopee-br-ip-review
description: Use when you need to screen a Shopee Brazil listing for intellectual-property risk — registered trademarks, copyright, industrial design, patents, and brand authorisation gaps — and to distinguish a brand claim from nominative or compatibility use such as "compatível com". Produces screening signals that always require human review; never establishes infringement on its own.
---

# Shopee BR 知识产权与授权风险筛查

> 状态：**骨架 — 待 `TASK-IP-01` 填充**
> 契约版本：1.0.0
> 规则前缀：`IP`
> 归属：`skills/shopee-br-ip-review/**`、`tests/shopee-br-ip-review/**`

---

## 1. 职责

| # | 职责 | 规则前缀 |
|---|---|---|
| 1 | 商标风险信号筛查（含未授权使用、仿牌宣称） | `IP` |
| 2 | 著作权风险信号筛查（图片水印、版权声明、第三方素材） | `IP` |
| 3 | 外观设计风险信号筛查 | `IP` |
| 4 | 专利风险筛查（**待补规则**） | `IP` |
| 5 | 品牌授权与素材来源缺口识别 | `IP` |
| 6 | 指示性使用（兼容性描述）与侵权主张的**区分** | `IP` |

## 2. 非职责

- ❌ **不作最终侵权认定** —— 需权利人投诉、卖家书面授权或平台投诉通知三者之一
- ❌ 不做重复刊登 / 跨店关联
- ❌ 不做商品内容合规判定（禁售/夸大宣称等）
- ❌ 不解析原始文件
- ❌ 不代运营方向品牌方发函或处理投诉

## 3. 输入契约

使用 `contracts/skill_input.schema.json`（v1.0.0）：

| 字段 | 本模块用法 |
|---|---|
| `request_id` | 贯穿产出 |
| `task_type` | 固定 `ip_review` |
| `products[]` | 使用 `title` / `description` / `brand` / `attributes` / `images[].ocr_text` / `images[].detected_logos` / `history.authorization_documents` |
| `rules[]` | 待用规则（`rule_envelope` 格式） |
| `options.include_logo_scan` | 是否检查图片 logo（缺省 true） |
| `options.strict_authorization` | 授权材料是否必须齐备（缺省 false） |
| `provenance` | 原样透传 |

## 4. 输出契约

产出符合 `contracts/audit_result.schema.json`（v1.0.0）的 `AuditResult[]`：

- `module` 固定为 `shopee-br-ip-review`
- **`confidence` 恒为 `signal`**（硬约束 H1）
- **`requires_human_review` 恒为 `true`**（硬约束 H1）
- `action` 最高为 `escalate_legal`；普通品牌命中为 `flag_for_review`
- `review_rationale` 说明**需要人判断什么**
- `evidence_refs[]` = 需要的授权材料类型

## 5. 规则与来源要求

### 5.1 规则文件

`rules/02_ip_trademark_copyright.json`（8 条，前缀 `IP`）

| rule_id | 内容 |
|---|---|
| `SBR-IP-001` | 注册商标未经授权使用 |
| `SBR-IP-002` | 明示仿牌/假冒宣称 |
| `SBR-IP-003` | 外卖平台 logo 的包（平台码 [349]） |
| `SBR-IP-004` | 未经授权使用 Shopee logo/banner（[608]） |
| `SBR-IP-005` | 图片中检出第三方 logo |
| `SBR-IP-006` | **兼容性描述不算侵权**（反误判规则） |
| `SBR-IP-007` | 著作权内容未授权使用（[602]） |
| `SBR-IP-008` | 外观设计（Lei 9.279/96 Art. 2º, II） |

### 5.2 法律依据

| 法条 | 要点 | 用途 |
|---|---|---|
| **Lei 9.279/96 Art. 132, II** | 商标权人**不得阻止**配件制造商使用该商标指示产品用途（只要遵守正当竞争惯例） | `SBR-IP-006` 的依据 —— 兼容性描述**不构成侵权** |
| Lei 9.279/96 Art. 2º, II | 外观设计由国家授予专有权 | `SBR-IP-008` |
| Lei 9.279/96 Art. 194 / 195 | 虚假来源标识、不正当竞争 | 侵权后果 |
| Lei 9.610/98 | 著作权 | `SBR-IP-007` |

### 5.3 平台依据

| 平台码 | 内容 | 严重度 |
|---|---|---|
| [133] | 违反注册商标权 | Baixa，不扣分 |
| [601] | 假冒 / 违反商标 | **Alta，扣分** |
| [205] | 疑似非正品 | Média，扣分 |
| [602] | 违反著作权 | **Alta，扣分** |
| [603] | 违反外观设计 | **Alta，扣分** |
| [604] | 违反专利 | **Alta，扣分** |
| [349] | 外卖平台 logo 的包 | Baixa |
| [608] | 未经授权使用 Shopee logo | Baixa |

### 5.4 解封机制（重要，来自 2026-09 合规审计线）

知识产权类账号冻结**只有投诉方（品牌方）撤销投诉才能重新激活**；监管机构类必须由原投诉机构书面同意。

> **这意味着**：卖家申诉前必须先让品牌方撤诉 —— 申诉不是解封的必要条件，撤诉才是。运营人员应知此流程。
>
> 是否把「品牌方已撤诉」做成解冻的硬前置条件，属于业务策略选择，已登记为待裁定项 `Q-A`。在裁定前，本模块只**提示**该事实，不阻断。

## 6. 硬约束

| ID | 本模块如何满足 |
|---|---|
| **H1** | 所有结果 `confidence="signal"` + `requires_human_review=true` —— **无条件** |
| H2 | `action` 最高 `escalate_legal`；只有 `platform_official`/`law` 的 `active` 规则可产生该动作 |
| H3 | 缺 `images` → `SBR-IP-005`/`008` 未评估；缺 `history.authorization_documents` → 授权规则未评估 |
| H4 | 引文逐字核验（当前 8/8 通过） |
| H5 | 授权材料只存引用 |
| H6 | `escalate_legal` 为 `human_only` —— 本模块不提供任何执行入口 |

### 6.1 不得使用的表述

| 禁止 | 正确 |
|---|---|
| 「这是假货」「这是侵权」 | 「命中注册商标词，判定为疑似侵权风险信号」 |
| 「品牌方已投诉」 | 「若权利人发起投诉则属 [601] 情形」 |
| 把 `signal` 说成 `confirmed` | 恒为 `signal` |

## 7. 指示性使用 vs 品牌宣称（核心判定）

| 判定要素 | 指示性使用（不违规） | 品牌宣称（高风险） |
|---|---|---|
| 表述形式 | 「compatível com」「para o modelo」「aplicável em」 | 「original」「oficial」「importado」「réplica」「1ª linha」 |
| 语境 | 指示适配的机型/系列 | 宣称商品本身即该品牌 |
| 商品性质 | 配件（非品牌商品本身） | 品牌商品或仿牌 |
| 后果 | `allow` 或 `flag_for_review` | `escalate_legal` |

**举例**：
- ✅ `Capa de Banco Automotiva Impermeável Compatível com Ford Focus 2015-2020` → 指示性使用
- ❌ `Tênis Nike Air Max Importado Original` → 品牌宣称

## 8. 失败处理

| 情形 | 行为 | 产出 |
|---|---|---|
| 无图片数据 | 图片类规则不评估 | `unevaluated` + warning |
| 图片已分析但无 logo | 正常通过 | `allow` |
| 品牌方名称未知 | 标记待核实 | `pending_verification` 语义 |
| 授权材料不完整 | 列出缺失项 | `require_evidence` + `evidence_refs[].provided=false` |
| 命中但无法区分宣称/指示 | **不猜测** | `flag_for_review` + `review_rationale` |
| 无投诉/授权/通知 | 绝不表述为侵权 | 恒 `signal` |

## 9. 测试案例与验收标准

| 类别 | 用例 | 断言 |
|---|---|---|
| 正例 | 标题含 `Nike` + `Importado Original` | 命中品牌规则，`action=escalate_legal` |
| 正例 | 描述含 `réplica` | 命中 `SBR-IP-002` |
| 正例 | 图片 `detected_logos=["Adidas"]` | 命中 `SBR-IP-005` |
| 正例 | 授权材料仅 `invoice`，缺 `anvisa_registration` | 命中授权规则，`evidence_refs` 含缺失项 |
| **反例** | `Compatível com Ford Focus 2015-2020` | **不判侵权**（Art. 132, II） |
| **反例** | `images[].detected_logos=[]` | **不命中** `SBR-IP-005` |
| **反例** | 无图片 | 照片类规则**未评估**，不判通过 |
| H1 | 任意 IP 命中 | `confidence="signal"` + `requires_human_review=true` |
| 契约 | 正常输入 | 输出通过 `audit_result` 校验 |
| 表述 | 全部结果 | 不含「侵权」字样而无投诉/授权/通知支撑 |

## 10. 依赖

- **依赖**：`TASK-POLICY-01`（来源与引文）、`TASK-INGEST-01`（商品、图片字段、授权清单）
- **期待下游**：`shopee-br-reporting` 消费本模块结果；主 Skill 整合时**不得降级**本模块的 `escalate_legal`
- **对其他模块的影响**：`SBR-IP-006` 的兼容性上下文可被 listing-audit 复用（避免重复实现兼容性识别）

## 13. 文件所有权

本模块的路径所有权由 `contracts/file_ownership.json` 定义（`ownership_version` 1.4.0）。

**可写路径（白名单）—— 越界即任务失败：**

```
skills/shopee-br-ip-review/**
tests/shopee-br-ip-review/**
rules/02_ip_trademark_copyright.json
```

**只读路径：**

```
contracts/**
data/schema/**
research/**
rules/04_cases_relist_authorization.json
lexicon/term_groups.json
lexicon/exemptions.json
tools/scan_lexicon.py
```

**本模块拥有的规则前缀：** `IP`

> IP=商标版权外观设计专利。rules/04 中的 AU 前缀归 duplicate-detection，本模块只读引用，不改写。

公共契约（`contracts/**`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、`manifest.json`、`tasks/**`、`tests/test_plan.md`、`tests/fixtures/**`、`docs/**`、`tools/**`、`scripts/**`、`.archive/**`）对所有模块 Agent **只读**。
需要修改时提交契约变更建议，不要自行改动。

## 14. 待填内容

- [ ] `references/ip_categories.md` —— IP 四类的定义、法律依据、平台码
- [ ] `references/nominative_use.md` —— 指示性使用 vs 品牌宣称的判定表与更多例子
- [ ] `references/authorization_checklist.md` —— 授权材料清单与 INPI 核验方法
- [ ] `references/dissolution_flow.md` —— 品牌方撤诉解封流程说明
- [ ] `tests/shopee-br-ip-review/run_tests.py`

## 15. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1.0 | 2026-10-27 | 骨架创建（待 TASK-IP-01 填充） |
