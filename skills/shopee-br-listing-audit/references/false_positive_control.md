# 误报控制规范

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-LA-003` |
| 所属模块 | `shopee-br-listing-audit` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 误报来源清单、词边界定义、豁免机制与上下文判定规则 |
| 相关文档 | `references/lexicon_scanning.md`、`references/audit_semantics.md`、`lexicon/exemptions.json`、`lexicon/term_groups.json`、`tools/scan_lexicon.py`、`docs/SOP_COMPLIANCE_REVIEW.md` §6 |
| 未决事项 | 无 |

---

## 1. 为什么误报比漏判贵

> 平台漏判会下架商品；误判会浪费人工复核工时，并让正常商品无法上架。
> **默认策略偏保守**：宁可 `flag_for_review` 交给人，不轻易 `block`。

这条策略在代码里的具体体现：

| 机制 | 实现位置 | 效果 |
|---|---|---|
| 词库命中只写 `evidence_refs`，不写 `rule_refs` | `engine.py` 的 `_build_evidence_refs()` | 词库永远不单独产生结论 |
| 词库组 → 规则映射只声明「去判哪条规则」 | `contracts/lexicon_rule_map.json` | 映射表不产生动作 |
| 动作由矩阵查表，不由词库决定 | `matrix.py` 的 `verdict_for()` | 词库不放大风险 |
| 受限类命中 = `require_evidence` 而非 `block` | `rules/01_prohibited_restricted_items.json` | 缺材料 = 补材料，不是判违规 |
| `requires_human_review` 在多条路径下自动为 `true` | `engine.py` 的 `_review_requirements()` | 拿不准的一律给人 |

---

## 2. 两个「层」的词边界**不同** —— 必须分清

这是本模块最容易踩的坑。**规则层与词库层用两套不同的文本聚合与匹配机制。**

| | 规则层 | 词库层 |
|---|---|---|
| 聚合字段 | `title` + `description` + `brand` + `category` + `model` + **图片 `ocr_text`** | `title` + `description` + `brand` + `category` + **`attributes` 的字符串值** |
| 实现 | `fields.py` 的 `any_text()` | `tools/scan_lexicon.py` 的 `Scanner.scan_product()` |
| 归一化 | **不做** —— 正则直接跑在原文上 | `小写 → NFD → 去组合附加符`（`norm()`） |
| 边界 | 规则内显式写 `(?<![a-zA-Zà-ÿÀ-ß])…(?![a-zA-Zà-ÿÀ-ß])` | 词组级策略：`group_meta.matching` = `strict` / `loose` |

实测差异：

```python
product = {
    "title": "Tênis Comum", "description": "Comum", "brand": "Comum",
    "category": "Casa", "model": "Pistola de Treinamento",
    "images": [{"image_id": "i1", "ocr_text": "Munição de plástico"}],
    "attributes": {"Material": "Pistola", "Cor": "Azul", "Qtd": 3},
}
```

- 规则层 `any_text` = `'Tênis Comum\nComum\nComum\nCasa\nPistola de Treinamento\nMunição de plástico'`
  → **含 `model` 与 `ocr_text`，不含 `attributes`**
- 词库层命中：只有一条 `proibido_armas / pistola / field=attributes.Material`
  → **含 `attributes`，不含 `model` 与 `ocr_text`**

> **推论**：同一段文字，规则层能看到而词库层看不到（或反之）是**正常现象**，
> 不是 bug。两条层各有盲区，靠 `evidence_refs` 里两类条目（`EV-SBR-*` 与 `EV-LEX-*`）
> 一起呈现给复核者。

### 2.1 规则层的葡语边界 —— 显式 lookaround

规则里的葡语关键词**一律**用显式边界：

```
(?<![a-zA-Zà-ÿÀ-ß])词(?![a-zA-Zà-ÿÀ-ß])
```

这条规则的含义是「**左右不挨着字母**」。与 Python 的 `\b` 的实测差异：

| 文本 | 显式 lookaround | `\b` |
|---|---|---|
| `pistola` | 命中 | 命中 |
| `pistola9` | 命中 | **不命中**（`9` 是 word 字符） |
| `9pistola` | 命中 | **不命中** |
| `pistola_x` | 命中 | **不命中**（`_` 是 word 字符） |
| `x-pistola` | 命中 | 命中 |
| `pistolada` | 不命中 | 不命中 |

也就是说：**显式边界比 `\b` 宽** —— 数字与下划线不算「挨着」。
这正是想要的：`pistola9`、`pistola_x` 里的 `pistola` 仍然是武器词。

> ⚠️ **一处需要纠正的旧说法**：骨架文档里写「Python 的 `\b` 在葡语重音元音旁不可靠，
> 会把 `Óculos` 吞成 `culos`」。在 CPython 3 的 **str 模式**上实测**复现不了**：
> `re.search(r"\bat[óo]xico\b", "Óculos para visão")` 返回 `None`，
> `re.sub(r"\s*at[óo]xico\b\s*", " ", "Óculos para visão")` 原样返回
> `'Óculos para visão'` —— Python 3 的 `\b` 是 Unicode 感知的。
>
> 显式 lookaround 仍然值得保留（它给出**可预期的、与语种无关**的边界语义，
> 且与 `tools/scan_lexicon.py` 的 `STRICT` 常量一致），但**理由不是「`\b` 会吞首字母」**。
> 真实理由是上表那三行：数字与下划线。

### 2.2 规则层的重音敏感性（真实的漏检风险）

规则层**不做重音折叠**，正则直接跑在原文上。因此 NFD 分解形式（`u` + `◌̃`
组合符）会**漏检**：

| 输入 | `SBR-PI-001` 结果 |
|---|---|
| `munição de treino`（预组合 NFC） | **命中** |
| `munição de treino`（NFD 分解） | **不命中** |
| `MUNIÇÃO DE TREINO`（大写） | 命中（正则默认 `re.IGNORECASE`） |
| `MUNICAO DE TREINO`（去重音） | 命中（正则里写的是 `[óo]` / `[aá]` 这样的字符类） |

而词库层走 `norm()`（NFD + 去组合附加符），**不受影响**。

> **这条不对称是已知的漏检面**：若上游给的是 NFD 文本，规则层可能漏、
> 词库层仍会命中。词库命中会写进 `evidence_refs`，能作为「规则层可能漏了」的提示。
> **修复方向**（不在本模块职责内）：在 `shopee-br-data-ingestion` 的文本清洗层
> 统一做 NFC 规范化，而不是在规则层加归一化 —— 规则层加归一化会让
> `matched_excerpt` 的偏移与原文对不上。

### 2.3 词库层的组级边界策略

`lexicon/term_groups.json` 的 `group_meta.<group_id>.matching` 决定边界：

| `matching` | 组数 | 边界写法 | 用在哪 |
|---|---|---|---|
| `strict` | 36 | `(?<![a-zA-Zà-ÿÀ-ß]){body}(?![a-zA-Zà-ÿÀ-ß])` | 真品牌名、类目词、禁售词 |
| `loose` | 1 | `{body}`（**无边界**） | `ip_variante_marca`（仿牌拼写变体） |

`loose` 只给 `ip_variante_marca` 用，原因写在 `group_meta` 的 `note` 里：
仿牌词天然与其它文字粘连（`Addidaspreto`、`Rolecx`），严格边界会漏掉最典型的仿牌形态。

实测：

| 文本 | 结果 |
|---|---|
| `Addidaspreto originals` | 命中 `ip_variante_marca`（loose） |
| `Nikex informado` | **不**命中 `ip_marca_global`（strict） |
| `Óculos para visão` | **不**命中 `ip_marca_global`（strict） |

---

## 3. 已知误报来源清单

以下每一类都有**实测证据**，不是推测。

### 3.1 工具类商品被判为武器（`proibido_armas`）

菜刀、剪刀、螺丝刀、美工刀是工具，不是武器。`SBR-PI-001` 的正则只匹配
火器 / 弹药 / 电击枪 / 防弹衣，**不含** `faca` / `canivete` —— 所以规则层不会误判。
但词库组 `proibido_armas` 里也没有这些工具词。

> 真正的误报源是**豁免的组级作用域**：见 §4.2。

### 3.2 功能描述被当成夸大宣称（`proibido_garantia` / `violacao_qualidade`）

`docs/SOP_COMPLIANCE_REVIEW.md` §6 记录了三个高频误报词：

| 词 | 实际语境 | 处置 |
|---|---|---|
| `reduzir` | `reduzir a entrada de água`（功能描述） | **保留**（豁免 `EX-REDUZIR`） |
| `desconforto` | `em caso de desconforto, suspenda o uso`（安全提示） | **保留**（豁免 `EX-DESCONFORTO`） |
| `seguro` | `fechamento seguro`（功能描述） | **保留**（豁免 `EX-SEGURO-FUNCIONAL`） |

> **改这些反而会降低合规性。** 误报控制的价值高于「扫描器数字归零」。

实测（词库层）：

| 文本 | 词库命中 |
|---|---|
| `Kit para Reduzir a Entrada de Água` | 无命中 |
| `Kit para Reduzir a Entrada de Água 100% Eficaz` | `proibido_garantia/100%` 命中且**带豁免** `EX-REDUZIR`（`confidence: low`）；同时 `violacao_qualidade/100% eficaz` 命中且**无豁免**（`confidence: high`） |

注意后者：`violacao_qualidade` 组**没有** `EX-REDUZIR` 豁免规则，所以
「100% eficaz」在这组上照样命中。**豁免是按组配的，不是全局的。**

### 3.3 品牌词出现在描述里

`Compatível com Samsung Galaxy S21` 会命中 `ip_marca_global / Samsung`。
指示性使用（兼容性描述）在法律上是合法的，但**本模块不做 IP 判定** ——
这条命中走 `contracts/lexicon_rule_map.json` 映射到 `SBR-IP-001` 与 `SBR-LV-004`，
其中 `SBR-IP-001` 属 `shopee-br-ip-review`，**本模块的 `candidate_rules()` 会按
`OWNED_PREFIXES` 把它过滤掉**；`SBR-LV-004` 只在标题里出现**两个及以上**品牌名时才命中。

> 因此「描述里出现一个品牌名」在本模块**不产生任何结论**，只会作为
> `EV-LEX-*` 证据条目出现。

### 3.4 主观宣传用语

`melhor`、`premium`、`top`、`#1`、`frete grátis` 都在 `proibido_garantia` 组里。
实测：

