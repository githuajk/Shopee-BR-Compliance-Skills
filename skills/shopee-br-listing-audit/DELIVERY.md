# TASK-LISTING-01 交付说明

> 任务：`TASK-LISTING-01` —— 商品内容合规审核模块
> 模块：`shopee-br-listing-audit`
> 契约版本：1.0.0
> 交付日期：2026-10-27
> 工作区：`/config/dianshang/Shopee-BR-Compliance-Skills`（未建独立分支，按主 Agent 统一提交）
> 本次交付范围：**4 份 `references/` 文档填实 + 本交付说明**（实现代码与测试已在同一任务内完成并提交）

---

## 1. 文件清单

### 1.1 本次交付（文档）

| 路径 | 动作 | 说明 |
|---|---|---|
| `skills/shopee-br-listing-audit/references/audit_semantics.md` | 修改 | 填实：判定分三层（规则 / 矩阵 / 词库）、四类规则（PI / RI / MED / LV）逐条的判定含义与边界、正例反例全表、`_resolve_action` 三级降级链、`_confidence` 三档的实测触发条件、`requires_human_review` 的 9 条判定、缺失输入的三种表现、H1–H6 的落点表。状态由 Draft 改为 **Active**，版本 1.0.0 |
| `skills/shopee-br-listing-audit/references/false_positive_control.md` | 修改 | 填实：规则层与词库层的**文本聚合范围不同**（实测对照）、葡语显式边界的真实语义（与 `\b` 的差异表）、规则层的 NFD 漏检面、8 类已知误报来源、豁免机制（7 条逐条说明 + `action`/`confidence` 对应 + 组级作用域的实测）、词库→规则映射边界、8 种「命中只是信号」的情形、反例强制项与实测覆盖率、上下文判定操作准则。状态改为 **Active**，版本 1.0.0 |
| `skills/shopee-br-listing-audit/references/policy_currency.md` | 修改 | 填实：`status` 的 4 态状态机、`last_verified` 的确切含义（是什么 / 不是什么 / 代码里做什么用）、7 种必须重新核验的触发条件与标准流程、**2026-08-06 Anvisa MIP 变更**对判定的影响（三条 MED 规则的分工与实测边界表）、平台未公开数值的清单与禁止引用规则、生效性日期现状（不自动降级）、人工核验清单、政策变更→判定变化的映射表。状态改为 **Active**，版本 1.0.0 |
| `skills/shopee-br-listing-audit/references/evidence_checklist.md` | 修改 | 填实：H5 的落地形态（`artifact_ref` 只有两种取值）、`evidence_required` 的两个用途与对动作的影响、15 种证据类型键的逐规则清单、受限类目按监管机构的材料对照表（附平台逐字原文）、**缺材料是 `require_evidence` 不是 `block`** 的理由、证据链的四个层次与字段来源、实测的完整 `evidence_refs[]` 产出、`unevaluated[]` 与待补证据的分工、禁售类目为什么也列证据、不允许做的事。状态改为 **Active**，版本 1.0.0 |
| `skills/shopee-br-listing-audit/DELIVERY.md` | 新增 | 本文件 |

**文档规模**：4 份 references 从 71/62/66/191 行的骨架变为
538 / 500 / 448 / 394 行，合计 **1,880 行**（原骨架合计 390 行）。

### 1.2 同任务内已完成的实现（此前已提交，本次未改动）

| 路径 | 状态 |
|---|---|
| `skills/shopee-br-listing-audit/src/sbr_listing_audit/rules.py` | 195 行 —— 规则装载、归一化、`TIER_MAX_ACTION`、`blocking_allowed`、`is_ip_rule` |
| `skills/shopee-br-listing-audit/src/sbr_listing_audit/engine.py` | 783 行 —— 判定引擎、`_resolve_action`、`_confidence`、`_human_review` |
| `skills/shopee-br-listing-audit/src/sbr_listing_audit/conditions.py` | 304 行 —— 条件求值算子（三态） |
| `skills/shopee-br-listing-audit/src/sbr_listing_audit/fields.py` | 110 行 —— 字段提取与「存在但为空」判定 |
| `skills/shopee-br-listing-audit/src/sbr_listing_audit/lexicon.py` | 115 行 —— 词库匹配（复用 `tools/scan_lexicon.py`） |
| `skills/shopee-br-listing-audit/src/sbr_listing_audit/matrix.py` | 132 行 —— 契约矩阵只读视图 |
| `skills/shopee-br-listing-audit/src/sbr_listing_audit/pipeline.py` | 313 行 —— 批次编排与交接记录 |
| `skills/shopee-br-listing-audit/src/sbr_listing_audit/__init__.py` | 60 行 —— 公开 API |
| `skills/shopee-br-listing-audit/src/sbr_listing_audit_cli.py` | 102 行 —— 命令行入口 |
| `tests/shopee-br-listing-audit/run_tests.py` | 1,157 行 —— 383 项断言 |
| `tests/shopee-br-listing-audit/fixtures/listing_audit_rule_cases.json` | 71 个用例（33 正例 / 33 反例 / 3 缺失 / 2 边界），覆盖全部 34 条 owned 规则 |

