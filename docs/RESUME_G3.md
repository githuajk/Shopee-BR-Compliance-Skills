# 续做说明 —— G5 进行中（最后一个任务）

> **⚠️ 此文档为 2026-10-27 快照（G3 续做起点）**，描述的是当时的中断状态。截至 2026-10-28，所有任务已全部完成（10/10），见 `docs/PROGRESS_REPORT.md` v2.1.0 / `docs/integration_report.md` v1.2.0 / `tasks/task_registry.json`。下文正文保留原状以供追溯，不作为当前状态依据。

| 字段 | 值 |
|---|---|
| 日期 | 2026-10-27 |
| 状态 | **G2 + G3 + G4 全部完成（9/10）**，TASK-INTEGRATE-01 正在开发 |
| 最近一次中断原因 | 子 Agent 因 Token Plan 用量上限（HTTP 429）中止 |
| 已入库 | 见 `git log --oneline -10`；远端 `main` 与本地同步 |

---

## 1. 当前进度

| 任务 | 模块 | 状态 | 自有测试 |
|---|---|---|---|
| TASK-FRAME-01 | — | ✅ 完成 | — |
| TASK-FRAME-02 | — | ✅ 完成 | — |
| TASK-POLICY-01 | `shopee-br-policy-research` | ✅ 完成 | 1467 项通过 |
| TASK-INGEST-01 | `shopee-br-data-ingestion` | ✅ 完成 | 201 项通过 |
| TASK-LISTING-01 | `shopee-br-listing-audit` | ✅ 完成 | 383 项通过 |
| TASK-DUP-01 | `shopee-br-duplicate-detection` | ✅ 完成 | 587 项通过 |
| TASK-IP-01 | `shopee-br-ip-review` | ✅ 完成 | 231 项通过 |
| TASK-REPORT-01 | `shopee-br-reporting` | ✅ 完成 | 210 项通过 |
| **TASK-MAIN-01** | `shopee-br-compliance` | ✅ 完成 | 107 项通过 |
| **TASK-INTEGRATE-01** | — | 🔄 **开发中（G5）** | — |

注册表：`tasks/task_registry.json` → `summary: completed=9, pending=1`

**8 个模块全部有真实可运行的 CLI 入口**（G5 的基础）：

| 模块 | CLI 入口 | 测试 |
|---|---|---|
| `shopee-br-data-ingestion` | `skills/shopee-br-data-ingestion/src/sbr_ingestion_cli.py` | 201 |
| `shopee-br-listing-audit` | `skills/shopee-br-listing-audit/src/sbr_listing_audit_cli.py` | 383 |
| `shopee-br-duplicate-detection` | `skills/shopee-br-duplicate-detection/src/sbr_duplicate_detection_cli.py` | 587 |
| `shopee-br-ip-review` | `skills/shopee-br-ip-review/src/sbr_ip_review_cli.py` | 231 |
| `shopee-br-reporting` | `skills/shopee-br-reporting/src/sbr_reporting_cli.py` | 210 |
| `shopee-br-compliance` | `skills/shopee-br-compliance/src/sbr_compliance_cli.py` | 107 |

每个模块的 `SKILL.md` 都含「输入契约」与「输出契约」章节 —— 主 Skill
必须按这些章节显式读取并驱动，**不得**假设自动调用能力。

### 1.1 各模块 CLI 参数约定**不统一**（集成时最容易踩的坑）

| 模块 | 参数 |
|---|---|
| `data-ingestion` | `--request-id` `--out-dir` + **位置参数**（输入文件） |
| `listing-audit` | `--skill-input`（必需）`--request-id` `--out-dir` |
| `duplicate-detection` | `--skill-input`（必需）`--out-dir`（**无** `--request-id`） |
| `ip-review` | `--request-id` `--out-dir` + **位置参数**（**无** `--skill-input`） |
| `reporting` | `--request-id` `--out-dir` `--result-file` `--skill-input` |
| `compliance`（主） | `--request-id` `--out-dir` `--input` `--product-file` `--result-file` `--modules` |

