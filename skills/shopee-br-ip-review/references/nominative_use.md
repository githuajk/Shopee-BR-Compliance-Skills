| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-IP-002` |
| 所属模块 | `shopee-br-ip-review` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 指示性使用与品牌宣称的判定要素、对比表、正反例，以及代码里的实际豁免行为 |
| 相关文档 | `rules/02_ip_trademark_copyright.json`、`research/raw/br_lei_propriedade_industrial_9279.txt`、`skills/shopee-br-ip-review/src/sbr_ip_review/engine.py` |
| 未决事项 | `SBR-IP-006` 的品牌词表与 `SBR-IP-001` 不完全一致（`supreme` 只在前者）—— 见 §7 |

---

## 1. 法律依据：指示性使用（nominative use）

**Lei nº 9.279/1996 Art. 132, II**
来源 `research/raw/br_lei_propriedade_industrial_9279.txt`，
`source_url=https://www.planalto.gov.br/ccivil_03/leis/l9279.htm`，`last_verified=2026-10-27`。

> Art. 132. O titular da marca não poderá:
> - impedir que comerciantes ou distribuidores utilizem sinais distintivos que lhes são próprios, juntamente com a marca do produto, na sua promoção e comercialização;
> II - impedir que fabricantes de acessórios utilizem a marca para indicar a destinação do produto, desde que obedecidas as práticas leais de concorrência;
> IV - impedir a citação da marca em discurso, obra científica ou literária ou qualquer outra publicação, desde que sem conotação comercial e sem prejuízo para seu caráter distintivo.

**要点**：Art. 132, II 是**对商标权人的限制**，不是对使用者的授权。
它说的是「商标权人**不得**阻止配件制造商用该商标**指明产品用途**」。
因此「兼容某型号」这类描述**不构成商标侵权依据**。

**同一法条的上位款**：

> Art. 130. Ao titular da marca ou ao depositante é ainda assegurado o direito de:
> - ceder seu registro ou pedido de registro;
> II - licenciar seu uso;

以及 Art. 132, I（经销商标的独立使用）—— 两者合起来构成本模块判定表的语境基准。

## 2. 判定要素对比表

| 判定要素 | 指示性使用（不构成侵权依据） | 品牌宣称 / 混淆性使用（高风险） |
|---|---|---|
| **目的** | 指明**产品用途 / 适配机型 / 适用系列** | 借用品牌**吸引力**，暗示商品本身即该品牌 |
| **商品性质** | **配件**（非品牌商品本身） | 品牌商品本身，或仿牌 |
| **表述形式** | `compatível com` / `compatível para` / `para o modelo` / `do modelo` / `aplicável em` | `original` / `oficial` / `importado` / `réplica` / `1ª linha` / `certificado` |
| **品牌词位置** | 非主导，与适配信息绑定 | 主导，独立出现或置于标题首位 |
| **配套声明** | 有「非授权配件 / 产品无品牌」类声明更好 | 无，或反而声明「官方授权」 |
| **法律后果** | 不受 Art. 132 保护的是**商标权人**，使用者不侵权 | 可能落入 `[133]` `[601]`；严重时触及 Art. 194 / Art. 195 |

## 3. 代码里的实际判定机制

### 3.1 两条规则的触发条件

`rules/02_ip_trademark_copyright.json`：

| 规则 | 条件 | severity | 声明动作 | source tier |
|---|---|---|---|---|
| `SBR-IP-001` | 条件 1：`any_text` 命中品牌词表 | high | `escalate_legal` | `platform_official` |
| `SBR-IP-006` | 条件 1：`any_text` 命中兼容性措辞；**且** 条件 2：`any_text` 命中品牌词表 | info | `allow` | `law` |

`trigger_conditions` 之间是 **AND** 关系。所以 `SBR-IP-006` 命中意味着
「这段文本里既有兼容性措辞、又有品牌词」—— 这正是指示性使用的形态。

### 3.2 豁免的实现位置与范围

实现写在 `skills/shopee-br-ip-review/src/sbr_ip_review/engine.py`：

```
NOMINATIVE_USE_EXEMPTED = ("SBR-IP-001",)
```

