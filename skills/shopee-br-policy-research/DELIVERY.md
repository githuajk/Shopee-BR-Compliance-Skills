# TASK-POLICY-01 交付说明

> 任务：`TASK-POLICY-01` —— 官方政策研究与来源核查
> 模块：`shopee-br-policy-research`
> 契约版本：1.0.0
> 交付日期：2026-10-27

---

## 1. 文件清单

| 路径 | 动作 | 说明 |
|---|---|---|
| `skills/shopee-br-policy-research/SKILL.md` | 修改 | 七要素齐全；状态改为「已实现」；补来源层级与动作上限表、失败处理、测试矩阵、工作区与域名变体约定 |
| `skills/shopee-br-policy-research/references/source_registry.md` | 修改 | 填实：清单结构、17 条来源全表、tier 分层、域名变体处理、抓取报告同步要求、维护流程 |
| `skills/shopee-br-policy-research/references/violation_codes.md` | 修改 | 填实：106 条码的结构、严重度映射表、处罚点交叉表、9 个 category、码号重复的原因、与规则前缀的对应 |
| `skills/shopee-br-policy-research/references/citation_verification.md` | 修改 | 填实：核验算法、宽松匹配的边界、什么算逐字、7 类常见失败原因与处置 |
| `skills/shopee-br-policy-research/references/platform_policy_summary.md` | 修改 | 填实：禁限售、2026-08-06 Anvisa 新规、处罚点机制、封禁vs下架、IP 四类、消费者保护、类目、账号主体 |
| `research/sources.json` | 修改 | 补登 3 条未登记的来源；2 条 Anvisa 抓取失败来源标注 `capture_status` |
| `research/edu_articles.json` | 修改 | 修正 `shopee_br_ip_complaint` → `shopee_br_categoria_correta`（slug 与 article 2820 实际标题不符） |
| `research/raw/_fetch_report.json` | 修改 | 对齐 12 条 `text_chars` 与实际文件（此前记为占位值 20） |
| `research/raw/_edu_fetch_report.json` | 修改 | 同一条 slug 修正；`mudanca_conta_cpf_cnpj` 状态由超时改为 ok（重抓已成功） |
| `tools/check_sources.py` | 新增 | 来源清单 ↔ 抓取件 ↔ 抓取报告 ↔ 规则引用 的一致性校验 |
| `tests/shopee-br-policy-research/run_tests.py` | 新增 | 1467 项断言，L1–L8 |

**未改动**：`rules/**`（只读引用）、`research/raw/*.txt`（抓取件是证据，不改）。

## 2. 测试结果

### 2.1 模块自有测试

```bash
$ env -u LD_LIBRARY_PATH python3 tests/shopee-br-policy-research/run_tests.py
```

实际输出：

```
==============================================================
shopee-br-policy-research 模块测试
仓库根: /config/dianshang/Shopee-BR-Compliance-Skills
==============================================================

=== L1 来源清单结构 ===
=== L2 抓取件 ===
=== L3 抓取报告与实际一致 ===
=== L4 规则引用的来源 ===
=== L5 平台违规码目录 ===
=== L6 未公开数值与占位文本 ===
=== L8 教育中心文章登记 ===
=== L7 校验工具可执行 ===

==============================================================
PASSED: 1467   FAILED: 0
全部测试通过。
```

**退出码 0。**

### 2.2 新增校验工具

```bash
$ env -u LD_LIBRARY_PATH python3 tools/check_sources.py
核对 17 条来源，17 个抓取件
  抓取失败（已登记，不得用于支撑规则）：2 条
    - br_anvisa_publicidade_medicamentos
    - br_anvisa_medicamentos_prescricao
来源清单与抓取件一致。
```

**退出码 0。**

### 2.3 全项目校验

```bash
$ env -u LD_LIBRARY_PATH bash scripts/check_all.sh
```

实际输出（摘要）：

```
PASSED: 298   FAILED: 0      框架自检全部通过。
契约校验 — 通过 19，失败 0
PASSED: 266   FAILED: 0      词库校验通过
0 errors, 0 warnings
0 errors, 0 warnings
50/50 excerpts verified verbatim, 0 failed
来源清单与抓取件一致。
全部规则的正则可编译，且无逻辑自指缺陷。
validated 90 products, 10 cases across 8 scenarios + shared fixtures
校验 108 条夹具-规则断言：58 应命中、50 应不命中
PASSED: 589   FAILED: 0      任务包与所有权一致性全部通过。
ALL CHECKS PASSED
```

