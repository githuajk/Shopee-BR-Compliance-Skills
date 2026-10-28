| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-IP-004` |
| 所属模块 | `shopee-br-ip-review` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | IP 类投诉的处理路径、卖家可采取的动作、需准备的证据，以及本模块的边界 |
| 相关文档 | `research/raw/shopee_br_termos_de_servico.txt`、`research/raw/shopee_br_violacoes_anuncio.txt`、`research/raw/shopee_br_pontos_de_penalidade.txt`、`docs/SBRCA-P0-004_open_questions.json` |
| 未决事项 | 「品牌方已撤诉」是否作为解冻的硬前置条件 —— 待裁定项 `Q-A`，见 §7 |

---

## 1. 本模块的边界（先读这一节）

> **本模块不执行任何线上动作。**
>
> 不发通知、不提交申诉、不联系品牌方、不撤案、不改商品、不下架商品、
> 不冻结也不解冻账号、不调用任何外部接口。

代码层面的事实（`skills/shopee-br-ip-review/src/` 全部 import）：

```
hashlib / json / os / re / datetime / typing / argparse / sys
```

**没有** `requests`、`urllib`、`socket`、`http`、任何 API 调用，
也没有写操作入口。模块产出的是**建议**：

| 产出 | 文件 | 契约 |
|---|---|---|
| 审核结果 | `audit_result.json` / `audit_results.json` | `contracts/audit_result.schema.json` |
| 模块交接 | `module_handoff.json` | `contracts/module_handoff.schema.json` |
| 判定明细（非契约） | `signals.json` | 供人工复核 |
| 错误记录 | `errors.json` | —— |

`ModuleHandoff.assumptions` 里写死了这条边界：

> The module performs no online action — no publication, deletion, freeze or appeal is executed here; only recommendations are emitted.

`contracts/risk_action_matrix.json` 的 H6 同向规定：

> freeze_relist 与 escalate_legal 为 human_only —— 任何自动化都不得执行解冻或 IP 投诉处置。

## 2. IP 投诉的处理路径

### 2.1 平台侧的投诉受理通道

**Termos de Serviço da Shopee Brasil 第 8 条**
来源 `research/raw/shopee_br_termos_de_servico.txt`，
`source_url=https://help.shopee.com.br/portal/4/article/77113-Termos-de-Servi%C3%A7o-da-Shopee`，
`last_verified=2026-10-27`。

> Shopee não permite que sejam inseridos e/ou comercializados em sua Plataforma qualquer produto e/ou Conteúdo que violem os direitos autorias, direitos de marca ou direitos de propriedade intelectual em geral (DPI) de propriedade alheia (“ Proprietário de DPI ”).

> Se você é um Proprietário DPI ou um agente devidamente autorizado por um Proprietário IPR (“ Agente DPI ”) e acredita que seu direito ou de seu representado foi violado, por favor, envie sua reclamação através do Shopee Brand IP Portal, fornecendo-nos os documentos requisitados a seguir para sustentar sua reivindicação.

> Apenas notificações de violação de direito de propriedade intelectual enviadas por meio do canal adequado e com todas as informações e documentos necessários serão processadas e analisadas pela Shopee, sendo que a Shopee se resguarda ao direito de não analisar reclamações e/ou notificações envidas por outros canais

**平台要求的通知内容**（同一条款列举）：

| 项 | 原文 |
|---|---|
| 涉事商品 URL | `(d) URL(s) do(s) anúncio(s) que contém a suposta violação;` |
| 投诉人联系方式 | `(e) informações suficientes para permitir à Shopee contatar o Notificante, como endereço físico, número de telefone e endereço de e-mail;` |
| 善意声明 | `(f) uma declaração do Informante de que a denúncia é apresentada de boa-fé e que o uso da propriedade intelectual, conforme identificado pelo Notificante, não está autorizado pelo Proprietário DPI ou pela lei;` |

> 结论：**投诉必须走 Shopee Brand IP Portal**。走别的渠道（社交媒体、邮件、
> 平台内私信）平台明确说「不处理」。这条决定了卖家应对投诉时**只能**
> 在同一渠道里回应。

### 2.2 处置后果

平台对违规的下架/封禁后果（`research/raw/shopee_br_violacoes_anuncio.txt`，
`source_url=https://seller.br.shopee.cn/edu/article/16318`，`article_id=16318`，
`last_verified=2026-10-27`）：

