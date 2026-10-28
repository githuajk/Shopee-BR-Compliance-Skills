| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-CO-003` |
| 所属模块 | `shopee-br-compliance`（主 Skill） |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 多个模块结果的整合、聚合与冲突处理 |
| 相关文档 | `skills/shopee-br-compliance/src/sbr_compliance/integration.py`、`contracts/risk_action_matrix.json` |
| 未决事项 | 无 |

---

## 1. 整合层的职责边界

| 整合层**做** | 整合层**不做** |
|---|---|
| 按契约矩阵清洗上游结果 | 不重新判定业务规则 |
| 聚合同一目标的多条结果 | 不替模块决定「有没有问题」 |
| 合并 `rule_refs` / `evidence_refs` / `unevaluated` | 不擅自取舍来源层级（冲突如实记录） |
| **再次强制**硬约束 H1 / H2 | 不静默丢弃上游的降级动作 |

实现：`skills/shopee-br-compliance/src/sbr_compliance/integration.py`

---

## 2. 清洗（sanitize）—— 每条上游结果先过一遍

`integrate.sanitize(record, matrix, log)`：

### 2.1 H2：阻断类动作必须有权威来源

```python
if matrix.is_deterministic(action):        # block / freeze_relist / escalate_legal
    if not tiers:
        → 降级为 flag_for_review，理由「该结果没有引用任何带来源层级的规则，
           H2 无法确认权威依据」
    elif not authoritative:
        → 降级为 flag_for_review，理由「引用的来源层级 {…} 不是权威层级
           （H2 只允许 platform_official / law）」
```

「至少有一个权威来源，但也有非权威来源」→ **保留原动作**，但**记一条
说明**（不是静默放过）。

**降级原因必须出现在结果里** —— `sanitize` 把它写进 `errors[]`
（`severity: warning`，`error_id` 前缀 `SBRC-ADJ-`）。

### 2.2 H1：IP 结论恒为 signal

```python
if item.module == "shopee-br-ip-review" or _has_ip_rule(item):
    if confidence != "signal":       → 压回 "signal"，记录原因
    if requires_human_review != True → 置为 True，记录原因
```

**为什么整合层还要再强制一次**：上游模块自己会强制 H1，但主 Skill 是
**最后一道关口**。若某个上游模块（或将来新增的模块）误报了
`confirmed`，汇总层不得把它原样传出去。

判据是**规则 ID 前缀** `SBR-IP-*` —— 不依赖 `module` 字段，因此别的
模块引用 IP 规则时同样受约束。

### 2.3 矩阵组合合法性

`(risk_level, action)` 组合不被矩阵允许 → 换成合法且**不更宽松**的动作，
记 warning。

### 2.4 verdict 一致性

上游自报的 `verdict` 与其 `action` 在矩阵里推出的 verdict 不一致 →
**记 warning，以矩阵推导的为准**。

> 上游自报 `verdict=BLOCK` 但 action 不支持它 —— 这正是 `shopee-br-reporting`
> 发现的绕过洞（内部来源规则自报 BLOCK 就能跳过 H2）。整合层不采信自报值。

---

## 3. 聚合（aggregate_target）

同一 `target_ref` 上的多条上游结果 → 一条 `AuditResult`。

### 3.1 verdict：由**清洗后**的 action 推导

```python
bands = [_band(matrix, s.action) for s in sanitized]
verdict = matrix.max_verdict(bands)
```

**先清洗再聚合** —— 否则被降级的结果仍会用原 action 参与投票。

### 3.2 action：保留最细粒度的那一条

```python
candidates = [s.action for s in sanitized if _band(matrix, s.action) == verdict]
action = matrix.most_specific(candidates) or _band_default(matrix, verdict)
```

**不是取最大值，也不是退化** —— 在达成该 verdict 的动作里，选**粒度最细**
的那一条。粒度序取自 `contracts/risk_action_matrix.json` 的 `actions`
段声明顺序（笼统 → 具体）。

### 3.3 risk_level：取最严重

`matrix.max_risk([...])`

### 3.4 H3：未评估项不得判通过

```python
unevaluated = _merge_unevaluated(records)
if unevaluated and verdict == "PASS":
    verdict = "REVIEW"
    action = _band_default(matrix, "REVIEW")
```

**这条最关键**：某个维度因缺输入无法评估时，即使其它维度都通过，
整条结论**不得**是 `PASS`。缺数据 ≠ 没问题。

### 3.5 confidence：取最弱

```python
confidence = min((s.confidence for s in sanitized),
                 key=lambda c: _CONFIDENCE_RANK.get(c, 1))
```

序：`signal` < `likely` < `confirmed`。IP 结论不会因合并而升格。

### 3.6 需人工复核的判定

```python
requires_human_review = (
    matrix.always_human_review(action)     # 矩阵声明该动作恒需复核
    or unevaluated                            # 有未评估维度
    or confidence == "signal"                 # 最弱置信度是筛查信号
    or any(s.requires_human_review ...)      # 任一上游要求复核
    or any(e.severity in ("error","fatal"))   # 有错误
)
```

**五条任一成立即需复核** —— 不做「全部不成立才复核」的判断。

---

## 4. 合并规则

| 字段 | 规则 |
|---|---|
| `rule_refs` | 按 `rule_id` 去重合并；**同一规则的来源信息不一致时如实记录冲突**，不擅自取舍 |
| `evidence_refs` | 合并去重；只存路径，不存内容（硬约束 H5） |
| `unevaluated` | 合并；**不因其它模块通过而清除** |
| `errors` | 合并；上游的 error 与整合层自己的调整说明都保留 |

### 4.1 冲突记录

`_merge_rule_refs()` 返回 `(refs, conflicts)` —— 冲突进 `summary.conflicts`，
**主 Skill 不得替模块重新判定来源层级**。

---

## 5. 调整必须可见

整合层对上游做的每一次调整（降级、压回、替换）都写进结果的 `errors[]`：

```json
{
  "error_id": "SBRC-ADJ-xxxxxxxxxxxx",
  "stage": "integrate",
  "severity": "warning",
  "message": "action 'block' was rejected: the cited rule tier(s) internal_risk are not authoritative (H2 allows only platform_official / law); downgraded to 'flag_for_review'",
  "context": {"result_id": "...", "module": "...", "target_ref": "..."}
}
```

**静默调整 = 隐瞒**。复核者必须能看到「这个动作被改过，为什么」。

---

## 6. 批次级汇总

`summary` 的关键字段：

| 字段 | 含义 |
|---|---|
| `batch_verdict` / `batch_action` / `batch_risk_level` | 整批结论 |
| `verdict_counts` | 各 verdict 的目标数 |
| `needs_human_review_count` | 需人工复核的目标数 |
| `unevaluated_count` / `unevaluated_target_count` | 未评估项数 / 受影响目标数 |
| `missing_evidence_count` | 缺证据的目标数 |
| `deterministic_count` / `human_only_count` | 按动作可执行方分类 |
| `rejected_result_count` | 被契约校验拒绝的上游结果数 |
| `conflicts` | 合并冲突 |
| `executed_modules` / `not_executed_modules` | 执行与跳过的模块 |
| `routing` | 分流决定 |

批次级结论同样遵守 H3：整批有未评估项时，批次 verdict **不得**是 `PASS`。
