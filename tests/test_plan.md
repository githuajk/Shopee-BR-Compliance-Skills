# SBRCA 统一测试与集成验收标准

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-TEST-001` |
| 版本 | 1.0.0 |
| 状态 | **Frozen — 已冻结** |
| 冻结日期 | 2026-10-27 |
| 适用范围 | 全部模块的测试要求、共享夹具、集成验收门槛 |
| 相关文档 | `PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、`contracts/risk_action_matrix.json`、`tasks/task_registry.json` |

---

## 1. 原则

| 原则 | 说明 |
|---|---|
| **真实性** | **没有真实执行的测试，不得标记为通过。** 交付时必须贴出实际命令与输出 |
| **可复现** | 固定夹具；随机成分固定种子；无网络依赖 |
| **可独立** | 模块测试不依赖其他模块的运行时产物；共享夹具只读 |
| **误报优先** | 误封正常商品的代价 > 漏检一个风险商品的代价 |
| **边界显式** | 缺失数据不是「通过」；未评估必须可见 |
| **契约内** | 测试断言以契约为准，不以实现细节为准 |

---

## 2. 测试层级

| # | 层级 | 范围 | 位置 | 责任方 |
|---|---|---|---|---|
| L1 | 单元测试 | 单函数、单规则分支 | `tests/<module>/` | 各模块 |
| L2 | 契约测试 | 输出符合 `audit_result` 契约 | `tests/<module>/` | 各模块 |
| L3 | 规则测试 | 每规则正例 + 反例 | `tests/<module>/` | 各模块 |
| L4 | 硬约束测试 | H1–H6 断言 | `tests/<module>/` | 各模块 |
| L5 | 集成测试 | 多模块结果整合 | `tests/shopee-br-compliance/` | 主 Skill |
| L6 | 端到端 | 输入文件 → 最终结论 | `tests/shopee-br-compliance/` | 主 Skill |
| L7 | 冲突/重复检查 | 跨模块规则 ID、语义、职责 | 集成阶段 | 集成 Agent |

**各模块至少交付 L1–L4。** L5–L6 由主 Skill 交付，L7 由集成 Agent 交付。

---

## 3. 硬约束断言（L4）

这些断言在**每个模块**都必须有对应测试。

| ID | 断言方式 | 失败信息 |
|---|---|---|
| **H1** | 构造 IP 类输入，断言输出中所有 `category ∈ {ip_trademark, ip_copyright, ip_design, ip_patent}` 的结果 `confidence == "signal"` 且 `requires_human_review == true` | 「IP 结论未标记为 signal」 |
| **H2** | 构造 `source.tier ∈ {internal_risk, unverified}` 的规则，断言其 `action` 不为 `block`/`freeze_relist`/`escalate_legal`；构造 `status != "active"` 的规则同理 | 「非权威规则产生了阻断类动作」 |
| **H3** | 构造缺失必需输入字段的输入，断言输出 `unevaluated` 非空且对应规则**未**产生 result；断言 `errors[]` 含 `stage == "rule_evaluation"` 的 warning | 「缺失输入被当作通过」 |
| **H4** | 对本模块全部 `active` 规则跑 `tools/verify_citations.py`，断言 0 失败 | 「引文核验失败」 |
| **H5** | 断言所有 `evidence_refs[].artifact_ref` 不含凭证特征（`sk-`、`ghp_`、长 base64、文件内容片段） | 「证据引用内嵌了凭证内容」 |
| **H6** | 断言 `action ∈ {freeze_relist, escalate_legal}` 的结果 `requires_human_review == true`，且模块不提供任何执行该动作的入口 | 「human_only 动作缺少人工复核标记」 |

---

## 4. 规则测试（L3）

### 4.1 每条规则两个用例

| 用例 | 断言 |
|---|---|
| **正例** | 命中该规则；`action` 与 `severity` 符合规则声明；`rule_refs` 含该 `rule_id` |
| **反例** | **不**命中该规则（防规则过宽） |

**反例来源**：共享夹具的正常商品池；若找不到合适反例，说明该规则可能过宽 → 在交付的「未解决问题」中登记。

### 4.2 覆盖度检查

```bash
# 规则总数
env -u LD_LIBRARY_PATH python3 -c "
import json,glob
n=sum(len(json.load(open(f,encoding='utf-8'))['rules']) for f in glob.glob('rules/*.json'))
print(n)
"
```

集成验收要求：**每条 `active` 规则有 ≥1 正例 + ≥1 反例**，覆盖率 100%。

---

## 5. 共享夹具

### 5.1 位置与所有权

