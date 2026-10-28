| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-PR-002` |
| 所属模块 | `shopee-br-policy-research` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 平台违规码目录的结构与解读 |
| 相关文档 | `research/violation_codes.json`、`research/raw/shopee_br_banimento_suspensao_anuncios.txt` |
| 未决事项 | 无 |

---

## 1. 目录的来源

`research/violation_codes.json` 解析自平台教育中心文章
**「Principais Motivos de Banimento e Suspensão de Anúncios」**
（`https://seller.br.shopee.cn/edu/article/5139`），
抓取件为 `research/raw/shopee_br_banimento_suspensao_anuncios.txt`（22KB）。

| 字段 | 值 |
|---|---|
| `source_title` | Principais Motivos de Banimento e Suspensão de Anúncios |
| `source_url` | `https://seller.br.shopee.cn/edu/article/5139` |
| `source_tier` | `platform_official` |
| `source_file` | `research/raw/shopee_br_banimento_suspensao_anuncios.txt` |
| `code_count` | 106 |

> **同一码号可能出现多次**（不同底层原因）—— 例如 `[311]` 既对应
> 「直接促进吸烟消费的配件」也对应「促进吸烟行为的产品」。
> 它们是**不同的条目**，不是重复数据。

## 2. 单条结构

```json
{
  "code": 100,
  "description": "Item proibido ou restrito pelos órgãos reguladores.",
  "severity_pt": "Alta",
  "severity": "high",
  "generates_penalty_point": true,
  "penalty_note": "Gera ponto de penalidade. Para mais informações, clique aqui.",
  "category": "regulator_prohibited",
  "platform_code": "[100]"
}
```

| 字段 | 含义 |
|---|---|
| `code` | 平台违规码（数字） |
| `description` | 平台原文描述（葡语） |
| `severity_pt` | 平台原文严重度：`Extrema` / `Alta` / `Média` / `Baixa` |
| `severity` | 归一化严重度：`critical` / `high` / `medium` / `low` |
| `generates_penalty_point` | **是否产生处罚点**（平台明文） |
| `penalty_note` | 平台原文（`Gera ponto de penalidade...` / `Não gera ponto de penalidade...`） |
| `category` | 归类，见 §3 |
| `platform_code` | 带方括号的码（`[100]`），用于规则的 `source.platform_code` |

### 2.1 严重度映射

| `severity_pt` | `severity` | 条数 |
|---|---|---|
| `Extrema` | `critical` | 13 |
| `Alta` | `high` | 27 |
| `Média` | `medium` | 24 |
| `Baixa` | `low` | 42 |

### 2.2 处罚点交叉表

| `severity` | 产生处罚点 | 不产生 |
|---|---|---|
| `critical` | 13 | 0 |
| `high` | 26 | 1 |
| `medium` | 14 | 10 |
| `low` | 0 | 42 |

> **`low` 严重度全部不产生处罚点** —— 但仍会被下架。
> `high` 有 1 条例外（不产生处罚点），所以**不能**用严重度反推处罚点。

## 3. 分类

| `category` | 条数 | 说明 |
|---|---|---|
| `prohibited_restricted_policy` | 41 | 禁售/受限商品政策 |
| `listing_violation` | 39 | 刊登质量违规 |
| `regulator_prohibited` | 11 | 监管机构禁止的物品（Anatel / Anvisa 等） |
| `ip_trademark` | 7 | 商标 |
| `regulator_policy_change` | 3 | 监管政策变化导致商品变为禁售 |
| `duplicate_listing` | 2 | 重复刊登 |
| `ip_copyright` | 1 | 版权（`[602]`） |
| `ip_design` | 1 | 外观设计（`[603]`） |
| `fulfillment` | 1 | 不发货（`[103]`） |

### 3.1 与规则前缀的对应

违规码的 `category` 与规则库的 `rule_id` 前缀不是一一对应，但概念上对应：

| 违规码 category | 规则前缀 | 规则文件 |
|---|---|---|
| `prohibited_restricted_policy` | `PI` `RI` | `rules/01_prohibited_restricted_items.json` |
| `regulator_prohibited` | `PI` `RI` | 同上 |
| `listing_violation` | `LV` | `rules/03_listing_violations.json` |
| `ip_trademark` / `ip_copyright` / `ip_design` | `IP` | `rules/02_ip_trademark_copyright.json` |
| `duplicate_listing` | `DUP` | `rules/03_listing_violations.json` |
| `regulator_policy_change` | `PI`（政策变更） | `rules/01_prohibited_restricted_items.json` |
| `fulfillment` | （本库未覆盖） | — |

> `fulfillment`（不发货）在本规则库里**没有对应规则**。
> 平台确实有这条码，但本项目聚焦内容合规，未实现该类判定。

## 4. 怎么用这个目录

### 4.1 规则引文

规则的 `source_excerpt` **逐字**取自该码的 `description` + 严重度 + 处罚点说明。
例如 `SBR-PI-001` 的引文：

```
[317] Anúncio proibido para armas de fogo, tasers, munições e coletes à prova de balas. Severidade: Extrema. Gera ponto de penalidade.
```

核验命令：

```bash
env -u LD_LIBRARY_PATH python3 tools/verify_citations.py
```

当前：**50/50 逐字核验通过。**

### 4.2 填规则的 `source.platform_code`

规则的 `source.platform_code` 直接用目录里的 `platform_code` 值（如 `[337]`），
便于从结论反查平台原文。

### 4.3 严重度不是动作

**违规码的严重度 ≠ 规则的动作。**

| 概念 | 出处 |
|---|---|
| 平台严重度（Extrema/Alta/Média/Baixa） | 平台原文 |
| 规则 `severity`（risk_level） | 规则作者的判断 |
| 规则 `decision`（action） | 由 `contracts/risk_action_matrix.json` 查表决定 |

例：码 `[349]`（外卖 App logo 背包）严重度是 `Baixa`（`low`），
但平台明确「listing is removed」—— 下架。规则 `SBR-IP-003` 的
`decision` 是 `flag_for_review`（人工复核），不是 `block`：
严重度低 ≠ 可以忽略，**关键词命中只是筛查信号**（硬约束 H1）。

## 5. 禁止事项

| # | 禁止 |
|---|---|
| 1 | 引用**处罚点分值** —— 平台页面只说「是否产生处罚点」，没说扣几分。分值未公开 |
| 2 | 把「不产生处罚点」读成「不违规」—— 仍会被下架 |
| 3 | 同一码号出现多次就当重复数据删除 —— 是不同底层原因 |
| 4 | 用 `severity` 反推 `generates_penalty_point` —— `high` 有 1 条例外 |

## 6. 维护

平台更新该页面后：

```bash
# 1. 重抓
#    tools/fetch_edu_article.py 或 tools/fetch_sources.py
# 2. 重新解析违规码
env -u LD_LIBRARY_PATH python3 tools/parse_violation_codes.py
# 3. 核对
env -u LD_LIBRARY_PATH python3 tools/check_sources.py
env -u LD_LIBRARY_PATH python3 tools/verify_citations.py
```

码号集合是**平台事实** —— 若某码消失或新增，如实记录，
不要为了「保持 106 条」而保留已消失的码。
