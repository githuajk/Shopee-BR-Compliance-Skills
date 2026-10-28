| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-IP-001` |
| 所属模块 | `shopee-br-ip-review` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 知识产权四类的区分、法律依据、平台违规码与对应规则 |
| 相关文档 | `rules/02_ip_trademark_copyright.json`、`contracts/risk_action_matrix.json`、`research/violation_codes.json` |
| 未决事项 | 专利类（`ip_patent`）当前无规则 —— 见 §5 |

---

## 1. 本模块覆盖的四类

`contracts/risk_action_matrix.json` 的硬约束 H1 把 IP 类定义为四个 `category`：
`ip_trademark`、`ip_copyright`、`ip_design`、`ip_patent`。模块代码里同一个集合写在
`skills/shopee-br-ip-review/src/sbr_ip_review/rules.py` 的 `IP_CATEGORIES`。

**四类都在 H1 的保护范围内**（恒为 `confidence="signal"` + `requires_human_review=true`），
**但只有三类有规则**。本模块拥有的规则文件 `rules/02_ip_trademark_copyright.json` 共 8 条，
分布如下：

| category | 规则 ID | 条数 |
|---|---|---|
| `ip_trademark` | `SBR-IP-001` `SBR-IP-002` `SBR-IP-003` `SBR-IP-004` `SBR-IP-005` `SBR-IP-006` | 6 |
| `ip_copyright` | `SBR-IP-007` | 1 |
| `ip_design` | `SBR-IP-008` | 1 |
| `ip_patent` | —— | **0** |

> 另有 `SBR-AU-001`（授权缺口）从 `rules/04_cases_relist_authorization.json` **只读引用**，
> `category="authorization"`，不属于四类 IP，但参与同一次判定。

## 2. 结论的强制语义（硬约束 H1）

| 约束 | 实现位置 | 效果 |
|---|---|---|
| `confidence` 恒为 `signal` | `engine.py` 的 `confidence = "signal"` | 永不变为 `likely` / `confirmed` |
| `requires_human_review` 恒为 `true` | `engine.py` 的 `requires_human_review = True` | 无条件 |
| `reason` 必含免责句 | `_build_reason()` 追加 `IP findings are screening signals, not an infringement finding` | 每条结果都带这句 |

理由：把「疑似侵权」直接认定为「侵权」既缺法律依据，也可能造成错误下架与商誉损害。
**仅权利人投诉、书面授权或平台投诉通知**三者之一可确立侵权 —— 这句话同时写进
`ModuleHandoff.assumptions`（由 `engine.py` 的 `_build_handoff()` 生成）。

`verdict` 只能取 `PASS` / `REVISE` / `REVIEW` / `BLOCK` 四值，由 `contracts/risk_action_matrix.json`
的 `actions[].verdict` 查表得到；`confidence` 只能取 `signal` / `likely` / `confirmed`。
本模块**只产出 `signal`**。

## 3. 商标 `ip_trademark`（6 条规则）

### 3.1 规则与平台码

| 规则 ID | 触发 | severity | 声明动作 | 平台码 | 需要的证据 |
|---|---|---|---|---|---|
| `SBR-IP-001` | `any_text` 命中品牌词表 | high | `escalate_legal` | `[133]` `[601]` | `brand_authorization_letter` `trademark_registration` `supplier_invoice` `product_photographs` |
| `SBR-IP-002` | `any_text` 命中仿牌词 | critical | `escalate_legal` | `[601]` | `brand_authorization_letter` `supplier_invoice` |
| `SBR-IP-003` | 包类词与 logo/送餐平台线索同现 | medium | `flag_for_review` | `[349]` | `product_photographs` |
| `SBR-IP-004` | `image_text` 含 `shopee` / `shopee.br` / `loja oficial shopee` | medium | `flag_for_review` | `[608]` | `image_review` |
| `SBR-IP-005` | `image` 的 `detected_logos` 非空 | medium | `flag_for_review` | `[205]` `[601]` `[133]` | `image_review` `brand_authorization_letter` |
| `SBR-IP-006` | 兼容性上下文 **且** 出现品牌词 | info | `allow` | —— | —— |

### 3.2 法律依据

**Lei nº 9.279/1996（Lei da Propriedade Industrial）**
来源 `research/raw/br_lei_propriedade_industrial_9279.txt`，
`source_url=https://www.planalto.gov.br/ccivil_03/leis/l9279.htm`，`last_verified=2026-10-27`。

