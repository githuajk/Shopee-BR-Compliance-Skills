# 交付说明 —— TASK-INTEGRATE-01（Shopee BR 合规审核集成验收）

> 按 `AGENT_COLLABORATION.md` §8 的六段格式填写。**不得留空。**
> 任务包：`tasks/TASK-INTEGRATE-01.md`（12 章节，自包含，是唯一权威说明）。
> 工作区：`/config/dianshang/Shopee-BR-Compliance-Skills`（主仓库；未建独立分支，
> 提交由主 Agent 统一执行 —— 本任务**未** `git commit` / `git push`）。

---

## 12.1 文件清单

| 路径 | 动作 | 说明 |
|---|---|---|
| `tests/integration/run_tests.py` | 新增 | 集成验收脚本（1589 行，218 项断言）。**真实串联**：以子进程调用六个模块的真实 CLI，ingestion 的真实产出喂给三个审核模块，再喂给 reporting，最后由主 Skill 汇总。覆盖 `tests/test_plan.md` §6 的 C1–C6 / I1–I6 / V1–V6 / A1–A5，另含缺字段、注入、IP、重复、降级五类场景用例与 3 个跨模块缺陷的特征检测。 |
| `tests/integration/module_handoff.json` | 新增 | 本任务的交接记录，符合 `contracts/module_handoff.schema.json`（已用 `tools/validate_json.py` 校验通过）。`assumptions` 7 条、`known_gaps` 8 条、`unevaluated` 2 条（C5、C6）。 |
| `docs/integration_report.md` | 新增 | 集成验收报告（453 行）：逐项兑现 C1–C6 / I1–I6 / V1–V6 / A1–A5；全链路实测数字；C5/C6 两项未达成的说明；D1–D3 三个跨模块缺陷台账（含根因、影响、规避方式）；契约变更建议的证据表。 |
| `docs/parallel_execution_plan.md` | 修改 | 补记波次 5 的执行结果（C1–C4 / I1–I6 / V1–V6 / A1–A5 通过；C5、C6 未达成；登记 D1–D3），并更新 §4 完成判据与变更记录（版本 1.0.0 → 1.1.0）。 |

**未修改**：`contracts/`、`rules/`、`lexicon/`、`tasks/`、`tools/`、`scripts/`、
`manifest.json`、`README.md`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、
`tests/fixtures/`、`skills/**` —— 全部未动（`git status` 确认仅上述 4 个文件）。

**未新增共享夹具**：`tests/fixtures/` 的 7 个文件已覆盖验收所需的全部场景，
且 `tools/verify_fixtures.py` 的 108 条夹具-规则断言全部通过。验收需要的
跨模块组合数据（案件对象 + 改标题/SKU 的副本、两店同名同款）在脚本运行时
**从共享夹具派生**，不污染模块只读的夹具池。

---

## 12.2 测试结果

### ① 集成验收脚本（本任务自有测试）

```bash
cd /config/dianshang/Shopee-BR-Compliance-Skills
env -u LD_LIBRARY_PATH python3 tests/integration/run_tests.py
```

实际输出（尾部，退出码 **0**）：

