# .archive/ — 归档区（当前为空）

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-ARCH-001` |
| 版本 | 2.0.0 |
| 状态 | **Active — 当前为空目录，保留待用** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 第一阶段（Phase 0/1）产物的临时存放位 |
| 相关文档 | `PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、`manifest.json` |
| 未决事项 | 归档内容已确认丢失，是否需要重新实现原型 —— 待用户裁定 |

---

## 1. 用途

本目录是临时保留区。内容**不删除**，仅移出活跃工作区，避免与新的 Skills 集合框架产生版本冲突与阅读干扰。

---

## 2. 当前状态：归档内容缺失（2026-10-27 核实）

> **本节记录的是核实结果，不是计划。**

v1.0.0 本文件曾声称"移入 48 个文件（docs 18 / src 13 / tests 1 / prompts 1 / out 2 / 其它 13）"，并逐条列出
`.archive/phase0_prototype/` 下的文件路径。**核实结果表明这些文件从未存在于版本库中。**

### 2.1 核实过程与证据

| # | 检查 | 方法 | 结果 |
|---|---|---|---|
| 1 | 归档目录实际内容 | `find .archive -type f` | **仅本 README.md 一个文件** |
| 2 | 是否曾进入版本库 | `git log --all --name-only \| grep -i archive` | 全历史仅 `.archive/README.md`；**无任何 `phase0_prototype/` 路径** |
| 3 | 是否曾被删除 | `git log --all --diff-filter=D --name-only` | **无任何删除记录** —— 说明它们从未被提交，也就无从丢失 |
| 4 | 本机文件系统 | 全盘 `find / -xdev` 搜 `compliance_agent` / `phase0_prototype` / `run_tests.py` | **零命中** |
| 5 | 同主机另一仓库 | `yan/ai-longxiang-2026-shopee` 全量 tree（30593 条目） | **零命中** |
| 6 | 首次提交时是否已如此 | `git show <首个提交>` | 仓库初始化时只有 `.gitkeep`；归档 README 是第 1 个交付提交引入的，**其"48 个文件"的说法在引入时即不成立** |

### 2.2 结论

- 第一阶段的原型实现（`src/compliance_agent/`：parsers / engine / report，共 13 个文件）、旧测试套件（333 项）、
  旧治理文档（18 份）、旧提示词与上一次运行的输出，**均不存在于任何可访问的存储介质中**。
- 这不是"归档后被误删"，而是**从未入库**。
- 因此 `PROJECT_RULES.md` §3.1 目录树中的 `src/`、`tests/test_plan.md` §9 的"实测基线 333 项通过"、
  `manifest.json` 的 `reference_implementation` 字段，**都指向不存在的资产**。

### 2.3 受影响的下游引用

| 文件 | 位置 | 现状 |
|---|---|---|
| `manifest.json` | `shared_assets.reference_implementation` | 指向不存在的 `src/compliance_agent/`（已标注为缺失） |
| `tests/test_plan.md` | §9「现有基线（实测）」 | 引用不存在的 `tests/run_tests.py` 与 333 项结果（已改为如实说明） |
| `tools/gen_references.py` | 9 处 `.archive/phase0_prototype/...` 引用 | 指向不存在的路径（已标注为不可用） |
| `skills/*/references/*.md` | 若干「相关文档」栏 | 指向不存在的归档路径（已标注为不可用） |

**上述引用均已就地标注，不再伪装成可查阅的资产。**

---

## 3. 原型实现的替代方案

原型代码丢失**不影响**当前框架的推进路径 —— 新框架的模块由任务包驱动独立实现，
不依赖原型：

| 原型能力 | 新框架中的归属 | 任务 |
|---|---|---|
| `ingest.parsers`（多格式解析） | `shopee-br-data-ingestion` | `TASK-INGEST-01` |
| `engine.evaluator`（规则判定） | `shopee-br-listing-audit` / `shopee-br-ip-review` / `shopee-br-duplicate-detection` | `TASK-LISTING-01` / `TASK-IP-01` / `TASK-DUP-01` |
| `engine.duplicates`（重复检测） | `shopee-br-duplicate-detection` | `TASK-DUP-01` |
| `engine.relist`（重发冻结状态机） | `shopee-br-duplicate-detection` | `TASK-DUP-01` |
| `engine.reviewer`（案件流转） | `shopee-br-duplicate-detection` | `TASK-DUP-01` |
| `report.markdown`（报告渲染） | `shopee-br-reporting` | `TASK-REPORT-01` |
| `compile_ac`（Aho-Corasick 词库扫描） | `shopee-br-data-ingestion`（词库 + 扫描器） | `TASK-INGEST-01` |

**新实现的行为参照改为冻结契约本身**：`contracts/risk_action_matrix.json`（判定语义）、
`contracts/audit_result.schema.json`（输出形态）、`contracts/file_ownership.json`（职责边界）。
契约是权威，原型从来只是参考。

---

## 4. 调用方式

### 4.1 存入新内容

需要归档的产物放进本目录，**保留原相对路径**，并在下方 §6 变更记录登记一行：

```bash
mkdir -p .archive/<批次名>/
cp -r <产物目录> .archive/<批次名>/
```

### 4.2 回迁

```bash
cp -r .archive/<批次名>/<路径> <目标路径>
```

回迁后**必须**更新引用方的路径，并检查 `tools/framework_check.py` 是否仍通过。

---

## 5. 保留期限与清理条件

满足**任一**条件时，本目录可正式清理（需用户确认）：

1. 七个 Skill 全部通过集成验收。
2. `docs/SBRCA-P0-004_open_questions.json` 的 14 项裁定全部落地，相关治理文档正式 Approved。
3. 用户显式指示删除。

**在满足上述条件前，本目录只增不删。**

---

## 6. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 2.0.0 | 2026-10-27 | **核实归档内容缺失**：v1.0.0 声称的 48 个文件从未入库（6 项检查全部见 §2.1）。改为如实记录，并给出原型的替代实现路径（§3）。同步修正 `manifest.json`、`tests/test_plan.md`、`tools/gen_references.py`、`skills/*/references/` 中的失效引用标注 |
| 1.0.0 | 2026-10-27 | 建立归档区，声称移入 48 个文件 —— **该声称不成立**，见 §2.1 |
