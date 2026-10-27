| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-IP-003` |
| 所属模块 | `shopee-br-ip-review` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 品牌授权材料的核查项、`history` 字段结构、有清单 vs 无清单的语义、INPI 商标注册核验方法 |
| 相关文档 | `rules/04_cases_relist_authorization.json`（只读引用 `SBR-AU-001`）、`contracts/evidence_reference.schema.json`、`research/raw/br_inpi_legislacao_marcas.txt` |
| 未决事项 | INPI 查询为**人工流程**，本模块不提供接口；见 §6 |

---

## 1. 授权维度的数据来源

授权材料清单**不在**独立的输入字段里，而是挂在商品的 `history` 对象下。
读取代码在 `skills/shopee-br-ip-review/src/sbr_ip_review/evaluator.py`：

```
AUTHORIZATION_KEYS = ("authorization_documents", "missing")
```

`history` 的结构（`data/schema/product.schema.json` 里 `history` 是
`additionalProperties: true` 的自由对象）：

```json
{
  "history": {
    "authorization_documents": ["brand_authorization_letter"],
    "missing": []
  }
}
```

| 键 | 含义 | 类型 |
|---|---|---|
| `authorization_documents` | **已提供**的授权材料类型键清单 | 字符串数组 |
| `missing` | **已知缺口** —— 已核查但未取得的材料类型键清单 | 字符串数组 |

两个键都**不存在**时，授权状态是**未知**，不是「未授权」。

## 2. 三种状态与各自的判定后果

`authorization_inventory()` 返回 `{"provided": [...], "missing": [...], "known": bool}`。
`known` 的判定：`history` 是 dict **且**至少含 `authorization_documents` 或 `missing` 之一。

| 情形 | `known` | `missing` | 引擎行为 | 结论语义 |
|---|---|---|---|---|
| **有清单且无缺口** | `true` | `[]` | `SBR-AU-001` **不命中** | 已授权（或至少已核查齐备） |
| **有清单且有缺口** | `true` | `["brand_authorization_letter"]` | `SBR-AU-001` **命中** → `require_evidence` | **无法证明有权销售**，≠ 侵权 |
| **无清单**（`history` 缺失 / 不是 dict / 空 dict / 两个键都没有） | `false` | `[]` | `SBR-AU-001` **记入 `unevaluated[]`**（`missing_fields: ["history"]`） | **状态未知** —— 既不能判「已授权」，也不能判「未授权」 |

> **「无清单 = 状态未知」是本模块的核心语义。**
> 引擎在 `provenance.notes` 里如实写出来：
>
> `no authorisation inventory present — authorisation status is unknown, not 'missing'`
>
> `ModuleHandoff.assumptions` 也把它列为全局前提：
> 「An absent authorisation inventory means the authorisation status is unknown, not 'missing'.」
>
> **绝不能**把「没提供清单」读成「没授权」。那会把数据缺失误判成合规问题。

### 2.1 三种状态的实测输出

| `history` 形态 | `known` | `missing` | `fired` | `unevaluated` | `action` / `verdict` / `risk` |
|---|---|---|---|---|---|
| 键完全缺失 | `false` | `[]` | —— | 含 `SBR-AU-001`（`missing_fields: ["history"]`） | `flag_for_review` / `REVIEW` / low |
| `{}` | `false` | `[]` | —— | 同上 | 同上 |
| `[]`（不是 dict） | `false` | `[]` | —— | 同上 | 同上 |
| `"x"`（不是 dict） | `false` | `[]` | —— | 同上 | 同上 |
| `{"authorization_documents": []}` | `true` | `[]` | 不含 `SBR-AU-001` | 不含 `SBR-AU-001` | `flag_for_review` / `REVIEW` / low |
| `{"missing": []}` | `true` | `[]` | 不含 `SBR-AU-001` | 不含 `SBR-AU-001` | 同上 |
| `{"authorization_documents": [], "missing": []}` | `true` | `[]` | 不含 `SBR-AU-001` | 不含 `SBR-AU-001` | 同上 |
| `{"missing": ["brand_authorization_letter"]}` | `true` | `["brand_authorization_letter"]` | **含 `SBR-AU-001`** | —— | **`require_evidence` / `REVIEW` / high** |
| `{"missing": "brand_authorization_letter"}`（非数组） | `true` | `["brand_authorization_letter"]` | **含 `SBR-AU-001`** | —— | 同上（非数组会被归一化成单元素数组） |
| `{"authorization_documents": "letter.pdf"}`（非数组） | `true` | `[]` | 不含 `SBR-AU-001` | —— | `flag_for_review` / `REVIEW` / low（`provided=["letter.pdf"]`） |

> `{"authorization_documents": []}` 与 `{"missing": []}` 都能让 `SBR-AU-001` **可评估** ——
> 因为 `history_missing_nonempty` 算子在 `missing` 键缺失时返回「不命中但可评估」，
> 在 `missing` 存在但为空时同样返回「不命中但可评估」。
> 二者的差别只在 `provenance.notes` 的措辞与 `provided` 计数。

## 3. 缺材料时的动作：`require_evidence`，不是 `block`

### 3.1 `SBR-AU-001` 自身的声明动作

`SBR-AU-001` 归属 `shopee-br-duplicate-detection`，本模块**只读**引用
`rules/04_cases_relist_authorization.json` 中的这一条：

| 字段 | 值 |
|---|---|
| `category` | `authorization` |
| `severity` | `high` |
| `decision` | **`require_evidence`** |
| `source_tier` | `platform_official` |
| `status` | `active` |
| `evidence_required` | `anvisa_registration` `distribution_authorization` `supplier_invoice` `homologation_certificate` |

`require_evidence` 在 `contracts/risk_action_matrix.json` 的 `actions.require_evidence` 里定义：

```json
"require_evidence": {
  "label": "需补齐证据",
  "description": "在补齐 evidence_required 指定的材料前不得上架。",
  "verdict": "REVIEW",
  "always_human_review": true,
  "executable_by": "human"
}
```

**这条规则永远不会单独产生 `block`。** 它的语义是
「在补齐 `evidence_required` 指定的材料前不得上架」，**不是**「侵权」。

### 3.2 与商标规则同时命中时的聚合

动作取最重（`engine.py` 的 `_ACTION_RANK`：`require_evidence=2` < `escalate_legal=4`）。
所以：

| 情形 | `fired` | `action` | `verdict` | `risk_level` |
|---|---|---|---|---|
| **只有**授权缺口（无品牌词） | `['SBR-AU-001']` | `require_evidence` | `REVIEW` | high |
| 授权缺口 + 品牌词（`brand` 填了他人商标） | `['SBR-IP-001', 'SBR-AU-001']` | `escalate_legal` | `BLOCK` | high |

> ⚠️ **诚实说明**：授权缺口**本身**的动作是 `require_evidence`；
> 但当它与 `SBR-IP-001`（品牌宣称，`escalate_legal`）同时命中时，
> 聚合后的 `action` 是 `escalate_legal`、`verdict` 是 `BLOCK`。
>
> 这个 `BLOCK` **来自品牌宣称规则**，不来自授权缺口。
> 读结论时必须看 `rule_refs` 区分来源 —— 授权缺口那一维始终是
> `require_evidence` 语义（「补材料」），不是「已认定侵权」。

### 3.3 授权不完整的正确表述

```
授权材料缺失/不完整
  → confidence = `signal`（硬约束 H1）
  → action = require_evidence（该维度的语义）
  → requires_human_review = true
  → 不得表述为侵权
