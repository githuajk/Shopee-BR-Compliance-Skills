# 人工审核操作手册（Shopee BR 商品合规）

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-SOP-MANUAL-001` |
| 版本 | 1.0.0 |
| 状态 | **Draft — 待用户审批** |
| 创建/更新 | 2026-10-28 |
| 面向对象 | **人工审核员** —— 纯手工，不需要看代码、不需要跑脚本 |
| 适用范围 | Shopee 巴西站商品标题与详情的**人工合规审核** |
| 判定依据 | 全部来自 `rules/*.json`（50 条规则）、`lexicon/*.json`、`research/violation_codes.json`（106 个平台处罚码） |
| 配套文档 | `docs/USER_SOP.md`（整体流程框架）、`docs/SOP_COMPLIANCE_REVIEW.md`（判定原理） |

---

## 0. 这份手册怎么用

**不需要跑任何工具。** 你只需要：打开商品 → 对着清单看 → 记结论。

三条线：

| 线 | 你在做什么 | 用哪几节 |
|---|---|---|
| **主线** | 逐个商品从头审到尾 | §1 顺序 → §2 标题 → §3 详情 → §4 图片 → §5 属性 |
| **判断线** | 看到一个词，判它是不是违规 | §6 关键词判定表（核心） |
| **处置线** | 判完之后怎么办 | §7 处置决策 → §8 改写标准 → §9 豁免（不要误伤） |

**一句话记住全流程**：

> **先看标题 → 再看详情 → 看图 → 看属性 → 命中词就查 §6 判定表 → 按 §7 定处置 → 改写按 §8 标准**

---

## 1. 审核顺序（照着走，不要跳）

```
① 标题  →  ② 详情  →  ③ 图片  →  ④ 属性/类目/品牌  →  ⑤ 跨店重复
```

### 为什么标题排第一

标题是平台最先扫的字段，也是最容易被下架的字段。**标题里出现禁售品类词 = 直接不上架**，不用往下看了。

### 第一步：先分类目（30 秒，决定后面用哪张表）

| 看到这些词 | 类别 | 去查 |
|---|---|---|
| 化妆品 / batom / base / sérum / hidratante / pó / protetor solar | **化妆品** | §8.3 化妆品专属 |
|Battery / pilha / bateria / power bank | **电池** | §6.2 受限类 |
| 汽车 / peça automotiva / óleo / filtro / pastilha | **汽配** | §6.2 受限类 |
| 酒 / cerveja / vinho / destilado | **酒类** | §6.2 受限类 |
| 药 / remédio / suplemento / vitamina | **药品保健品** | §6.2 + §8.3 |
| 宠物药 / antiparasitário / vacina pet | **兽药** | §6.2 |
| 太阳镜 / óculos de sol | **太阳镜** | §8.3（INMETRO） |
| 母婴 / carrinho / trava infantil / cesto de bebê | **儿童安全** | §8.3（INMETRO） |
| 其他 | **普通商品** | 通用清单 |

> **同一个词在不同类别意思完全不同。** 比如 `Cura`（治愈）在化妆品里是违规宣称，在化工产品里可能只是描述。**先定类别，再判词。**

---

## 2. 标题检查清单

**标题是最容易中招的地方。** 逐条看：

| # | 检查什么 | 什么算不合格 | 严重度 |
|---|---|---|---|
| 2.1 | **禁售品类词** | 武器/烟草/毒品/化学品/赌博/证件/野生动物/成人 | 🔴 致命 → 不上架 |
| 2.2 | **品牌名** | 标题里出现别的品牌（Nike / Adidas / Apple / Samsung / Gucci…） | 🟡 要查授权 |
| 2.3 | **品牌堆砌** | 标题里塞了 2 个以上品牌 | 🟢 低（[507]） |
| 2.4 | **关键词堆砌** | 标题是一长串不相关词；或标题超过约 120 字符 | 🟢 低（[506]） |
| 2.5 | **形态词矛盾** | 同时出现 3 个以上形态词（pomada / creme / gel / spray / sérum / máscara / pó / óleo…） | 🟡 需核实实物 |
| 2.6 | **年龄不符** | 标题写 `infantil` / `kids` 但实际是成人用品；或反之 | 🟢 低（[510]） |
| 2.7 | **功效承诺** | `cura` / `garantido` / `elimina` / `milagroso` / `emagrece` / `resultado garantido` | 🟡 要改（[337]） |
| 2.8 | **时间承诺** | `resultado em 30 dias` / `em 2 semanas` | 🟡 要改 |
| 2.9 | **英文残留** | 标题或详情里有英文（Anti-Aging / Firming / Wrinkles / Lifting…） | 🟡 要改 |
| 2.10 | **葡语错误** | 重音错、拼写错、逗号写成小数点 | 🟡 要改 |
| 2.11 | **末尾悬空** | 标题最后一个词是 `de` `da` `para` `com` `vi` `pa` 这类断词 | 🟡 要改 |
| 2.12 | **GTIN / 编号** | 缺 GTIN 或货号（平台要用来比重复） | 🟢 低（[307]） |

### 标题的合格标准

| 项 | 标准 |
|---|---|
| 长度 | 60–95 字符（**不超过 120**） |
| 结构 | 空格分隔关键词，**不要用分隔逗号** |
| 数字 | 葡语小数用逗号：`19x2,5cm`（不是 19x2.5cm） |
| 形态词 | 最多 1–2 个，与实物一致 |
| 品牌 | 只有真能用才写，且最多 1 个 |
| 结尾 | 不能是悬空断词 |

---

## 3. 详情检查清单

| # | 检查什么 | 什么算不合格 | 严重度 |
|---|---|---|---|
| 3.1 | **长度** | 少于 120 字符 → 平台直接判"描述不足" | 🟡 中（[605] **扣分**） |
| 3.2 | **长度** | 剥掉模板和链接后少于 250 字符 → 内容太薄 | 🟡 要补充 |
| 3.3 | **长度** | 少于 500 字符 → 缺"使用方法"和"包装内容"两段 | 🟡 要补充 |
| 3.4 | **功效承诺** | `cura` `garantido` `garantia` `eficaz` `elimina` `definitivo` `total` `milagroso` `emagrece` `resultados garantidos` | 🟡 要改（[337]） |
| 3.5 | **疾病宣称** | 出现具体病名：`psoríase` `eczema` `dermatite` `acne` `manchas` `queda de cabelo` `cravos` | 🟡 要改 |
| 3.6 | **医疗词** | `medicamento` `antisséptico` `antibacteriano` `anti-inflamatório` `analgésico` `antidepressivo` `ansiolítico` `terapêutico` | 🟡 要改或删 |
| 3.7 | **绝对化用语** | `100%` `original` `melhor` `o mais` `total` `para todos` `todos os tipos` | 🟡 要改 |
| 3.8 | **商标词** | 品牌名出现（除非是兼容说明） | 🟡 要查授权 |
| 3.9 | **外链/导流** | 网址、WhatsApp、Telegram、"请加微信"、站外联系方式 | 🟡 中（[112]） |
| 3.10 | **残留话术** | 店铺名、客服话术、物流话术（`Bem-vindos à loja...` / `Nossa equipe...` / `Os pedidos são preparados...`） | 🟡 要删 |
| 3.11 | **图片链接** | 详情里塞了店铺图片 URL（`cf.shopee.com.br/file/...`） | 🟡 要删 |
| 3.12 | **中文残留** | 任何中文字符 | 🟡 要删 |
| 3.13 | **法语残留** | `nécessaire` `obligatoire` `déjà` `très bien` | 🟡 要删 |
| 3.14 | **翻译机器味** | 单词粘连：`uniformementeizar` `aplicaruniformemente` `parauniformizar` | 🟡 要改（见 §8.5） |
| 3.15 | **空洞宣称** | `Material premium` `Acabamento cuidadoso` `Confortavel` `Produto de alta qualidade` | 🟡 要改成具体描述 |
| 3.16 | **产地统一** | 所有商品都写 `Origem: China` | 🟡 要按实物改 |
| 3.17 | **类目模板** | 首饰/工具类却写 `Tipo: Cosmético` | 🟡 要改 |
| 3.18 | **测试宣称** | `Testado dermatologicamente` | 🟡 要删（无证据） |
| 3.19 | **拼写错误** | 葡语拼写错、双空格、缺空格 | 🟡 要改 |
| 3.20 | **残句** | `para auxilia` / `A design` / `rotina de rotina` / `uso geral e uso doméstico` | 🟡 要改 |

### 详情的合格标准

**必须按这六段写，顺序固定：**

```
1. Descrição            —— 首句 = 商品名 + 具体用途
2. Características      —— 用 • 分条，每条一个卖点
3. Especificações        —— 尺寸 / 容量 / 材质 / 适用
4. Modo de uso           —— 怎么用
5. Conteúdo da embalagem —— 包装里有什么
6. Cuidados importantes  —— 注意事项 + 适用年龄 + 不替代专业建议
```

**首句必须含商品实词：**

| ✅ 合格 | ❌ 不合格 |
|---|---|
| `Saco de malha transparente para organizar livros e materiais.` | `Item para organizar a rotina, com capacidade ampla e alça confortável.` |
| `Suporte de pia fixado na parede para esponjas e utensílios.` | `Produto versátil para o dia a dia.` |

---

## 4. 图片检查清单

| # | 检查什么 | 什么算不合格 | 严重度 |
|---|---|---|---|
| 4.1 | **数量** | 少于 1 张 | 🟢 低（[606]） |
| 4.2 | **质量** | 模糊、纯白底无商品、与商品无关 | 🟢 低（[606]） |
| 4.3 | **第三方 logo** | 图里有别的品牌 logo、字标、压印 | 🟡 要查授权 |
| 4.4 | **Shopee logo** | 用了 Shopee 的 logo 或 banner | 🟡 中（[608]） |
| 4.5 | **外卖平台 logo** | 背包/袋子上有 iFood / Rappi / delivery app 的 logo | 🟡 中（[349]） |
| 4.6 | **版权图** | 用了盗图、带水印、"todos os direitos reservados" | 🟡 要换（[602]） |
| 4.7 | **工业设计** | 外形抄袭了注册外观设计 | 🟡 转法务（[603]） |

> **图片里的 logo 是独立触发条件** —— 即使标题和详情都干净，图上有别人的 logo 一样会被下架。

---

## 5. 属性 / 类目 / 品牌检查清单

| # | 检查什么 | 什么算不合格 | 严重度 |
|---|---|---|---|
| 5.1 | **类目正确** | 选错类目（尤其受限品放错类目） | 🟢 低（[613]/[612]） |
| 5.2 | **品牌准确** | 品牌字段空、或与实际不符 | 🟢 低（[301]） |
| 5.3 | **尺寸重量** | 尺寸重量没填、填错 | 🟢 低（[120]） |
| 5.4 | **尺寸超限** | 超出 Shopee 允许的重量/尺寸 | 🟡 中（[508]/[509]） |
| 5.5 | **注册信息** | 化妆品/电器/汽车件/医疗器械缺 ANVISA / ANATEL / INMETRO / MAPA 注册号或认证 | 🟡 要补证（[503]-[505]） |
| 5.6 | **年龄等级** | 年龄段和类目/标题对不上 | 🟢 低（[510]） |
| 5.7 | **变体滥用** | 变体里塞价格/规格混乱数据 | 🟢 低（[309]） |
| 5.8 | **变体尺寸** | 变体带不准确的尺寸重量 | 🔴 致命（[517]） |
| 5.9 | **GTIN** | 缺 GTIN | 🟢 低（[307]） |

### 跨店 / 重复检查（如果有多个店铺）

| # | 检查什么 | 说明 | 严重度 |
|---|---|---|---|
| 5.10 | **同店重复** | 同一店两个商品内容几乎一样 | 🟡 中（[401]） |
| 5.11 | **跨店重复** | 同款商品在多个店铺都上了（**包括你自己家的店**） | 🟡 中（[302]） |
| 5.12 | **换皮重发** | 之前被下架的商品，改个标题或换 SKU 重新上 | 🔴 冻结重发（[401]） |
| 5.13 | **未结案件** | 商品还挂在未关闭的违规案件上 | 🟡 中 |
| 5.14 | **已被删** | 商品是平台删掉的，删掉不可恢复 | 🔴 冻结重发 |
| 5.15 | **处罚点** | 账号有处罚点 | 🟡 要查 |
| 5.16 | **申诉中** | 处罚点申诉还没到期 | 🟡 别重发 |

---

## 6. 关键词判定表（核心）

**这是审核员最常用的一张表。** 看到一个词 → 查这里 → 定结论。

### 6.1 禁售类（🔴 致命 —— 不上架）

| 品类 | 关键词（葡语） | 平台码 | 备注 |
|---|---|---|---|
| **武器** | arma de fogo, revólver, pistola, escopeta, taser, colete à prova de balas, munição | [317] | **菜刀/剪刀/螺丝刀/美工刀不算**（见 §9） |
| **烟草电子烟** | cigarro, charuto, cachimbo, tabaco, vape, juice, nicotina, narguil, pods, atomizador | [311] | 电子烟配件也禁 |
| **毒品管制药** | droga, medicamento controlado, tarja preta, tarja vermelha, aborto, abortivo, injetável, estimulante sexual, antidepressivo, minoxidil | [313] | 分红标/黑标 |
| **化工易燃爆炸** | explosivo, nitrogênio, gasolina, diesel, acetona, produto químico bruto, corrosivo, trinitrotolueno | [332] | |
| **假币证件** | dinheiro, real, nota, cartão, clonador, jammer, documentos falsificados | [341] | |
| **赌博数字商品** | jogo de azar, loteria online, aposta, caixa misteriosa, itens digitais | [338] | |
| **政府徽章制服** | insígnia, brasão, uniforme militar, policial, item oficial governamental | [516] | |
| **野生动物** | animais vivos, partes de animais selvagens, espécies ameaçadas, fauna, flora | [339] | |
| **成人内容** | pornográfico, conteúdo adulto, sexo, explícito | [320] | |
| **未巴氏消毒乳制品** | leite cru, queijo artesanal, iogurte artesanal, manteiga artesanal | [342] | 工业巴氏杀菌密封装**可以** |

### 6.2 受限类（🟡 要资质 —— 缺证就不能上）

| 品类 | 关键词 | 平台码 | 需要什么资质 |
|---|---|---|---|
| **酒类** | cerveja, vinho, whisky, conhaque, aguardente, champanhe, destilado, licor, bebida alcoólica | [325]/[342] | 酒类销售文件；**自酿酒直接禁** |
| **健康用品保健品** | suplemento, vitaminas, monitor de pressão, aparelho médico, ortopédico, teste | [312] | 卫生监管注册 |
| **电池充电宝** | pilha, bateria alcalina, recarregável, power bank | [333] | 运输安全要求 |
| **汽配** | componente automotivo, peça de carro, homologação | [132]/[343]/[344] | Inmetro/Anatel 认证；**二手/翻新件禁**。注意：[132] 扣分，[343]/[344] 不扣分 |
| **生鲜冷冻食品** | alimento fresco, congelado, frutas, verduras, carne | [331] | 必须密封包装 |
| **兽药** | medicamento pet, veterinário, antiparasitário, vacina, vermífugo | [334] | MAPA 资质 |
| **气枪/彩弹** | airsoft, paintball, arma de pressão, equipamento tático | [315] | |
| **人用药** | medicamento, isento de prescrição, remédio, tarja | [313]/MED | **2026-08-06 起只有持牌药店/药店类店铺能卖 MIP** |

### 6.3 功效宣称类（🟡 要改 —— [337] 中等严重度，**扣分**）

| 触线词 | 为什么不行 | 改成 |
|---|---|---|
| `cura` / `curar` / `curativo` | 医疗宣称 | `cuidados com a pele` / `auxilia em` |
| `garantido` / `garantia` / `garante` | 绝对承诺 | `pode auxiliar` / `auxilia em` / `pode oferecer` |
| `eficaz` / `eficiente` | 功效宣称 | 去掉，或改成具体描述 |
| `elimina` / `eliminar` | 绝对效果 | `auxilia a reduzir` |
| `definitivo` / `definitiva` | 绝对效果 | 去掉 |
| `total` / `completamente` | 绝对化 | 去掉 |
| `milagroso` / `milagrosa` | 奇迹宣称 | 去掉 |
| `resultado garantido` / `resultados garantidos` | 结果承诺 | 去掉 |
| `emagrece` / `emagrecimento` | 减重宣称 | 删除 / 改成 `design` |
| `redutor de medidas` | 塑形宣称 | 删除 |
| `anti-idade` / `antirrugas` | 抗衰宣称 | `cuidados com a pele` |
| `clareador` / `clareamento` | 美白宣称 | `esfoliante` |
| `lifting facial` | 医美宣称 | `tratamento` |
| `cicatrizante` | 医疗宣称 | `cuidados com a pele` |
| `anti-inflamatório` | 医疗宣称 | `calmante para a pele` |
| `analgésico` | 医疗宣称 | `relaxante` |
| `antidepressivo` / `ansiolítico` | 精神类药物 | **删除** |
| `antisséptico` / `antibacteriano` | 医疗宣称 | `higiênico` |
| `terapêutico` | 医疗宣称 | `tratamento`（慎用） |
| `antifraude` | 误导 | `decorativo` |
| `antiembaçante` | 宣称 | `antivisão embaçada` |
| `resultado em 30 dias` / `em N dias` | 时间承诺 | 去掉 |
| `100%` / `original` / `produto original` | 绝对化 / 真伪无据 | 去掉 |

### 6.4 疾病名类（🟡 要改 —— 只要出现具体病名就删）

| 词 |
|---|
| `psoríase` `eczema` `dermatite` `acne` `manchas` `cravos` `queda de cabelo` `cólera` `fungos` `bactérias` `vírus` `germes` |

> `bactérias` `vírus` `germes` → 改成 `microrganismos`。

### 6.5 营销/绝对化类（🟡 要改）

| ❌ | ✅ |
|---|---|
| `mais vendido` / `best seller` | `um dos mais procurados` |
| `alta qualidade` / `qualidade premium` | 具体描述（材质、工艺、参数） |
| `melhor do mercado` | 删 |
| `frete grátis` | 删（Shopee 自带） |
| `produto original` | 删 |
| `para todos os tipos de pele` | 按说明书写适用人群 |
| `testado dermatologicamente` | 删（除非有报告） |

### 6.6 侵权类（🟡→🔴 要查授权）

**高风险品牌（举例）**：Nike, Adidas, Puma, Samsung, Apple, Xiaomi, Sony, Dyson, Lululemon, Supreme, Rolex, Gucci, Louis Vuitton, Versace, Ford, Toyota, Volkswagen, Chevrolet, Fiat, Huawei, Amazon, Natura, Boticário, Avon, Lancôme, L'Oréal, Disney, Marvel, Pokemon, Sanrio, Lego, Nintendo

| 情况 | 判定 |
|---|---|
| 品牌名用在标题/详情做商品标识 | 🔴 需授权，否则 [133] 下架 |
| 明写 `réplica` `contrafé` `falso` `falsificado` `cópia não autorizada` `pirata` `look alike` `inspired` | 🔴 直接定性，[602]/[603] |
| 图片上有别人 logo | 🟡 查授权 |
| 写 `compatível com X` / `para X` / `modelo compatível` | ✅ **不是侵权**（Lei 9.279/1996 art. 132 II 指示性使用） |
| 品牌名是产品通用词（vidro, maleta, case, bolsa, cabide…） | 🟡 看上下文，默认按侵权 |

### 6.7 标题质量类（🟢 低 —— 不扣分但会被下架）

| 情况 | 平台码 |
|---|---|
| 关键词堆砌 | [506] |
| 品牌堆砌 | [507] |
| 描述不足（<120 字符） | [605] 中等，**扣分** |
| 图片差/缺图 | [606] |
| 类目错误 | [613] / [612] |
| 品牌字段不准 | [301] |
| 尺寸重量不准 | [120] |
| 变体数据滥用 | [309] |
| 引导站外 | [112] 中等 |
| 误导折扣/划线价 | [105] / [405] |

---

## 7. 处置决策（判完之后怎么办）

### 7.1 严重度 → 动作对照

| 严重度 | 平台说法 | 扣处罚点 | 你该做什么 |
|---|---|---|---|
| 🔴 **致命** Extrema | 枪支、毒品、赌博、假证、成人、野生动物 | ✅ 扣 | **不上架**。有疑问先问 |
| 🔴 **高** Alta | ANVISA/ANATEL/Inmetro 禁限、烟酒药、汽配无认证、图片侵权 | ✅ 扣 | **先查资质**，无资质不上架 |
| 🟡 **中** Média | 描述不足、受限品违规、站外导流、超重 | ✅ 扣 | **必须改**；改不了就下架 |
| 🟢 **低** Baixa | 标题堆词、类目错、品牌错、图片差、重复 | ❌ 不扣 | **能改就改**；不改也能留 |

> **扣处罚点 ≠ 立刻封号。** 但致命和高危类反复出现，会累积到账号处罚带，限制持续 14–28 天。**致命类一次都不能漏。**

### 7.2 处置四选一

| 情形 | 动作 |
|---|---|
| **改文案能解决**（功效宣称、空洞描述、模板化） | **改写**，按 §8 |
| **缺资质**（化妆品没 ANVISA 号、汽配没认证） | **出工单**，不批量改写 |
| **本体违规**（自酿酒、生鲜未密封、枪支） | **不上架**，报店主 |
| **没把握** | **挂"待复核"**，不要自己拍板 |

### 7.3 下架红线（★）

> **没有店主对具体商品的明确同意，不要下架任何商品。**

| 你可以做 | 你不可以做 |
|---|---|
| 列出建议下架清单（行号 + 触线词 + 严重度） | 直接把商品删掉 |
| 在报告里标"建议下架" | 因为"规则说要禁"就自己下架 |
| 说"这 3 个建议不上架" | 顺手把"看起来差不多"的也删了 |

**清单模板**：

```
建议下架（待店主确认）：
  行 20  | à prova d'água      | 标题禁售宣称  | 致命
  行 74  | Retinol              | 标题药品词    | 高
  行 101 | Resultado em 30 dias | 时间承诺      | 中
```

### 7.4 工单模板（缺资质类）

```
商品：行号 47 | SKU xxxx
缺什么：ANVISA 注册号
依据：SBR-LV-009（[503] sem informação de registro）
建议：补证后上架；无证则下架
```

---

## 8. 改写标准（要改成什么样）

### 8.1 改写优先级

```
1. 删掉违规承诺（最容易见效）
2. 换掉医疗/药品词
3. 把绝对化改成具体描述
4. 把空洞宣称换成实参数
5. 补齐六段结构
6. 修正葡语拼写和重音
```

### 8.2 触线 → 中性 替换表（可直接抄）

| 触线 | 改成 |
|---|---|
| garante / garantido / garantia | pode auxiliar / auxilia em / pode oferecer |
| Anti-Idade / Antirrugas | Cuidados com a pele |
| clareador / clareamento | esfoliante |
| Lifting Facial | Tratamento |
| Cicatrizante | Cuidados com a pele |
| Anti-inflamatório | Calmante para a pele |
| Analgésico | Relaxante |
| Antidepressivo / Ansiolítico | 删除 |
| Antisséptico / Antibacteriano | Higienico |
| Terapêutico | tratamento（慎用） |
| bactéria / vírus / germes | microorganismos |
| pós-cirúrgica | fase de cuidado / uso doméstico |
| veterinária | especialista em pets |
| Curativo | Adesivo |
| Joanete / Martelo | Dedos |
| Medicamento / uso tópico | 删除 / uso externo |
| reembolso / troca grátis | 全删 |
| 100% garantido / 100% seguro | 全删 |
| Antifraude | Decorativo |
| Antiembaçante | Antivisão Embaçada |
| proporcionar（各种变位） | facilitar |
| emagrece / modela | 删除 / design |
| Redutor de medidas | 删除 |

### 8.3 品类专属改写标准

**化妆品**

| ❌ | ✅ |
|---|---|
| `Anti-idade` `Rugas` `Firming` `Lifting` `Rejuvenescimento` | `Cuidados com a pele` |
| `Cura acne` `Elimina manchas` | `Auxilia na rotina de skincare` |
| `100% seguro` `Garantido` | `Pode auxiliar` |
| `Todos os tipos de pele` | `Pele normal a seca`（按实物） |
| `Testado dermatologicamente` | 删 |
| `Tipo: Cosmético` | `Cosmético`（按真实类别） |

**不能靠改文案解决的**：化妆品必须有 **ANVISA 注册号**。把 "Anti-idade" 改成 "Cuidados" 解决不了这个问题。**没注册号就不上架**，不管文案改得多干净。

**汽配**

| ❌ | ✅ |
|---|---|
| `Homologado`（无认证号） | 删，或写实际认证机构 |
| `Original` `Novo`（描述来源不明） | 删 |

> **注意**：汽配/工业品类里，`Cura` `Tratamento` `Profissional` `Substitui` `Firma` `Inspeção` `Certificação` 这些词在**化工和免责声明语境里是正常的** —— 别误伤。详见 §9。

**药品保健品**

| ❌ | ✅ |
|---|---|
| `Cura` `Emagrece` `Garantido` `Eficaz` | `Pode auxiliar` |
| `tarja` `prescrição` `controlado` | 删除 |
| 具体病名 | 删除 |
| `100% natural` | 删 |

**太阳镜**

- ❌ `UV400` `Proteção UV` `lente escura`
- ✅ 去掉数字宣称，写 `com lentes escuras`
- ⚠️ **但实质合规要 INMETRO 的 UV 实测报告** —— 文字改过只是文字层过关。

**儿童安全用品**

- ❌ 直接承诺安全
- ✅ 加 `Uso com supervisão de um adulto`
- ✅ 加 `Não use por menores de [X] anos`
- ⚠️ **实质要 INMETRO 认证**

### 8.4 反模板化：改写后必须自己看一遍

**下面的现象任一出现，说明这批改写是套模板的，必须重做：**

| 现象 | 为什么是问题 |
|---|---|
| 同一句话在一批商品里出现 5 次以上 | 批量味 |
| 两个商品的详情**一字不差** | 最严重的问题 |
| `✅` 出现 4 次以上 | 套模板 |
| 同一句 `Quer X mais forte` 反复出现 | 套模板 |
| 首句不含商品实词 | 空泛 |
| 标题里同时有 3 个以上形态词 | 矛盾 |

> **首句唯一率必须 100%。** 不是"首句种类数"达标就行 —— 111 种 vs 245 条商品，人工看过去还是模板。

**首句要写成这样：**

```
✅ Saco de malha transparente para organizar livros e materiais.
✅ Suporte de pia fixado na parede para esponjas e utensílios.
✅ Kit de 4 potes de vidro com tampa para guardar temperos.
❌ Item para organizar a rotina, com capacidade ampla e alça confortável.
❌ Produto versátil que atende às suas necessidades.
```

### 8.5 翻译机器味（改写后逐条检查）

改写工具常见错误 —— **单词粘在一起**：

| 错误 | 改成 |
|---|---|
| `uniformementeizar` | `uniformizar` |
| `uniformementeemente` | `uniformemente` |
| `aplicaruniformemente` | `espalhar uniformemente` |
| `espalharuniformemente` | `espalhar uniformemente` |
| `distribuiruniformemente` | `distribuir uniformemente` |
| `parauniformizar` | `para uniformizar` |
| `euniformemente` | `e uniformemente` |
| `pressãouniformemente` | `pressão uniformemente` |
| `v[íi]trees` | `vidros` |
| `produtouniformementemente` | `produto uniformemente` |
| `eelasticidade` | `elasticidade` |

> ⚠️ **`proporcional` 不算错** —— 它是形容词，正常词，别去动它。

**残句**（改写工具留下的病句）：

| 错误 | 改成 |
|---|---|
| `para auxilia` | `para auxiliar` |
| `A design` / `a design` | `O design` / `o design` |
| `rotina de rotina` | `rotina` |
| `Conforto e Conforto` | `Conforto` |
| `Cintura Alta Cintura` | `Cintura Alta` |
| `cuidado com a pele com cuidado` | `cuidado com a pele` |
| `uso geral e uso doméstico` | `uso doméstico` |
| `garantir maior` | `buscar maior` |
| `garantir que` | `para que` |
| `beaconchegante` | `e aconchegante` |
| `permitevariados` | `permite variados` |
| `leitidas` | `lidas` |

**还有一类：批量替换把并列结构打出了空洞**

```
❌ Adequado para, e todos os tipos de.
❌ Adequado para,, palmas manchadas, ...,,,,,, auxilia nos cuidados...,, 
```

> 这种病句规则救不了 —— **整段手工重写。**

### 8.6 葡语重音速查（常见错）

| 错 | 对 |
|---|---|
| pratico | prático |
| confortavel | confortável |
| diario | diário |
| especificacoes | especificações |
| aplicacao | aplicação |
| tendencia | tendência |
| hidratacao | hidratação |
| oleo | óleo |
| serum | sérum |
| mascara | máscara |
| E original | É original |
| frequencia | frequência |
| experiencia | experiência |

**格式**

| 项 | 标准 |
|---|---|
| 容量 | `30ml` `50g`（小写） |
| 防晒 | `FPS 15`（葡语用 FPS 不是 SPF） |
| 时长 | `12 horas`（葡语用复数） |
| 货币 | `R$ 99,90` |
| 小数 | 逗号：`19x2,5cm` |

### 8.7 改完必须做的 3 件事

| # | 动作 | 为什么 |
|---|---|---|
| 1 | **从头再读一遍改后的详情全文** | 扫描器数字归零 ≠ 内容正确 |
| 2 | **再搜一遍刚才删掉的词** | 改写会引入新违规词 |
| 3 | **检查自己刚改的地方** | 你的修改本身可能是下一个错误 |

> **真实事故**：一条没有边界的替换规则把 `Separador` 改成了 `Separadesconforto`；一句自己手写的安全提示（`não substitui acompanhamento profissional`）触发了违规词典。**改完必须再看一遍。**

---

## 9. 豁免清单（不要误伤）

**看到这些词不要直接判违规。** 误伤比漏判更常见，也更伤商品。

| # | 情况 | 正确处理 |
|---|---|---|
| 9.1 | **工具类**：faca, facas, tesoura, tesouras, chave de fenda, chave phillips, alicate, estilicho, multiplasca, canivete | ✅ **豁免**，不算武器 |
| 9.2 | **CE 标志事实陈述**：`produto impresso com selo CE` | ✅ 记录但不拦截 |
| 9.3 | **Hermes 出现在物流语境**：entrega / transportadora / expresso / frete / logística + Hermes | 🟡 默认按侵权，**看上下文** |
| 9.4 | **`reduzir`**：`reduzir a entrada de água` `reduzir escorregões` | ✅ 功能描述，保留 |
| 9.5 | **`desconforto`**：`em caso de desconforto, suspenda o uso` | ✅ 安全提示，保留 |
| 9.6 | **`seguro` 作功能**：`fechamento seguro` `encaixe seguro` `trava segura` `suporte seguro` `fixação segura` | ✅ 功能描述，保留 |
| 9.7 | **品牌名是通用词**：vidro, maleta, case, bolsa, cabide, suporte, organizador, abertura, fechadura | 🟡 看上下文，**默认仍按侵权** |
| 9.8 | **兼容说明**：`compatível com X` `para X` `modelo compatível` | ✅ **不是侵权**（Lei 9.279/1996 art. 132 II） |
| 9.9 | **汽配/工业语境**：`Cura` `Tratamento` `Profissional` `Substitui` `Firma` `Inspeção` `Certificação` | ✅ 化工术语和免责声明，**不是**医疗宣称 |

> **第 9.9 条特别重要。** 这六个词在化妆品里是违规宣称，在汽配和化工里是正常术语。**先定类别再判词**（§1）。

> **误报控制的价值高于"扫描器数字归零"。** 把 `desconforto`、`seguro` 这些安全提示和功能描述全改掉，会让详情读起来像机器人，还降低了合规性。

---

## 10. 无法靠改文案解决的（出工单，不要批量改）

**这些商品的合规性由商品本体决定，改文案无效。**

| 品类 | 监管方 | 关键词 | 需要什么 |
|---|---|---|---|
| **化妆品** | ANVISA | cosmético, batom, base, sérum, hidratante, desodorante, pó facial, protetor solar, sabonete facial | ANVISA 注册号 + 责任主体 |
| **器械/矫形** | ANVISA | joelheira, cotoveleira, compressa, cinta abdominal, tala, aparelho de pressão, massageador, furo auricular | 器械注册与资质 |
| **宠物口腔** | MAPA | escova dental pet, spray bucal pet, espuma dental pet, tártaro pet, halitose pet | 兽药资质，或改成纯清洁宣称 |
| **化学制剂** | ANVISA | cola, epoxy, resina, primer, selante, cera automotiva, solução de limpeza, vedante, espuma expansiva, desengraxante | 包装含成分/警示/批号/有效期 |
| **太阳镜** | INMETRO | óculos de sol, lente escura | UV 实测报告 + 认证 |
| **儿童安全** | INMETRO | trava de segurança infantil, protetor de canto, bloqueador de roda, cesto de bebê, cadeira de bebê | INMETRO 认证 |

**处理流程**

```
命中 → 是上表品类吗？
  是 → 出工单（行号 + 缺什么资质 + 建议）→ 不进批量改写
  否 → 进改写流程 → 改完重读 → 抽样人工读
```

---

## 11. 报告怎么写

**每次审核完，交一份报告。** 六节，顺序固定：

```
## 1. 摘要              —— 审了多少商品、结论分布、需人工处理几个
## 2. 数据缺口          —— 没查到的部分（没有就写"无"）
## 3. 需决策的发现      —— 要店主拍板的
## 4. 待复核的发现      —— 需要人看一眼的
## 5. 逐商品结果        —— 每个商品一条
## 6. 已查阅规则        —— 用到的规则和依据
```

> **第 2 节不能省。** 它把"没查"和"查过没问题"分开。省了它，店主会以为所有商品都过了审。

**摘要写法（给店主的数字对）**

```
本次审核 158 个商品。
致命 3 个（建议不上架）、高 12 个（需资质或改文案）、中 41 个（需修改）、
低 23 个（建议优化）、通过 79 个。
改写后需复扫 158 个。
```

**不要写**"整体状况良好""基本合规"这种话 —— **给数字对**。

---

## 12. 审核员自查（交工前问自己）

| # | 问题 | 过 |
|---|---|---|
| 1 | 每个商品都过了标题、详情、图片、属性四关？ | □ |
| 2 | 每个禁售品类都查过了？ | □ |
| 3 | 每个命中的词都过了一遍 §9 豁免清单？ | □ |
| 4 | 高风险品牌都查了授权？ | □ |
| 5 | 缺资质的都出工单了，没混进改写清单？ | □ |
| 6 | 建议下架的都列出来了，**没有自己删**？ | □ |
| 7 | 改写的文案改完后**从头读了一遍**？ | □ |
| 8 | 改写有没有引入中文/法语/粘连词？ | □ |
| 9 | 有没有商品详情和其他商品一字不差？ | □ |
| 10 | 报告第 2 节（数据缺口）写了？ | □ |
| 11 | 摘要写的是**具体数字**，不是"基本合规"？ | □ |
| 12 | 有拿不准的，挂"待复核"了而不是自己拍板？ | □ |

---

## 13. 平台处罚与解封（店主须知）

| 处罚 | 触发 | 能恢复吗 |
|---|---|---|
| 账号冻结（IP 类） | 品牌方投诉 + 平台审核 | **只有品牌方撤销投诉才能恢复** |
| 账号冻结（监管机构类） | Anvisa / Inmetro / 农业部 | **必须原投诉机构书面同意** |
| 下架（IPR） | 商标/版权/专利/外观 | 申诉路径：Contestar → 品牌方决定 |
| 删除（`excluído`） | listing 违规 | **不可恢复**，且计入处罚点 |
| 封禁（`banimento`） | 严重违规 | 问题解决后**可恢复** |
| 限制触达（`alcance limitado`） | 轻度违规 | 整改后**自动恢复** |

> **审批通过 ≠ 解封成功。** 案件要记录**平台侧的实际状态**。

**处罚点机制**：每周一归属 → 一周后生效 → 限制持续 14–28 天 → 每条已认定违规可申诉一次。

**五大 NCL 高风险类目**

| NCL | 类目 | 高风险品牌 |
|---|---|---|
| 03 | 化妆品/个人卫生 | Natura / Boticário / Avon / Lancôme / L'Oréal |
| 09 | 电子/科技 | Apple / Samsung / Sony / Xiaomi / Huawei / Beats / JBL |
| 18 | 皮革/仿皮 | LV / Gucci / Hermès / Chanel / Prada / Coach / MK / Burberry |
| 25 | 服装/鞋帽 | Nike / Adidas / Puma / Supreme / TNF / Champion / Levi's |
| 28 | 玩具/游戏 | Disney / Marvel / Pokemon / Sanrio / Lego / Nintendo |

---

## 14. 改录依据（这份手册的来源）

所有判定标准都来自本仓库的机器可读资产，**不是拍脑袋写的**：

| 来源 | 内容 |
|---|---|
| `rules/01_prohibited_restricted_items.json` | 17 条禁售/受限规则（PI + RI） |
| `rules/02_ip_trademark_copyright.json` | 8 条知识产权规则（IP） |
| `rules/03_listing_violations_duplicates.json` | 17 条刊登与重复规则（LV + DUP） |
| `rules/04_cases_relist_authorization.json` | 5 条案件/重发/授权规则（RL + AU + AC） |
| `rules/05_medicines_health.json` | 3 条药品健康规则（MED） |
| `research/violation_codes.json` | 106 个平台处罚码（严重度 + 是否扣分） |
| `lexicon/exemptions.json` | 7 条误报豁免规则 |
| `lexicon/non_avoidable.json` | 6 类无法靠文字规避的品类 |
| `lexicon/rewrite_map.json` | 触线 → 中性替换表 |
| `lexicon/quality_patterns.json` | 15 条套模板/批量味特征 |

**发现手册和规则库不一致时**：以 `rules/*.json` 为准，并提出来更正本手册。

---

## 15. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-10-28 | 初版：由 50 条规则 + 106 个处罚码 + 7 条豁免 + 6 类无法规避 + 15 条质量特征生成的纯手工审核手册 |
