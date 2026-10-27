# 判定语义规范

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-LA-001` |
| 所属模块 | `shopee-br-listing-audit` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 本模块 `PI` / `RI` / `MED` / `LV` 四类规则的审核语义与判定边界 |
| 相关文档 | `references/false_positive_control.md`、`references/evidence_checklist.md`、`references/policy_currency.md`、`references/lexicon_scanning.md`、`contracts/risk_action_matrix.json`、`PROJECT_RULES.md` §7 |
| 未决事项 | 无 |

---

## 1. 判定分三层

本模块的结论由三层协作产生，各层职责不重叠。**任何一层都不能替代另一层。**

| 层 | 输入 | 产出 | 权威依据 | 实现 |
|---|---|---|---|---|
| 规则层 | 商品 + 规则 | 命中 / 未命中 / 未评估 | `rules/**` + `data/schema/rule.schema.json` | `skills/shopee-br-listing-audit/src/sbr_listing_audit/conditions.py` |
| 矩阵层 | 命中规则的严重度 + 声明动作 | `risk_level` / `action` / `verdict` | `contracts/risk_action_matrix.json` | `skills/shopee-br-listing-audit/src/sbr_listing_audit/matrix.py` |
| 词库层 | 商品文案 | 筛查信号（**不产生结论**） | `lexicon/**` + `contracts/lexicon_rule_map.json` | `skills/shopee-br-listing-audit/src/sbr_listing_audit/lexicon.py` |

**关键词命中 ≠ 违规。** 词库命中只作为佐证写入 `evidence_refs`（`EV-LEX-*`）与
`provenance.notes`；是否违规由规则层判定，是否阻断由矩阵层决定。

规则层的三态由 `conditions.py` 的 `MATCH` / `NO_MATCH` / `UNEVALUATED` 定义：

| 规则级状态 | 含义 | 契约层表现 |
|---|---|---|
| 命中（`MATCH`） | 规则的 `trigger_conditions` 全部成立 | 产生 `rule_refs[]` 条目，参与动作聚合 |
| 不成立（`NO_MATCH`） | 条件已评估但不成立 | **不产生任何条目**（不是「通过」的同义词，只是本规则没命中） |
| 未评估（`UNEVALUATED`） | 依赖字段缺失或为空，**无法评估** | 写入 `unevaluated[]` + `errors[]`（`stage: "rule_evaluation"`, `severity: "warning"`），**不得**计入通过 |

> **最容易出错的地方：未评估 ≠ 通过。**
> 当输入缺 `description` 时，依赖 `description` 的 `SBR-LV-006` 不会被评估。
> 该商品**不能**因此被判为合规 —— 硬约束 **H3** 要求它进 `unevaluated[]`，
> 且结果 `confidence` 降为 `signal`、`requires_human_review` 为 `true`。

### 1.1 契约取值（冻结，不可自造）

`AuditResult.verdict` 只有 4 个取值：`PASS` / `REVISE` / `REVIEW` / `BLOCK`。
`AuditResult.confidence` 只有 3 个取值：`signal` / `likely` / `confirmed`。

`verdict` 由 `action` 经 `contracts/risk_action_matrix.json` 的 `actions` 段映射
（见 `matrix.py` 的 `verdict_for()`），**不是**由本模块直接决定：

| `action` | `verdict` |
|---|---|
| `allow` | `PASS` |
| `flag_for_review` | `REVIEW` |
| `require_evidence` | `REVIEW` |
| `revise` | `REVISE` |
| `block` | `BLOCK` |
| `freeze_relist` | `BLOCK` |
| `escalate_legal` | `BLOCK` |

`pass` / `flag` / `not_evaluated` / `not_applicable` / `pending_verification` **不是**
契约取值，不能写进 `AuditResult.verdict`。同理 `low` / `medium` / `high` 不是
`confidence` 的合法取值（那三个是 `risk_level` 的取值）。

---

## 2. PI（禁售）—— `SBR-PI-001` … `SBR-PI-009`

### 2.1 判定含义

禁售类 = **平台明文禁止刊登的商品本身**。命中即意味着该商品**不得上架**，
`severity` 全部为 `critical`，`decision` 全部为 `block`。

判定路径：`any_text` 上的单个正则条件（`regex` 算子），命中即触发。

| 规则 | 平台码 | 覆盖对象 | 声明动作 |
|---|---|---|---|
| `SBR-PI-001` | `[317]` | 枪械、电击枪、弹药、防弹衣 | `block` |
| `SBR-PI-002` | `[311]` | 烟草、香烟、雪茄、烟斗、电子烟及配件 | `block` |
| `SBR-PI-003` | `[313]` | 管制药品、处方药、红/黑标签药、堕胎药、注射剂、性兴奋剂、抗抑郁药 | `block` |
| `SBR-PI-004` | `[332]` | 工业原料化学品、爆炸物、高易燃品（汽油、柴油、乙醇、硝基苯、TNT 等） | `block` |
| `SBR-PI-005` | `[341]` | 假币、刷卡克隆器、数据与伪造证件、人体器官 | `block` |
| `SBR-PI-006` | `[338]` | 赌博游戏、在线彩票、抽奖箱、数字商品与服务 | `block` |
| `SBR-PI-007` | `[516]` | 政府/军方标识、徽章、制服等官方用品 | `block` |
| `SBR-PI-008` | `[339]` | 活体动物、野生动物制品、濒危物种及动植物衍生品 | `block` |
| `SBR-PI-009` | `[320]` | 色情内容 | `block` |

引文（逐字，来自 `research/raw/shopee_br_banimento_suspensao_anuncios.txt`）：

> `[317] Anúncio proibido para armas de fogo, tasers, munições e coletes à prova de balas. Severidade: Extrema. Gera ponto de penalidade.`
>
> `[311] Anúncio proibido para tabaco, cigarros, charutos, cachimbos e vapes. Severidade: Extrema. Gera ponto de penalidade.`
>
> `[313] Anúncio proibido para medicamentos com tarja preta, abortivos, injetáveis, estimulantes sexuais e antidepressivos. Severidade: Extrema. Gera ponto de penalidade.`
>
> `[332] Anúncio proibido de produtos químicos brutos e industriais, explosivos e/ou produtos altamente inflamáveis como gasolina, diesel, etanol, nitrobenzeno, TNT, nitrato de potássio e outros. Severidade: Extrema. Gera ponto de penalidade.`
>
> `[341] Anúncio proibido de venda de dados, jammers e documentos falsificados. Severidade: Extrema. Gera ponto de penalidade.`
>
> `[338] Anúncio proibido de venda de jogos de azar e loteria online. Severidade: Extrema. Gera ponto de penalidade.`
>
> `[516] Anúncio proibido de itens de uso oficial governamental, como insígnias, brasões, uniformes e itens correlatos. Severidade: Extrema. Gera ponto de penalidade.`
>
> `[339] Anúncio proibido para animais vivos, partes de animais selvagens e/ou espécies ameaçadas de extinção. Severidade: Extrema. Gera ponto de penalidade.`
>
> `[320] Anúncio de natureza pornográfica proibida por lei. Severidade: Extrema. Gera ponto de penalidade.`

**来源**（`source.tier = platform_official`）：

| 规则 | `source.url` | `article_id` | `last_verified` |
|---|---|---|---|
| `SBR-PI-001` … `SBR-PI-009` | `https://seller.br.shopee.cn/edu/article/5139` | `5139` | 2026-10-27 |

### 2.2 判定边界

| 边界 | 说明 |
|---|---|
| **平台码 ≠ 处罚点分值** | 码 `[317]` 的原文只说「Gera ponto de penalidade」（会产生处罚点），**没有给出分值**。平台未公开分值，本模块不推断、不写入规则。见 `references/policy_currency.md` §5 |
| **词命中 ≠ 商品本体** | 规则在文案上判定。文案写「munição de plástico」的训练用品会命中 `SBR-PI-001`。因此 `SBR-PI-001` 的 `evidence_required` 含 `product_photographs`，且 `human_review_required: true` —— **阻断前必须由人确认实物** |
| **PI 规则不处理授权** | 禁售就是禁售，不存在「补材料即可上架」的路径。`SBR-PI-001` 等的 `decision` 是 `block` 而不是 `require_evidence` |
| **PI 与 IP 不重叠** | 「假冒」类判定归 `shopee-br-ip-review`（`SBR-IP-*`）。本模块的 `SBR-PI-005` 只管「假币 / 伪造证件 / 克隆器」，不管「仿牌服装」 |

### 2.3 典型正例 / 反例

| 规则 | 正例（应命中） | 反例（不应命中） |
|---|---|---|
| `SBR-PI-001` | `Pistola de Treinamento Airsoft com Munição de Plástico` | `Kit 6 Facas de Cozinha em Aço Inox`（工具类） |
| `SBR-PI-002` | `Vape Descartável 4000 Puffs com Atomizador` | `Carregador USB-C 30W para Celular` |
| `SBR-PI-003` | `Antidepressivo com Tarja Vermelha 30 Comprimidos` | `Vitamina C 1000mg 60 Comprimidos` |
| `SBR-PI-004` | `Solvente Acetona 5 Litros para Limpeza Industrial` | `Detergente Neutro para Limpeza de Pisos 5L` |
| `SBR-PI-005` | `Máquina de Clonador de Cartão e Cédulas para Treinamento` | `Kit 10 Peneiras em Aço Inox para Cozinha` |
| `SBR-PI-006` | `Caixa Misteriosa com Surpresa Colecionável` | `Jogo de Tabuleiro Familiar 100 Peças` |
| `SBR-PI-007` | `Uniforme Militar com Insígnia Governamental Costurada` | `Aventom de Trabalho em Canvas com Bolso` |
| `SBR-PI-008` | `Coleção de Fauna e Flora e Derivados — Âncoras Naturais` | `Arranjo de Flores Artificiais em vaso de Cerâmica` |
| `SBR-PI-009` | `DVD de Conteúdo Adulto com Cenas Explícitas` | `DVD de Filme de Comédia Familiar` |

> 正例 / 反例全文见 `tests/shopee-br-listing-audit/fixtures/listing_audit_rule_cases.json`
> （71 个用例：33 正例 + 33 反例 + 3 缺失 + 2 边界），每条 `active` 规则都覆盖。

---

## 3. RI（受限）—— `SBR-RI-001` … `SBR-RI-008`

### 3.1 判定含义

受限类 = **商品本身可以卖，但需要资质 / 授权 / 注册才能卖**。
命中的语义是「**证据不足，不得上架**」，不是「商品违规」。

| 规则 | 平台码 | 覆盖对象 | `severity` | 声明动作 |
|---|---|---|---|---|
| `SBR-RI-001` | `[325]` | 酒精饮料 | `high` | `require_evidence` |
| `SBR-RI-002` | `[312]` | 健康类目：保健品、医疗用品、监测设备、矫形器具 | `high` | `require_evidence` |
| `SBR-RI-003` | `[333]` | 电池与充电宝 | `high` | `require_evidence` |
| `SBR-RI-004` | `[132]` | 汽车零部件与车用油 | `high` | `require_evidence` |
| `SBR-RI-005` | `[331]` | 生鲜与冷冻食品 | `medium` | `require_evidence` |
| `SBR-RI-006` | `[334]` | 宠物药品（兽药） | `medium` | `require_evidence` |
| `SBR-RI-007` | `[315]` | 气枪 / 彩弹 / 气压武器与战术装备 | `high` | `require_evidence` |
| `SBR-RI-008` | —— | 未巴氏杀菌 / 散装 / 无工业封装的乳制品 | `high` | `block` |

> **`SBR-RI-008` 是例外**：它的 `category` 是 `prohibited_item`、`decision` 是 `block`，
> 尽管 `rule_id` 前缀是 `RI`。这是因为该政策原文写的是「Proibidos (para todos os
> vendedores)」—— 对所有卖家禁售，与「需授权才能卖」不同。
> **判定边界看 `category` 与 `decision`，不看 `rule_id` 前缀。**

### 3.2 判定边界

| 边界 | 说明 |
|---|---|
| **缺材料 ≠ 违规** | 受限类命中后的动作是 `require_evidence`（`verdict: REVIEW`），语义是「补齐材料前不得上架」，不是「商品有问题」 |
| **同一批里 RI 与 PI 的区分** | PI = 商品不得存在；RI = 商品存在但需授权。`SBR-RI-007`（气枪，`require_evidence`）与 `SBR-PI-001`（火器，`block`）的差别正是这条 |
| **保健品本身是允许的** | `SBR-RI-002` 的 `description` 明确写了平台允许保健品（维生素、草药、天然产品）本身，平台对保健品执行的是**宣称的真实性**（见 `SBR-MED-003`）与**监管注册**（监测仪、检测试剂、矫形支撑） |
| **RI 命中不等于必须有证** | 规则只判定「这件商品落在受限类目里」，证照是否存在由人工凭 `evidence_required` 清单核对 |

### 3.3 典型正例 / 反例

| 规则 | 正例（应命中） | 反例（不应命中） |
|---|---|---|
| `SBR-RI-001` | `Kit Gin's Tonic e Whisky 12 Anos 1 Garrafa` | `Refrigerante de Cola Zero 2L` |
| `SBR-RI-002` | `Multivitamínicos 60 Comprimidos e Oxímetro de Pulso` | `Suplemento Alimentar de Proteína com 24 Porções Sabor Chocolate` |
| `SBR-RI-003` | `Power Bank 20000mAh com Bateria de Lítio 18650` | `Furadeira de Impacto sem Fio 18V com Maleta e Bateria` |
| `SBR-RI-004` | `Óleo Automotivo Sintético 5W30 com Homologação do Produto` | `Capa de Banco Automotiva Impermeável` |
| `SBR-RI-005` | `Caixa de Frutas Frescas e Legumes Frescos Orgânicos` | `Pacote de Arroz Integral 1kg` |
| `SBR-RI-006` | `Antiparasitário para Cães de 10kg a 40kg 3 Comprimidos` | `Comedouro Duplo para Cães em Aço Inox` |
| `SBR-RI-007` | `Kit Airsoft com Arma de Pressão CO2 e Equipamentos Táticos` | `Maleta de Ferramentas 82 Peças` |
| `SBR-RI-008` | `Queijo Artesanal de Leite Cru e Manteiga Artesanal 500g` | `Queijo Muçarela Fatiado Industrial 150g` |

> `SBR-RI-003` 的边界在 v2 被收窄：电池词必须带类型限定词（`de lítio` / `18650` /
> `9v` / `ni-mh` / `alcalina` / `recarregável`），或命中 `power bank` /
> `banco de energia portátil`。单独的 `bateria` 不再命中 —— 否则电钻等普通工具
> 会被误判为电池类。

### 3.4 受限类目的证据清单

见 `references/evidence_checklist.md` §3。摘要：

| 规则 | 需要的材料（`evidence_required`） |
|---|---|
| `SBR-RI-001` | `supplier_invoice`、`distribution_authorization`、`product_photographs` |
| `SBR-RI-002` | `anvisa_registration`、`supplier_invoice` |
| `SBR-RI-003` | `product_photographs`、`supplier_invoice` |
| `SBR-RI-004` | `homologation_certificate`、`supplier_invoice` |
| `SBR-RI-005` | `sanitary_registration`、`product_photographs` |
| `SBR-RI-006` | `mapa_registration`、`supplier_invoice` |
| `SBR-RI-007` | `product_photographs`、`supplier_invoice` |
| `SBR-RI-008` | `sanitary_registration`、`product_photographs` |

---

## 4. MED（药品与健康）—— `SBR-MED-001` … `SBR-MED-003`

### 4.1 判定含义

MED 类专门处理**药品与健康品**，判定的核心问题只有一个：
**这件商品是「绝对不能卖」，还是「卖它的人有没有资格卖」，还是「宣称是否失实」。**

| 规则 | `category` | `severity` | 声明动作 | 判定的问题 |
|---|---|---|---|---|
| `SBR-MED-001` | `prohibited_item` | `critical` | `block` | 是不是**绝对禁止**的那几类药？ |
| `SBR-MED-002` | `restricted_item` | `high` | `require_evidence` | 卖方**是不是持牌药房 / 药店**？ |
| `SBR-MED-003` | `consumer_protection` | `high` | `flag_for_review` | 保健品的**宣称是不是失实**？ |

三条规则的划分对应三个互斥的事实维度，**不重叠**：

| 情形 | 命中规则 | 动作 |
|---|---|---|
| 绝对禁止的药（人用药、兽药、堕胎药、CDS/MMS、注射剂、毒品） | `SBR-MED-001` | `block` |
| 非处方药（MIP）/ 管制药，但卖方资质不明 | `SBR-MED-002` | `require_evidence` |
| 保健品宣称失实 | `SBR-MED-003` | `flag_for_review` |

引文（逐字，来自 `research/raw/shopee_br_categorias_restrritas.txt`）：

> `Medicamentos de uso humano em geral; Medicamentos de uso veterinário; Medicamentos, produtos ou serviços que estejam relacionados com a realização de abortos; Clorito de sódio, dióxido de cloro (CDS) ou soluções minerais milagrosas (MMS), em todas as suas formas e apresentações;`
>
> `Desde 6 de agosto de 2026, a Shopee está autorizada pela Anvisa a comercializar medicamentos isentos de prescrição (MIPs), apenas por farmácias e drogarias regularmente licenciadas que sigam rigorosamente todas as regulamentações da categoria e da agência, conforme a Resolução-RE nº 3.056/2026.`
>
> `De acordo com a política da Shopee, anúncios que vendem medicamentos controlados (sem licenciamento apropriado), drogas ilícitas ou suplementos de saúde com informações falsas e enganosas serão excluídos.`

**来源**（`source.tier = platform_official`）：`source.url` =
`https://seller.br.shopee.cn/edu/article/7379`，`article_id` = `7379`，
`last_verified` = 2026-10-27。

### 4.2 判定边界

| 边界 | 说明 |
|---|---|
| **不因通用词「medicamento」而阻断** | `SBR-MED-001` 的正则刻意**不含**裸词 `medicamento`。通用词一命中就会把所有保健品listing判成禁售，而且在 2026-08-06 之后本身就是错的。裸词由 `SBR-MED-002` 的资质维度接管 |
| **`SBR-MED-002` 是 `require_evidence` 不是 `block`** | 药可能完全合法，卖方也可能就是持牌药店 —— 区分这两者的正是证据清单（`pharmacy_license`）。拿不出药店执照的商品**不得**上架，但结论动作是「补材料」而非「商品违规」 |
| **`SBR-MED-003` 管宣称不管商品** | 保健品本身被平台明确允许（`Suplementos de saúde, como: vitaminas, ervas e produtos naturais;`）。被平台执行的是**失实宣称** |
| **「绝对禁止」的清单是穷举式的** | `SBR-MED-001` 匹配的是原文列举的具体品类（MMS / CDS / 堕胎药 / 注射剂 / 兽药 / 毒品），不是「所有药」 |

### 4.3 典型正例 / 反例

| 规则 | 正例（应命中） | 反例（不应命中） |
|---|---|---|
| `SBR-MED-001` | `Solução Mineral Milagrosa 500ml com Clorito de Sódio` | `Suporte Ergonômico para Mesa de Trabalho` |
| `SBR-MED-002` | `Medicamento Isento de Prescrição com Tarja Vermelha 30 Comprimidos` | `Ômega 3 1000mg 120 Cápsulas` |
| `SBR-MED-003` | `Suplemento de Saúde com Informações Falsas - 100% Eficaz` | `Suplemento Alimentar de Proteína 24 Porções` |

---

## 5. LV（刊登质量）—— `SBR-LV-001` … `SBR-LV-014`

### 5.1 判定含义

LV 类管的是**商品页面本身的质量与合规**，不涉及商品本体能不能卖。
全部 `active` 的 LV 规则的声明动作都是 `flag_for_review` —— **没有一条 LV 规则会阻断**。

| 规则 | 平台码 | 判定对象 | `severity` | `decision` |
|---|---|---|---|---|
| `SBR-LV-001` | `[337]` | 夸大 / 奇迹式健康宣称 | `medium` | `flag_for_review` |
| `SBR-LV-002` | `[405]` | 误导折扣 / 欺骗性定价 | `low` | `flag_for_review` |
| `SBR-LV-003` | `[506]` | 标题关键词堆砌 | `low` | `flag_for_review` |
| `SBR-LV-004` | `[507]` | 标题里堆砌 / 无关品牌名 | `low` | `flag_for_review` |
| `SBR-LV-005` | `[112]` | 站外引流 / 站外联系方式 | `medium` | `flag_for_review` |
| `SBR-LV-006` | `[605]` | 描述内容不足 / 不当 / 不相关 | `medium` | `flag_for_review` |
| `SBR-LV-007` | `[606]` | 图片质量低 / 不当 / 与商品无关 | `low` | `flag_for_review` |
| `SBR-LV-008` | `[613]` | 类目错误 / 缺失 | `low` | `flag_for_review` |
| `SBR-LV-009` | —— | 商品缺监管注册 / 认证信息 | `low` | `flag_for_review` |
| `SBR-LV-010` | `[510]` | 年龄分级与类目 / 标题不符 | `low` | `flag_for_review` |
| `SBR-LV-011` | `[301]` | 品牌信息不准确 / 缺失 | `low` | `flag_for_review` |
| `SBR-LV-012` | `[120]` | 尺寸 / 重量信息不精确 | `low` | `flag_for_review` |
| `SBR-LV-013` | `[509]` | 声明了完整三维尺寸（是否超限人工确认） | `medium` | `flag_for_review` |
| `SBR-LV-014` | `[309]` | 变体使用不当 —— **状态 `draft`，不产出任何结论** | `info` | `allow` |

引文（逐字，来自 `research/raw/shopee_br_banimento_suspensao_anuncios.txt`）：

> `[337] Anúncio removido por conter promessas exageradas ou milagrosas. Severidade: Média. Gera ponto de penalidade.`
>
> `[405] Propaganda Enganosa. Severidade: Baixa. Não gera ponto de penalidade.`
>
> `[506] Palavras-chave excessivas e/ou irrelevantes no título do anúncio. Severidade: Baixa. Não gera ponto de penalidade.`
>
> `[507] Marcas excessivas e/ou irrelevantes no título do anúncio. Severidade: Baixa. Não gera ponto de penalidade.`
>
> `[112] Anúncio removido por conter informações não permitidas de direcionamento para fora da Shopee. Severidade: Média. Não gera ponto de penalidade.`
>
> `[605] Anúncio removido por conteúdo insuficiente, inadequado ou irrelevante na descrição do produto. Severidade: Média. Gera ponto de penalidade.`
>
> `[606] Anúncio removido por imagem de baixa qualidade, inapropriada ou fora do contexto do produto anunciado. Severidade: Baixa. Não gera ponto de penalidade.`
>
> `[613] Categoria incorreta. Severidade: Baixa. Não gera ponto de penalidade.`
>
> `[510] A faixa etária do produto não corresponde à categoria selecionada e/ou título do anúncio. Severidade: Baixa. Não gera ponto de penalidade.`
>
> `[301] Anúncio removido por imprecisão na marca informada. Severidade: Baixa. Não gera ponto de penalidade.`
>
> `[120] Anúncio removido por informações imprecisas sobre dimensões e peso do produto. Severidade: Baixa. Não gera ponto de penalidade.`
>
> `[509] Anúncio removido por exceder as dimensões e/ou pesos permitidos. Severidade: Alta. Gera ponto de penalidade.`

`SBR-LV-009` 的引文来自 `research/raw/shopee_br_politica_produtos_proibidos.txt`：

> `São proibidos produtos que não tenham a devida homologação, licença e/ou registro das agências nacionais ou órgãos competentes, como: ANVISA, ANATEL, ANS, INMETRO, ANP e MAPA.`

**来源**：

| 规则 | `source.url` | `article_id` | `last_verified` |
|---|---|---|---|
| `SBR-LV-001` … `SBR-LV-008`、`SBR-LV-010` … `SBR-LV-014` | `https://seller.br.shopee.cn/edu/article/5139` | `5139` | 2026-10-27 |
| `SBR-LV-009` | `https://seller.shopee.com.br/edu/article/3304/politica-de-produtos-proibidos-e-restritos` | `3304` | 2026-10-27 |

### 5.2 判定边界 —— 逐条实测语义

LV 类的触发条件有 5 种算子，语义各不相同。**读 `reason` 里的 `matched in <field>` 片段就能知道命中了什么。**

| 规则 | 条件 | 实际判定语义 |
|---|---|---|
| `SBR-LV-001` | `any_text` / `regex` | 匹配「夸大 / 奇迹式宣称」的固定短语表（`cura definitiva`、`100% eficaz`、`elimina psoríase`、`tratamento milagroso` 等）。命中的是**措辞**，不是宣称背后的证据 |
| `SBR-LV-002` | `any_text` / `regex` | 匹配折扣话术（`desconto de N%`、`de R$ X por R$ Y`）。**只判「有折扣话术」这个事实**，不判折扣是否失实 —— 真实性要看 `price_history` / `promotion_terms` |
| `SBR-LV-003` | `title` / `regex` | 正则 `(?i)(\b(?:\w+[-–]?){15,}\b)`。实测：15 个字母的连续串命中，14 个不命中；**空白会断开计数**。所以它实际拦的是「超长无空格串」与「连字符串」，不是「标题词数 ≥ 15」 |
| `SBR-LV-004` | `title` / `regex` | 命中**两个及以上**已知品牌名同时出现（`Nike` + `Adidas` 等 13 个品牌表） |
| `SBR-LV-005` | `any_text` / `regex` | 站外引流：非 Shopee 域名 URL、`WhatsApp` / `wa.me` / `telegram` / `@账号` / `compre direto` 等 |
| `SBR-LV-006` | `description` / `length_lt` | 描述**字符数 < 120**。这是可判定的结构事实，不涉及内容质量判断 |
| `SBR-LV-007` | `image` / `image_count_lt` | 图片**张数 < 1**。实测语义是「**没有图片**」，不是「图片质量差」—— 质量需要 `image_review` 人工看 |
| `SBR-LV-008` | `category` / `field_missing` | 类目**缺失或为空**。实测：类目键缺失与类目为空串都命中 |
| `SBR-LV-009` | `any_text` / `regex` | 命中「`homologação` / `registro anvisa` / `certificado inmetro` / `GTIN` / `EAN+8~14 位数字`」等**注册痕迹**。实测语义是「商品页自称或提及注册信息」，不是「已核验注册有效」 |
| `SBR-LV-010` | `any_text` / `regex` | 成人标记（`adulto` / `18+`）与儿童标记（`criança` / `infantil` / `bebê` / `kids`）**同时出现**（两个方向都判），距离 ≤ 40 字符 |
| `SBR-LV-011` | `brand` / `field_missing` | 品牌**缺失或为空**。实测：品牌键缺失与空白串（`"  "`）都命中 |
| `SBR-LV-012` | `any_text` / `regex` | 重量与尺寸**同时出现**（`peso` + `dimensões`/`tamanho`，或 `dimensões`/`largura`/`altura` + `peso`，间距 ≤ 60 字符）。判的是「两套数据并存却可能互相矛盾」 |
| `SBR-LV-013` | `any_text` / `regex` | 匹配**完整三维尺寸**（`NNcm` × 3，或 `NNcm` × 2 + `NNm`）。**平台未公开尺寸上限数值**，本规则只标记「声明了完整三维尺寸」这一事实，是否超限由人工复核 —— 详见 `references/policy_currency.md` §5 |
| `SBR-LV-014` | `variations` / `has_field` | **`status = draft`**，不参与判定。规则自身的 `notes` 写明：该触发条件无法区分「不当使用变体」与「正常变体」，需要变体 / 属性一致性检查才能落地。保留为 draft 是为了**保证它永远不会阻断** |

> `rules/03_listing_violations_duplicates.json` 里同时还有 `SBR-DUP-001` … `SBR-DUP-003`。
> **本模块不读它们** —— `rules.py` 的 `load_rules()` 按前缀过滤，只取 `PI` / `RI` / `MED` / `LV`。

### 5.3 典型正例 / 反例

| 规则 | 正例（应命中） | 反例（不应命中） |
|---|---|---|
| `SBR-LV-001` | `Sérum Facial Antiacne 30ml` | `Suporte Ergonômico para Reduzir o Desconforto Postural` |
| `SBR-LV-002` | `Fone Bluetooth com Desconto de 70%` | `Fone Bluetooth Sem Fio com Cancelamento de Ruído` |
| `SBR-LV-003` | `Tênis Esportivo Premium Masculino Feminino Unissex Casual Esportivo-running Treino Academia Confortável Leve Durável Impermeável Para Dia a Dia` | 同标题但无连字符串的 14 词版本 |
| `SBR-LV-004` | `Tênis Nike com Technology Adidas Solado Premium` | `Tênis Esportivo Nike Runner Masculino` |
| `SBR-LV-005` | `Camiseta Personalizada Estampa a Your Name`（详情含 WhatsApp） | `Chaleira Elétrica Inox 1,7L` |
| `SBR-LV-006` | `Chaveiro de Couro Personalizado`（描述 < 120 字符） | `Chaveiro de Couro Personalizado com Gravação`（描述 ≥ 120 字符） |
| `SBR-LV-007` | `Kit 4 Copos de Vidro 250ml`（`images: []`） | 同款商品但 `images` 非空 |
| `SBR-LV-008` | `Organizador de Gaveta com 6 Compartimentos`（`category` 为空） | 同款商品但 `category` 完整 |
| `SBR-LV-009` | `Fone Bluetooth sem Certificado e sem Registro` | `Organizador de Gaveta Transparente com Tampa` |
| `SBR-LV-010` | `Mochila Infantil para Adultos 30L` | `Mochila Infantil para Crianças 20L` |
| `SBR-LV-011` | `Garrafa Térmica 500ml Inox`（品牌为空） | 同款商品但品牌为 `TermoSul` |
| `SBR-LV-012` | `Tapete de Yoga Antiderrapante 6mm`（同时给厚度与重量） | `Kit 10 Peneiras em Aço Inox para Cozinha` |
| `SBR-LV-013` | `Caixa de Armazenamento Grande 60L`（声明三维尺寸） | `Kit 6 Copos de Vidro 250ml` |
| `SBR-LV-014` | —— （`draft`，永不命中） | `Camiseta Estampada com Variação de Tamanho` |

---

## 6. 动作解析：`_resolve_action` 的降级链

规则声明的动作**不是**最终动作。`engine.py` 的 `_resolve_action()` 依次过三道关，
每一道降级都会写进 `reason`（形如 `... was downgraded to '...'`），
让复核者看到「本来想做什么、为什么没做成」。

```
1. status != "active"
   → 规则根本不参与判定（_evaluate_rule 直接返回 "skipped"）
   → 已降级的场景不适用

2. 声明动作 ∈ {block, freeze_relist, escalate_legal} 但 source.tier ∉ {platform_official, law}
   → 降级为矩阵允许的 require_evidence → flag_for_review
   → 理由文本含 "(hard constraint H2)"

3. 矩阵不允许 (risk_level, 声明动作) 组合
   → 取该风险等级下「不弱于声明动作」的最细允许动作
   → 找不到则取最强允许动作 + 记 error（stage=rule_evaluation, severity=error）
```

实测降级行为：

| 场景 | 声明 | 结果 | `downgrade_reason` |
|---|---|---|---|
| `internal_risk` + `critical` | `block` | `require_evidence` | `... requires source.tier in {platform_official, law} and status 'active' ... (hard constraint H2)` |
| `platform_official` + `critical` | `revise` | `flag_for_review` | `... is not allowed for risk level 'critical' by contracts/risk_action_matrix.json ...` |
| `platform_official` + `info` | `block` | `flag_for_review` + error | `no allowed action matches the declared action 'block' at risk level 'info' ...` |

**聚合阶段**（`build_result()`）：

- `risk_level` = 命中规则的最重 `severity`（`SEVERITY_ORDER`：`info` < `low` < `medium` < `high` < `critical`）
- `action` = 命中规则动作里**最细粒度**的那一条（`ACTION_GRANULARITY`：`allow` 0 < `flag_for_review` 1 < `require_evidence` 2 < `revise` 3 < `block` 4 < `freeze_relist` 5 < `escalate_legal` 6）
- `verdict` = 由最终 `action` 查矩阵得出
- `confidence` = 命中规则里**最弱**的那一个（`signal` < `likely` < `confirmed`）

> `verdict` 取最重、`action` 保留最细粒度 —— 这正是
> `contracts/risk_action_matrix.json` → `verdict_aggregation.rule = "max_with_action_detail"`
> 的含义。因此「`verdict: REVIEW` + `action: require_evidence`」是**正常的**
> 组合，不是矛盾。

---

## 7. 置信度：`_confidence()` 的三档

`confidence` 只描述**这条结论有多硬**，取值只有 `signal` / `likely` / `confirmed`。

| 取值 | 触发条件（实测） |
|---|---|
| `confirmed` | `status == "active"` 且 `source.tier ∈ {platform_official, law}`，且触发的算子**全部**属于结构算子集合（`field_missing`、`has_field`、`has_nonempty`、`image_count_lt`、`image_count_gte`、`length_lt`、`length_gte`、`equals`、`not_equals`、`gt`、`gte`、`lt`、`lte`） |
| `likely` | 同上（权威来源 + `active`），但触发了非结构算子（`regex` / `contains_any` / `contains_all` / `not_contains_any`） |
| `signal` | 非权威来源 / 非 `active` 规则 / IP 四类规则（硬约束 **H1**） |

实测对照：

| 触发算子 | `confidence` |
|---|---|
| `field_missing` / `length_lt` / `has_field` / `equals` / `image_count_lt` / `length_gte` | `confirmed` |
| `regex` / `contains_any` / `contains_all` / `not_contains_any` | `likely` |
| `category = ip_trademark`（任意算子） | `signal` |

> **本模块不产生 IP 类规则结论**（`rules/02_ip_trademark_copyright.json` 属
> `shopee-br-ip-review`）。但 `_confidence()` 里的 H1 分支是**实装的**，
> 且 `L4 / H1` 测试段对它有断言 —— 以防上游通过 `SkillInput.rules[]`
> 传入 IP 规则（`rules.py` 的 `load_rules()` 支持 `extra_rules`，
> 但仍按 `OWNED_PREFIXES` 过滤，`IP` 前缀会被丢弃）。

---

## 8. 人工复核：`requires_human_review` 的判定

`_review_requirements()` 汇总下列任一条件成立即为 `true`：

| # | 条件 |
|---|---|
| 1 | 动作在矩阵里 `always_human_review`（`allow` 之外的全部 6 个动作都是） |
| 2 | 命中了 IP 类规则 |
| 3 | 规则 `requires_human_review: true`（本模块 34 条规则里 29 条为 `true`） |
| 4 | 规则 `status != "active"` |
| 5 | 规则 `source.tier ∈ {internal_risk, unverified}` |
| 6 | 命中规则发生过降级（`downgrade_reason` 非空） |
| 7 | `confidence == "signal"` |
| 8 | 存在 `unevaluated[]` 条目 |
| 9 | 词库筛查未能运行（`lexicon_state == "unevaluated"`） |

`review_rationale` 会把上述原因逐条列出来，形如
`manual review needed: action 'block' always requires human review; confidence is 'signal' (keyword/screening level only); ...`。

---

## 9. 缺失输入的三种表现（实测）

`fields.py` 的 `is_empty()` 定义：**存在但为空 == 缺失**。

| 输入形态 | `is_empty()` | 结果 |
|---|---|---|
| 键缺失（`product` 里没有 `description`） | `True` | 依赖它的规则进 `unevaluated[]` |
| `null` | `True` | 同上 |
| 空字符串 `""` | `True` | 同上 |
| 只有空白字符 `"  "` | `True` | 同上（**去空白后为空**） |
| 空数组 `[]` / 空字典 `{}` | `True` | 同上 |
| 数字 `0` / 布尔 `False` | **`False`** | **不算缺失** —— 0 是有效取值 |

实测对照（同一商品，只改一个字段）：

| 输入 | 命中规则 | `unevaluated[]` |
|---|---|---|
| `description` 缺失 | —— | `SBR-LV-006`（`missing_fields: ["description"]`） |
| `images` 键缺失 | —— | `SBR-LV-007`（`missing_fields: ["image"]`） |
| `images: []`（空数组） | `SBR-LV-007` | —— |
| `category` 键缺失 | `SBR-LV-008` | —— |
| `category: ""` | `SBR-LV-008` | —— |
| `brand: null` | `SBR-LV-011` | —— |
| `brand: "  "` | `SBR-LV-011` | —— |

> **`images: []` 与 `images` 键缺失不是一回事。**
> 前者「确实没有图」→ `SBR-LV-007` 命中；后者「本次没拿到图数据」→ 未评估。
> 规则 `SBR-LV-007` 的 `notes` 写明了这条设计意图：
> *"Only evaluated when the input actually carried image data; a spreadsheet with no
> image column is a data gap, not a violation."*

### 9.1 `field_missing` 类规则的特殊性

`SBR-LV-008`（类目缺失）与 `SBR-LV-011`（品牌缺失）用的就是 `field_missing`
算子 —— **「字段缺失」本身就是要检出的违规事实**，不是数据缺口。
所以这两条规则在字段缺失时**命中**而非未评估。

但 `field_missing` 算子必须先过 `is_empty()`：空串与纯空白串同样算「缺失」，
所以 `brand: "  "` 会命中 `SBR-LV-011`。这是有意的：平台要求品牌字段不得留白。

> 早期版本给 `SBR-LV-007` / `SBR-LV-008` / `SBR-LV-011` 写了自指的 `requires_input`
> （检查字段 X 是否存在，同时又声明依赖字段 X），逻辑上永不可满足 —— 字段缺失即被判
> 未评估，等于规则永不生效。v2 已移除这三个自指的 `requires_input`。

---

## 10. 硬约束在本模块的落点

| ID | 约束 | 本模块如何满足 | 实现位置 |
|---|---|---|---|
| **H1** | IP 类结论恒为 `signal` + 强制人工复核 | `_confidence()` 首行判 `is_ip_rule`；`_review_requirements()` 对 IP 规则追加理由。本模块不加载 `IP` 前缀规则，`candidate_rules()` 也按前缀过滤掉 IP 词组 | `engine.py` |
| **H2** | `block` / `freeze_relist` / `escalate_legal` 只来自 `platform_official` / `law` 的 `active` 规则 | `rules.py` 的 `blocking_allowed()` + `TIER_MAX_ACTION`；`engine.py` 的 `_resolve_action()` 降级 | `rules.py`、`engine.py` |
| **H3** | 输入缺失 → 不评估 + 上报 `unevaluated[]` + warning 错误 | `conditions.py` 返回 `UNEVALUATED`；`engine.py` 记 `unevaluated[]` 与 `errors[]`（`stage: "rule_evaluation"`, `severity: "warning"`） | `conditions.py`、`engine.py` |
| **H4** | `source.excerpt` 必须逐字出现在 `research/raw/` 抓取件中 | 全部 `active` 规则的引文逐字取自抓取件；核验命令 `tools/verify_citations.py`（当前 `50/50 excerpts verified verbatim, 0 failed`） | `rules/**`、`tools/verify_citations.py` |
| **H5** | `evidence_refs.artifact_ref` 只存引用，不内嵌凭证内容 | 观测证据的 `artifact_ref` 恒为 `products/<product_id>/<field>`；待补证据恒为 `null` | `engine.py` 的 `_build_evidence_refs()` |
| **H6** | `freeze_relist` / `escalate_legal` 为 `human_only` | 本模块 34 条规则无一声明这两个动作（`decision` 分布：`flag_for_review` 14 / `block` 11 / `require_evidence` 8 / `allow` 1），且源码不含任何线上处置入口 | `rules/**`、`skills/shopee-br-listing-audit/src/sbr_listing_audit_cli.py` |

---

## 11. 本模块**不做**的事

| 不做 | 归属 |
|---|---|
| IP 侵权判定（`ip_trademark` / `ip_copyright` / `ip_design` / `ip_patent`） | `shopee-br-ip-review` |
| 重复刊登 / 跨店关联 / 重发冻结（`SBR-DUP-*` / `SBR-RL-*` / `SBR-AU-*` / `SBR-AC-*`） | `shopee-br-duplicate-detection` |
| 原始文件解析与字段标准化 | `shopee-br-data-ingestion` |
| 报告生成 | `shopee-br-reporting` |
| 任何线上处置（发布 / 删除 / 冻结 / 申诉） | 无人 —— 本模块只产出结论与待补证据清单 |

---

## 12. 判定的权威依据

| 语义 | 权威来源 |
|---|---|
| 风险等级 × 处理动作的允许组合 | `contracts/risk_action_matrix.json` → `matrix` |
| 动作 → `verdict` 映射 | `contracts/risk_action_matrix.json` → `actions` |
| 结论聚合顺序与粒度保留 | `contracts/risk_action_matrix.json` → `verdict_aggregation` |
| 输出字段与枚举 | `contracts/audit_result.schema.json` |
| 规则的字段与算子枚举 | `data/schema/rule.schema.json` |
| 规则的来源与状态 | `data/schema/rule_collection.schema.json` |
| 硬约束 H1–H6 | `contracts/risk_action_matrix.json` → `hard_constraints`、`PROJECT_RULES.md` §6.1 |
| 引用字段形状 | `contracts/rule_envelope.schema.json` |
| 证据引用字段形状 | `contracts/evidence_reference.schema.json` |