```

`SBR-AU-001` 的 `description` 原文：

> A restricted-category item may only be listed with the supporting documentation the platform requires. When the authorisation file is incomplete — for example an invoice but no ANVISA registration for a health product — the listing must not go live on the documentation it has.

平台依据（`research/raw/shopee_br_produtos_restritos_liberacao.txt`，
`source_url=https://seller.br.shopee.cn/edu/article/12544`，`article_id=12544`，
`last_verified=2026-10-27`）：

> O vendedor é responsável por garantir que os produtos anunciados estejam em conformidade com a legislação brasileira, com as normas dos órgãos reguladores aplicáveis e com as políticas da Shopee.

## 4. 授权核查项清单

下表把「规则库声明的证据类型」与「人工复核要查的内容」分开。
**规则库只声明材料类型，不判定材料是否有效** —— 有效性由人判断。

| # | 核查项 | 对应材料类型键 | 缺失的后果 |
|---|---|---|---|
| 1 | 品牌方书面授权存在 | `brand_authorization_letter` | `require_evidence` |
| 2 | 商标注册证明（INPI 查册，见 §6） | `trademark_registration` | `require_evidence` |
| 3 | 供应商发票 / 采购凭证 | `supplier_invoice` | `require_evidence` |
| 4 | 商品实拍图 | `product_photographs` | `require_evidence` |
| 5 | 版权授权书（作品类） | `licence_document` | `require_evidence` |
| 6 | 外观设计登记（`SBR-IP-008`） | `design_registration` | `require_evidence` |
| 7 | 图片人工复核记录 | `image_review` | `require_evidence` |
| 8 | 受限类目资质（`SBR-AU-001`） | `anvisa_registration` `homologation_certificate` `distribution_authorization` | `require_evidence` |

材料类型的完整清单在 `contracts/evidence_reference.schema.json` 的
`evidence_type.examples`。该 Schema 同时约束证据记录的形状：

