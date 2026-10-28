# 词库 D6 缺口补全 + 误伤豁免 —— 交付说明

**任务 ID**：TASK-INGEST-01（续，D6 覆盖缺口补全）
**分支**：`feature/lexicon-real-source-batch003`
**日期**：2026-10-28
**职责模块**：shopee-br-data-ingestion

---

## 1. 文件清单

| 文件 | 变更 | 说明 |
|------|------|------|
| `lexicon/term_groups.json` | 修改 | 并入 D6 补全词条 178 条；组数仍 100（并入现有语义组，不新增组，避免改冻结契约映射表） |
| `lexicon/exemptions.json` | 修改 | 豁免规则 44 → 61（新增 17 条，误伤防护） |

**未改动**：`contracts/**`、`rules/**`、`tools/**`、`docs/**`、`tests/**`（均非本模块所有权路径）

---

## 2. 工作内容

### 2.1 D6 缺口补全（来源：Shopee 官方禁售类目树）

上一批已覆盖 18 大类 + OUTRAS CATEGORIAS 主体。本批做**细节补全**，逐字从
`research/raw/shopee_br_politica_produtos_proibidos.txt` 抽取。

流程：
1. 直接读官方类目树原文，不用预设词探针（预设词命中率仅 5/40，多为 ANVISA 目录词偶然撞上）
2. 官方原文用官方分类名（`NERFS E ARMAS DE BRINQUEDO`、`CLAREAMENTO DOS DENTES`、
   `SUPLEMENTOS E VITAMINAS PARA GRÁVIDAS`），按原文短语抽取
3. **逐字核验 240/240 通过**（迭代纠错：`bastão`→`bastões`、`cuja`→`cujo`、
   `cerol (linha chinesa)`→`cerol (linha chilena)`、`vehicular`→`Veicular`）
4. 差集分析剔除与现有词库重复的 49 条
5. 剔除裸日常词（`gasolina`/`etanol`/`diesel` 等，普通商品标题易误伤）
6. 最终 **178 词条 / 50 组**，其中 `oficial_partes_corpo_humano`、`oficial_servicos_proibidos`
   因词条全部与现有词库重复而整组剔除

**本批真正增量**（上一批缺失）：`keylogger`、`clonagem de chave`、
`gravador de voz de espionagem`、`câmera com finalidade de espionagem`、`emuladores`、
`pneus remoldados`、`minoxidil`、`cerol (linha chilena)`、`GNV (Gás Natural Veicular)`、
`extintores de incêndio`、`clareadores dentais`、`softwares distribuídos digitalmente`

### 2.2 契约阻塞与并入式落位

`contracts/lexicon_rule_map.json` 为冻结契约（integrator 独占），
`tools/validate_lexicon.py` 第 198 行强制「每个词组必须有映射、unmapped 必须为空」。
新增 50 组必然校验失败。

**决策**：不碰契约，把 50 个新组词条按语义**并入现有 100 组中语义对应的组**，
纯 `lexicon/**` 范围内改动。

映射语义修正（初版有误）：
- `oficial_antincendio`（灭火器）→ `certificacao_marca`（INMETRO 认证，非政府禁售）
- `oficial_espionagem_*` → `platform_illegal_activities`（比 `proibido_government` 贴切）
- `oficial_fertilizantes_mapa` → `certificacao_marca`（MAPA 认证）
- `oficial_eletronicos_usados` 从 `platform_out_of_commerce` 移出（「número de homologação」不对口）

### 2.3 误伤豁免（核心工作）

**原则**：政策原文逐字不可改 → 误伤只能靠 `lexicon/exemptions.json` 加豁免。
豁免语义 = 命中仍记录，confidence 降级（`exempt`→low，其他→medium）。

**实测优先，不凭猜**：用真实商品标题测，发现政策原文自带限定条件而被我提取时丢失：

