# 证据要求与证据链规范

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-LA-002` |
| 所属模块 | `shopee-br-listing-audit` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 各类判定的证据要求、`evidence_required` 的作用、证据链构造规则 |
| 相关文档 | `contracts/evidence_reference.schema.json`、`contracts/audit_result.schema.json`、`references/audit_semantics.md`、`references/policy_currency.md` |
| 未决事项 | 无 |

---

## 1. 硬约束 H5 —— 只存引用，不存内容

> `H5`：`evidence_refs` 的 `artifact_ref` 只存引用，**禁止内嵌完整凭证或授权文件内容**。

`contracts/evidence_reference.schema.json` 的字段说明原文：
`"引用（路径或外部工单号）。禁止内嵌完整凭证或授权文件内容。"`

`PROJECT_RULES.md` §9 同样写明：`artifact_ref` **引用**（路径或外部工单号），**不存内容**。

**证据本体（图片、授权书扫描件、发票 PDF）留在原处。** 审核结果里只记路径与元信息，
由人去原处取件。

### 1.1 本模块的落地方式（实测）

`engine.py` 的 `_build_evidence_refs()` 生成三类条目，**`artifact_ref` 只有两种形态**：

| 条目类型 | `evidence_id` 形态 | `artifact_ref` | `provided` |
|---|---|---|---|
| 观测证据（规则命中处） | `EV-<rule_id>-<field>`（`.` 替换为 `-`） | `products/<product_id>/<field>` | `true` |
| 待补证据（规则要求但未提供） | `EV-<rule_id>-REQ-<evidence_type>` | **`null`** | `false` |
| 词库筛查命中（佐证信号） | `EV-LEX-<group_id>-<term>`（空格替换为 `-`） | `products/<product_id>/<field>` | `true` |

> **「待补证据」不是「缺失的证据记录」** —— 它是「**关闭这条规则需要的材料清单**」。
> 它的 `artifact_ref` 恒为 `null`，因为材料**还没提供**，没有路径可指。
> 它的 `notes` 恒为：
>
> ```
> required to close <rule_id>; the module does not store credential contents (hard constraint H5)
> ```

测试里的断言（`tests/shopee-br-listing-audit/run_tests.py` 的 `L4 / H5` 段）：

| 断言 | 内容 |
|---|---|
| `evidence_refs 不含凭证特征` | 扫 `artifact_ref` / `notes` / `source_locator`，不得出现 OpenAI key、GitHub token、长 base64、私钥、CPF 样式号码 |
| `artifact_ref 只存产品字段路径引用` | 非空 `artifact_ref` 必须以 `products/` 开头 |
| `待补证据标记 provided=false 且 artifact_ref 为空` | 所有 `provided: false` 的条目 `artifact_ref` 必须为 `null` |

---

## 2. `evidence_required` 的作用

### 2.1 它是「关闭条件」，不是「判定条件」

规则库里的 `evidence_required` 有**两个彼此独立的用途**：

| 用途 | 由谁执行 | 影响什么 |
|---|---|---|
| **判定**（规则命中与否） | `trigger_conditions` + `conditions.py` | 决定规则是否命中 |
| **关闭条件**（命中后还差什么） | `evidence_required` + `_build_evidence_refs()` | 决定 `evidence_refs[]` 里列出哪些待补材料 |

> **`evidence_required` 不参与命中判定。** 一条规则的 `evidence_required` 是空的
> （如 `SBR-LV-003` 关键词堆砌），它照样会命中、照样产出 `rule_refs[]` 与
> `flag_for_review` 结论 —— 只是没有待补材料清单。

### 2.2 它如何影响动作

**`evidence_required` 不直接决定动作。** 动作由规则的 `decision` 声明、
再经矩阵查表得到。`evidence_required` 影响的是**结论的语义**：

| `decision` | `evidence_required` 非空时的含义 |
|---|---|
| `require_evidence` | **这些材料就是补齐清单**。补齐前不得上架（`verdict: REVIEW`） |
| `block` | 商品不得上架。列出的材料（如 `product_photographs`）是**给人工确认实物用的**，不是「补齐就能上架」 |
| `flag_for_review` | 材料是**判断依据**。`SBR-LV-001` 要 `manufacturer_claim_reference` —— 没有它就无法判断「夸大宣称」是否属实 |

### 2.3 本模块的 `evidence_required` 分布（实测）

| 规则 | `evidence_required` |
|---|---|
| `SBR-PI-001` | `product_photographs`、`supplier_invoice` |
| `SBR-PI-002` | `product_photographs`、`supplier_invoice` |
| `SBR-PI-003` | `anvisa_registration`、`supplier_invoice` |
| `SBR-PI-004` | `product_photographs`、`supplier_invoice` |
| `SBR-PI-005` | `product_photographs` |
| `SBR-PI-006` | `product_photographs` |
| `SBR-PI-007` | `product_photographs`、`supplier_invoice` |
| `SBR-PI-008` | `product_photographs`、`supplier_invoice` |
| `SBR-PI-009` | `product_photographs` |
| `SBR-RI-001` | `supplier_invoice`、`distribution_authorization`、`product_photographs` |
| `SBR-RI-002` | `anvisa_registration`、`supplier_invoice` |
| `SBR-RI-003` | `product_photographs`、`supplier_invoice` |
| `SBR-RI-004` | `homologation_certificate`、`supplier_invoice` |
| `SBR-RI-005` | `sanitary_registration`、`product_photographs` |
| `SBR-RI-006` | `mapa_registration`、`supplier_invoice` |
| `SBR-RI-007` | `product_photographs`、`supplier_invoice` |
| `SBR-RI-008` | `sanitary_registration`、`product_photographs` |
| `SBR-MED-001` | `product_photographs`、`supplier_invoice`、`anvisa_registration` |
| `SBR-MED-002` | `anvisa_registration`、`pharmacy_license`、`distribution_authorization`、`supplier_invoice` |
| `SBR-MED-003` | `manufacturer_claim_reference`、`product_photographs` |
| `SBR-LV-001` | `manufacturer_claim_reference`、`product_photographs` |
| `SBR-LV-002` | `price_history`、`promotion_terms` |
| `SBR-LV-003` | （空） |
| `SBR-LV-004` | （空） |
| `SBR-LV-005` | （空） |
| `SBR-LV-006` | （空） |
| `SBR-LV-007` | `image_review` |
| `SBR-LV-008` | （空） |
| `SBR-LV-009` | `homologation_certificate`、`anvisa_registration`、`anatel_registration`、`inmetro_certificate` |
| `SBR-LV-010` | （空） |
| `SBR-LV-011` | （空） |
| `SBR-LV-012` | `product_measurements` |
| `SBR-LV-013` | `product_measurements` |
| `SBR-LV-014` | （空）—— `draft`，不参与判定 |

统计：15 种不同的证据类型键；8 条规则的 `evidence_required` 为空。

### 2.4 `evidence_type` 与契约的关系

`contracts/evidence_reference.schema.json` 的 `evidence_type` 是**自由字符串**
（`minLength: 2`），`examples` 列了一批建议值。本模块用到 15 种键：

| 键 | 出现在契约的 `examples` 里 |
|---|---|
| `product_photographs`、`supplier_invoice`、`anvisa_registration`、`distribution_authorization`、`homologation_certificate`、`sanitary_registration`、`mapa_registration`、`pharmacy_license`、`manufacturer_claim_reference`、`image_review`、`product_measurements` | ✅ |
| `price_history`、`promotion_terms` | ❌ **不在** `examples` 里（`SBR-LV-002` 使用） |

> 契约的 `examples` **不是** `enum` —— `evidence_type` 只有 `minLength: 2` 约束，
> 所以 `price_history` / `promotion_terms` **完全合法**，产出也通过了
> `contracts/audit_result.schema.json` 的校验（`L2 契约测试` 段）。
>
> **含义**：契约的 `examples` 是一份**建议清单**，不是封闭集合。
> 新增证据类型键不需要改契约。若要让这两项出现在清单里，
> 属于**契约变更建议**（见 `DELIVERY.md` §5）。

---

## 3. 受限类目需要什么材料

受限类目（`SBR-RI-*`）的语义是「**商品可以卖，但需要资质 / 授权 / 注册才能卖**」。
因此材料清单围绕三件事：**这商品受哪个机构管、卖方有没有资质、货从哪来**。

### 3.1 按监管机构对应材料

| 监管机构 | 对应 `evidence_type` | 出现在哪些规则 |
|---|---|---|
| **ANVISA**（药品、健康品、化妆品、器械） | `anvisa_registration` | `SBR-RI-002`、`SBR-MED-001`、`SBR-MED-002`、`SBR-LV-009` |
| **MAPA**（兽药、宠物用品） | `mapa_registration` | `SBR-RI-006` |
| **INMETRO**（工业认证、婴童安全、太阳镜） | `inmetro_certificate` | `SBR-LV-009` |
| **ANATEL**（电信设备） | `anatel_registration` | `SBR-LV-009` |
| **汽车零部件监管机构** | `homologation_certificate` | `SBR-RI-004`、`SBR-LV-009` |
| **卫生 / 市政（Alvará、Licença Sanitária、AFE）** | `sanitary_registration` | `SBR-RI-005`、`SBR-RI-008` |
| **持牌药房 / 药店** | `pharmacy_license` | `SBR-MED-002` |
| **分销授权** | `distribution_authorization` | `SBR-RI-001`、`SBR-MED-002` |
| **采购凭证** | `supplier_invoice` | 14 条规则 |

### 3.2 平台对受限类目的材料要求（逐字原文）

来源：`research/raw/shopee_br_produtos_restritos_liberacao.txt`
（`source.url` =
`https://seller.br.shopee.cn/edu/article/12544/como-solicitar-a-liberacao-para-venda-de-produtos-restritos`，
`article_id` = `12544`，`last_verified` = 2026-10-27）