```
==============================================================
Shopee BR 合规审核 —— 集成验收测试
仓库根: /config/dianshang/Shopee-BR-Compliance-Skills
运行时间: 2026-10-28T01:36:44.822866+00:00
==============================================================

=== C1–C6 跨模块冲突 / 重复 / 归属检查 ===
=== C6 证据类型词表 —— 各模块使用的 evidence_type ===
=== I3 接口一致性 —— 各模块 CLI 的参数面 ===
=== L5/L6 真实全链路：XLSX → ingestion → 三模块 → reporting → 主 Skill ===
=== I1–I5 契约符合性 —— 每一步的产出都通过真实 Schema 校验 ===
=== V1–V6 硬约束在全链路上的成立 ===
=== A1–A5 聚合行为 —— 一个商品的最终结论 = 各模块结论按契约聚合 ===
=== H3 场景：缺 title / brand → 对应维度记 unevaluated，最终不得判 PASS=***
=== 注入场景：描述里混入指令 → 不得改变判定结论（对照实验） ===
=== IP 场景：品牌宣称 / 假货 / 指示性使用（豁免）/ 授权缺失 / 授权完整 ===
=== 重复场景：跨店同款 / 违规重发 / 案件状态机 ===
=== 降级场景：某个模块不可用 → 如实报未执行，不判通过 ===
=== 已知集成缺陷 —— 如实登记，不静默、不计入回归失败 ===
  [缺陷 D1] 仍在：主 Skill 的 --result-file（仅整合）路径崩溃：伪 decision 对象缺 skipped 属性
  [缺陷 D1b] 仍在：主 Skill 的 --result-file 路径默认 root 推导上溯 4 级，找不到 contracts/risk_action_matrix.json
  [缺陷 D2] 仍在：ip-review 的 target_ref 取来源路径而非商品 id：15 条商品级结论塌缩为 1 个数据源级目标 —— 1 个 target_ref / 15 条结果
  [缺陷 D2b] 仍在：塌缩后的 target_ref 是来源文件路径（商品级归因丢失） —— /config/dianshang/Shopee-BR-Compliance-Skills/data/samples/demo_mass_update.xlsx
  [缺陷 D3] 仍在：主 Skill 的 --input 路径未产出任何商品：xlsx 的店铺名在 banner 单元格内、BANNER_SHOP 正则要求同行，shop_id 无法推导 —— 产出 0 件商品（期望 0 = 当前行为）
  [缺陷 D3b] 仍在：ingestion 对 15 条无法规范化的记录如实报 error（未静默丢弃） —— 30 条 error
  [缺陷 D3c] 仍在：--input 路径上三个专业维度全部未执行（只剩汇总） —— executed=['shopee-br-data-ingestion', 'shopee-br-reporting']

--------------------------------------------------------------
已知集成缺陷台账（DEFECT LEDGER）
--------------------------------------------------------------
  [D1] 仍存在：主 Skill 的 --result-file（仅整合）路径崩溃：伪 decision 对象缺 skipped 属性
  [D1b] 仍存在：主 Skill 的 --result-file 路径默认 root 推导上溯 4 级，找不到 contracts/risk_action_matrix.json
  [D2] 仍存在：ip-review 的 target_ref 取来源路径而非商品 id：15 条商品级结论塌缩为 1 个数据源级目标
  [D2b] 仍存在：塌缩后的 target_ref 是来源文件路径（商品级归因丢失）
  [D3] 仍存在：主 Skill 的 --input 路径未产出任何商品：xlsx 的店铺名在 banner 单元格内、BANNER_SHOP 正则要求同行，shop_id 无法推导
  [D3b] 仍存在：ingestion 对 15 条无法规范化的记录如实报 error（未静默丢弃）
  [D3c] 仍存在：--input 路径上三个专业维度全部未执行（只剩汇总）

==============================================================
PASSED: 218   FAILED: 0
已知缺陷: 7 条登记在册
耗时: 11.39s
集成验收全部通过。
```

### ② 全库校验

```bash
cd /config/dianshang/Shopee-BR-Compliance-Skills
env -u LD_LIBRARY_PATH bash scripts/check_all.sh
```

实际输出（退出码 **0**）：

```
== 0/10  框架自检（并行开发框架不变量）==
PASSED: 206   FAILED: 0
框架自检全部通过。

== 1/10  公共契约校验（contracts/）==
契约校验 — 通过 19，失败 0
公共契约全部通过。

== 2/10  合并词库校验（lexicon/ + 映射表）==
PASSED: 305   FAILED: 0
词库校验通过：37 组 / 856 词 / 37 条映射 / 50 条规则

== 3/10  词库扫描器自测（回归用例）==
自测: 12/12 通过

== 4/10  规则库 + 词库 Schema 校验 ==
0 errors, 0 warnings

== 5/10  引文逐字核验（无编造引文）==
50/50 excerpts verified verbatim, 0 failed

== 6/10  来源清单与抓取件一致 ==
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
PASSED: 256   FAILED: 0
任务包与所有权一致性全部通过。

ALL CHECKS PASSED
```

### ③ 各模块自有测试（回归确认）

