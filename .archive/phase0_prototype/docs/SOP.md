# SOP — Shopee BR 商品合规审核

> 面向运营与审核人员。每次审核遵循本 SOP，保证结论可复现、可追溯、可审计。

---

## 阶段 0：准备

### 0.1 确认规则库是最新的

```bash
cd /config/dianshang/shopee-br-compliance-agent

env -u LD_LIBRARY_PATH python3 tools/validate_json.py \
    --schema data/schema/rule_collection.schema.json rules/
env -u LD_LIBRARY_PATH python3 tools/verify_citations.py
env -u LD_LIBRARY_PATH python3 tests/run_tests.py
```

三条都通过才能继续。**任一失败都停下来修，不要带着坏规则库跑审核。**

### 0.2 准备输入

| 输入 | 放置位置 | 说明 |
|---|---|---|
| Shopee 导出 xlsx | 任意路径 | 保留原文件，**不要改名或编辑** |
| 历史案件 | `--cases cases.json` | 平台违规记录整理后的 JSON |
| 历史商品 | `--history-products history.json` | 用于重发比对的历史商品快照 |
| 授权材料清单 | 挂在商品的 `history.authorization_documents` / `history.missing` | 见 §4.3 |

---

## 阶段 1：运行审核

### 1.1 单店

```bash
env -u LD_LIBRARY_PATH python3 scripts/review.py \
    --input "/path/to/store_export.xlsx" \
    --shop-id SHOP1 \
    --cases cases.json \
    --history-products history.json \
    --out out/SHOP1_20261027
```

### 1.2 多店（跨店同款检测需要同一次运行）

```bash
env -u LD_LIBRARY_PATH python3 scripts/review.py \
    --input store_a.xlsx --shop-id SHOP_A \
    --input store_b.xlsx --shop-id SHOP_B \
    --input store_c.xlsx --shop-id SHOP_C \
    --out out/cross_store_20261027
```

> **跨店铺重复发布必须同一次运行**。跨店比对依赖同一份索引，分两次运行无法发现跨店同款。

### 1.3 检查摄入输出

```
parsed store_a.xlsx: 296 products, 0 errors
```

- `products` 数与导出行数对不上 → 先查 `errors`
- **有 errors 不要跳过**：解析失败的行等于**没有被审核的行**。修好输入或手工补审。

---

## 阶段 2：读报告

打开 `out/<...>/review_report.md`，按顺序读：

### 2.1 第 1 节 — 摘要

先看 `Parse errors` 与 `Unreviewed rules`（如果有）。这两个数字告诉你这次审核的**覆盖度**。

> **注意**：如果某条规则出现在「未评估」列表里，说明输入缺它依赖的字段 —— 那部分商品**没有被检查**，不是「检查过没问题」。

### 2.2 第 3 节 — 需决策的发现

这是要你做事的地方。按顺序处理：

| 决策 | 含义 | 你要做的 |
|---|---|---|
| `freeze_relist` | 冻结重发 | 查历史案件；确认是否是同一商品被改标题/SKU 重发 |
| `block` | 不得上架 | 查违规类型；确认是否真的属于禁售/受限类 |
| `escalate_legal` | 转法务/PI | **不要自己下架判定**。整理证据转法务 |
| `require_evidence` | 需补证据 | 向供应商索取清单里的材料 |
| `flag_for_review` | 人工看一眼 | 逐条判断 |

### 2.3 每条发现必看三个字段

1. **Base（来源层级）** — `regra da plataforma` / `lei brasileira` / `sugestão de risco interno` / `hipótese não verificada`。
   内部风控建议**不能**作为下架依据。
2. **Confiança（置信度）** — `signal` / `likely` / `confirmed`。
   IP 类命中**永远是 `signal`**。`signal` 不是结论。
3. **Trecho encontrado（命中片段）** — 确认规则匹配的是你以为的那段文字。

### 2.4 特别提醒：兼容性描述

「compatível com Ford Focus」这类车型/机型兼容描述**不是商标侵权**（Lei 9.279/1996 Art. 132, II）。

引擎会在这类命中上附注说明。看到这条说明时，判断标准是：**商标是被当作「品牌宣称」使用，还是被当作「适配说明」使用**？后者不违规。

---

## 阶段 3：处理 IP 类发现

IP 命中只是**筛查信号**。判定侵权需要以下之一：

- 权利人（商标/著作权/外观设计持有人）提交的**投诉记录**
- 卖家提供的**书面授权**（`brand_authorization_letter`）
- 平台下发的 **IP 投诉通知**

