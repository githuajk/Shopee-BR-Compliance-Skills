| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-CO-004` |
| 所属模块 | `shopee-br-compliance` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 模块不可用时的降级行为 |
| 相关文档 | `skills/shopee-br-compliance/src/sbr_compliance/driver.py`、`skills/shopee-br-compliance/src/sbr_compliance/pipeline.py` |
| 未决事项 | 无 |

---

## 1. 核心原则

> **宁可如实报告「未执行」，不可假装「通过」。**

模块不可用时，**绝不能**把它的职责当成「没问题」。

实现里的总纲（`pipeline.py` 模块 docstring）：

> **绝不静默丢弃**：每个模块要么产出结论，要么在 `errors[]` /
> `known_gaps` 里留下痕迹。

## 2. 降级情形与实际行为

| 情形 | 实际行为 | 代码位置 |
|---|---|---|
| 模块 `SKILL.md` 不可读 | 该模块未执行；记 error，`stage="module_invocation"` | `driver.run_module()` |
| 模块 CLI 文件不存在 | 该模块未执行；理由「the module entry point does not exist」 | `driver.run_module()` |
| 模块进程非零退出 | 该模块未执行；理由含 stderr 末行 | `driver.run_module()` |
| 模块产出无 `AuditResult` | 该模块未执行；理由「an empty result set is not evidence of compliance」 | `driver.run_module()` |
| 单条结果不合约 | **该条**进 `rejected[]`，不合入总结果；记 error | `driver.run_module()` |
| 矩阵读不到 | 抛 `MatrixUnavailable` —— **模块停止**，不退化成「无风险」 | `matrix.load_matrix()` |
| 输入数据缺失 | 模块自己记 `unevaluated[]`（H3），动作升级为人工复核 | 各专业模块 |

### 2.1 「空结果集不是合规证据」

```python
if not candidates:
    run.reason = ("the module output contains no AuditResult object; an "
                  "empty result set is not evidence of compliance")
```

模块跑了但没产出任何结论 —— 这**不等于**「没发现问题」。它被当作失败，
该维度记为未执行。

### 2.2 单条不合约 ≠ 整模块作废

契约校验是**逐条**做的：

- 一条结果不合约 → 只废这一条，进 `rejected[]`
- 其它结果照常合入
- `summary.rejected_result_count` 记录被拒的条数

**部分执行是允许的** —— 前提是**如实计数**。

### 2.3 降级动作可见

整合层对上游做的调整（降级、压回）都进 `errors[]`，
`error_id` 前缀 `SBRC-ADJ-`，`severity="warning"`。

**静默调整 = 隐瞒**。

## 3. 输出形态

### 3.1 未执行的模块

写进 `summary.not_executed_modules`：

```json
[
  {"module": "shopee-br-ip-review",
   "reason": "the module exited with status 2: sbr_ip_review_cli.py: error: unrecognized arguments: --skill-input"}
]
```

### 3.2 被契约拒绝的结果

计入 `summary.rejected_result_count`，并在 `provenance.notes` 追加：

```
; 3 upstream result(s) rejected by the contract and excluded
```

交接记录的 `assumptions` 里同样会写明。

### 3.3 交接记录的 `known_gaps`

`contracts/module_handoff.schema.json` 的 `known_gaps` **必填**（数组可为空）。
有缺口时逐条列出，例：

```json
["6 rule evaluation(s) could not be completed because the required input was missing; those dimensions are unassessed, not cleared."]
```

## 4. 错误阶段（`stage`）

`errors[]` 的 `stage` 取值（`errors.py`）：

| `stage` | 含义 |
|---|---|
| `routing` | 分流阶段的问题 |
| `module_invocation` | 模块读说明 / 调 CLI / 产出加载失败 |
| `input_load` | 输入读取失败 |
| `contract_validation` | 契约校验不通过 |
| `integration` | 整合层的调整与冲突 |
| `reporting` | 汇总阶段的问题 |
| `output_write` | 产出落盘失败 |

## 5. 报告中的呈现

降级**必须**在报告的数据缺口节体现。报告由
`shopee-br-reporting` 产出，主 Skill 通过 `--result-file` 把结果喂给它。

**不得**在摘要里把未评估的商品算作「通过」。

## 6. 摘要中的计数

`summary` 里这几项**分开统计**，不混在一起：

| 字段 | 含义 |
|---|---|
| `verdict_counts` | 各 verdict 的**目标**数 |
| `unevaluated_count` | 未评估**条目**数 |
| `unevaluated_target_count` | 受未评估影响的**目标**数 |
| `needs_human_review_count` | 需人工复核的目标数 |
| `missing_evidence_count` | 缺证据的目标数 |
| `rejected_result_count` | 被契约拒绝的上游结果数 |

**未评估的目标不进 `verdict_counts` 的 PASS 里** —— 它们的目标结论
本身就不是 `PASS`（H3：未评估的维度使整条结论升级为 `REVIEW`）。

## 7. 实测基线

```bash
$ env -u LD_LIBRARY_PATH python3 tests/shopee-br-compliance/run_tests.py
```

| 场景 | 观察到的降级 |
|---|---|
| 39 个违规商品、无 `cases[]` | 6 个未评估项、3 条 H3 警告（跨店比对不可行、无案件历史） |
| ip-review 参数套错（故障注入） | `not_executed_modules` 记录该模块，理由含 `unrecognized arguments` |
| 契约拒绝上游结果 | `rejected_result_count` 递增，结论注明「excluded」 |