`tests/fixtures/` —— **集成 Agent 拥有**。模块只读，需要新夹具 → 提建议。

### 5.2 夹具分类

`tests/fixtures/` —— **集成 Agent 拥有**。模块只读，需要新夹具 → 提建议。

| 文件 | 内容 | 用途 | 现状 |
|---|---|---|---|
| `normal_products.json` | 正常商品池 | 规则的**反例**来源 | 12 件 |
| `violation_products.json` | 明确违规商品 | 规则的**正例**来源 | 39 件 |
| `edge_cases.json` | 边界（兼容性描述、模板化详情、夸大宣称但合规的表述） | 防过宽 | 12 例 |
| `missing_data_cases.json` | 资料缺失（缺图片/类目/品牌/授权） | H3 测试 | 6 例 |
| `case_history.json` | 历史案件样本（已删除/暂停/整改中/已结案） | 重发与冻结测试 | 7 件 |
| `ip_cases.json` | IP 场景（品牌宣称/指示性使用/图片 logo/授权缺失） | H1 测试 | 7 例 |
| `injection_cases.json` | 提示注入样本 | 安全测试 | 5 例 |

**全部为合成数据**，不含任何真实商品或店铺信息。

### 5.3 夹具注解与机械校验

夹具记录上可带三个**注解字段**（不是商品/案件契约的一部分，校验 Schema 前会剥离）：

| 字段 | 出现在 | 含义 |
|---|---|---|
| `targets` | `normal_products.json` | 这些规则**必须不命中** |
| `targets_exempted` | `normal_products.json` | 这些规则**允许命中** —— 用于豁免路径反例（如 IP-006 兼容性豁免必须与 IP-001 同时命中） |
| `note` | 全部 | 该夹具针对哪条规则、期望什么结论 |

用例级夹具（`edge_cases` / `ip_cases` / `injection_cases` / `missing_data_cases`）用
`must_fire` / `must_not_fire` / `must_be_unevaluated` 声明期望。

> **注解必须被机械校验，否则会随规则演进而静默失效。**
> 校验命令：
>
> ```bash
> env -u LD_LIBRARY_PATH python3 tools/verify_fixtures.py
> ```
>
> 当前基线：**108 条夹具-规则断言**（58 应命中 / 50 应不命中）全部通过。
> 规则一改，夹具没跟着改，这个工具立刻报错并点名具体夹具与规则。

### 5.4 构造原则

| 原则 | 说明 |
|---|---|
| 合成优先 | 不复制真实商品到项目目录 |
| 覆盖真实形态 | 模拟真实 xlsx 的 6 行 banner + 表头结构 |
| 正反成对 | 每个违规样本配一个「看起来像但合规」的对照 |
| 可归因 | 每个夹具说明它针对哪条规则、期望什么结论 |

### 5.5 高误报来源（必须作为反例）

来自历史经验，这四类是本项目最容易踩的坑：

| 来源 | 现象 | 处置 |
|---|---|---|
| 店主 2026-09 审阅 | 491 个详情完全相同（模板化） | 跨商品详情相似度 → 独立规则 |
| chongyang1 | 57 处触线命中全为误报（`reduzir` 46 / `desconforto` 4 / `seguro` 1） | 关键词命中必须带上下文判定 |
| zzj-02 | 兼容性描述被误判侵权 | `SBR-IP-006` 反误判规则 |
| 原型首版 | 15/15 全被判违规（输入缺列） | `requires_input` + 未评估上报 |

---

## 6. 集成验收标准（L5–L7）

由**集成 Agent** 在 `TASK-INTEGRATE-01` 执行。全部通过才算集成完成。

### 6.1 冲突检查

| # | 检查 | 通过标准 |
|---|---|---|
| C1 | 跨模块规则 ID 冲突 | 0 个 ID 被两个模块定义 |
| C2 | 规则语义冲突（同 ID 不同含义） | 0 处 |
| C3 | 职责重叠（两模块声明同一职责） | 0 处 |
| C4 | 重复实现（同一逻辑两处） | 0 处 |
| C5 | 规则文件归属与前缀一致 | `rules/03` 已拆分，0 个文件仍含多 owner 前缀 |
| C6 | 证据类型词表一致 | 各模块使用的 `evidence_type` 均在 `contracts/evidence_reference.schema.json` 的示例集合内或已扩充该 Schema |

### 6.2 接口一致性