引擎先跑完全部规则，再做豁免：若 `SBR-IP-006` 命中，
则把 `fired` 列表里**属于 `NOMINATIVE_USE_EXEMPTED` 的规则移除**，
并在 `reason` 里追加可审计的豁免说明：

> 指示性使用豁免（Lei 9.279/1996 Art. 132, II）：兼容性上下文成立，品牌宣称规则 SBR-IP-001 不构成侵权依据

### 3.3 **豁免的确切边界（必读）**

| 规则 | 被豁免？ | 理由 |
|---|---|---|
| `SBR-IP-001`（品牌宣称） | ✅ **是** | 这正是 `SBR-IP-006` 的反规则 |
| `SBR-IP-002`（假货宣称） | ❌ **否** | 假货风险不受 Art. 132 保护 |
| `SBR-IP-003`（外卖平台 logo 的包） | ❌ 否 | 与品牌宣称无关 |
| `SBR-IP-004`（Shopee logo/banner） | ❌ 否 | 与品牌宣称无关 |
| `SBR-IP-005`（图片第三方 logo） | ❌ 否 | 图片本身是独立信号 |
| `SBR-IP-007`（版权声明） | ❌ 否 | 类别不同 |
| `SBR-IP-008`（外观设计） | ❌ 否 | 类别不同 |
| `SBR-AU-001`（授权缺口） | ❌ 否 | 类别不同 |

> **`SBR-IP-006` 只豁免 `SBR-IP-001` 一条。**
> 「réplica compatível com X」既是指示性措辞、又是假货宣称 ——
> 引擎会同时命中 `SBR-IP-002` 与 `SBR-IP-006`，`SBR-IP-002` **不被豁免**，
> 最终 `action=escalate_legal` / `verdict=BLOCK` / `risk_level=critical`。
>
> `SBR-IP-006` 的 `notes` 也明写：「it is NOT a pass on its own,
> because the surrounding text may still contain a brand claim.」
> —— 引擎把豁免理解为「**品牌宣称这一条不成立**」，不是「整条商品无风险」。

### 3.4 豁免后仍然是 `signal` + 强制人工复核

豁免**不放松 H1**。`SBR-IP-006` 命中后的结果仍然：

- `confidence = "signal"`（`engine.py` 里写死，无分支）；
- `requires_human_review = true`（无分支）；
- `review_rationale` 非空（因为有命中规则）。

## 4. 正例（指示性使用）

### 4.1 完整可评估的兼容性描述

```
title       : Capa de Banco Automotiva Impermeável Compatível com Ford Focus 2015-2020
description : Capa para banco de carro, material impermeável. Compatível com o modelo
              Ford Focus 2015 a 2020. Não acompanha o veículo. Produto sem marca registrada.
brand       : Sem Marca
```

实测：`fired=['SBR-IP-006']`（`SBR-IP-001` 被豁免）、
`action=allow` / `verdict=PASS` / `risk_level=info` / `confidence=signal` /
`requires_human_review=true`。

`reason` 里含：

> 1 IP screening signal(s) matched (SBR-IP-006); action 'allow' at risk level 'info'; 指示性使用豁免（Lei 9.279/1996 Art. 132, II）：兼容性上下文成立，品牌宣称规则 SBR-IP-001 不构成侵权依据; IP findings are screening signals, not an infringement finding

### 4.2 兼容性描述 + 图片检出 logo

```
title   : Capa de Banco Compatível com Ford Focus
images  : [{ "ocr_text": "FORD", "detected_logos": ["Ford"] }]
```

实测：`fired=['SBR-IP-005', 'SBR-IP-006', 'SBR-IP-008']`、
`action=flag_for_review` / `verdict=REVIEW` / `risk_level=medium`。

> 兼容性语境**只**压掉品牌宣称那条。图片里的 logo 是**独立的**信号，
> 必须由人判断这个 logo 是「适配标识」还是「冒用标识」。

### 4.3 兼容性措辞 + `brand` 字段填了他人商标

```
title   : Capa de Banco Impermeável
brand   : Nike
description : Compatível com o modelo Ford Focus.
```

