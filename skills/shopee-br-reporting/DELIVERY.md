# TASK-REPORT-01 交付说明

> 任务：`TASK-REPORT-01` —— 审核结果汇总与报告生成模块
> 模块：`shopee-br-reporting`
> 契约版本：1.0.0
> 交付日期：2026-10-27
> 工作区：`/config/dianshang/Shopee-BR-Compliance-Skills`（未建独立分支，按主 Agent 统一提交）

---

## 1. 文件清单

| 路径 | 动作 | 说明 |
|---|---|---|
| `skills/shopee-br-reporting/SKILL.md` | 修改 | 七要素齐全；状态由「骨架」改为「已实现」；补输入适配格式、核心不变式、失败处理表、实测基线、待填内容与变更记录 |
| `skills/shopee-br-reporting/references/aggregation_rules.md` | 修改 | 填实：verdict 由 action 推导的不变式、verdict 取重、action 粒度保留、风险等级替换算法、H2 清洗表、缺口并集、规则去重与冲突记录、置信度取最弱、常见聚合错误 |
| `skills/shopee-br-reporting/references/report_structure.md` | 修改 | 填实：六节固定结构、每节的指标与空值表达、第 3/5/6 节的列定义、硬约束节的数字回填规则、Markdown 转义 |
| `skills/shopee-br-reporting/references/evidence_citation.md` | 修改 | 填实：只引用不改写、命中片段与政策原文的区分、来源层级中文映射、证据字段呈现、H5 的四条具体做法、核查日期透传 |
| `skills/shopee-br-reporting/src/sbr_reporting/__init__.py` | 新增 | 公开 API（`run_reporting` / `render_report` / `aggregate` / `build_summary` / `build_handoff`）、版本标识 |
| `skills/shopee-br-reporting/src/sbr_reporting/matrix.py` | 新增 | 契约矩阵的只读视图：verdict 顺序、动作粒度顺序、允许组合、风险等级顺序、`MatrixUnavailable` |
| `skills/shopee-br-reporting/src/sbr_reporting/contracts.py` | 新增 | 运行时契约校验器（最小 JSON Schema 子集，纯标准库），校验 `AuditResult` 与 `ModuleHandoff` |
| `skills/shopee-br-reporting/src/sbr_reporting/errors.py` | 新增 | `ErrorLog`：错误记录的统一容器（`warning` / `error` / `fatal`） |
| `skills/shopee-br-reporting/src/sbr_reporting/loader.py` | 新增 | 结果装载：内联 + 文件三种形态；逐条契约校验；单文件失败不中断整批 |
| `skills/shopee-br-reporting/src/sbr_reporting/aggregate.py` | 新增 | 聚合引擎：H2 清洗、verdict 取重、action 粒度保留、风险等级替换、`unevaluated`/`errors`/`rule_refs`/`evidence_refs` 并集、冲突记录 |
| `skills/shopee-br-reporting/src/sbr_reporting/render.py` | 新增 | 六节 Markdown 报告渲染 + 硬约束清单 + 中文标签映射 + 表格转义 |
| `skills/shopee-br-reporting/src/sbr_reporting/rules.py` | 新增 | 规则索引：只读 `rules/**`，提供类别 / 严重度 / 来源层级 / 核查日期 |
| `skills/shopee-br-reporting/src/sbr_reporting/pipeline.py` | 新增 | 管线编排：装载 → 聚合 → 汇总 → 渲染 → 落盘；交接记录构造 |
| `skills/shopee-br-reporting/src/sbr_reporting_cli.py` | 新增 | 命令行入口（`--request-id` / `--out-dir` / `--result-file` / `--skill-input`） |
| `tests/shopee-br-reporting/run_tests.py` | 新增 | 210 项断言，覆盖 L1–L4 + 报告结构 + 失败路径 + 端到端 + CLI + 共享夹具 + 真实上游集成 + 引文核验 |
| `skills/shopee-br-reporting/DELIVERY.md` | 新增 | 交付说明：文件清单、测试真实输出、未解决问题、依赖说明、契约变更建议、自我约束核查 |

**代码规模**：实现 2,343 行（10 个 Python 文件），测试 1,124 行，文档 870 行。

## 2. 测试结果

### 2.1 模块自有测试

```bash
$ cd /config/dianshang/Shopee-BR-Compliance-Skills && env -u LD_LIBRARY_PATH python3 tests/shopee-br-reporting/run_tests.py
```

