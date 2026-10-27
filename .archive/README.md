# .archive/ — 归档区（Phase 0/1 原型实现）

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-ARCH-001` |
| 版本 | 3.0.0 |
| 状态 | **Active — 已包含 Phase 0/1 原型实现（48 个文件）** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 第一阶段（Phase 0/1）产物的临时存放位 |
| 相关文档 | `PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、`manifest.json` |
| 未决事项 | 无 —— 归档内容已入库，校验已修正 |

---

## 1. 用途

本目录是临时保留区。内容**不删除**，仅移出活跃工作区，避免与新的 Skills 集合框架产生版本冲突与阅读干扰。

---

## 2. 当前状态：归档内容已入库（2026-10-27 修正）

> **本节记录的是核实结果，不是计划。**

v2.0.0 曾记录"48 个文件从未存在于版本库中"，依据是当时的 6 项检查（`find` 结果仅 README.md、`git log` 无路径、无删除记录等）。
**该结论在当时成立，但在同日稍后被推翻** —— 原型实现文件重新出现在工作区并已提交入库。

### 2.1 核实过程与证据（v2.0.0 → v3.0.0 的结论变更）

| # | 检查 | 方法 | 结果 |
|---|---|---|---|
| 1 | 归档目录实际内容 | `find .archive -type f` | **48 个文件**（docs 18 / src 13 / tests 1 / prompts 1 / out 2 / 其它 13） |
| 2 | 是否进入版本库 | `git log --all --name-only \| grep -i archive` | **已入库**，`phase0_prototype/` 路径全部在版本库中 |
| 3 | 文件时间戳分布 | `find -printf %TH:%TM` | 2026-10-27 10:01 – 11:31 陆续生成 |
| 4 | 归档内容完整性 | 与 `_FILELIST_BEFORE.txt` 比对 | 文件清单一致 |

### 2.2 结论

- 第一阶段的原型实现（`src/compliance_agent/`：parsers / engine / report，13 个文件）、旧测试套件（`tests/run_tests.py`）、旧治理文档（18 份）、旧提示词与上一次运行的输出，**现已全部入库**。
- 原型代码**不参与活跃框架的路径引用校验**（见 §2.3），但作为历史参照完整保留。

### 2.3 归档区不参与活跃路径校验（v3.0.0 新增）

归档内的文档使用**归档当时的相对路径约定**（例如 `docs/ARCHITECTURE.md`、`engine/evaluator.py`），
相对于仓库根解析会全部落空，产生大量假阳性悬空引用。

`tools/framework_check.py` §10 的文档扫描已排除 `.archive/` 目录：

```python
dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", ".archive")]
```

活跃区（`docs/`、`skills/`、`tasks/`、`tests/`、`contracts/`、`tools/`）的路径引用校验**不受影响，仍全部生效**。

### 2.4 受影响的下游引用

| 文件 | 位置 | 现状 |
|---|---|---|
| `manifest.json` | `shared_assets.reference_implementation` | 指向 `src/compliance_agent/`（归档路径已注明） |
| `tests/test_plan.md` | §9「现有基线（实测）」 | 说明 333 项基线来自归档原型 |
| `tools/gen_references.py` | 9 处 `.archive/phase0_prototype/...` 引用 | 指向归档内路径（已存在，可用） |

---

## 3. 原型实现的替代方案

原型代码**不影响**当前框架的推进路径 —— 新框架的模块由任务包驱动独立实现，
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
契约是权威，原型只是参考。

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
| 3.0.0 | 2026-10-27 | **归档内容已入库**：Phase 0/1 原型 48 个文件已提交入库，v2.0.0 的"从未入库"结论不再成立（§2.1 四项检查）。`tools/framework_check.py` §10 文档扫描排除 `.archive/`，消除归档相对路径约定导致的假阳性悬空引用（§2.3） |
| 2.0.0 | 2026-10-27 | 核实归档内容缺失：v1.0.0 声称的 48 个文件当时未入库（6 项检查见 §2.1）。改为如实记录，并给出原型的替代实现路径（§3） |
| 1.0.0 | 2026-10-27 | 建立归档区，声称移入 48 个文件 —— **该声称当时不成立**，见 v2.0.0 §2.1 |
