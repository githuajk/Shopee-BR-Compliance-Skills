# SBRCA 模块完成进度报告

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-PROG-001` |
| 版本 | 1.0.0 |
| 状态 | **Draft — 进度快照，待用户确认** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 七个模块 + 公共层的实际完成度核查 |
| 核查方式 | 机械核验（文件内容、任务注册表、校验输出），非人工估计 |

---

## 1. 总体结论

| 层面 | 完成度 | 说明 |
|---|---|---|
| **公共层**（契约/规范/词库/夹具/校验） | **~90%** | 可用，冻结 |
| **七个模块** | **~20%** | 骨架就绪，**业务逻辑未实现** |
| **整体** | **~35%** | 框架完成，模块待开发 |

> ⚠️ **注册表说 2/10 任务完成（20%），但这是"框架任务"的口径。**
> 按模块实际能力算，7 个模块都还只是**骨架**：有完整的 SKILL.md 与 references 目录，
> 但**没有任何一个模块有可执行的判定逻辑**。

---

## 2. 公共层：已完成

| 资产 | 规模 | 状态 |
|---|---|---|
| 公共契约 | 9 份（contracts/） | ✅ 冻结 |
| 全局规范 | `PROJECT_RULES.md` + `AGENT_COLLABORATION.md` | ✅ 冻结 |
| 统一 SOP | `docs/SOP_COMPLIANCE_REVIEW.md`（18 章） | ✅ 合并 9 份历史文档 |
| 合并词库 | 37 组 / 856 词 + 5 份配套资产 | ✅ 覆盖率 96.3% |
| 词→规则映射 | 37 条 | ✅ |
| 规则库 | 50 条（49 active） | ✅ 引文 50/50 逐字核验 |
| 共享夹具 | 7 份 / 90 商品 / 10 案件 | ✅ |
| 任务包 | 9 份 | ✅ |
| 校验工具链 | 9 个（框架 298 / 契约 19 / 词库 305 / 任务包 589 项断言） | ✅ |

**校验流程**：`scripts/check_all.sh` 9 步全通过。

---

## 3. 七个模块：骨架就绪，业务逻辑为空

| 模块 | SKILL.md | references | 规则 | **可执行逻辑** | **自有测试** |
|---|---|---|---|---|---|
| `shopee-br-policy-research` | 6.8 KB / 11 章 | 4 份 | 0 | ❌ 无 | ❌ 无 |
| `shopee-br-data-ingestion` | 7.4 KB / 13 章 | 4 份 | 0 | ❌ 无 | ❌ 无 |
| `shopee-br-listing-audit` | 9.0 KB / 12 章 | 5 份 | **34** | ⚠️ 词库层有 | ❌ 无 |
| `shopee-br-duplicate-detection` | 8.9 KB / 14 章 | 4 份 | **8** | ❌ 无 | ❌ 无 |
| `shopee-br-ip-review` | 9.5 KB / 13 章 | 4 份 | **8** | ⚠️ 词库层有 | ❌ 无 |
| `shopee-br-reporting` | 8.0 KB / 20 章 | 3 份 | 0 | ❌ 无 | ❌ 无 |
| `shopee-br-compliance` | 11.1 KB / 15 章 | 4 份 | 0 | ⚠️ 词库层有 | ❌ 无 |

**31 个 references 全部标记 `Draft — 骨架，内容待 TASK-*-01 填充`**，每个末尾都有「待 XXX 确定」章节。

**34 个待填项**（`SKILL.md` 的 `- [ ]` 清单）：

| 模块 | 待填 | 构成 |
|---|---|---|
| policy-research | 5 | 4 份 references + 1 个测试 |
| data-ingestion | 5 | 4 份 references + 1 个测试 |
| listing-audit | 5 | 4 份 references + 1 个测试 |
| duplicate-detection | 5 | 4 份 references + 1 个测试 |
| ip-review | 5 | 4 份 references + 1 个测试 |
| reporting | 4 | 3 份 references + 1 个测试 |
| compliance | 5 | 4 份 references + 1 个测试 |

> **每个模块都缺一个 `tests/<module>/run_tests.py`** —— `tests/` 下只有 `fixtures/` 与 `test_plan.md`，**没有任何模块自有测试**。

---

## 4. 任务状态

| 任务 | 波次 | 状态 |
|---|---|---|
| `TASK-FRAME-01` 框架与契约 | G0 | ✅ completed |
| `TASK-FRAME-02` 测试与验收标准 | G1 | ✅ completed |
| `TASK-POLICY-01` | G2 | ⬜ pending |
| `TASK-INGEST-01` | G2 | ⬜ pending |
| `TASK-LISTING-01` | G3 | ⬜ pending |
| `TASK-DUP-01` | G3 | ⬜ pending |
| `TASK-IP-01` | G3 | ⬜ pending |
| `TASK-REPORT-01` | G3 | ⬜ pending |
| `TASK-MAIN-01` | G4 | ⬜ pending |
| `TASK-INTEGRATE-01` | G5 | ⬜ pending |

**2/10 完成**，8 个待分发。最大并行度 4（G3）。

---

## 5. 本次核查发现并修复的问题

### 5.1 仿牌变体的边界策略缺陷（真实缺陷，已修）

**现象**：`ip_variante_marca` 组的 42 个仿牌拼写变体（`Addidas`、`Rolecx`、`N1ke`…）
用严格边界匹配时，**最典型的仿牌形态全部漏检**：

```
Addidaspreto     → 无命中   ← 应该命中
Rolecx旗舰店      → 无命中   ← 应该命中
```

**根因**：仿牌变体本身就常与其它文字粘连（`Addidas` + `preto`），
而严格边界要求前后不能是字母。

**修复**：在词库元信息里增加**组级匹配策略**：

| 组类型 | 策略 | 理由 |
|---|---|---|
| 真品牌名 `ip_marca_global` | `strict` | `Nikex` 不是 `Nike` |
| 仿牌变体 `ip_variante_marca` | `loose` | `Addidaspreto` 就是 `Addidas` |

**回归保护**：`tools/scan_lexicon.py --self-test` 12 条用例全通过，已接入 `check_all.sh` 第 3 步。

### 5.2 其它

- `lexicon.schema.json` 增加 `matching` 字段（枚举 `strict`/`loose`）
- `validate_lexicon.py` 增加策略检查：仿牌变体组必须 loose，真品牌组必须 strict

---

## 6. 关键判断：什么算"完成"

一个模块算完成，必须同时满足：

| # | 条件 | 当前 |
|---|---|---|
| 1 | `SKILL.md` 七要素齐全 | ✅ 7/7 |
| 2 | `references/` 每份有实质内容（非骨架） | ❌ 0/31 |
| 3 | 实现可执行的判定逻辑 | ❌ 0/7 |
| 4 | 有 `tests/<module>/run_tests.py` 且实际执行通过 | ❌ 0/7 |
| 5 | 只改白名单内文件 | — 未开始 |
| 6 | 硬约束 H1–H6 逐条自查 | — 未开始 |
| 7 | 产出通过 `audit_result.schema.json` 校验 | ❌ 0/7 |

**按此标准，当前 0/7 模块完成。**

---

## 7. 已具备的条件（分发前无需再准备）

| 条件 | 状态 |
|---|---|
| 公共契约冻结 | ✅ |
| 路径所有权唯一 | ✅ 机械校验 |
| 并行波次路径零重叠 | ✅ 机械校验 |
| 依赖图无环 | ✅ 机械校验 |
| 规则库 + 引文 | ✅ 50 条 / 50/50 逐字核验 |
| 词库 + 映射 | ✅ 856 词 / 37 条映射 |
| 共享夹具（含正例与反例） | ✅ 90 商品 / 10 案件 |
| 夹具与规则库一致性 | ✅ 108 条断言全通过 |
| 词库扫描器 + 回归用例 | ✅ 12/12 |
| 任务包（自包含） | ✅ 9 份 |

> **分发前唯一还缺的是用户裁定** `SBRCA-P0-004` 的 14 项待确认事项。

---

## 8. 建议的推进顺序

```
第 0 步：用户裁定 P0-004 的 14 项（每项带 default_if_no_answer，可按默认执行）
   ↓