实际输出（完整）：

```
==============================================================
shopee-br-reporting 模块测试
仓库根: /config/dianshang/Shopee-BR-Compliance-Skills
运行时间: 2026-10-27T09:31:30.510894+00:00
==============================================================

=== L1 单元测试 ===

=== L2 契约测试 ===

=== L3 聚合测试 ===

=== L4 硬约束测试 ===

=== 报告结构测试 ===

=== 失败路径测试 ===

=== 端到端与 CLI 测试 ===

=== 共享夹具兼容性（只读） ===

=== 与真实上游模块的集成 ===

=== 引文核验 ===

==============================================================
PASSED: 210   FAILED: 0
全部测试通过。
```

**退出码 0。**

### 2.2 真实上游模块集成

上游 `shopee-br-listing-audit` 在本任务交付期间已就绪。本模块把它在
`tests/fixtures/violation_products.json`（39 件明确违规商品）上的**真实产出**
直接送进本模块：

```
listing-audit produced 39 results
sample result: {"result_id": "RES-LISTING-REQ-INTEG-001-FX-VIOL-PI001", "request_id": "REQ-INTEG-001",
"module": "shopee-br-listing-audit", "target_ref": "FX-VIOL-PI001", "verdict": "BLOCK",
"risk_level": "critical", "action": "block", "reason": "3 rule(s) fired on FX-VIOL-PI001: ..."}
reporting ok: True
targets: 39
batch: BLOCK block
errors: 0
unevaluated: 0
rules in summary: 33
```

**39 条真实结果 → 39 个目标聚合，0 错误，33 条去重后的规则。**
该用例已固化进 `run_tests.py` 的「与真实上游模块的集成」段。

### 2.3 CLI 端到端

```bash
$ env -u LD_LIBRARY_PATH python3 skills/shopee-br-reporting/src/sbr_reporting_cli.py \
    --request-id REQ-DEMO-001 \
    --out-dir /tmp/report-demo/out \
    --result-file /tmp/report-demo/results.json
```

实际输出：

```
request:  REQ-DEMO-001
targets:  39
results:  39 from 1 module(s)
verdict:  BLOCK  action: block  risk_level: critical
gaps:     0 unevaluated, 0 error(s)
errors:   0
outputs:  /tmp/report-demo/out
```

**退出码 0。** 产出四份文件：`audit_summary.json` / `audit_report.md` /
`audit_results.json` / `module_handoff.json`。

### 2.4 产出对契约的校验

```bash
$ env -u LD_LIBRARY_PATH python3 tools/validate_json.py \
    --schema contracts/module_handoff.schema.json /tmp/report-demo/out/module_handoff.json
ok   /tmp/report-demo/out/module_handoff.json

0 errors, 0 warnings
```

`audit_results.json` 中的每一条 `AuditResult` 也在测试里逐条通过了
`contracts/audit_result.schema.json` 的校验（`L2 契约测试` 段 + 集成段）。

### 2.5 全项目校验

```bash
$ cd /config/dianshang/Shopee-BR-Compliance-Skills && env -u LD_LIBRARY_PATH bash scripts/check_all.sh
```

实际输出（完整）：

```
== 0/10  框架自检（并行开发框架不变量）==
==============================================================
PASSED: 272   FAILED: 0
框架自检全部通过。

== 1/10  公共契约校验（contracts/）==

==========================================================
契约校验 — 通过 19，失败 0
公共契约全部通过。

== 2/10  合并词库校验（lexicon/ + 映射表）==

=== 5. 词库→规则映射 ===

==============================================================
PASSED: 305   FAILED: 0
词库校验通过：37 组 / 856 词 / 37 条映射 / 50 条规则

== 3/10  词库扫描器自测（回归用例）==
  ok   位置记录: offset=6 excerpt='Tênis Nike Air Max'

自测: 12/12 通过

== 4/10  规则库 + 词库 Schema 校验 ==
ok   rules/05_medicines_health.json

0 errors, 0 warnings
ok   lexicon/term_groups.json

0 errors, 0 warnings

== 5/10  引文逐字核验（无编造引文）==
ok    SBR-MED-003    verbatim in 'shopee_br_categorias_restrritas'

50/50 excerpts verified verbatim, 0 failed

== 6/10  来源清单与抓取件一致 ==
  抓取失败（已登记，不得用于支撑规则）：2 条
    - br_anvisa_publicidade_medicamentos
    - br_anvisa_medicamentos_prescricao
来源清单与抓取件一致。

== 7/10  规则触发正则可编译性 ==
检查 50 条规则、36 条正则
全部规则的正则可编译，且无逻辑自指缺陷。

== 8/10  共享夹具校验（Schema）==
validated 90 products, 10 cases across 8 scenarios + shared fixtures
all fixtures valid

== 9/10  夹具与规则库一致性（正例真命中 / 反例真不命中）==
校验 108 条夹具-规则断言：58 应命中、50 应不命中
全部夹具与规则库一致。

== 10/10  任务包与所有权一致性 ==

==============================================================
PASSED: 502   FAILED: 0
任务包与所有权一致性全部通过。

ALL CHECKS PASSED
```

