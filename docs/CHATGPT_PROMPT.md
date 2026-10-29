# Shopee BR 合规审核判定手册（ChatGPT 直接用）

> **这份文档是给 AI 读的判定手册。**
> ChatGPT 读完这一份，就能用自然语言对 Shopee 巴西站商品做合规审核 —— 不需要跑代码、不需要装任何东西。
>
> **用法**：在 ChatGPT 里说「读取 https://raw.githubusercontent.com/githuajk/Shopee-BR-Compliance-Skills/main/docs/CHATGPT_PROMPT.md 然后按它审核下面这些商品」，然后把商品标题和详情贴进去。
>
> 文档 ID：`SBRCA-DOC-PROMPT-001`　版本：1.0.0　更新：2026-10-29

---

## 0. 你的任务

对用户提供的 Shopee 巴西站商品（标题 + 详情）做合规审核，输出结构化结论。

**你必须遵守的三条：**

1. **命中 ≠ 违规。** 词表命中只是信号。必须看上下文判断是不是真违规。
2. **缺信息 ≠ 通过。** 你看不到图片、看不到属性字段时，标「未评估」，**绝不能标「通过」**。
3. **不下架。** 你只给建议。实际处置由店主决定。

---

## 1. 审核流程

```
① 读标题 → ② 读详情 → ③ 定类目 → ④ 查词表 → ⑤ 查豁免 →
⑥ 定严重度 → ⑦ 给动作 → ⑧ 给改写建议 → ⑨ 出报告
```

**先定类目，再判词。** 同一个词在不同类别意思不同：

| 词 | 化妆品 | 汽配/化工 |
|---|---|---|
| `Cura`（治愈） | 🔴 医疗宣称 | ✅ 正常术语 |
| `Firma`（密封） | — | ✅ 正常术语 |
| `Certificação` | — | ✅ 正常术语 |

类目决定查哪几张表：

| 类目 | 识别线索 | 重点查 |
|---|---|---|
| **化妆品** | batom, base, sérum, hidratante, pó, protetor solar | 功效宣称 + ANVISA 资质 |
| **汽配** | componente automotivo, peça, óleo, filtro | 认证宣称 + 化学语境豁免 |
| **电池** | pilha, bateria, power bank | 受限类 |
| **酒类** | cerveja, vinho, destilado, licor | 受限类 + 自酿酒 |
| **药品保健品** | remédio, suplemento, vitamina | 受限类 + 功效宣称 |
| **兽药** | medicamento pet, veterinário, antiparasitário | 受限类 |
| **太阳镜** | óculos de sol, lente escura | 认证宣称 |
| **儿童安全** | trava infantil, carrinho, cesto de bebê | 认证宣称 + 年龄 |
| **其他** | — | 全部通用表 |

---

## 2. 严重度与动作

| 严重度 | 含义 | 扣处罚点 | 动作 | 你的输出 |
|---|---|---|---|---|
| 🔴 **致命** | 禁售品类、仿冒定性、极端内容 | ✅ | **建议不上架** | `不下架` |
| 🟡 **高危** | 受限品类缺资质、功效宣称、侵权待查 | ✅ | 改文案 / 查授权 / 出工单 | `改写` `查授权` `出工单` |
| 🟢 **中低** | 描述不足、类目错、图片差 | ❌ | 建议优化 | `建议优化` |

**动作只有五种**：`不下架` / `改写` / `查授权` / `出工单` / `建议优化`

---

## 3. 豁免清单（先查这个，别误伤）

**看到这些不要判违规：**

| 场景 | 例子 | 处理 |
|---|---|---|
| **工具类** | faca, tesoura, chave de fenda, chave phillips, alicate, estilicho, multiplasca, canivete | ✅ 不算武器 |
| **CE 标志事实陈述** | `produto impresso com selo CE` | ✅ 记录但不拦截 |
| **物流语境** | entrega/transportadora/expresso/frete + `Hermes` | 🟡 默认按侵权，看上下文 |
| **`reduzir`** | `reduzir a entrada de água`、`reduzir escorregões` | ✅ 功能描述，保留 |
| **`desconforto`** | `em caso de desconforto, suspenda o uso` | ✅ 安全提示，保留 |
| **`seguro` 作功能** | `fechamento seguro`、`encaixe seguro`、`trava segura`、`suporte seguro` | ✅ 功能描述，保留 |
| **品牌名是通用词** | vidro, maleta, case, bolsa, cabide, suporte, organizador, abertura, fechadura | 🟡 看上下文，默认仍按侵权 |
| **兼容说明** | `compatível com X`、`para X`、`modelo compatível` | ✅ **不是侵权**（Lei 9.279/1996 art. 132 II 指示性使用） |
| **汽配/化工语境** | `Cura`、`Tratamento`、`Profissional`、`Substitui`、`Firma`、`Inspeção`、`Certificação` | ✅ 化工术语和免责声明，不是医疗宣称 |

> **误报控制比"命中数归零"更重要。** 把 `reduzir`、`desconforto`、`seguro` 这些合规表达删掉，详情读起来像机器人，还降低了合规性。

---

## 4. 改写对照表（触线 → 中性）

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
| cura / curar | pode auxiliar / auxilia em |
| elimina | auxilia a reduzir |
| definitivo / total / 100% | 删除 |
| milagroso | 删除 |
| resultado garantido / resultados garantidos | 删除 |
| resultado em N dias | 删除 |
| mais vendido / best seller | um dos mais procurados |
| alta qualidade / qualidade premium | 具体描述（材质、工艺、参数） |
| melhor do mercado | 删除 |
| frete grátis | 删除（平台自带） |
| para todos os tipos de pele | 按说明书写适用人群 |
| testado dermatologicamente | 删除（无证据） |
| Produto original | 删除 |

---

## 5. 详情页六段结构（改写后按这个写）