```json
{
  "evidence_id": "EV-IP-0001-01",
  "evidence_type": "brand_authorization_letter",
  "provided": true,
  "artifact_ref": "authorizations/SKU-0001/authorization.pdf",
  "source_locator": "products.json#/history/authorization_documents/0",
  "collected_at": "2026-10-27T00:00:00Z",
  "notes": "授权方为 INPI 注册权利人，2026 年度有效"
}
```

> **硬约束 H5**：`artifact_ref` **只存引用**（路径或外部工单号），
> **禁止**内嵌授权书正文、扫描件内容或凭证。
>
> `data/schema/case.schema.json` 的 `evidence[]` 用的是另一组字段
> （`evidence_type` / `provided` / `artifact_ref` / `notes` / `collected_at`），
> 与 `contracts/evidence_reference.schema.json` 的 `evidence_id` / `source_locator`
> 不同 —— 写证据记录时注意区分是案件侧还是结果侧。

### 4.1 人工复核要问的、规则库不问的问题

| # | 问题 | 为什么规则库不问 |
|---|---|---|
| 1 | 授权方是**商标权利人**还是有权转授权方？ | 需要查 INPI 登记与授权链，规则库无此数据 |
| 2 | 授权覆盖**本商品品牌**？ | 授权书内容不在输入里（只有材料类型键） |
| 3 | 授权覆盖**本商品类目**？ | 同上 |
| 4 | 授权在**销售期内**？ | 同上 |
| 5 | 授权覆盖**销售地区**（含巴西）？ | 同上 |
| 6 | 授权覆盖**销售主体**（店铺 / CNPJ）？ | 同上 |
| 7 | 多级分销时**授权链**是否逐级可查？ | 同上 |
| 8 | 授权书**真实性**可验证？ | 需要品牌方直接确认 |

> 这 8 项**全部**落在人工身上 —— 输入里只有材料类型键，没有材料内容。
> 声称「授权已通过核查」而不做这 8 项，等于没核查。

## 5. 授权状态在结果里的落点

| 落点 | 内容 |
|---|---|
| `rule_refs[]` | 命中 `SBR-AU-001` 时含 `rule_id` / `title` / `source_tier` |
| `provenance.notes` | `authorisation gaps recorded: <缺口列表>` 或 `authorisation documents recorded: <数量>` 或 `no authorisation inventory present — authorisation status is unknown, not 'missing'` |
| `unevaluated[]` | 无清单时含 `SBR-AU-001` + `missing_fields: ["history"]` |
| `reason` | 命中数 + 动作 + 风险等级 + 降级原因 + 免责句 |
| `signals[].authorization`（非契约字段） | `{"provided": [...], "missing": [...], "known": bool}` —— 复核时最直接 |

> `signals[]` 里的 `authorization` 是**人工复核的入口** ——
> 它一眼能看出「缺什么」或「状态未知」。

## 6. INPI 商标注册核验方法

### 6.1 核验目的

确认**被指用的品牌词是否是一个在巴西有效注册的商标**、权利人是谁、
注册类别覆盖什么、注册是否仍在有效期。

**法律依据**（`research/raw/br_lei_propriedade_industrial_9279.txt`，
`last_verified=2026-10-27`）：

> Art. 133. O registro da marca vigorará pelo prazo de 10 (dez) anos, contados da data da concessão do registro, prorrogável por períodos iguais e sucessivos.

### 6.2 INPI 的入口（抓取件已证实存在）

来源 `research/raw/br_inpi_legislacao_marcas.txt`，
`source_url=https://www.gov.br/inpi/pt-br/servicos/marcas/legislacao`，
`last_verified=2026-10-27`（页面标注 `Atualizado em 21/10/2026 14h18`）。

抓取件的导航区明确列出这些服务入口：

| 入口 | 抓取件中的原文 | 用途 |
|---|---|---|
| 商标检索 | `Busca` | 查是否已注册、权利人是谁 |
| 系统 e-Marcas | `Sistema e-Marcas` | 商标申请与管理的在线系统 |
| 商标文件副本 | `Cópia de Documentos de Marcas` | 取注册证明文件 |
| 商标基础指南 | `Guia Básico` | 流程与分类说明 |

抓取件同时列出了管辖法律：

> Lei nº 9.279, de 14/05/96 — Lei da Propriedade Industrial – Regula direitos e obrigações relativos à propriedade industrial.

> Lei nº 9.610, de 19 de fevereiro de 1998 — Lei de Direitos Autorais – Altera, atualiza e consolida a legislação sobre direitos autorais e dá outras providências.

### 6.3 人工核验步骤

