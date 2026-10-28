# 政策时效性规范

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-LA-004` |
| 所属模块 | `shopee-br-listing-audit` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 规则来源的时效状态、`last_verified` 的含义、重新核验触发条件、政策变更的处理流程 |
| 相关文档 | `references/audit_semantics.md` §6、`references/evidence_checklist.md`、`references/false_positive_control.md`、`contracts/risk_action_matrix.json`、`research/sources.json`、`research/raw/` |
| 未决事项 | 无 |

---

## 1. 时效状态机

规则的 `status` 字段（`data/schema/rule.schema.json` 的 `enum`）只有 4 个取值，
它们决定规则**是否参与判定**：

| `status` | 含义 | 是否产出结论 | 实现位置 |
|---|---|---|---|
| `active` | 已核验且在有效期内 | ✅ 参与判定 | `engine.py` 的 `_evaluate_rule()` |
| `draft` | 编写中 | ❌ **不产出任何结论** | 同上（直接返回 `skipped`） |
| `deprecated` | 已被政策取代 | ❌ **不产出任何结论** | 同上 |
| `suspended` | 暂停执行 | ❌ **不产出任何结论** | 同上 |

> **只有 `active` 才可能被评估。** `engine.py` 的 `_evaluate_rule()` 第一步就是：
>
> ```python
> if rule.get("status") != "active":
>     return {"status": "skipped", "rule": rule,
>             "reason": f"rule {rule_id} has status '{rule.get('status')}' and "
>                       f"therefore produced no conclusion", ...}
> ```
>
> 非 `active` 的规则**不进 `rule_refs[]`，不进 `unevaluated[]`**（它不是「无法评估」，
> 是「不在评估范围内」），也不进 `evidence_refs[]`。它只出现在交接记录的
> `known_gaps[]` 里：
>
> ```
> 1 rule(s) are not 'active' and produced no conclusion: SBR-LV-014.
> ```

### 1.1 `status != active` 与 H2 的关系

硬约束 **H2** 规定：`block` / `freeze_relist` / `escalate_legal` 只能由
`source.tier ∈ {platform_official, law}` 的 **`active`** 规则产生。

代码里的落地是两道：

1. `rules.py` 的 `blocking_allowed()` —— 同时检查 `tier` 与 `status`；
2. `engine.py` 的 `_resolve_action()` —— 即使规则非 `active`（理论上不会走到，
   因为 `_evaluate_rule` 已经拦掉了），也会走降级分支。

> 本仓库当前 57 条规则的状态分布：`active` 56 条、`draft` 1 条
> （`SBR-LV-014`，变体使用不当）。
> 本模块的 41 条里同样只有 `SBR-LV-014` 是 `draft`。

---

## 2. `last_verified` 的确切含义

### 2.1 定义

`last_verified` = **该规则的 `source.excerpt` 被逐字核对过、且与来源页面当前内容一致的日期**
（ISO 8601，`YYYY-MM-DD`）。

它**不是**：

| 不是 | 为什么 |
|---|---|
| 规则创建日期 | 规则可以反复修订（`version` 字段记录修订次数） |
| 规则最后修改日期 | 修改的是规则逻辑（正则、动作）时，`last_verified` 可以不变 |
| 平台页面的发布日期 | 那是 `source` 页面自己的属性，与核验动作无关 |
| 「规则仍然有效的保证」 | 它只保证**引文属实**，不保证**政策语义未变** |

`data/schema/rule.schema.json` 的原文描述：
`"Date the rule text was last checked against its source."`
`contracts/rule_envelope.schema.json`：`source.last_verified` 是**必填**字段。

### 2.2 它在代码里做什么用

`last_verified` **不参与判定**。它只出现在两处，都是给人和下游看的：

| 位置 | 内容 |
|---|---|
| `AuditResult.provenance.notes` | `SBR-PI-001 \| tier=platform_official \| status=active \| v1 \| last_verified=2026-10-27 \| source_excerpt='[317] …'` |
| `rules.py` 的 `normalise_rule()` | 归一化到 `source.last_verified`（`rule.last_verified` 优先，回落 `rule.source.last_verified`） |

> **模块不自动判定「过期」。** 引擎里没有任何按日期比较、降级、
> 或自动改 `status` 的逻辑 —— `engine.py` 只读 `status` 字段，
> 不看 `last_verified`。**时效判断是人的动作，不是代码的动作。**

### 2.3 当前值

| 文件 | 库级 `last_verified` | 规则级 `last_verified` | 条数 |
|---|---|---|---|
| `rules/01_prohibited_restricted_items.json` | 2026-10-27 | 2026-10-27 | 17 |
| `rules/05_medicines_health.json` | 2026-10-27 | 2026-10-27 | 3 |
| `rules/03_listing_violations.json`（`LV` 部分） | 2026-10-27 | 2026-10-27 | 14 |

> 库级与规则级的 `last_verified` 是两个独立的字段，**都要维护**。
> 规则级才是「这条规则的引文被核验过」。

### 2.4 有效期

**本仓库没有内置的有效期表，也不自动按天数降级。**

骨架文档里曾写过「`platform_official` 90 天 / `law` 180 天」这类建议，
但代码里**没有实现**（`engine.py` / `rules.py` 都不含日期比较逻辑），
因此本文档不把它写成生效规则 —— 见 §6 的说明。

现实中的检查节奏由**抓取件的可核验性**决定，而不是由天数决定：

| 层 | 权威来源 |
|---|---|
| `source.excerpt` 是否逐字存在于 `research/raw/` | `tools/verify_citations.py`（宽松匹配：折叠空白、统一引号与破折号、去掉句末标点） |
| 抓取件是否与 `research/sources.json` 一致 | `tools/check_sources.py` |

当前状态（实测）：

```
57/57 excerpts verified verbatim, 0 failed
来源清单与抓取件一致。
  抓取失败（已登记，不得用于支撑规则）：2 条
    - br_anvisa_publicidade_medicamentos
    - br_anvisa_medicamentos_prescricao