> Art. 132. O titular da marca não poderá:
> - impedir que comerciantes ou distribuidores utilizem sinais distintivos que lhes são próprios, juntamente com a marca do produto, na sua promoção e comercialização;
> II - impedir que fabricantes de acessórios utilizem a marca para indicar a destinação do produto, desde que obedecidas as práticas leais de concorrência;

> Art. 130. Ao titular da marca ou ao depositante é ainda assegurado o direito de:
> - ceder seu registro ou pedido de registro;
> II - licenciar seu uso;

**侵权后果**（同一抓取件）：

> Art. 194. Usar marca, nome comercial, título de estabelecimento, insígnia, expressão ou sinal de propaganda ou qualquer outra forma que indique procedência que não a verdadeira, ou vender ou expor à venda produto com esses sinais.

> Art. 195. Comete crime de concorrência desleal quem:
> IV - usa expressão ou sinal de propaganda alheios, ou os imita, de modo a criar confusão entre os produtos ou estabelecimentos;

**商标权期限**（同一抓取件）：

> Art. 133. O registro da marca vigorará pelo prazo de 10 (dez) anos, contados da data da concessão do registro, prorrogável por períodos iguais e sucessivos.

### 3.3 平台依据

来源 `research/raw/shopee_br_banimento_suspensao_anuncios.txt`，
`source_url=https://seller.br.shopee.cn/edu/article/5139`，`article_id=5139`，`last_verified=2026-10-27`。

> [133] Anúncio removido por violação de direitos de marca registrada Severidade: Baixa Não gera ponto de penalidade.

> [205] Anúncio removido por suspeita de inautenticidade Severidade: Média Gera ponto de penalidade.

> [349] Proibida a venda de mochilas/bags com logo de aplicativos de entrega Severidade: Baixa Não gera ponto de penalidade.

> [601] Anúncio removido por violação de contrafação e/ou marca registrada (Trademark/Counterfeit) Severidade: Alta Gera ponto de penalidade.

> [608] Anúncio removido por uso de logotipo ou banner da Shopee sem autorização Severidade: Baixa Não gera ponto de penalidade,

### 3.4 典型场景

| 场景 | 命中 | 典型结论 |
|---|---|---|
| 标题/详情直接写他人品牌（`brand` 字段也是他人商标） | `SBR-IP-001` | `escalate_legal` / `BLOCK` / high |
| 详情出现 `réplica` `cópia não autorizada` `falso` `look alike` `inspired by` | `SBR-IP-002` | `escalate_legal` / `BLOCK` / critical |
| 「mochila / bolsa de mão / bag」与「logo / iFood / Rappi / 99Food / delivery」同现 | `SBR-IP-003` | `flag_for_review` / `REVIEW` / medium |
| 图片 OCR 出现 `shopee` / `shopee.br` / `loja oficial shopee` | `SBR-IP-004` | `flag_for_review` / `REVIEW` / medium |
| 图片 `detected_logos` 非空（如 `["Adidas"]`） | `SBR-IP-005` | `flag_for_review` / `REVIEW` / medium |
| 兼容性描述且品牌词在表内（如 `Compatível com Ford Focus`） | `SBR-IP-006` | 品牌宣称被豁免 → 见 `references/nominative_use.md` |

> **品牌词表是筛查触发器，不是判定。** `SBR-IP-001` 的 `notes` 写明：
> 「The keyword list is a SCREENING trigger, not a determination.」

## 4. 版权 `ip_copyright`（1 条规则）

### 4.1 规则

| 规则 ID | 触发 | severity | 声明动作 | 平台码 | 需要的证据 |
|---|---|---|---|---|---|
| `SBR-IP-007` | `image_text` 命中 `marca registrada` / `copyright` / `todos os direitos reservados` / `© <年份>` | high | `escalate_legal` | `[602]` | `licence_document` `image_review` |

### 4.2 法律依据

**Lei nº 9.610/1998（Lei de Direitos Autorais）**
来源 `research/raw/br_lei_direitos_autorais_9610.txt`，
`source_url=https://www.planalto.gov.br/ccivil_03/leis/l9610.htm`，`last_verified=2026-10-27`。

> Art. 22. Pertencem ao autor os direitos morais e patrimoniais sobre a obra que criou.

> Art. 29. Depende de autorização prévia e expressa do autor a utilização da obra, por quaisquer modalidades, tais como:

**授权书的形式要求**（同一抓取件）：

> II - somente se admitirá transmissão total e definitiva dos direitos mediante estipulação contratual escrita;

### 4.3 平台依据

来源 `research/raw/shopee_br_banimento_suspensao_anuncios.txt`，`article_id=5139`。

