# 续做说明 —— G3 两项未完成模块

| 字段 | 值 |
|---|---|
| 日期 | 2026-10-27 |
| 状态 | **TASK-LISTING-01 与 TASK-IP-01 部分完成，待续做** |
| 原因 | 子 Agent 因 Token Plan 用量上限（HTTP 429）中止 |
| 已入库 | commit `2f156c6`（部分产出）、`b6fd3a9`（注册表与 README 同步） |
| 续做方式 | 从磁盘现状接着做，**不要重写已有文件** |

---

## 1. 当前进度一览

| 任务 | 模块 | 状态 | 自有测试 |
|---|---|---|---|
| TASK-FRAME-01 | — | ✅ 完成 | — |
| TASK-FRAME-02 | — | ✅ 完成 | — |
| TASK-POLICY-01 | `shopee-br-policy-research` | ✅ 完成 | 1467 项通过 |
| TASK-INGEST-01 | `shopee-br-data-ingestion` | ✅ 完成 | 201 项通过 |
| TASK-DUP-01 | `shopee-br-duplicate-detection` | ✅ 完成 | 587 项通过 |
| TASK-REPORT-01 | `shopee-br-reporting` | ✅ 完成 | 210 项通过 |
| **TASK-LISTING-01** | `shopee-br-listing-audit` | 🔶 **部分完成** | ❌ 失败（`KeyError: 'product'`） |
| **TASK-IP-01** | `shopee-br-ip-review` | 🔶 **部分完成** | ❌ 未开始（无测试文件） |
| TASK-MAIN-01 | `shopee-br-compliance` | ⬜ 未开始 | — |
| TASK-INTEGRATE-01 | — | ⬜ 未开始 | — |

注册表：`tasks/task_registry.json` → `summary: completed=6, pending=4`

---

## 2. TASK-LISTING-01 —— 商品内容合规审核

### 已有产出（勿重写）

```
skills/shopee-br-listing-audit/SKILL.md
skills/shopee-br-listing-audit/references/audit_semantics.md
skills/shopee-br-listing-audit/src/sbr_listing_audit/__init__.py
skills/shopee-br-listing-audit/src/sbr_listing_audit/conditions.py
skills/shopee-br-listing-audit/src/sbr_listing_audit/engine.py
skills/shopee-br-listing-audit/src/sbr_listing_audit/fields.py
skills/shopee-br-listing-audit/src/sbr_listing_audit/lexicon.py
skills/shopee-br-listing-audit/src/sbr_listing_audit/matrix.py
skills/shopee-br-listing-audit/src/sbr_listing_audit/pipeline.py
skills/shopee-br-listing-audit/src/sbr_listing_audit/rules.py
skills/shopee-br-listing-audit/src/sbr_listing_audit_cli.py
tests/shopee-br-listing-audit/fixtures/listing_audit_rule_cases.json
tests/shopee-br-listing-audit/run_tests.py
```

各文件职责：

| 文件 | 职责 |
|---|---|
| `conditions.py` | 条件求值 |
| `engine.py` | 规则引擎 |
| `fields.py` | 字段提取 |
| `lexicon.py` | 词库匹配（对接 `tools/scan_lexicon.py`） |
| `matrix.py` | 契约矩阵只读视图 |
| `pipeline.py` | 编排 |
| `rules.py` | 规则装载 |

### 当前阻塞点

```bash
$ env -u LD_LIBRARY_PATH python3 tests/shopee-br-listing-audit/run_tests.py
KeyError: 'product'
...
- 注入的 internal_risk 规则被加载: ['SBR-LV-007']
- 注入样本 INJ-01 未产生阻断类动作: block
EXIT: 1
```

两个症状：

1. **`KeyError: 'product'`** —— 规则条件或夹具期望的字段名与引擎实际产出的字段名不一致。
   先确认 `rules/03_listing_violations_duplicates.json` 里 `LV-*` 规则的
   `trigger` 引用了哪个字段，再对齐 `fields.py` 的产出。
2. **INJ-01 产生了 `block`** —— 注入样本（`tests/fixtures/injection_cases.json`）
   本应是**筛查信号**，却产出了阻断类动作。违反硬约束 H1（IP 类恒为
   `signal` + 人工复核）与 H2（只有 `platform_official` / `law` 的
   `active` 规则能 `block`）。`SBR-LV-007` 是 `internal_risk` 层级 ——
   按矩阵它**不该**能产出 `block`。查 `matrix.py` 的 tier→action 上限。

### 续做步骤

1. 跑测试定位 `KeyError` 的具体位置（栈回溯指到 `conditions.py` 还是 `engine.py`）
2. 修字段名对齐
3. 修 `internal_risk` 层级产出 `block` 的问题（查 `matrix.py`）
4. 补 `DELIVERY.md`（文件清单 / 测试真实输出 / 未解决问题 / 依赖说明 / 契约变更建议 / 自我约束核查）
5. 确认 `SKILL.md` 的「待填内容」全部勾选、`references/` 无 TODO 占位

---

## 3. TASK-IP-01 —— 知识产权与授权风险筛查

### 已有产出（勿重写）

```
skills/shopee-br-ip-review/SKILL.md
skills/shopee-br-ip-review/src/sbr_ip_review/__init__.py
skills/shopee-br-ip-review/src/sbr_ip_review/evaluator.py
skills/shopee-br-ip-review/src/sbr_ip_review/matrix.py
skills/shopee-br-ip-review/src/sbr_ip_review/rules.py
```