实测：`fired=['SBR-IP-006']`、`action=allow` / `verdict=PASS`。

> ⚠️ **这是当前实现的一个真实缺口**：`brand` 字段填了 `Nike` 却仍判 `PASS`，
> 因为 `SBR-IP-006` 命中后 `SBR-IP-001` 被无条件豁免，
> 引擎**不检查被豁免的那条规则到底命中了什么**。
> 人工复核必须补看 `brand` 字段 —— 见 §8「已知局限」。

## 5. 反例（品牌宣称 / 假货宣称）

### 5.1 品牌宣称

```
title   : Tênis Esportivo Nike Airborne Runner
brand   : Nike
description : Tênis esportivo com tecnologia de amortecimento avançada.
```

实测：`fired=['SBR-IP-001']`、`action=escalate_legal` / `verdict=BLOCK` /
`risk_level=high` / `confidence=signal` / `requires_human_review=true`。

`review_rationale`（实际输出，非连续片段，分两段）：

> IP-category findings are screening signals only; only a rights-holder complaint, a written authorisation, or a platform complaint notice can establish infringement;

> action 'escalate_legal' always requires human review

### 5.2 假货宣称（**不受 Art. 132 保护**）

```
title   : Réplica de Tênis Esportivo Premium
description : Réplica de tênis esportivo em couro sintético. Produto original com
              acabamento idêntico ao da marca. Cópia não autorizada.
```

实测：`fired=['SBR-IP-002']`、`action=escalate_legal` / `verdict=BLOCK` /
`risk_level=critical`。

平台依据（`research/raw/shopee_br_politica_produtos_proibidos.txt`，`article_id=3304`，
`last_verified=2026-10-27`）：

> Além disso, são proibidos produtos potencialmente infratores: produtos incluindo - mas não limitado a - réplicas, produtos falsificados, e cópias não-autorizadas de um produto ou item que pode violar determinados direitos autorais, marcas registradas ou outros direitos de propriedade intelectual de terceiros.

### 5.3 指示性措辞 + 假货宣称（混合，最危险的组合）

```
title   : Capa de Banco Compatível com Nike Focus
description : Réplica compatível com o modelo Nike Focus. Produto original.
```

实测：`fired=['SBR-IP-002', 'SBR-IP-006']`、`action=escalate_legal` /
`verdict=BLOCK` / `risk_level=critical`。

> `reason` 里**同时**出现豁免说明和 `SBR-IP-002` 命中 ——
> 这正是「豁免只针对品牌宣称」的实证。

## 6. 对比速查表

| 文本特征 | 命中 | 结论 | 依据 |
|---|---|---|---|
| `compatível com <Marca> <Modelo>` | `SBR-IP-006` | `allow` / `PASS` / info | Art. 132, II |
| `para o modelo <Marca>` | `SBR-IP-006` | `allow` / `PASS` / info | Art. 132, II |
| `do modelo <Marca>` | `SBR-IP-006` | `allow` / `PASS` / info | Art. 132, II |
| `aplicável em <Marca>` | `SBR-IP-006` | `allow` / `PASS` / info | Art. 132, II |
| `<Marca> <Modelo>`（无兼容性措辞） | `SBR-IP-001` | `escalate_legal` / `BLOCK` / high | `[133]` `[601]` |
| `original` + `<Marca>` + 兼容性措辞 | `SBR-IP-006`（`SBR-IP-001` 被豁免） | `allow` / `PASS` / info | **见 §8 局限** |
| `réplica` / `cópia não autorizada` | `SBR-IP-002` | `escalate_legal` / `BLOCK` / critical | `[601]` |
| `réplica` + 兼容性措辞 | `SBR-IP-002` + `SBR-IP-006` | `escalate_legal` / `BLOCK` / critical | 假货不受 Art. 132 保护 |

## 7. 兼容性措辞与品牌词表的实际取值

`SBR-IP-006` 条件 1 的正则（逐字取自 `rules/02_ip_trademark_copyright.json`）：

```
(?i)(compat[íi]vel\s+com|compat[íi]vel\s+para|para\s+(o\s+)?modelo|do\s+modelo|aplic[aá]vel\s+em)
```