| 文本 | 词库命中 | 规则层 |
|---|---|---|
| `Cerveja lager premium` | `proibido_garantia/premium`（无豁免） | 不命中任何规则（`SBR-LV-001` 的正则不含 `premium`） |

> 规则层与词库层的词表**不是同一套**。词库更宽（用于筛查与改写），
> 规则层更窄（用于判定）。词库命中不改变结论。

### 3.5 认证标志的事实陈述

`CE`、`ANVISA`、`INMETRO` 等在 `certificacao_marca` 组里。该组的
`group_meta` 明确标注：`'FDA Approved' 是错误说法（FDA 不批准化妆品/食品上市）；
'CE' 是欧洲合规标志非质量认证`。

实测：

| 文本 | 词库命中 |
|---|---|
| `Produto com o selo CE` | `certificacao_marca/CE`，带豁免 `EX-CE-FACT`（`confidence: medium`） |
| `Item possui CE` | 同上 |
| `Produto impresso com o selo CE` | `certificacao_marca/CE`，**无豁免**（`confidence: high`） |

> 最后一条是豁免正则的边界：`EX-CE-FACT` 的模式是
> `\b(produto|item|artigo)\s+(impresso|com|possui|apresenta)\s+(o\s+)?(selo\s+)?CE\b`
> —— 「Produto impresso com o selo CE」在 `impresso` 与 `com` 之间多了一个词，
> 不匹配该模式。**豁免不覆盖所有自然表达**，未命中豁免的仍然是「记录但不拦截」
> （该组只映射到 `SBR-AU-001` 与 `SBR-LV-009`，且 `SBR-LV-009` 判的是
> 「商品页自称**无**注册信息」，不是「提到注册信息」）。