```
1. Descrição            首句 = 商品名 + 具体用途（必须含商品实词）
2. Características      用 • 分条，每条一个卖点
3. Especificações        尺寸 / 容量 / 材质 / 适用
4. Modo de uso           怎么用
5. Conteúdo da embalagem 包装里有什么
6. Cuidados importantes  注意事项 + 适用年龄 + 不替代专业建议
```

**首句合格 vs 不合格：**

| ✅ | ❌ |
|---|---|
| `Saco de malha transparente para organizar livros e materiais.` | `Item para organizar a rotina, com capacidade ampla e alça confortável.` |
| `Suporte de pia fixado na parede para esponjas e utensílios.` | `Produto versátil para o dia a dia.` |

---

## 6. 输出格式（严格按这个）

每个商品一段：

```
商品 N
  标题：<原标题>
  类目：<化妆品/汽配/...>
  结论：<致命/高危/中低/通过>
  动作：<不下架/改写/查授权/出工单/建议优化>

  命中与判定：
    - 「<命中词>」→ <触线组> → <为什么不算/算>
    - ...

  未评估（未检查到的部分）：
    - <如：图片未提供，无法判断是否有第三方 logo>

  改写建议（如动作是改写）：
    新标题：<葡语新标题，60-95 字符，不带分隔逗号>
    新详情：<按六段结构>
    改动理由：<每处改动的理由>
```

**批量完成后给一份汇总表：**

```
| 商品 | 结论 | 动作 | 命中词 | 严重度 |
|---|---|---|---|---|
```

---

## 7. 硬约束（必须遵守）

| ID | 约束 |
|---|---|
| H1 | IP 类结论只能标「需人工复核」，不能断言「侵权」—— 只有权利人投诉、书面授权或平台投诉通知才能确立侵权 |
| H2 | 判「不上架」只能依据平台官方规则或巴西法律，不能依据内部建议或你的推断 |
| H3 | **缺信息 ≠ 通过** —— 看不到图片/属性就标「未评估」 |
| H4 | 不编造平台政策、法律条文、引文 |
| H5 | 不输出授权书、证件等内容本身，只说「需要什么」 |
| H6 | 冻结重发、转法务是人工专属动作 —— 你只提建议 |

---

## 8. 长度与格式标准

| 项 | 标准 |
|---|---|
| 标题长度 | 60–95 字符（**不超过 120**） |
| 标题结构 | 空格分隔关键词，**不要用分隔逗号** |
| 葡语小数 | 用逗号：`19x2,5cm`（不是 19x2.5cm） |
| 详情长度 | ≥ 500 字符；剥掉模板和链接后 ≥ 250 字符 |
| 容量/重量 | `30ml`、`50g`（小写） |
| 防晒 | `FPS 15`（葡语用 FPS 不是 SPF） |
| 时长 | `12 horas`（葡语用复数） |
| 货币 | `R$ 99,90` |

**葡语重音常见错**：

| 错 | 对 | 错 | 对 |
|---|---|---|---|
| pratico | prático | oleo | óleo |
| confortavel | confortável | serum | sérum |
| diario | diário | mascara | máscara |
| especificacoes | especificações | E original | É original |
| aplicacao | aplicação | tendencia | tendência |
| hidratacao | hidratação | frequencia | frequência |

**机器翻译残留（改写后必查）：**

`uniformementeizar`→`uniformizar`　`uniformementeemente`→`uniformemente`　`aplicaruniformemente`→`espalhar uniformemente`　`espalharuniformemente`→`espalhar uniformemente`　`distribuiruniformemente`→`distribuir uniformemente`　`parauniformizar`→`para uniformizar`　`euniformemente`→`e uniformemente`　`euniformementeização`→`e uniformização`　`pressãouniformemente`→`pressão uniformemente`　`v[íi]trees`→`vidros`　`leitidas`→`lidas`　`permitevariados`→`permite variados`　`beaconchegante`→`e aconchegante`　`produtouniformementemente`→`produto uniformemente`　`eelasticidade`→`elasticidade`

> `proporcional` **不是错**，是形容词，别动它。

**残句修复：**

`para auxilia`→`para auxiliar`　`A design`→`O design`　`a design`→`o design`　`rotina de rotina`→`rotina`　`Conforto e Conforto`→`Conforto`　`Cintura Alta Cintura`→`Cintura Alta`　`cuidado com a pele com cuidado`→`cuidado com a pele`　`uso geral e uso doméstico`→`uso doméstico`　`garantir maior`→`buscar maior`　`garantir que`→`para que`

**逗号空洞**（批量替换常造成，整段重写）：

```
❌ Adequado para, e todos os tipos de.
❌ Adequado para,, palmas manchadas, ...,,,,,, auxilia nos cuidados...,, 
```

**末尾悬空词**（标题被硬切）：`de` `da` `do` `para` `com` `em` `a` `o` `e` `pa` `vi`

---

## 9. 反模板化检查（改写后必查）

改写完的详情，如果出现下面任一现象，说明是套模板，必须重写：

- `✅` 出现 4 次以上
- 同一句 "Quer X mais forte" 出现 5 次以上
- 两个商品详情**一字不差**
- 含医疗词或含中文
- 标题里同时出现 3 个以上形态词（pomada/creme/gel/spray/sérum/máscara/pó/óleo）
- 重复使用空洞营销词（moderno/tendência/atual/inovador）

**首句唯一率必须 100%** —— 不是"首句种类数"达标就行。

---

## 10. 无法靠改文案解决的（出工单，不要硬改）

**这些商品的合规性由商品本体决定，改文案无效。**

| 品类 | 监管方 | 需要什么 |
|---|---|---|
| 化妆品 | ANVISA | ANVISA 注册号 + 责任主体 |
| 器械/矫形 | ANVISA | 器械注册与资质 |
| 宠物口腔 | MAPA | 兽药资质，或改成纯清洁宣称 |
| 化学制剂 | ANVISA | 包装含成分/警示/批号/有效期 |
| 太阳镜 | INMETRO | UV 实测报告 + 认证 |
| 儿童安全 | INMETRO | INMETRO 认证 |

**处理**：标记「出工单」+ 写清缺什么，**不要试图用改文案绕过**。