```bash
# 对 7 个模块目录逐一执行自有测试（下面按模块名列全，避免变量展开）
env -u LD_LIBRARY_PATH python3 tests/shopee-br-data-ingestion/run_tests.py
env -u LD_LIBRARY_PATH python3 tests/shopee-br-policy-research/run_tests.py
env -u LD_LIBRARY_PATH python3 tests/shopee-br-listing-audit/run_tests.py
env -u LD_LIBRARY_PATH python3 tests/shopee-br-duplicate-detection/run_tests.py
env -u LD_LIBRARY_PATH python3 tests/shopee-br-ip-review/run_tests.py
env -u LD_LIBRARY_PATH python3 tests/shopee-br-reporting/run_tests.py
env -u LD_LIBRARY_PATH python3 tests/shopee-br-compliance/run_tests.py
```

实际输出：

```
shopee-br-data-ingestion         PASSED: 201   FAILED: 0
shopee-br-policy-research        PASSED: 1467   FAILED: 0
shopee-br-listing-audit          PASSED: 383   FAILED: 0
shopee-br-duplicate-detection    PASSED: 587   FAILED: 0
shopee-br-ip-review              PASSED: 231   FAILED: 0
shopee-br-reporting              PASSED: 210   FAILED: 0
shopee-br-compliance             PASSED: 107   FAILED: 0
```

### ④ 本任务交接记录的契约校验

```bash
env -u LD_LIBRARY_PATH python3 tools/validate_json.py \
    --schema contracts/module_handoff.schema.json tests/integration/module_handoff.json
```

实际输出：

```
ok   tests/integration/module_handoff.json

0 errors, 0 warnings
```

### ⑤ 全链路的实测数字（`REQ-INT-CHAIN-001`）

| 环节 | 产出条数 | `assumptions`/`known_gaps` |
|---|---|---|
| ingestion | 1（+ 15 件商品） | 6 / 2 |
| listing-audit | 15 | 5 / 2 |
| ip-review | 15 | 4 / 1 |
| duplicate-detection | 15 | 8 / 5 |
| reporting | 17 | 5 / 4 |
| 主 Skill 汇总 | 17 | 6 / 3 |
| **合计** | **80 条 `AuditResult`** | — |

* 主 Skill 汇总的结论分布：`PASS: 0 / REVISE: 0 / REVIEW: 14 / BLOCK: 2`
  （16 个目标 = 15 件商品 + 1 个数据源级目标）；
  整批结论 **BLOCK / escalate_legal / critical**，`deterministic_count = 2`、
  `human_only_count = 1`。
* 硬约束全链路断言：**19 条 IP 结论 0 违反 H1**、**8 条阻断类动作 0 违反 H2**、
  **64 条带缺口的结论 0 违反 H3**、**50/50 引文逐字核验通过**、
  **0 处凭证特征命中**、**0 处线上处置入口**。
* 聚合一致性：主 Skill 与 reporting 对**同一批**上游结果的聚合结论
  **16/16 目标逐项完全一致**（0 处差异）。

### 未执行的测试及原因

| 测试 | 原因 |
|---|---|
| `tests/integrator/run_tests.py` | **不适用** —— `integrator` 是**角色**而非 Skill 模块。`contracts/file_ownership.json` 的 `modules.integrator.owns` 不含 `skills/**`；`tools/task_pack_check.py` 明确断言「integrator 无 Skill.md（角色而非模块）」。任务包 §9 的「测试文件位置：`tests/integrator/`」与 §11 的「`skills/integrator/SKILL.md`（七要素齐全）」两处均与该角色定义冲突 —— 按**权威的**所有权登记（任务包 §2.2 声明「路径所有权由 `contracts/file_ownership.json` 定义，这是唯一权威来源」）执行：测试落在 `tests/integration/`（白名单内的 `tests/integration/**`），无 `SKILL.md` 与 `references/`。**这是任务包自身的内在不一致，已在 §12.5 登记为契约变更建议 S4。** |
| 真实 Shopee 导出文件的端到端回归 | 仓库内无真实导出样本，`data/samples/demo_mass_update.xlsx` 是唯一的 xlsx 合成样本。验收只覆盖该合成样本 + 共享夹具。 |
| `rules/03` 拆分后的回归 | 拆分未执行（C5），故无从验证拆分后的链路 —— 拆分需要白名单外的写权限。 |

