# AGENT_COLLABORATION.md — 多 Agent 协作规则

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-PROJ-002` |
| 版本 | 1.0.0 |
| 状态 | **Frozen — 已冻结，任何 Agent 不得自行修改** |
| 冻结日期 | 2026-10-27 |
| 适用范围 | 参与 SBRCA 的全部 Agent（模块 Agent、集成 Agent、任务执行者） |
| 相关文档 | `PROJECT_RULES.md`、`contracts/`、`tasks/task_registry.json`、`tasks/task_template.md`、`tests/test_plan.md` |

> **命名说明**：章程要求建立 `AGENTS.md`。该文件名被宿主平台保留用于其自身的 Agent 指令注入，写入被系统拦截（保护文件）。因此本项目的协作规范落在本文件 `AGENT_COLLABORATION.md`，**内容与职责完全等同于章程所指的 `AGENTS.md`**。本文件在 `PROJECT_RULES.md` §3.1 与 `manifest.json` 中以 `agent_collaboration_doc` 字段登记，集成 Agent 视为其唯一权威副本。

---

## 0. 你是谁、你在做什么

你可能是：

| 角色 | 职责 | 产出 |
|---|---|---|
| **模块 Agent** | 独立开发一个专业模块 | `skills/<module>/**` + `tests/<module>/**` + 自有规则文件 |
| **集成 Agent** | 统一审查、合并、拆分冲突文件、维护公共契约 | 集成报告 + 契约变更 |
| **任务执行者** | 领取注册表中的单个任务并交付 | 任务说明 + 交付物 |

**共同约束**：你不是业务规则的最终批准人。发现规则存疑 → 记录并提出建议，不擅自定案。

---

## 1. 开工前必读（按顺序）

```
1. PROJECT_RULES.md                      公共工程规范（冻结）
2. AGENT_COLLABORATION.md                本文件（冻结）
3. contracts/README.md                   契约索引
4. contracts/*.schema.json               你会用到的契约
5. tasks/task_registry.json              你的任务（找自己的 TASK_ID）
6. tasks/<你的 TASK_ID>.md               任务说明
7. tests/test_plan.md                    统一测试与验收标准
```

**读完再动手。** 跳过契约直接实现是本项目最常见的失败原因。

---

## 2. 你的任务从哪来

`tasks/task_registry.json` 是唯一任务来源。每个任务有：

| 字段 | 说明 |
|---|---|
| `task_id` | 唯一标识 |
| `module` | 归属模块 |
| `title` | 任务名 |
| `allowed_paths` | **允许修改的路径**（白名单） |
| `readonly_paths` | 需要读但不得改的路径 |
| `depends_on` | 前置任务 |
| `blocks` | 本任务完成后解锁的任务 |
| `parallel_group` | 同组可并行 |
| `acceptance` | 验收标准 |
| `deliverables` | 必交付物 |

**只允许修改 `allowed_paths` 内的文件。** 越界即任务失败。

---

## 3. 工作区隔离

### 3.1 独立工作目录

每个 Agent 在**独立分支**或**独立工作目录**中工作。

推荐（Git 分支）：

```bash
git switch -c task/<TASK_ID>
```

无 Git 时（当前状态：工作区无仓库），用独立目录：

```
/tmp/sbrca_work/<TASK_ID>/
```

**在开始前声明你的工作区路径**，并在交付说明中写明。

### 3.2 禁止

- 在其他 Agent 的工作区里改文件
- 在主工作区直接改动自己拥有的文件后再让集成 Agent 去猜哪些是你的
- 两个 Agent 并发写同一路径

---

## 4. 硬约束（违反即任务不通过）

| # | 约束 |
|---|---|
| C1 | **不得修改公共契约** —— `PROJECT_RULES.md` `AGENT_COLLABORATION.md` `contracts/**` `manifest.json` `tasks/task_registry.json` `tasks/task_template.md` `tests/test_plan.md` |
| C2 | **不得修改非自己拥有的文件** |
| C3 | 不得编造平台政策、法律条文、来源引文、测试结果 |
| C4 | 不得声称执行了未实际执行的测试 |
| C5 | 不得假设 Skill 间存在自动调用能力 |
| C6 | 不得依赖模型内部记忆或不可访问的上下文 —— 一切通过文件契约传递 |
| C7 | IP 类结论不得使用「侵权」表述而无投诉/授权/通知支撑 |
| C8 | 不得把输入缺失当作合规通过 |
| C9 | 不得使用平台未公开的数值作为事实 |
| C10 | 不得引入 YAML/JSONL/CSV/TXT/XML 作内部正式数据源 |

### 4.1 发现契约问题怎么办

**提建议，不直接改。**

在你的交付说明中增加「契约变更建议」段：

```markdown
### 契约变更建议
- **问题**：`contracts/xxx.schema.json` 的 `yyy` 字段不足以表达 `zzz`
- **证据**：具体场景 + 复现方式
- **建议变更**：字段/枚举/约束的具体改法
- **影响面**：哪些模块受影响
- **严重度**：blocking / non-blocking
```

由集成 Agent 审查并统一修改。

---

## 5. 独立开发要求

### 5.1 模块不假设其他模块存在

你的模块**必须能独立测试**。测试时：

- 用 `tests/fixtures/` 的共享夹具（只读）
- 或在自己的 `tests/<module>/` 下建自有夹具
- **不要**依赖其他模块的运行时产物

### 5.2 依赖通过契约表达

如果你需要另一个模块的产物，你**声明期望的输入/输出格式**，而不是去调用它。声明写在 `SKILL.md` 的「依赖」段。

### 5.3 接口一致性自查

交付前确认：

- 我的输入能被下游按契约解析
- 我的输出包含契约要求的全部必填字段
- 我没有引入契约之外的新必填字段
- 我的 `assumptions` 与 `known_gaps` 如实填写

---

## 6. 规则与来源要求

### 6.1 规则条目

规则必须符合 `contracts/rule_envelope.schema.json`。

### 6.2 来源引文

| 要求 | 说明 |
|---|---|
| `source.excerpt` 逐字可核验 | 必须在 `research/raw/*.txt` 中逐字出现 |
| `source.last_verified` | 核查日期（ISO 8601） |
| `source.tier` | 如实标注；不确定用 `unverified` |
| `source.url` | 指向具体页面 |

核验命令：

```bash
env -u LD_LIBRARY_PATH python3 tools/verify_citations.py
```

**核验不通过 → 任务不通过。** 若引文确实不存在于抓取件中，不要改写成"看起来对"的版本 —— 标注 `unverified` 并在交付说明中说明。

### 6.3 禁止

- 引用平台未公开的数值（处罚点分值、OKlist 名单等）
- 把 2026-09-15 前的政策当现状（注意 2026-08-06 的非处方药政策变更）
- 把 `internal_risk` 建议表述为平台要求

---

## 7. 测试要求

### 7.1 必测

| 类别 | 要求 |
|---|---|
| 正例 | 每条规则至少 1 个触发用例 |
| 反例 | 每条规则至少 1 个**不**触发用例（防过宽） |
| 契约 | 输出通过 `contracts/audit_result.schema.json` 校验 |
| 失败路径 | 输入异常/字段缺失时的行为符合契约 |
| 硬约束 | H1（IP 恒 signal）、H2（AI 不可驱动 block）、H3（缺失不当作通过） |

### 7.2 真实性

**没有真实执行的测试，不得标记为通过。**

交付说明中必须贴出实际执行的命令与输出。无法执行的测试明确写「未执行」及原因。

### 7.3 共享夹具

`tests/fixtures/` 由集成 Agent 拥有。需要新夹具 → 提建议，不要自己改。

---

## 8. 交付格式

每个任务交付（写在你自己的 `tasks/<TASK_ID>.md` 或独立交付文件中）必须包含：

```markdown
## 1. 文件清单
| 路径 | 动作 | 说明 |
|---|---|---|

## 2. 测试结果
实际执行的命令 + 输出摘要
未执行的测试 + 原因

## 3. 未解决问题
已知缺陷 / 未实现 / 存疑

## 4. 依赖说明
- 我依赖的：
- 我期待下游提供的：
- 我对其他模块的影响：

## 5. 契约变更建议（如有）
按 §4.1 格式

## 6. 自我约束核查
- [ ] 只改了 allowed_paths 内的文件
- [ ] 未修改公共契约
- [ ] 未修改他人拥有的文件
- [ ] 引文核验通过
- [ ] 自有测试实际执行
- [ ] SKILL.md 七要素齐全
```

---

## 9. SKILL.md 必备七要素

每个模块的 `SKILL.md` 必须包含：

1. **frontmatter** —— 平台强制格式：`name`、`description`
2. **职责与非职责** —— 明确不做什么
3. **输入契约** —— 引用 `contracts/skill_input.schema.json` 并说明本模块用哪些字段
4. **输出契约** —— 引用 `contracts/audit_result.schema.json` 并说明本模块产出哪些
5. **规则来源要求** —— 本模块的规则怎么来、来源要求是什么
6. **失败处理** —— 出错时怎么办、产出什么错误
7. **测试案例与验收标准**

`description` 必须是**自包含的触发语**（这是 Skill 被选中的依据），格式：
`Use when <触发条件>. <一句话行为>.`

---

## 10. 集成 Agent 的职责

| 职责 | 说明 |
|---|---|
| 契约守卫 | 拒绝任何未经流程的公共契约修改 |
| 冲突检查 | 跨模块的规则 ID 冲突、语义冲突、职责重叠 |
| 重复检查 | 跨模块的重复规则、重复实现 |
| 接口一致性 | 各模块输出是否真的符合契约、能否被主 Skill 整合 |
| 文件拆分 | 拆分混有多模块前缀的规则文件（`03_listing_violations_duplicates.json`） |
| 验收 | 按 `tests/test_plan.md` 的集成验收标准判定 |

集成 Agent **也是**契约的唯一修改者（经流程）。

---

## 11. 冲突处理

| 情况 | 处理 |
|---|---|
| 两个模块对同一规则 ID 有不同定义 | 集成 Agent 裁定；ID 归先发布者，另一方改名 |
| 两个模块实现同一职责 | 合并职责定义，保留一个 owner，另一方改为调用方 |
| 契约不足以表达需求 | 走 §4.1 变更建议流程 |
| 模块输出无法被主 Skill 整合 | 优先修模块输出（契约内解决）；契约不够则走变更流程 |

---

## 12. 快速自查清单

交付前逐项确认：

```
[ ] 读完 PROJECT_RULES.md + AGENT_COLLABORATION.md + 我的任务说明
[ ] 只改了 allowed_paths 内的文件
[ ] 没碰公共契约
[ ] 没碰别人的文件
[ ] JSON 全部通过 Schema 校验
[ ] 引文逐字核验通过
[ ] 自有测试实际执行并贴出输出
[ ] SKILL.md 七要素齐全
[ ] assumptions / known_gaps 如实填写
```

---

## 13. 变更记录

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| 1.0.0 | 2026-10-27 | 初版并冻结（文件名为 `AGENT_COLLABORATION.md` 以避开平台保护文件） | 技术负责人（Agent） |
