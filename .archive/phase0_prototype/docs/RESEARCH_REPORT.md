# 官方规则调研报告 — Shopee 巴西站商品合规

> 调研日期：2026-10-27
> 调研范围：Shopee 巴西站平台政策、服务条款、社区准则 + 巴西联邦知识产权与消费者保护法
> 原始抓取件：`research/raw/`（每个来源一个 `.txt`，未修改）
> 来源清单：`research/sources.json`
> 结构化违规码：`research/violation_codes.json`（106 条）

---

## 0. 本报告怎么读

本报告严格区分四类信息，任何一条结论都标注其**层级**：

| 层级 | 含义 | 在规则库中的对应 | 可否直接用于处置 |
|---|---|---|---|
| `platform_official` | Shopee 官方页面明确写出的规则 | `source_tier: "platform_official"` | 可以（严重度与处罚由平台定义） |
| `law` | 巴西联邦法律明文规定 | `source_tier: "law"` | 可以（法律义务） |
| `internal_risk` | 内部风控建议、运营经验 | `source_tier: "internal_risk"` | **不可以**，只能提示人工复核 |
| `unverified` | 尚未核实的假设 | `source_tier: "unverified"` | **不可以**，只能进入待核实清单 |

**所有正式规则的 `source_excerpt` 都经过 `tools/verify_citations.py` 的逐字校验**：引文必须在 `research/raw/` 的抓取件中逐字出现，否则校验失败。当前状态：**47/47 条规则引文通过逐字校验**。

---

## 1. 来源清单与抓取情况

### 1.1 抓取成功的来源

| # | 来源 | URL | 层级 | 抓取件 | 备注 |
|---|---|---|---|---|---|
| 1 | Termos de Serviço da Shopee | `help.shopee.com.br/portal/4/article/77113` | platform_official | `shopee_br_termos_de_servico.txt` | 服务端渲染，含 IP 投诉条款 |
| 2 | Diretrizes da Comunidade Shopee | `help.shopee.com.br/4/article/150027` | platform_official | `shopee_br_diretrizes_comunidade.txt` | 内容准则 |
| 3 | Política de Produtos Proibidos e Restritos | `seller.shopee.com.br/edu/article/3304` | platform_official | `shopee_br_politica_produtos_proibidos.txt` | **禁售/受限商品总纲**，18+12 个大类 |
| 4 | Produtos e categorias restritas | `seller.br.shopee.cn/edu/article/12544` | platform_official | `shopee_br_produtos_restritos_liberacao.txt` | 授权申请流程 |
| 5 | Principais dúvidas sobre Violações de Anúncio | `seller.br.shopee.cn/edu/article/16318` | platform_official | `shopee_br_violacoes_anuncio.txt` | 违规类型、封禁 vs 下架 |
| 6 | Principais Motivos de Banimento e Suspensão | `seller.br.shopee.cn/edu/article/5139` | platform_official | `shopee_br_banimento_suspensao_anuncios.txt` | **106 条违规码 + 严重度 + 扣分标记** |
| 7 | Sistema de Pontos de Penalidade | `seller.shopee.com.br/edu/article/16316` | platform_official | `shopee_br_pontos_de_penalidade.txt` | 处罚点、申诉时限 |
| 8 | Diretrizes da Comunidade Shopee Video | `help.shopee.com.br/portal/10/article/188364` | platform_official | `shopee_br_diretrizes_comunidade_video.txt` | 视频内容准则 |
| 9 | Lei nº 9.279/1996 — Propriedade Industrial | `planalto.gov.br/ccivil_03/leis/l9279.htm` | law | `br_lei_propriedade_industrial_9279.txt` | 工业产权法 |
| 10 | Lei nº 9.610/1998 — Direitos Autorais | `planalto.gov.br/ccivil_03/leis/l9610.htm` | law | `br_lei_direitos_autorais_9610.txt` | 著作权法 |
| 11 | INPI — Legislação de Marcas | `gov.br/inpi/pt-br/servicos/marcas/legislacao` | law | `br_inpi_legislacao_marcas.txt` | 商标注册程序索引 |
| 12 | Lei nº 8.078/1990 — Código de Defesa do Consumidor | `planalto.gov.br/ccivil_03/leis/l8078compilado.htm` | law | `br_consumidor_cdc_publicidade.txt` | 消费者保护/误导性宣传 |
| 13 | Como fazer a migração da conta CPF para CNPJ | `seller.shopee.com.br/edu/article/9216` | platform_official | `shopee_br_mudanca_conta_cpf_cnpj.txt` | 店铺资质 |
| 14 | O que acontece se eu colocar para venda um medicamento proibido? | `seller.br.shopee.cn/edu/article/7379` | platform_official | `shopee_br_categorias_restrritas.txt` | 禁售药品处理 |
| 15 | Como selecionar a categoria de anúncios correta? | `seller.br.shopee.cn/edu/article/2820` | platform_official | `shopee_br_categoria_correta.txt` | 类目选择规范 |