> `Anúncios de produtos restritos são aqueles que podem exigir análise prévia, apresentação de documentação comprobatória, autorização específica ou liberação da categoria antes de serem comercializados na plataforma.`
>
> `A venda de produtos restritos sem autorização, documentação válida ou cadastro correto poderá resultar na remoção do anúncio e na aplicação de penalidades à conta do vendedor.`

该页面还给出了**保健品**（对应 `SBR-RI-002`）的具体材料清单示例：

> `Alvará ou Licença Sanitária vigente ou AFE (Autorização de Funcionamento de Empresa). Em casos excepcionais, conforme a regulamentação vigente, também será aceito comprovante oficial de Dispensa de Alvará. Em caso de dúvidas, procure o órgão responsável para mais informações.`
>
> `Notas Fiscais de 4 suplementos de marcas diferentes, emitidas nos últimos 6 meses, com quantidades compatíveis com o volume de revenda. Se você revende apenas uma marca, envie as notas fiscais dos 4 produtos mais vendidos dessa marca.`

> 这些是**平台页面上的具体要求**，用来解释 `evidence_required` 各项的含义。
> **模块本身不解析材料内容** —— 它只声明「需要哪一类材料」，
> 由人按平台要求去准备。

### 3.3 缺材料时的动作 —— `require_evidence`，**不是** `block`

