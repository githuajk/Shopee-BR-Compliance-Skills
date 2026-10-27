# TASK-IP-01 交付说明 —— references 填实

> 任务：`TASK-IP-01` —— 知识产权与授权风险筛查
> 模块：`shopee-br-ip-review`
> 契约版本：1.0.0
> 交付日期：2026-10-27
> 本次范围：**4 份 references 文档填实 + 本交付说明**（不含代码改动）

---

## 1. 文件清单

| 路径 | 动作 | 说明 |
|---|---|---|
| `skills/shopee-br-ip-review/references/ip_categories.md` | 修改 | 53 → 290 行。IP 四类的定义、法律依据（具体法条）、平台违规码、对应规则 ID、典型场景。**如实写明专利类（`ip_patent`）当前无规则** —— `rules/02_ip_trademark_copyright.json` 里没有该 category 的规则，引擎既不命中也不记 `unevaluated[]`。另写明 `SBR-IP-008` 与 `SBR-IP-005` 触发条件完全相同（复用图片 logo 信号，未做外观相似度比对）。 |
| `skills/shopee-br-ip-review/references/nominative_use.md` | 修改 | 62 → 286 行。Art. 132, II 的判定要素对比表、正反例（含实测输出）、**代码里的实际豁免行为**：`SBR-IP-006` 命中时覆盖 `SBR-IP-001`（品牌宣称），**不**豁免 `SBR-IP-002`（假货宣称）—— 8 条规则的豁免与否逐条列表。含 5 项已知局限（`brand` 字段填他人商标仍判 `PASS`、词表只有 18 个品牌、兼容性措辞只认 5 种写法等）。 |
| `skills/shopee-br-ip-review/references/authorization_checklist.md` | 修改 | 70 → 319 行。`history` 字段结构（`authorization_documents` / `missing`）、**有清单 vs 无清单的区别（无清单 = 状态未知，不是「未授权」）**、10 种 `history` 形态的实测行为矩阵、缺材料时动作是 `require_evidence` 而非 `block`（含与品牌规则同时命中时的聚合说明）、INPI 商标注册核验的 8 步人工流程。 |
| `skills/shopee-br-ip-review/references/dissolution_flow.md` | 修改 | 63 → 304 行。IP 投诉的处理路径（Shopee Brand IP Portal 受理通道 + 通知内容 + 平台处置后果）、卖家可采取的动作（查原因 / 申诉 / 补材料 / 申请恢复 / 联系品牌方）、需准备的证据清单、**本模块不执行任何线上动作**的边界（附 `src/` 的 import 清单佐证）。 |
| `skills/shopee-br-ip-review/DELIVERY.md` | 新增 | 本文件。 |

**未改动**（本次范围内确认无 diff）：
`skills/shopee-br-ip-review/src/**`（含 `engine.py` / `evaluator.py` / `rules.py` / `matrix.py` / `sbr_ip_review_cli.py`）、
`skills/shopee-br-ip-review/SKILL.md`、
`tests/shopee-br-ip-review/**`、`rules/**`、`contracts/**`、`research/**`、
`lexicon/**`、`tools/**`、`scripts/**`、`docs/**`、`tasks/**`、`manifest.json`、`README.md`。

> 工作区里 `skills/shopee-br-listing-audit/**` 同时有未提交改动 ——
> 那是**并行 Agent** 的产出，不属于本任务，我未触碰。

## 2. 测试结果

### 2.1 模块自有测试

```bash
$ cd /config/dianshang/Shopee-BR-Compliance-Skills && env -u LD_LIBRARY_PATH python3 tests/shopee-br-ip-review/run_tests.py
```

实际输出（完整）：

```
==============================================================
shopee-br-ip-review 模块测试
仓库根: /config/dianshang/Shopee-BR-Compliance-Skills
==============================================================

=== L1 共享夹具 —— IP 场景逐条判定 ===

=== L2 硬约束 H1 —— IP 结论恒为 signal + 强制人工复核 ===

=== L3 指示性使用豁免（Lei 9.279/1996 Art. 132, II） ===

=== L4 硬约束 H2 —— 阻断类动作只来自权威 active 规则 ===

=== L5 硬约束 H3 —— 缺失输入记 unevaluated，不判通过 ===

=== L6 授权完整性维度 ===

=== L7 产出符合冻结契约 ===

=== L8 模块交接 ===

=== L9 CLI 端到端 ===

=== L10 规则库读不到必须显式失败 ===

==============================================================
PASSED: 228   FAILED: 0
耗时: 0.16s
模块测试全部通过。
```

