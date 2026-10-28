# TASK-MAIN-01 交付说明

> 任务：`TASK-MAIN-01` —— 主 Skill（编排层）
> 模块：`shopee-br-compliance`
> 契约版本：1.0.0
> 交付日期：2026-10-27

---

## 1. 文件清单

| 路径 | 行数 | 说明 |
|---|---|---|
| `skills/shopee-br-compliance/src/sbr_compliance/__init__.py` | 106 | 公开接口（`run_compliance` / `decide` / `aggregate` / `render_report`） |
| `skills/shopee-br-compliance/src/sbr_compliance/registry.py` | 121 | 模块登记（`ModuleSpec` / `MODULE_SPECS` / `STAGE_ORDER`） |
| `skills/shopee-br-compliance/src/sbr_compliance/routing.py` | 247 | 分流决策（`decide()` / `RoutingDecision`） |
| `skills/shopee-br-compliance/src/sbr_compliance/driver.py` | 320 | **显式读取模块 SKILL.md 并驱动其 CLI**（`run_module()`） |
| `skills/shopee-br-compliance/src/sbr_compliance/integration.py` | 585 | 清洗与聚合（`sanitize()` / `aggregate_target()`） |
| `skills/shopee-br-compliance/src/sbr_compliance/matrix.py` | 198 | 契约矩阵只读视图（`RiskMatrix`） |
| `skills/shopee-br-compliance/src/sbr_compliance/contracts.py` | 144 | 运行时契约校验器（最小 JSON Schema 子集） |
| `skills/shopee-br-compliance/src/sbr_compliance/pipeline.py` | 665 | 编排主流程（`run_compliance()`） |
| `skills/shopee-br-compliance/src/sbr_compliance/render.py` | 315 | Markdown 报告渲染 |
| `skills/shopee-br-compliance/src/sbr_compliance/errors.py` | 74 | 错误日志（7 个 stage 常量） |
| `skills/shopee-br-compliance/src/sbr_compliance_cli.py` | 311 | 命令行入口 |
| `skills/shopee-br-compliance/SKILL.md` | 251 | 七要素齐全，状态改为 Active |
| `skills/shopee-br-compliance/references/routing.md` | 190 | 分流决策表与边界情形 |
| `skills/shopee-br-compliance/references/execution_workflow.md` | 239 | 显式工作流逐步说明 |
| `skills/shopee-br-compliance/references/integration_rules.md` | 172 | 整合、聚合与冲突处理 |
| `skills/shopee-br-compliance/references/degradation.md` | 148 | 模块缺失时的降级行为 |
| `tests/shopee-br-compliance/run_tests.py` | 480 | 107 项断言（L1–L9） |

**实现合计**：约 3,044 行（源）+ 749 行（references）+ 480 行（测试）。

## 2. 测试真实输出

```bash
$ env -u LD_LIBRARY_PATH python3 tests/shopee-br-compliance/run_tests.py
```

实际输出：

```
==============================================================
shopee-br-compliance 模块测试
仓库根: /config/dianshang/Shopee-BR-Compliance-Skills
==============================================================

=== L1 模块登记 ===
=== L2 各模块 CLI 参数约定（编排器必须逐个适配） ===
=== L3 分流决策 ===
=== L4 显式读取模块 SKILL.md ===
=== L5 整合层 —— 硬约束在整合时不被降级 ===
=== L6 真实串联（不是模拟） ===
=== L7 数据缺口必须被上报（不得静默） ===
=== L8 CLI 端到端 ===
=== L9 边界 —— 不执行任何线上处置 ===

==============================================================
PASSED: 107   FAILED: 0
耗时: 6.72s
模块测试全部通过。
```

**退出码 0。**

### 2.1 全项目校验

```bash
$ env -u LD_LIBRARY_PATH bash scripts/check_all.sh
```

实际输出（摘要）：

```
PASSED: 217   FAILED: 0      框架自检全部通过。
契约校验 — 通过 19，失败 0
PASSED: 305   FAILED: 0      词库校验通过
0 errors, 0 warnings
0 errors, 0 warnings
50/50 excerpts verified verbatim, 0 failed
来源清单与抓取件一致。
全部规则的正则可编译，且无逻辑自指缺陷。
validated 90 products, 10 cases across 8 scenarios + shared fixtures
校验 108 条夹具-规则断言：58 应命中、50 应不命中
PASSED: 305   FAILED: 0      任务包与所有权一致性全部通过。
ALL CHECKS PASSED
```

**退出码 0。**

### 2.2 真实串联实测