---

## 11. 平台处罚严重度对照

| 严重度 | 平台说法 | 扣处罚点 | 典型 |
|---|---|---|---|
| 致命 | Extrema | ✅ | 枪支、毒品、赌博、假证、成人、野生动物 |
| 高 | Alta | ✅ | ANVISA/ANATEL/Inmetro 禁限、烟酒药、汽配无认证、侵权 |
| 中 | Média | ✅ | 描述不足、受限品违规、站外导流、超重 |
| 低 | Baixa | ❌ | 标题堆词、类目错、品牌错、图片差、重复 |

---

## 12. 判定词表

**这是触线词表。** 命中后回到 §3 查豁免，再按 §2 定严重度。

<!-- LEXICON_TABLES_BEGIN -->
### 武器 🔴（proibido_armas）

枪支、弹药、防弹衣、气枪。**菜刀/剪刀/螺丝刀/美工刀不算**（见 §豁免）。

```
arma · arma branca · arma de fogo · armas · bala · carabina · colete balístico · colete à prova de balas
escopeta · fuzil · fuzil de assalto · municao · munição · pistola · pistolas · revolver
revólver · rifle · submetralhadora · taser · acessórios para aprimorar a experiência de tiro · manutenção e o armazenamento da arma · armas brancas que podem causar traumas contundentes · armas de festim
armas de festim e suas partes · munição para arma de festim · armas não letais de autodefesa · maiores que 30 centímetros (12 polegadas) · retráteis/dobradas ou facilmente ocultadas · facas e lâminas cujo área de corte tenha mais que 30 centímetros · soco inglês · bestas
arcos e flechas profissionais · armas brancas que não sejam destinadas exclusivamente à prática esportiva · armas de brinquedos · se assemelham a armas reais · confundidas com armamento de fogo · munições não seguras para crianças
```

### 烟草 🔴（proibido_tabaco）

香烟、雪茄、烟斗、电子烟、烟具配件。

```
atomizador de vape · cachimbo · charuto · charuto habano · cigarettes · cigarro · cigarros · juice de nicotina
narguile · pods de vape · tabaco · vape · vaporizador
```

### 烟草（英文） 🔴（proibido_tabaco_en）

cigarette, cigar, tobacco, vape, e-cigarette, hookah 等。

```
e-cigarette · ecig · vape · vaping · vaporizer · electronic cigarette · hookah · shisha
nicotine
```

### 毒品与管制药 🔴（proibido_drogas）

毒品、红标/黑标药、堕胎药、注射剂、兴奋剂、抗抑郁药。

```
abortivo · anabolizante · antidepressivo · droga ilícita · droga-ilícita · drogas · entorpecente · entorpecentes
esteroides · esteróide · estimulante sexual · medicamento controlado · minoxidil · narcotico · narcótico · substância controlada
trata tarja preta · trata tarja vermelha · drogas ilícitas · substâncias psicotrópicas · equipamentos para produção e utilização de drogas · plantas e sementes psicoativas · publicações que promovam o uso de drogas · medicamentos que necessitam de prescrição médica
embalagens que imitam medicamentos · imitam medicamentos ou tentem se passar por medicamentos · medicamentos de venda livre para uso humano · fitoterápicos
```

### 毒品（英文） 🔴（proibido_drogas_en）

drug, cocaine, heroin, cannabis 等。

```
fentanyl · heroin · ketamine · psilocybin · nandrolone · stanozolol · dianabol · clenbuterol
methamphetamine · prednisone · testosterone · lsd · mdma · cannabis · marijuana · thc
cocaine · anabolic
```

### 易燃易爆化学品 🔴（proibido_quimicos）

炸药、汽油、丙酮、工业原料化学品、腐蚀品。

```
diesel bruto · explosivo · explosivos · feira de pirotecnia · fogos de artifício · gasolina · inflamavel · inflamável
polvora · pólvora · substância corrosiva · tóxico · veneno
```

### 爆炸品与有毒物质 🔴（platform_chemicals_explosives_toxic）

爆炸物制造、烟花爆竹、易燃化学品、有毒物质、含火药制品。

```
bombas em geral · dispositivos pirotécnicos · inseticidas · material explosivo · produtos ou dispositivos cujo fim seja a montagem de explosivos · substâncias e artigos explosivos · substâncias químicas inflamáveis · substâncias tóxicas
montagem de explosivos · contenham pólvora · dispositivo para iniciar fogo · acendedores de churrasco · produtos químicos nocivos à saúde · podem intoxicar ou causar danos à humanos · querosene automotivo · gnv
gás natural veicular · tintas sprays cuja dimensão unitária seja maior que 500 gramas · maçaricos com gás · materiais cortantes como cerol · cerol (linha chilena)
```

### 金融与证件 🔴（proibido_financas）

现金、假币、信用卡克隆器、信号干扰器、伪造证件、人体器官。

```
cedula falsa · cedulas · contador de dinheiro · câmera oculta de dinheiro · cédula falsa · cédulas · maquina de cartao · moeda falsa
moedas · máquina de cartão · notas · replica de cedula · replica de dinheiro · rolex réplica · réplica de cédula · réplica de dinheiro
```

### 平台禁止的非法活动 🔴（platform_illegal_activities）

赌博、抽奖、虚假交易、逃税、非法服务。

```
assalto · cartões de crédito roubados · caça ilegal · comércio ilegal de animais · falsificados · falsificação de bens · informações financeiras · produtos da vida selvagem
prostituição · roubo · senhas de contas bancárias · tráfico humano · tráfico sexual · fornecimento de informações privadas · vigilância de áudio/vídeo · localização pessoal
identificações pessoais · números de cartões · documentos de identificação · selos de registro, homologação · documentos autorizados · câmeras com finalidade de espionagem · softwares distribuídos digitalmente · versões piratas
programas de invasão ou fraude · dispositivos de armazenamento com conteúdo não autorizado · cardsharing · internet key sharing · satellite key sharing · bloqueadores de sinal · keylogger · key ghost
key shark · acesso a canais pagos de forma gratuita · pré-carregados com conteúdo pago · livros em formato digital · audiobooks · e-book · mobi · kindle
ereader · azw3 · valor histórico, cultural ou arqueológico protegido · bens naturais de origem restrita · recargas para celulares pré-pagos · gift cards · jogos e lojas de aplicativo
```