| 词条 | 官方原文限定 | 处置 |
|------|-------------|------|
| `queijo artesanal` / `manteiga artesanal` | 「**sem rotulagem adequada**」；2.2.2 明示 minas frescal 为许可品 | 带合规标识→`require_review` |
| `alimentos frescos` | 「**exceto para vendedores autorizados**」 | 该组映射 RI-005 require_evidence（非禁售）→`flag_low` |
| `bebidas caseiras` | 2.1 禁的是自酿酒；2. 鲜食章节指未许可食品 | `flag_low` |
| `equipamentos táticos` | 「**alguns** ... como colete à prova de balas」 | 普通战术装备→`flag_low` |
| `pilhas alcalinas` | 「É **restrita** a venda」= 受限非禁售 | `flag_low`（拦截依据是缺 Inmetro，由 RI-003/AU-001 承接） |
| `selos`/`rótulos`/`lacres`/`garrafas vazias` | 原句「Garrafas vazias, selos, rótulos, lacres e certificações **de bebidas alcóolicas**」整句 | 空白标签贴/封条本身合法→`require_review` |
| `metais preciosos` | 6. MOEDA FÍSICA / CRÉDITOS，指贵金属货币/投资标的 | 珠宝工具/工艺品→`require_review` |
| `extintores de incêndio` | 合规在售品类，受 Inmetro 认证约束 | `require_review`（拦截点是缺认证号） |
| `pneus remoldados`/`pneus usados` | 5.4 允许 remold，须标「Remold」+ Inmetro 注册号 | `require_review` |
| `produtos cosméticos e perfumes usados` | 7. BELEZA 无条件禁止 | `flag_low`（命中正确，仅降置信提示复核） |

**保留不豁免（正确命中）**：
- `colete à prova de balas` —— 官方明文禁售，防弹衣必须拦
- `produtos cosméticos e perfumes usados` —— 无条件禁止

**发现但不在本次范围（记录待处理）**：
`claim_alimento` 组 `orgânico` 为原有词条（`100% orgânico` 的子串），
命中「Frutas Orgânicas」属既有问题，非本批引入。

---

## 3. 测试结果

### 3.1 全量校验（实际命令输出）

```
env -u LD_LIBRARY_PATH bash scripts/check_all.sh
```

```
== 0/10  框架自检          PASSED: 206   FAILED: 0
== 1/10  公共契约校验       通过 19，失败 0
== 2/10  合并词库校验       PASSED: 889   FAILED: 0
         词库校验通过：100 组 / 210985 词 / 100 条映射 / 57 条规则
== 3/10  扫描器自测         12/12 通过
== 4/10  Schema 校验        0 errors, 0 warnings
== 5/10  引文逐字核验       57/57
== 6/10  来源清单一致       ok
== 7/10  正则可编译性       42 条
== 8/10  共享夹具校验       90 商品 / 8 场景 all valid
== 9/10  夹具-规则一致性    108 条断言（58 应命中 / 50 应不命中）一致
== 10/10 任务包与所有权     PASSED: 259   FAILED: 0

ALL CHECKS PASSED
```

### 3.2 误伤实测（真实商品标题）

| 测试集 | 规模 | 未豁免误伤 |
|--------|------|-----------|
| 老板真实品类标题（宠物/美妆/家居） | 57 条 | **0** |
| 项目 normal_products 夹具 | 12 条 | **0** |
| 新增词组专用压测（中性标题、去豁免） | 61 条 | **0** |
| 边界商品（合规奶酪/消防/园艺/轮胎） | 19 条 | **0**（2 条为正确命中） |

### 3.3 召回有效性

- 178 个词条**全部 100% 自命中**（词条本身无缺陷）
- 用原文措辞测 50 组：命中 49 组；`oficial_explosivos` 剩余 2 词条
  （`montagem de explosivos`、`contenham pólvora`）测试标题未含，词库正常

---

## 4. 未解决问题

1. **`contracts/lexicon_rule_map.json` 未改**（本次规避）。若后续要独立成组，
   需 integrator 走契约变更流程。
2. **`tools/validate_lexicon.py:198` 强制「所有词组必须有映射」** 与包自带
   `unmapped_groups` 设计及项目 `unmapped_group_policy`（未映射组仅作提示）冲突，
   已多次提出，建议契约层裁定。
