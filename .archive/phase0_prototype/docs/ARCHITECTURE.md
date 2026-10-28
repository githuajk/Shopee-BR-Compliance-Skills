# 架构与设计决策

本文记录**为什么这样设计**，以及每个关键决策背后的取舍。决策记录格式：`背景 → 决策 → 代价`。

---

## 1. 总体结构

```
输入 (任意格式)
   │
   ▼
ingest/parsers.py ──► Product[]  +  ParseError[]
   │                        （原始文件只读；每条记录保留 raw_ref）
   ▼
engine/reviewer.py  ── 编排器
   │  ├── engine/duplicates.py   同店 / 跨店重复
   │  ├── engine/relist.py        重发匹配 + 冻结
   │  ├── engine/evaluator.py     条件求值 + 权限守卫
   │  │      └── engine/loader.py 规则加载 + Aho-Corasick
   ▼
review_result.json  +  review_report.md
```

---

## 2. 关键决策

### 2.1 只用标准库

**背景**：Hermes 运行时是托管的 PEP 668 环境，`pip install openpyxl` 失败（这是 `shopee-listing-bulk-compliance` skill 里已经踩过的坑）。项目必须能离线运行。

**决策**：
- XLSX 读取用 `zipfile` + `xml.etree.ElementTree` 直接解析 OOXML 部件。
- JSON Schema 校验器自己实现（`tools/validate_json.py`，支持项目用到的 draft 2020-12 子集）。
- CDP 客户端自己实现（`tools/cdp_client.py`，极简 RFC6455 websocket）。

**代价**：约 400 行额外代码，且 Schema 校验器只支持项目实际用到的关键字。好处是 `git clone` 之后立刻能跑，不需要任何安装步骤。

### 2.2 Seller Centre 是 SPA，必须渲染

**背景**：`seller.shopee.com.br/edu/article/<id>` 的正文来自 `/help/api/v3/article/detail/?article_id=<id>`，该请求带 `SPC_CDS` 会话令牌。直接 HTTP 请求返回 `{"msg":"not allowed language","code":1008}`；静态抓取只能拿到 13 KB 的空壳。

**决策**：`tools/render_page.py` 用无头 Chromium 加载页面（拿到令牌、SPA 自己取数据），再通过 CDP 读 `document.body.innerText`。

**踩过的坑**（都已在工具里注释）：
- Chromium 在路径过深时启动即死：`Socket path too long`。`TMPDIR` 与 `--user-data-dir` 必须固定在 `/tmp` 下。
- `/json/list` 会报告**过期的 URL**。必须 `Page.navigate` 后校验 `location.href`。
- 浏览器级 websocket + flattened session 会丢响应；直接连 **page target** 的 websocket 更稳。

**代价**：每次抓取要 20–25 秒，且依赖 `/usr/bin/chromium`。`help.shopee.com.br` 是服务端渲染的，用普通 HTTP 抓取即可（快 20 倍），所以两个抓取器并存。

### 2.3 规则库只用 JSON，词库可以很大

**背景**：需求要求「大规模关键词库可以使用 Aho–Corasick 等算法建立索引，但规则原始数据仍以 JSON 保存」。

**决策**：规则与词库的**磁盘格式**统一为 JSON；`engine/loader.py` 在加载时把词库编译成 Aho-Corasick 自动机（`O(1)` 摊销的多模式匹配，单遍扫描）。

**当前状态**：`lexicon/` 目录已建好但为空 —— 规则目前用正则表达。词库机制已就位，等真实数据量上来再填。

### 2.4 哨兵触发（sentinel trigger）

**背景**：重复刊登与重发这类判定，**不是文本模式能表达的** —— 它需要跨记录比对。规则 JSON 里没法写「如果商品 A 与商品 B 相似度超过 0.72 则触发」。

**决策**：把这类规则拆成两层。

- **引擎层**（`duplicates.py` / `relist.py`）负责真正的比对，把结论以哨兵 token 的形式注入被检查字段：
  `__DUPLICATE_SIGNAL__`、`__CROSS_STORE_DUPLICATE_SIGNAL__`、`__RELIST_SIGNAL__`、`__OPEN_CASE_SIGNAL__`、`__REMOVED_LISTING_SIGNAL__`
- **规则层**（`rules/*.json`）声明这条结论的严重度、决策、所需证据、来源链接。

**收益**：规则的严重度与证据要求仍然是**可审阅的数据**（能被人读、被 Schema 校验、被引用核验），而复杂的比对逻辑留在代码里。

**代价**：多一层间接。`reviewer.py` 里要把哨兵命中映射回真实证据描述，否则报告里会出现看不懂的 token。

### 2.5 三条权限守卫

**背景**：需求明确「严格区分平台明确要求、法律规定、内部风控建议和待核实事项。不得编造平台政策或将疑似侵权直接认定为侵权」。

**决策**（`engine/evaluator.py`）：

| # | 守卫 | 实现 |
|---|---|---|
| 1 | 非权威来源不得阻断 | `Rule.is_enforceable` 要求 `status == "active"` **且** `source_tier ∈ {platform_official, law}`；否则决策降级为 `flag_for_review` |
| 2 | IP 命中永远是信号 | `category ∈ {ip_trademark, ip_copyright, ip_design}` → `confidence = "signal"`、`human_review_required = True`；`block` 升级为 `escalate_legal` |
| 3 | 缺失数据 ≠ 违规 | 触发条件可声明 `requires_input`；输入缺该字段时条件不评估，并写入结果的 `errors` |