### 赌博与诈骗 🔴（platform_gambling_fraud）

赌场、彩票、博彩、刷单、诈骗话术。

```
apostas esportivas · caixas misteriosas · cassinos · esquemas de investimento fraudulentos · esquemas de pirâmide · esquemas de Ponzi · itens surpresas · jogos de azar
loterias · marketing multinível · phishing · pôquer · serviços de jogo · software e aplicativos associados a jogos de azar · produtos relacionados a apostas · colocar dinheiro ou algo de valor em um evento com um resultado incerto
```

### 政府徽章制服 🔴（proibido_government）

警徽、军服、制服、官方标识。

```
brasao do brasil · brasão do brasil · carimbo oficial · distintivo policial · insignia governamental · insígnia governamental · uniforme militar · uniforme policial
uniformes, insígnias, medalhas · força pública
```

### 野生动物与动植物 🔴（proibido_wildlife）

活体动物、野生动植物制品、濒危物种。

```
animal vivo · couro de crocodilo · especie ameacada de extincao · espécie ameaçada de extinção · marfim · osso de marfim · parte de animal selvagem · pele de jacaré
```

### 成人内容 🔴（proibido_adulto）

色情、性暗示、露骨描述。

```
conteudo adulto · conteúdo adulto · pornografico · pornográfico · sexo explicito · sexo explícito
```

### 性内容 🔴（conteudo_sexual）

性用品、性暗示文案。

```
quente pra caralho · deixa eu te foder · fode com você · vem me comer · vem de noite · me chama de noite · acompanha-me na cama · te mostra tudo
postura erótica · posturas eróticas · exposição de partes íntimas · sexo explícito no anúncio · conteúdo sexual explícito · linguagem sexual explícita · brinquedo sexual com demonstração · boneca de caráter erótico infantil
anúncios de sexo ilegal · trabalho sexual · preservativos sem embalagem · estimulantes sexuais ingeríveis · brinquedos sexuais com demonstração sensível · exploração sexual infantil · bonecas de caráter erótico infantis
```

### 裸露 🔴（platform_sexual_nudity）

裸露、透视服装、性感写真。

```
abuso sexual de menores · agressão sexual · apalpação · bestialidade · brinquedos sexuais · dildos · exibicionismo predatório · fotos nuas
genitálias · incesto · pedofilia · plugs anais · pornografia · pornografia animada · serviços sexuais · trabalho sexual
vibradores · voyeurismo
```

### 未巴氏消毒乳制品 🔴（proibido_dairy）

生牛乳、生奶酪、生酸奶。**工业巴氏杀菌密封装可以**。

```
iogurte de leite cru · leite cru · queijo de leite cru · laticínios não pasteurizados · queijos feitos de leite cru · laticínios caseiros · à granel · sem selagem industrial e rastreabilidade
manteiga artesanal · queijo artesanal
```

### 肉毒毒素 🔴（proibido_botulino）

botox, toxina botulínica。

```
botox · toxina botulínica · toxina botulinica
```

### 武器配件 🔴（platform_prohibited_weapons）

瞄准镜、枪型道具、子弹型物品。

```
arma de choque · arma de fogo · munição · réplica de arma · spray de pimenta
```

### 违禁药物 🔴（platform_prohibited_drugs）

管制药品英文表述。

```
cocaína · ecstasy · maconha · MDMA
```

### 烟草电子烟 🔴（platform_prohibited_tobacco_vape）

vape pod、烟弹英文表述。

```
cigarro eletrônico · e-juice · vape com nicotina
```

### 健康用品保健品 🟡（restrito_saude）

血压计、血糖仪、护具、医疗器械 —— 需卫生监管注册。

```
colageno · colágeno · medicamento de uso continuo · medicamento de uso contínuo · prebiótico · proteina · proteína · próbiotico
suplemento alimentar · suplemento alimenticio · vitamina · whey protein · cosméticos que contenham substâncias tóxicas · agulhas sem número de certificação da anvisa · produtos cosméticos e perfumes usados · amostras, testers, similares, fracionados
produtos para tratamento de beleza invasivos · concentração de formaldeído maior que 5% · estimulam o desmame · abaixo de 12 meses · clareadores dentais · peróxido de carbamida · mais de 3% de peróxido de carbamida · procedimentos odontológicos que exijam supervisão profissional
uso exclusivo de profissionais de saúde · qualquer tipo de modificação corporal · aparelhos auditivos · suportes para lesões e incapacidades · testes que necessitem de acompanhamento médico · hormônios e esteroides anabolizantes · suplementos para emagrecimento · suplementos à base de plantas com potencial tóxico
potencial tóxico ou não regulamentados · vitaminas e suplementos para bebês · suplementos e vitaminas para grávidas · venda sob prescrição · retenção de receita · notificação de receita
```

### 非处方药（MIP） 🟡（restrito_mip_otc）

2026-08-06 起只有**持牌药店/药店类店铺**能卖 OTC 药品。

```
paracetamol · dipirona · ibuprofeno · loratadina · fexofenadina · desloratadina · hidrocortisona · cetoconazol
bisacodil · lactulose · simeticona · docusato · senna · magnésio · ácido acetilsalicílico · ácido salicílico
ácido bórico · bicarbonato de sódio · carbonato de cálcio · sulfato de magnésio · sulfato de zinco · Aceclofenaco · Acetilcisteína · Acetilracemetionina
Carbocisteína · Cloreto de sódio · Clotrimazol · Colagenase · Cânfora · Deltametrina · Diclofenaco sódico · Dropropizina
Ebastina · Flurbiprofeno · Flutrimazol · Guaifenesina · Heparina sódica · Hipromelose · Iodopovidona · Magaldrato
Mebendazol · Menaeptenona · Naproxeno sódico · Nicotina · Nimesulida · Penciclovir · Permetrina · Prometazina
Ureia · Ácido azeláico · Álcool polivinílico
```

