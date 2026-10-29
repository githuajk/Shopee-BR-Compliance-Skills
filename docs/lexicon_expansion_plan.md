# 词库扩展与去集中规划（SBRCA-LEX-EXP-001）

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-LEX-EXP-001` |
| 状态 | **提案 —— 待裁定（open_questions Q-015）** |
| 日期 | 2026-10-28 |
| 提出 | integrator（2026-10-28 用户问询「词库是否可以扩展，目前类目太集中」） |
| 相关 | `lexicon/term_groups.json`（102 组 / 210,992 词）、`contracts/lexicon_rule_map.json`（102 映射）、README §下一阶段 #4（scan_fields 契约建议） |

---

## 1. 集中度现状（2026-10-28 实测）

| 维度 | 数据 | 说明 |
|---|---|---|
| C 类 ANVISA 目录 37 组 | 209,671 词 = **99.4%** | 其中 `health_commercial_names__multi` 一组 87,622 词 = 全库 41.5% |
| 非 catalog 政策/违规信号 | 65 组 / 1,340 词 = **0.64%** | prohibited 446 + ip_signal 486 + listing_violation 124 + restricted 政策短语 |
| catalog 监管方 | **全部为 ANVISA**（37/37） | 批次交付说明中的「ANVISA/CTI/MAPA」实际只有 ANVISA 落库；CTI/MAPA 为 0 组 |
| 单词组 | 26,139 词（12.4%） | 含 ≤4 字符条目 **846 个**（「AAA」「ABC」「KG」「MG」类）+ 通用词（`Marca` 已删，同类 `POMADA/SOLUÇÃO/Gel/KIT` 等 9 个待处理） |
| 扫描性能 | 单品 ~50 s（CLI 实测），listing 全量套件 ~45 min | 线性匹配，Aho–Corasick 索引未实现（`lexicon_scanning.md` §7 未决） |

**结论**：可以扩展 —— 架构上就是按开放数据流水线 + 批次交付设计的（D6 先例：178 词 + 17 豁免一批入库）。但「太集中」是事实：99% 的词只贡献一个 flag 级动作（SBR-MED-004），而真正的高判别力政策词（禁售/IP/社区准则）占比 <1%。

## 2. 内容扩展路线（batch004 候选，按价值/成本排序）

| # | 批次 | 内容 | 依据 | 建议映射 | 成本 |
|---|---|---|---|---|---|
| B1 | **药妆/化妆品** | ANVISA RDC 701/2021 化妆品规范 + 禁用/限用物质清单（hydroquinona >2%、mercúrio、tetra…） | 上一轮「药妆」缺口检查：声明层有、品类层无 | 新组 `proibido_cosmetico_substancia`（platform_official/law → SBR-MED-001 或新 PI 条款需裁定） | 需新抓取 2–3 篇 RDC |
| B2 | **处方药 RDC 44/2009** | 重抓（现登记 http_503，`_fetch_report.json` 已留痕） | `research/sources.json` 在册来源，校验器放行但不支撑规则 | `catalog_anvisa_restricted_medicine_*` 已有骨架，补全 | 1 篇重抓 |
| B3 | **MAPA（农业/兽药/饲料）** | MAPA 兽药/饲料/农药目录 | SBR-RI-006（宠物药品）目前**零词库支撑** | `catalog_mapa_*` → SBR-RI-006 + SBR-MED-004 | 新数据源 |
| B4 | **ANATEL/CTI（电信认证）+ INMETRO（安全认证）** | 无线设备/蓝牙/Wi-Fi 认证目录、玩具/电器安全认证 | 电子类目（耳机/路由器/充电宝）目前无认证类词支撑 | `catalog_anatel_*` → SBR-RI-004 类比/新 RI 条款需裁定 | 新数据源 |
| B5 | **英文信号词** | 跨境卖家常用英文违规词（nandrolone、prednisone、e-cigarette、hookah、anabolic…）+ 英文品牌词 | 现有词库葡语中心；英文信号 <1% | 并入 `proibido_drogas`/`proibido_tabaco` 等既有组（同 tier） | 纯词表，无抓取 |
| B6 | **IP 品牌词扩充** | 高仿重灾品牌（当前 ip_signal 仅 486 词） | `tests/fixtures/ip_cases.json` 覆盖有限 | `ip_*` 组 → SBR-IP-001/006（flag 级） | 需品牌清单来源 |

## 3. 结构调整（去集中 + 性能，无需新抓取）

| # | 项 | 内容 | 影响 |
|---|---|---|---|
| S1 | **scan_fields 分字段开关**（README 待裁定 #4 已登记契约建议） | catalog 组只扫 `title`/`description`，不扫 `brand`/`category`；或单词组只写 provenance 不产生候选 | 直接压掉「Sem Marca」类误触面与 ~12% 扫描量 |
| S2 | **通用词机械过滤** | 单词组中 ≤4 字符 846 个 + 通用容器词（pomada/solução/gel/kit/mg…）列入剔除候选；执行需 data-ingestion 按 C3 原则逐词留痕 | 降低 MED-004 低质量候选，扫描量再降 |
| S3 | **Aho–Corasick 索引**（`lexicon_scanning.md` §7 未决项） | 词库 21 万词线性扫描 50 s/品不可持续；**B1–B6 扩容前应先做** | 扫描 50 s → 毫秒级；测试套件 45 min → 分钟级 |
| S4 | **置信度分层** | catalog 单词命中 = signal（只 provenance）；catalog 多词命中 = candidate（可驱动规则）；政策词命中 = 高置信 candidate | 对齐 H3「筛查缺失 ≠ 通过」语义 |

## 4. 执行进度（2026-10-28 当晚更新）

- [x] **B5 英文信号词**：`proibido_drogas_en`（18 词）/ `proibido_tabaco_en`（9 词）入库；SBR-PI-003 v3 / SBR-PI-002 v2 正则联动（「nicotine」不入正则——戒烟贴片走 SBR-MED-002，仅「nicotine pouch」入正则）。靶向 11 例全过（7 阳性全命中、4 阴性零误伤）。
- [x] **S2 剔除执行**：848 项候选中 601 项已剔除（医学缩写/数字/含空格词 217 项保留），逐词留痕 `docs/s2_exclusion_trace_20261029.json`。
- [x] **S3 索引**：已由集成轮完成（前缀分桶 + C 级 str.find，见 lexicon_scanning.md §7.1）。
- [ ] B1 药妆 / B2 RDC44（重抓 URL 已 404，需新来源）/ B3 MAPA / B4 ANATEL —— 下一批
- [x] **S1 scan_fields 机制**（2026-10-29）：`lexicon.py` 新增 `field_scope()` / `apply_field_scope()`（纯函数，引擎 scan_product 自动应用）；契约 1.5.0 登记 `field_scoping` 机制块（PATCH：0 组声明，行为不变）。对 catalog_* 组**应用**分字段（如单词组降 provenance 级）属数据决策，需夹具回归后执行（Q-015）。
- [ ] S4 分层（与 dbdf8d7 豁免收窄联动，主 agent 推进）

---

## 5. 建议执行顺序（原始）

1. **立即（本集成轮可做）**：S3 前置评估 + S2 剔除候选清单（数据-only，留痕后交 data-ingestion）；B5 英文信号词表（无需抓取，可本批做）
2. **下一批（data-ingestion 任务包）**：B1 药妆 + B2 RDC44 重抓（补两个已知缺口）
3. **再下一批**：B3 MAPA + B4 ANATEL/INMETRO（新监管方覆盖）
4. **与任一扩容联动**：S1 scan_fields + S4 分层（走契约变更建议流程，`lexicon_rule_map.json` 加 `scan_fields` / `confidence` 字段，PATCH 级）

裁定入口：`docs/SBRCA-P0-004_open_questions.json` Q-015（本规划整体 + 各批次默认处置）。