---

## 12.3 未解决问题

| # | 问题 | 影响 | 建议 |
|---|---|---|---|
| 1 | **C5 未达成** —— `rules/03_listing_violations_duplicates.json` 仍同时含 14 条 `LV`（归 `shopee-br-listing-audit`）与 3 条 `DUP`（归 `shopee-br-duplicate-detection`） | **当前无功能影响**：两个模块都按 `rule_id` **前缀**从该文件取自己那部分，都不写它，集成验收已断言「每个规则文件的实际前缀 ⊆ 声明 owner 的前缀集」。但文件归属与前缀**不一致**，与 `contracts/file_ownership.json` 的单一归属原则相悖 | 在下一轮拿到 `rules/**` 与两个模块目录写权限后执行拆分：`DUP-*` 移入 `rules/04_cases_relist_authorization.json`（或新建 `rules/06_duplicates.json`），同步更新 `skills/shopee-br-listing-audit/src/sbr_listing_audit/rules.py` 的 `READONLY_RULE_FILES` 与 `skills/shopee-br-duplicate-detection/src/sbr_duplicate_detection/rules.py` 的 `RULE_FILES` |
| 2 | **C6 未达成** —— 4 个 `evidence_type`（`image` / `listing_field` / `price_history` / `promotion_terms`）不在 `contracts/evidence_reference.schema.json` 的 `examples` 集内（实际用 11 个，示例集 24 个） | **不违反 Schema** —— JSON Schema 的 `examples` 是注解而非断言，这 4 个值全部通过 `evidence_reference.schema.json` 校验（`minLength: 2` 才是约束）。但验收标准 C6 要求「在示例集内**或已扩充该 Schema**」 | 二选一：扩充 `contracts/evidence_reference.schema.json` 的 `examples`（**推荐**，词表应反映实际用法），或由 `shopee-br-listing-audit` 把这 4 个类型改名为既有词表中的名字 |
| 3 | **D1（严重）** —— 主 Skill 的 `--result-file`（仅整合既有结果）路径崩溃：`AttributeError: '_Decision' object has no attribute 'skipped'`（`skills/shopee-br-compliance/src/sbr_compliance/pipeline.py:566`） | 「拿已有审核结果做整合」这一入口**完全不可用** —— 交接给人工复核、或把多次审核合并成一批的流程走不通 | 在 `skills/shopee-br-compliance/src/sbr_compliance_cli.py` 的 `_integrate_only()` 里给伪 `_Decision` 类补上 `skipped = {}`（及 `reasons = {}`），或改用真实的 `routing.RoutingDecision` |
| 4 | **D1b** —— 同上路径的默认 root 推导上溯**四级**，落到仓库的**上一级**（`/config/dianshang`），找不到 `contracts/risk_action_matrix.json` | 同上（即使修好 D1 仍会失败） | 修正 `sbr_compliance_cli.py` 的 `_default_root()`：从 `skills/shopee-br-compliance/src/` 上溯**三级**（或直接复用 `sbr_compliance.matrix.find_repo_root()`，后者会向上探测含 `contracts/risk_action_matrix.json` 的目录） |
| 5 | **D2（建议优先修复）** —— `shopee-br-ip-review` 的 `target_ref` 取 `product['source']['path']` 而非商品 id，15 件商品的 IP 结论**塌缩成 1 个数据源级目标**（实测 1 个 `target_ref` / 15 条结果） | **不违反任何硬约束**（H1–H6 全部成立），但 IP 维度的**商品级归因丢失** —— IP 结论挂到了数据源上，人工复核时无法定位到具体商品。与 `listing-audit` / `duplicate-detection`（都用 `product_id`）口径不一致，是典型的「接口不一致」 | 把 `skills/shopee-br-ip-review/src/sbr_ip_review/engine.py` 的 `_target_ref()` 改为优先返回 `product_id`（`source.path` 属数据源级信息，适合放在 `provenance.source_refs`，那里已经有一份） |
| 6 | **D3** —— 主 Skill 的 `--input` 路径对 `data/samples/demo_mass_update.xlsx` 产出 **0** 件商品 | 「给一个 xlsx 就出结论」这一入口只产出 1 条数据源级结论，三个专业维度**全部未执行**。根因：xlsx 的 banner 是 `["Loja:", "Loja Demo SP", …]`（标签与店名在**相邻两个单元格**），而 `BANNER_SHOP` 正则要求两者**在同一单元格**，故 `shop_name` 解析不出；xlsx 又无 `shop_id` 列 | 两条路：(a) 放宽 `BANNER_SHOP` 使其能匹配「标签单元格 + 右侧相邻单元格」的形态（真实 Shopee 导出就是这个形态）；(b) 让主 Skill 的 `--input` 支持把 `--default-shop-id` 透传给 ingestion。**注意正面结论**：缺口没有被吞掉 —— ingestion 如实报 30 条 error、产出 15 条 `unevaluated`、结论为 `REVIEW / flag_for_review`（**不是 PASS**），主 Skill 的 `known_gaps` 也写明了未执行的维度 —— **H3 在这条路径上成立** |
| 7 | **任务包自身的内在不一致** —— §9 要求测试放 `tests/integrator/`、§11 要求 `skills/integrator/SKILL.md`（七要素齐全），但 `integrator` 是**角色**而非 Skill 模块（`contracts/file_ownership.json` 的 `modules.integrator.owns` 无 `skills/**`；`tools/task_pack_check.py` 断言「integrator 无 Skill.md」） | 照字面执行会越界（`skills/integrator/**` 与 `tests/integrator/**` 都不在 `modules.integrator.owns` 里） | 本任务按**权威的**所有权登记执行：测试落 `tests/integration/`（白名单内），无 `SKILL.md`/`references/`。建议由总控 Agent 修正 `tools/gen_task_packs.py` 对 `integrator` 这一角色的模板分支，使任务包的 §9/§11 与所有权登记一致（见 §12.5 S4） |
| 8 | `rules/03` 的拆分一旦执行，`tools/verify_fixtures.py` 的夹具归属与 `tools/task_pack_check.py` 的「并行波次路径零重叠」检查需同步复核 | 拆分后的规则文件路径变化可能触发既有校验的路径断言 | 拆分时一并跑 `env -u LD_LIBRARY_PATH bash scripts/check_all.sh` 确认 |