> [602] Anúncio removido por violação de direito autoral (Copyright) Severidade: Alta Gera ponto de penalidade.

### 4.4 典型场景

| 场景 | 命中 | 典型结论 |
|---|---|---|
| 图片 OCR 出现 `© 2024 todos os direitos reservados` | `SBR-IP-007` | `escalate_legal` / `BLOCK` / high |
| 图片带他人摄影作品但**无**版权声明文字 | **不命中** | 由 `SBR-IP-005`（若检出 logo）或人工复核覆盖 |

> **检测边界**：本模块只做**文字层**的版权标识检测（`image_text` 正则），
> **不做图像相似度比对**。没有版权声明文字 ≠ 没有侵权 ——
> 这是筛查面的局限，不是「通过」的依据。

## 5. 外观设计 `ip_design`（1 条规则）

### 5.1 规则

| 规则 ID | 触发 | severity | 声明动作 | 平台码 | 需要的证据 |
|---|---|---|---|---|---|
| `SBR-IP-008` | `image` 的 `detected_logos` 非空 | medium | `flag_for_review` | `[603]` | `design_registration` `image_review` `supplier_invoice` |

### 5.2 法律依据

**Lei nº 9.279/1996 Art. 2º, II**
来源 `research/raw/br_lei_propriedade_industrial_9279.txt`，`last_verified=2026-10-27`。

> Art. 2º A proteção dos direitos relativos à propriedade industrial, considerado o seu interesse social e o desenvolvimento tecnológico e econômico do País, efetua-se mediante:
> II - concessão de registro de desenho industrial;

### 5.3 平台依据

来源 `research/raw/shopee_br_banimento_suspensao_anuncios.txt`，`article_id=5139`。

> [603] Anúncio removido por violação de desenho industrial (Industrial Design) Severidade: Alta Gera ponto de penalidade.

### 5.4 典型场景与已知局限

| 场景 | 命中 | 典型结论 |
|---|---|---|
| 图片 `detected_logos` 含他人标识（夹具 `IP-04`：背包 + `["Adidas"]`） | `SBR-IP-008` + `SBR-IP-005` | `flag_for_review` / `REVIEW` / medium |

> **已知局限（务必知悉）**：`SBR-IP-008` 的触发条件与 `SBR-IP-005` **完全相同**
> （都是 `image` + `has_nonempty` `detected_logos`）。它**没有**做外观设计的
> 相似度比对，只是复用图片 logo 信号并挂上 `[603]` 的法律依据。
> 因此 `SBR-IP-008` 与 `SBR-IP-005` **必然同时命中或同时不命中** ——
> 实测「有 logo」命中两条，「无 logo」两条都不命中。
> 把它当成「外观设计已排查」的证据是不成立的。

## 6. 专利 `ip_patent` —— **当前无规则**

### 6.1 事实陈述

- `rules/02_ip_trademark_copyright.json` 里**没有** `category="ip_patent"` 的规则。
- `skills/shopee-br-ip-review/src/sbr_ip_review/rules.py` 的 `IP_CATEGORIES` **包含**
  `ip_patent` —— 即专利类**在 H1 的适用范围内**（一旦有规则，结论同样恒为 `signal`）。
- 但**没有任何规则可评估这个维度**，所以引擎既不会命中它，
  **也不会把它记入 `unevaluated[]`** —— 因为 `unevaluated[]` 只记录
  「有规则但缺输入」的情况（硬约束 H3）。

实测：给一个标题为 `Dispositivo com patente`、其它输入齐备的商品跑一遍，
`fired=[]`、`unevaluated=[]`、`action=allow` / `verdict=PASS`。
**这个 `PASS` 不代表专利维度已排查** —— 它代表**该维度根本没有被检查**。

### 6.2 法律与平台依据（存在，但无规则支撑）

**Lei nº 9.279/1996 Art. 183**
来源 `research/raw/br_lei_propriedade_industrial_9279.txt`，`last_verified=2026-10-27`。

> Art. 183. Comete crime contra patente de invenção ou de modelo de utilidade quem:
> - fabrica produto que seja objeto de patente de invenção ou de modelo de utilidade, sem autorização do titular; ou

**平台码 `[604]`**
来源 `research/raw/shopee_br_banimento_suspensao_anuncios.txt`，`article_id=5139`。

> [604] Anúncio removido por violação de patente (Patent) Severidade: Alta Gera ponto de penalidade.

### 6.3 平台政策里专利是被明文禁止的一类

