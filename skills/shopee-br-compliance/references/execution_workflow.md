# 显式执行工作流

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-CO-002` |
| 所属模块 | `shopee-br-compliance`（主 Skill） |
| 版本 | 1.0.0 |
| 状态 | **Draft — 骨架，内容待 TASK-MAIN-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 主 Skill 调用各模块的完整步骤 |
| 相关文档 | `skills/shopee-br-compliance/SKILL.md` §4、`contracts/module_handoff.schema.json` |
| 未决事项 | 平台若将来提供 Skill 自动调用能力，本工作流只替换执行层，判定语义不变 |

---

## 1. 为什么是显式工作流

> **目标平台不保证 Skill 之间存在自动调用能力。**

因此本模块**不得**假设可以"调用"另一个 Skill。它做的是：

1. **读取**目标模块的 `SKILL.md`（文本）
2. **遵循**其中的输入/输出契约
3. 在当前上下文中**按契约执行**该模块的职责
4. 校验产出符合契约
5. 记录交接

平台若将来提供自动调用能力，只需把第 3 步替换为真正的调用，**第 1、2、4、5 步完全不变**。

---

## 2. 工作流步骤

### 步骤 0 — 读取契约

```
读取 contracts/skill_input.schema.json
读取 contracts/audit_result.schema.json
读取 contracts/risk_action_matrix.json
```

### 步骤 1 — 分流

按 `references/routing.md` 的决策表，确定本次需要执行哪些模块。

典型分流：

| 输入特征 | 需要执行的模块 |
|---|---|
| 只有商品标题/详情 | `listing-audit` |
| 含图片 | `listing-audit` + `ip-review` |
| 含多店铺商品集 | `duplicate-detection` |
| 含历史案件 | `duplicate-detection`（重发检查） |
| 含品牌或疑似商标 | `ip-review` |
| 输入是 Excel/CSV/PDF | 先 `data-ingestion` |
| 全部场景 | 最后一律 `reporting` |

### 步骤 2 — 逐模块执行

对每个选中的模块：

```
读取 skills/<module>/SKILL.md
  ↓
提取该模块声明的：
  - 输入契约字段用法
  - 输出契约字段
  - 规则与来源要求
  - 硬约束自检项
  - 失败处理行为
  ↓
按该模块的职责执行
  ↓
产出 AuditResult[]，module = <module-name>
```

**关键**：执行时必须遵守该模块 SKILL.md 里的约束，而不是主 Skill 的偏好。

### 步骤 3 — 校验

每份模块产出都**必须**通过 `contracts/audit_result.schema.json` 校验。

```bash
env -u LD_LIBRARY_PATH python3 tools/validate_json.py \
  --schema contracts/audit_result.schema.json <模块产出路径>
```

校验失败 → 该模块结果视为**无效**，进入步骤 5 的降级处理，**不得**把未校验的结果合入总结果。

### 步骤 4 — 整合

按 `references/integration_rules.md`：

- 确定性动作**只增不减**
- 同一 `product_id` 的多条结果按 `verdict_aggregation` 聚合
- `unevaluated[]` 合并，**不因其它模块通过而清除**
- `rule_refs[]` 合并去重（按 `rule_id`）

### 步骤 5 — 交接记录

每模块执行后产出一份 `ModuleHandoff`（`contracts/module_handoff.schema.json`）：

| 字段 | 填写 |
|---|---|
| `from_module` / `to_module` | 本次执行的模块名 |
| `request_id` | 主 Skill 的 `request_id` |
| `payload_ref` | 该模块产出的文件路径 |
| `assumptions` | 本模块执行中做的假设（**不得为空数组**除非确无） |
| `known_gaps` | 已知的数据缺口（**不得为空数组**除非确无） |
| `unevaluated` | 因数据缺失而未评估的项 |
| `requires_human_review` | 是否需人工复核 |

### 步骤 6 — 报告

调用 `shopee-br-reporting` 的职责（同样走步骤 2–5 的显式流程）产出最终报告。

---

## 3. 降级行为

模块不可用时的处理见 `references/degradation.md`。核心原则：

> **宁可如实报告"未执行"，不可假装"通过"。**

---

## 4. 完整示例

```
用户请求："检查这批商品是否合规" + Excel 附件

步骤 0: 读契约
步骤 1: 分流 → [data-ingestion, listing-audit, ip-review,
              duplicate-detection, reporting]
步骤 2: 逐个读 SKILL.md 并执行
        - data-ingestion: 解析 Excel → 15 个 Product
        - listing-audit:  对 15 个 Product → 若干 AuditResult
        - ...
步骤 3: 校验每份产出
步骤 4: 整合 → 单份总 AuditResult
步骤 5: 5 份 ModuleHandoff
步骤 6: 报告 → Markdown
```

---

## 5. 待 TASK-MAIN-01 确定

- [ ] 分流决策表的完整形态
- [ ] 模块执行顺序的强制约束（若有）
- [ ] 降级时的具体输出形态
- [ ] 是否需要中间产物的落盘目录约定