条件 2 的品牌词表与 `SBR-IP-001` **相同**，但**少了 `supreme`**：

```
(?<![a-zA-Zà-ÿÀ-ß])(nike|adidas|puma|samsung|apple|xiaomi|sony|dyson|lululemon|rolex|ford|toyota|volkswagen|chevrolet|fiat|huawei|amazon)\b
```

**实测后果**：标题为 `Capa de Banco Compatível com Supreme Focus` 时，
`SBR-IP-006` **不命中**（`supreme` 不在它的词表里），
`SBR-IP-001` 命中 → `action=escalate_legal` / `verdict=BLOCK` / `risk_level=high`。

> 遍历 18 个品牌词 × 5 种兼容性措辞共 90 组实测：
> 85 组命中 `SBR-IP-006` 且 `SBR-IP-001` 被豁免；
> 5 组（全部是 `supreme`）只命中 `SBR-IP-001`。
>
> **这是已知的词表不一致，属规则库问题，不是文档问题** ——
> 修它要改 `rules/02_ip_trademark_copyright.json`（本模块拥有），
> 不在本次文档任务范围内。

## 8. 已知局限（复核时必须人工补看）

| # | 局限 | 复核动作 |
|---|---|---|
| 1 | `brand` 字段填他人商标 + 描述里有兼容性措辞 → 仍判 `PASS`（`SBR-IP-001` 被豁免，引擎不看被豁免规则命中的具体内容） | **必看 `brand` 字段**。配件可写 `brand=Sem Marca`，配件填他人品牌等于品牌宣称 |
| 2 | `SBR-IP-006` 命中不代表全文都干净 —— 同一段文本里可能还有别的品牌宣称 | 看 `rule_refs` 全部条目，逐条确认 |
| 3 | 词表只有 18 个品牌 | 词表外的品牌（`Bosch`、`Philco`、`Electrolux`、`Brastemp`、`Consul`…）**完全不触发** |
| 4 | 兼容性措辞只认上表 5 种写法 | `indicado para`、`serve para`、`destinado a` 等写法**不触发**豁免，会按品牌宣称判 |
| 5 | Art. 132, II 要求「遵守正当竞争惯例」 | 引擎**不判断**「必要且适度」——是否适度由人判断 |

> 限度 1 与 3 的共同后果：**`verdict=PASS` 不等于「商标维度已排查干净」**。
> 它只等于「本模块的规则没命中」。H1 的 `requires_human_review=true` 恒成立，
> 就是为了让这一步永远由人补上。

## 9. 判定流程（人工复核用）

```
检测到品牌词
  ↓
看上下文：是「兼容性/用途」还是「品质/来源」？
  ↓
兼容性措辞 + 品牌词 → 指示性使用
  → 看 rule_refs 是否只有 SBR-IP-006
  → 是 → 人工确认 brand 字段与图片 logo，再决定 PASS / REVISE
  ↓
品质/来源宣称 → 品牌宣称 / 假货宣称
  → SBR-IP-002 命中 → escalate_legal（Art. 132 不提供抗辩）
  → 仅 SBR-IP-001 命中 → escalate_legal
```

## 10. 不得使用的表述

| 禁止 | 正确 |
|---|---|
| 「已豁免，所以没问题」 | 「兼容性语境成立，品牌宣称这一条不构成侵权依据；仍需人工复核」 |
| 「这是指示性使用，所以合法」 | 「指示性使用不构成商标侵权依据；是否违反正当竞争惯例由人判断」 |
| 「命中 `SBR-IP-006` 就没有风险」 | 「豁免只覆盖 `SBR-IP-001`；`SBR-IP-002` 等规则不被豁免」 |
| 把 `signal` 说成 `confirmed` | 恒为 `signal` |

## 11. 交叉引用

| 主题 | 文档 |
|---|---|
| 四类的定义、法律依据、平台码 | `references/ip_categories.md` |
| 授权材料清单与 INPI 核验 | `references/authorization_checklist.md` |
| 品牌方撤诉解封流程 | `references/dissolution_flow.md` |
| 风险等级 × 动作查表 | `contracts/risk_action_matrix.json` |