### 3.6 「没有图片」被当成「图片质量差」

`SBR-LV-007` 的实际触发条件是 `image_count_lt 1`，即**图片张数为 0**。
平台的 `[606]` 说的是「imagem de baixa qualidade, inapropriada ou fora do contexto」
（图片质量低 / 不当 / 与商品无关），本规则**只判得动「一张图都没有」**，
质量维度要靠 `evidence_required` 里的 `image_review` 交给人看。

> **同理**：`SBR-LV-006`（`[605]`）判的是描述**字符数 < 120**，
> 不是内容质量；`SBR-LV-009` 判的是「页面里出现了注册字样」，
> 不是「注册有效」。这些边界写在 `references/audit_semantics.md` §5.2。

### 3.7 尺寸 / 重量类

`SBR-LV-013` 的触发条件只匹配「声明了完整三维尺寸」这一事实。
**平台未公开尺寸与重量上限数值**（禁止引用未公开数值），
所以是否超限由人工复核 —— 规则动作恒为 `flag_for_review`，不阻断。

### 3.8 类目 / 品牌的「空」

`SBR-LV-008`（类目）与 `SBR-LV-011`（品牌）用的是 `field_missing` 算子。
实测：键缺失、`null`、`""`、纯空白串 `"  "` **全部命中**。