套错参数 → argparse 直接退出 → **该维度静默缺失**。
`skills/shopee-br-compliance/src/sbr_compliance/driver.py` 有逐角色的适配，
并有测试逐个核对这五个 `--help`。

---

## 2. 下一步：G4 —— TASK-MAIN-01（主 Skill）

主 Skill **不实现新的判定逻辑** —— 它是编排层，显式读取各模块的
`SKILL.md` 工作流并串联它们。

关键约束（来自 `AGENT_COLLABORATION.md` 与 `PROJECT_RULES.md`）：

| # | 约束 |
|---|---|
| 1 | **不假设 Skill 之间存在自动调用能力** —— 主 Skill 必须显式读取 `skills/<module>/SKILL.md` 的工作流 |
| 2 | 不得自行发明规则语义、枚举、引用 |
| 3 | 不得执行任何线上处置（发布/删除/冻结/申诉）—— 只输出建议 |
| 4 | 降级策略：模块不可用时必须显式记录 `known_gaps`，不能静默跳过 |

参考实现：`skills/shopee-br-compliance/` 已有骨架
（`skills/shopee-br-compliance/SKILL.md` +
`skills/shopee-br-compliance/references/routing.md`、
`skills/shopee-br-compliance/references/execution_workflow.md`、
`skills/shopee-br-compliance/references/integration_rules.md`、
`skills/shopee-br-compliance/references/degradation.md`），references 多数仍是骨架，
需要按真实模块实现填实。

**待确认**：`TASK-MAIN-01` 的任务包在 `tasks/TASK-MAIN-01.md`
（12 章节，自包含）。

---

## 3. 下一步：G5 —— TASK-INTEGRATE-01（集成验收）

集成阶段要跨模块验证真实串联。已有可用的真实接口：

| 模块 | CLI 入口 | 产出 |
|---|---|---|
| `shopee-br-data-ingestion` | `skills/shopee-br-data-ingestion/src/sbr_ingestion_cli.py` | `skill_input.json` / `products.json` / `audit_result.json` / `module_handoff.json` |
| `shopee-br-listing-audit` | `skills/shopee-br-listing-audit/src/sbr_listing_audit_cli.py` | 同上 |
| `shopee-br-duplicate-detection` | `skills/shopee-br-duplicate-detection/src/sbr_duplicate_detection_cli.py` | 同上 |
| `shopee-br-ip-review` | `skills/shopee-br-ip-review/src/sbr_ip_review_cli.py` | 同上 |
| `shopee-br-reporting` | `skills/shopee-br-reporting/src/sbr_reporting_cli.py` | 同上 |

集成测试应当做**真实串联**（不是模拟）：ingestion 产出 → listing-audit /
duplicate-detection / ip-review 消费 → reporting 汇总。

`shopee-br-reporting` 已在交付时做过一次真实集成
（39 条真实违规结果 → 39 目标聚合，0 错误，33 条去重规则），
该用例已固化进它的测试 —— 可作为集成阶段的起点。

---

## 4. 通用约束（续做时必读）

### 环境

```bash
# Python 的 SSL 在本环境损坏 —— 所有 python3 命令必须这样跑
env -u LD_LIBRARY_PATH python3 <script>
```

纯标准库实现。可用：`zipfile`（XLSX）、`csv`、`json`、`re`、`hashlib`、
`pathlib`。

### 路径白名单（越界即任务失败）

| 任务 | 可写 |
|---|---|
| TASK-MAIN-01 | `skills/shopee-br-compliance/**`、`tests/shopee-br-compliance/**` |
| TASK-INTEGRATE-01 | 见 `tasks/task_registry.json` 的 `allowed_paths` |

**不要改**：`contracts/`、`rules/`、`lexicon/`、`tasks/`、`tools/`、
`scripts/`、`docs/`、`manifest.json`、`README.md`。

### 冻结契约