**退出码 0。**

### 2.6 未执行的测试

| 测试 | 原因 |
|---|---|
| `shopee-br-duplicate-detection` / `shopee-br-ip-review` 的真实产出接入 | 这两个模块在本任务交付时仍在并行开发中，产出尚未稳定。输入适配对它们同样适用（按契约校验 + 按 `target_ref` 聚合），但**未实测** |
| 与主 Skill `shopee-br-compliance` 的端到端联调 | 属 `TASK-MAIN-01` 的范围 |
| 性能基准（万级商品耗时） | 章程 §6.1 要求先有基线再定阈值，本任务未做基准 —— 不臆造性能数字 |
| 报告的 PDF/HTML 渲染 | 本模块只产出 Markdown 与 JSON，不在任务范围 |

## 3. 未解决问题

| # | 问题 | 影响 | 建议 |
|---|---|---|---|
| 1 | `shopee-br-duplicate-detection` / `shopee-br-ip-review` 的真实产出未实测接入 | 若这两个模块的 `target_ref` 语义与 `product_id` 不同，聚合会按它们的 `target_ref` 分组 —— 逻辑上仍正确，但「逐商品结果」表的粒度可能与预期不同 | 上游稳定后跑一次集成用例即可确认；本模块无需改动 |
| 2 | 上游结果的 `verdict` 与 `action` 不一致时，本模块以矩阵推导的 verdict 为准 | 上游若自报了比动作更重的 verdict（例如自报 `BLOCK` 但动作是 `flag_for_review`），本模块会降级并记 `warning` | 这是**有意的**（否则 H2 可被绕过）。上游应保证自报值与动作一致；不一致时两条记录都会出现在 `errors[]` 里，不会静默 |
| 3 | 规则库缺失时报告第 6 节显示「无」 | 若 `rules/` 目录不可读，已查阅规则表会是空的 | 规则库是仓库内只读资产，正常不会缺失。若确实缺失，报告第 6 节会显示「无」而不是编造规则信息 |
| 4 | 上游给出的 `source_url` 与规则库不一致时以上游为准 | 上游可能刚更新过来源链接 | 差异会在 `conflicts[]` 中记录（仅当 `source_tier` 不同时才记录冲突）；`source_url` 的差异不记冲突 |
| 5 | 单个目标的 `reason` 在报告第 4 节被截断到 160 字符 | 长理由在报告里看不全 | 完整理由在 `audit_summary.json` 与 `audit_results.json` 里 —— 报告是摘要，不是唯一载体 |
| 6 | 未评估项在报告中按「规则 / 原因 / 缺失字段」呈现，不按目标分组 | 一个规则影响多个目标时，读者需要自己扫表 | 数据量不大时可接受。若目标数超过百级，建议增加按目标分组的子表 |
| 7 | 报告第 2 节的「待补齐的证据」表在违规批次里会很长（示例中 111 行） | 报告文件变大 | 表格形式便于筛选与排序；完整数据在 JSON 汇总里。若需要，可在 `options` 里加一个「每类证据只列一次」的开关（**本任务未实现**） |

## 4. 依赖说明

- **我依赖的**：
  - `TASK-POLICY-01`（来源信息用于报告第 6 节表格）
  - `contracts/risk_action_matrix.json`（**聚合语义的唯一权威** —— verdict 顺序、动作粒度、允许组合、硬约束清单）
  - `contracts/audit_result.schema.json` / `contracts/module_handoff.schema.json` / `contracts/evidence_reference.schema.json`（输出契约）
  - `rules/**`（规则元信息，只读）