这是**有意**的：平台要求这两个字段不得留白。
但要注意它与 H3 的边界 —— 这里「缺失」是要被检出的**违规事实**，
不是数据缺口。规则 `SBR-LV-008` 的 `notes` 写明：
*"Only evaluated when the input carried a category column."*

---

## 4. 豁免机制（`lexicon/exemptions.json`）

### 4.1 权威定义与读取位置

豁免规则由 `shopee-br-data-ingestion` 拥有，定义在 `lexicon/exemptions.json`；
本模块**只读不写**，通过 `tools/scan_lexicon.py` 的 `Scanner` 使用。

`Scanner._build()` 把每条豁免编译成 `(id, pattern, action, reason)` 四元组，
按 `group_id` 归档；`scan_text()` 命中词后**逐条**试该组的豁免正则，
**第一条匹配就停**（`break`），并把 `exempt` 写进命中记录。

### 4.2 三种 `action` 与 `confidence` 的对应

| `action` | `hit["confidence"]` | 语义 |
|---|---|---|
| `exempt` | `low` | 判定为误报场景 —— 命中仍记录，但降置信度 |
| `flag_low` | `medium` | 记录但不拦截 |
| `require_review` | `medium` | 默认仍按（可能的）违规命中，转人工复核上下文 |

未被豁免命中的词条 `confidence` 恒为 `high`。

**豁免 ≠ 放行。** 豁免只影响词库命中记录里的 `confidence` 字段，
**不影响规则层的任何判定**。规则层用的是自己的正则和自己的证据要求。

> **豁免的组级作用域（重要）**
> `scan_text()` 是**逐文本**判定的：一旦该文本命中某条豁免正则，
> **该组内所有命中词**都会带上同一个豁免标记。
>
> 实测：`Munição de Treinamento para Pistola de Plástico. Kit inclui Faca de Cozinha.`
> → `proibido_armas` 组的 3 个命中（`municao` / `munição` / `pistola`）**全部**
> 被打上 `EX-TOOLS`、`confidence` 降为 `low`。
> 而同一段文字去掉刀具那句，3 个命中的 `confidence` 回到 `high`。
>
> **但规则层不受影响** —— `SBR-PI-001` 照样命中，因为它的正则只认
> `pistola` / `munição` 这类词，不认 `faca`。豁免降的是**词库信号的置信度**，
> 不是规则的判定。

### 4.3 七条豁免逐条说明

| ID | `group_id` | `action` | 场景 | 触发模式要点 |
|---|---|---|---|---|
| `EX-TOOLS` | `proibido_armas` | `exempt` | 菜刀 / 剪刀 / 螺丝刀 / 美工刀属工具类 | `\b(faca|facas|tesoura|tesouras|chave de fenda|chave phillips|alicate|estilhaco|multiplasca|canivete)\b` |
| `EX-CE-FACT` | `certificacao_marca` | `flag_low` | 「产品印有 CE 标志」是事实陈述 | `\b(produto\|item\|artigo)\s+(impresso\|com\|possui\|apresenta)\s+(o\s+)?(selo\s+)?CE\b` |
| `EX-HERMES-CARRIER` | `ip_marca_global` | `require_review` | `Hermes` 是快递 / 物流商名 | 物流词与 `Hermes` 同现（两个方向都匹配） |
| `EX-REDUZIR` | `proibido_garantia` | `exempt` | 功能描述（`reduzir a entrada de água`） | `\breduzir\b` |
| `EX-DESCONFORTO` | `proibido_garantia` | `exempt` | 安全提示语 | `\b(em caso de\s+)?desconforto\b` |
| `EX-SEGURO-FUNCIONAL` | `proibido_garantia` | `exempt` | 功能描述「安全闭合」 | `\b(fechamento\|encaixe\|trava\|suporte\|fixacao)\s+seguro\w*` |
| `EX-BRAND-GENERIC` | `ip_marca_global` | `require_review` | 品牌名可能是产品通用词 | 通用词（`vidro` / `maleta` / `case` / `bolsa` / `cabide` / `suporte` / `organizador` / `abertura` / `fechadura`）与品牌名同现 |

