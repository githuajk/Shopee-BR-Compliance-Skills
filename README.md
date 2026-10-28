# SBRCA — Shopee Brazil Compliance Agent Skills

> **项目定位**：一套可供**不同 Agent、不同模型**使用的 **Skills 集合**，不是一个需要立即部署的完整软件服务。

| 字段 | 值 |
|---|---|
| 项目代号 | SBRCA |
| 阶段 | 第二轮 — 统一 SOP 与合并词库已并入 |
| 契约版本 | 1.0.0 |
| 所有权版本 | 1.3.0 |
| manifest | 1.1.0 |
| 最后更新 | 2026-10-27 |

---

## 快速开始

```bash
cd /config/dianshang/shopee-br-compliance-agent

# 全量校验（5 步）
env -u LD_LIBRARY_PATH bash scripts/check_all.sh
```

> **为什么要 `env -u LD_LIBRARY_PATH`？** Hermes 自带运行时会让 `libcrypto.so.3` 覆盖系统 OpenSSL，导致 `import ssl` 失败。

---

## 我该看哪份文档？

| 你是谁 | 先读 | 再读 |
|---|---|---|
| **店主 / 老板** | `docs/USER_SOP.md` §1 §2 §9 §10 | `docs/USER_SOP.md` §8（怎么看报告） |
| **运营 / 执行人** | `docs/USER_SOP.md`（全文，按步骤做） | `docs/SOP_COMPLIANCE_REVIEW.md`（判定语义与铁律细节） |
| **审核执行人** | **`docs/MANUAL_REVIEW.md`**（纯手工手册，不需看代码） | `docs/USER_SOP.md` §5 §6 §7 |
| **开发 Agent** | `PROJECT_RULES.md` + `AGENT_COLLABORATION.md` | `tasks/*.md`（自包含任务包） |

> **三份 SOP 的分工**
> - `docs/USER_SOP.md` —— **给使用者看**。回答"做什么、按什么顺序做、做完交什么、遇到问题怎么办"。
> - `docs/MANUAL_REVIEW.md` —— **给人工审核员看**。纯手工、无代码：查什么、怎么判、改成什么样。
> - `docs/SOP_COMPLIANCE_REVIEW.md` —— **给判定层看**。回答"什么算违规、怎么判定、哪些铁律不能破"。
> - USER_SOP 与 MANUAL_REVIEW **不新增任何判定规则**，只做流程框架与操作入口；判定依据一律来自 `rules/*.json` 与 `research/violation_codes.json`。

---

## 三个交付物

### ① 公共契约与全局规范

| 文件 | 作用 |
|---|---|
| `PROJECT_RULES.md` | 公共工程规范：定位、格式政策、契约总览、四态语义、风险×动作、规则 ID、证据引用、复核要求、错误处理、交付标准、命名、禁止事项 |
| `AGENT_COLLABORATION.md` | 多 Agent 协作规则：分工、边界、冲突处理、变更建议流程、交付规范 |
| `contracts/skill_input.schema.json` | 统一输入格式 |
| `contracts/audit_result.schema.json` | 统一输出格式 |
| `contracts/rule_envelope.schema.json` | 规则外层格式 |
| `contracts/evidence_reference.schema.json` | 证据引用格式 |
| `contracts/risk_action_matrix.json` | 风险×动作矩阵 + 硬约束 H1–H6 |
| `contracts/module_handoff.schema.json` | 模块交接格式 |
| `contracts/file_ownership.json` | **文件所有权登记（唯一权威来源）** |
| `manifest.json` | 项目清单 |
| `tasks/task_registry.json` | 任务注册表 |
| `tasks/task_template.md` | 任务说明模板 |
| `tests/test_plan.md` | 统一测试与集成验收标准 |
| `contracts/lexicon_rule_map.json` | 词组 → 规则映射 |
| `docs/SOP_COMPLIANCE_REVIEW.md` | ★ **统一审核 SOP**（合并历史全部方法） |
| `docs/USER_SOP.md` | ★★ **使用者操作规程**（店主/运营/审核人看的端到端流程框架） |
| `docs/MANUAL_REVIEW.md` | ★★ **人工审核操作手册**（纯手工，无代码：查什么/怎么判/改成什么样） |

### ② 七个 Skill 的模块说明与文件所有权