> Anúncios banidos podem ser restabelecidos assim que a violação for resolvida. Os anúncios excluídos pela Shopee não podem ser recuperados e incorrerão pontos no sistema de Pontos de Penalidade do Vendedor da Shopee.

> Vendedores com violações de anúncios severas terão os anúncios removidos e podem ter suas contas permanentemente congeladas.

平台对 IP 类违规的定性（同一抓取件）：

> Violação de IP e falsificação: por exemplo, venda de produtos que contenham marcas registradas sem autorização do proprietário da marca;

### 2.3 卖家收到通知

来源 `research/raw/shopee_br_politica_produtos_proibidos.txt`，
`source_url=https://seller.shopee.com.br/edu/article/3304/politica-de-produtos-proibidos-e-restritos`，
`article_id=3304`，`last_verified=2026-10-27`。

> Quando ocorrer uma violação da política, nós enviaremos um e-mail, uma mensagem do sistema e uma notificação por push ao vendedor, informando-o que o anúncio foi removido de nosso site.

来源 `research/raw/shopee_br_violacoes_anuncio.txt`，`article_id=16318`：

> Você receberá uma notificação via Central do Vendedor se tiver algum anúncio banido ou excluído.

### 2.4 完整路径（人 + 平台）

```
品牌方 / 授权代理人 通过 Shopee Brand IP Portal 提交投诉
   ↓  平台审核 → 商品下架（[133] / [601] / [602] / [603] / [604]）→ 严重的账号冻结
   ↓
卖家收到通知（邮件 + 系统消息 + push + Central do Vendedor）
   ↓
卖家在 Central do Vendedor 查违规原因与申诉期限
   ↓
内部核实：是不是真的侵权？（本模块在这一步提供筛查信号）
   ↓
若不侵权 → 走申诉（Contestar），举证反证
若确侵权   → 联系品牌方，协商撤诉或取得授权
   ↓
品牌方撤诉 / 出具授权 → 提交平台 → 平台恢复
   ↓
记录**平台侧实际状态**（不是内部审批状态）
```

## 3. 卖家可采取的动作

| 动作 | 平台原文依据 | 谁执行 | 备注 |
|---|---|---|---|
| 查违规原因与期限 | `Verifique o motivo pelo qual seu anúncio foi banido/excluído por meio da página de violações de anúncio. Em seguida, edite o mesmo de acordo antes do prazo especificado para a revisão da Shopee.` | 卖家（人工） | **期限过后自动删除** —— 删除不可恢复 |
| 提交申诉（apelación） | `Você pode recorrer apenas uma vez para cada infração atestada na sua Central do Vendedor.` | 卖家（人工） | **每条已认定违规只能申诉一次** |
| 补交材料支持申诉 | `Inclua o ID do pedido, os motivos da apelação e documentos e evidências relevantes que apoiam o seu caso estão anexados à sua apelação.` | 卖家（人工） | 必须附**订单 ID + 申诉理由 + 证据** |
| 要求恢复被下架商品 | `No entanto, os anúncios que foram removidos podem ser restabelecidos mediante solicitação.` | 卖家（人工） | 这条在处罚点语境里 —— 申诉被驳回后**处罚点不可撤销**，但被下架商品可申请恢复 |
| 联系品牌方协商撤诉 / 取得授权 | —— | 卖家（人工） | 见 §4 |
| 让平台恢复 | `A Shopee responderá à sua notificação assim que possível.` | 平台 | 平台侧时点不由卖家控制 |

> **本模块对以上动作一律不执行。** 它只提供 §5 的筛查信号与证据要求清单。

### 3.1 申诉不等于撤诉 —— 两者都要做

| | 申诉（Contestar / apelación） | 撤诉（品牌方撤诉） |
|---|---|---|
| 发起方 | **卖家** | **品牌方** |
| 解决的是 | 「这条违规认定是否成立」 | 「我不再主张这项权利」 |
| 适用 | 认为自己没侵权 | 确实用了对方的东西，但愿意和解 / 补授权 |
| 结果 | 成立 → 违规撤销，商品恢复 | 平台按投诉方的意思处理 |