> `EX-BRAND-GENERIC` 的 `action` 是 `require_review` 而不是 `exempt` ——
> 意图是「**默认仍按侵权命中**，但要人看上下文」。
> 这与 `docs/SOP_COMPLIANCE_REVIEW.md` §6 的原则一致：
> 「品牌名作为产品通用词 → **默认仍按侵权命中**」（不是自动放行）。

实测 `EX-BRAND-GENERIC`：

| 文本 | 结果 |
|---|---|
| `Tênis Nike Copo de Vidro` | `ip_marca_global/Nike` 命中，带豁免 `EX-BRAND-GENERIC`，`confidence: medium` |
| `Copo de Vidro` | 无命中（该组没有命中词） |

实测 `EX-HERMES-CARRIER`：

| 文本 | 结果 |
|---|---|
| `Entrega feita pela transportadora Hermes para todo o Brasil` | `ip_marca_global/Hermes` 与 `Hermès` 两条命中，均带豁免 `EX-HERMES-CARRIER`，`confidence: medium` |

> 词库里 `Hermes` 与 `Hermès` 是**两个词条**，所以一次文本扫描会出**两条命中**、
> 两个 `EV-LEX-*` 证据条目。这是「同一条目双写」而不是重复 bug。

### 4.4 豁免在产出里的位置

豁免信息出现在两处：

1. **`evidence_refs[]`** —— `EV-LEX-<group_id>-<term>` 条目的 `notes`：
   `lexicon screening hit 'pistola' in group 'proibido_armas' (field title); a lexical hit is a signal, not a violation finding; exemption EX-TOOLS applied (工具类（菜刀/剪刀/螺丝刀/美工刀）不属武器。来源：合规扫描 SOP 错误案例 1。)`
2. **`provenance.notes`** —— 汇总行：
   `lexicon screening: 2 hit(s) in 1 group(s); 2 exempted (EX-TOOLS)`

`provenance.notes` 里还有逐条规则的来源摘要，形如
`SBR-PI-001 | tier=platform_official | status=active | v1 | last_verified=2026-10-27 | source_excerpt='[317] …'`。

---

## 5. 词库 → 规则的映射边界

`contracts/lexicon_rule_map.json` 的 `principles` 声明了四条原则：

1. 一个词组可映射多条规则（如「冒牌描述词」既触 IP 也触质量）
2. 映射到规则的 severity 不得高于该规则的 severity（**词库不能放大风险**）
3. `source.tier = internal_risk` 的词组只能映射到 flag 级规则
4. 未在此表列出的词组不产生规则触发 —— 只作为扫描提示

实测覆盖情况：

| 项 | 数量 |
|---|---|
| 词库组总数 | 105（210,439 词，2026-10-28 集成扩充 + 肉毒/蜂毒补齐后；原 37 组 / 856 词） |
| 映射条目数 | 105 |
| 映射到本模块前缀（`PI`/`RI`/`MED`/`LV`）的组 | 95 |
| 只映射到他模块前缀的组 | 10（`ip_marca_cn`、`ip_marca_br`、`ip_entretenimento`、`ip_esportes`、`ip_variante_marca`、`ip_copyright`、`ip_shopee_asset`、`platform_ip_explicit`、`platform_ip_signal_terms`、`ip_cti_registered_marks`） |

`lexicon.py` 的 `candidate_rules()` 只保留 `OWNED_PREFIXES` 的规则：

```python
for hit in hits:
    for rule_id in rule_map.get(group_id, []):
        prefix = str(rule_id).split("-")[1] if "-" in str(rule_id) else ""
        if prefix not in owned_prefixes:
            continue
        candidates.setdefault(rule_id, []).append(hit)
```