```

---

## 3. 什么情况下必须重新核验

按触发条件从强到弱：

| # | 触发条件 | 动作 |
|---|---|---|
| 1 | `tools/verify_citations.py` 报某条规则「excerpt not found verbatim」 | 重新抓取该来源 → 更新引文 → 更新 `last_verified` → 若语义变了，`version + 1` 且 `status` 置 `draft` |
| 2 | `tools/check_sources.py` 报「报告已过期」或抓取失败 | 同上；抓取失败时该来源**不得**用于支撑任何规则 |
| 3 | 平台页面「Última atualização」日期晚于 `last_verified` | 重新抓取并逐条比对引文 |
| 4 | 监管机构（Anvisa / MAPA / INMETRO / ANATEL / ANP）发布新规 | 评估受影响的规则；语义实质变化则 `version + 1` + `status` 置 `draft` |
| 5 | 平台新增 / 变更违规码 | 更新 `research/violation_codes.json`（当前 106 条），再评估对应规则 |
| 6 | 出现新的错误案例（误报或漏报） | 收紧 / 放宽该规则的触发条件，`version + 1`，并补正例 + 反例 |
| 7 | 引文核验通过但页面语义变了（同一段文字含义不同） | 引文不动，但规则的 `description` / 触发条件要改，`version + 1` |

### 3.1 重新核验的标准流程

```
检测到政策变更 / 核验失败
  ↓
重新抓取 → research/raw/<slug>.txt（不覆盖历史抓取件，另存带日期的版本）
  ↓
逐字核验受影响规则的引文（tools/verify_citations.py）
  ↓
更新规则的 source.last_verified / source.excerpt
  ↓
若语义实质变化 → 规则 version + 1，status 置 draft
  ↓
重新执行受影响规则的测试（tests/shopee-br-listing-audit/run_tests.py）
  ↓