### 1.2 抓取失败 / 未完成的来源（待核实）

| 来源 | 目标 URL | 状态 | 影响 |
|---|---|---|---|
| RDC 96/2008（Anvisa 药品广告） | `bvsms.saude.gov.br/...` | **HTTP 503** | 药品/保健品类广告宣称规则无一手来源 |
| RDC 44/2009（处方药分发） | `bvsms.saude.gov.br/...` | **HTTP 503** | 处方药禁售细则无一手来源 |
| 商品链接抓取（Seller Centre 后台列表） | `seller.shopee.com.br/edu/...` | 需要登录态 | 未做；见 §5 |

> **说明**：`seller.shopee.com.br/edu/article/*` 是客户端渲染的 SPA，静态抓取只会得到空壳。工具链 `tools/render_page.py` 用无头 Chromium 执行 SPA 后再取渲染文本，这是拿到一手正文的前提。

---

## 2. 平台规则要点

### 2.1 违规的四种类型（`shopee_br_violacoes_anuncio.txt`）

平台把 listing 违规分为四类：

| 类型 | 平台原文要点 | 本项目对应规则类别 |
|---|---|---|
| **Anúncios proibidos** | "produtos proibidos para venda por lei ou pelo Shopee" | `prohibited_item` / `restricted_item` |
| **Violação de IP e falsificação** | "venda de produtos que contenham marcas registradas sem autorização do proprietário da marca" | `ip_trademark` / `ip_copyright` / `ip_design` |
| **Spam** | "anúncios duplicados, Spam de palavras-chave no título" | `duplicate_listing` / `cross_store_duplicate` / `listing_violation` |
| **Item de Qualidade Insatisfatória (IQI)** | "pode resultar na exclusão do anúncio e na aplicação de pontos de penalidade" | `listing_violation` / `consumer_protection` |

### 2.2 「封禁」与「下架」是两种不同的处置（关键区分）

> 原文：*"Anúncios banidos podem ser restabelecidos assim que a violação for resolvida. **Os anúncios excluídos pela Shopee não podem ser recuperados** e incorrerão pontos no sistema de Pontos de Penalidade do Vendedor da Shopee. Itens com o alcance limitado também retornam assim que houver a correção indicada."*

这直接决定了「违规商品重发」的处置逻辑：

| 平台处置 | 是否可恢复 | 重发后果 | 本项目规则 |
|---|---|---|---|
| **Banido**（封禁） | 违规解决后**可以**恢复 | 需人工复核 | `SBR-RL-001`（仅提示复核） |
| **Excluído**（下架） | **不可**恢复 | 计入处罚点 | `SBR-RL-002` → `freeze_relist` |
| **Alcance limitado**（限流） | 改正后**自动**恢复 | — | `SBR-RL-001` |

### 2.3 处罚点机制（`shopee_br_pontos_de_penalidade.txt`）

- 处罚点**每周一**统一归属，不再即时生效。
- 店铺进入处罚档位后，**一周后**开始执行限制，限制期 **14–28 天**。
- 费用在处罚开始**两周后**从钱包扣除；上月 GMV 低于 R$2.500 的店铺不收该费用。
- 处罚点**不清零**，保留至季度末。
- **每个已认定的违规只能申诉一次**；申诉被驳回后，即使补充材料也不能撤销处罚点，但被下架的 listing 可以申请恢复。
- 申诉材料需包含订单 ID、申诉理由与证据附件。
- 账号因违规被冻结时，货款可能被扣留直至处罚撤销。

> 这些是「重发冻结」与「申诉时限」两条规则（`SBR-AC-001`、`SBR-AC-002`）的一手依据。

### 2.4 违规码目录（106 条）

`research/violation_codes.json` 收录了平台公开的全部 **106 条**违规码，每条带原始严重度与是否扣分。分类分布：