- **我期待下游提供的**：
  - 上游模块以 `target_ref = product_id` 输出，使同一商品的多模块结果能聚合到一起
  - 上游为每条 `rule_refs[]` 填 `source_tier` —— **阻断类动作靠它满足 H2**；缺失时本模块会把该阻断降为 `flag_for_review`
  - 上游为缺输入的规则产出 `unevaluated[]` 条目（本模块会并集保留，但不会替上游生成）
  - 上游的 `matched_excerpt` 是人可读描述（不是内部 token）
  - 上游的 `artifact_ref` 只放路径或工单号，不放凭证内容
- **我对其他模块的影响**：
  - 本模块定义了报告的呈现结构与聚合语义 —— 其他模块的产出必须能被本模块消费而不丢失信息
  - 本模块会**拒绝**不符合契约的结果（记 `error` 并跳过）。上游若产出契约外的 verdict 取值（小写的 `pass`），结果会被丢弃并出现在报告第 2 节
  - 本模块要求上游的 `source_tier` 必须填 —— 这是 H2 的落地前提
  - 本模块的「整批结论」是主 Skill `shopee-br-compliance` 的直接输入

## 5. 契约变更建议

**无契约变更建议。**

实现过程中未发现需要修改冻结契约的问题。三点**使用说明**（非变更请求）：

1. `contracts/audit_result.schema.json` 的 `type` 是 `object`（单条），但本模块产出
   `AuditResult[]`。沿用 `shopee-br-data-ingestion` 的同一约定：CLI 同时写
   `audit_results.json`（数组）与逐条可校验的形式。
2. `contracts/risk_action_matrix.json` 的 `actions` 段没有显式声明动作的**粒度顺序**，
   但它的**声明顺序**（`allow` → … → `escalate_legal`）天然就是粒度顺序。
   `verdict_aggregation.rule = "max_with_action_detail"` 的实现依赖这一点。
   本模块据此实现并在 `references/aggregation_rules.md` §4 写明。
   若集成 Agent 认为该依赖不够显式，建议在矩阵里补一个显式的
   `action_granularity` 数组 —— **non-blocking**，本模块的现有实现无需改动即可继续工作。
3. `contracts/audit_result.schema.json` 的 `errors[].error_id` 有 `minLength: 4`
   约束。上游若用 3 字符的 ID，该结果会被契约校验拒绝。本模块已实测此路径
   （`L2 契约测试` 段的「契约拒绝 verdict=...」与失败路径段）。

## 6. 自我约束核查

- [x] 只改了白名单内的文件（`skills/shopee-br-reporting/**`、`tests/shopee-br-reporting/**`）
      —— `git status --short` 确认：本任务只产生 `M skills/shopee-br-reporting/SKILL.md`、
      `M skills/shopee-br-reporting/references/*.md`、`?? skills/shopee-br-reporting/src/`、
      `?? tests/shopee-br-reporting/` 四类变更。`skills/shopee-br-duplicate-detection/src/`、
      `skills/shopee-br-ip-review/src/`、`skills/shopee-br-listing-audit/src/`、
      `tests/shopee-br-duplicate-detection/`、`tests/shopee-br-listing-audit/`
      是**其它并行 Agent 的产出**，本任务未触碰
- [x] 未修改公共契约（`contracts/**`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、
      `manifest.json`、`tasks/**`、`tests/test_plan.md`、`docs/**`、`tools/**`、`scripts/**`）
- [x] 未修改他人拥有的文件（`rules/**`、`research/**`、`lexicon/**`、`tests/fixtures/**`）
- [x] 引文核验通过（本模块不新增引文；全库 `50/50 excerpts verified verbatim, 0 failed` 保持通过，
      并在 `run_tests.py` 的「引文核验」段断言）
- [x] 自有测试实际执行（210 项全通过，输出见 §2.1）
- [x] 全项目校验实际执行（`scripts/check_all.sh` 退出码 0，输出见 §2.5）
- [x] `SKILL.md` 七要素齐全（frontmatter、职责/非职责、输入契约、输出契约、
      规则与来源要求、失败处理、测试案例与验收标准；另含依赖、文件所有权、
      待填内容、变更记录）
- [x] `references/` 内容已填实（3 份文档，无占位符、无 TODO）
- [x] 硬约束 H1–H6 已逐条自查（`run_tests.py` 的 `L4 硬约束测试` 段有逐条断言，
      `SKILL.md` §8 有逐条说明，报告末尾有自检清单）
- [x] 未执行 git commit / git push（由主 Agent 统一提交）
