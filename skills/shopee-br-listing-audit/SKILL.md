---
name: shopee-br-listing-audit
description: Use when you need to check a Shopee Brazil product listing for prohibited or restricted items and listing-quality violations — keywords, exaggerated health or miracle claims, misleading discounts, keyword stuffing, off-platform contact details, wrong category, and the 2026-08-06 Anvisa change for over-the-counter medicines. Produces cited AuditResults with verdicts; never makes IP infringement determinations.
---

# Shopee BR 商品内容合规审核

> 状态：**骨架 — 待 `TASK-LISTING-01` 填充**
> 契约版本：1.0.0
> 规则前缀：`PI` `RI` `MED` `LV`
> 归属：`skills/shopee-br-listing-audit/**`、`tests/shopee-br-listing-audit/**`

---

## 1. 职责

| # | 职责 | 规则前缀 |
|---|---|---|
| 1 | 禁售类目检查（武器、烟草电子烟、管制药品、化学危险品、假币证件、赌博、野生动物、成人内容、政府标识） | `PI` |
| 2 | 受限类目检查（酒精、健康品、电池、汽车件、生鲜、宠物药、气枪、特殊乳制品） | `RI` |
| 3 | 药品与保健品专项 | `MED` |
| 4 | listing 质量违规（夸大宣称、误导折扣、标题堆砌、站外引流、描述不足、图片不当、类目错误、注册信息缺失、尺寸重量不准、年龄分级不符） | `LV` |

## 2. 非职责

- ❌ 不做 IP 侵权判定 —— 归 `shopee-br-ip-review`
- ❌ 不做重复刊登 / 跨店关联 / 重发检查 —— 归 `shopee-br-duplicate-detection`
- ❌ 不解析原始文件 —— 归 `shopee-br-data-ingestion`
- ❌ 不生成报告 —— 归 `shopee-br-reporting`
- ❌ 不认定侵权

## 3. 输入契约

使用 `contracts/skill_input.schema.json`（v1.0.0）：

| 字段 | 本模块用法 |
|---|---|
| `request_id` | 贯穿产出 |
| `task_type` | 固定 `listing_audit` |
| `products[]` | 待审商品；使用 `title` / `description` / `attributes` / `category` / `brand` / `images[]` |
| `rules[]` | 待用规则（`rule_envelope` 格式） |
| `scope.shop_ids` / `scope.categories` | 生效范围 |
| `options.rule_prefixes` | 限定本次使用的规则前缀（缺省=本模块全部） |
| `provenance` | 原样透传 |

## 4. 输出契约

产出符合 `contracts/audit_result.schema.json`（v1.0.0）的 `AuditResult[]`：

- `module` 固定为 `shopee-br-listing-audit`
- `rule_refs[]` = 命中的规则（含 `matched_field` / `matched_excerpt` / `source_tier`）
- `evidence_refs[]` = 需要的证据类型（`evidence_required`），`provided: false` 表示待补
- `unevaluated[]` = 因输入缺字段而未评估的规则
- `errors[]` = 解析错误 + 未评估警告

## 5. 规则与来源要求

### 5.1 规则文件

| 文件 | 前缀 | 条数 |
|---|---|---|
| `rules/01_prohibited_restricted_items.json` | `PI` `RI` | 17 |
| `rules/05_medicines_health.json` | `MED` | 3 |
| `rules/03_listing_violations_duplicates.json` 的 `LV` 部分 | `LV` | 14 |

> `rules/03` 混有 `DUP` 前缀（属 duplicate-detection）。**本模块在集成阶段前不得直接修改该文件**，只提拆分建议。

### 5.2 来源层级与动作

| 层级 | 允许的最高动作 |
|---|---|
| `platform_official` | `block`（禁售类） / `require_evidence`（受限类） |
| `law` | `flag_for_review`（消费者保护类，如 CDC 误导性广告） |
| `internal_risk` | `flag_for_review` —— **不可阻断** |
| `unverified` / `draft` | `flag_for_review` |

### 5.3 政策时效性（重要）

- **2026-08-06 起**，Shopee 获 Anvisa 授权销售非处方药（MIP），但**仅限持牌药店/药妆店**。任何「药品一律禁售」的表述都已过时。规则 `SBR-MED-001/002/003` 分三种情形处理。
- 平台违规码以 `research/violation_codes.json` 为准（当前 106 条）。
- 处罚点**具体分值**平台未公开 —— 不得推断，不得写入规则。

### 5.4 葡语词边界

Python 的 `\b` 在葡语重音元音旁不可靠（`at[óo]xico\b` 会吞 `Óculos` 首字母）。规则中的葡语边界一律用：

```
(?<![a-zA-Zà-ÿÀ-ß])词(?![a-zA-Zà-ÿÀ-ß])
```

## 6. 硬约束

| ID | 本模块如何满足 |
|---|---|
| H1 | 不产生 IP 类别结果 |
| H2 | 阻断类动作只来自 `platform_official` 且 `active` 的规则 |
| H3 | 规则依赖的输入字段缺失 → 产出 `unevaluated` + `errors[]` warning，**不产生 result** |
| H4 | 所有 `active` 规则引文逐字核验通过 |
| H5 | 证据只引用类型，不含内容 |
| H6 | 本模块不产生 `freeze_relist` / `escalate_legal` |