第 1 步：分发 G2 —— TASK-INGEST-01（建议优先，产出是其余模块的输入）
              + TASK-POLICY-01（2 个 Agent 并行）
   ↓
第 2 步：分发 G3 —— TASK-LISTING-01 / DUP-01 / IP-01 / REPORT-01（4 个 Agent 并行）
   ↓
第 3 步：分发 G4 —— TASK-MAIN-01（主 Skill，需等 G3 完成）
   ↓
第 4 步：分发 G5 —— TASK-INTEGRATE-01（集成验收）
```

**建议 8 个 Agent；最低 3 个**（A→B→{C,D,E,F}→G）。

**每个 Agent 需要的输入**：
1. `tasks/TASK-<X>.md`（自包含任务包）
2. `PROJECT_RULES.md` + `AGENT_COLLABORATION.md`
3. `contracts/` 全部
4. 本模块的 `skills/<module>/SKILL.md` + `references/`

---

## 9. 未决事项

| # | 问题 | 默认处置 |
|---|---|---|
| 1 | P0-004 的 14 项待裁定 | 按各项 `default_if_no_answer` 执行 |
| 2 | P1：是否建本地 Git 仓库 | 暂不建（待裁定） |
| 3 | 词库规模（`CONF-002`） | 856 词先跑基准，十万条假设待验证 |
| 4 | 专利规则 `SBR-IP-009` | 在 `TASK-IP-01` 补 |
| 5 | 处罚点分值表（平台未公开） | 只用「是否扣分」标识，不编造分值 |

---

## 10. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-10-27 | 初版进度快照；修复仿牌变体边界策略缺陷 |