**退出码 0。**

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
==============================================================
契约校验 — 通过 19，失败 0
公共契约全部通过。

== 2/10  合并词库校验（lexicon/ + 映射表）==
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

### 2.3 文档引文的额外逐字核验

4 份 references 里共 77 个引用块，其中 44 个是拉丁文引文（其余 33 个是中文说明性旁白，
不是引文，不参与核验）。逐字核验脚本覆盖三类来源：

| 来源类别 | 核验依据 | 结果 |
|---|---|---|
| 平台政策 / 巴西法律 | `research/raw/*.txt` 抓取件（`tools/verify_citations.py` 的同一套归一化） | 全部命中 |
| 引擎运行时字符串 | **实际跑一次引擎**取 `reason` / `review_rationale` / `provenance.notes` / `handoff.assumptions` / `handoff.known_gaps` | 全部命中 |
| 规则库 / 契约片段 | `rules/*.json`、`contracts/risk_action_matrix.json` | 全部命中 |

```
ALL 44 Latin quote blocks (of 77 blocks) verified verbatim
```

> **过程中修正了 3 处引文不准确**：初稿把引擎运行时字符串做了跨片段拼接
> （`review_rationale` 与 `known_gaps` 的中间被省略/插入），以及把
> `contracts/risk_action_matrix.json` 的 `require_evidence` 定义重排成了一行。
> 三处都改成了**逐字可核验**的形式 —— 前两处标为「非连续片段，分两段」并给出
> 各自的连续子串，第三处直接引用 JSON 原文代码块。

### 2.4 文档内容与引擎行为的实测比对

文档里每一条「实测」结论都来自对真实引擎的调用（`engine.review_products()`），
不是从代码推演的。覆盖的实测场景：

| # | 场景 | 实测结论 |
|---|---|---|
| 1 | 兼容性描述（全部维度可评估） | `fired=['SBR-IP-006']`、`allow` / `PASS` / info |
| 2 | 兼容性描述（图片与授权缺失） | `fired=['SBR-IP-006']`、`flag_for_review` / `REVIEW` / low、3 条 `unevaluated` |
| 3 | 品牌宣称 | `fired=['SBR-IP-001']`、`escalate_legal` / `BLOCK` / high |
| 4 | 假货宣称 | `fired=['SBR-IP-002']`、`escalate_legal` / `BLOCK` / critical |
| 5 | 指示性措辞 + 假货宣称 | `fired=['SBR-IP-002','SBR-IP-006']`、`escalate_legal` / `BLOCK` / critical（**`SBR-IP-002` 未被豁免**） |
| 6 | 兼容性 + 图片 logo | `fired=['SBR-IP-005','SBR-IP-006','SBR-IP-008']`、`flag_for_review` / `REVIEW` / medium |
| 7 | 仅授权缺口（无品牌词） | `fired=['SBR-AU-001']`、**`require_evidence` / `REVIEW` / high** |
| 8 | 授权缺口 + 品牌词 | `fired=['SBR-IP-001','SBR-AU-001']`、`escalate_legal` / `BLOCK` / high |
| 9 | 10 种 `history` 形态 | 见 `authorization_checklist.md` §2.1 的行为矩阵 |
| 10 | 缺输入（无 title/description） | 7 条规则记 `unevaluated`、`flag_for_review` / `REVIEW` / low、**`verdict != PASS`** |
| 11 | 干净商品 | `allow` / `PASS` / info、`review_rationale=None`、`requires_human_review=true` |
| 12 | 18 品牌词 × 5 兼容性措辞 = 90 组 | 85 组命中 `SBR-IP-006`；5 组（全是 `supreme`）只命中 `SBR-IP-001` |
| 13 | 专利维度商品 | `fired=[]`、`unevaluated=[]`、`allow` / `PASS` —— **专利维度根本没被检查** |
| 14 | `any_text` 字段覆盖 | `title` / `description` / `brand` / `category` / `model` + 图片 OCR；**不含** `attributes` / `notes` |

### 2.5 未执行的测试

| 测试 | 原因 |
|---|---|
| 重新抓取平台/法律页面 | 环境无可靠网络访问。`research/raw/` 下的抓取件是既有证据，**不重新抓取**是本任务的设计约束 |
| INPI 在线查询 | INPI 无公开接口可由本模块调用；核验是**人工流程**，见 `authorization_checklist.md` §6 |
| 修改 `rules/02_ip_trademark_copyright.json` 修复词表不一致 | 属规则库变更，超出本次「只写文档」范围。已作为未解决问题登记（§3 第 2 项） |