**还缺**（对照 `tasks/TASK-IP-01.md` §11 交付物）：

| 交付物 | 状态 |
|---|---|
| `skills/shopee-br-ip-review/src/sbr_ip_review/` 完整实现 | 🔶 4 / 约 8 文件 |
| `skills/shopee-br-ip-review/src/sbr_ip_review_cli.py` | ❌ 缺 |
| `tests/shopee-br-ip-review/run_tests.py` | ❌ 缺 |
| `tests/shopee-br-ip-review/fixtures/` | ❌ 缺 |
| `skills/shopee-br-ip-review/references/` 4 份填实 | ❌ 缺（骨架还在，状态是 Draft） |
| `skills/shopee-br-ip-review/DELIVERY.md` | ❌ 缺 |

### IP 模块的特殊约束（最容易违反）

| 约束 | 内容 |
|---|---|
| **H1** | IP 类结论**恒为** `confidence: signal` + 强制人工复核。关键词/logo 命中只是筛查信号。仅权利人投诉、书面授权、平台投诉通知可确立侵权 |
| **H2** | 只有 `platform_official` / `law` 的 `active` 规则能产出 `block` |
| **H3** | 缺失必需输入必须记入 `unevaluated[]`，不得判通过 |
| **H4** | `source.excerpt` 必须是 `research/raw/` 抓取件里的**逐字原文**（`tools/verify_citations.py` 核验） |

**指示性使用豁免**（Lei 9.279/1996 art. 132 II）—— `SBR-IP-006`
（`severity: info` / `decision: allow`）命中时应**覆盖** `SBR-IP-001` 的
品牌词命中。「Compatível com Ford Focus 2015-2020」是指示性使用，
不是侵权；平台针对的是把商标当商品品牌宣称。

### 参考资产

| 路径 | 内容 |
|---|---|
| `rules/02_ip_trademark_copyright.json` | IP 规则（`IP` 前缀），含 `SBR-IP-001/003/006` |
| `tests/fixtures/ip_cases.json` | IP 场景夹具（最重要的输入） |
| `tests/fixtures/injection_cases.json` | 提示注入夹具（IP 关键词常被用于注入） |
| `research/raw/br_lei_propriedade_industrial_9279.txt` | 工业财产法（113KB） |
| `research/raw/br_lei_direitos_autorais_9610.txt` | 著作权法（76KB） |
| `research/raw/br_inpi_legislacao_marcas.txt` | INPI 商标立法（40KB） |
| `research/violation_codes.json` | 平台 IP 违规码：商标 `[133]`、版权 `[602]`、外观设计 `[603]` |

---

## 4. 续做时的通用约束

### 环境

```bash
# Python 的 SSL 在本环境损坏 —— 所有 python3 命令必须这样跑
env -u LD_LIBRARY_PATH python3 <script>
```

纯标准库实现，不要引入第三方依赖。可用：`zipfile`（XLSX）、`csv`、
`json`、`re`、`hashlib`、`pathlib`。

### 路径白名单（越界即任务失败）

| 任务 | 可写 |
|---|---|
| TASK-LISTING-01 | `skills/shopee-br-listing-audit/**`、`tests/shopee-br-listing-audit/**` |
| TASK-IP-01 | `skills/shopee-br-ip-review/**`、`tests/shopee-br-ip-review/**` |

**不要改**：`contracts/`、`rules/`、`lexicon/`、`tasks/`、`tools/`、
`scripts/`、`docs/`、`manifest.json`、`README.md`。

### 冻结契约

- `contracts/audit_result.schema.json` —— `verdict` 只能
  `PASS` / `REVISE` / `REVIEW` / `BLOCK`；`confidence` 只能
  `signal` / `likely` / `confirmed`
- `contracts/risk_action_matrix.json` —— `action` 查表决定，不得自造
- **不得**把 `pass` / `flag` / `not_evaluated` / `signal` 当作契约 `verdict`

### 仓库协作

**远端有另一个 Agent 在同仓库推 `main`。** 必须：

```bash
git fetch origin
git merge origin/main --no-ff    # 绝不 force-push
```

合并后**重跑完整校验** —— 合并两个分支可能让单独通过过的检查失败。

### 每阶段收尾（必做）

```bash
cd /config/dianshang/Shopee-BR-Compliance-Skills
env -u LD_LIBRARY_PATH python3 tests/<module>/run_tests.py   # 模块自测
env -u LD_LIBRARY_PATH bash scripts/check_all.sh             # 全库 10 步
```

提交由**主 Agent 统一执行**，子 Agent 不要 `git commit` / `git push`。

---

## 5. 每次提交前的自我核查

- [ ] 模块测试实际跑过，**输出里的数字是真的**（不编造）
- [ ] `SKILL.md` 七要素齐全，「待填内容」全部勾选
- [ ] `references/` 无 TODO / 占位符
- [ ] `source.excerpt` 逐字来自 `research/raw/` 抓取件
- [ ] `source.last_verified` 填了核查日期
- [ ] H1–H4 逐条自查（IP 模块重点查 H1）
- [ ] 只改了白名单内的路径
- [ ] `DELIVERY.md` 写明未解决问题与依赖
- [ ] `scripts/check_all.sh` 全绿
