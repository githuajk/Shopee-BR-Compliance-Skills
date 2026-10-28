# SBRCA-P0-001 项目目录现状报告

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-P0-001` |
| 版本 | 1.0.0 |
| 状态 | Draft（待用户审批） |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 项目根目录与相关工作区的资产盘点、归属判定与变更保护 |
| 关联文档 | `SBRCA-P0-002` 历史需求恢复报告、`SBRCA-P0-003` 需求追踪清单、`SBRCA-P0-004` 待确认事项清单 |

---

## 1. 执行的检查动作

依 §2.1 逐项执行，全部为只读操作：

| # | 检查 | 方法 | 结果 |
|---|---|---|---|
| 1 | 确认当前工作目录 | `pwd` | `/config/dianshang` |
| 2 | 检查文件夹实际位置 | `find /config -maxdepth 3 -type d` | 项目位于 `/config/dianshang/shopee-br-compliance-agent` |
| 3 | 列出已有文件与子目录 | `find` / `ls -la` | 见 §3 |
| 4 | 检查 Git 仓库 | `find /config -maxdepth 4 -type d -name .git` | **工作区内无任何 Git 仓库**（含项目目录） |
| 5 | 检查 README / 配置 / 用户资料 | `ls /config/*.md`、`ls /config/dianshang/*.md` | 工作区根层**无** README 或配置；项目目录内有 `README.md`（见 §3 归属判定） |
| 6 | 判断用户原有内容 | 与 `session_search` 历史记录交叉比对 | 见 §3 归属判定表 |
| 7 | 生成初始目录清单 | `find` 输出快照 | §3 |

---

## 2. 关键发现：工作区根层没有项目目录

§2.1 假设「用户已经建立项目文件夹」。**实际情况是：工作区 `/config/dianshang` 根层不存在 SBRCA 项目目录。**

```
/config/dianshang/
├── .venv/                    # 既有虚拟环境
├── _ad_analysis/             # 既有：广告分析
├── _learning/                # 既有：知识沉淀（含 2026-09 合规审计线）
├── ad_analysis/              # 既有
├── chongyang1_output/        # 既有
├── tools/                    # 既有
├── zzj-02_v27_output/        # 既有
├── zzj-03_output/            # 既有
└── shopee-br-compliance-agent/   # ← SBRCA 候选目录
```

`shopee-br-compliance-agent/` 由**上一轮会话（2026-10-27，同一工作区）**创建，内容为第一阶段的本地规则引擎原型（50 条规则 / 6 份 Schema / 333 项测试 / 15 份一手抓取件）。

**结论**：项目目录已存在且内容可用，**不新建** `sbrca/` 或 `SBRCA/` 目录，避免出现两套并行目录。

---

## 3. 初始目录清单与资产归属判定

### 3.1 SBRCA 候选目录 `/config/dianshang/shopee-br-compliance-agent/`

| 路径 | 类型 | 归属 | 判定依据 |
|---|---|---|---|
| `README.md` | 文档 | **本项目原生产物**（上一轮生成） | 内容为本引擎的使用说明；非用户手写 |
| `docs/ARCHITECTURE.md` | 文档 | 本项目原生产物 | 同上 |
| `docs/RESEARCH_REPORT.md` | 文档 | 本项目原生产物 | 同上 |
| `docs/SOP.md` | 文档 | 本项目原生产物 | 同上 |
| `prompts/agent_prompt.md` | 文档 | 本项目原生产物 | 同上 |
| `rules/*.json`（5 文件 / 50 规则） | 数据 | 本项目原生产物 | 同上 |
| `lexicon/term_groups.json` | 数据 | 本项目原生产物 | 同上 |
| `data/schema/*.json`（6 份） | 数据 | 本项目原生产物 | 同上 |
| `data/samples/*` | 数据 | 本项目原生产物（**合成数据**） | 同上 |
| `research/raw/*`（15 份抓取件） | 数据 | 本项目原生产物（**第三方公开内容**） | 同上 |
| `research/violation_codes.json` | 数据 | 本项目原生产物 | 同上 |
| `src/compliance_agent/**` | 源码 | 本项目原生产物 | 同上 |
| `tools/**`、`scripts/**`、`tests/**` | 源码 | 本项目原生产物 | 同上 |
| `out/**` | 产物 | 可再生成 | 派生输出 |

**该目录内没有用户手写内容。** 全部为本项目上一轮自动生成。

### 3.2 既有工作区资产（**用户原有内容，不得修改**）

| 路径 | 内容 | 与 SBRCA 的关系 |
|---|---|---|
| `_learning/compliance_audit/` | **2026-09-15 合规审计线全套文档** | ★ 历史需求来源，见 `SBRCA-P0-002` |
| `_learning/compliance_audit/compliance_audit__侵权词库__risk_words.md` | 17 类侵权词库**文档版** | ★ 词库内容来源 |
| `_learning/compliance_audit/compliance_audit__侵权词库__USAGE.md` | 词库 SQLite 查询用法 | ★ 技术选型线索 |
| `_learning/compliance_audit/compliance_audit__侵权词库__shopee_侵权政策_官方.md` | 8 篇 Shopee 侵权政策抓取 | ★ 政策来源（2026-09 版） |
| `_learning/compliance_audit/compliance_audit__侵权词库__inpi_巴西商标_查询指南.md` | INPI 查询工具 + 5 大 NCL 类目 | ★ IP 风险核验方法 |
| `_learning/compliance_audit/compliance_audit__反馈学习__xiuyu_review_learning.md` | 店主审阅反馈 + 10 条学习原则 | ★ 审核质量基线 |
| `_learning/compliance_audit/compliance_audit__进度报告.md` | 该线进度 | ★ 阶段遗留状态 |
| `_learning/SHOPEE_MASTER_SOP.md` | 主 SOP（35 条坑） | ★ 改写侧经验，本项目只读参考 |
| `_learning/00_baseline.md` | 店铺摸底（633 商品） | ★ 规模基线参考 |
| `_learning/HISTORY.md` | 项目演化时间线 | 背景 |
| `_learning/01_repo_structure.md`、`02_risk_dictionary.md` | 仓库结构 / 风险词典 | 参考 |
| `zzj-02_v27_output/`、`zzj-03_output/`、`chongyang1_output/` | 三店改写输出 | 改写侧，非本项目范围 |
| `/tmp/ai-app2026-stage/docs/knowledge_base/` | `_learning` 的**子集镜像**（53 文件） | 无独有信息，已核对 |

### 3.3 资产缺失（重要）

`_learning/compliance_audit/compliance_audit__侵权词库__USAGE.md` 引用了两个词库数据文件：

| 引用名 | 文档声称 | 实际状态 |
|---|---|---|
| `risk_words.json` | 17 类 / 1,320 词（阶段 1 已验证） | **不存在** |
| `risk_words_FINAL.db` | 36,372 词 / 33 分类 / SQLite + FTS5（阶段 2 目标） | **不存在** |

全盘检索结果（`find / -xdev -iname "*risk_words*"`）只命中两份 `.md`，无任何 `.json` / `.db`。

**判定**：2026-09-15 那条线的**词库数据资产已丢失，只剩文档**。阶段 2 的 5 个 subagent 扩展工作（目标 12,500 词）是否完成无法证实 —— 进度报告标注为「🔄 后台」，且进度报告本身写的是「进行中」。

**影响**：§4.2 的「规则及黑名单可能超过十万条」这一规模假设，**当前没有任何可用的数据支撑**。词库需要重建。

---

## 4. 目录结构评估与调整建议

### 4.1 现有结构 vs 治理要求

| 治理要求 | 现状 | 结论 |
|---|---|---|
| §2.2 仅 JSON + MD | ✅ 全部数据为 JSON，文档为 MD | 符合 |
| §2.2 Excel 仅作输入 | ✅ `data/samples/demo_mass_update.xlsx` 是合成输入样例 | 符合 |
| §2.3 核心 JSON 有 Schema | ✅ 6 份 Schema 覆盖 rule/product/case/result/lexicon/collection | 符合 |
| §2.4 MD 文档含元信息头 | ❌ 现有 5 份 MD **无**版本号/状态/更新时间/适用范围 | **需补** |
| §2.5 英文小写下划线命名 | ✅ 符合 | 符合 |
| §3.1 需求编号与追踪 | ❌ 无 | **需建** |
| §5.5 决策取值 PASS/REVISE/REVIEW/BLOCK | ⚠️ 现为 allow/flag_for_review/require_evidence/block/freeze_relist/escalate_legal | **需映射对齐** |
| §6.3 测试层级 | ⚠️ 现有单元/Schema/引擎/解析测试；缺集成/回归/权限安全/性能基准/E2E | **需补** |
| §7.1 最小权限 | ❌ 无权限模型 | **需建** |
| §8.1 ADR | ❌ 无 | **需建** |
| §9 Phase 6 GitHub | ❌ 未开始 | 计划中 |

### 4.2 建议的目录调整（**待审批，本轮不执行**）

```
shopee-br-compliance-agent/
├── README.md                     # 保留：快速上手（指向总章程）
├── docs/
│   ├── CHARTER.md                # 新增 SBRCA-P1-001 项目总章程
│   ├── requirements.md           # 新增 SBRCA-P0-003 需求追踪清单
│   ├── architecture.md           # 新增 SBRCA-P1-002 架构设计
│   ├── data_spec.md              # 新增 SBRCA-P1-003 数据规范
│   ├── security_model.md         # 新增 SBRCA-P1-004 安全与威胁模型
│   ├── test_strategy.md          # 新增 SBRCA-P1-005 测试策略
│   ├── roadmap.md                # 新增 SBRCA-P1-007 实施路线图
│   ├── adr/                      # 新增 SBRCA-P1-006 ADR 目录
│   │   ├── ADR-0001_*.md ...
│   ├── ARCHITECTURE.md           # 保留：原型实现说明（降级为实现注记）
│   ├── RESEARCH_REPORT.md        # 保留：调研报告（补元信息头）
│   └── SOP.md                    # 保留：审核 SOP（补元信息头）
├── rules/                        # 规则库
├── lexicon/                      # 词库
├── data/
│   ├── schema/                   # JSON Schema
│   ├── samples/                  # 合成测试数据
│   └── cases/                    # 新增：历史案件库（Phase 2）
├── src/compliance_agent/         # 源码
│   ├── ingest/ engine/ report/ ai/ workflow/  # 后续阶段扩展
├── tools/ scripts/ tests/        # 工具与测试
├── research/                     # 调研原始材料
└── out/                          # 运行产物（不纳入版本管理）
```

**调整原则**：只**新增**文件与目录，不删除、不重命名既有文件。`docs/ARCHITECTURE.md` 与新的 `docs/architecture.md` 并存会造成困惑 —— 建议把旧的 `ARCHITECTURE.md` 重命名为 `docs/implementation_notes.md`（**需用户批准**，因其涉及重命名既有文件）。

---

## 5. 本轮实际改动

| 文件 | 动作 | 说明 |
|---|---|---|
| `docs/SBRCA-P0-001_directory_status.md` | 新增 | 本文档 |
| `docs/SBRCA-P0-002_requirements_recovery.md` | 新增 | 历史需求恢复 |
| `docs/SBRCA-P0-003_requirement_register.md` | 新增 | 需求追踪清单 |
| `docs/SBRCA-P0-004_open_questions.md` | 新增 | 待确认事项 |
| `docs/SBRCA-P1-*.md` | 新增 | Phase 1 治理文档 |
| `docs/adr/*.md` | 新增 | ADR |
| 既有 `rules/`、`src/`、`tools/`、`tests/`、`data/`、`research/` | **未改动** | 本轮为纯规划阶段 |

**未执行**：未创建 Git 仓库、未初始化远程仓库、未修改任何既有业务数据、未部署任何服务。

---

## 6. 尚未确定事项

1. 项目目录名是否改为 `sbrca`？（当前 `shopee-br-compliance-agent` 保持不变）
2. `docs/ARCHITECTURE.md` 是否重命名为 `implementation_notes.md`？
3. 词库数据资产丢失后，是重建（Phase 2）还是先做最小可用集？
4. 工作区既有 4 个目录（`_learning`、`_ad_analysis` 等）是否纳入本项目版本管理范围？**建议否** —— 它们是跨项目的用户资料。

## 7. 相关文档

- `SBRCA-P0-002` 历史需求恢复报告
- `SBRCA-P0-003` 需求追踪清单
- `SBRCA-P0-004` 待确认事项清单
- `SBRCA-P1-001` 项目总章程