来源 `research/raw/shopee_br_politica_produtos_proibidos.txt`，
`source_url=https://seller.shopee.com.br/edu/article/3304/politica-de-produtos-proibidos-e-restritos`，
`article_id=3304`，`last_verified=2026-10-27`。

> São proibidos anúncios que violem as leis de direito autoral, patentes, marcas, modelos de utilidade, desenhos industriais, indicações geográficas, denominações de origem, selos de certificações e de agências regulatórias, entre outros.

### 6.4 结论

**专利维度目前是盲区。** 平台有 `[604]` 码、法律有 Art. 183，但：

1. 本模块**不产出任何专利维度的信号**；
2. 专利判定需要**权利要求比对**，本模块**没有**这个能力，
   关键词或 logo 匹配对专利毫无意义；
3. 因此**不能**在 `unevaluated[]` 里给它编一条「缺输入」的记录 ——
   那会把「没检查」伪装成「检查不了」。

> **待裁定**：是否新增 `ip_patent` 规则，取决于是否引入专利权利要求比对能力。
> 在此之前，**人工复核专利高风险类目时必须单独确认专利维度未被覆盖**。

## 7. 四类与平台违规码总表

`research/violation_codes.json` 的 106 条码里，`category` 以 `ip_` 开头的共 10 条：

| 平台码 | category | severity | 扣分 | 原文 |
|---|---|---|---|---|
| `[133]` | `ip_trademark` | low | 否 | Anúncio removido por violação de direitos de marca registrada |
| `[205]` | `ip_trademark` | medium | 是 | Anúncio removido por suspeita de inautenticidade |
| `[349]` | `ip_trademark` | low | 否 | Proibida a venda de mochilas/bags com logo de aplicativos de entrega |
| `[515]` | `ip_trademark` | low | 否 | Anúncio removido por uso indevido de logo do Governo Federal |
| `[601]` | `ip_trademark` | high | 是 | Anúncio removido por violação de contrafação e/ou marca registrada (Trademark/Counterfeit) |
| `[602]` | `ip_copyright` | high | 是 | Anúncio removido por violação de direito autoral (Copyright) |
| `[603]` | `ip_design` | high | 是 | Anúncio removido por violação de desenho industrial (Industrial Design) |
| `[604]` | `ip_trademark` | high | 是 | Anúncio removido por violação de patente (Patent) |
| `[608]` | `ip_trademark` | low | 否 | Anúncio removido por uso de logotipo ou banner da Shopee sem autorização |

> `[515]` 与 `[604]` **当前没有规则对应**。
> `[604]` 属专利（见 §6）；`[515]`（联邦政府 logo）不在本模块范围内。
> 分类字段 `ip_trademark` 覆盖了 `[604]` 是 `research/violation_codes.json`
> 的既有分类，**不表示**本模块有专利规则。

## 8. 平台对四类的总口径

来源 `research/raw/shopee_br_politica_produtos_proibidos.txt`，`article_id=3304`，`last_verified=2026-10-27`。

> São proibidos anúncios que violem as leis de direito autoral, patentes, marcas, modelos de utilidade, desenhos industriais, indicações geográficas, denominações de origem, selos de certificações e de agências regulatórias, entre outros.

> Além disso, são proibidos produtos potencialmente infratores: produtos incluindo - mas não limitado a - réplicas, produtos falsificados, e cópias não-autorizadas de um produto ou item que pode violar determinados direitos autorais, marcas registradas ou outros direitos de propriedade intelectual de terceiros.

平台把**知识产权**列为一个整体违规类别，处置包含下架与账号层面的措施；
具体落到哪个**违规码**取决于被认定的权利类型（商标 `[133]`/`[601]`、
版权 `[602]`、外观设计 `[603]`、专利 `[604]`）。

## 9. 不得使用的表述

| 禁止 | 正确 |
|---|---|
| 「这是假货」「这是侵权」 | 「命中注册商标词，判定为疑似侵权风险信号」 |
| 「品牌方已投诉」 | 「若权利人发起投诉则属 `[601]` 情形」 |
| 「专利已排查」 | 「专利维度当前无规则，未评估」 |
| 把 `signal` 说成 `confirmed` | 恒为 `signal` |

## 10. 交叉引用

| 主题 | 文档 |
|---|---|
| 指示性使用 vs 品牌宣称的判定表 | `references/nominative_use.md` |
| 授权材料清单与 INPI 核验 | `references/authorization_checklist.md` |
| 品牌方撤诉解封流程 | `references/dissolution_flow.md` |
| 风险等级 × 动作查表 | `contracts/risk_action_matrix.json` |
| 平台违规码全表 | `research/violation_codes.json` |