3. **扫描器 D1–D6 六缺陷未修**（`tools/scan_lexicon.py` 归 listing-audit）：
   - D1 豁免作用域过大：只看全文是否匹配，不校验豁免区间与命中位置
     （`Faca de cozinha` + `pistola` 同文时枪械被一起豁免）
   - D2 同词多次只报一次（`pat.search` 非 `finditer`）
   - D3 offset 在归一化文本上计算，回切原文错位（`Tênis NÍKE`）
   - D4 豁免正则用裸 `\b` 且未归一化（`fixação`/`logística` 匹配不上）
   - D5 `EX-BRAND-GENERIC` 用 `^(.*)...(.*)$`，不跨行、贪婪无距离约束
   - D6 长句/复数词组在真实短标题中命中率低（本次用豁免缓解，未根治）
4. **`file_ownership.json` 六个 lexicon 文件被 data-ingestion 与 listing-audit 双重 owns**，
   违反「一路径一 owner」，未修。
5. **C 类词库 21 万词，扫描器每次启动重建索引约 37s**，批量扫需常驻进程。
6. **`orgânico` 既有子串问题**（`100% orgânico` 词条），本次不动。

---

## 5. 依赖说明

- 本次仅依赖 `research/raw/shopee_br_politica_produtos_proibidos.txt`（已在
  `research/sources.json` 登记为 `platform_official`），无新增外部来源
- `research/raw/` 三个抓取件（RDC 96 / Video 准则 ×2）由前序提交引入，本批未新增
- 未引入任何第三方库
- 运行环境必须 `env -u LD_LIBRARY_PATH`（否则 libcrypto.so.3 破坏 import ssl）

---

## 6. 契约变更建议

### 建议 1：`validate_lexicon.py` 映射强制策略

**现状**：第 198 行 `unmapped` 必须为空，与 `unmapped_group_policy` 语义冲突。

**建议**：允许词组标记 `"status": "candidate"` 或 `"mapping_required": false`，
未映射组只产生 warning 不导致校验失败，与 `unmapped_group_policy` 的
「不触发规则但作为提示列出」对齐。

**理由**：官方目录类词条（ANVISA/MAPA/CTI 登记名）天然无法一一映射到平台违规规则，
强制映射会导致把「目录登记」误当「平台禁售」。

### 建议 2：`file_ownership.json` 双重 owns

**现状**：`term_groups`/`rewrite_map`/`exemptions`/`quality_patterns`/
`non_avoidable`/`verb_conjugations` 六文件同时归 data-ingestion 与 listing-audit。

**建议**：归一化为 `lexicon/**` 归 data-ingestion，listing-audit 改只读。

---

## 7. 自我约束核查（AGENT_COLLABORATION C1–C10）

| 约束 | 核查 |
|------|------|
| C1 不改公共契约 | ✅ 本次未改 `contracts/**`（映射表沿用前序提交的 100 条，未新增） |
| C2 不改他人文件 | ✅ 仅改 `lexicon/term_groups.json`、`lexicon/exemptions.json`（均属 data-ingestion） |
| C3 不编造政策/引文 | ✅ 240/240 词条逐字核验通过；17 条豁免 reason 均引官方原文 |
| C4 不编造测试结果 | ✅ §3 全部为实际命令输出；未执行项已注明 |
| C5 不假设 Skill 自动调用 | ✅ 本次无 Skill 间调用 |
| C6 不依赖模型内部记忆 | ✅ 全部词条来自 `research/raw/` 逐字检索 |
| C7 IP 类不得无据称「侵权」 | ✅ 本次不涉及 IP 规则 |
| C8 缺失不得当通过 | ✅ 6 项未解决问题已列明，未当作已解决 |
| C9 不用未公开数值 | ✅ 所有计数可从仓库文件复核 |
| C10 不引入禁用格式 | ✅ 仅改 JSON，无 YAML/CSV/TXT 作为内部数据源 |

---

## 8. 复核入口

```bash
cd Shopee-BR-Compliance-Skills
git log --oneline -3
env -u LD_LIBRARY_PATH bash scripts/check_all.sh
python3 -c "import json;print(len(json.load(open('lexicon/exemptions.json'))['rules']))"
```
