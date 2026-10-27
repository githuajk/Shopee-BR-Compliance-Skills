# 判定语义规范

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-LA-001` |
| 所属模块 | `shopee-br-listing-audit` |
| 版本 | 1.0.0 |
| 状态 | **Draft — 骨架，内容待 TASK-LISTING-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 本模块所有判定结论的语义定义 |
| 相关文档 | `contracts/risk_action_matrix.json`、`PROJECT_RULES.md` §5 |
| 未决事项 | 判定阈值的具体数值待模块 Agent 依据规则层确定 |

---

## 1. 四态语义（不可协商）

模块对每条规则的评估**只有四种合法结论**，没有第五种：

| 规则级结论 | 契约 `verdict` | 契约 `action` | 含义 | 何时产生 |
|---|---|---|---|---|
| 通过 | `PASS` | `allow` | 规则的全部适用条件均已评估且均不成立 | 所有 `requires_input` 字段齐备，且不命中任何 `trigger_conditions` |
| 命中 | 由 `risk_action_matrix` 查表决定（`REVIEW` / `REVISE` / `BLOCK`） | 同左 | 规则命中 | 命中 `trigger_conditions` |
| 未评估 | **不产生 result** | — | **无法评估**，不是"通过" | 规则的 `requires_input` 声明的字段在输入中缺失 |

> ⚠️ **三个层次必须分清** —— 混淆它们是本项目最容易犯的错：
>
> | 层次 | 取值 | 存在哪里 |
> |---|---|---|
> | 规则级结论 | 通过 / 命中 / 未评估 | 只在本节与 `unevaluated[]` 的语义中出现 |
> | 契约 `verdict` | `PASS` `REVISE` `REVIEW` `BLOCK` | `AuditResult.verdict` |
> | 契约 `action` | `allow` `flag_for_review` `require_evidence` `revise` `block` `freeze_relist` `escalate_legal` | `AuditResult.action` |
>
> **`pass` / `flag` / `not_evaluated` 不是契约取值**，不能写进 `AuditResult.verdict`。
> 契约只有 4 个 `verdict` 值和 7 个 `action` 值 —— 见
> `contracts/audit_result.schema.json`。
>
> **最容易出错的地方**：未评估 ≠ 通过。
>
> 当输入缺少 `brand` 字段，而某条规则的触发条件依赖 `brand` 时，**不能**因为"没看到品牌"就判定通过。
> 必须把该规则记入 `unevaluated[]` 并产出 `stage: "rule_evaluation"` 的 warning 错误，
> **且不产生**该规则的 `AuditResult`。这直接对应硬约束 **H3**。

---

## 2. `requires_input` 机制

每条规则声明它依赖哪些输入字段：

```json
{
  "rule_id": "SBR-LV-001",
  "requires_input": ["title", "description", "images"],
  "trigger_conditions": [ ... ]
}
```

判定算法：

```
for rule in applicable_rules:
    missing = [f for f in rule.requires_input if f not in provided_fields or is_empty(provided_fields[f])]
    if missing:
        → 不产生 AuditResult
        → unevaluated.append({rule_id, reason, missing_fields})
        → errors.append({stage: "rule_evaluation", severity: "warning"})
        → 跳过 trigger 匹配
    else:
        if any(trigger matches):
            → risk_level = rule.severity
            → action = risk_action_matrix 查表(rule.severity, rule.decision)
            → verdict = 由 action 映射（allow→PASS / flag_for_review|require_evidence→REVIEW
                       / revise→REVISE / block|freeze_relist|escalate_legal→BLOCK）
        else:
            → 不产生命中 result（该规则未命中）
```

**字段"存在但为空"等同于缺失。** 空字符串、空数组、null、全是空白字符 —— 都算缺失。

---

## 3. 结论与动作的映射

由 `contracts/risk_action_matrix.json` 决定，模块**不得**自行决定动作：

```
rule.severity (critical/high/medium/low/info)
        │
        ▼
风险等级 risk_level  ← 规则定义
        │
        ▼
动作 action         ← 矩阵查表（35 个组合）
        │
        ▼