```
skills/
├── shopee-br-policy-research/     官方政策研究与来源核查
├── shopee-br-listing-audit/       商品内容合规审核
├── shopee-br-duplicate-detection/ 重复刊登与违规重发检查
├── shopee-br-ip-review/           知识产权与授权风险筛查
├── shopee-br-data-ingestion/      多格式资料读取与标准化
├── shopee-br-reporting/           审核结果汇总与报告生成
└── shopee-br-compliance/          ★ 主 Skill（分流 + 整合）
```

每个 `SKILL.md` 含七要素 + 文件所有权章节：

```
frontmatter（name / description）
1. 职责          2. 非职责
3. 输入契约      4. 输出契约
5. 规则与来源要求  6. 失败处理
7. 测试案例与验收标准
8. 依赖          9. 文件所有权
10. 待填内容     11. 变更记录
```

每个模块另有 `references/` 下的深度说明（共 27 份），如：

| 模块 | references |
|---|---|
| listing-audit | `audit_semantics.md`（四态语义）、`evidence_checklist.md`、`false_positive_control.md`（葡语词边界坑）、`policy_currency.md` |
| ip-review | `ip_categories.md`、`nominative_use.md`（Art. 132 II 指示性使用）、`authorization_checklist.md`、`dissolution_flow.md`（只有撤诉能解封） |
| duplicate-detection | `relist_axes.md`（封禁 vs 删除）、`duplicate_signals.md`、`case_workflow.md`、`penalty_mechanics.md` |
| data-ingestion | `format_matrix.md`、`field_mapping.md`、`provenance.md`、`lexicon_format.md` |
| policy-research | `source_registry.md`、`violation_codes.md`、`citation_verification.md`、`platform_policy_summary.md` |
| reporting | `report_structure.md`、`aggregation_rules.md`、`evidence_citation.md` |
| compliance（主） | `routing.md`、`execution_workflow.md`、`integration_rules.md`、`degradation.md` |

### ②b 合并词库（37 组 / 856 词）

| 文件 | 用途 | 规模 |
|---|---|---|
| `lexicon/term_groups.json` | 词组（扫描用） | 37 组 / 856 词 |
| `lexicon/rewrite_map.json` | 触线 → 中性替代（改写用） | 8 类映射 |
| `lexicon/exemptions.json` | 误报豁免规则 | 7 条 |
| `lexicon/quality_patterns.json` | 套模板/批量味检测 | 15 条特征 |
| `lexicon/non_avoidable.json` | 无法文字规避的品类 | 6 类 |
| `lexicon/verb_conjugations.json` | 葡语动词变位匹配表 | 7 个动词 |
| `contracts/lexicon_rule_map.json` | 词组 → 规则映射 | 37 条 |

**合并来源**：2026-09-15 合规审计线 7 类 1320 词词库 + `02_risk_dictionary` 触线词 + 原 25 组 179 词。
**覆盖率 96.3%**（逐词比对；剩余为文档说明文字而非词条）。

### ③ 可直接分发的独立任务包

`tasks/TASK-*.md` 共 9 份，每份 12 个章节，**自包含**（执行 Agent 不需要读历史对话）。

```
TASK-POLICY-01      官方政策研究与来源核查        G2  ✅ 已完成
TASK-INGEST-01      多格式资料读取与标准化        G2  ✅ 已完成
TASK-LISTING-01     商品内容合规审核              G3  ✅ 已完成
TASK-DUP-01         重复刊登与违规重发检查         G3  ✅ 已完成
TASK-IP-01          知识产权与授权风险筛查         G3  ✅ 已完成
TASK-REPORT-01      审核结果汇总与报告生成         G3  ✅ 已完成
TASK-MAIN-01        主 Skill（编排层）            G4  ✅ 已完成
TASK-INTEGRATE-01   集成验收                      G5  ✅ 已完成 2026-10-28
TASK-FRAME-02       测试与验收标准               ✅ 已完成
```

**10/10 任务全部完成。** 集成验收报告见 `docs/integration_report.md`，
集成验收脚本见 `tests/integration/run_tests.py`（226 项断言全过）。

---

## 核心设计

### 调用语义（关键）

> 目标平台**不保证** Skill 之间存在自动调用能力。

主 Skill 因此被设计为**显式读取** `skills/<module>/SKILL.md` 的工作流：

```
主 Skill 读模块 SKILL.md → 依契约构造输入 → 依契约取得并校验输出
  → 依 risk_action_matrix 整合 → 记录 module_handoff
```