---

## 2. 测试结果

### 2.1 模块自有测试

```bash
$ cd /config/dianshang/Shopee-BR-Compliance-Skills && env -u LD_LIBRARY_PATH python3 tests/shopee-br-listing-audit/run_tests.py
```

实际输出（完整）：

```
shopee-br-listing-audit 1.0.0 —— 模块测试
仓库根: /config/dianshang/Shopee-BR-Compliance-Skills

=== L1 字段取值与空值判定 ===

=== L1 触发条件求值 ===

=== L1 风险动作矩阵查表 ===

=== L1 规则加载与来源层级 ===

=== L1 词库筛查（信号层） ===

=== L2 契约校验 ===

=== L2 结果与矩阵一致 ===

=== L3 自有规则用例（每条规则正例 + 反例） ===

=== L3 共享夹具一致性（只读） ===

=== L3 共享夹具未被修改 ===

=== L4 / H1 —— IP 类结论恒为 signal + 强制人工复核 ===

=== L4 / H2 —— 阻断类动作只来自 platform_official / law 的 active 规则 ===

=== L4 / H3 —— 输入缺失不等于合规 ===

=== L4 / H4 —— 引文逐字核验 ===

=== L4 / H5 —— 证据只存引用，不内嵌凭证内容 ===

=== L4 / H6 —— freeze_relist / escalate_legal 为 human_only ===

=== 失败路径 —— 不静默丢弃、不中断整批 ===

=== CLI 端到端 ===

=== 注入安全 —— 输入文档中的指令只是数据 ===

==============================================================
PASSED: 383   FAILED: 0
耗时: 8.39s
模块测试全部通过。
```

**退出码 0。** 383 项断言全部通过。

### 2.2 全项目校验

```bash
$ cd /config/dianshang/Shopee-BR-Compliance-Skills && env -u LD_LIBRARY_PATH bash scripts/check_all.sh
```

实际输出（完整）：

```
== 0/10  框架自检（并行开发框架不变量）==
==============================================================
PASSED: 229   FAILED: 0
框架自检全部通过。

== 1/10  公共契约校验（contracts/）==

==========================================================
契约校验 — 通过 19，失败 0
公共契约全部通过。

== 2/10  合并词库校验（lexicon/ + 映射表）==

=== 5. 词库→规则映射 ===

==============================================================
PASSED: 305   FAILED: 0
词库校验通过：37 组 / 856 词 / 37 条映射 / 50 条规则

== 3/10  词库扫描器自测（回归用例）==
  ok   位置记录: offset=6 excerpt='Tênis Nike Air Max'

自测: 12/12 通过

== 4/10  规则库 + 词库 Schema 校验 ==
ok   rules/05_medicines_health.json

0 errors, 0 warnings
ok   lexicon/term_groups.json

0 errors, 0 warnings

== 5/10  引文逐字核验（无编造引文）==
ok    SBR-MED-003    verbatim in 'shopee_br_categorias_restrritas'

50/50 excerpts verified verbatim, 0 failed

== 6/10  来源清单与抓取件一致 ==
  抓取失败（已登记，不得用于支撑规则）：2 条
    - br_anvisa_publicidade_medicamentos
    - br_anvisa_medicamentos_prescricao
来源清单与抓取件一致。

== 7/10  规则触发正则可编译性 ==
检查 50 条规则、36 条正则
全部规则的正则可编译，且无逻辑自指缺陷。

== 8/10  共享夹具校验（Schema）==
validated 90 products, 10 cases across 8 scenarios + shared fixtures
all fixtures valid

== 9/10  夹具与规则库一致性（正例真命中 / 反例真不命中）==
校验 108 条夹具-规则断言：58 应命中、50 应不命中
全部夹具与规则库一致。

== 10/10  任务包与所有权一致性 ==

==============================================================
PASSED: 352   FAILED: 0
任务包与所有权一致性全部通过。

ALL CHECKS PASSED
```