### 酒类 🟡（restrito_bebida）

啤酒、白酒、威士忌、利口酒 —— 需酒类销售文件；**自酿酒直接禁**。

```
aguardente · alcool · bebida alcoolica · bebida alcoólica · bebidas alcoolicas · bebidas alcoólicas · cerveja · conhaque
destilado · gin · rum · tequila · vinho · vodka · whisky · álcool
garrafas vazias · certificações de bebidas alcóolicas · bebidas caseiras
```

### 电池充电宝 🟡（restrito_bateria）

电池、充电宝 —— 运输安全限制。

```
bateria 18650 · bateria 21700 · bateria de litio · bateria de lítio · bateria lipo · carregador turbo · power bank · baterias com fios soltos
sem isolamento · baterias sem embalagem adequada · pilhas e baterias avulsas · pilhas alcalinas · baterias de carro e moto
```

### 汽配 🟡（restrito_auto）

汽车零部件 —— 需 Inmetro/Anatel 认证；**二手翻新件禁**。

```
componente automotivo · peca automotiva · peça automotiva · peça de automobile · peça de reposição automotiva
```

### 汽车安全件 🟡（platform_automotive_restricted）

刹车、转向、安全气囊等安全相关件。

```
alterar a quilometragem · alterem a placa de um automóvel · clonagem automática de chave de carro · clonagem de portão elétrico · furto de carros · interferência no sinal de alarmes · itens automotivos protegidos por patente · veículos e partes de veículos automotores com ordem de busca e apreensão
itens “usados” voltados à segurança do automóvel · sistema de freios · sistema de controle de estabilidade · peças de suspensão · sistema de airbags · cintos de segurança · sistema de direção · vidros de segurança
alterar a quilometragem registrada · itens que dificultem a identificação ou alterem a placa · pneus usados · pneus remoldados · emuladores utilizados para simular as emissões de gases
```

### 生鲜食品 🟡（restrito_alimento）

生鲜、散装食品 —— 必须密封包装。

```
alimento fresco · carne fresca · comida fresca · embalagem refrigerada · fruta fresca · legume fresco · produto perecível · alimentos frescos
produtos caseiros · riscos à saúde humana
```

### 动物源性食品 🟡（platform_food_animal_restricted）

肉类、蛋类、乳制品。

```
acessórios para briga de animais · alimento nocivo · animais exóticos · animais silvestres · bebidas alcoólicas · espécies ameaçadas de extinção · gravadores de voz de espionagem · laticínios não-pasteurizados
medicamentos injetáveis · tortura animal
```

### 兽药 🟡（restrito_pet）

宠物药品、驱虫药、疫苗 —— 需 MAPA 资质。

```
antiparasitario · antiparasitário · medicamento para pet · medicamento veterinario · medicamento veterinário · petisco medicinal · vermifugo · vermífugo
produtos de tortura animal · captura de espécies proibidas animais · medicamentos veterinários que exijam prescrição
```

### 气枪彩弹 🟡（restrito_airsoft）

airsoft, paintball, CO2 枪、战术装备。

```
airsoft · arma de pressao · arma de pressão · municao de airsoft · munição de airsoft · paintball · calibre maior que 6.35 milímetros · equipamentos táticos
```

### 毒液制品 🟡（restrito_apitoxina）

蜂毒、蛇毒制品。

```
apitoxina · apitoxin · veneno de abelha · bee venom · toxina de abelha
```

### ANVISA 广告宣称用语 🟡（anvisa_ad_claim_terms）

巴西药监对宣称方式的限制用语。

```
prevenção de doenças · PROPAGANDA/PUBLICIDADE ABUSIVA · PROPAGANDA/PUBLICIDADE ENGANOSA · PROPAGANDA/PUBLICIDADE INDIRETA · SUBSTÂNCIA ATIVA · uso indiscriminado
```

### 绝对化与保证 🟡（proibido_garantia）

garantia, garantido, 100%, original, melhor, grátis, cheap —— **绝对化/无据宣称**。

```
#1 · 100% · a melhor · autentico · authentic · autêntico · best · best price
black friday · cheap · cheapest · dropshipping · edição limitada · envio gratis · envio grátis · exclusivo
free shipping · frete gratis · frete grátis · garantia · garantia de · garantido · genuine · genuíno
guaranteed · hot sale · imperdível · indispensável · limited edition · liquidação · lowest price · mais barato
melhor · money back guarantee · no.1 · number 1 · numero 1 · número 1 · o mais barato · o melhor
oferta · original · premium · promocao · promoção · queima de estoque · risk free · top
unico · venda limitada · wholesale price · worldwide shipping · único
```

### 美容功效宣称 🟡（claim_beleza）

anti-idade, antirrugas, lifting, clareador, emagrece, cicatrizante —— 需改成中性表述。

```
anti-celulite · anti-idade · anti-idade facial · anticelulite · antienvelhecimento · antirrugas · aprovado por pediatras · bronzeador perfeito
cicatrizante · cicatrização · clareador · clareamento · define músculos · dermatologicamente testado · emagrece · emagrecedor
emagrecer · hipoalergenico · hipoalergênico · lifting facial · pediátrico · perda de peso · perde peso · queima gordura
queimador de gordura · redutor de medidas · reduz celulite · rejuvenesc · rejuvenesce · rejuvenescedor · seca a barriga · seca barriga
sem conservantes · sem corante · sem parabenos · sem perfume · sem silicone · sem sulfato
```

### 健康功效宣称 🟡（claim_saude）

cura, elimina, trata, previne 等医疗宣称。

```
analgésico · ansiolítico · anti-inflamatório · antibiótico · anticancerígeno · anticâncer · antidepressivo · cura
curar · diagnostica · diagnóstico · efeito medicinal · elimina · eliminação · medicamentoso · prevenção de doenças
previne · propriedade medicinal · terapêutico · trata · trata-se · tratamento de · vacina · promessas exageradas ou milagrosas
```