| 分类 | 条数 | 代表码 |
|---|---|---|
| `prohibited_restricted_policy` | 41 | [311] 烟草/电子烟、[313] 管制药品、[332] 化学危险品、[516] 政府标识 |
| `listing_violation` | 39 | [605] 描述不足、[606] 图片不当、[613] 类目错误、[506] 标题堆砌 |
| `regulator_prohibited` | 11 | [100] 监管禁售、[122] Anatel、[123] Anvisa、[125] Inmetro、[126] MAPA |
| `ip_trademark` | 7 | [133] 商标权、[601] 假冒/商标、[205] 疑似非正品、[349] 外卖平台 logo |
| `regulator_policy_change` | 3 | [101] 政策变更、[117]/[118] 变为禁售 |
| `duplicate_listing` | 2 | [401] 复制他人 listing、[302] 重复 listing |
| `ip_copyright` | 1 | [602] 著作权 |
| `ip_design` | 1 | [603] 外观设计 |
| `fulfillment` | 1 | [103] 未发货 |

严重度分布中，**Extrema（极严重）** 的码包括 [311] 电子烟、[313] 黑标药品、[317] 枪支弹药、[320] 色情、[326] 假币、[332] 易燃化学品、[338] 赌博、[339] 野生动物、[340] 人体器官、[341] 伪造证件/干扰器、[516] 政府标识。

### 2.5 禁售与受限商品总纲（18 大类 + 12 其他类）

`shopee_br_politica_produtos_proibidos.txt` 的结构：

- **18 个主类目**：服饰配件(眼镜)、食品饮料(酒精、乳制品)、宠物(宠物药品)、音频(录音笔)、汽车(外挂/内饰/机油/附加件/轮胎)、电池、 美妆(护肤/美甲/染发)、相机无人机、家居(厨具/家护/工具/园艺/消防)、手机平板、电脑配件(存储/网络/键鼠)、家电(电视)、运动户外(露营/气枪/拳击)、收藏品、票券服务、书籍杂志、孕婴(玩具/婴儿健康/孕期)、健康(性健康/口腔/护眼/营养补充/医疗用品)。
- **12 个其他类目**：武器(枪械配件/弓弩/白刃/气枪/枪械配件/刀具)、毒品与医疗器械(非法毒品/管制药品/OTC)、监控(个人数据/授权文件/制服)、**不实健康信息**、赌博、实体货币与点数、**人体部位**、**政治/宗教**、化学品爆炸物(爆炸物/易燃/有毒致癌)、**禁止服务**、**烟草尼古丁电子烟**、**非流通商品**。

总纲中的三条总原则：

1. **知识产权**："São proibidos anúncios que violem as leis de direito autoral, patentes, marcas, modelos de utilidade, desenhos industriais, indicações geográficas, denominações de origem, selos de certificações e de agências reguladoras."
2. **监管注册**："São proibidos produtos que não tenham a devida homologação, licença e/ou registro das agências nacionais ou órgãos competentes, como: ANVISA, ANATEL, ANS, INMETRO, ANP e MAPA."
3. **召回商品**："produtos que tenham sido objeto de recall e retirados de circulação" 同样禁止。

乳制品条款给出了平台常用的三段式判例写法（禁止 / 仅授权卖家可售 / 全卖家可售），本项目的 `SBR-RI-008` 直接采用该结构。

### 2.6 受限类目授权流程

`seller.br.shopee.cn/edu/article/12544` 明确：卖家**自负合规责任**；受限类目需通过官方表单申请；需 CNPJ 生效、账号完成身份验证。卖家责任声明的原文是本项目 `SBR-AU-001` 的一手依据。

### 2.7 ⚠️ 药品政策变更（2026-08-06）—— 必须特别注意

`shopee_br_categorias_restrritas.txt`（文章 7379，页面标注更新于 2026-08-10）记录了一次**实质性政策放宽**：

> *"Desde 6 de agosto de 2026, a Shopee está autorizada pela Anvisa a comercializar medicamentos isentos de prescrição (MIPs), apenas por farmácias e drogarias regularmente licenciadas que sigam rigorosamente todas as regulamentações da categoria e da agência, conforme a Resolução-RE nº 3.056/2026."*

**含义**：自 2026 年 8 月 6 日起，Shopee 获得 Anvisa 授权销售**非处方药（MIPs）** —— 但**仅限**持有正规牌照、严格遵守品类与机构全部规定的**药店/药妆店卖家**。

**这对规则库的影响**：任何在 2026-08-06 之前写的「所有药品一律禁售」规则都已过时。本项目把两种情况分开处理：