status 改回 active 前，必须重新跑引文核验（tools/verify_citations.py）
```

> **不覆盖历史抓取件。** 旧引文的可核验性依赖于旧抓取件仍在。
> `tools/fetch_sources.py` 的行为是：目标 `.txt` 存在且 > 200 字节就 `skip`（缓存），
> 所以重抓需要人工先把旧文件改名或删除。

### 3.2 规则版本号的用法

`version` 记录的是**规则本身的修订次数**，与 `last_verified` 独立。
`engine.py` 的 `rule_version()` 把「规则 ID + 版本 + 状态」拼成一个稳定摘要：

```python
payload = json.dumps([[rule["rule_id"], rule.get("version"), rule.get("status")]
                       for rule in self.rules], ensure_ascii=False, sort_keys=True)
digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
return f"sbr-listing-rules/{self.module_version()}+{digest}"
```

写进 `AuditResult.rule_version`（形如 `sbr-listing-rules/1.0.0+<12 位摘要>`）。
**下游可以据此判断两次审核用的规则集是否一致。**

### 3.3 规则 `notes` 字段的时效记录惯例

每条被修改过的规则都在 `notes` 里写明改动原因与日期。例如：

| 规则 | `version` | `notes` |
|---|---|---|
| `SBR-PI-005` | 2 | `2026-10-27: 修复触发正则缺失的右括号 —— 原文无法编译（re.compile 抛错），评估时会中断。匹配语义按原意恢复…` |
| `SBR-RI-003` | 2 | `2026-10-27: 收敛触发条件 —— 原正则中 `bateria(s)?\s+(...)?` 的 `?` 让「bateria」单独即可命中，会把普通工具（如电钻）判为电池类（实测误报）…` |
| `SBR-LV-003` | 2 | `2026-10-27: 修正词数判定 —— 原正则的重复单元 `\w+\b[\s,]*` 要求每词后跟空白/逗号，连字符词（如 Esportivo-running）会中断重复，导致实际词数被低估。改为按 `\w+[-–]?` 连续计词，阈值 15 词不变。` |
| `SBR-LV-006` | 3 | `2026-10-27: 修正算子 —— 原写法 \`description lt 120\` 意为「字符串 < 数字」，评估时抛 TypeError。改为 \`length_lt\`（字符数比较），语义不变。` |
| `SBR-LV-013` | 2 | `2026-10-27: 明确语义边界 —— 平台未公开尺寸/重量上限数值（禁止引用未公开数值），本规则只标记「商品声明了完整三维尺寸」这一可判定事实，是否超限由人工复核确认；动作保持 flag_for_review，不阻断。` |

> `notes` 是**改动的自述**，不是权威依据。权威依据永远是 `source.excerpt` + 抓取件。

---

## 4. 2026-08-06 Anvisa MIP 变更对判定的影响

### 4.1 政策原文

来源：`research/raw/shopee_br_categorias_restrritas.txt`
（`source.url` = `https://seller.shopee.com.br/edu/article/7379`，`article_id` = `7379`，
`last_verified` = 2026-10-27）

> `Desde 6 de agosto de 2026, a Shopee está autorizada pela Anvisa a comercializar medicamentos isentos de prescrição (MIPs), apenas por farmácias e drogarias regularmente licenciadas que sigam rigorosamente todas as regulamentações da categoria e da agência, conforme a Resolução-RE nº 3.056/2026.`

该抓取件里还有：

> `Última atualização: 10 de agosto de 2026.`

以及同一篇文章里「允许」的清单：

> `Suplementos de saúde, como: vitaminas, ervas e produtos naturais;`

以及「禁止」的清单：

> `Medicamentos de uso humano em geral; Medicamentos de uso veterinário; Medicamentos, produtos ou serviços que estejam relacionados com a realização de abortos; Clorito de sódio, dióxido de cloro (CDS) ou soluções minerais milagrosas (MMS), em todas as suas formas e apresentações;`

### 4.2 变更前后的判定差异

