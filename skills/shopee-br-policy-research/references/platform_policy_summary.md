| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-PR-004` |
| 所属模块 | `shopee-br-policy-research` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 政策要点摘要（禁限售类目、处罚机制、IP 四类） |
| 相关文档 | `research/raw/`、`research/violation_codes.json`、`docs/SOP_COMPLIANCE_REVIEW.md` |
| 未决事项 | 2 条 Anvisa 来源待重抓 |

> 本文件是**摘要**，不是权威。权威是 `research/raw/` 下的抓取件原文。
> 每条摘要都注明出处；引用到规则时**必须**回到抓取件逐字摘录。

---

## 1. 禁售与受限商品

**来源**：`shopee_br_politica_produtos_proibidos`（平台，36KB）、
`shopee_br_produtos_restritos_liberacao`（平台，15KB）、
`shopee_br_categorias_restrritas`（平台，5KB）

| 类别 | 平台立场 | 对应规则前缀 |
|---|---|---|
| **禁售**（proibidos） | 不得刊登；违反即下架，情节严重封店 | `PI` |
| **受限**（restritos） | 需资质/授权才能刊登；缺材料不得上架 | `RI` |
| **监管机构禁止** | Anatel / Anvisa 等机构禁止的商品 | `PI` / `RI` |
| **政策变更** | 商品因监管政策变化变成禁售 | `PI` |

> **受限 ≠ 禁售**。受限商品可以卖，但必须补齐指定材料
> （注册证、授权书、许可证）。缺材料时动作是 `require_evidence`，不是 `block`。

## 2. 2026-08-06 —— Anvisa 非处方药新规（**时效性关键**）

**来源**：`shopee_br_categorias_restrritas`（article 7379）

> *Desde 6 de agosto de 2026, a Shopee está autorizada pela Anvisa a
> comercializare medicamentos isentos de prescrição (MIPs), apenas por
> farmácias e drogarias regularmente licenciadas que sigam rigorosamente
> todas as regulamentações da categoria e da agência, conforme a
> Resolução-RE nº 3.056/2026.*

要点：

| 项 | 内容 |
|---|---|
| 生效日 | **2026-08-06**（抓取件页面更新日期：2026-08-10） |
| 授权范围 | Shopee 获 Anvisa 授权销售**非处方药（MIP）** |
| 限定主体 | **仅**由持牌药店/药房（farmácias e drogarias regularmente licenciadas）销售 |
| 前提 | 严格遵守类目与机构的全部规定 |
| 依据 | Resolução-RE nº 3.056/2026 |

**对审核的影响**：

- MIP（isento de prescrição）**不再一律禁售** —— 但**必须**是持牌主体在售
- 规则 `SBR-MED-002`（MIP 需证据）对应这一变化：动作是 `require_evidence`
  （补齐资质），**不是** `block`
- 标题/描述含「medicamento isento de prescrição」但主体无资质 → 应要求补证

> ⚠️ **抓取件里 2 条 Anvisa 来源（`br_anvisa_*`）抓取失败（HTTP 503）**，
> 相关的 `Resolução-RE` 原文无法逐字核验。规则 `SBR-MED-002` 因此改用
> **Shopee 官方文章**作为引文来源（该文章逐字引用了这项授权），
> 而不是引 Anvisa 原文 —— 引文必须能核验。

## 3. 处罚点制度（Pontos de Penalidade）

**来源**：`shopee_br_pontos_de_penalidade`（article 16316，9KB）

| 机制 | 平台原文要点 |
|---|---|
| 归属 | 每周一（segundas-feiras）统一分配 |
| 生效 | 进入处罚档位后**一周**才开始生效 —— 留出申诉窗口 |
| 持续 | 限制持续 **14 到 28 天** |
| 扣款 | 处罚开始两周后从钱包余额扣除；申诉通过则不扣 |
| 豁免 | 前一个月商品 GMV 低于 R$ 2.500 的店铺不扣款 |
| 后果 | 账号受限 + 可能扣费；账号因违规被冻结时**付款会被暂扣** |
| 查看 | 卖家中心 → Desempenho da Conta |
| 预防 | 按时发货、避免刊登违规、及时回复 chat |

> **平台未公开「扣几分」**。只公开「是否产生处罚点」与严重度。
> 因此本项目**不得**引用具体分值（硬约束 N10）。

**对审核的影响**：

- 规则 `SBR-AC-001`（账户有处罚点）→ 动作 `require_evidence`（需人工复核后决定）
- 规则 `SBR-AC-002`（申诉时限未过）→ **不得重新刊登**该商品
  （申诉证据依赖被处理时的刊登状态）
- 处罚点**档位决定权益暂停时长**，不是每次违规都直接封店

> **「处罚点」与「封禁」是两件事**。封禁（banimento）是账号级处置，
> 由多次违规累积导致；处罚点是逐次计分。

## 4. 封禁 vs 下架

**来源**：`shopee_br_banimento_suspensao_anuncios`（article 5139，22KB）、
`shopee_br_violacoes_anuncio`（article 16318，5KB）

| 处置 | 范围 | 可否恢复 | 触发 |
|---|---|---|---|
| **下架**（remoção do anúncio） | 单个商品 | 改掉问题后可重新刊登 | 单次违规 |
| **限触达**（alcance limitado） | 单个商品的曝光 | 整改后**自动恢复** | 轻���违规 |
| **封禁**（banimento） | 整个账号 | 问题解决后可恢复 | 违规累积 |
| **冻结重发**（relist freeze） | 特定商品的重发 | 需关联案件了结 | 删除的违规商品被重发 |

**关键区分**：**封禁 vs 下架** 决定了「重发该商品是否违规」——
删除的商品被重发仍是重发违规（规则 `SBR-RL-002` → `freeze_relist`）。

## 5. IP 四类

**法律来源**：`br_lei_propriedade_industrial_9279`（工业财产法，113KB）、
`br_lei_direitos_autorais_9610`（著作权法，76KB）、
`br_inpi_legislacao_marcas`（INPI 商标立法，40KB）

| 类别 | 法律依据 | 平台违规码 | 规则前缀 |
|---|---|---|---|
| **商标**（marca registrada） | Lei 9.279/1996 | `[133]` | `IP` |
| **版权**（direito autoral） | Lei 9.610/1998 | `[602]` | `IP` |
| **外观设计**（desenho industrial） | Lei 9.279/1996 | `[603]` | `IP` |
| **专利**（patente） | Lei 9.279/1996 | — | `IP` |

### 5.1 指示性使用（Art. 132 II）

Lei 9.279/1996 art. 132, II 明确：权利人**不得**阻止配件制造商使用商标
**指明产品用途**（目的地），只要遵守竞争惯例。

**实操含义**：「Compatível com Ford Focus 2015-2020」是**指示性使用**，
不是侵权。平台针对的是**把商标当商品品牌宣称**（as a brand claim）。

规则 `SBR-IP-006` 是这条豁免（`severity: info` / `decision: allow`），
命中时**覆盖** `SBR-IP-001` 的品牌词命中。

> ⚠️ 但 IP 类结论**恒为 `confidence: signal` + 强制人工复核**（硬约束 H1）——
> 关键词或 logo 命中只是**筛查信号**。仅权利人投诉、书面授权或平台投诉通知
> 可确立侵权。

## 6. 消费者保护与广告

**来源**：`br_consumidor_cdc_publicidade`（CDC + 广告法，86KB）

| 原则 | 对应规则 |
|---|---|
| 不得做无法证实的功效承诺 | `SBR-LV-001`（夸大宣称） |
| 不得误导性折扣表述 | `SBR-LV-002` |
| 不得站外引流 | `SBR-LV-005` |

## 7. 类目

**来源**：`shopee_br_categoria_correta`（article 2820，5KB）

类目错误 → `[613] Categoria incorreta`（`Baixa`，不产生处罚点），
规则 `SBR-LV-008`（`decision: flag_for_review`）。

## 8. 账号与主体

**来源**：`shopee_br_mudanca_conta_cpf_cnpj`（article 9216，14KB）

个人（CPF）店铺迁移为公司（CNPJ）的流程。与 `SBR-AC-001`（账号处罚点）
相关 —— 主体变更会影响账号层面的违规记录归属。

## 9. 政策时效性

| 政策 | 生效/更新 | 影响 |
|---|---|---|
| Anvisa MIP 授权 | **2026-08-06** | `SBR-MED-002` 的判定基础 |
| 处罚点改为每周一分配 | 平台文章「Desde 01 de julho」 | `SBR-AC-001` 的申诉窗口计算 |
| 处罚限制延后一周生效 | 现行 | 申诉窗口 |

> **每次引用前确认 `last_verified`。** 平台政策会变，
> 2026-09-15 之前的政策不能当现状。
> 本项目的规则全部标注了 `last_verified`（当前均为 2026-10-27）。

## 10. 核验

```bash
env -u LD_LIBRARY_PATH python3 tools/verify_citations.py   # 50/50
env -u LD_LIBRARY_PATH python3 tools/check_sources.py      # 17 条来源一致
```

**摘要与原文不一致时，以原文为准** —— 摘要错了就改摘要，
不要改引文去迁就摘要。