> **注意**：`candidate_rules()` 的输出（`evaluation["lexical_candidates"]`）在
> `engine.py` 里被计算并保存，但**不进入 `AuditResult`**。
> 它只作为调试信息供 `evaluations[]` 使用 —— 候选规则**不会**因为词库命中而命中。
> 词库命中进入产出的唯一途径是 `evidence_refs[]` 里的 `EV-LEX-*` 条目。

### 5.1 词库 `source_tier` 的分布

| `source_tier` | 组数 |
|---|---|
| `platform_official` | 25 |
| `internal_risk` | 12 |

`internal_risk` 的 12 组：`proibido_licenca`、`restrito_auto`、`ip_marca_global`、
`ip_marca_cn`、`ip_marca_br`、`ip_entretenimento`、`ip_esportes`、`ip_variante_marca`、
`certificacao_marca`、`violacao_qualidade`、`violacao_spam`、`violacao_atributo`。

`group_meta` 的 `note` 里有两条直接与误报有关的警示：

- `proibido_licenca`：*「这类词常出现在『无证销售』的表述中；命中不等于商品本身违规，需上下文判定」*
- `violacao_spam`：*「'black friday'/'frete grátis'/'promoção' 等词在 proibido_garantia …」*

> `violacao_spam` 组的词（`compre já`、`desconto imperdível`、`oferta relâmpago`、
> `por tempo limitado`、`promoção relâmpago`、`só hoje`、`última chance`）映射到
> `SBR-LV-002` 与 `SBR-LV-003`。但 `SBR-LV-002` 的正则判的是
> **折扣数字与划线价**，不是促销话术 —— 所以「Black Friday」本身不触发规则。

---

## 6. 什么时候命中只是「信号」，必须人工看

以下任一情形下，即使规则命中，结论也**必须**由人确认，不得自动执行：

| # | 情形 | 代码里的表现 | 为什么 |
|---|---|---|---|
| 1 | 命中的是**文案措辞**，不是结构事实 | `confidence: likely`（非结构算子） | `regex` 只能证明「这句话写了」，证明不了「商品是这件东西」 |
| 2 | `confidence == "signal"` | 非权威来源 / 非 `active` / IP 类 | 同上，且更弱 |
| 3 | 规则本身要求人工复核 | `requires_human_review: true`（本模块 41 条里 36 条；规则文件字段名 `human_review_required`） | 规则作者显式声明「这需要人判断」 |
| 4 | 命中被降级过 | `downgrade_reason` 非空 | 降级说明「本来想做的结论做不成」，必须有人补位 |
| 5 | 存在 `unevaluated[]` 条目 | `requires_human_review: true` | 有维度根本没跑，不能当合规 |
| 6 | 词库筛查没跑成 | `lexicon_state == "unevaluated"` | 少了一层信号 |
| 7 | 动作是 `require_evidence` | 矩阵里 `always_human_review: true` | 缺材料，且材料可能根本拿不到 |
| 8 | 动作是 `block` / `freeze_relist` / `escalate_legal` | 矩阵里 `always_human_review: true` | 阻断必须有人签字 |

`review_rationale` 会把上述原因逐条列出：

```
manual review needed: action 'block' always requires human review; rule SBR-PI-001 requires human review; confidence is 'likely' (keyword/screening level only)
```

### 6.1 「命中但上下文不明确」时的行为

**不猜测。** 具体做法：

- 规则的 `evidence_required` 列出的材料，以 `provided: false` 的
  `EV-<rule_id>-REQ-<type>` 条目形式出现在 `evidence_refs[]` 里，
  `artifact_ref` 为 `null`；
- `reason` 里带上命中的字段与片段（`matched in <field>: <excerpt>`），
  片段限长 160 字符、前后各 40 字符上下文；
- `review_rationale` 说明「需要人判断什么」。

---

## 7. 反例是强制项

**每条 `active` 规则都必须有正例与反例。** 反例缺失的规则不得标记 `active`。

实测覆盖情况（`tests/shopee-br-listing-audit/fixtures/listing_audit_rule_cases.json`）：

| 项 | 数量 |
|---|---|
| 夹具用例总数 | 71 |
| 正例 | 33 |
| 反例 | 33 |
| 缺失类（H3） | 3 |
| 边界类 | 2 |
| 覆盖的规则数 | **34 / 34**（本模块全部 `PI`/`RI`/`MED`/`LV` 规则） |
| 未覆盖的规则 | **0** |