三者都没有时，**不能**下架判定，只能标记待观察。

---

## 阶段 4：跨店铺同款处理

### 4.1 判断是不是真同款

引擎给的是**候选**，理由有三档：

| 依据 | 可信度 |
|---|---|
| 同一供应商 SKU / 同一平台 PID | 强 |
| 标题+详情相似度 | 中 |
| 仅图片相似 | 弱 |

### 4.2 真同款的正确处理

**不是**删商品。正确做法：

1. 指定**主商品**（canonical listing）：留在哪个店、保留哪个 PID
2. 其余店铺的下架该 listing
3. 在案件里记录 `duplicate_of` 指向主商品
4. 主商品下架变体合并（颜色/尺码用 listing 内的变体选项，不要开多个 listing）

> **原因**：平台按「同一 listing 重复刊登」扣分（[401] / [302]）。同店同款拆成多个 listing 会被下架并降权；跨店同款虽然平台不管，但会分裂评价历史、增加处罚点风险，且一旦主店被处罚，另一个店会被牵连。

---

## 阶段 5：违规重发处理

### 5.1 三种平台处置，三种处理

| 平台处置 | 可恢复性 | 处理 |
|---|---|---|
| **Banido**（封禁） | 违规解决后可恢复 | 整改后申请恢复；重发前需人工复核 |
| **Excluído**（下架） | **不可**恢复，计入处罚点 | 重发前必须有关联案件的关闭记录 + 审批 |
| **Alcance limitado**（限流） | 改正后自动恢复 | 按提示改正即可 |

### 5.2 换标题/SKU 重发照样会被抓

引擎按五条轴匹配：平台 PID、供应商 SKU、卖家 SKU、商品链接、内容指纹（标题/详情相似度 + 图片哈希）。

**改标题或换 SKU 不会产生一个干净的 listing** —— 它继承原案件的记录。

### 5.3 重发冻结的正确解除

1. 找到关联的历史案件号
2. 收集 `remediation_evidence`（清单在 `SBR-DUP-003` / `SBR-RL-002` 的 `evidence_required`）
3. 在案件 `approvals` 里记一条 `approve` 记录（含 actor + timestamp + reason）
4. 才能解除冻结

---

## 阶段 6：处罚点与申诉

### 6.1 处罚点机制（平台规则）

- 处罚点**每周一**统一归属
- 进入处罚档位后**一周后**开始执行限制，限制期 **14–28 天**
- 费用在处罚开始**两周后**从钱包扣除
- 上月 GMV < R$2.500 的店铺**不收**该费用
- 处罚点**不清零**，保留到季度末
- **每个已认定违规只能申诉一次**
- 申诉被驳回后，补材料也**不能**撤销处罚点（但被下架的 listing 可申请恢复）
- 申诉材料必须含：**订单 ID + 申诉理由 + 证据附件**

### 6.2 申诉截止前不要动 listing

申诉证据依赖 listing **被处置时的样子**。整改会破坏证据一致性。`SBR-AC-002` 会把有未决申诉的商品标出来。

---

## 阶段 7：写审核结论

审核结论用 Markdown 记录（JSON 用于机器消费）。结论必须包含：

1. 审核范围（哪些文件、哪些店、什么时间）
2. 覆盖度：解析失败的行数、**未评估的规则**
3. 每条阻断/冻结的**规则编号 + 原文依据 + 证据**
4. 人工复核过的 IP 命中，注明**结论与理由**
5. 待办事项与责任人

---

## 常见错误

| 错误 | 后果 | 正确做法 |
|---|---|---|
| 拿 `flag` 当成「已确认违规」 | 误下架正常商品 | `flag` = 需要人看，不是结论 |
| 看到 IP 命中就下架 | 误伤兼容性/配件 listing；可能构成不正当竞争 | 按 §3 处理 |
| 输入缺字段却当作「通过」 | 漏检 | 看报告的「未评估规则」 |
| 分店跑审核 | 发现不了跨店同款 | 多店同一次运行 |
| 改原始导出文件 | 原始输入不可追溯 | 解析器只读 |
| 直接编辑 `rules/*.json` 不跑校验 | 引文编造、Schema 破坏 | 每次改完跑 §0.1 三条命令 |
| 用 glob 删除 `*_FINAL_*` 文件 | 唯一副本丢失 | 先 `ls` 出确切文件名再删 |