**两者是并列路径，不是二选一。** 内部审批通过、整改完成、申诉成立 ——
**都不等于账号解封**（见 §4.3）。

## 4. 需要准备的证据

### 4.1 证据清单

| 证据 | 说明 | 证据类型键 |
|---|---|---|
| 撤诉证明 | 品牌方的书面撤诉 / 同意函 | `appeal_record` |
| 品牌授权书 | 若走授权途径 | `brand_authorization_letter` |
| 商标注册证明 | INPI 查册取得（见 `references/authorization_checklist.md` §6） | `trademark_registration` |
| 供应商发票 / 采购凭证 | 证明合法来源 | `supplier_invoice` |
| 商品实拍图 | 证明商品本体与宣称一致 | `product_photographs` |
| 版权授权书 | 作品类 | `licence_document` |
| 外观设计登记 | `SBR-IP-008` | `design_registration` |
| 申诉记录 | 平台申诉回执 | `appeal_record` |
| 平台恢复证明 | 平台侧实际恢复的记录 | `remediation_evidence` |
| 平台通知 | 原始通知载荷 | `platform_notice` |

材料类型键来自 `contracts/evidence_reference.schema.json` 的 `evidence_type.examples`；
`data/schema/case.schema.json` 的 `case_type` 枚举里有 `ip_complaint` 与
`authorization_review` 两个专门值。

> **硬约束 H5**：证据只存**路径**（`artifact_ref`）与元信息，
> **禁止**内嵌授权书正文、投诉原件或凭证内容。

### 4.2 两种授权路径

| 路径 | 适用 | 需要什么 |
|---|---|---|
| **撤诉** | 卖家确实是仿牌 / 无授权使用 | 品牌方书面撤诉函 → 提交平台 |
| **补授权** | 卖家有（或能拿到）品牌方授权 | 品牌方授权书（覆盖品牌、类目、期限、地区、主体）→ 提交平台 |

授权书形式的法律要求（`research/raw/br_lei_direitos_autorais_9610.txt`，
`last_verified=2026-10-27`）：

> II - somente se admitirá transmissão total e definitiva dos direitos mediante estipulação contratual escrita;

### 4.3 两个状态必须分开记录

案件必须区分：

| 字段 | 含义 |
|---|---|
| **内部审批状态** | 内部是否认定侵权、是否已处置、是否已批准 |
| **平台侧实际状态** | 账号/商品**在平台侧**是否真的恢复 |

> ⚠️ **审批通过 ≠ 解封成功。**
> 原型的解冻逻辑只要求「案件关闭 + 人工审批」，
> 这不足以证明解封 —— 必须以**平台侧实际状态**为准。

`data/schema/case.schema.json` 提供了对应字段：
`status`（`open` / `under_review` / `awaiting_evidence` / `blocked` /
`relist_frozen` / `approved` / `rejected` / `closed` / `escalated`）、
`frozen` / `freeze_reason` / `freeze_until`、
`approvals[]`（含 `unfreeze` 与 `appeal` 两个动作）、
以及 `platform_notice`（平台通知原文载荷）。

> **注意**：这些字段是**案件侧**的。本模块产出的 `AuditResult`
> 没有 `frozen` / `unfreeze` 字段 —— **解冻不是一个 IP 筛查结论能决定的事**。

### 4.4 品牌方撤诉的效力边界

平台对投诉通道的立场（`research/raw/shopee_br_termos_de_servico.txt`）：

> Apenas notificações de violação de direito de propriedade intelectual enviadas por meio do canal adequado e com todas as informações e documentos necessários serão processadas e analisadas pela Shopee, sendo que a Shopee se resguarda ao direito de não analisar reclamações e/ou notificações envidas por outros canais

这条同时约束两侧：**品牌方的撤诉/同意函也应当走同一通道**。
通过邮件或第三方转达，平台有权不处理。

## 5. 本模块在解封流程中的位置

### 5.1 能提供的

| 产出 | 在解封流程中的用途 |
|---|---|
| `rule_refs[]` | 指出命中了哪条规则 —— 复核者据此判断是不是真侵权 |
| `confidence="signal"` | 明确「这是筛查信号，不是侵权认定」 |
| `requires_human_review=true` | 强制人工介入，不允许自动放行 |
| `unevaluated[]` | 告诉复核者**哪些维度根本没查**（如无图片、无授权清单） |
| `evidence_required` | 告诉复核者**要准备哪些材料**（各规则的 `evidence_required`） |
| `provenance.notes` | 授权状态是「未知」还是「有缺口」 |