```bash
$ env -u LD_LIBRARY_PATH python3 skills/shopee-br-compliance/src/sbr_compliance_cli.py \
    --request-id REQ-G4-TEST-002 --out-dir /tmp/g4out2 \
    --product-file tests/fixtures/violation_products.json
```

```
module:   shopee-br-compliance/1.0.0  contract: 1.0.0
request:  REQ-G4-TEST-002
route:    shopee-br-listing-audit → shopee-br-ip-review →
          shopee-br-duplicate-detection → shopee-br-reporting
targets:  39
results:  117 upstream result(s)
verdict:  BLOCK  action: escalate_legal  risk_level: critical
gaps:     6 unevaluated, 3 error(s)
outputs:  /tmp/g4out2
```

各模块实际产出：

| 模块 | ok | 结果数 |
|---|---|---|
| `shopee-br-listing-audit` | ✅ | 39 |
| `shopee-br-ip-review` | ✅ | 39 |
| `shopee-br-duplicate-detection` | ✅ | 39 |
| `shopee-br-reporting` | ✅ | 40 |

3 条 error 是 duplicate-detection 的 H3 警告（本次输入无 `cases[]`，
跨店比对不可行、无案件历史）—— **正确行为**，不是缺陷。

### 2.3 故障注入验证

| 注入 | 结果 |
|---|---|
| 把 ip-review 的参数改回 `--skill-input` | exit 1，报「shopee-br-ip-review 真实执行成功: the module exited with status 2: … unrecognized arguments: --skill-input」 |
| 去掉整合层的 H1 压回 | exit 1，报「H1：IP 结论被压回 signal: confirmed」「H1：压回动作被记录（非静默）: []」 |

### 2.4 未执行的测试

| 测试 | 原因 |
|---|---|
| 端到端走 ingestion（XLSX → 规范化） | 本次串联用 `--product-file`（已规范化的 `products[]`），跳过了 ingestion 阶段。ingestion 本身有 201 项独立测试 |
| 跨店同款识别 | 共享夹具 `violation_products.json` 只有 1 个店铺，跨店比对维度记为未评估。跨店逻辑由 duplicate-detection 的 587 项独立测试覆盖 |

## 3. 我在验收子 Agent 产出时发现并修复的缺陷

子 Agent 因 Token Plan 429 中止，写了 11 个源文件（3,044 行）但**没写测试**。
我核实其产出时发现两个模块**根本没跑起来**，而编排器报告的是「0 errors」。

### 缺陷 1：CLI 参数约定套错（`driver.py`）

各模块的 argv 约定**并不统一**，此前对三个「else」模块套用了同一套：

| 模块 | 实际参数 | 此前编排器传的 |
|---|---|---|
| `ip-review` | `--request-id` + **位置参数**（无 `--skill-input`） | `--skill-input` ❌ |
| `duplicate-detection` | `--skill-input`（**无** `--request-id`） | 两者都传 ❌ |
| `listing-audit` | 两者都认 | ✅ |

套错 → argparse 直接退出 → **该维度静默缺失**。

实测对比：

```
修复前：listing-audit 39 / ip-review 0 / duplicate 0 / reporting 40
修复后：listing-audit 39 / ip-review 39 / duplicate 39 / reporting 40
```

**最危险的地方**：汇总结果从 39 条变成 117 条，但 `error_count` 仍是 0，
报告里看不出缺了 IP 与重复两个维度。已加 L2 段测试逐个核对五个 `--help`。

### 缺陷 2：整合层不强制 H1（`integration.py`）

上游若误报 `confidence=confirmed`，汇总层原样传出。主 Skill 是**最后
一道关口**，不该盲信上游。

已加：引用 `SBR-IP-*` 规则的结果，`confidence` 强制压回 `signal`、
`requires_human_review` 强制为 `true`，调整原因写入 `errors[]`。

判据用**规则 ID 前缀**而非 `module` 字段 —— 别的模块引用 IP 规则时
同样受约束。

### 文档层面的不实内容（我一并更正）

| 位置 | 原文 | 实际 |
|---|---|---|
| `SKILL.md` §8 | 「动作只增不减 …… 不被任何模块降级」 | **错的**。H2 要求阻断动作必须可追溯到权威来源，整合层**必须**有权降级。只增不减会让一条 `internal_risk` 规则自报 `block` 就直接成为最终结论 |
| `SKILL.md` §5.1 | 分流表写「多商品同店 → 不跑 duplicate-detection」 | 与实现不符。**只要有商品，三个专业维度都执行**；单店时跨店维度由模块记缺口 |
| `references/routing.md` §6 | 4 项「待确定」 | 其中「是否支持手动指定模块」已实现（`options.modules`），已填实 |
| `references/degradation.md` §6 | 2 项「待确定」 | 已填实 |