---

## 12.4 依赖说明

- **我依赖的**：
  - `TASK-MAIN-01`（主 Skill `shopee-br-compliance`）—— 已完成，107 项自测通过。集成验收**以它为驱动**：编排层由它执行，本任务验证它对上游模块的整合与降级行为。
  - 六个模块的真实 CLI 入口与 `rules/`、`contracts/`、`lexicon/`、`data/schema/`、`tests/fixtures/`、`research/raw/` —— 全部只读引用，未修改。
  - `tools/validate_json.py`（契约校验器）、`tools/verify_citations.py`（引文核验）、`tools/validate_fixtures.py`、`tools/verify_fixtures.py` —— 以**真实工具**执行，未自造校验逻辑。

- **我期待下游提供的**：
  - **主 Agent**：统一 `git commit` / `git push`（本任务**未**提交）。改动仅 4 个文件，全在 `modules.integrator.owns` 白名单内。
  - **`shopee-br-compliance` 模块 Agent**：修 D1（`_Decision` 缺 `skipped`）、D1b（默认 root 上溯 4 级）、D3（`--input` 路径的 `shop_id` 推导）。修好后 `tests/integration/run_tests.py` 中对应的特征检测断言会**失败** —— 那是提醒更新缺陷台账的信号，不是回归。
  - **`shopee-br-ip-review` 模块 Agent**：修 D2（`target_ref` 取 `product_id` 而非 `source.path`）。**建议优先** —— 它不影响硬约束，但影响人工复核的定位能力。
  - **总控 Agent**：`contracts/evidence_reference.schema.json` 的 `examples` 是否扩充（§12.3 #2）；`tools/gen_task_packs.py` 对 `integrator` 角色的模板分支是否修正（§12.3 #7）。
  - **集成 Agent（下一轮）**：`rules/03` 的拆分（§12.3 #1）—— 需要 `rules/**` 与两个模块目录的写权限。