**退出码 0。**

### 2.3 文档引文的额外核验

本次交付的 4 份 references 里引用了 **34 段平台/法律原文**。
除 `tools/verify_citations.py` 覆盖的 50 条规则引文外，我用同一套宽松匹配算法
（`tools/verify_citations.py` 的 `loose()`）对文档里的引文逐条做了独立核验：

```
34/34 quotes verified, 0 failed
```

覆盖的抓取件：`shopee_br_banimento_suspensao_anuncios`（21 段）、
`shopee_br_categorias_restrritas`（5 段）、`shopee_br_politica_produtos_proibidos`（1 段）、
`shopee_br_produtos_restritos_liberacao`（2 段）、
`shopee_br_pontos_de_penalidade`（3 段）、
`shopee_br_categoria_correta`（1 段）、`br_consumidor_cdc_publicidade`（1 段）。

> 引文核验脚本是一次性的（写在 `/tmp` 下），**未入库** ——
> 本模块不拥有 `tools/**`，且该功能已由 `tools/verify_citations.py` 覆盖。

### 2.4 悬空路径引用检查

`tools/framework_check.py` 的第 10 项「内部路径引用有效」通过（229 项全过）。
另外我对 4 份 references 单独跑了一遍路径解析（同一套正则，
仓库根 / 文档目录 / 模块目录三个候选）：

```
checked 60 distinct (file, ref) pairs
dangling: 0
```

### 2.5 未执行的测试

| 测试 | 原因 |
|---|---|
| 与 `shopee-br-ip-review` / `shopee-br-duplicate-detection` 的真实产出联调 | 这两个模块是**并行**开发的（`TASK-IP-01` 刚提交）。本模块的 `load_rules()` 按前缀过滤，IP / DUP 规则不会被加载 —— 逻辑上确定不冲突，但**未实测** |
| 与主 Skill `shopee-br-compliance` 的端到端联调 | 属 `TASK-MAIN-01` 的范围 |
| 性能基准（万级商品耗时） | 章程要求先有基线再定阈值，本任务未做基准 —— 不臆造性能数字 |
| 规则库按日期自动降级 | **未实现**（见 §3 未解决问题 #1）。这是有意的设计决定，不是遗漏 |
| 图片 OCR 质量的自动判定 | `SBR-LV-007` 只判「图片张数为 0」；质量判定依赖 `image_review` 人工环节，模块不实现视觉分析 |

---

## 3. 未解决问题