- `contracts/audit_result.schema.json` —— `verdict` 只能
  `PASS` / `REVISE` / `REVIEW` / `BLOCK`；`confidence` 只能
  `signal` / `likely` / `confirmed`
- `contracts/risk_action_matrix.json` —— `action` 查表决定
- `contracts/module_handoff.schema.json` —— 必需字段是
  `handoff_id` / `from_module` / `to_module` / `request_id` /
  `contract_version` / `produced_at` / `assumptions` / `known_gaps`。
  **自造字段（如 `summary` / `notes`）会让校验失败** ——
  该 Schema 是 `additionalProperties: false`。

### 硬约束

| # | 内容 |
|---|---|
| **H1** | IP 类结论恒为 `confidence="signal"` + 强制人工复核。关键词/logo 命中只是筛查信号 |
| **H2** | 只有 `platform_official` / `law` 的 `active` 规则能产出阻断类动作 |
| **H3** | 缺失必需输入必须记入 `unevaluated[]`，动作升级为人工复核，**不得**判通过 |
| **H4** | `source.excerpt` 必须是 `research/raw/` 抓取件里的**逐字原文**（`tools/verify_citations.py` 核验） |
| **H5** | `evidence_refs` 只存路径，不存凭证内容 |
| **N10** | 不得引用平台未公开的数值（如处罚点分值） |

---

## 5. 仓库协作

**远端有另一个 Agent 在同仓库推 `main`。** 必须：

```bash
git fetch origin
git merge origin/main --no-ff    # 绝不 force-push
```

合并后**重跑完整校验** —— 合并两个分支可能让单独通过过的检查失败。

---

## 6. 每阶段收尾（必做）

```bash
cd /config/dianshang/Shopee-BR-Compliance-Skills
env -u LD_LIBRARY_PATH python3 tests/<module>/run_tests.py   # 模块自测
env -u LD_LIBRARY_PATH bash scripts/check_all.sh             # 全库 10 步
```

提交由**主 Agent 统一执行**，子 Agent 不要 `git commit` / `git push`。

---

## 7. 已踩过的坑（续做时注意）

| # | 坑 | 正确做法 |
|---|---|---|
| 1 | 子 Agent 自报「测试通过」不可信 | 必须自己实跑每个模块的 `run_tests.py` |
| 2 | 注入测试写成「不得产生阻断动作」 | 与夹具本意矛盾。正确测法是**对照实验**：把载荷换成**等长**中性填充再跑一次，比对命中规则集与动作 |
| 3 | 删除注入载荷会让长度型规则多命中 | `description length_lt 120` 这类规则 —— 必须等长替换，不能删除 |
| 4 | 注入的规则没被加载，断言空转 | 检查规则前缀过滤；用 `options={"rule_prefixes": (...)}` 放开 |
| 5 | `module_handoff` 自造 `summary`/`notes` 字段 | Schema 是 `additionalProperties: false`，只能用契约里的字段 |
| 6 | 未评估维度被判 PASS | H3：动作必须升级为 `flag_for_review`，risk_level 升为 `low` |
| 7 | 未知算子时只报「missing: unknown field」 | 记录条件自己依赖的字段，复核者才知道缺什么 |
| 8 | 指示性使用豁免没覆盖品牌宣称规则 | `NOMINATIVE_USE_EXEMPTED` 显式列出被覆盖的规则；豁免原因要写进 `reason` 可审计 |

---

## 8. 提交前自我核查

- [ ] 模块测试实际跑过，**输出里的数字是真的**（不编造）
- [ ] `SKILL.md` 七要素齐全，「待填内容」全部勾选
- [ ] `references/` 无 TODO / 占位符
- [ ] `source.excerpt` 逐字来自 `research/raw/` 抓取件
- [ ] H1–H5 + N10 逐条自查
- [ ] 只改了白名单内的路径
- [ ] `DELIVERY.md` 写明未解决问题与依赖
- [ ] `scripts/check_all.sh` 全绿
- [ ] 产出通过 `tools/validate_json.py` 对**真实**契约 Schema 的校验
