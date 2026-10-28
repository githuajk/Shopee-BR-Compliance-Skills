# contracts/ — 公共契约索引

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-CON-000` |
| 版本 | 1.0.1 |
| 状态 | **Frozen — 已冻结** |
| 冻结日期 | 2026-10-27 |
| 适用范围 | 全部模块的输入输出契约 |
| 相关文档 | `PROJECT_RULES.md` §4、`AGENT_COLLABORATION.md` |

---

## 1. 契约清单

| 文件 | 契约 | 谁读它 |
|---|---|---|
| `skill_input.schema.json` | **统一输入格式** | 全部模块 |
| `audit_result.schema.json` | **统一输出格式** | 全部模块 + 集成 |
| `rule_envelope.schema.json` | 规则外层格式 | 引用规则的模块 + 集成 |
| `evidence_reference.schema.json` | 证据引用格式 | 全部模块 + 集成 |
| `risk_action_matrix.schema.json` | 风险×动作矩阵的 Schema | 集成 |
| `risk_action_matrix.json` | **风险×动作矩阵实例**（含硬约束 H1–H6） | 全部模块 + 集成 |
| `module_handoff.schema.json` | 模块交接格式 | 集成 + 主 Skill |
| `file_ownership.json` | **文件所有权登记**（唯一权威来源） | 全部模块 + 集成 |
| `lexicon_rule_map.json` | **词组 → 规则映射** | listing-audit + ip-review + 集成 |

---

## 1.1 文件所有权

`file_ownership.json` 是**路径所有权的唯一权威来源**。它定义：

| 字段 | 含义 |
|---|---|
| `modules.<name>.owns` | 该角色可写的路径（白名单） |
| `modules.<name>.reads` | 该角色可读的路径 |
| `modules.<name>.rule_prefixes` | 该角色拥有的规则前缀 |
| `global_readonly` | 对所有角色只读的路径 |
| `shared_assets` | 共享只读资产（工具、Schema、样例） |
| `reserved_paths` | 总控/集成保留路径（`integrator` 豁免） |

**一致性要求**：

- `skills/<module>/SKILL.md` 的「文件所有权」章节 —— 必须与本登记一致
- `tasks/<TASK-ID>.md` 的 §2.1 白名单 —— 必须与本登记一致
- `tasks/task_registry.json` 的 `allowed_paths` —— 供机器消费，须一致

三者由 `tools/task_pack_check.py` 机械校验（368 项断言）。

> **模块 Agent 不得修改本文件。** 需要变更时提交契约变更建议。

---

## 2. 契约版本

当前：**1.0.1**（2026-10-28：`evidence_reference.schema.json` 的 `evidence_type` 示例集并入 14 个实际使用类型，解决集成验收 C6；澄清语义级变更，模块无需改动）

| 变更类型 | 版本号变化 | 处理 |
|---|---|---|
| 新增可选字段 | MINOR（1.1.0） | 集成 Agent 统一修改；模块不需改动 |
| 新增必填字段 | MAJOR（2.0.0） | 需先做影响分析；所有模块同步升级 |
| 修改枚举取值 | MAJOR（2.0.0） | 同上 |
| 澄清语义（不改结构） | PATCH（1.0.1） | 集成 Agent 修改，模块读文档即可 |

**模块必须声明它依赖的契约版本。** 契约升级后，未声明兼容的模块由集成 Agent 判定是否需重新验证。

---

## 3. 硬约束摘要（完整定义见 `risk_action_matrix.json`）

| ID | 约束 |
|---|---|
| **H1** | IP 类结论恒为 `signal` + 强制人工复核 |
| **H2** | `block`/`freeze_relist`/`escalate_legal` 只能来自 `platform_official`/`law` 的 `active` 规则；AI 与内部建议最高只能 `flag_for_review` |
| **H3** | 输入缺失 → 该规则不评估 + 必须上报 `unevaluated`；不得当作通过 |
| **H4** | `source.excerpt` 逐字可核验；不通过则规则不得 `active` |
| **H5** | `artifact_ref` 只存引用，不存凭证内容 |
| **H6** | `freeze_relist` / `escalate_legal` 为 `human_only` |

---

## 4. 模块如何引用契约

在 `SKILL.md` 中**引用文件名与版本**，不要复制字段定义：

```markdown
## 输入契约
本模块使用 `contracts/skill_input.schema.json`（v1.0.0）的字段：
- `request_id` —— 用于串联结果
- `products[]` —— 待审商品
- `rules[]` —— 待用规则
- `provenance` —— 必须原样透传

## 输出契约
本模块产出符合 `contracts/audit_result.schema.json`（v1.0.0）的 `AuditResult[]`：
- `module` 固定为 `shopee-br-listing-audit`
- `rule_refs[]` —— 命中的规则引用
- `evidence_refs[]` —— 证据引用
- `errors[]` —— 解析错误与未评估项
```

**不要**在自己的文档里重述契约字段 —— 那会立刻产生不一致。

---

## 5. 变更流程

契约冻结后，任何变更走：

```
Agent 提交变更建议（AGENT_COLLABORATION.md §4.1）
  → 集成 Agent 评估影响面
  → 集成 Agent 修改契约文件 + 提升版本号
  → 集成 Agent 更新本索引
  → 通知所有模块重跑契约相关测试
```

**模块 Agent 不得直接修改 `contracts/` 下的任何文件。**

---

## 6. 快速校验

```bash
# 校验契约文件自身合法
env -u LD_LIBRARY_PATH python3 tools/validate_json.py \
    --schema data/schema/lexicon.schema.json contracts/ 2>/dev/null | tail -2

# 校验模块输出符合 audit_result 契约
env -u LD_LIBRARY_PATH python3 tools/validate_json.py \
    --schema contracts/audit_result.schema.json tests/<module>/
```

> 注：`contracts/` 下的 Schema 文件自身用 `tools/validate_json.py` 的 JSON 语法检查（它们是 Schema，不是 Schema 的实例）。