### 6.1 误报控制（关键）

**关键词命中 ≠ 违规。** 已知的高误报来源：

| 来源 | 现象 | 处置 |
|---|---|---|
| chongyang1 | 57 处触线命中全为误报（`reduzir` 46 / `desconforto` 4 / `seguro` 1） | 功能描述与安全提示**不违规**；命中后须读上下文 |
| 店主 2026-09 审阅 | 491 个详情完全相同 | 属模板化问题 → `revise`，不是违规 |
| 兼容性描述 | 「compatível com X」被误判 | 归 IP 模块；本模块不处理品牌 |

**规则的正例与反例各至少一个** —— 反例用于防止规则过宽。

## 7. 失败处理

| 情形 | 行为 | 产出 |
|---|---|---|
| 商品缺 title | 无法审核 | `error`（severity=error）+ 该商品不出结果 |
| 缺 description | 依赖 description 的规则不评估 | `unevaluated` + warning |
| 缺 images | 依赖图片的规则不评估 | `unevaluated` + warning |
| 缺 category / brand | 同上 | `unevaluated` + warning |
| 规则引文核验失败 | 该规则不参与判定 | `warning` + 说明 |
| 命中但上下文不明确 | **不猜测** | `flag_for_review` + `review_rationale` 说明需人判断什么 |
| 命中禁售类目且证据充分 | 阻断 | `block` + `requires_human_review: true` |

## 8. 测试案例与验收标准

| 类别 | 用例 | 断言 |
|---|---|---|
| 正例 | 电子烟 listing | 命中 `SBR-PI-002`，`action=block` |
| 正例 | 假冒宣称（"réplica"） | 命中 `SBR-IP-002`——**注意属 IP 模块**，本模块只命中 `PI/RI/MED/LV` |
| 正例 | 夸大健康宣称 | 命中 `SBR-LV-001`，`action=flag_for_review` |
| 正例 | 站外引流（WhatsApp） | 命中 `SBR-LV-005` |
| 正例 | 维生素 D3（保健品） | 命中 `SBR-MED-003` 或 `SBR-RI-002`，`action=require_evidence` |
| 反例 | 普通玻璃杯 listing | **不命中任何规则** |
| 反例 | 含 `reduzir o espaço` 的功能描述 | **不命中**夸大宣称规则 |
| 反例 | 含 `em caso de desconforto, suspenda o uso` 的安全提示 | **不命中** |
| 契约 | 正常输入 | 输出通过 `audit_result` 校验 |
| H3 | 缺 category 的输入 | `unevaluated` 含 `SBR-LV-008`，无对应 result |
| H2 | `internal_risk` 规则 | `action` 不为 `block` |
| 逐条 | 每条规则 | ≥1 正例 + ≥1 反例 |

## 9. 依赖

- **依赖**：`TASK-POLICY-01`（来源与引文）、`TASK-INGEST-01`（商品与字段）
- **期待下游**：`shopee-br-reporting` 消费本模块的 `AuditResult[]`
- **对其他模块的影响**：本模块产出 `PI/RI/MED/LV` 类结果；主 Skill 整合时与 IP、重复模块的结果合并

## 12. 文件所有权

本模块的路径所有权由 `contracts/file_ownership.json` 定义（`ownership_version` 1.6.0）。

**可写路径（白名单）—— 越界即任务失败：**

```
skills/shopee-br-listing-audit/**
tests/shopee-br-listing-audit/**
rules/01_prohibited_restricted_items.json
rules/05_medicines_health.json
lexicon/term_groups.json
lexicon/rewrite_map.json
lexicon/exemptions.json
lexicon/quality_patterns.json
lexicon/non_avoidable.json
lexicon/verb_conjugations.json
tools/scan_lexicon.py
```

**只读路径：**

```
contracts/**
data/schema/**
lexicon/term_groups.json
research/**
rules/03_listing_violations_duplicates.json
```

**本模块拥有的规则前缀：** `PI, RI, MED, LV`

> PI=禁售受限、RI=受限商品、MED=药品健康专项、LV=listing 质量。rules/03 中的 LV 前缀由本模块提出拆分建议，拆分由集成 Agent 执行。

公共契约（`contracts/**`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、`manifest.json`、`tasks/**`、`tests/test_plan.md`、`tests/fixtures/**`、`docs/**`、`tools/**`、`scripts/**`、`.archive/**`）对所有模块 Agent **只读**。
需要修改时提交契约变更建议，不要自行改动。

## 13. 待填内容

- [x] `references/audit_semantics.md` —— 各规则类别的审核语义与判定边界
- [x] `references/false_positive_control.md` —— 误报来源清单与上下文判定规则
- [x] `references/policy_currency.md` —— 政策时效性（含 2026-08-06 变更）
- [x] `references/evidence_checklist.md` —— 各受限类目的证据清单
- [x] `references/lexicon_scanning.md` —— 合并词库的使用、匹配算法与误报控制
- [x] `tests/shopee-br-listing-audit/run_tests.py` —— 383 项断言
- [x] `DELIVERY.md` —— 交付说明

## 14. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1.0 | 2026-10-27 | 骨架创建（待 TASK-LISTING-01 填充） |