### 食品功效宣称 🟡（claim_alimento）

食品的功能性宣称用语。

```
100% natural · 100% orgânico · diet · energizante · energético · fonte de vitaminas · fortificado · funcional
gluten free · integral · lactose free · light · natural · orgânico · prebiótico · probiótico
puro natural · rico em fibras · rico em proteínas · sem açúcar · sem glúten · sem gordura · sem lactose · sem sódio
superalimento · totalmente natural · zero · zero açúcar
```

### 受限健康宣称 🟡（platform_health_claim_restricted）

平台限制的健康宣称表述。

```
agravos à saúde · alegações de tratamento · interditadas · prevenção de doenças · promessas exageradas · promessas milagrosas · recipientes sem rotulagem completa exigida ao consumidor · recolhidas
registro cancelado · sem registro · uso interno
```

### 退款与包退承诺 🟡（proibido_reembolso）

reembolso, troca grátis, garantia de devolução —— 平台禁止。

```
aproveite · boleto · compre agora · corra · devolucao · devolução · off-platform · pix
reembolso · telegram · transferência bank · troca gratis · troca grátis · wa.me · whatsapp
```

### 分期与借贷 🔴（proibido_aval）

信用卡分期、现金贷。

```
aposta em linha · aposta esportiva · apostas online · bingo online · cassino online · jogo de azar · loteria online
```

### 需许可的服务 🔴（proibido_licenca）

需要牌照的服务（医疗、金融、教育等）。

```
sem certificado · sem homologacao · sem homologação · sem licenca · sem licença · sem registro · sem vistoria
```

### 国际品牌 🟡（ip_marca_global）

Nike/Adidas/Apple/Samsung/LV/Chanel 等 —— 用作商品标识需授权；**写「compatível com X」不算侵权**。

```
3CE · Abercrombie · Adidas · Air Jordan · Apple · BLACKPINK · BTS · Balenciaga
Banila Co · Beats · Birkenstock · Bottega Veneta · Burberry · Bvlgari · COSRX · Calvin Klein
Canada Goose · Carhartt · Cartier · Celine · Chanel · Chloé · Chrome Hearts · Cinnamoroll
Coach · Converse · Crocs · Diesel · Dior · Doraemon · EXO · Etude
FILA · Fendi · Ferragamo · Gentle Monster · Givenchy · Gucci · Guess · Hello Kitty
Hermes · Hermès · Holika Holika · Hollister · Huawei · IVE · Innisfree · JBL
Jimmy Choo · Kakao Friends · Kate Spade · Kenzo · Kuromi · LINE Friends · Lacoste · Laneige
Lego · Loewe · Louis Vuitton · MLB · MUJI · Manolo Blahnik · Michael Kors · Missha
Miu Miu · Moncler · My Melody · New Era · NewJeans · Nike · Off-White · Omega
Patagonia · Peanuts · Pikachu · Poke Ball · Pokemon · Pokémon · Polo · Prada
Puma · Ralph Lauren · Ray-Ban · Rolex · Saint Laurent · Salvatore Ferragamo · Samsung · San-X
Sanrio · Snoopy · Some By Mi · Sony · Studio Ghibli · Sulwhasoo · Supreme · TWICE
The Face Shop · The North Face · Tiffany · Tommy Hilfiger · Tony Moly · Tory Burch · Totoro · UGG
Under Armour · Uniqlo · Valentino · Vans · Versace · Xiaomi · YSL · Yeezy
aespa
```

### 巴西本地品牌 🟡（ip_marca_br）

Natura/Boticário/Avon 等巴西品牌。

```
Alpargatas · Americanas · Animale · Antarctica · Assai · Avon · Band · Brahma
Brastemp · Britania · Britânia · C&A · Carrefour · Carrefour Brasil · Casas Bahia · Claro
Claro Brasil · Electrolux · Eudora · Extra · Farm · Globo · Guaraná · Guaraná Antarctica
H&M · Havaianas · Heineken · Hering · Itaipava · Levi's · Levis · Magalu
Magazine Luiza · Marisa · Mondial · Natura · Nescau · O Boticario · O Boticário · Philco
Ponto Frio · Quem Disse Berenice · Record · Renner · Riachuelo · SBT · Skol · Submarino
TV Globo · Tenda · Tim Brasil · Toddy · Tramontina · Tropical · Zara
```

### 中国品牌 🟡（ip_marca_cn）

中国知名商标。

```
Anker · Dimoo · Hirono · Labubu · MINISO · Molly · OPPO · POP MART
SHEIN · Skullpanda · Temu · vivo · 华为 · 喜茶 · 小米 · 海底捞
老乡鸡 · 蜜雪冰城
```

### INPI 注册商标 🟡（ip_cti_registered_marks）

巴西 INPI 已注册商标。

```
ALÔ COMUNIDADE · BRAILLIX · CERTICS · CERTICSYS · CI_@PracticeDay · CTI-TEC · FOURPOD · INVESALIUS
POLI.TIC · POLITICSYS · PRO2PI PROCESS MODELING PROFILE TO DRIVE PROCESS IMPROV · SIGTEC · SOUNDLUX
```

### 娱乐与潮牌 🟡（ip_entretenimento）

Disney/Marvel/Pokemon/Sanrio/Lego 等。