任何"自动调用"表述都视为契约违规。**平台若将来提供自动调用能力，只替换执行层，契约与判定语义不变。**

### 风险等级 × 处理动作（正交）

| 风险等级 | 处理动作 |
|---|---|
| `info` `low` `medium` `high` `critical` | `allow` `flag_for_review` `require_evidence` `revise` `block` `freeze_relist` `escalate_legal` |

矩阵定义全部 35 个组合的允许性、结论聚合规则（`max_with_action_detail`）与 6 条硬约束。

### 六条硬约束

| ID | 约束 |
|---|---|
| **H1** | IP 类结论恒为 `signal` + 强制人工复核 |
| **H2** | `block`/`freeze_relist`/`escalate_legal` 只来自 `platform_official`/`law` 的 `active` 规则；确定性结论不可被降级 |
| **H3** | 输入缺失 → 该规则不评估 + 必须上报 `unevaluated`；**不得当作通过** |
| **H4** | `source.excerpt` 必须逐字出现在 `research/raw/` 抓取件中 |
| **H5** | `artifact_ref` 只存引用，不内嵌凭证内容 |
| **H6** | `freeze_relist`/`escalate_legal` 为 `human_only` |

---

## 并行开发

### 依赖图

```
FRAME-01 → FRAME-02 → {POLICY-01, INGEST-01} → {LISTING-01, DUP-01, IP-01, REPORT-01} → MAIN-01 → INTEGRATE-01
```

**最大并行度 4**（G3 四个专业模块，路径零重叠 —— 机械校验通过）。

### 文件所有权

`contracts/file_ownership.json` 是**唯一权威来源**。同一路径只有一个 owner。

唯一潜在冲突是 `rules/03_listing_violations_duplicates.json`（含 `LV` 属 listing-audit、`DUP` 属 duplicate-detection）—— 两者都**只提拆分建议**，由集成 Agent 统一拆分。

**三方一致性**（`tools/task_pack_check.py` 368 项断言强制）：
`SKILL.md` 所有权章节 ≡ `tasks/*.md` §2.1 白名单 ≡ `task_registry.json` `allowed_paths`

### 公共契约冻结

`PROJECT_RULES.md` `AGENT_COLLABORATION.md` `contracts/**` `manifest.json` `tasks/**` `tests/test_plan.md` `docs/**` `tools/**` `scripts/**` 对模块 Agent **只读**。

发现问题 → 提交变更建议（`AGENT_COLLABORATION.md` §4.1）→ 集成 Agent 审查并统一修改。

---

## 格式政策

| 用途 | 格式 |
|---|---|
| 规则、配置、结构化数据、测试数据、Schema、任务注册表、清单 | **JSON** |
| 文档、Skill 指令、模块说明、调研报告、测试说明 | **Markdown** |
| `SKILL.md` frontmatter | 平台强制 YAML —— **唯一豁免** |
| 源码、二进制素材、外部输入 | 平台标准扩展名 |

**禁止** YAML / JSONL / CSV / TXT / XML 作内部正式数据源。外部输入读取后统一转换为项目数据模型。

---

## 归档区

第一阶段（Phase 0/1）的原型实现**已于 2026-10-27 归档入库**于
`.archive/phase0_prototype/`（48 个文件：docs 18 / src 13 / tests 1 / prompts 1 /
out 2 / 其它 13）。

> **核实结论有变更**：v2.0.0 曾记录「从未入库」，依据是当时的 6 项检查
> （git 全历史无该路径、本机与同主机另一仓库 30593 条目零匹配等）。
> **该结论在当时成立**，但同日稍后原型文件重新出现在工作区并已提交入库 ——
> 详见 `.archive/README.md` §2.1 的变更记录。

归档内容**不参与活跃框架的路径引用校验**，也**不在活跃校验流程中**
（它们的端到端校验不计入 `scripts/check_all.sh`）。本项目**不依赖原型参考实现** ——
模块行为以冻结契约为唯一权威依据。

```bash
cat .archive/README.md    # 核实记录（含结论变更）+ 归档区使用约定
```

详见 `.archive/README.md` §2（核实与结论变更）与 §3（原型的替代实现路径）。

---

## 验证

```bash
env -u LD_LIBRARY_PATH bash scripts/check_all.sh
```