| | 变更前（错误理解） | 变更后（现行判定） |
|---|---|---|
| 非处方药（MIP） | 一律禁售 → `block` | **可以卖**，但**只有持牌药房 / 药店**可以卖 → 证据不足时 `require_evidence` |
| 判定落在哪条规则 | 「药品」通用规则 | `SBR-MED-001`（绝对禁止）/ `SBR-MED-002`（资质）/ `SBR-MED-003`（宣称）三条分立 |
| 裸词 `medicamento` | 命中即阻断 | **不触发** `SBR-MED-001`；由 `SBR-MED-002` 的资质维度接管 |
| 保健品 | 与药品混在一起判 | 保健品本身**允许**；被执行的是**失实宣称**（`SBR-MED-003`） |

### 4.3 三条 MED 规则的分工

| 规则 | `category` | `severity` | `decision` | 判定的问题 | 证据清单 |
|---|---|---|---|---|---|
| `SBR-MED-001` | `prohibited_item` | `critical` | `block` | 是不是**绝对禁止**的那几类药？ | `product_photographs`、`supplier_invoice`、`anvisa_registration` |
| `SBR-MED-002` | `restricted_item` | `high` | `require_evidence` | 卖方**是不是持牌药房 / 药店**？ | `anvisa_registration`、`pharmacy_license`、`distribution_authorization`、`supplier_invoice` |
| `SBR-MED-003` | `consumer_protection` | `high` | `flag_for_review` | 保健品的**宣称是不是失实**？ | `manufacturer_claim_reference`、`product_photographs` |

`rules/05_medicines_health.json` 的库级 `notes` 写明了这次变更的落点：

> `IMPORTANT — this library encodes a policy change dated 6 August 2026. Since then Shopee is Anvisa-authorised to sell over-the-counter medicines (MIPs), but ONLY by regularly licensed pharmacies and drugstores that follow the category's and the agency's regulations strictly, per Resolução-RE nº 3.056/2026. A seller that is not a licensed pharmacy/drugstore therefore still may not list medicines at all. Any rule written before 2026-08-06 that treats ALL medicines as prohibited is out of date; this library separates the two cases explicitly.`

`SBR-MED-001` 的 `notes`：

> `This rule deliberately does NOT fire on the generic word 'medicamento' — see SBR-MED-002, which handles the licensing question. Firing on the generic word would block every supplement listing and would be wrong after the 6 Aug 2026 Anvisa authorisation.`

`SBR-MED-002` 的 `notes`：

> `The decision is require_evidence, not block: the medicine may be legitimate and the seller may be a licensed pharmacy. The evidence list is what separates the two cases. A seller that cannot produce the pharmacy/drugstore licence must not list the item.`

`SBR-RI-002`（健康类目）的 `notes`：

> `Supplements are permitted as products; the restricted-category handling here concerns the items needing regulator approval (monitors, test kits, injury supports). Medicines are handled separately by SBR-MED-001/002 because the 6 Aug 2026 Anvisa authorisation changed the rules for over-the-counter medicines specifically.`

### 4.4 实测的判定边界

| 输入 | `SBR-MED-001` | `SBR-MED-002` | `SBR-RI-002` | `SBR-MED-003` |
|---|---|---|---|---|
| `Medicamento de Uso Contínuo para Diabetes` | 不命中 | 不命中 | **命中**（`Medicamento de Uso Contínuo`） | 不命中 |
| `Suplemento de Saúde Vitamina D3` | 不命中 | 不命中 | **命中**（`Vitamina`） | 不命中 |
| `Vitamina D3 2000UI` | 不命中 | 不命中 | **命中**（`Vitamina`） | 不命中 |
| `Medicamento Isento de Prescrição 500mg` | 不命中 | **命中** | 不命中 | 不命中 |
| `Clorito de Sódio 500ml` | **命中** | 不命中 | 不命中 | 不命中 |
| `Suplemento de Saúde com Informações Falsas e Enganosas` | 不命中 | 不命中 | 不命中 | **命中** |