## 3. 未解决问题

| # | 问题 | 影响 | 建议 |
|---|---|---|---|
| 1 | **专利维度是盲区**：`rules/02_ip_trademark_copyright.json` 无 `ip_patent` 规则，但平台有 `[604]`（Alta，扣分）、法律有 Lei 9.279/1996 Art. 183 | 专利类商品**完全不会被筛查**，也不会记入 `unevaluated[]` —— 复核者容易把「没命中」误读成「已排查」 | 已在 `ip_categories.md` §6 如实写明。要补齐需引入**权利要求比对**能力（关键词/logo 匹配对专利无意义），属能力建设非文档问题 |
| 2 | `SBR-IP-006` 的品牌词表比 `SBR-IP-001` **少 `supreme`** | `Compatível com Supreme X` 不触发豁免 → `escalate_legal` / `BLOCK`（实测 5/90 组） | 在 `rules/02_ip_trademark_copyright.json` 里让两条规则共用同一份品牌词表 |
| 3 | 指示性使用豁免**不检查**被豁免规则命中的具体内容 | `brand` 字段填了 `Nike` + 描述有兼容性措辞 → 仍判 `allow` / `PASS` | 豁免逻辑应在抑制前检查 `SBR-IP-001` 的命中片段是否落在兼容性上下文内；本次已写进 `nominative_use.md` §8 作为复核必看项 |
| 4 | `SBR-IP-008`（外观设计）与 `SBR-IP-005`（图片 logo）触发条件**完全相同** | 外观设计维度没有独立检测能力；两者必然同时命中或同时不命中 | 需要真正的外观设计相似度比对才能拆开 |
| 5 | 品牌词表只有 18 个 | `Bosch` / `Philco` / `Electrolux` / `Brastemp` / `Consul` 等家电品牌完全不触发 | 扩充词表或改为外部维护的品牌清单 |
| 6 | 兼容性措辞只认 5 种写法 | `indicado para` / `serve para` / `destinado a` 等不触发豁免 | 扩充 `SBR-IP-006` 条件 1 的正则 |
| 7 | `any_text` 不含 `attributes` 与 `notes` | 藏在属性字段里的品牌词不触发商标规则 | 与 `data-ingestion` 的字段映射约定对齐后统一处理 |
| 8 | `SBR-AU-001` 的 `evidence_required` 是**受限类目**的材料（`anvisa_registration` 等），不含商标授权材料 | 授权缺口命中的时候，复核者拿不到「该补哪些品牌授权材料」的清单 | 该规则归 `shopee-br-duplicate-detection`；若要拆分品牌授权材料类型，需该模块的规则变更（见 §5） |
| 9 | 待裁定项 `Q-A`（品牌方撤诉是否作为解冻硬前置）未裁定 | 不影响本模块 —— 本模块不实现解冻判定，也不产出 `unfreeze` 动作 | 已在 `dissolution_flow.md` §7 登记为待裁定，并说明「无论裁定结果如何本模块行为都不需改动」 |

## 4. 依赖说明

- **我依赖的**：
  - `rules/02_ip_trademark_copyright.json`（本模块拥有，8 条 IP 规则）
  - `rules/04_cases_relist_authorization.json`（**只读**引用 `SBR-AU-001`）
  - `contracts/risk_action_matrix.json`（动作 → verdict 查表 + H1–H6）
  - `contracts/audit_result.schema.json`、`contracts/module_handoff.schema.json`、
    `contracts/evidence_reference.schema.json`（冻结契约）
  - `research/raw/*.txt`（引文逐字核验的证据）、`research/violation_codes.json`（平台码）
  - `data/schema/product.schema.json`（`history` / `images` 字段形状）
- **我期待下游提供的**：
  - `shopee-br-reporting` 消费本模块结果时**不得降级** `escalate_legal`
  - 主 Skill 整合时保留 `requires_human_review=true` 与 `confidence=signal`
- **我对其他模块的影响**：
  - `SBR-IP-006` 的兼容性识别可被 `shopee-br-listing-audit` 复用，避免重复实现
  - `SBR-AU-001` 的 `history_missing_nonempty` 算子与 `missing` 字段约定
    对 `shopee-br-duplicate-detection` 的授权判定同样有效

