| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-CO-002` |
| 所属模块 | `shopee-br-compliance`（主 Skill） |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 主 Skill 调用各模块的完整步骤 |
| 相关文档 | `skills/shopee-br-compliance/SKILL.md` §4、`contracts/module_handoff.schema.json` |
| 未决事项 | 平台若将来提供 Skill 自动调用能力，本工作流只替换执行层，判定语义不变 |

---

## 1. 为什么是显式工作流

> **目标平台不保证 Skill 之间存在自动调用能力。**

因此本模块**不得**假设可以「调用」另一个 Skill。它做的是：

1. **读取**目标模块的 `SKILL.md`（文本）
2. **遵循**其中的输入/输出契约
3. 在当前上下文中**按契约执行**该模块的职责
4. 校验产出符合契约
5. 记录交接

平台若将来提供自动调用能力，只需把第 3 步替换为真正的调用，**第 1、2、4、5 步完全不变**。

实现位置：`skills/shopee-br-compliance/src/sbr_compliance/driver.py`
的 `run_module()`。

---

## 2. 工作流步骤（实现级别）

### 步骤 0 — 读取契约

```
读取 contracts/skill_input.schema.json
读取 contracts/audit_result.schema.json
读取 contracts/risk_action_matrix.json
读取 contracts/module_handoff.schema.json
```

契约读不到 → **模块停止并显式失败**（`matrix.MatrixUnavailable`），
绝不退化成「没有风险」。

### 步骤 1 — 分流

按 `references/routing.md` 的判据确定本次要执行哪些模块。
实现：`routing.decide()`。

### 步骤 2 — 显式读取模块说明并驱动

```
读取 skills/<module>/SKILL.md              ← driver.read_module_skill_md()
  ↓
提取该模块声明的：输入契约字段用法 / 输出契约字段 /
                规则与来源要求 / 硬约束自检项 / 失败处理行为
  ↓
按该模块自己的入口执行
  ↓