> **注意 `SBR-MED-002` 只认「非处方药 / MIP / 管制药 / 带 tarja 的药」这几种表述**，
> 不认裸词 `medicamento`。这与 `SBR-RI-002`（认 `medicamento de uso contínuo`）不重叠 ——
> 一个是「药店资质」维度，一个是「健康类目」维度。

### 4.5 「只有持牌药店才能卖」怎么落到动作上

`SBR-MED-002` 的动作是 `require_evidence`（`verdict: REVIEW`），不是 `block`。
区分「合法药店」与「无资质卖家」的是**证据清单**：

| 证据 | 用来区分 |
|---|---|
| `pharmacy_license` | 卖方是不是持牌药房 / 药店 —— **决定性证据** |
| `anvisa_registration` | 药品本身的注册 |
| `distribution_authorization` | 供货链条的授权 |
| `supplier_invoice` | 采购凭证 |

> 拿不出 `pharmacy_license` 的卖家**不得上架**该商品 ——
> 但这是「补材料」的动作，结论本身不是「商品违规」。

### 4.6 过期表述清单 —— 以下说法在 2026-08-06 之后一律是错的

| 错误表述 | 为什么错 | 正确表述 |
|---|---|---|
| 「药品一律禁售」 | MIP 已获 Anvisa 授权，可由持牌药店销售 | 「绝对禁止的药禁售；MIP 需持牌资质」 |
| 「保健品需 ANVISA 批号才能卖」 | 平台明确允许保健品（维生素、草药、天然产品） | 「保健品本身允许，被执行的是失实宣称与监管注册」 |
| 「出现 `medicamento` 就阻断」 | 会把所有保健品 listing 判成禁售 | 「裸词不触发；按品类分流到 MED-001 / MED-002 / RI-002」 |

---

## 5. 平台未公开数值 —— 禁止引用

**平台未公开的具体数值，本模块不得引用、不得推断、不得写入规则。**

### 5.1 已确认未公开的数值

| 数值 | 状态 | 平台原文说了什么 | 原文 |
|---|---|---|---|
| **处罚点分值** | ❌ 未公开 | 只说「Gera ponto de penalidade」/「Não gera ponto de penalidade」 | 见下 |
| **尺寸 / 重量上限** | ❌ 未公开 | 只说「exceder as dimensões e/ou pesos permitidos」 | `[509] Anúncio removido por exceder as dimensões e/ou pesos permitidos. Severidade: Alta. Gera ponto de penalidade.` |
| **处罚点分档表** | ❌ 未公开 | 抓取件里只有「Consulte a tabela a seguir:」，**表本身不在文本里**（是页面上的图片/表格，抓取器只拿到正文） | 见下 |
| **处罚费率金额** | ❌ 未公开 | 抓取件只给出「R$ 2.500」这一个门槛（低于此额不收处罚费） | 见下 |

处罚点机制的逐字原文（`research/raw/shopee_br_pontos_de_penalidade.txt`，
`source.url` = `https://seller.shopee.com.br/edu/article/16316/o-que-sao-pontos-de-penalidade`，
`article_id` = `16316`，`last_verified` = 2026-10-27）：

> `Você pode enfrentar restrições em sua conta e cobrança de taxa, dependendo da quantidade de Pontos de Penalidade acumulados. Consulte a tabela a seguir:`
>
> `Um ou dois Pontos de Penalidade servem como alerta sem perda de benefícios, para que você melhore os processos internos de atendimento, entrega, e qualidade, além de garantir a excelência da sua loja. Mais pontos podem restringir suas vantagens, como promoções e visibilidade.`
>
> `O valor será descontado do saldo da carteira duas semanas após o início da penalização, exceto nos casos em que eventuais apelações sejam aprovadas. Importante: essa cobrança não será aplicada para lojas que tiverem vendido menos de R$2.500 (em valor bruto da mercadoria) no mês anterior ao início da penalização.`