## 5. 契约变更建议

**无。**

本次只写文档，未触碰任何契约、规则、代码。核心理由：

1. 4 份文档描述的都是**代码里已经存在的行为**，没有提出新的契约要求；
2. §3 里的 9 个未解决问题中，#2 / #3 / #4 / #5 / #6 / #8 的修复都落在
   `rules/02_ip_trademark_copyright.json` 或 `rules/04_cases_relist_authorization.json`
   —— 前者本模块拥有、后者归 `shopee-br-duplicate-detection`，**都不需要改契约**；
3. 唯一涉及外部规则的 #8，若要拆分品牌授权材料类型，
   建议由 `shopee-br-duplicate-detection` 在 `SBR-AU-001` 的
   `evidence_required` 里增补 `brand_authorization_letter` /
   `trademark_registration` —— 那是**规则库**变更，**不是契约变更**，
   故不作为契约变更建议提出。

## 6. 自我约束核查

- [x] **只改了白名单内的文件** —— `git diff --stat -- skills/shopee-br-ip-review/`
      显示只有 4 份 `references/*.md` + 新增 `DELIVERY.md`
- [x] **未修改公共契约** —— `contracts/**`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、
      `manifest.json`、`tasks/**`、`tests/test_plan.md` 全部无 diff
- [x] **未修改他人拥有的文件** —— `rules/**`、`lexicon/**`、`research/**`、
      `docs/**`、`tools/**`、`scripts/**`、`tests/fixtures/**` 全部无 diff；
      `rules/04_cases_relist_authorization.json` 只被**读取**
- [x] **未修改本模块的实现代码** —— `src/**` 与 `tests/shopee-br-ip-review/**` 无 diff
- [x] **引文核验通过** —— 44 个拉丁文引用块逐字核验全部命中（§2.3）；
      `tools/verify_citations.py` 的 50/50 保持通过
- [x] **自有测试实际执行** —— 228 项全通过，输出见 §2.1，退出码 0
- [x] **全项目校验实际执行** —— `scripts/check_all.sh` 10 步全绿，输出见 §2.2，退出码 0
- [x] **SKILL.md 七要素齐全** —— 未改动，原有内容已满足
- [x] **references/ 内容已填实（无占位符）** —— 4 份文档共 1199 行；
      `grep` 扫描 `TODO` / `FIXME` / `待填` / `占位` / `TBD` / `XXX` **无命中**；
      状态由 Draft 改为 **Active**，版本 **1.0.0**
- [x] **文档描述的是真实行为，不是想象** —— 每条「实测」结论都来自对
      `engine.review_products()` 的实际调用（§2.4 的 14 组场景）
- [x] **硬约束 H1–H6 已逐条自查** ——
      H1（恒 `signal` + 恒人工复核）写进 `ip_categories.md` §2；
      H2（阻断类只来自权威 active 规则）在四份文档里都标注了规则的 `source_tier`；
      H3（缺输入记 `unevaluated`，不判通过）写进 `ip_categories.md` §2 与
      `authorization_checklist.md` §2；
      H4（引文逐字）见 §2.3；
      H5（证据只存路径）写进 `authorization_checklist.md` §4.1 与
      `dissolution_flow.md` §4.1；
      H6（`human_only`，不执行线上动作）写进 `dissolution_flow.md` §1 与 §3
- [x] **verdict / confidence 取值合法** —— 全文扫描 `verdict=` 只有
      `PASS` / `REVIEW` / `BLOCK` 出现（均在 `contracts/audit_result.schema.json`
      的 enum 内）；`confidence=` 只有 `signal`；
      `likely` / `confirmed` 仅出现在「永不使用」和枚举说明的语境里
- [x] **路径引用为仓库根相对** —— `tools/framework_check.py` 的悬空引用守卫
      通过（229 项全绿）；文档内引用的 `rules/…` / `research/raw/…` /
      `contracts/…` / `data/schema/…` / `docs/…` / `tests/…` 全部存在
- [x] **未执行 git commit / git push** —— 交由主 Agent 统一提交
- [x] **测试失败如实报告** —— 本次无失败；文档引文核验过程中发现并**修正**了
      3 处自身引文不准确（§2.3 末段），未隐瞒

## 7. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 0.1.0 | 2026-10-27 | 骨架创建（待 TASK-IP-01 填充） |
| 1.0.0 | 2026-10-27 | 4 份 references 填实为 Active；新增本交付说明 |