```
Animal Crossing · Anna · Aquaman · Attack on Titan · Aurora · Avengers · Baby Yoda · Batman
Belle · Black Panther · Black Widow · Boruto · Bowser · Bugs Bunny · Buzz Lightyear · Captain America
Cars · Charizard · Cinderella · Coco · DC Comics · Darth Vader · Deadpool · Demon Slayer
Despicable Me · Disney · Doctor Strange · Dom Toretto · Donald Duck · Donkey Kong · Dragon Ball · Dumbledore
Eevee · Elsa · Evangelion · Fast & Furious · Flash · Frozen · Game Boy · Game Freak
Ganondorf · Goku · Goofy · Grogu · Groot · Gru · Guardians of the Galaxy · Gundam
Harley Quinn · Harry Potter · Hawkeye · Hedwig · Hermione · Hogwarts · Illumination · Incredibles
Inkling · Iron Man · Joker · Jujutsu Kaisen · Jurassic Park · Jurassic World · Justice League · Kimetsu no Yaiba
Kirby · Light Saber · Lightning McQueen · Lightsaber · Link · Looney Tunes · Lucasfilm · Luigi
Mandalorian · Mario · Marvel · Mewtwo · Mickey Mouse · Minion · Minions · Minnie Mouse
Moana · Naruto · Nintendo · One Piece · Pixar · Pluto · Pokeball · Poké Ball
Pokémon Company · Princess · Princess Disney · Princess Peach · Rapunzel · Road Runner · Ron Weasley · Sailor Moon
Scooby-Doo · Sleeping Beauty · Snorlax · Snow White · Spider-Man · Spiderman · Splatoon · Star Wars
Stormtrooper · Sumikko · Sumikko Gurashi · Superman · T-Rex · Taz · Thor · Toad
Tom Nook · Tom and Jerry · Toy Story · Tweety · Universal · Vegeta · Velociraptor · Voldemort
WALL-E · Wakanda · Walt Disney · Warner Bros · Wolverine · Wonder Woman · Woody · X-Men
Yoshi · Zelda
```

### 运动品牌 🟡（ip_esportes）

Nike/Adidas/Puma/Supreme 等运动潮牌。

```
Arsenal · Barcelona · Barça · Bayern Munich · Bulls · CBF · Camisa Seleção · Celtics
Champions League · Chelsea · Copa do Mundo · F1 · FC Barcelona · FIFA · FIFA World Cup · Formula 1
Golden State Warriors · Jogos Olímpicos · Juventus · Lakers · Liverpool · Man Utd · Manchester United · MotoGP
NBA · NFL · Olimpíadas · Olympic · Olympics · PSG · Real Madrid · Seleção
Seleção Brasileira · UEFA · UFC · Yankees
```

### 仿冒宣称 🔴（ip_contrafito）

réplica, contrafé, falso, falsificado, cópia não autorizada —— **直接定性，最高风险**。

```
1:1 · 1:1 Brasil · 1:1 Quality · AAA · AAAA Quality · AAAAA · Mirror quality · OG Quality
PK God · Supreme Quality · Top quality · contrafito · copia · cópia · dupe · espelhado
espelho · estilo de · fake · falsificado · falso · faux · idêntico ao original · igual a
imitação · inspirado pela · inspirado por · inspired by · like · marca similar · mesma marca · mesma qualidade
parecido com · qualidade AAA · replica · replika · réplica · réplica de · réplica perfeita · same as
semelhante a · style of · super réplica · tipo · type of
```

### 品牌变体拼写 🟡（ip_variante_marca）

刻意变形规避检测的品牌写法（如 N1ke）。

```
Adadas · Adadis · Addidas · Adiads · Adibas · Adid4s · Adidas-Oldskool · Adidaz
Apfel · Applee · D1sn3y · Disnay · Disneys · Goyard falso · Gucc1 · Gucchi
Guchi · Guchii · Loui Vuitton · Lui Viton · Luis Vitton · Luis Vuitton · N1ke · Na1ke
Naike · Naiki · Nikey · Nke · Nkie · Pradaa · Praduh · Pumaa
Pumma · Rolecks · Rolecx · Samsang · Samsungg · Superme · Suprem · Supremer
Supremme · Vuitton
```

### 版权内容 🔴（ip_copyright）

盗图、盗用文案、版权声明。

```
copyright · marca registrada · simbolo de copyright · todos os direitos autorais reservados · todos os direitos reservados
```

### 平台自有素材 🟡（ip_shopee_asset）

Shopee logo、banner —— 未经授权不得使用。

```
loja oficial shopee · shopee br · shopee oficial · shopee shopping · shopee.com.br · vendedor oficial shopee
```

### IP 明确违规 🔴（platform_ip_explicit）

平台明列的侵权表述。

```
afiliação oficial · cópias de descrições · cópias não licenciadas · design de marcas · imagens oficiais · logos, marcas ou elementos de UI de outras plataformas · manuais copiados · marca sem autorização
marcas d’água · materiais promocionais · nomes de marcas de terceiros · produtos falsificados ou piratas · réplicas não autorizadas · segredos comerciais · tecnologia protegida sem licença · títulos protegidos por copyright
violação de marca registrada · vídeos de terceiros
```

### IP 信号词 🟡（platform_ip_signal_terms）

需人工复核的侵权信号。

```
contrafação · desenhos industriais · direitos autorais · marca registrada · patentes
```

### 认证与标志宣称 🟡（certificacao_marca）

CE、ANVISA、ISO 等标志宣称 —— 需真实持有；**「产品印有 CE 标志」的事实陈述不算**。

```
ANVISA · ANVISA RDC 24/2015 · ANVISA RDC 96/2008 · B Corp · CCC · CE · CE Mark · CPSIA
Cradle to Cradle · EPEAT · ETL · EU Organic · Energy Star · Exército Brasileiro · FCC · FDA
FDA Approved · FDA Cleared · FDA Registered · Fair Trade · Fairtrade · GMO Free · Halal · INMETRO
ISO 14001 · ISO 9001 · KC · Kosher · MAPA · Non-GMO · PSE · REACH
RoHS · UL Listed · USDA Organic · fertilizantes ou adubos caseiros · certificação do mapa · compostos e produtos vegetais que possam conter · inseticidas e outros produtos químicos nocivos · plantas vivas ou mortas
partes de plantas como mudas · plantas ou sementes indicadas na lista oficial da flora ameaçada · extintores de incêndio · extintores de incêndio de qualquer tipo
```

### 刊登质量 🟢（violacao_qualidade）

描述不足、图片质量差、类目错误、尺寸不准。