共享夹具（`tests/fixtures/**`，只读）另有 16 条本模块规则的断言，
分布在 `edge_cases.json`（10）、`injection_cases.json`（3）、
`missing_data_cases.json`（5）。

### 7.1 反例的来源

| 来源 | 说明 |
|---|---|
| `docs/SOP_COMPLIANCE_REVIEW.md` §6 | 4 类已知误报模式（工具类 / Hermes 物流 / CE 事实陈述 / 品牌通用词）与 3 个高频误报词（`reduzir` / `desconforto` / `seguro`） |
| `docs/SOP_COMPLIANCE_REVIEW.md` §7 | 店主 2026-09 审阅 491 个商品发现的模板化问题。**这是内容质量问题，不是违规问题** —— 491 个商品详情完全相同，店主判定「最严重」，但它对应的是改写流程（`references/lexicon_scanning.md` §6），不是审核阻断。审核侧只把它记成 `SBR-LV-006`（描述不足）等结构性问题 |
| 规则 `notes` 字段 | 每条改过的规则都记了改动原因。例如 `SBR-RI-003` v2：*「原正则中 `bateria(s)?\s+(...)?` 的 `?` 让「bateria」单独即可命中，会把普通工具（如电钻）判为电池类（实测误报）。改为电池词必须带类型限定词」* |

---

## 8. 上下文判定的操作准则

当规则命中但上下文可能改变结论时，人工按下面的顺序看：

| 步骤 | 看什么 | 例子 |
|---|---|---|
| 1 | 命中在哪个字段 | `matched_field` 是 `title` 还是 `description` |
| 2 | 命中的完整片段 | `matched_excerpt`（含前后 40 字符上下文） |
| 3 | 该规则要什么证据 | `rule_refs[].rule_id` → 规则库里的 `evidence_required` |
| 4 | 哪些证据还缺 | `evidence_refs[]` 里 `provided: false` 的条目 |
| 5 | 词库信号与规则是否一致 | `EV-LEX-*` 条目 —— 词库没命中但规则命中，说明规则用的是更精确的模式；反过来则说明词库更宽 |
| 6 | 有没有豁免 | `EV-LEX-*` 的 `notes` 里的 `exemption <ID> applied (<reason>)` |

**不允许**做的事：

- ❌ 因为「看起来是误报」就**修改结论**（结论是规则层 + 矩阵层的机械产物，不接受主观覆盖）；
- ❌ 把词库命中当作违规证据（词库只产出 `EV-LEX-*`）；
- ❌ 引用未公开的平台数值（处罚点分值、尺寸上限）—— 见 `references/policy_currency.md` §5；
- ❌ 在没有实物/证照的情况下把 `require_evidence` 升级为 `block`；
- ❌ 把 `unevaluated` 的维度当成已通过。

---

## 9. 误报控制的量化基线

用本模块 71 个夹具用例跑一遍（本仓库实测）：

| 指标 | 数值 |
|---|---|
| 结果数 | 71 |
| `verdict` 分布 | `REVIEW` 57 / `BLOCK` 13 / `PASS` 1 |
| `action` 分布 | `flag_for_review` 48 / `block` 13 / `require_evidence` 9 / `allow` 1 |
| `confidence` 分布 | `likely` 55 / `confirmed` 16 |

唯一的 `PASS` 是 `LA-LV007-NEG`（有图片、描述 ≥ 120 字符、类目与品牌完整的
`Kit 4 Copos de Vidro 250ml`）：

```
verdict PASS / action allow / risk_level info / confidence confirmed / requires_human_review false
reason: all 34 applicable rule(s) were evaluated against LA-LV007-NEG and none fired;
        no prohibited, restricted, medicine or listing-quality signal was found
rule_refs: []
evidence_refs: []
```

> 71 个用例里只有 1 个是 `PASS` —— 因为夹具是**按规则构造**的，
> 绝大多数用例都命中至少一条规则。这不代表真实批次的分布。
>
> 词库层面的命中数在 `provenance.notes` 里单独汇总，
> 形如 `lexicon screening: 2 hit(s) in 1 group(s); 2 exempted (EX-TOOLS)`。
> **词库命中数不参与 verdict 计算**。
