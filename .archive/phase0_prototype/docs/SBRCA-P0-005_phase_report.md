# SBRCA-P0-005 Phase 0 / Phase 1 阶段报告与待审批事项

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-P0-005` |
| 版本 | 1.0.0 |
| 状态 | **Draft — 提交用户审批** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | Phase 0 与 Phase 1 交付汇总、实际执行结果、待批准事项 |
| 相关文档 | `SBRCA-P0-001` ~ `SBRCA-P0-004`、`SBRCA-P1-001` ~ `SBRCA-P1-007`、`docs/adr/` |

---

## 1. 一句话结论

Phase 0 与 Phase 1 的规划工作已完成并可审阅：**14 份新治理文档 + 6 份 ADR**，需求追踪清单 52 条待审批事项 14 项（5 冲突 + 9 问题），既有实现未受任何改动，全量校验通过。

**尚未进入 Phase 2**，等待您对第 5 节 14 项待审批事项的裁定。

---

## 2. 实际执行了什么

### 2.1 只读检查（§2.1）

| 检查 | 结果 |
|---|---|
| 当前工作目录 | `/config/dianshang` |
| 项目文件夹位置 | `/config/dianshang/shopee-br-compliance-agent`（**已存在**，非新建） |
| 已有文件/子目录 | 13 个顶层项，逐项归属判定见 `SBRCA-P0-001` §3 |
| Git 仓库 | **工作区内无任何 Git 仓库**（含项目目录） |
| README / 配置 / 用户资料 | 工作区根层无；项目目录内 `README.md` 为本项目上一轮自动生成，非用户手写 |
| 初始目录清单 | 已生成（`SBRCA-P0-001` §3） |

### 2.2 历史需求恢复（§3.2）

恢复出 **4 条历史工作线**，其中 1 条是本项目直接前身：

| 线 | 时间 | 与 SBRCA 关系 |
|---|---|---|
| **合规审计线** | 2026-09-15 ~ 09-17 | ★ **直接前身**。产出 8 篇侵权政策抓取、INPI 查询指南、17 类词库文档、店主 491 条审阅反馈 |
| 详情页改写线 | 2026-08 ~ 10 | 职责不同（改写 vs 审核），但 4 条工程教训必须继承 |
| 合规扫描线 | 更早 | 尚未细读，Phase 2 前需确认与线 1 的关系 |
| 广告分析线 | 2026-10 | 无关，未纳入范围 |

**本次章程的 50 条要求全部登记为「用户已明确确认」层级**（`C-01` ~ `C-50`，逐条映射到 52 条 `REQ-*`）。

### 2.3 重新调研（§4.2 第 4 项）

- 官方规则：15 份一手抓取件已在第一阶段完成，本轮复用并交叉验证。
- **技术调研新增发现**：2026-09 历史线记录的「浏览器访问 + JS 渲染后提取 innerText」与本项目独立得出的结论**完全一致** —— 两条独立路径互证，可信度高。

### 2.4 目录评估（§4.2 第 5 项）

现有结构与治理要求的逐项比对在 `SBRCA-P0-001` §4.1。**7 项符合，5 项需补**：

| 需补项 | 处理 | 计划 |
|---|---|---|
| 既有 5 份 MD 无元信息头 | 已补 9 份新文档；剩 3 份 | 任务 2.13 |
| 决策取值与章程 4 值不一致 | 给出 3 个方案 + 建议 | 裁定项 CONF-001 |
| 缺需求编号与追踪 | 已建 52 条 | ✅ 完成 |
| 缺权限模型 | 已建七类权限矩阵 | ✅ 完成 |
| 缺 ADR | 已建 6 份 | ✅ 完成 |

---

## 3. 关键发现（需要您知道的）

### 3.1 ★ 词库数据资产已丢失

`_learning/compliance_audit/` 的文档引用了两个词库数据文件：

| 文件 | 文档声称 | 实际 |
|---|---|---|
| `risk_words.json` | 17 类 / 1,320 词「已验证」 | **不存在** |
| `risk_words_FINAL.db` | 36,372 词 / 33 分类 / SQLite + FTS5 | **不存在** |

全盘检索（`find / -xdev`）只命中两份 `.md`。`/tmp/ai-app2026-stage` 是 `_learning` 的**子集镜像**（53 文件，无独有信息，已 diff 核对）。

**影响**：章程 §4.2 的「规则及黑名单可能超过十万条」这一规模假设，**当前没有任何可用数据支撑**。词库需重建（裁定项 `Q-G`）。

### 3.2 ★ 2026-09 线有一个当前实现缺失的关键机制

该线记录的 `article/21440` 指出：**知识产权类账号冻结，只有投诉方（品牌方）撤销投诉才能重新激活**；监管机构类必须由原机构书面同意。

当前 SBRCA 的解冻逻辑只要求「关联案件关闭 + 人工审批」—— **审批通过不等于解封成功**。

是否做成硬前置条件是业务策略选择，已登记为 `Q-A`（建议方案 A：做成硬前置）。

### 3.3 ★ 规则引文编造已被工具抓到

第一阶段的 `SBR-IP-006` 引了「Art. 125. Não constitui uso indevido…」—— 该葡语**在 Planalto 原文里不存在**。真实条文是 **Lei 9.279/1996 Art. 132, II**。

已建成 `tools/verify_citations.py` 做逐字核验并纳入测试套件，**当前 50/50 通过**。这条能力已固化为 ADR-0005。

### 3.4 2026-08-06 药品政策变更

Shopee 获 Anvisa 授权卖非处方药，但**仅限持牌药店/药妆店**。早于该日期写的「药品一律禁售」规则已过时，规则库已分三条处理（`SBR-MED-001/002/003`）。

### 3.5 ⚠️ 有三项测试缺口

章程 §6.2 要求的十类测试案例中：

| 类别 | 状态 |
|---|---|
| 规则冲突案例 | ❌ 缺失（Phase 2 任务 2.12） |
| 历史删除 vs 暂停的差异化 | ⚠️ 部分（行为已实现，但缺独立断言） |
| 词库级误报反例 | ⚠️ 部分（引擎侧有断言，词库级用例待补） |

---

## 4. 交付物清单

### 4.1 Phase 0

| 文件 | 大小 | 内容 |
|---|---|---|
| `docs/SBRCA-P0-001_directory_status.md` | 11 KB | 目录现状、资产归属、缺失分析、调整建议 |
| `docs/SBRCA-P0-002_requirements_recovery.md` | 19 KB | 4 条历史线、50 条已确认要求、不可访问清单 |
| `docs/SBRCA-P0-003_requirement_register.json` | 38 KB | **52 条需求**，9 类别，含来源与验收标准 |
| `docs/SBRCA-P0-004_open_questions.json` | 18 KB | **5 冲突 + 9 问题**，各带选项/建议/默认处置 |
| `docs/RESEARCH_REPORT.md`（既有） | 17 KB | 官方规则调研（第一阶段） |

### 4.2 Phase 1

| 文件 | 大小 | 内容 |
|---|---|---|
| `docs/SBRCA-P1-001_charter.md` | 13 KB | 总章程：定位、角色、文件治理、工程规范、权限、审计 |
| `docs/SBRCA-P1-002_architecture.md` | 21 KB | 六层架构、接口契约、规模设计、依赖规则 |
| `docs/SBRCA-P1-003_data_spec.md` | 12 KB | JSON 规范、命名、ID 体系、四态语义、Schema 规范 |
| `docs/SBRCA-P1-004_security_model.md` | 13 KB | 权限矩阵、14 项威胁、GitHub 安全、审批闸门 |
| `docs/SBRCA-P1-005_test_strategy.md` | 12 KB | 九层级、十类用例、12 条不变量、基准计划 |
| `docs/SBRCA-P1-007_roadmap.md` | 11 KB | Phase 0–7 任务分解与验收门槛 |

### 4.3 ADR

| 编号 | 主题 | 状态 |
|---|---|---|
| ADR-0001 | 内部持久化格式仅 JSON+MD（SQLite 派生索引的条件） | Draft 待批 |
| ADR-0002 | 语言与依赖：默认纯标准库，逐个论证引入 | Draft 待批 |
| ADR-0003 | 确定性规则与 AI 审核分层及不可逆合并 | Draft 待批 |
| ADR-0004 | 跨记录判定采用哨兵触发 | Draft 待批 |
| ADR-0005 | 规则引文必须逐字可核验 | Draft 待批 |
| ADR-0006 | 缺失数据不等于合规：未评估项必须显式上报 | Draft 待批 |

---

## 5. 待审批事项（14 项）

完整内容见 `docs/SBRCA-P0-004_open_questions.json`。以下为摘要：

### 5.1 冲突（5 项）

| ID | 议题 | 建议 | 不答复时 |
|---|---|---|---|
| **CONF-001** | 章程要求 `PASS/REVISE/REVIEW/BLOCK`，原型用 6 值 | **A**：6 值 + 聚合标签 | A |
| **CONF-002** | 词库规模：12,500（2026 目标）vs 10 万（章程假设），且数据已丢失 | **C→A**：先基准再定 | C→A |
| **CONF-003** | 是否允许 SQLite 作派生索引 | **B**（JSON 仍是唯一权威源） | A（严格照章） |
| **CONF-004** | 是否允许第三方库 | **C**：默认标准库，逐个 ADR 论证 | A |
| **CONF-005** | 既有文档重命名与元信息补齐 | **A**：补头 + `ARCHITECTURE.md`→`implementation_notes.md` | B（不动既有文件） |

### 5.2 待确认问题（9 项）

| ID | 议题 | 建议 | 需在何时关闭 |
|---|---|---|---|
| **Q-A** | IP 解冻是否需「品牌方已撤诉」硬前置 | A（硬前置） | Phase 5 |
| **Q-B** | 店主 10 条审阅原则的固化层级 | B（可判定的做规则，其余给 AI） | Phase 3/4 |
| **Q-C** | 需求 ID 体系（章程示例 5 类 vs 现行 9 类） | B（9 类） | Phase 1 |
| **Q-D** | GitHub 预授权机制 | C→A（先验证再定型） | Phase 6 |
| **Q-E** | 仓库范围（是否纳入 `_learning/`） | A（只纳入项目目录） | Phase 6 |
| **Q-F** | 项目目录是否改名 | A（保持不变） | Phase 1 |
| **Q-G** | 词库重建来源 | A→C（从现存文档抽取 + 规则层先行） | Phase 2 |
| **Q-H** | 历史案件数据导入格式 | A（定义 Schema 人工整理） | Phase 2 |
| **Q-I** | 性能验收阈值 | A（先出基线再定） | Phase 3 |

> 每项都给了 `default_if_no_answer`。**若您不逐条答复，我将按默认执行并在报告中标注「按默认执行」。**

### 5.3 需要您提供的两项信息

| # | 需要什么 | 为什么需要 | 缺了会怎样 |
|---|---|---|---|
| 1 | **可接受的最长审核等待时间** 与 **可接受的规则库启动时间** | `Q-I` 性能门槛 | Phase 3 验收无量化标准 |
| 2 | **历史违规案件数据**（平台违规记录导出 / 通知邮件 / 手工整理） | `Q-H` 重发检测需要历史案件库 | 重发检测只能靠人工提供 `cases.json` |

---

## 6. 本轮实际改动清单

### 6.1 新增（16 个文件，全部为规划文档）

```
docs/SBRCA-P0-001_directory_status.md
docs/SBRCA-P0-002_requirements_recovery.md
docs/SBRCA-P0-003_requirement_register.json
docs/SBRCA-P0-004_open_questions.json
docs/SBRCA-P0-005_phase_report.md        ← 本文件
docs/SBRCA-P1-001_charter.md
docs/SBRCA-P1-002_architecture.md
docs/SBRCA-P1-003_data_spec.md
docs/SBRCA-P1-004_security_model.md
docs/SBRCA-P1-005_test_strategy.md
docs/SBRCA-P1-007_roadmap.md
docs/adr/SBRCA-ADR-0001_storage_format.md
docs/adr/SBRCA-ADR-0002_language_and_dependencies.md
docs/adr/SBRCA-ADR-0003_deterministic_vs_ai.md
docs/adr/SBRCA-ADR-0004_sentinel_trigger.md
docs/adr/SBRCA-ADR-0005_verbatim_citation_verification.md
docs/adr/SBRCA-ADR-0006_missing_data_vs_noncompliance.md
```

### 6.2 未改动

- `rules/` `lexicon/` `data/` `research/` `src/` `tools/` `scripts/` `tests/` —— **全部未改动**
- 既有 `docs/ARCHITECTURE.md` `docs/RESEARCH_REPORT.md` `docs/SOP.md` `docs/../prompts/` `README.md` —— **全部未改动**（mtime 仍为 10:25–10:30，本轮写入为 10:43 起）
- 工作区其他目录（`_learning/` `_ad_analysis/` `zzj-*_output/` 等）—— **未触碰**
- 未创建 Git 仓库、未初始化远程仓库、未部署服务、未连接任何生产数据

### 6.3 验证结果（本轮实跑）

```
== 1/5  JSON Schema 校验      0 错误 0 警告
== 2/5  引文逐字核验          50/50 通过
== 3/5  测试套件              PASSED: 333  FAILED: 0
== 4/5  端到端 demo           15 商品 / 6 标记 / 2 阻断 / 8 发现 / 3 未评估
== 5/5  结果 Schema 校验      0 错误 0 警告
ALL CHECKS PASSED
```

文档元信息头：**14/17 合规**（3 份既有文档待补，已登记为任务 2.13）。

---

## 7. 下一阶段（Phase 2）计划

**前置条件**：第 5 节裁定项关闭 + 提供 §5.3 的两项信息。

Phase 2 的 14 项任务已在 `SBRCA-P1-007` §5.1 分解完毕，核心是：

1. 词库重建（`Q-G`）
2. 三态语义落地到 Product/Case Schema
3. 审核结果补版本字段（`engine_version` / `ruleset_version` / `input_digest`）
4. 案件库 Schema 与目录（`Q-H`）
5. 引用完整性 / 命名合规 / 敏感信息 / 依赖环 四类检查脚本
6. 输入层加固（zip 上限、XXE 防护）
7. 基线查询接口
8. 补齐测试缺口（规则冲突用例、词库级误报用例）

**验收门槛**：见 `SBRCA-P1-007` §5.2。

---

## 8. 声明

- 本报告的每一条结论都标注了来源层级（`SBRCA-P0-002` §2.1 的 7 类）。
- 不可访问的历史资料已在 `SBRCA-P0-002` §1.1 逐项列出，**未以推测补全**。
- 性能数字均来自本轮实跑并附环境；10 万规则规模的数字**尚不存在**，已在测试策略 §4.3 明确标注不可外推。
- 规则引文 50/50 逐字核验通过，无编造。
- **未进入 Phase 2，等待您的裁定。**