| # | 问题 | 影响 | 建议 |
|---|---|---|---|
| 1 | **规则库不实现基于 `last_verified` 的自动降级** | 一条 `last_verified` 是 3 个月前的 `active` 规则，**仍会照常判定**，包括照常产出 `block`。时效判断目前完全靠人工流程 | 现状的防线是 `tools/verify_citations.py` 在 CI 里拦截 —— 页面一改，引文就核验不过，规则必须更新才能重新 `active`。若集成 Agent 认为需要自动降级，建议在 `rules.py` 加 `is_stale(rule, today)` 并在 `_evaluate_rule()` 里把过期规则按 `stale` 处理 —— **但这会改变判定行为，属契约层变更**，需集成阶段统一决定。**本模块不自行实现**（已写入 `references/policy_currency.md` §6） |
| 2 | **规则层的 NFD 分解文本会漏检** | 规则层正则直接跑在原文上，不做重音折叠。若上游给的是 NFD 形式（`u` + 组合符），`SBR-PI-001` 这类规则会漏。实测：NFC `munição de treino` 命中，NFD 不命中 | 在 `shopee-br-data-ingestion` 的文本清洗层统一做 **NFC** 规范化，而不是在规则层加归一化 —— 规则层加归一化会让 `matched_excerpt` 的偏移与原文对不上。**词库层不受影响**（走 `norm()`），所以词库命中仍会作为漏检提示出现在 `evidence_refs[]` |
| 3 | **规则层与词库层的文本聚合范围不同** | 规则层 `any_text` = `title` + `description` + `brand` + `category` + `model` + 图片 `ocr_text`；词库层 = `title` + `description` + `brand` + `category` + `attributes` 的字符串值。`model` / `ocr_text` 只有规则层看，`attributes` 只有词库层看 | 两条层各有盲区，靠 `evidence_refs[]` 里两类条目一起呈现。若要补齐，需同时改 `fields.py` 的 `any_text()` 与 `tools/scan_lexicon.py` 的 `scan_product()` —— 后者属本模块白名单，但改动会影响 ip-review 的共享使用，**建议由集成 Agent 统一决策** |
| 4 | **`SBR-LV-014`（变体使用不当）仍是 `draft`** | 变体使用不当这一维度**完全没有被检测**。规则自己的 `notes` 写明：触发条件无法区分「不当使用变体」与「正常变体」，需要变体 / 属性一致性检查 | 需要「变体 vs 属性一致性」的判定逻辑才能落地。在实现之前它保持 `draft` 是**有意的** —— 保证它永远不会阻断。交接记录的 `known_gaps[]` 会显式列出 `1 rule(s) are not 'active' and produced no conclusion: SBR-LV-014.` |
| 5 | **LV 类的 3 条规则判的是「可判定的结构事实」，不是平台规则的完整语义** | `SBR-LV-006` 判描述字符数 < 120（不是「内容质量差」）；`SBR-LV-007` 判图片张数为 0（不是「图片质量差」）；`SBR-LV-013` 判是否声明了完整三维尺寸（不判是否超限 —— 上限未公开） | 这是**平台未公开可判定边界**下的正确取舍。已在 `references/audit_semantics.md` §5.2 逐条写明。补齐需要平台公开阈值或人工复核环节 |
| 6 | **禁售类目的 `evidence_required` 无法自动核验** | `SBR-PI-001` 要求 `product_photographs` + `supplier_invoice`，但模块**不解析材料内容**，只能列出待补清单 | 这是 H5 的直接后果，也是有意的设计：材料本体留在原处，模块只记路径。人工核对是设计的一部分，不是缺陷 |
| 7 | **`evidence_type` 的 `price_history` / `promotion_terms` 不在契约的 `examples` 里** | 契约的 `examples` **不是** `enum`（只有 `minLength: 2`），所以完全合法，产出也通过了契约校验。但下游若按 `examples` 做白名单校验会漏掉这两项 | 已在 `references/evidence_checklist.md` §2.4 写明，并在 §5 提交了**非阻塞**契约变更建议 |
| 8 | **平台未公开的数值无法进入判定** | 处罚点分值、处罚分档表、尺寸 / 重量上限全部未公开。`research/raw/shopee_br_pontos_de_penalidade.txt` 里只有「Consulte a tabela a seguir:」—— 表本身是页面上的图片，不在文本抓取件里 | 已在 `references/policy_currency.md` §5 逐项列出并明确禁止引用。`SBR-LV-013` 的 `notes` 就是这条原则在规则层的落地 |
| 9 | **两条 Anvisa 来源抓取失败** | `br_anvisa_publicidade_medicamentos`（RDC 96/2008）与 `br_anvisa_medicamentos_prescricao`（RDC 44/2009）均 HTTP 503。**项目未用它们支撑任何规则** —— 药品类规则全部改用平台自己的说明文章 | 若要引用，必须先重抓成功并让 `tools/verify_citations.py` 通过。`tools/check_sources.py` 会持续报出这两条 |
| 10 | **词库层不扫描 `model` 与图片 `ocr_text`** | 见 #3。`ocr_text` 里的违禁词（例如包装上的警告语）只有规则层能看到 | 同 #3 |

---

## 4. 依赖说明