| 规则 | 场景 | 决策 |
|---|---|---|
| `SBR-MED-001` | 绝对禁售药类：人用药、兽用药、堕胎相关、**氯化钠/二氧化氯（CDS）/ 神奇矿物溶液（MMS）**、医疗/美容用途注射剂与静脉制剂、非法毒品 | `block` |
| `SBR-MED-002` | MIP / 管制药，但卖家**不是**持牌药店/药妆店 | `require_evidence`（要药店牌照） |
| `SBR-MED-003` | 保健品本身**允许**（维生素、草药、天然产品），平台管的是**宣称的真实性** | `flag_for_review` |

注意 `SBR-MED-001` 的触发词**刻意不包含**泛指的「medicamento」—— 否则会把所有保健品 listing 一起阻断，而且在 8 月 6 日之后是错的。

**仍待核实**：Resolução-RE nº 3.056/2026 的**具体要求清单**（牌照类型、品类范围、审核流程）未采集，见 §5。

---

## 3. 巴西法律要点

### 3.1 Lei nº 9.279/1996（工业产权法）

| 条文 | 要点 | 对应规则 |
|---|---|---|
| Art. 2º | 保护通过：专利/实用型号、**外观设计注册**、商标注册、地理标志压制、不正当竞争压制 | `SBR-IP-008` |
| Art. 129 | 商标权经有效注册取得，**排他使用** | `SBR-IP-001` |
| **Art. 132, II** | **商标权人不得阻止配件制造商使用该商标指示产品的用途**（只要遵守正当竞争惯例） | **`SBR-IP-006`（兼容性描述不算侵权）** |
| Art. 194 | 使用虚假来源标识的商标/商号/招牌，或销售带此类标识的商品 —— 拘役 1–3 个月或罚金 | `SBR-IP-002` |
| Art. 195, IV | 使用他人广告表达或仿冒以造成混淆 —— **不正当竞争罪** | `SBR-IP-002` |

> **Art. 132, II 是本项目最重要的「反误判」依据**：车型兼容性描述（"compatível com Ford Focus"）在巴西法下是合法的指示性使用，不构成商标侵权。规则 `SBR-IP-006` 就是为了防止引擎把兼容性 listing 误判为侵权。

### 3.2 Lei nº 9.610/1998（著作权法）

保护文学、艺术与科学作品；网络传播与商业化受控制。平台对应码 [602]（严重度 Alta，扣分）。本项目 `SBR-IP-007` 只做**信号级**筛查（图片上的版权声明/水印），不认定侵权。

### 3.3 Lei nº 8.078/1990（消费者保护法）

误导性广告与夸大宣称受消费者保护法规制；这与平台码 [337]（"promessas exageradas ou milagrosas"，Média，扣分）和 [405]（"Propaganda Enganosa"）一致。

---

## 4. 规则库如何映射到调研结果

47 条规则分四个文件：

| 文件 | 规则数 | 覆盖 |
|---|---|---|
| `rules/01_prohibited_restricted_items.json` | 17 | 禁售（9 类）+ 受限（8 类） |
| `rules/02_ip_trademark_copyright.json` | 8 | 商标 / 著作权 / 外观设计 + **兼容性反误判规则** |
| `rules/03_listing_violations_duplicates.json` | 17 | listing 质量违规 + 重复刊登 + 跨店同款 + 重发冻结 |
| `rules/04_cases_relist_authorization.json` | 5 | 案件关联、授权资料、处罚点与申诉 |
| `rules/05_medicines_health.json` | 3 | 药品禁售类目、2026-08-06 Anvisa 新规、保健品宣称 |

**决策权限设计**（`src/compliance_agent/engine/evaluator.py`）：

1. 只有 `status == "active"` **且** `source_tier ∈ {platform_official, law}` 的规则才可能产生 `block`。
2. `internal_risk` / `unverified` / `draft` 规则最多只能产生 `flag_for_review`。
3. IP 类规则（`ip_trademark` / `ip_copyright` / `ip_design`）**永远**标记为 `confidence: "signal"` 且 `human_review_required: true` —— 关键词或 logo 命中只是**筛查信号**，只有权利人投诉或书面授权才能认定侵权。
4. 存在兼容性表述时，IP 命中的置信度被降级并在说明中附上反误判依据。

---

## 5. 待核实问题

### 5.1 阻断性（影响规则可信度）

