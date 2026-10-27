# SBRCA — Shopee Brazil Compliance Agent Skills

> **项目定位**：一套可供**不同 Agent、不同模型**使用的 **Skills 集合**，不是一个需要立即部署的完整软件服务。

| 字段 | 值 |
|---|---|
| 项目代号 | SBRCA |
| 阶段 | 第一轮 — 公共契约、模块说明、任务包已就绪 |
| 契约版本 | 1.0.0 |
| 所有权版本 | 1.2.0 |
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

### ③ 可直接分发的独立任务包

`tasks/TASK-*.md` 共 9 份，每份 12 个章节，**自包含**（执行 Agent 不需要读历史对话）。

```
TASK-POLICY-01      官方政策研究与来源核查        G2
TASK-INGEST-01      多格式资料读取与标准化        G2
TASK-LISTING-01     商品内容合规审核              G3
TASK-DUP-01         重复刊登与违规重发检查         G3
TASK-IP-01          知识产权与授权风险筛查         G3
TASK-REPORT-01      审核结果汇总与报告生成         G3
TASK-MAIN-01        主 Skill                      G4
TASK-INTEGRATE-01   集成验收                      G5
TASK-FRAME-02       测试与验收标准（第一轮已完成）
```

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

第一阶段（Phase 0/1）的原型实现**已核实从未入库**（git 全历史无该路径，本机与同主机另一仓库
共 30593 条目零匹配，6 项检查见 `.archive/README.md` §2.1）。归档目录当前为空，
本项目**不依赖任何原型参考实现** —— 模块行为以冻结契约为唯一权威依据。

```bash
cat .archive/README.md    # 核实记录 + 归档区使用约定
```

详见 `.archive/README.md` §2（缺失核实）与 §3（原型的替代实现路径）。

---

## 验证

```bash
env -u LD_LIBRARY_PATH bash scripts/check_all.sh
```

| 步骤 | 检查 | 结果 |
|---|---|---|
| 0/5 | 框架自检（`tools/framework_check.py`） | **303 项全通过** |
| 1/5 | 公共契约校验（`tools/validate_contracts.py`） | **18 项全通过** |
| 2/5 | 规则库 + 词库 Schema 校验 | 0 错误 0 警告 |
| 3/5 | 引文逐字核验 | **50/50 通过** |
| 4/5 | 共享夹具校验 | 9 商品 / 3 案件 / 8 场景全通过 |
| 5/5 | 任务包与所有权一致性（`tools/task_pack_check.py`） | **368 项全通过** |

---

## 命名说明

章程要求建立 `AGENTS.md`。该文件名被宿主平台保留用于其自身的 Agent 指令注入，写入被系统拦截（保护文件）。协作规范因此落在 **`AGENT_COLLABORATION.md`**，内容与职责等同于章程所指的 `AGENTS.md`，并在 `manifest.json` 的 `governance.agent_collaboration_doc` 字段登记。

---

## 下一阶段

分发波次 2（`TASK-INGEST-01` 建议优先，产出是其余模块的输入）与 `TASK-POLICY-01`。

待裁定：`docs/SBRCA-P0-004_open_questions.json`（5 冲突 + 9 问题，每项带 `default_if_no_answer`），该文件**现存于 `docs/`**。