**第 3 条的价值**：演示首版在 15 条合成商品上把 **15/15 全标违规**，因为 xlsx 没有图片/类目/品牌列，而规则写着「无图片 → 违规 [606]」。这三条守卫把结论修正为 **2 阻断 / 4 待复核 / 9 通过 / 3 项未评估**，并且未评估项在报告里可见。

### 2.6 引文逐字核验

**背景**：项目最大的失败模式是「编造平台政策」。写规则时很容易凭印象写出一段看似合理的葡语引文。

**决策**：`tools/verify_citations.py` 把每条规则的 `source_excerpt` 与 `research/raw/*.txt` 的抓取件做**逐字比对**（空白与句末标点归一化，其余字符严格）。不通过就报错。该检查也接进了测试套件。

**这个工具抓到了真实的编造**：初版 `SBR-IP-006` 引用了「Art. 125. Não constitui uso indevido…」—— 这段葡语**在 Planalto 原文里根本不存在**。实际条文是 **Art. 132, II**，且原文的「I -」在 HTML 渲染时丢失为「-」，必须逐字匹配才能过。

**代价**：引文必须与抓取件的换行/标点完全一致，改动规则描述时容易连带失效，需要重跑核验。

### 2.7 状态优先级：冻结重发 > 阻断

**背景**：一个被下架的商品重发，可能同时命中「假冒」（escalate_legal）和「重发已下架商品」（freeze_relist）。产品最终状态该取哪个？

**决策**（`engine/evaluator.py::product_status`）：

```
block            → "block"      (硬性禁售，商品根本不该存在)
escalate_legal   → "block"      (需要法务 owner)
freeze_relist    → "frozen"     (商品还在，但不许再上架)
require_evidence / flag_for_review → "flag"
```

**理由**：`freeze_relist` 是**对上架这个动作**的处置（不许再发），而 `escalate_legal` 是**对问题性质**的定性（需要法务）。当两者同时出现时，运营要执行的动作是「冻结重发」，定性信息仍完整保留在发现列表与建议动作里（`product_action` 会追加「+ freeze re-listing」）。

**反例防护**：`escalate_legal` 仍然映射为 `block` 状态 —— 因为法务介入意味着必须停止上架。

### 2.8 未评估规则要报告，不能沉默

**背景**：守卫 #3 让「输入没有的字段」不再产生发现。但如果不报告，运营会误以为「检查过了，没问题」。

**决策**：`reviewer.py` 汇总所有带 `requires_input` 的规则，若整个输入里都没有该字段，写一条 `warning` 级错误进结果的 `errors`，并在报告的「Erros de ingestão」小节列出。

**收益**：报告里的「未评估」是一等公民，与「通过」明确区分。

---

## 3. 数据模型

### 3.1 为什么 Product 有 `history` 而不是独立的表

违规追踪需要的是「这个商品身上挂着哪些案件、哪些证据、哪些处罚点」。这些是**商品的属性**，不是商品的标识。独立建表会带来额外的主外键维护成本，而查询时永远要 join 回来。

`history` 是一个自由字典，规则可以按 key 匹配（`authorization_documents`、`penalty_points`、`appeal_pending`）。它的取值来自导入时附带的案件/处罚记录。

### 3.2 为什么 Case 的 `status` 决定冻结行为

`relist.py::_is_actioned` 里，`open` / `under_review` / `awaiting_evidence` **不算**已处置，即使 `frozen: true` 也不算。

**理由**：案件处于这些状态时，卖家正在整改并申请平台复核。此时冻结重发会**挡住正要提交复核的整改**。只有平台已经实际处置（`blocked` / `relist_frozen` / `escalated` / `rejected`）的案件才冻结重发。

这条区分在测试 `TC-02`（被暂停商品整改后申请复核 → 期望 `flag`）里被强制验证。

---

## 4. 扩展点

| 想加什么 | 改哪里 |
|---|---|
| 新规则 | 在 `rules/` 加 JSON 条目 + 更新 `data/schema/rule.schema.json`（若需新字段）+ 跑两个校验器 |
| 新输入格式 | 在 `ingest/parsers.py` 的 `EXT_DISPATCH` 加一个函数 |
| 新条件算子 | `engine/evaluator.py::eval_condition` 加分支 + `rule.schema.json` 的 operator 枚举 |
| 图片 OCR / logo 识别 | 产出 `Product.images[].ocr_text` 与 `detected_logos`，现有 `SBR-IP-005` / `SBR-IP-008` 自动生效 |
| 大规模词库 | `lexicon/*.json` → `engine/loader.py::compile_ac` |
| 新的历史来源 | 转成 `Case` / `Product` 记录喂给 `Reviewer(history_cases=..., history_products=...)` |

---

## 5. 明确的非目标

- **不自动推送 GitHub，不部署外部服务。** 第一阶段只做本地项目。
- **不编造真实商品记录。** `data/samples/` 里全部是合成数据。
- **不做 LLM 改写。** 本项目是**审核**引擎，不是文案改写引擎。LLM 可以在人工复核环节辅助，但判定逻辑必须是确定性的、可复现的、可审计的。
- **不推断平台未公开的数值**（如处罚点分值）。
