| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-CO-003` |
| 所属模块 | ``shopee-br-compliance`` |
| 版本 | 0.1.0 |
| 状态 | **Draft — 骨架，内容待 TASK-MAIN-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 主 Skill 的整合规则 |
| 相关文档 | `contracts/risk_action_matrix.json`、`contracts/module_handoff.schema.json` |
| 未决事项 | 整合的具体实现待确定 |

---

## 1. 整合输入

```
各模块的 AuditResult[]
各模块的 ModuleHandoff[]
```

## 2. 整合步骤

```
1. 校验每份 AuditResult 通过 audit_result.schema.json
   └─ 校验失败 → 该模块结果无效，进入降级，不合入

2. 按 product_id 分组

3. 每组内按 verdict_aggregation 聚合
   └─ 确定性动作只增不减

4. 合并 unevaluated（并集，绝不清除）

5. 合并 rule_refs（按 rule_id 去重）

6. 合并 evidence_refs（按 evidence_id 去重）

7. provenance.notes 记录：执行了哪些模块、跳过了哪些、原因

8. 产出最终 AuditResult
```

## 3. 冲突处理

| 冲突 | 处理 |
|---|---|
| 同商品，两模块给不同风险等级 | 按矩阵聚合，取更严格动作 |
| 同商品，一模块 pass 一模块 flag | flag 胜（确定性动作不降级） |
| 同商品，一模块 not_evaluated 一模块 pass | **两者都保留** —— 该维度未评估 |
| 同规则，来源信息不一致 | 以 `platform_official` 优先，并在 notes 标注 |
| 同商品，两模块给互相矛盾的 block | 保留两条，不合并 —— 由人工裁决 |

## 4. 不得做的事

| 不得 | 为什么 |
|---|---|
| 用"多数模块通过"覆盖单个模块的 block | 稀释确定性结论 |
| 因聚合而删除 `unevaluated` | 掩盖数据缺口 |
| 主 Skill 重新判定来源层级 | 越权 |
| 主 Skill 自行转述平台政策 | 破坏可追溯性 |
| 把未校验的模块结果合入 | 契约失效 |

## 5. 整合后的 `rule_version`

取各模块所用规则集版本的**共同基准**；不一致时在 `provenance.notes` 说明。

## 6. 待 TASK-MAIN-01 确定

- [ ] 整合的具体实现
- [ ] 规则版本不一致的处理细节