> **本模块不执行任何步骤。** 下面是给人工复核者的操作指引 ——
> 本模块没有 INPI 接口，引擎里也没有任何网络调用
> （`src/` 下只 import `hashlib` / `json` / `os` / `re` / `datetime` / `typing` / `argparse` / `sys`）。

| 步 | 动作 | 记录什么 |
|---|---|---|
| 1 | 打开 INPI 的 `Busca`（商标检索）入口 | 检索时间 |
| 2 | 按品牌词检索，逐个核对结果中的**文字商标** | 命中哪些注册号 |
| 3 | 对每个命中记录：注册号、权利人名称、注册类别（classe）、状态、到期日 | 写入 `trademark_registration` 材料的 `notes` |
| 4 | 比对**权利人**与授权书上的**授权方** | 是否为同一人；否则需要转授权链 |
| 5 | 比对**注册类别**与商品**类目** | 类别不覆盖 → 授权覆盖不了本商品 |
| 6 | 核对注册**是否仍有效**（Art. 133 的 10 年 + 续展） | 过期商标不构成有效权利 |
| 7 | 取注册证明文件（`Cópia de Documentos de Marcas`） | 存**路径**到 `artifact_ref`（H5） |
| 8 | 把结论写进复核意见 | —— |

### 6.4 核验结果的两种含义

| 查册结果 | 含义 | 复核结论 |
|---|---|---|
| **未查到注册** | 该词在巴西**可能不是注册商标** | 商标维度的风险降低，但**不等于**没有其它权利（外观设计/版权/不正当竞争仍可能成立） |
| **查到了注册** | 存在有效注册商标 | 需要授权材料支撑；无授权 → `require_evidence` |

> ⚠️ **查册结论只能作为证据，不能作为判定。**
> 按硬约束 H1，即便查册确认存在注册商标，本模块的结论仍恒为
> `confidence="signal"` + `requires_human_review=true`。
> 侵权只由**权利人投诉、书面授权或平台投诉通知**确立。

## 7. 授权状态与商标检测的关系

| 情形 | 商标检测 | 授权维度 | 聚合结论 |
|---|---|---|---|
| 品牌词 + 有完整授权清单 | 可能命中 `SBR-IP-001` | `SBR-AU-001` 不命中 | `escalate_legal` / `BLOCK` / high —— 命中的是**品牌宣称**信号，授权齐备**不撤销**该信号 |
| 品牌词 + 授权清单有缺口 | 命中 `SBR-IP-001` | 命中 `SBR-AU-001` | `escalate_legal` / `BLOCK` / high |
| 品牌词 + 无授权清单 | 命中 `SBR-IP-001` | `SBR-AU-001` 记 `unevaluated` | `escalate_legal` / `BLOCK` / high，且 `unevaluated[]` 含 `SBR-AU-001` |
| 品牌词 + 指示性使用 | `SBR-IP-001` 被豁免 | 视清单而定 | `allow` / `PASS` / info（若其它维度可评估） |
| 无品牌词 + 授权清单有缺口 | 不命中 | 命中 `SBR-AU-001` | `require_evidence` / `REVIEW` / high |
| 无品牌词 + 无授权清单 | 不命中 | `SBR-AU-001` 记 `unevaluated` | `flag_for_review` / `REVIEW` / low |

> **重要**：授权齐备**不会**撤销 `SBR-IP-001` 的命中。
> 实测夹具 `IP-07`（`brand=Nike` + `authorization_documents=["brand_authorization_letter"]`）：
> `fired=['SBR-IP-001']`、`action=escalate_legal` / `verdict=BLOCK` / `risk_level=high`。
>
> 这是**符合设计**的：关键词命中只是**筛查信号**，最终「是否已授权、是否侵权」
> 由人结合授权材料判断 —— 引擎不做这个判断，也不该做。

## 8. 不得使用的表述

| 禁止 | 正确 |
|---|---|
| 「没有授权清单 = 未授权」 | 「无授权清单 → 授权状态未知」 |
| 「授权缺失 = 侵权」 | 「无法证明有权销售 → `require_evidence`」 |
| 「授权齐全 = 放行」 | 「授权维度已核查；品牌宣称信号仍需人工判定」 |
| 「INPI 查不到 = 合法」 | 「未查到注册商标；其它权利维度未排除」 |
| 把 `signal` 说成 `confirmed` | 恒为 `signal` |

## 9. 交叉引用

| 主题 | 文档 |
|---|---|
| 四类的定义、法律依据、平台码 | `references/ip_categories.md` |
| 指示性使用 vs 品牌宣称的判定表 | `references/nominative_use.md` |
| 品牌方撤诉解封流程 | `references/dissolution_flow.md` |
| 证据引用 Schema | `contracts/evidence_reference.schema.json` |
| 案件证据结构 | `data/schema/case.schema.json` |
| 平台违规码全表 | `research/violation_codes.json` |