**这是本模块最容易搞错的一条。**

受限类目命中后，缺材料**不等于**商品违规。正确的动作是 `require_evidence`
（`verdict: REVIEW`），语义是「**在补齐 `evidence_required` 指定的材料前不得上架**」
（`contracts/risk_action_matrix.json` → `actions.require_evidence.description`：
*"在补齐 evidence_required 指定的材料前不得上架。"*）。

| 情形 | 动作 | `verdict` |
|---|---|---|
| 受限类目命中，材料齐全（人已核对） | `require_evidence` → 人工确认后可上架 | `REVIEW` |
| 受限类目命中，材料缺失 | `require_evidence` | `REVIEW` |
| 受限类目命中，**但**卖方明确无资质（如 `SBR-MED-002` 拿不出 `pharmacy_license`） | 由人决定**不得上架** | —— 但**结论动作仍是 `require_evidence`** |
| 禁售类目命中（`SBR-PI-*`） | `block` | `BLOCK` |
| 未巴氏杀菌乳制品（`SBR-RI-008`，政策原文是「Proibidos (para todos os vendedores)」） | `block` | `BLOCK` |

> **实测**：一个酒精饮料 listing 的产出是
> `verdict: REVIEW / action: require_evidence / risk_level: high / confidence: likely`，
> `evidence_refs[]` 里同时有 4 条观测证据与 3 条待补证据
> （`supplier_invoice` / `distribution_authorization` / `product_photographs`）。

**为什么不能是 `block`**：