> 注意原文用的是 **`restrições em sua conta`**（不是本模块早期引文里的
> `restrições na sua conta`）。**逐字引用必须用原文的写法。**

### 5.2 违规码表里有什么、没有什么

`research/violation_codes.json`（106 条，`source_url` =
`https://seller.br.shopee.cn/edu/article/5139`）每条记录这些字段：

```json
{
  "code": 317,
  "description": "Anúncio proibido para armas de fogo, tasers, munições e coletes à prova de balas.",
  "severity_pt": "Extrema",
  "severity": "critical",
  "generates_penalty_point": true,
  "penalty_note": "Gera ponto de penalidade. Para mais informações, clique aqui.",
  "category": "prohibited_restricted_policy",
  "platform_code": "[317]"
}
```

**有**：`severity`（严重度）、`generates_penalty_point`（是否产生处罚点的布尔值）。
**没有**：处罚点的**分值**。

严重度分布（106 条实测）：

| `severity` | 条数 |
|---|---|
| `low` | 42 |
| `high` | 27 |
| `medium` | 24 |
| `critical` | 13 |

> `severity_pt` 是平台原文的葡语档位（`Baixa` / `Média` / `Alta` / `Extrema`），
> `severity` 是本项目归一化后的英文档位。
> 归一化映射写在本模块规则的 `severity` 字段里（如 `SBR-PI-001` = `critical`）。

### 5.3 怎么在结论里表达「会产生处罚点」

**用 `severity` 与码号表达，不要用数字。**

| 表达方式 | 允许 |
|---|---|
| 「`SBR-PI-001` 命中，平台码 `[317]`，严重度 `critical`」 | ✅ |
| 「原文写明『Gera ponto de penalidade』」 | ✅（引文逐字） |
| 「`SBR-PI-001` 命中，会扣 10 个处罚点」 | ❌ **禁止** —— 数值未公开 |
| 「`SBR-PI-002` 命中会扣 5 分」 | ❌ **禁止** |
| 「`SBR-LV-013` 命中说明尺寸超过 100cm」 | ❌ **禁止** —— 上限未公开 |

`SBR-LV-013` 的 `notes` 就是这条原则在规则层的落地：

> `2026-10-27: 明确语义边界 —— 平台未公开尺寸/重量上限数值（禁止引用未公开数值），本规则只标记「商品声明了完整三维尺寸」这一可判定事实，是否超限由人工复核确认；动作保持 flag_for_review，不阻断。`

### 5.4 已登记抓取失败的来源

`research/sources.json` 里有两条 `tier: law` 的来源**抓取失败**：

| slug | 状态 | 处置 |
|---|---|---|
| `br_anvisa_publicidade_medicamentos` | `failed_http_503` | **不得用于支撑任何规则** |
| `br_anvisa_medicamentos_prescricao` | `failed_http_503` | **不得用于支撑任何规则** |

`research/sources.json` 的 `capture_note` 原文：

> `抓取失败（HTTP 503）—— bvsms.saude.gov.br 当时不可达。本项目未使用该来源支撑任何规则；相关规则改用其它已核验来源。`

> 这两条是 Anvisa 的 RDC 96/2008（药品与健康品广告）与 RDC 44/2009（药房配药）。
> 因为抓不到，本项目**没有**任何规则引用它们。
> 药品类的规则全部改用已核验的 `research/raw/shopee_br_categorias_restrritas.txt`
> （平台自己的说明文章）。
>
> **推论**：RDC 96/2008 这类「Anvisa 详细广告规范」目前**不在**本项目的依据里。
> 若将来要引用，必须先重抓成功并让 `tools/verify_citations.py` 通过。

---

## 6. 生效性日期与自动降级 —— 现状说明

**现状：模块不实现基于日期的自动降级。**

`engine.py` 与 `rules.py` 里没有任何「比较 `last_verified` 与当前日期」的逻辑。
`status` 是**人工维护**的字段。

这带来两个必须说清楚的后果：