### 5.2 不能提供的

| 缺口 | 为什么本模块给不了 |
|---|---|
| 撤诉证明 | 需要品牌方与平台之间的动作 |
| 平台侧恢复状态 | 本模块不连平台 |
| 侵权认定 | 硬约束 H1 —— 仅权利人投诉、书面授权或平台投诉通知可确立侵权 |
| 账号解冻 | 硬约束 H6 —— `freeze_relist` / `escalate_legal` 是 `human_only` |
| 申诉提交 | 本模块不执行任何线上动作 |
| 专利维度的排查 | 当前无 `ip_patent` 规则（见 `references/ip_categories.md` §6） |

### 5.3 交接里的假设与缺口

`ModuleHandoff.assumptions` 固定包含这四条：

1. IP 结论只是筛查信号，侵权只能由权利人投诉、书面授权或平台投诉通知确立（H1）；
2. 每条结果 `confidence="signal"` 且 `requires_human_review=true`；
3. 本模块**不执行任何线上动作** —— 不发布、不删除、不冻结、不申诉，只产出建议；
4. 授权维度读自商品的 `history` 字段；无授权清单 = 状态**未知**，不是「缺失」。

`ModuleHandoff.known_gaps` 会在有未评估规则时记录（数字是插值的，其余为固定文本）：

> could not be completed because the required input was missing; those dimensions are unassessed, not cleared.

无商品时记录：

> No products were supplied, so no IP dimension was evaluated.

## 6. 内部流程与平台流程的对照

| 内部动作 | 平台侧动作 | 顺序 |
|---|---|---|
| 核实是否侵权 | —— | 先 |
| 决定是否整改 / 补授权 | —— | —— |
| 联系品牌方 | —— | —— |
| —— | 品牌方撤诉 / 出具同意函 | —— |
| —— | 提交平台 | —— |
| —— | 平台恢复商品 / 账号 | 末 |
| 记录平台侧实际状态 | —— | 最后 |

> **「提交平台」这一步是内部流程无法替代的。**
> 撤诉证明拿到手不等于平台已经恢复 —— 必须以平台侧实际状态为准。

## 7. 待裁定项 `Q-A`

`docs/SBRCA-P0-004_open_questions.json` 登记的开放问题 `Q-A`：

> **IP 投诉「品牌方撤诉才能解封」是否作为硬性解冻前置条件**

| 选项 | 内容 |
|---|---|
| A | 硬前置：IP 类案件的解除必须附带「品牌方已撤诉」的证据类型 |
| B | 软提示：审批时要求填写品牌方沟通状态，不强制阻断 |
| C | 不纳入（人工审批时自行判断） |

该文件登记的 `default_if_no_answer` 是 **B（软提示）**，
并把 `Q-A` 列进 `blocking_phase_5`。

> **本模块在裁定前只「提示」该事实，不阻断。**
> 本模块不实现解冻判定，也不产出 `unfreeze` 动作 ——
> 因此无论裁定结果如何，本模块的行为都不需要改动。

## 8. 不得使用的表述

| 禁止 | 正确 |
|---|---|
| 「内部审批通过 = 已解封」 | 「以平台侧实际状态为准」 |
| 「申诉通过 = 品牌方已撤诉」 | 「申诉针对的是违规认定；撤诉须由品牌方发起」 |
| 「本模块已提交申诉 / 已联系品牌方」 | 「本模块不执行任何线上动作」 |
| 「命中品牌词 = 侵权成立」 | 「筛查信号，需权利人投诉 / 授权 / 平台通知才成立」 |

## 9. 交叉引用

| 主题 | 文档 |
|---|---|
| 四类的定义、法律依据、平台码 | `references/ip_categories.md` |
| 指示性使用 vs 品牌宣称的判定表 | `references/nominative_use.md` |
| 授权材料清单与 INPI 核验 | `references/authorization_checklist.md` |
| 平台违规码全表 | `research/violation_codes.json` |
| 案件状态机与证据结构 | `data/schema/case.schema.json` |
| 风险动作与硬约束 | `contracts/risk_action_matrix.json` |