- **我依赖的**：
  - `TASK-POLICY-01` —— `research/sources.json`（17 条来源）、`research/raw/`（抓取件）、
    `research/violation_codes.json`（106 条违规码）。**全部引文的唯一依据**。
  - `TASK-INGEST-01` —— `lexicon/term_groups.json`（37 组 / 856 词）、
    `lexicon/exemptions.json`（7 条豁免）、`contracts/lexicon_rule_map.json`（37 条映射）。
  - `contracts/risk_action_matrix.json` —— **动作语义的唯一权威**：
    `matrix`（35 个组合）、`actions`（动作 → `verdict` 映射）、`verdict_aggregation`、
    `hard_constraints`（H1–H6）。
  - `contracts/audit_result.schema.json` / `contracts/evidence_reference.schema.json` /
    `contracts/module_handoff.schema.json` / `contracts/skill_input.schema.json` /
    `contracts/rule_envelope.schema.json` —— 输出契约（全部只读、冻结）。
  - `data/schema/rule.schema.json` / `data/schema/rule_collection.schema.json` /
    `data/schema/product.schema.json` —— 规则与商品的字段枚举。
  - `rules/01_prohibited_restricted_items.json`、`rules/05_medicines_health.json`（可写，
    本模块拥有）、`rules/03_listing_violations_duplicates.json` 的 `LV` 部分（**只读**）。
  - `tools/scan_lexicon.py`（本模块拥有）—— 词库扫描器实现，
    `skills/shopee-br-listing-audit/src/sbr_listing_audit/lexicon.py` 复用它而不重复实现。
- **我期待下游提供的**：
  - 上游把商品字段规范化好（**尤其是 NFC 规范化**，见 §3 #2），
    否则规则层会漏检。
  - 上游以 `target_ref = product_id` 输出，使同一商品的多模块结果能聚合到一起。
  - 下游（`shopee-br-reporting`）按 `action` 区分 `require_evidence`（补齐后复审）
    与 `block`（不得上架）的呈现 —— 两者的 `verdict` 都是 `REVIEW` / `BLOCK`，
    只有 `action` 不同。
  - 下游不要把 `EV-LEX-*` 条目当作违规证据（词库只产出信号）。
- **我对其他模块的影响**：
  - 本模块定义了 `PI` / `RI` / `MED` / `LV` 四类结论的语义边界。
    `shopee-br-ip-review` 负责 `SBR-IP-*`，`shopee-br-duplicate-detection` 负责
    `SBR-DUP-*` / `SBR-RL-*` / `SBR-AU-*` / `SBR-AC-*`。
  - **本模块不加载 IP 与 DUP 规则**：`rules.py` 的 `load_rules()` 按
    `OWNED_PREFIXES = ("PI", "RI", "MED", "LV")` 过滤；即使上游通过
    `SkillInput.rules[]` 传入 IP 规则也会被丢弃。
  - `contracts/lexicon_rule_map.json` 里 37 个词组中有 **30 个映射到本模块的规则**，
    **7 个只映射到他模块**（`ip_marca_cn`、`ip_marca_br`、`ip_entretenimento`、
    `ip_esportes`、`ip_variante_marca`、`ip_copyright`、`ip_shopee_asset`）。
  - `rules/03_listing_violations_duplicates.json` 仍混有 `LV` 与 `DUP` 两组前缀。
    拆分建议见 `tasks/task_registry.json` 的 `split_request` 字段，
    **本模块未修改该文件**。

---

## 5. 契约变更建议

**无 blocking 级契约变更建议。** 现有冻结契约足以支撑本模块的全部行为。

以下 3 条是 **non-blocking** 的使用说明 / 改进建议，**本模块不自行改动**：

### 5.1 `contracts/evidence_reference.schema.json` 的 `examples` 建议补两项

- **问题**：本模块的 `SBR-LV-002` 使用 `price_history` 与 `promotion_terms`
  两个 `evidence_type` 键，契约的 `examples` 列表里没有这两项。
- **证据**：`contracts/evidence_reference.schema.json` 的 `examples` 共 24 项，
  本模块用到的 15 种键里有 13 种在列表内，2 种不在。
- **建议变更**：在 `examples` 里补上 `price_history` 与 `promotion_terms`。
- **影响面**：仅 `examples`（非 `enum`），**不影响任何校验结果** —— 现有产出已经通过
  `contracts/audit_result.schema.json` 的校验。
- **严重度**：non-blocking。

### 5.2 `contracts/risk_action_matrix.json` 建议补一个显式的动作粒度数组

- **问题**：`verdict_aggregation.rule = "max_with_action_detail"` 要求「action 保留最细粒度的那一条」，
  但矩阵的 `actions` 段没有显式声明**粒度顺序**。