1. 商品本身可能完全合法 —— 酒本身不违法，缺的是**卖家的分销授权**；
2. 缺材料是**数据缺口**，不是「已确认违规」的证据；
3. `block` 的语义是「不得上架」，把「还没交材料」等同于「违规」会误伤合规卖家。

**`require_evidence` 与 `block` 的区别在下游**：
`require_evidence` 是「**补齐后复审**」，`block` 是「**不得上架**」。
`shopee-br-reporting` 会按 `action` 区分这两类的呈现。

### 3.4 禁售类目为什么也列证据

`SBR-PI-001` 的 `evidence_required` 是 `product_photographs` + `supplier_invoice`，
动作却是 `block`。这两者不矛盾：

> **禁售类目的材料不是「补齐就能上架的门槛」，而是「确认这个判定对不对」的依据。**

规则在文案上判定「这件商品是武器」，但**文案不能证明实物是什么**。
`product_photographs` 用来确认实物，`supplier_invoice` 用来确认货源。
人看完之后如果认为判定错了，**走的是申诉 / 复核流程，不是改 `action`**。

这也是为什么 `SBR-PI-*` 全部 `human_review_required: true` —— 阻断必须有人签字。

---

## 4. 证据链的构造

### 4.1 一条完整证据链的四个层次

```
① 结论        AuditResult.verdict / action / risk_level / confidence
      ↓
② 规则引用    rule_refs[] —— 命中的规则 + 命中字段 + 命中片段 + 来源层级 + 来源 URL
      ↓
③ 观测证据    evidence_refs[] 里 provided=true 的条目 —— 命中发生在哪个字段、原文是什么
      ↓
④ 待补证据    evidence_refs[] 里 provided=false 的条目 —— 关闭这条结论还差哪些材料
```

### 4.2 各层的字段来源

| 层 | 字段 | 来源 | 实现 |
|---|---|---|---|
| ① | `verdict` | 由 `action` 查 `contracts/risk_action_matrix.json` | `matrix.py` 的 `verdict_for()` |
| ① | `action` | 规则声明 + 矩阵查表 + H2 降级 | `engine.py` 的 `_resolve_action()` / `_align_combo()` |
| ① | `risk_level` | 命中规则的最重 `severity` | `engine.py` 的 `build_result()` |
| ① | `confidence` | 命中规则里最弱的 `confidence` | `engine.py` 的 `_confidence()` |
| ② | `rule_id` / `title` | 规则 | `engine.py` 的 `_build_rule_ref()` |
| ② | `matched_field` | 命中条件声明的 `field` | 同上 |
| ② | `matched_excerpt` | 命中片段（前后 40 字符上下文，限长 160 字符） | `conditions.py` 的 `_excerpt()` |
| ② | `source_tier` / `source_url` | 规则的 `source` | `rules.py` 的 `normalise_rule()` |
| ③ | `artifact_ref` | `products/<product_id>/<field>` | `engine.py` 的 `_build_evidence_refs()` |
| ③ | `notes` | `rule <rule_id> matched here: <excerpt>` | 同上 |
| ④ | `evidence_type` | 规则的 `evidence_required` 条目 | 同上 |
| ④ | `notes` | `required to close <rule_id>; the module does not store credential contents (hard constraint H5)` | 同上 |

### 4.3 `source_locator` 与 `collected_at`

| 字段 | 本模块的取值 | 说明 |
|---|---|---|
| `source_locator` | 观测证据 = 命中字段名（如 `description`、`image`、`any_text`）；待补证据 = `null` | `contracts/evidence_reference.schema.json` 的说明是「原始定位，如 'row 42'、'line 7'、'sheet1!C7'」—— 本模块给的是**字段名**，不是行号 |
| `collected_at` | 恒为 `null` | 采集时间由上游 `shopee-br-data-ingestion` 负责，本模块不重新采集 |

### 4.4 `evidence_type` 的两个取值来源

| 取值 | 何时出现 | 例子 |
|---|---|---|
| `listing_field` | 文本类命中 | `EV-SBR-PI-001-any_text` |
| `image` | 图片类命中（字段是 `image` 或 `image_text`） | `EV-SBR-LV-007-image` |
| 规则的 `evidence_type` 键 | 待补证据 | `EV-SBR-RI-001-REQ-supplier_invoice` |