requires_human_review ← 矩阵 + 硬约束
```

硬约束 **H2**：产生 `block` / `freeze_relist` / `escalate_legal` 的规则，`source.tier` 必须是 `platform_official` 或 `law`，且 `status` 必须是 `active`。

---

## 4. 确定性 vs 启发式

| 类型 | 判定方式 | 允许的最高 `action` | 例 |
|---|---|---|---|
| 确定性 | 词库精确匹配 / 字段比对 / 正则 | 规则声明的 `decision`（可到 `block`） | 禁售词命中 |
| 启发式 | 相似度 / 语义推断 | 只能 `flag_for_review` | 疑似盗图、疑似夸大 |

> 启发式判定**永远不能**单独产生 `block` / `freeze_relist` / `escalate_legal`（硬约束 **H2**）。
> 若启发式信号达到高置信度，输出 `action: flag_for_review` + `requires_human_review=true`，
> 对应 `verdict: REVIEW`，并说明置信度依据。

---

## 5. 来源层级的动作限制

| `source.tier` | 允许的最高动作 | 说明 |
|---|---|---|
| `platform_official` | `block` | 平台明文规则 |
| `law` | `block` | 法律规定（禁售类） |
| `technical` | `flag_for_review` | 技术调研结论 —— 不可阻断 |
| `internal_risk` | `flag_for_review` | 内部风控建议 —— 不可阻断 |
| `unverified` | `flag_for_review` | 来源未核实 —— 不可阻断 |
| `ai_inference` | `flag_for_review` | AI 推断 —— 不可阻断 |

---

## 6. 边界案例的默认处理

| 情形 | 正确行为 | 错误行为 |
|---|---|---|
| 字段缺失 | 不产生 result + 记入 `unevaluated[]` + warning 错误 | 判 `PASS`（当作通过） |
| 字段存在但为空 | 同上（空 = 缺失） | 判 `PASS`（当作通过） |
| 同一商品命中多条规则 | 全部输出，按矩阵聚合 | 只输出第一条 |
| 一条规则命中但证据不足 | `action: require_evidence` + `requires_human_review`（`verdict: REVIEW`） | 判 `PASS`（当作通过） |
| 规则 `status` 非 `active` | 不产出结论 | 照常判定 |
| 描述为多语言/混合语种 | 保留原文，不做翻译改写 | 自行改写文本 |
| 商品属于多个类目 | 按 `category_declared_by` 优先 | 自行选择 |

---

## 7. 误判控制

**每个规则必须有正例与反例。** 反例的作用是证明规则不会误伤正常商品。

典型反例：

| 规则 | 正常商品（不得命中） | 为什么不应命中 |
|---|---|---|
| 禁售词匹配 | "Kit 5 peças, tira-glacês" | 单词 `tira` 出现在普通配件名中 |
| 医疗功效词 | "Suporte para）(it) Polegar" | 无医疗声明 |
| 兼容性描述 | "Compatível com modelo X" | 描述兼容性 ≠ 商标侵权 |
| 夸大词 | "Melhor do mercado" | 主观宣传，非平台禁止的绝对化用语 |
| 品牌字段 | `brand` 为空 | 空 = 未评估，不是"无品牌违规" |

**已知反例来源**：`data/samples/test_cases.json`（合成边界案例，8 场景，含 TC-05 兼容性描述反例、TC-08 正常商品反例）。

---

## 8. 判定的权威依据

本模块的判定语义以**冻结契约**为权威依据，不依赖任何原型实现：

| 语义 | 权威来源 |
|---|---|
| 风险等级 × 处理动作的允许组合 | `contracts/risk_action_matrix.json` → `matrix` |
| 结论聚合顺序与粒度保留 | `contracts/risk_action_matrix.json` → `verdict_aggregation` |
| 输出字段与枚举 | `contracts/audit_result.schema.json` |
| 四态错误语义（missing / unknown / not_applicable / pending_verification） | `PROJECT_RULES.md` §11.1 |
| 硬约束 H1–H6 | `PROJECT_RULES.md` §6.1、`contracts/risk_action_matrix.json` → `hard_constraints` |

关键一致点：

1. **`requires_input` 的判定逻辑**（空值 = 缺失，不是"合规"）。
2. 规则未评估时**不产生 finding**，但**产生 `unevaluated` 记录**（H3）。
3. 结论按 `verdict_aggregation` 聚合，而非简单取最大值。

> 早期版本此处引用第一阶段原型的 `evaluator.py` 作为行为对照。
> 该原型**已于 2026-10-27 归档入库**于 `.archive/phase0_prototype/`
> （结论变更见 `.archive/README.md` §2.1），但不参与活跃校验，
> 因此改为以上述冻结契约为唯一权威依据。

---

## 9. 待 TASK-LISTING-01 确定

- [ ] 各规则的具体 `requires_input` 字段集
- [ ] 词库匹配的规范化规则（大小写、重音符号、词边界）
- [ ] 启发式信号的置信度阈值
- [ ] 类目歧义的 override 表