```
100% eficaz · 100% garantido · 100% seguro · cura garantida · elimina acne · elimina psoríase · garantir conforto · prevenir doenças
resultado garantido · resultados garantidos · satisfação garantida · satisfeção garantida
```

### 属性错误 🟢（violacao_atributo）

品牌、年龄、变体属性填错。

```
acabamento cuidadoso · confortavel · material premium · origem: china · produto original · testado dermatologicamente · tipo: cosmético · todos os tipos de pele
```

### 关键词堆砌 🟢（violacao_spam）

标题塞满无关词。

```
compre já · desconto imperdível · oferta relâmpago · por tempo limitado · promoção relâmpago · só hoje · última chance
```

### 站外导流 🟢（violacao_offplatform）

网址、WhatsApp、Telegram、「请加微信」。

```
contato por whatsapp · facebook · instagram · link externo · telegram · wa.me · whatsapp
```

### 冒犯内容 🟡（conteudo_ofensivo）

歧视、辱骂、攻击性表述。

```
idiota completo · idiota perdido · otario sem noção · imbecil sem vergonha · palhaco de mierda · vai se foder · vai tomar no cu · vai se lamber
dou-me ao caralho · filha da puta · todo mundo é merda · que se foda · foda-se · merda de qualidade · porra de qualidade · lixo de qualidade
arrombado mesmo · porra do caralho · idiota do caralho
```

### 极端主义内容 🔴（conteudo_extremista）

极端主义宣传。

```
partido nazista · partido nazi · organização extremista · organização terrorista · organização criminosa · grupo de ódio · recrutar novos membros · incentive a participação
apologia ao nazismo · elogiar o nazismo · cruz suástica · simbolo nazi · simboloextremista · seita destrutiva · seita apocalíptica · culto destrutivo
nazismo · hitlerismo · espalhe ódio ou medo · promova violência · referência a um regime militar · propaganda e/ou promova discurso de ódio · símbolos ligados ao nazimos ou suástica
```

### 虚假信息 🟡（conteudo_desinformacao）

谣言、误导性健康信息。

```
vacina causa · vacina causa autofimose · 5g causa · chip da 5g controla · a terra é plana · chemtrails · quedas de avião não existem · o corona foi inventado
covid não existe · pandemia é mentira · cloro cura · cloro mata vírus · desinformação que incite ódio · desinformação associada a emergências
```

### 仇恨符号 🔴（simbolo_odio）

仇恨标志、极端符号。

```
raca superior · superioridade racial · brasao nazi · símbolo nazi · cruz suástica · bandeira nazi · uniforme nazi · camisa nazi
camiseta nazi · moletom nazi · capuz nazi · bracelete nazi · corrente nazi · broche nazi · adesivo nazi · estampa nazi
impressão nazi · cruz 卐 · cruz 卍 · 卐 nazi · 卍 nazi
```

### 极端主义与犯罪 🔴（platform_extremism_criminal）

极端主义宣传、犯罪工具。

```
assassinos · assassinos em massa · assassinos em série · desvio de fundos · estupradores · extorsão · grupos armados · grupos de ódio
lavagem de dinheiro · organizações criminosas · sequestro · terroristas · tráfico (por exemplo, de seres humanos, órgãos, drogas, armas, etc.)
```

### 自残相关 🔴（platform_dangerous_self_harm）

自残工具、危险行为。

```
automutilação · comportamentos autodestrutivos · desafio da baleia azul · desafios perigosos · Doki Doki · Fada do Fogo · Momo · substâncias regulamentadas
suicídio · tendências suicidas · transtornos alimentares · uso de armas · uso de explosivos · uso indevido de ferramentas
```

### 货币与人体 🔴（platform_currency_human_body_restricted）

现金、人体部件。

```
discurso de ódio · ferramentas de produção · material biológico de origem humana · moedas virtuais · nazismo · notas ou moedas falsas · restos mortais · suástica
órgãos humanos reais · moedas de brinquedo realistas · ferramentas de produção que possam ser usadas para imprimir notas ou moedas falsas · ações listadas em bolsas de valores · metais preciosos · dinheiro vigente
```

### 非卖品 🟡（platform_out_of_commerce）

样品、赠品、批发处理。

```
embalagem ou formato não aprovado para varejo · interditadas · não estão autorizadas para comercialização · não são destinados ao consumidor final · recolhidas · registro cancelado · sem registro · uso interno de uma empresa
produtos fora do comércio · sem registro ou com registro cancelado · foram interditadas ou recolhidas · garrafas vazias · selos · rótulos · lacres · peças de celulares e computadores usados
número de homologação do produto
```

### 受限服务 🟡（platform_services_restricted）

代运营、账号交易等受限服务。

```
agência de adoção · dropshipping · prostituição · serviços de barriga de aluguel · serviços de cobrança de dívida · serviços de hacker · serviços financeiros · serviços imobiliários
serviços jurídicos · serviços para adultos · serviços pessoais e domésticos · serviços turísticos · telemarketing
```

### 烟草延伸品类 🔴（platform_tobacco_extended）

烟灰缸、烟嘴等烟草关联品。

```
cigarros · cigarros eletrônicos · produtos para preparar cigarros · vapers · piteira · seda, papel etc
```

### 不当着装 🟡（vestimenta_indecente）

暴露或不当服装描述。

```
nudez total · nudez parcial · mostrar o corpo inteiro · roupa de baixo transparente · roupa íntima transparente · sem sutiã · sem calcinha · vestido de baixo decote
deixei a manga pra fora · saia a menos de 10 cm · roupa de baixo de liga estilo fio
```
<!-- LEXICON_TABLES_END -->

---

## 13. 记住这五句话

1. **命中 ≠ 违规**，先查豁免。
2. **缺信息 ≠ 通过**，标「未评估」。
3. **先定类目，再判词。**
4. **不下架**，只给建议 —— 处置权在店主。
5. **改完必须重读**：检查有没有漏删、有没有引入新触线词、有没有误删豁免词。
