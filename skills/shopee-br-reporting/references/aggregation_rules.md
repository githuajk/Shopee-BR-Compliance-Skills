| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-RP-002` |
| 所属模块 | `shopee-br-reporting` |
| 版本 | 1.0.0 |
| 状态 | **Active — 已实现** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 多模块结果的聚合语义 |
| 相关文档 | `contracts/risk_action_matrix.json` 的 `verdict_aggregation`、`contracts/audit_result.schema.json` |
| 实现 | `skills/shopee-br-reporting/src/sbr_reporting/aggregate.py`、`matrix.py` |

---

## 1. 聚合的唯一权威

`contracts/risk_action_matrix.json` → `verdict_aggregation` 字段。

**本模块不定义聚合规则**，只执行矩阵里写明的规则。矩阵读不到或不可解析时
抛 `MatrixUnavailable`，管线记 `fatal` 并**停止本模块** —— 不自造映射。

## 2. 核心不变式：verdict 永远由 action 推导

矩阵的 `actions` 段为每个动作定义了唯一的 verdict：

| action | verdict |
|---|---|
| `allow` | `PASS` |
| `flag_for_review` | `REVIEW` |
| `require_evidence` | `REVIEW` |
| `revise` | `REVISE` |
| `block` | `BLOCK` |
| `freeze_relist` | `BLOCK` |
| `escalate_legal` | `BLOCK` |

因此聚合**只从清洗后的 action 推导 verdict**，**绝不**采用输入自报的 verdict
作为覆盖项。

> **为什么。** 如果允许自报 verdict 覆盖，一条 `internal_risk` 规则只要自报
> `verdict=BLOCK`，就能在动作被 H2 降到 `flag_for_review` 之后仍然产出
> `BLOCK` 结论 —— 硬约束 H2 会被绕过。

输入自报 verdict 与其动作不一致时：

1. 记一条 `warning`（`stage=aggregation`），**如实暴露**不一致；
2. 结论仍以矩阵为准。

## 3. verdict 聚合：取最重

`verdict_aggregation.order` = `PASS < REVISE < REVIEW < BLOCK`。

```
verdict = max(所有清洗后 action 所隐含的 verdict)
```

**不是**取最大风险等级，**不是**取最大声明值。

## 4. action 聚合：保留最细粒度

`verdict_aggregation.rule` = `max_with_action_detail`。

矩阵的 `actions` 段按「笼统 → 具体」排列：

```
allow → flag_for_review → require_evidence → revise → block → freeze_relist → escalate_legal
```

**声明顺序即粒度顺序**：越靠后越具体。因此「保留最细粒度的那一条」=
在同一 verdict 档内取**声明顺序最靠后**的动作。

| 输入 | 输出 |
|---|---|
| `flag_for_review` + `require_evidence` | `verdict=REVIEW`，`action=require_evidence` |
| `require_evidence` + `block` | `verdict=BLOCK`，`action=block` |
| `allow` + `revise` | `verdict=REVISE`，`action=revise` |
| `block` + `escalate_legal` | `verdict=BLOCK`，`action=escalate_legal` |
| `block` + `allow` | `verdict=BLOCK`，`action=block`（不降级） |

**退化保护**：若某档内没有候选动作（例如因未评估而升到 REVIEW 时），取该档
**最不激进**的动作（`flag_for_review`），而不是随便挑一个。

## 5. 风险等级聚合

取最严重的等级（`risk_levels` 的声明顺序：`info < low < medium < high < critical`）。

**风险等级与动作正交** —— 最高风险等级不一定对应最严格动作。两者的允许组合
由矩阵的 `matrix` 段定义。

### 5.1 组合不合法时的替换

若聚合出的 `(risk_level, action)` 不在矩阵允许组合里，替换成一个
**合法且不更宽松**的动作：

1. 只考虑矩阵允许该风险等级的动作；
2. 优先保持原动作的 verdict 档（同档内取最不激进的那个）；
3. 同档无解时降到刚好低一档，取该档最不激进的动作；
4. 更轻的档也没有时回落到 `flag_for_review`（它在每个风险等级都被允许）。

**永不升档** —— 替换函数只可能降低结论的强制性。

矩阵中的典型禁止组合：

| 组合 | 矩阵备注 |
|---|---|
| `info` + `require_evidence` | 信息级风险不需补证 |
| `low` + `block` | 低风险不阻断 |
| `medium` + `allow` | 中风险不直接放行 |
| `critical` + `revise` | 极严重风险不适用「改一改再上」 |

## 6. 清洗：硬约束 H2 的落点

每条输入结果在聚合前先被清洗：

| 情形 | 处理 | 记错 |
|---|---|---|
| 阻断类动作 + 来源层级含 `platform_official` / `law` | 保留 | — |
| 阻断类动作 + 只有 `internal_risk` / `unverified` / `ai_inference` / `technical` | 降为 `flag_for_review` | `error` |
| 阻断类动作 + 完全没有 `source_tier` | 降为 `flag_for_review` | `error` |
| 阻断类动作 + 权威与非权威层级混合 | 保留（存在权威依据） | `warning` |
| 自报 verdict 与动作隐含的 verdict 不一致 | 以矩阵为准 | `warning` |

清洗记录**同时**进入 `errors[]`（`stage=aggregation`），在报告第 2 节可见。

## 7. 确定性结论只增不减

> 硬约束 **H2** 的推论：整批的结论**不得弱于**任一模块的结论。

```
若模块 A 给出 block，整批结论必须包含 block
若模块 A 给出 flag，整批结论不得被另一模块的 pass 覆盖
```

**不允许**用「多数投票」或「取平均」稀释确定性结论。

## 8. `unevaluated` 的合并

```
整批的 unevaluated = 所有模块的 unevaluated 之并
```

> **绝不因其它模块通过而清除。** 某个模块说「这个商品我没评」，整批结果就说
> 「这个商品在这个维度未评估」。

**推论（H3）**：一个目标只要有 `unevaluated` 条目，其 verdict **不得**是
`PASS` —— 聚合会把 verdict 提升到 `REVIEW`，动作取该档最不激进的那个，
并把 `requires_human_review` 置为 `true`。

## 9. `rule_refs` 合并

按 `rule_id` 去重。同一规则被多个模块引用时，保留其 `source` 信息
（`source_tier` / `source_url` 以先出现者为准，其余为空的字段由后出现者补齐）。

**来源不一致时**（同一 `rule_id` 的 `source_tier` 或 `source_url` 不同），
**如实记录冲突**，不擅自取舍：

```
rule SBR-LV-001: source_tier differs between modules ('platform_official' vs 'internal_risk')
```

冲突出现在报告第 2 节与汇总的 `conflicts[]`。

## 10. `evidence_refs` 合并

按 `evidence_id` 去重。同一证据被多个模块引用时，**`provided=true` 优先**
（已有凭证引用胜过「缺失」）。

**只存引用**（硬约束 H5）：`artifact_ref` 原样透传，本模块**从不**读取、
复制或摘要化被引用的文件内容。

## 11. `errors` 合并

上游每一条 `error` 都保留（含原始 `error_id` 以便回溯到来源模块）。
本模块自身的清洗记录也追加进来。

## 12. 置信度聚合：取最弱

```
confidence = min(所有清洗后结果的 confidence)
```

`signal < likely < confirmed`。**取最弱**而不是最强 —— 否则一条
`signal` 的 IP 结论会被另一模块的 `confirmed` 掩盖，违反硬约束 H1。

## 13. `requires_human_review` 的判定

满足**任一**即为 `true`：

| 条件 | 依据 |
|---|---|
| 矩阵声明该动作恒需人工复核 | `actions[].always_human_review` |
| 存在 `unevaluated` 条目 | H3 |
| 置信度为 `signal` | H1 / `PROJECT_RULES` §10 |
| 任一上游结果要求人工复核 | 上游结论 |
| `errors[]` 中存在 `error` / `fatal` | `PROJECT_RULES` §11 |

## 14. 常见聚合错误

| 错误 | 正确做法 |
|---|---|
| 只取「最严重的那一条」 | 保留全部记录，聚合动作 |
| 用通过覆盖未评估 | 未评估必须保留，且不得判 PASS |
| 把不同商品的发现混在一起 | 按 `target_ref` 聚合 |
| 动作被风险等级覆盖 | 查矩阵，不自行推断 |
| 用自报 verdict 覆盖矩阵推导 | 以矩阵为准，不一致只记 warning |
| 把 `pass` / `flag` 当 verdict | 契约枚举只有 PASS/REVISE/REVIEW/BLOCK |

## 15. 跨模块规则冲突的处理

本模块**不裁定**冲突。三种情形：

| 情形 | 处理 |
|---|---|
| 同一 `rule_id` 的来源层级不同 | 记录冲突，如实呈现，交由集成 Agent 裁定 |
| 同一 `rule_id` 的严重度不同 | 取最严重（`max_risk`），来源层级仍按 §9 处理 |
| 两条不同 `rule_id` 指向同一事实 | **不合并** —— 两条都保留，各自可追溯 |

## 16. 整批结论

整批结论是逐目标结论的再聚合：

- `verdict` —— 逐目标 verdict 取最重
- `action` —— 该档内逐目标 action 取最细粒度
- `risk_level` —— 取最严重
- `unevaluated` —— 全部输入结果的并集
- `confidence` —— 取最弱

整批结论的 `target_ref` 为 `batch-<request_id>`，便于与逐目标结论区分。