- **我对其他模块的影响**：
  - **无代码改动**。本任务只新增 `tests/integration/**` 与 `docs/integration_report.md`，并更新 `docs/parallel_execution_plan.md`。
  - 但本任务**产出 3 个可复现的缺陷报告**（含精确复现命令与实测输出），它们是各模块 Agent 下一轮的直接输入 —— 尤其 D2 的「三个模块 `target_ref` 口径不一致」这一发现，是在真实全链路上跑出来的，单模块自测**看不到**。
  - `tests/integration/run_tests.py` 定位为**集成级**测试（`tests/test_plan.md` §2 的 L7 层级，责任方是集成 Agent），与各模块的 L1–L4 自测并列而不重叠 —— 它不重复验证各模块的规则语义，只验证**跨模块**的不变量。

---

## 12.5 契约变更建议

| # | 问题 | 证据 | 建议变更 | 影响面 | 严重度 |
|---|---|---|---|---|---|
| **S1** | `contracts/evidence_reference.schema.json` 的 `evidence_type.examples` 未覆盖 4 个实际使用的类型（`image` / `listing_field` / `price_history` / `promotion_terms`） | 真实全链路实测：实际使用 11 个 `evidence_type`，其中 4 个不在 24 个示例内；全部由 `shopee-br-listing-audit` 产出。见 `docs/integration_report.md` §4.2 | 在 `examples` 数组中补入这 4 个值（`examples` 是注解，补入不改变任何校验行为，只让词表反映实际用法） | `contracts/evidence_reference.schema.json`、`shopee-br-listing-audit`（无需改代码）；`tools/task_pack_check.py` 无影响 | non-blocking |
| **S2** | `tasks/task_registry.json` 里 `TASK-INTEGRATE-01.allowed_paths` 含 `rules/**`，与任务包 §2.1 的白名单（不含 `rules/**`）矛盾 | 注册表 `allowed_paths`：`["rules/**", "contracts/**", "manifest.json", "tests/fixtures/**", "docs/integration_report.md", "PROJECT_RULES.md", "AGENT_COLLABORATION.md"]`；任务包 §2.1：`docs/integration_report.md`、`docs/parallel_execution_plan.md`、`tests/fixtures/**`、`tests/integration/**`。任务包 §2.1 声明「越界即任务失败」，且 §2.2 声明 `contracts/file_ownership.json` 是唯一权威 | 二者对齐。若拆分本属集成阶段职责，则**任务包 §2.1 应补入 `rules/**`**（并在 §12.5 记录「拆分须同步更新两个模块的规则文件常量」）；若拆分不属本阶段，则**注册表的 `allowed_paths` 应删除 `rules/**`** | `tasks/task_registry.json`、`tasks/TASK-INTEGRATE-01.md`、`tools/gen_task_packs.py`（模板从注册表生成白名单） | blocking（针对 C5 拆分项） |
| **S3** | `contracts/audit_result.schema.json` 的 `target_ref` 未约束「同一批次内的可归属性」，导致 ip-review 可把 15 件商品塌缩成 1 个目标 | 实测：15 条 IP 结果 → 1 个 `target_ref`（值 = 来源文件路径），见 `docs/integration_report.md` §4.3 D2 | 二选一：(a) 在 `audit_result.schema.json` 的 `target_ref` 描述中明确「**商品级结论必须用商品 id**；数据源级引用应放在 `provenance.source_refs`」；(b) 新增 `target_kind` 枚举字段（`product` / `case` / `rule` / `data_source`）显式区分 | `contracts/audit_result.schema.json`、`shopee-br-ip-review`（改为用 `product_id`）、`shopee-br-compliance` 与 `shopee-br-reporting`（聚合时按 `target_ref` 分桶的口径需复核） | non-blocking |
| **S4** | 任务包模板对 `integrator` 这一**角色**生成了不适用 §9/§11 的内容 | 任务包 §9 要求测试放 `tests/integrator/`、§11 要求 `skills/integrator/SKILL.md`（七要素齐全）；但 `contracts/file_ownership.json` 的 `modules.integrator.owns` 无 `skills/**`、无 `tests/integrator/**`，且 `tools/task_pack_check.py` 断言「integrator 无 Skill.md（角色而非模块）」 | `tools/gen_task_packs.py` 为 `integrator` 增加专门分支：§9 指向 `tests/integration/`，§11 去掉 `SKILL.md`/`references/` 两行、改为「集成验收报告 + 集成测试 + 交接记录」，并复用 `modules.integrator.owns` 作为白名单 | `tools/gen_task_packs.py`、`tasks/TASK-INTEGRATE-01.md`（重新生成）、后续任何 `integrator` 角色任务包 | non-blocking（本次已按所有权登记执行，未越界） |