- **证据**：本模块的实现依赖 `engine.py` 的 `ACTION_GRANULARITY` 常量
  （`allow` 0 < `flag_for_review` 1 < `require_evidence` 2 < `revise` 3 <
  `block` 4 < `freeze_relist` 5 < `escalate_legal` 6）。
  矩阵的 `actions` 段**声明顺序**恰好也是这个顺序，但那是隐式约定。
- **建议变更**：在矩阵里补一个显式的 `action_granularity` 数组。
- **影响面**：本模块的现有实现无需改动即可继续工作；补上后判定逻辑与契约的对应关系更显式。
- **严重度**：non-blocking。

### 5.3 `contracts/risk_action_matrix.json` 的 `hard_constraints` 建议补一条关于时效的条款

- **问题**：H1–H6 覆盖了 IP、阻断、缺失输入、引文、证据、human_only，
  但**没有**覆盖「规则来源过期后如何处理」。
- **证据**：模块不实现基于 `last_verified` 的自动降级（见 §3 #1），
  这件事目前只由 `references/policy_currency.md` §6 的流程描述承载。
- **建议变更**：在 `hard_constraints` 里加一条（例如 H7）明确
  「规则的时效判断是人工流程，不由模块自动降级」，
  或反过来明确要求实现自动降级并给出阈值口径。
- **影响面**：若选择实现自动降级，会改变判定行为，需要同步更新
  `references/audit_semantics.md` §6 与 `references/policy_currency.md` §6。
- **严重度**：non-blocking（现状本身是安全的 —— 过期规则仍需通过引文核验才能 `active`）。

---

## 6. 自我约束核查

- [x] **只改了白名单内的文件** —— `git status --short` 显示本次仅
      `M skills/shopee-br-listing-audit/references/audit_semantics.md`、
      `M skills/shopee-br-listing-audit/references/evidence_checklist.md`、
      `M skills/shopee-br-listing-audit/references/false_positive_control.md`、
      `M skills/shopee-br-listing-audit/references/policy_currency.md`
      + 新增 `skills/shopee-br-listing-audit/DELIVERY.md`。
      `skills/shopee-br-ip-review/references/**` 的 4 个文件是**另一个并行 Agent** 的产出，
      本任务未触碰。
- [x] **未修改公共契约** —— `contracts/**`、`PROJECT_RULES.md`、
      `AGENT_COLLABORATION.md`、`manifest.json`、`tasks/**`、`tests/test_plan.md`、
      `docs/**`、`tools/**`、`scripts/**` 全部未改。
- [x] **未修改他人拥有的文件** —— `rules/**`、`research/**`、`lexicon/**`、
      `tests/fixtures/**` 全部未改。`rules/03_listing_violations_duplicates.json`
      只读引用（`split_request` 已在任务注册表里登记）。
- [x] **引文核验通过** —— `tools/verify_citations.py` 全库 `50/50 excerpts verified verbatim, 0 failed`；
      另对本次 4 份文档里的 34 段原文做了独立核验，`34/34 quotes verified, 0 failed`。
- [x] **自有测试实际执行** —— 383 项全通过，输出见 §2.1（退出码 0）。
- [x] **全项目校验实际执行** —— `scripts/check_all.sh` 退出码 0，
      `ALL CHECKS PASSED`，输出见 §2.2。
- [x] **4 份 references 内容已填实** —— 合计 1,880 行，**无 TODO / FIXME / 占位符**
      （逐文件检查过）。骨架里的「待 TASK-LISTING-01 确定」章节已全部替换为实测结论。
- [x] **状态与版本** —— 4 份文档均改为 **Active**，版本 **1.0.0**。
- [x] **verdict / confidence 取值合法** —— 文档里出现的 `verdict` 全部取自
      `PASS` / `REVISE` / `REVIEW` / `BLOCK`，`confidence` 全部取自
      `signal` / `likely` / `confirmed`（`tools/task_pack_check.py` 的
      「文档中 verdict 取值合法」段通过，352 项全过）。
- [x] **路径引用为仓库根相对且无悬空** —— 60 个 (文件, 引用) 组合全部可解析，
      `tools/framework_check.py` 的悬空引用守卫通过。
- [x] **硬约束 H1–H6 已逐条自查** —— `run_tests.py` 的 `L4` 段有逐条断言；
      `references/audit_semantics.md` §10 有逐条落点表。
- [x] **未执行 git commit / git push** —— 由主 Agent 统一提交。
