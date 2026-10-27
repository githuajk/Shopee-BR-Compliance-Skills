# .archive/ — 临时归档区

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-ARCH-001` |
| 版本 | 1.0.0 |
| 状态 | **Active — 临时保留，可随时调用回迁** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 第一阶段（Phase 0/1）产物与原型实现的临时存放 |
| 相关文档 | `PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、`manifest.json` |
| 未决事项 | 归档内容何时回迁或正式废弃，待用户裁定 |

---

## 1. 用途

用户指示：**旧文件先保留到临时文件夹，在需要时候调用**。

本目录是**唯一**的临时保留区。内容**不删除**，仅移出活跃工作区，避免与新的 Skills 集合框架产生版本冲突与阅读干扰。

---

## 2. 归档内容清单

### 2.1 `docs/` — Phase 0/1 治理文档（18 份）

| 路径 | 原位置用途 | 何时调用 |
|---|---|---|
| `docs/SBRCA-P0-001_directory_status.md` | 初始目录清单与资产归属 | 需要知道"哪些是用户原有文件"时 |
| `docs/SBRCA-P0-002_requirements_recovery.md` | 历史需求恢复、来源分级 | 需要追溯需求来源时 |
| `docs/SBRCA-P0-003_requirement_register.json` | 52 条需求追踪清单 | 需要做需求覆盖分析时 |
| `docs/SBRCA-P0-004_open_questions.json` | 14 项待裁定（5 冲突 + 9 问题） | **裁定前必读** |
| `docs/SBRCA-P0-005_phase_report.md` | Phase 0/1 阶段报告 | 需要了解上一阶段实际执行结果时 |
| `docs/SBRCA-P1-001_charter.md` | 项目总章程（工程治理规范） | 需要引用治理原则时 |
| `docs/SBRCA-P1-002_architecture.md` | 架构设计 | 需要引用分层与接口设计时 |
| `docs/SBRCA-P1-003_data_spec.md` | 数据与 Schema 规范 | 需要定义新数据字段时 |
| `docs/SBRCA-P1-004_security_model.md` | 威胁模型与权限矩阵 | 需要做安全评审时 |
| `docs/SBRCA-P1-005_test_strategy.md` | 九层测试策略 | 需要扩展测试层次时 |
| `docs/SBRCA-P1-007_roadmap.md` | Phase 0–7 路线图 | 需要排期时 |
| `docs/adr/SBRCA-ADR-0001..0006` | 6 份架构决策记录 | 需要查"为什么这样定"时 |
| `docs/ARCHITECTURE.md` | 旧原型架构（描述 `src/`） | 归档回迁后参考 |
| `docs/RESEARCH_REPORT.md` | 官方政策调研报告 | **需要平台政策细节时** |
| `docs/SOP.md` | 旧操作手册 | 归档回迁后参考 |

### 2.2 `src/` — 第一阶段原型实现（13 份）

`compliance_agent/` 完整包：models / ingest.parsers / engine.{loader,evaluator,duplicates,relist,reviewer} / report.markdown。

**定位**：行为参考实现，**可读不可改**（见 `manifest.json` → `shared_assets.reference_implementation`）。

**用途**：为模块 Agent 提供**可运行的判定语义参照** —— 尤其 `engine/evaluator.py` 的 `requires_input` 语义、`engine/relist.py` 的冻结状态优先级、`engine/duplicates.py` 的跨店匹配。

### 2.3 `tests/run_tests.py` — 旧测试套件（333 项）

**定位**：原型的回归基线。归档后**不在活跃校验流程中**（`scripts/check_all.sh` 已相应调整）。

**用途**：模块 Agent 实现判定逻辑时，可作为**行为对照** —— 新实现必须产生与原型一致的结论。

### 2.4 `prompts/agent_prompt.md` — 旧 Agent 提示词

**定位**：早期单 Agent 提示词。新框架下每个 Skill 各自有 `SKILL.md`，本文件已不再接入执行链。

### 2.5 `out/` — 上一次原型运行的输出

`review_report.md` + `review_result.json`。纯构建产物，可随时重新生成或删除。

---

## 3. 调用方式

### 3.1 只读查阅（推荐）

```bash
cat .archive/phase0_prototype/docs/RESEARCH_REPORT.md
```

### 3.2 单文件回迁

```bash
cp .archive/phase0_prototype/docs/RESEARCH_REPORT.md docs/
```

回迁后**必须**更新引用方的路径，并检查 `tools/framework_check.py` 是否仍通过。

### 3.3 整组回迁

```bash
cp -r .archive/phase0_prototype/src .
```

> ⚠️ 回迁 `src/` 会使 `scripts/check_all.sh` 恢复旧的校验步骤。回迁前请确认这符合当前阶段意图。

---

## 4. 保留期限与清理条件

满足**任一**条件时，本目录可正式清理（需用户确认）：

1. 七个 Skill 全部通过集成验收，原型行为已完全被新实现覆盖。
2. `docs/SBRCA-P0-004_open_questions.json` 的 14 项裁定全部落地，相关治理文档正式 Approved。
3. 用户显式指示删除。

**在满足上述条件前，本目录只增不删。**

---

## 5. 变更记录

| 日期 | 变更 |
|---|---|
| 2026-10-27 | 建立归档区，移入 48 个文件（docs 18 / src 13 / tests 1 / prompts 1 / out 2 / 其它 13） |