> 代码：`evidence_type = "image" if field in ("image", "image_text") else "listing_field"`。

### 4.5 实测的完整产出（受限类目）

输入：`Cerveja Artesanal 500ml Pack 6`（无图片，描述 88 字符，含三维尺寸）

```
verdict: REVIEW   action: require_evidence   risk_level: high   confidence: likely
```

`evidence_refs[]`：

| `evidence_id` | `evidence_type` | `provided` | `artifact_ref` |
|---|---|---|---|
| `EV-SBR-LV-006-description` | `listing_field` | `true` | `products/EV1/description` |
| `EV-SBR-LV-007-image` | `image` | `true` | `products/EV1/image` |
| `EV-SBR-LV-013-any_text` | `listing_field` | `true` | `products/EV1/any_text` |
| `EV-SBR-RI-001-any_text` | `listing_field` | `true` | `products/EV1/any_text` |
| `EV-SBR-LV-007-REQ-image_review` | `image_review` | `false` | `null` |
| `EV-SBR-LV-013-REQ-product_measurements` | `product_measurements` | `false` | `null` |
| `EV-SBR-RI-001-REQ-supplier_invoice` | `supplier_invoice` | `false` | `null` |
| `EV-SBR-RI-001-REQ-distribution_authorization` | `distribution_authorization` | `false` | `null` |
| `EV-SBR-RI-001-REQ-product_photographs` | `product_photographs` | `false` | `null` |
| `EV-LEX-restrito_bebida-cerveja` | `listing_field` | `true` | `products/EV1/title` |
| `EV-LEX-proibido_garantia-premium` | `listing_field` | `true` | `products/EV1/description` |

**读法**：

1. `rule_refs[]` 里有 4 条命中（`SBR-LV-006` / `SBR-LV-007` / `SBR-LV-013` / `SBR-RI-001`）；
2. 每条命中都有对应的**观测证据**（`EV-<rule_id>-<field>`），`notes` 写明命中了什么
   （如 `rule SBR-LV-006 matched here: length 88 < 120`）；
3. 需要补材料的规则（`SBR-LV-007` / `SBR-LV-013` / `SBR-RI-001`）各带若干
   `provided: false` 的条目 —— 这是**待办清单**；
4. `EV-LEX-*` 是词库信号，`notes` 明写
   `a lexical hit is a signal, not a violation finding`。

### 4.6 `unevaluated[]` 与 `evidence_refs[]` 的分工

两者都是「还差东西」，但性质不同：

| | `unevaluated[]` | `evidence_refs[]`（`provided: false`） |
|---|---|---|
| 缺什么 | **输入数据**（字段没值 / 没拿到） | **凭据材料**（授权书、发票、实物照片） |
| 产生条件 | 规则的触发条件依赖的字段为空 | 规则命中了，但 `evidence_required` 未满足 |
| 后果 | 该规则**未被评估**，不能计入通过 | 该结论**已成立**，但关闭它还差材料 |
| 动作 | `flag_for_review`（若其它规则都没命中） | 由命中的规则决定 |

> **两者都不产生 `block`。** 输入缺失（`unevaluated`）与材料缺失
> （`require_evidence`）都是**数据问题**，不是「已确认违规」。

### 4.7 交接记录里的缺口

`ModuleHandoff.known_gaps[]`（`pipeline.py` 的 `_build_handoff()`）会把证据缺口显式列出：

```
2 rule evaluation(s) were skipped because required input was missing; those dimensions are NOT confirmed compliant.
1 rule(s) are not 'active' and produced no conclusion: SBR-LV-014.
2 product(s) carry no image data; image-based checks (image quality, OCR text, logos) were not evaluated for them.
```

`ModuleHandoff.unevaluated[]` 逐条列出 `rule_id` / `reason` / `missing_fields`。

> `assumptions[]` 里的第 1 条把「关键词命中 ≠ 违规」写成了交接前提：
>
> ```
> Detection is keyword- and field-based: a rule firing means the listing text matches
> a documented platform pattern, not that the physical item is what the text claims.
> Every finding needs a human to confirm the actual product.
> ```

---

## 5. 各类判定的证据要求（速查）