**退出码 0。** 校验流程从 8 步扩到 **9 步**（新增「来源清单与抓取件一致」）。

### 2.4 守卫的故障注入验证

新工具的每条检查都做了故障注入，确认能抓到问题：

| 注入 | 结果 |
|---|---|
| 从 `sources.json` 删掉一条来源登记 | `EXIT 1` —— 报「孤儿抓取件 research/raw/shopee_br_categoria_correta.txt —— sources.json 未登记，该抓取件无法被任何规则引用」 |
| 把 3 条 MED 规则的 `source_url` 指向抓取失败的 Anvisa 来源 | `EXIT 1` —— 逐条报「引用了抓取失败的来源 …… 引文无法核验，该规则必须改用其它已核验来源」 |

注入后均已恢复原状。

### 2.5 未执行的测试

| 测试 | 原因 |
|---|---|
| 重新抓取官方页面 | 环境无可靠网络访问。**不重新抓取**是本任务的设计约束 —— `research/raw/` 下的 17 份抓取件是既有证据 |
| 2 条 Anvisa 来源的引文核验 | 抓取失败（HTTP 503），无抓取件可核验。已登记，且**不被任何规则引用**（由 `check_sources.py` 强制） |

## 3. 未解决问题

| # | 问题 | 影响 | 建议 |
|---|---|---|---|
| 1 | 2 条 Anvisa 来源抓取失败（HTTP 503） | 无法引用 `Resolução-RE nº 3.056/2026` 原文 | 网络恢复后重抓。期间 `SBR-MED-002` 改用 Shopee 官方文章（该文章逐字引用了这项授权）支撑 |
| 2 | `_fetch_report.json` 记的是字节数，字段名叫 `text_chars` | 字段名与实际单位不符 | 下次抓取时统一为字符数；当前已把值对齐到实际文件大小 |
| 3 | `violation_codes.json` 中 `fulfillment` 类（不发货 `[103]`）无对应规则 | 该类违规不在本库覆盖范围 | 属范围决策，非缺陷。若要覆盖需新开规则前缀 |
| 4 | 抓取报告只有 2 份（帮助中心 / 教育中心），无统一索引 | 新增来源时要手工决定写进哪份 | 下次抓取时合并为单一报告 |
| 5 | 未做「政策变更检测」 | 平台政策更新后无法自动发现 | 需要定期重抓 + 对比 `last_verified`。本任务只保证「已抓取的来源是准确的」 |

## 4. 依赖说明

- **我依赖的**：无。可与 `shopee-br-data-ingestion` 并行。
- **我期待下游提供的**：各专业模块用我维护的 `source` 字段填规则信封；
  新增规则时引用 `research/violation_codes.json` 里的 `platform_code` 与严重度。
- **我对其他模块的影响**：我决定规则的**来源可信度** ——
  引文核验不过的规则不得 `active`；抓取失败的来源不得支撑任何规则。

## 5. 契约变更建议

**无。**

一条**使用说明**（非变更请求）：`contracts/audit_result.schema.json` 的
`source.platform_code` 与 `source.article_id` 不是必填，但本项目建议填 ——
它们让「从一条结论回到平台原文」变成一次查表。

## 6. 自我约束核查

- [x] 只改了白名单内的文件（`skills/shopee-br-policy-research/**`、`tests/shopee-br-policy-research/**`、`research/**`）
- [x] 未修改公共契约（`contracts/**`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、`manifest.json`、`tasks/**`、`tests/test_plan.md`）
- [x] 未修改他人拥有的文件（`rules/**`、`lexicon/**`、`tests/fixtures/**`、`docs/**`）
- [x] 未修改 `research/raw/*.txt` 抓取件（证据不可变）
- [x] 引文核验通过（全库 50/50 保持通过）
- [x] 自有测试实际执行（1467 项全通过，输出见 §2.1）
- [x] `SKILL.md` 七要素齐全
- [x] `references/` 内容已填实（无占位符）
- [x] 硬约束 H1–H6 已逐条自查（H2 的 tier→action 上限、H4 的逐字核验在 §5 中明确）
- [x] 未引用平台未公开的数值（L6 有专门断言）
- [x] 测试失败如实报告，未隐瞒