| # | 问题 | 影响 | 建议动作 |
|---|---|---|---|
| Q1 | **Seller Centre 后台的违规通知/申诉界面未采集**（需登录态） | 无法自动化「平台通知 → 案件」的入库 | 用真实账号导出违规记录页，或人工整理成 `cases.json` 交给 agent |
| Q2 | **Anvisa RDC 96/2008 与 RDC 44/2009 抓取失败（503）** | 药品/保健品类宣称与处方药禁售规则缺一手来源 | 换用 `antigo.anvisa.gov.br` 或 `in.gov.br` 镜像重抓 |
| Q3 | **平台处罚点具体数值表未采集** | 规则里只有「哪些违规扣分」，没有「扣几分」 | Seller Centre「Desempenho da Conta」页需登录；本项目暂不推断分值 |
| Q4 | **限制类目 OKlist 名单**（如 "Turbo - Alimentos Frescos"）未结构化 | 受限放行判定不精确 | 抓取 `seller.shopee.com.br` 的受限类目清单页 |
| Q5 | **Resolução-RE nº 3.056/2026 的具体要求未采集** | `SBR-MED-002` 只能要求「药店牌照」，无法判断某个卖家的牌照是否满足 MIP 销售条件 | 查 Anvisa 官网该决议原文 |

### 5.2 非阻断性（可后补）

| # | 问题 | 现状处理 |
|---|---|---|
| Q6 | 重复刊登的平台判定阈值不公开 | 采用自己的相似度阈值（标题 trigram Dice + Jaccard + 供应商 SKU），**标记为候选而非结论** |
| Q7 | 106 条违规码中部分码无中文/英文对照 | 保留葡语原文，避免翻译走样 |
| Q8 | 「跨店同款」是否算平台违规 | 平台只管「同店重复刊登」（[401]/[302]）；跨店同款本项目按 **内部风控** 处理，标 `source_tier: platform_official` 但只产生 `flag_for_review`，不阻断 |
| Q9 | 图片 OCR / logo 识别未接入 | `SBR-IP-005`/`SBR-IP-008` 目前不会触发（图片列表为空）。**引擎不会把「没有图片」当作通过** —— 见 §6 |

### 5.3 明确不做的事

- **不编造平台政策**。每条规则的 `source_excerpt` 必须逐字出现在抓取件中，否则 `tools/verify_citations.py` 判失败。
- **不把疑似侵权认定为侵权**。IP 规则一律 `confidence: "signal"` + 强制人工复核。
- **不推断处罚分值**。平台未公开或需登录才可见的数值不写入规则库。

---

## 6. 一个重要的设计决定：区分「没有数据」与「不合规」

第一版实现在演示导出（15 条合成商品）上把 **15/15 全部标记为违规**，原因有三：

- `SBR-LV-007`（无图片 → 违规 [606]）
- `SBR-LV-008`（无类目 → 违规 [613]）
- `SBR-LV-011`（无品牌 → 违规 [301]）

但那个 xlsx **根本没有图片列、类目列、品牌列**。这是**输入数据缺失**，不是**listing 违规**。

修正方案：规则的 trigger 条件可声明 `requires_input: ["image"]`。若输入里该字段根本没有，该条件**不评估**，并作为 `warning` 写入结果的 `errors` 数组：

```
rule SBR-LV-007 was not evaluated: the input carried none of the required field(s) image
```

修正后同一批数据的结论变为：**2 阻断、4 待复核、9 通过、3 项未评估**。未评估项在报告里是可见的缺口，不是沉默的通过。

---

## 7. 复现方式

```bash
cd shopee-br-compliance-agent

# 抓取/刷新官方来源（Seller Centre 页面需无头 Chromium 执行 SPA）
env -u LD_LIBRARY_PATH python3 tools/fetch_sources.py
env -u LD_LIBRARY_PATH python3 tools/fetch_edu_articles.py research/edu_articles.json

# 解析平台违规码目录
env -u LD_LIBRARY_PATH python3 tools/parse_violation_codes.py

# 校验：Schema、引用逐字核验、测试
env -u LD_LIBRARY_PATH python3 tools/validate_json.py --schema data/schema/rule_collection.schema.json rules/
env -u LD_LIBRARY_PATH python3 tools/verify_citations.py
env -u LD_LIBRARY_PATH python3 tests/run_tests.py

# 端到端演示
env -u LD_LIBRARY_PATH python3 scripts/make_demo_export.py data/samples/demo_mass_update.xlsx
env -u LD_LIBRARY_PATH python3 scripts/review.py --input data/samples/demo_mass_update.xlsx --shop-id SHOP1 --out out/
```

当前状态：**Schema 校验 0 错误 0 警告；引用逐字校验 50/50 通过；测试 333 项全通过。**