| 判定类型 | 代表规则 | 动作 | 证据要求 | 人要判断什么 |
|---|---|---|---|---|
| **禁售** | `SBR-PI-001` … `SBR-PI-009`、`SBR-MED-001`、`SBR-RI-008` | `block` | `product_photographs`、`supplier_invoice`（部分加 `anvisa_registration`） | 实物是不是这件禁售物？判定本身对不对？ |
| **受限** | `SBR-RI-001` … `SBR-RI-007`、`SBR-MED-002` | `require_evidence` | 按监管机构：`anvisa_registration` / `mapa_registration` / `sanitary_registration` / `homologation_certificate` / `pharmacy_license` / `distribution_authorization` / `supplier_invoice` / `product_photographs` | 卖方有没有资质？材料齐不齐？ |
| **药品资质** | `SBR-MED-002` | `require_evidence` | `pharmacy_license`（决定性）、`anvisa_registration`、`distribution_authorization`、`supplier_invoice` | 卖方是不是持牌药房 / 药店？ |
| **保健品宣称** | `SBR-MED-003`、`SBR-LV-001` | `flag_for_review` | `manufacturer_claim_reference`、`product_photographs` | 宣称有没有厂方依据？ |
| **定价** | `SBR-LV-002` | `flag_for_review` | `price_history`、`promotion_terms` | 折扣是不是失实？ |
| **图片** | `SBR-LV-007` | `flag_for_review` | `image_review` | 图片质量 / 是否与商品相符 |
| **注册信息** | `SBR-LV-009` | `flag_for_review` | `homologation_certificate`、`anvisa_registration`、`anatel_registration`、`inmetro_certificate` | 注册是真的吗？属于哪个机构？ |
| **尺寸重量** | `SBR-LV-012`、`SBR-LV-013` | `flag_for_review` | `product_measurements` | 数据是否自洽？是否超出平台上限（**上限未公开，由人确认**）？ |
| **纯文案质量** | `SBR-LV-003` … `SBR-LV-006`、`SBR-LV-008`、`SBR-LV-010`、`SBR-LV-011` | `flag_for_review` | （空） | 直接按 `matched_excerpt` 判断 |

---

## 6. 不允许做的事

| ❌ 不允许 | 为什么 |
|---|---|
| 把凭证内容写进 `artifact_ref` / `notes` / `source_locator` | 违反 **H5**；测试里的敏感信息扫描会拦 |
| 把「材料缺失」写成 `block` | 缺材料是数据缺口，不是已确认违规 —— 见 §3.3 |
| 把词库命中写成 `rule_refs[]` 条目 | 词库只产出 `EV-LEX-*` 证据 |
| 把 `unevaluated` 的维度当成已通过 | 违反 **H3** |
| 在结论里引用平台未公开的数值 | 处罚点分值、尺寸上限 —— 见 `references/policy_currency.md` §5 |
| 引用抓取失败的来源 | `br_anvisa_publicidade_medicamentos`、`br_anvisa_medicamentos_prescricao` 均 HTTP 503 |
| 自行发明 `evidence_type` 键 | 键必须是 `evidence_required` 里声明过的；契约允许新键但必须是既有语义 |
| 把 `provided: false` 的条目当成「证据不存在」 | 它的语义是「**尚未提供**」，不是「已确认不存在」 |

---

## 7. 证据相关字段的速查

`contracts/evidence_reference.schema.json`（`EvidenceReference`）：

| 字段 | 类型 | 必填 | 本模块取值 |
|---|---|---|---|
| `evidence_id` | `string`（`minLength: 4`） | ✅ | `EV-<rule_id>-<field>` / `EV-<rule_id>-REQ-<type>` / `EV-LEX-<group>-<term>` |
| `evidence_type` | `string`（`minLength: 2`） | ✅ | `listing_field` / `image` / 规则的 `evidence_required` 键 |
| `provided` | `boolean` | ✅ | 观测证据与词库命中 = `true`；待补证据 = `false` |
| `artifact_ref` | `string` / `null` | — | `products/<product_id>/<field>` 或 `null` |
| `source_locator` | `string` / `null` | — | 命中字段名 或 `null` |
| `collected_at` | `string`（date-time） / `null` | — | `null` |
| `notes` | `string` / `null` | — | 命中说明 / 待补说明 / 词库说明 |

> `additionalProperties: false` —— **不能加额外字段**。
> 想加信息就写进 `notes`。