| # | 检查 | 通过标准 |
|---|---|---|
| I1 | 各模块输出通过 `audit_result` 契约校验 | 100% |
| I2 | 各模块 `module` 字段取值合法 | 100% |
| I3 | 主 Skill 能解析全部模块输出 | 端到端用例通过 |
| I4 | 契约中声明的必填字段无模块遗漏 | 100% |
| I5 | 无模块引入契约外的必填字段 | 0 处 |
| I6 | `assumptions` / `known_gaps` 非空 | 100% 交接记录 |

### 6.3 硬约束集成验证

| # | 检查 | 通过标准 |
|---|---|---|
| V1 | 全量结果的 H1 断言 | 0 违反 |
| V2 | 全量结果的 H2 断言 | 0 违反 |
| V3 | 全量结果的 H3 断言 | 0 违反 |
| V4 | 引文逐字核验 | 100% 通过 |
| V5 | 敏感信息扫描 | 0 命中 |
| V6 | 规则正/反例覆盖 | 100% |

### 6.4 聚合行为

| # | 检查 | 通过标准 |
|---|---|---|
| A1 | 多模块结果聚合的 verdict 取最重 | 符合 `risk_action_matrix.verdict_aggregation` |
| A2 | 聚合保留最细粒度的 action | `require_evidence` 不退化为 `flag_for_review` |
| A3 | 未评估项与阻断项分区呈现 | 报告中有独立小节 |
| A4 | 确定性结论不被 AI 结论降级 | 断言通过 |
| A5 | IP 结论在最终结果中仍为 signal | 断言通过 |

---

## 7. 执行方式

### 7.1 模块自测

```bash
# 单模块
env -u LD_LIBRARY_PATH python3 tests/<module>/run_tests.py

# 引文核验（全库）
env -u LD_LIBRARY_PATH python3 tools/verify_citations.py

# 契约校验
env -u LD_LIBRARY_PATH python3 tools/validate_json.py \
    --schema contracts/audit_result.schema.json tests/<module>/
```

### 7.2 集成验收

```bash
env -u LD_LIBRARY_PATH python3 tools/integration_check.py
```

> 该脚本由集成 Agent 在 `TASK-INTEGRATE-01` 中实现，负责 C1–C6、I1–I6、V1–V6、A1–A5 的自动化断言。

---

## 8. 测试真实性要求

| 规则 | 说明 |
|---|---|
| 必须贴命令与输出 | 交付说明 §12.2 |
| 未执行必须写明 | 「未执行」+ 原因，不得留空 |
| 不得用「应该通过」代替实际运行 | 措辞审查 |
| 失败必须报告 | 不得隐瞒失败用例 |

**违反此要求的任务直接判定为不通过。**

---

## 9. 现有基线（实测）

**执行日期**：2026-10-27
**命令**：`env -u LD_LIBRARY_PATH bash scripts/check_all.sh`
**环境**：Python 3.14.4 / Linux 6.12.111 / Hermes 托管运行时

```
== 0/5  框架自检（并行开发框架不变量）==
PASSED: 303   FAILED: 0

== 1/5  公共契约校验（contracts/）==
契约校验 — 通过 18，失败 0

== 2/5  规则库 + 词库 Schema 校验 ==
0 errors, 0 warnings
0 errors, 0 warnings

== 3/5  引文逐字核验（无编造引文）==
50/50 excerpts verified verbatim, 0 failed

== 4/5  共享夹具校验 ==
validated 9 products, 3 cases across 8 scenarios

== 5/5  任务包与所有权一致性 ==
PASSED: 566   FAILED: 0

ALL CHECKS PASSED
```

**其他校验**：

| 校验 | 结果 |
|---|---|
| `tools/validate_json.py`（6 份既有 Schema） | 0 错误 0 警告 |
| `tools/verify_citations.py` | 50/50 通过 |
| `tools/validate_fixtures.py` | 9 商品 / 3 案件 / 8 场景合法 |
| 契约自洽校验 | 6 份契约加载通过；`risk_action_matrix` 实例 PASS |
| 规则 → `rule_envelope` 符合性 | 50/50 |

> **上表是本框架的框架级校验，不是模块测试。**
> 早期版本此处记录过第一阶段原型的 `tests/run_tests.py`（333 项）基线 ——
> 该原型代码**已于 2026-10-27 归档入库**于 `.archive/phase0_prototype/`
> （结论变更见 `.archive/README.md` §2.1），其 `tests/run_tests.py` 不在活跃校验
> 流程中，故本节不再引用该基线。
> 模块级测试（L1–L4）在各自任务中建立，见 §2。

---

## 10. 变更记录

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| 1.0.0 | 2026-10-27 | 初版并冻结 | 技术负责人（Agent） |