---

## 12.6 自我约束核查

- [x] **只改了白名单内的文件** —— `git status --porcelain --untracked-files=all` 仅显示 4 个文件：
      `docs/integration_report.md`（新）、`docs/parallel_execution_plan.md`（改）、
      `tests/integration/run_tests.py`（新）、`tests/integration/module_handoff.json`（新）。
      白名单 = `contracts/file_ownership.json` 的 `modules.integrator.owns`
      = `docs/integration_report.md`、`docs/parallel_execution_plan.md`、
      `tests/fixtures/**`、`tests/integration/**` —— 4 个文件**全部命中**。
      已用脚本逐文件核对，输出 `ALL IN WHITELIST: True`、
      `forbidden-path modifications: none`。
- [x] **未修改公共契约** —— `contracts/**`、`manifest.json`、`PROJECT_RULES.md`、
      `AGENT_COLLABORATION.md`、`tasks/**`、`tests/test_plan.md` 均未动
      （`git status` 无相关条目）。
- [x] **未修改他人拥有的文件** —— `skills/**`、`rules/**`、`lexicon/**`、
      `tools/**`、`scripts/**`、`tests/fixtures/**`、`tests/shopee-br-*/**` 均未动。
- [x] **引文核验通过** —— `env -u LD_LIBRARY_PATH python3 tools/verify_citations.py`
      → `50/50 excerpts verified verbatim, 0 failed`（并在集成脚本内作为 V4 断言复跑一次）。
- [x] **自有测试实际执行** —— `env -u LD_LIBRARY_PATH python3 tests/integration/run_tests.py`
      → `PASSED: 218   FAILED: 0`，退出码 **0**，输出已贴在 §12.2 ①。
      另实跑 7 个模块的自测（§12.2 ③）与 `scripts/check_all.sh`（§12.2 ②，退出码 **0**）。
      **没有**未执行却标记为通过的测试；未执行的三项及其原因已列在 §12.2 末尾。
- [x] **SKILL.md 七要素齐全** —— **不适用**：`integrator` 是角色而非 Skill 模块，
      按 §12.2 末尾的说明与 §12.3 #7 处理（已登记为契约变更建议 S4）。
- [x] **references/ 内容已填实（无占位符）** —— **不适用**（无 `references/`）。
      `docs/integration_report.md` 的每一处数字均来自实际执行输出，无占位符。
- [x] **硬约束 H1–H6 已逐条自查** —— 全链路 80 条 `AuditResult` 逐条断言：
      H1（19 条 IP 结论全为 `signal` + 人工复核，**0 违反**）、
      H2（8 条阻断类动作的来源层级全为 `platform_official`/`law`，**0 违反**）、
      H3（64 条带 `unevaluated` 的结论**无一条**判 `PASS`）、
      H4（50/50 引文逐字核验通过）、
      H5（证据引用 0 处凭证特征、0 处内嵌长内容）、
      H6（`freeze_relist`/`escalate_legal` 恒带人工复核；全模块源码 0 处线上处置入口）。
- [x] **未执行任何线上处置** —— 全程只读输入、只写产出文件；
      集成脚本以源码扫描断言六个模块均无 `publish_listing` / `delist_product` /
      `unfreeze_listing` / `submit_appeal` / `requests.post` / `urllib.request` 入口。
- [x] **未执行 `git commit` / `git push`** —— 提交由主 Agent 统一执行。