## 4. 未解决问题

| # | 问题 | 影响 | 建议 |
|---|---|---|---|
| 1 | **汇总层只按 `target_ref` 分桶** | 若两个模块对同一商品给出的 `target_ref` 写法不同（如带/不带店铺前缀），会被分到两个目标，各自聚合 | 统一 `target_ref` 约定；或在分桶前做规范化 |
| 2 | **跨店重复维度需要跨请求数据** | 单请求内的跨店比对可行，但「与本批之外的商品重复」查不到 | 需要 duplicate-detection 提供跨批次查询入口 |
| 3 | **未做性能基线** | 39 商品 4 阶段耗时约 1.8 秒（含 4 次 Python 解释器启动）。5,000 商品的耗时未实测 | 参照 `lexicon_scanning.md` §7.1 的做法实测后记录 |
| 4 | **`--modules` 显式指定时，跳过的维度不产生 `unevaluated`** | 用户显式跳过某个维度 → 该维度的结论从结果里消失 | 当前行为是「用户明确要求的」；但建议在 `known_gaps` 里记一句「用户指定跳过」 |
| 5 | **词库扫描性能瓶颈未解决** | 词库层单次扫描 130ms/10KB，5,000 商品约 32 分钟 | 见 `skills/shopee-br-listing-audit/references/lexicon_scanning.md` §7.1 的 3 个优化方向 |
| 6 | **专利维度是盲区** | 平台有 `[604]` 码、法律有 Art. 183，但规则库无 `ip_patent` 规则 | 需引入权利要求比对能力；已登记在 `skills/shopee-br-ip-review/DELIVERY.md` §3 第 1 项 |

## 5. 依赖说明

- **我依赖的**：
  - `skills/shopee-br-data-ingestion/SKILL.md` +
    `skills/shopee-br-data-ingestion/src/sbr_ingestion_cli.py`
  - `skills/shopee-br-listing-audit/SKILL.md` +
    `skills/shopee-br-listing-audit/src/sbr_listing_audit_cli.py`
  - `skills/shopee-br-duplicate-detection/SKILL.md` +
    `skills/shopee-br-duplicate-detection/src/sbr_duplicate_detection_cli.py`
  - `skills/shopee-br-ip-review/SKILL.md` +
    `skills/shopee-br-ip-review/src/sbr_ip_review_cli.py`
  - `skills/shopee-br-reporting/SKILL.md` +
    `skills/shopee-br-reporting/src/sbr_reporting_cli.py`
  - `contracts/audit_result.schema.json`、`contracts/module_handoff.schema.json`、
    `contracts/risk_action_matrix.json`、`contracts/skill_input.schema.json`
- **期待下游的**：TASK-INTEGRATE-01（集成验收）会做跨模块串联测试 ——
  本模块的 CLI 入口就是它的驱动对象。
- **对其他模块的影响**：本模块**不重新判定**任何业务规则，也不改任何
  模块的规则库。它只做分流、显式驱动、整合、报缺口。

## 6. 契约变更建议

**无。**

一条 non-blocking 使用说明：`contracts/module_handoff.schema.json` 是
`additionalProperties: false` —— 交接记录**只能用**契约里的字段
（`handoff_id` / `from_module` / `to_module` / `request_id` /
`contract_version` / `produced_at` / `assumptions` / `known_gaps` /
`unevaluated` / `requires_human_review` / `payload_ref`）。自造
`summary` / `notes` 字段会让校验失败。现有实现已符合。

## 7. 自我约束核查

- [x] 模块测试实际执行（107 项全通过，退出码 0）
- [x] `scripts/check_all.sh` 10 步全绿
- [x] `SKILL.md` 七要素齐全，状态已改为 Active
- [x] 「待填内容」清单全部勾选
- [x] 4 份 references 全部填实，无 TODO / 占位符
- [x] 文档描述**代码里真实存在的行为** —— 每条关键论断都实跑核对过
- [x] 不假设 Skill 自动调用能力 —— 显式读 `SKILL.md` 并记录 SHA-256 摘要
- [x] 不执行任何线上处置 —— L9 段扫描 `import` 与动作动词
- [x] 硬约束 H1 / H2 / H3 在整合层**强制**，不盲信上游
- [x] 降级与调整全部可见（进 `errors[]` / `known_gaps`）
- [x] 只改了白名单内的路径（`skills/shopee-br-compliance/**`、
      `tests/shopee-br-compliance/**`）
- [x] 未修改 `contracts/`、`rules/`、`lexicon/`、`tasks/`、`tools/`、
      `scripts/`、`docs/`、`manifest.json`、`README.md`
- [x] 测试失败如实报告，未隐瞒