| 后果 | 说明 |
|---|---|
| `last_verified` 过期**不会**自动把规则降级 | 一条 `last_verified` 是 3 个月前的 `active` 规则，**仍然会照常判定**，包括照常产出 `block` |
| 防止误用的机制是**流程**而非代码 | 靠 `tools/verify_citations.py` 在 CI 里拦截 —— 页面一改，引文就核验不过，规则**必须**更新才能重新 `active` |

> 骨架文档里写的「`platform_official` 90 天 / `law` 180 天有效期」**没有在代码里实现**，
> 因此不作为生效规则写在此处。
> 若集成 Agent 认为需要自动降级，建议：
>
> - 在 `rules.py` 增加一个 `is_stale(rule, today)` 判定（读 `source.last_verified`），
>   并在 `_evaluate_rule()` 里把过期的 `active` 规则按 `stale` 处理（跳过判定 +
>   记 `known_gaps`）—— **但这会改变判定行为，属于契约层变更**，需要集成阶段统一决定；
> - 或者维持现状，把「定期重抓 + 重核」作为**流程**写进 `docs/SOP_COMPLIANCE_REVIEW.md`。
>
> 本模块**不自行实现**这一点（越界修改判定语义）。

---

## 7. 时效核验清单（人工执行）

每次复核规则库时逐条过：

- [ ] `env -u LD_LIBRARY_PATH python3 tools/verify_citations.py` → `57/57 excerpts verified verbatim, 0 failed`
- [ ] `env -u LD_LIBRARY_PATH python3 tools/check_sources.py` → 来源清单与抓取件一致（允许 2 条已登记的抓取失败）
- [ ] `env -u LD_LIBRARY_PATH python3 tools/check_rule_regex.py` → 全部规则的正则可编译，且无逻辑自指缺陷
- [ ] 每条 `active` 规则的 `source.url` 指向的页面，其「Última atualização」日期不晚于该规则的 `last_verified`
- [ ] 没有任何规则引用了**未公开数值**（处罚点分值、尺寸/重量上限、分档表）
- [ ] 没有任何规则引用了**抓取失败**的来源
- [ ] 语义有实质变化的规则：`version` 已 +1，`notes` 写明改动原因与日期，`status` 走过 `draft` → `active`
- [ ] 受影响规则的正例 + 反例用例已更新（`tests/shopee-br-listing-audit/fixtures/listing_audit_rule_cases.json`）
- [ ] `env -u LD_LIBRARY_PATH python3 tests/shopee-br-listing-audit/run_tests.py` → 全通过
- [ ] `env -u LD_LIBRARY_PATH bash scripts/check_all.sh` → `ALL CHECKS PASSED`

---

## 8. 政策变更 → 判定变化的映射表

| 政策变化 | 受影响的规则 | 必须做的改动 |
|---|---|---|
| **MIP 授权变化**（如 Anvisa 扩大授权范围） | `SBR-MED-002` | 重新评估 `require_evidence` 是否仍是正确的动作；检查 `pharmacy_license` 是否仍是决定性证据 |
| **药品禁售清单变化** | `SBR-MED-001` | 更新触发正则；更新 `source.excerpt`；`version + 1` |
| **新增违规码** | 对应类别的规则 | 更新 `research/violation_codes.json`；补规则或扩展现有规则 |
| **违规码严重度调整** | 对应规则 | 更新规则的 `severity`；**注意动作会随风险等级变化**（`block` 在 `critical` / `high` / `medium` 允许，在 `low` 不允许） |
| **受限类目授权流程变化** | `SBR-RI-*` | 更新 `evidence_required`；可能影响 `require_evidence` → `block` 的选择 |
| **类目树变化** | `SBR-LV-008` | 平台的类目树不在抓取件里，`SBR-LV-008` 判的是「类目字段为空」而非「类目选错」 —— 类目树变化**不影响**本规则 |
| **处罚点机制变化** | 全部 | **不改判定** —— 只影响 `provenance.notes` 里可引用的信息 |