| 步骤 | 检查 | 结果 |
|---|---|---|
| 0/10 | 框架自检（`tools/framework_check.py`） | **272 项全通过** |
| 1/10 | 公共契约校验（`tools/validate_contracts.py`） | **19 项全通过** |
| 2/10 | 合并词库校验（`tools/validate_lexicon.py`） | **305 项全通过**（37 组 / 856 词 / 37 条映射 / 50 条规则） |
| 3/10 | 词库扫描器自测（`tools/scan_lexicon.py --self-test`） | **12/12 通过** |
| 4/10 | 规则库 + 词库 Schema 校验 | 0 错误 0 警告 |
| 5/10 | 引文逐字核验 | **50/50 通过** |
| 6/10 | 来源清单与抓取件一致（`tools/check_sources.py`） | 17 条来源 / 17 个抓取件一致 |
| 7/10 | 规则触发正则可编译性（`tools/check_rule_regex.py`） | **50 条规则 / 36 条正则全部可编译，无逻辑自指** |
| 8/10 | 共享夹具校验（Schema） | 90 商品 / 10 案件 全通过 |
| 9/10 | 夹具与规则库一致性（`tools/verify_fixtures.py`） | **108 条夹具-规则断言全通过** |
| 10/10 | 任务包与所有权一致性（`tools/task_pack_check.py`） | **256 项全通过** |

### 各模块自有测试

```bash
env -u LD_LIBRARY_PATH python3 tests/<module>/run_tests.py
env -u LD_LIBRARY_PATH python3 tests/integration/run_tests.py   # 集成验收
```

| 模块 | 断言数 | 模块 | 断言数 |
|---|---|---|---|
| `shopee-br-policy-research` | 1467 | `shopee-br-reporting` | 210 |
| `shopee-br-duplicate-detection` | 587 | `shopee-br-listing-audit` | 383 |
| `shopee-br-ip-review` | 236 | `shopee-br-data-ingestion` | 211 |
| `shopee-br-compliance` | 110 | **集成验收** | **226** |

### 校验工具的分工

| 工具 | 抓什么 |
|---|---|
| `verify_citations.py` | 引文是否逐字出现在 `research/raw/` 抓取件中（不编造来源） |
| `check_sources.py` | 来源清单 ↔ 抓取件 ↔ 抓取报告 ↔ 规则引用 是否一致 |
| `scan_lexicon.py` | 词库扫描器：归一化、组级边界策略、豁免、位置记录 |
| `validate_lexicon.py` | 合并词库的分组结构、变位覆盖、豁免与改写映射 |
| `check_rule_regex.py` | 规则正则能否编译；`requires_input` 是否自指；数值算子是否作用于文本字段 |
| `verify_fixtures.py` | 夹具声明的期望是否成立（正例真命中、反例真不命中、豁免真生效） |
| `task_pack_check.py` | 任务包枚举是否与冻结契约一致；文档中 `verdict` 取值是否合法；`ownership_version` 是否漂移 |
| `framework_check.py` | 框架不变量；文档内部路径引用是否悬空 |

---

## 命名说明

章程要求建立 `AGENTS.md`。该文件名被宿主平台保留用于其自身的 Agent 指令注入，写入被系统拦截（保护文件）。协作规范因此落在 **`AGENT_COLLABORATION.md`**，内容与职责等同于章程所指的 `AGENTS.md`，并在 `manifest.json` 的 `governance.agent_collaboration_doc` 字段登记。

---

## 下一阶段

**10/10 任务已全部完成。** 剩余工作不再是开发，而是以下三项**待裁定**事项：

| # | 事项 | 归属 | 阻塞性 |
|---|---|---|---|
| 1 | `docs/SBRCA-P0-004_open_questions.json`（14 项待裁定：5 冲突 + 9 问题，每项带 `default_if_no_answer`） | 用户 | 否 —— 可按默认值执行 |
| 2 | **C5**：`rules/03_listing_violations_duplicates.json` 拆分（LV → listing-audit，DUP → duplicate-detection） | 集成 Agent，需扩白名单 | 否 |
| 3 | **C6**：`audit_result.schema.json` 的 4 个 `evidence_type`（`image` / `listing_field` / `price_history` / `promotion_terms`）超出示例集 | 集成 Agent，需扩白名单 | 否 |

另有一项**已知范围外**的缺口：`shopee-br-policy-research` 无 `src/` 实现
（目录级：references + 测试），当前可接受。

集成验收报告见 `docs/integration_report.md`，集成脚本见 `tests/integration/run_tests.py`。