产出 AuditResult[]
```

实际执行轨迹示例（`ModuleRun.trail`）：

```
read skills/shopee-br-listing-audit/SKILL.md (425de1b987dbc2d3)
ran sbr_listing_audit_cli.py (exit 0)
```

各模块的说明文件在仓库里的位置：

| 模块 | 说明文件 |
|---|---|
| `shopee-br-data-ingestion` | `skills/shopee-br-data-ingestion/SKILL.md` |
| `shopee-br-listing-audit` | `skills/shopee-br-listing-audit/SKILL.md` |
| `shopee-br-ip-review` | `skills/shopee-br-ip-review/SKILL.md` |
| `shopee-br-duplicate-detection` | `skills/shopee-br-duplicate-detection/SKILL.md` |
| `shopee-br-reporting` | `skills/shopee-br-reporting/SKILL.md` |

**关键**：执行时必须遵守该模块 SKILL.md 里的约束，而不是主 Skill 的偏好。

每步都记进 `ModuleRun.trail`（可审计的执行轨迹）：

```
read skills/shopee-br-listing-audit/SKILL.md (425de1b987dbc2d3)
ran sbr_listing_audit_cli.py (exit 0)
```

`SKILL.md` 的 SHA-256 摘要（`driver.skill_md_digest()`）一并记录 ——
复核者能确认执行时读到的说明文件是哪个版本。

### 步骤 3 — 各模块的 CLI 参数约定**不统一**（实测）

这是最容易出错的一步。四个模块的 argv 约定各不相同：

| 模块 | 实际参数 |
|---|---|
| `data-ingestion` | `--request-id` `--out-dir` + **位置参数**（输入文件） |
| `listing-audit` | `--skill-input`（必需）`--request-id` `--out-dir` |
| `duplicate-detection` | `--skill-input`（必需）`--out-dir`（**没有** `--request-id`） |
| `ip-review` | `--request-id` `--out-dir` + **位置参数**（**没有** `--skill-input`） |
| `reporting` | `--request-id` `--out-dir` `--result-file` `--skill-input` |

套错参数 → argparse 直接退出 → **该维度静默缺失**。

实测证据（修复前）：`listing-audit` 39 条 / `ip-review` **0 条** /
`duplicate` **0 条** / `reporting` 40 条 —— 汇总结果少一大块，
却看不出缺了。

> `tests/shopee-br-compliance/run_tests.py` 的 L2 段逐个核对这五个
> `--help`，防止再次套错。

### 步骤 4 — 校验

每份模块产出都**必须**通过 `contracts/audit_result.schema.json` 校验。
实现：`skills/shopee-br-compliance/src/sbr_compliance/contracts.py` 的
`ContractValidator`（最小 JSON Schema 子集，纯标准库）。

校验失败 → 该条结果进 `rejected[]`，**不合入总结果**，并记 error。

> 契约校验用的是**同一份** `contracts/*.schema.json`，不是复制品。

### 步骤 5 — 整合

按 `references/integration_rules.md`：

- 硬约束在整合层**再次强制**（H1 / H2），不盲信上游
- 同一 `target_ref` 的多条结果按 `verdict_aggregation` 聚合
- `unevaluated[]` 合并，**不因其它模块通过而清除**
- `rule_refs[]` 合并去重（按 `rule_id`），来源冲突**如实记录**

### 步骤 6 — 交接记录

产出一份 `ModuleHandoff`（`contracts/module_handoff.schema.json`）。
**必需字段**（该 Schema 是 `additionalProperties: false`）：

| 字段 | 填写 |
|---|---|
| `handoff_id` | `HO-<模块前缀>-<request_id>` |
| `from_module` / `to_module` | 本次执行的模块名 / `shopee-br-compliance` |
| `request_id` | 主 Skill 的 `request_id` |
| `contract_version` | `1.0.0` |
| `produced_at` | ISO 8601 UTC |
| `assumptions` | 本次执行做的假设（**不得为空数组**除非确无） |
| `known_gaps` | 已知的数据缺口（**不得为空数组**除非确无） |
| `unevaluated` | 因数据缺失而未评估的项 |
| `requires_human_review` | 是否需人工复核 |
| `payload_ref` | 该模块产出的文件路径 + 内联结果 |

> **不得**自造 `summary` / `notes` 字段 —— Schema 是
> `additionalProperties: false`，多写字段校验就不过。

### 步骤 7 — 报告

调用 `shopee-br-reporting`（同样走步骤 2–6 的显式流程）产出最终报告。

---

## 3. 降级行为

模块不可用时的处理见 `references/degradation.md`。核心原则：

> **宁可如实报告「未执行」，不可假装「通过」。**

---

## 4. 完整示例（实测）

```bash
$ env -u LD_LIBRARY_PATH python3 skills/shopee-br-compliance/src/sbr_compliance_cli.py \
    --request-id REQ-G4-TEST-002 --out-dir /tmp/out \
    --product-file tests/fixtures/violation_products.json

module:   shopee-br-compliance/1.0.0  contract: 1.0.0
request:  REQ-G4-TEST-002
route:    shopee-br-listing-audit → shopee-br-ip-review →
          shopee-br-duplicate-detection → shopee-br-reporting
targets:  39
results:  117 upstream result(s)
verdict:  BLOCK  action: escalate_legal  risk_level: critical
gaps:     6 unevaluated, 3 error(s)
outputs:  /tmp/out
```

**117 = 39 × 3 + 40** —— 三个专业维度各 39 条 + 汇总 40 条。

产出的目录结构：

```
out/
├── audit_result.json      单条契约结果
├── audit_results.json     全部结果
├── audit_summary.json     批次汇总（含缺口统计）
├── audit_report.md        人读报告
├── module_handoff.json    交接记录
├── module_runs.json       各模块执行轨迹
├── routing_plan.json      分流决定
├── content_audit/         listing-audit 的产出
├── ip/                    ip-review 的产出
├── duplicate/             duplicate-detection 的产出
└── reporting/             reporting 的产出
```

---

## 5. 执行顺序的强制约束

| 约束 | 原因 |
|---|---|
| `ingestion` 最先 | 专业模块需要规范化的 `products[]` |
| `reporting` 最后 | 汇总需要全部上游结果 |
| 三个专业维度顺序固定 | `content_audit → ip → duplicate`（`registry.STAGE_ORDER`） |

顺序由 `registry.STAGE_ORDER` 定义，分流结果按它重排 —— **无论
分流函数以什么顺序返回**。

## 6. 中间产物的落盘目录约定

**有** —— 每个模块的产出落在自己的子目录，目录名是**阶段名**
（`stage`，不是模块名也不是 role）：

```python
stage_dir = os.path.join(work_root, stage)
```

| 阶段 | 目录 |
|---|---|
| `ingestion` | `ingestion/` |
| `content_audit` | `content_audit/` |
| `ip` | `ip/` |
| `duplicate` | `duplicate/` |
| `reporting` | `reporting/` |

这样一次批次的所有中间产物都在 `--out-dir` 下，可追溯、可复查。

> 未指定 `--out-dir` 时，中间产物落在仓库根的
> `.sbr-compliance-work/`（临时工作区），**不写**进正式产出目录。
