# 人工审核操作手册（Shopee BR 商品合规）

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-SOP-MANUAL-001` |
| 版本 | 1.1.0 |
| 状态 | **Draft — 待用户审批** |
| 创建/更新 | 2026-10-28 |
| 面向对象 | **人工审核员** —— 纯手工，不需要看代码、不需要跑脚本 |
| 适用范围 | Shopee 巴西站商品标题与详情的**人工合规审核** |
| 判定依据 | 全部来自 `rules/*.json`（50 条规则）、`lexicon/*.json`、`research/violation_codes.json`（106 个平台处罚码） |
| 配套文档 | `docs/USER_SOP.md`（整体流程框架）、`docs/SOP_COMPLIANCE_REVIEW.md`（判定原理） |

---

## 0. 这份手册怎么用

**不需要跑任何工具。** 你只需要：打开商品 → 对着清单看 → 记结论。

### 三条线

| 线 | 你在做什么 | 用哪几节 |
|---|---|---|
| **主线** | 逐个商品从头审到尾 | §1 定类目 → §2 标题 → §3 详情 → §4 图片 → §5 属性 → §5A 汇总 → §7 收口 |
| **判断线** | 看到一个词，判它是不是违规 | §6 关键词判定表（核心）+ §9 豁免清单 |
| **处置线** | 判完之后怎么办 | §7 收口 → §8 改写标准 → §7.6 复检 → §11 交报告 |

### ★ 关键：每一步都要"交出去"

**这是本手册的核心。** 审核不是看完四个清单就完事 —— 每一步看完都要产生一样东西，交给下一步：

```
第 0 步 定类目  ──交出──▶  【类目卡】决定后面用哪张判定表
第 1 步 看标题  ──交出──▶  【标题问题清单】命中词 + 硬伤
第 2 步 看详情  ──交出──▶  【详情问题清单】命中词 + 硬伤
第 3 步 看图片  ──交出──▶  【图片问题清单】logo / 版权 / 数量
第 4 步 看属性  ──交出──▶  【属性问题清单】类目 / 尺寸 / 资质
第 5 步 合并    ──交出──▶  【商品问题总表】五张清单合成一张，每行都有动作
第 6 步 收口    ──交出──▶  三个出口：改写 / 工单 / 挂起
第 7 步 改写    ──交出──▶  【新标题】+【新详情】
第 8 步 复检    ──交出──▶  【最终问题清单】残留问题
第 9 步 交报告  ──交出──▶  【报告】6 节 + 全部清单
```

**每一步结束时你手上必须有一张"问题清单"。** 空清单也要写"无"—— **空清单和"还没看"是两回事**。

### 一句话记住全流程

> **定类目 → 看标题 → 看详情 → 看图 → 看属性 → 合并总表 → 定动作 → 改写 → 复检 → 交报告**

### 全流程一张图

```
                    ┌──────────────────┐
                    │ 0. 定类目        │  30 秒
                    │    ↓ 产出：类目卡 │
                    └────────┬─────────┘
                             ↓
    ┌────────────────────────────────────────────────┐
    │ 1. 看标题  →  2. 看详情  →  3. 看图片  →  4. 看属性 │  每步产出一张问题清单
    │      ↓            ↓            ↓            ↓      │
    │   标题问题      详情问题      图片问题      属性问题  │
    └────────────────────┬───────────────────────────────┘
                         ↓  ★ §5A 合并：五张清单合成一张
              ┌──────────────────────────┐
              │ 5A. 商品问题总表         │  每行必须有动作
              │    每行一个动作：         │  改写/查授权/出工单/无需处理
              └────────────┬─────────────┘
                           ↓
              ┌──────────────────────────┐
              │ 6. 收口（§7）            │
              │  有致命? → 停，走 §7.2   │
              │  缺资质? → 停，走 §10    │
              │  其余    → 走 §8 改写    │
              └────────────┬─────────────┘
                           ↓
              ┌──────────────────────────┐
              │ 7. 改写（§8）            │  改完必须重读
              │    ↓ 产出：新标题/新详情 │
              └────────────┬─────────────┘
                           ↓
              ┌──────────────────────────┐
              │ 8. 复检（§7.6）          │  ★ 12 项逐条过
              │    ↓ 产出：最终问题清单    │  ★ 最容易漏的一步
              └────────────┬─────────────┘
                           ↓
              ┌──────────────────────────┐
              │ 9. 交报告（§11）         │  6 节 + 全部清单
              └──────────────────────────┘
```

> **§7.6 复检是最容易漏的一步。** 改写会引入新问题 —— 你自己改的地方可能是下一个错误。

---

## 1. 第 0 步：定类目（30 秒，决定后面用哪张表）

**为什么要先做**：同一个词在不同类别意思完全不同。`Cura`（治愈）在化妆品里是违规宣称，在汽配化工里是正常术语。**先定类目，再判词。**

### 1.1 产出一张「类目卡」

```
商品编号：____
类目：□ 化妆品  □ 汽配  □ 电池  □ 酒类  □ 药品保健品  □ 兽药
      □ 太阳镜  □ 儿童安全  □ 普通商品
判定依据：标题/详情里看到的：____________
```

### 1.2 类目 → 后面用哪张表

| 类目卡上的类目 | 标题查 | 详情查 | 改写查 | 特别注意 |
|---|---|---|---|---|
| **化妆品** | §2 + §6.3 | §3 + §6.3 | **§8.3 化妆品** | 没 ANVISA 号 → 直接 §10，**别改文案** |
| **汽配** | §2 + §6.6 | §3 + §6.6 | §8.3 汽配 | `Cura` `Firma` `Certificação` 在这里**正常**，别误伤（§9 EX-CHEMICAL） |
| **电池** | §2 + §6.2 | §3 + §6.2 | §8.1 | 查运输认证 |
| **酒类** | §2 + §6.2 | §3 + §6.2 | §8.1 | **自酿酒直接禁**（§10） |
| **药品保健品** | §2 + §6.2 + §6.3 | §3 + §6.3 | **§8.3 药品** | 2026-08-06 起只有持牌店能卖 MIP（§6.2） |
| **兽药** | §2 + §6.2 | §3 + §6.2 | §8.1 | MAPA 资质 |
| **太阳镜** | §2 + §6.1 | §3 + §6.1 | **§8.3 太阳镜** | 要 INMETRO 实测报告（§10） |
| **儿童安全** | §2 + §6.1 | §3 + §6.1 | **§8.3 儿童** | 要 INMETRO 认证 + 年龄限制（§10） |
| **普通商品** | §2 | §3 | §8.1 | 通用清单 |

### 1.3 ★ 两条硬分支（命中就立刻停，别往下走）

| 命中 | 立刻停在哪 |
|---|---|
| 标题或详情出现 **§6.1 禁售类**的词 | **§7.2 致命分支** —— 不上架，直接出清单给店主 |
| 类目是化妆品/太阳镜/儿童安全，**且没有对应注册号或认证** | **§10 缺资质** —— 出工单，不进改写 |

> **这两条是流程里唯一的"提前退出"。** 命中就别再往下审了 —— 后面看了也白看，结论已经定了。

### 1.4 交给下一步

```
→ 下一步要看：§2 标题检查清单
→ 带上的东西：【类目卡】（决定 §6 查哪张表）
→ 提醒：类目是汽配/化工的，§6.3 的词要额外对照 §9 的 EX-CHEMICAL 再判
```

---

## 2. 第 1 步：看标题（12 项）

**标题是最容易中招的地方。** 平台先扫标题，而且标题里的禁售词 = 直接不上架。

### 2.1 检查清单

| # | 检查什么 | 什么算不合格 | 严重度 | 归到哪张判定表 |
|---|---|---|---|---|
| 2.1 | **禁售品类词** | 武器/烟草/毒品/化学品/赌博/证件/野生动物/成人 | 🔴 致命 | §6.1 |
| 2.2 | **品牌名** | 标题里出现别的品牌（Nike / Adidas / Apple / Samsung / Gucci…） | 🟡 要查授权 | §6.6 |
| 2.3 | **品牌堆砌** | 标题里塞了 2 个以上品牌 | 🟢 低（[507]） | §6.7 |
| 2.4 | **关键词堆砌** | 标题是一长串不相关词；或标题超过约 120 字符 | 🟢 低（[506]） | §6.7 |
| 2.5 | **形态词矛盾** | 同时出现 3 个以上形态词（pomada / creme / gel / spray / sérum / máscara / pó / óleo…） | 🟡 需核实实物 | §8.3 |
| 2.6 | **年龄不符** | 标题写 `infantil` / `kids` 但实际是成人用品；或反之 | 🟢 低（[510]） | §6.7 |
| 2.7 | **功效承诺** | `cura` / `garantido` / `elimina` / `milagroso` / `emagrece` / `resultado garantido` | 🟡 要改（[337]） | §6.3 |
| 2.8 | **时间承诺** | `resultado em 30 dias` / `em 2 semanas` | 🟡 要改 | §6.3 |
| 2.9 | **英文残留** | 标题或详情里有英文（Anti-Aging / Firming / Wrinkles / Lifting…） | 🟡 要改 | §6.3 |
| 2.10 | **葡语错误** | 重音错、拼写错、逗号写成小数点 | 🟡 要改 | §8.6 |
| 2.11 | **末尾悬空** | 标题最后一个词是 `de` `da` `para` `com` `vi` `pa` 这类断词 | 🟡 要改 | §8.4 |
| 2.12 | **GTIN / 编号** | 缺 GTIN 或货号（平台要用来比重复） | 🟢 低（[307]） | §5.1 第 5.9 行 |

### 2.2 标题的合格标准

| 项 | 标准 |
|---|---|
| 长度 | 60–95 字符（**不超过 120**） |
| 结构 | 空格分隔关键词，**不要用分隔逗号** |
| 数字 | 葡语小数用逗号：`19x2,5cm`（不是 19x2.5cm） |
| 形态词 | 最多 1–2 个，与实物一致 |
| 品牌 | 只有真能用才写，且最多 1 个 |
| 结尾 | 不能是悬空断词 |

### 2.3 ★ 交给下一步

```
→ 产出：【标题问题清单】
  行号 | 命中词/问题 | 严重度 | 归到哪张判定表
  -----+------------+--------+--------------
  ...  | ...        | ...    | ...

→ 带上的东西：类目卡 + 标题问题清单
→ 关键提醒：
   · 标题里有 §6.1 的词？→ 停下，走 §7.2（后面不用看了）
   · 标题有功效承诺？→ 详情很可能有一样的，§3 要重点查
   · 标题形态词矛盾？→ §3 要核对详情写的到底是什么形态
```

> **§2 → §3 的衔接逻辑**：标题是详情的浓缩。**标题里有的问题，详情里几乎一定有**。所以 §2 命中的词，§3 要重点复查一遍；标题干净的，详情才可能干净。

---

## 3. 第 2 步：看详情（20 项）

### 3.1 检查清单

| # | 检查什么 | 什么算不合格 | 严重度 | 归到哪张判定表 |
|---|---|---|---|---|
| 3.1 | **长度** | 少于 120 字符 → 平台直接判"描述不足" | 🟡 中（[605] **扣分**） | §6.7 |
| 3.2 | **长度** | 剥掉模板和链接后少于 250 字符 → 内容太薄 | 🟡 要补充 | §8.4 |
| 3.3 | **长度** | 少于 500 字符 → 缺"使用方法"和"包装内容"两段 | 🟡 要补充 | §8.4 |
| 3.4 | **功效承诺** | `cura` `garantido` `garantia` `eficaz` `elimina` `definitivo` `total` `milagroso` `emagrece` `resultados garantidos` | 🟡 要改（[337]） | §6.3 |
| 3.5 | **疾病宣称** | 出现具体病名：`psoríase` `eczema` `dermatite` `acne` `manchas` `queda de cabelo` `cravos` | 🟡 要改 | §6.4 |
| 3.6 | **医疗词** | `medicamento` `antisséptico` `antibacteriano` `anti-inflamatório` `analgésico` `antidepressivo` `ansiolítico` `terapêutico` | 🟡 要改或删 | §6.3 |
| 3.7 | **绝对化用语** | `100%` `original` `melhor` `o mais` `total` `para todos` `todos os tipos` | 🟡 要改 | §6.5 |
| 3.8 | **商标词** | 品牌名出现（除非是兼容说明） | 🟡 要查授权 | §6.6 |
| 3.9 | **外链/导流** | 网址、WhatsApp、Telegram、"请加微信"、站外联系方式 | 🟡 中（[112]） | §6.7 |
| 3.10 | **残留话术** | 店铺名、客服话术、物流话术（`Bem-vindos à loja...` / `Nossa equipe...` / `Os pedidos são preparados...`） | 🟡 要删 | §8.1 |
| 3.11 | **图片链接** | 详情里塞了店铺图片 URL（`cf.shopee.com.br/file/...`） | 🟡 要删 | §8.1 |
| 3.12 | **中文残留** | 任何中文字符 | 🟡 要删 | §8.7 |
| 3.13 | **法语残留** | `nécessaire` `obligatoire` `déjà` `très bien` | 🟡 要删 | §8.7 |
| 3.14 | **翻译机器味** | 单词粘连：`uniformementeizar` `aplicaruniformemente` `parauniformizar` | 🟡 要改 | §8.5 |
| 3.15 | **空洞宣称** | `Material premium` `Acabamento cuidadoso` `Confortavel` `Produto de alta qualidade` | 🟡 要改成具体描述 | §8.1 |
| 3.16 | **产地统一** | 所有商品都写 `Origem: China` | 🟡 要按实物改 | §8.1 |
| 3.17 | **类目模板** | 首饰/工具类却写 `Tipo: Cosmético` | 🟡 要改 | §8.3 |
| 3.18 | **测试宣称** | `Testado dermatologicamente` | 🟡 要删（无证据） | §6.5 |
| 3.19 | **拼写错误** | 葡语拼写错、双空格、缺空格 | 🟡 要改 | §8.6 |
| 3.20 | **残句** | `para auxilia` / `A design` / `rotina de rotina` / `uso geral e uso doméstico` | 🟡 要改 | §8.5 |

### 3.2 详情的合格标准

**必须按这六段写，顺序固定：**

```
1. Descrição            —— 首句 = 商品名 + 具体用途
2. Características      —— 用 • 分条，每条一个卖点
3. Especificações        —— 尺寸 / 容量 / 材质 / 适用
4. Modo de uso           —— 怎么用
5. Conteúdo da embalagem —— 包装里有什么
6. Cuidados importantes  —— 注意事项 + 适用年龄 + 不替代专业建议
```

**首句必须含商品实词：**

| ✅ 合格 | ❌ 不合格 |
|---|---|
| `Saco de malha transparente para organizar livros e materiais.` | `Item para organizar a rotina, com capacidade ampla e alça confortável.` |
| `Suporte de pia fixado na parede para esponjas e utensílios.` | `Produto versátil para o dia a dia.` |

### 3.3 ★ 交给下一步

```
→ 产出：【详情问题清单】（格式同标题问题清单）
→ 带上的东西：类目卡 + 标题问题清单 + 详情问题清单
→ 关键提醒：
   · 标题命中过的词，详情里再搜一遍（同一违规常两处都有）
   · 详情里出现品牌名 → §4 看图时重点看图上有没有对应 logo
   · 详情写了"具体功效" → §5 要核对属性字段是否也夸大
   · 详情有外链/话术 → 记下来，§8 改写时一起删
```

> **§3 → §4 的衔接逻辑**：详情里的品牌名和图片上的 logo 是**同一件事的两个证据**。详情提到某个品牌，就要在图上确认是不是有该品牌实物 —— 有图有文 = 侵权坐实，只有文没有图 = 可能只是兼容说明（§9 EX-COMPAT）。

---

## 4. 第 3 步：看图片（7 项）

### 4.1 检查清单

| # | 检查什么 | 什么算不合格 | 严重度 | 归到哪张判定表 |
|---|---|---|---|---|
| 4.1 | **数量** | 少于 1 张 | 🟢 低（[606]） | §6.7 |
| 4.2 | **质量** | 模糊、纯白底无商品、与商品无关 | 🟢 低（[606]） | §6.7 |
| 4.3 | **第三方 logo** | 图里有别的品牌 logo、字标、压印 | 🟡 要查授权 | §6.6 |
| 4.4 | **Shopee logo** | 用了 Shopee 的 logo 或 banner | 🟡 中（[608]） | §6.7 |
| 4.5 | **外卖平台 logo** | 背包/袋子上有 iFood / Rappi / delivery app 的 logo | 🟡 中（[349]） | §6.6 |
| 4.6 | **版权图** | 用了盗图、带水印、"todos os direitos reservados" | 🟡 要换（[602]） | §6.6 |
| 4.7 | **工业设计** | 外形抄袭了注册外观设计 | 🔴 转法务（[603]） | §6.6 |

> **图片里的 logo 是独立触发条件** —— 即使标题和详情都干净，图上有别人的 logo 一样会被下架。

### 4.2 ★ 交给下一步

```
→ 产出：【图片问题清单】
→ 带上的东西：类目卡 + 前三张问题清单
→ 关键提醒：
   · 图上有 logo 但详情没提品牌 → 也要记（图片独立触发）
   · 图片数量 <1 → 这是硬伤，改文案救不了，只能补图
```

---

## 5. 第 4 步：看属性 / 类目 / 品牌（9 项 + 跨店 7 项）

### 5.1 属性检查清单

| # | 检查什么 | 什么算不合格 | 严重度 | 归到哪张判定表 |
|---|---|---|---|---|
| 5.1 | **类目正确** | 选错类目（尤其受限品放错类目） | 🟢 低（[613]/[612]） | §6.7 |
| 5.2 | **品牌准确** | 品牌字段空、或与实际不符 | 🟢 低（[301]） | §6.7 |
| 5.3 | **尺寸重量** | 尺寸重量没填、填错 | 🟢 低（[120]） | §6.7 |
| 5.4 | **尺寸超限** | 超出 Shopee 允许的重量/尺寸 | 🟡 中（[508]/[509]） | §6.7 |
| 5.5 | **注册信息** | 化妆品/电器/汽车件/医疗器械缺 ANVISA / ANATEL / INMETRO / MAPA 注册号或认证 | 🟡 要补证（[503]-[505]） | **§10** |
| 5.6 | **年龄等级** | 年龄段和类目/标题对不上 | 🟢 低（[510]） | §6.7 |
| 5.7 | **变体滥用** | 变体里塞价格/规格混乱数据 | 🟢 低（[309]） | §6.7 |
| 5.8 | **变体尺寸** | 变体带不准确的尺寸重量 | 🔴 致命（[517]） | §7.2 |
| 5.9 | **GTIN** | 缺 GTIN | 🟢 低（[307]） | §6.7 |

### 5.2 跨店 / 重复检查（如果有多个店铺）

| # | 检查什么 | 说明 | 严重度 |
|---|---|---|---|
| 5.10 | **同店重复** | 同一店两个商品内容几乎一样 | 🟡 中（[401]） |
| 5.11 | **跨店重复** | 同款商品在多个店铺都上了（**包括你自己家的店**） | 🟡 中（[302]） |
| 5.12 | **换皮重发** | 之前被下架的商品，改个标题或换 SKU 重新上 | 🔴 冻结重发（[401]） |
| 5.13 | **未结案件** | 商品还挂在未关闭的违规案件上 | 🟡 中 |
| 5.14 | **已被删** | 商品是平台删掉的，删掉不可恢复 | 🔴 冻结重发 |
| 5.15 | **处罚点** | 账号有处罚点 | 🟡 要查 |
| 5.16 | **申诉中** | 处罚点申诉还没到期 | 🟡 别重发 |

### 5.3 ★ 交给下一步（★ 进入收口）

```
→ 产出：【属性问题清单】
→ ★ 现在你有四张清单了：类目卡 + 标题 + 详情 + 图片 + 属性
→ 下一步：§7 收口 —— 把所有清单合成一张总表，定动作
→ 带上的东西：五张清单（全部）
```

---

## 5A. ★★ 五张清单怎么合成一张（收口前的整理）

**这一步是衔接的关键。** 四张清单是分开记的，到这里要合并成一张总表。

### 5A.1 合并去重

同一个词可能在标题和详情都出现 —— **算一条，不是两条**（严重度取高的）。

| 原样 | 合并后 |
|---|---|
| 标题清单：`cura` 🟡 | **详情清单：`cura` 🟡** | → 总表一条：`cura` 🟡 改写 |

### 5A.2 总表格式（每行一个商品一张总表）

```
商品编号：____   类目：____

| # | 命中词/问题 | 出现在 | 严重度 | 判定表 | 动作 |
|---|------------|--------|--------|--------|------|
| 1 | cura        | 标题+详情 | 🟡    | §6.3   | 改写 |
| 2 | Nike        | 详情     | 🟡    | §6.6   | 查授权 |
| 3 | 缺 ANVISA   | 属性     | 🟡    | §10    | 出工单 |

动作只有四种：改写 / 查授权 / 出工单 / 不上架
```

### 5A.3 ★ 每行都要有动作，没有就填"无需处理"

**空动作 = 没判完。** 每个命中都必须落到一个动作上。

### 5A.4 交给下一步

```
→ 产出：【商品问题总表】（每行都有动作）
→ 下一步：§7 收口定处置
```

---

## 6. 关键词判定表（核心）

**这是审核员最常用的一张表。** 看到一个词 → 查这里 → 定结论。

**用法**：总表里每行的「判定表」列告诉你去哪张表查。例如「§6.3」→ 查 §6.3 功效宣称表。

### 6.1 禁售类（🔴 致命 —— 不上架）

| 品类 | 关键词（葡语） | 平台码 | 备注 |
|---|---|---|---|
| **武器** | arma de fogo, revólver, pistola, escopeta, taser, colete à prova de balas, munição | [317] | **菜刀/剪刀/螺丝刀/美工刀不算**（见 §9） |
| **烟草电子烟** | cigarro, charuto, cachimbo, tabaco, vape, juice, nicotina, narguil, pods, atomizador | [311] | 电子烟配件也禁 |
| **毒品管制药** | droga, medicamento controlado, tarja preta, tarja vermelha, aborto, abortivo, injetável, estimulante sexual, antidepressivo, minoxidil | [313] | 分红标/黑标 |
| **化工易燃爆炸** | explosivo, nitrogênio, gasolina, diesel, acetona, produto químico bruto, corrosivo, trinitrotolueno | [332] | |
| **假币证件** | dinheiro, real, nota, cartão, clonador, jammer, documentos falsificados | [341] | |
| **赌博数字商品** | jogo de azar, loteria online, aposta, caixa misteriosa, itens digitais | [338] | |
| **政府徽章制服** | insígnia, brasão, uniforme militar, policial, item oficial governamental | [516] | |
| **野生动物** | animais vivos, partes de animais selvagens, espécies ameaçadas, fauna, flora | [339] | |
| **成人内容** | pornográfico, conteúdo adulto, sexo, explícito | [320] | |
| **未巴氏消毒乳制品** | leite cru, queijo artesanal, iogurte artesanal, manteiga artesanal | [342] | 工业巴氏杀菌密封装**可以** |

### 6.2 受限类（🟡 要资质 —— 缺证就不能上）

| 品类 | 关键词 | 平台码 | 需要什么资质 |
|---|---|---|---|
| **酒类** | cerveja, vinho, whisky, conhaque, aguardente, champanhe, destilado, licor, bebida alcoólica | [325]/[342] | 酒类销售文件；**自酿酒直接禁** |
| **健康用品保健品** | suplemento, vitaminas, monitor de pressão, aparelho médico, ortopédico, teste | [312] | 卫生监管注册 |
| **电池充电宝** | pilha, bateria alcalina, recarregável, power bank | [333] | 运输安全要求 |
| **汽配** | componente automotivo, peça de carro, homologação | [132]/[343]/[344] | Inmetro/Anatel 认证；**二手/翻新件禁**。注意：[132] 扣分，[343]/[344] 不扣分 |
| **生鲜冷冻食品** | alimento fresco, congelado, frutas, verduras, carne | [331] | 必须密封包装 |
| **兽药** | medicamento pet, veterinário, antiparasitário, vacina, vermífugo | [334] | MAPA 资质 |
| **气枪/彩弹** | airsoft, paintball, arma de pressão, equipamento tático | [315] | |
| **人用药** | medicamento, isento de prescrição, remédio, tarja | [313]/MED | **2026-08-06 起只有持牌药店/药店类店铺能卖 MIP** |

### 6.3 功效宣称类（🟡 要改 —— [337] 中等严重度，**扣分**）

| 触线词 | 为什么不行 | 改成 |
|---|---|---|
| `cura` / `curar` / `curativo` | 医疗宣称 | `cuidados com a pele` / `auxilia em` |
| `garantido` / `garantia` / `garante` | 绝对承诺 | `pode auxiliar` / `auxilia em` / `pode oferecer` |
| `eficaz` / `eficiente` | 功效宣称 | 去掉，或改成具体描述 |
| `elimina` / `eliminar` | 绝对效果 | `auxilia a reduzir` |
| `definitivo` / `definitiva` | 绝对效果 | 去掉 |
| `total` / `completamente` | 绝对化 | 去掉 |
| `milagroso` / `milagrosa` | 奇迹宣称 | 去掉 |
| `resultado garantido` / `resultados garantidos` | 结果承诺 | 去掉 |
| `emagrece` / `emagrecimento` | 减重宣称 | 删除 / 改成 `design` |
| `redutor de medidas` | 塑形宣称 | 删除 |
| `anti-idade` / `antirrugas` | 抗衰宣称 | `cuidados com a pele` |
| `clareador` / `clareamento` | 美白宣称 | `esfoliante` |
| `lifting facial` | 医美宣称 | `tratamento` |
| `cicatrizante` | 医疗宣称 | `cuidados com a pele` |
| `anti-inflamatório` | 医疗宣称 | `calmante para a pele` |
| `analgésico` | 医疗宣称 | `relaxante` |
| `antidepressivo` / `ansiolítico` | 精神类药物 | **删除** |
| `antisséptico` / `antibacteriano` | 医疗宣称 | `higiênico` |
| `terapêutico` | 医疗宣称 | `tratamento`（慎用） |
| `antifraude` | 误导 | `decorativo` |
| `antiembaçante` | 宣称 | `antivisão embaçada` |
| `resultado em 30 dias` / `em N dias` | 时间承诺 | 去掉 |
| `100%` / `original` / `produto original` | 绝对化 / 真伪无据 | 去掉 |

### 6.4 疾病名类（🟡 要改 —— 只要出现具体病名就删）

| 词 |
|---|
| `psoríase` `eczema` `dermatite` `acne` `manchas` `cravos` `queda de cabelo` `cólera` `fungos` `bactérias` `vírus` `germes` |

> `bactérias` `vírus` `germes` → 改成 `microrganismos`。

### 6.5 营销/绝对化类（🟡 要改）

| ❌ | ✅ |
|---|---|
| `mais vendido` / `best seller` | `um dos mais procurados` |
| `alta qualidade` / `qualidade premium` | 具体描述（材质、工艺、参数） |
| `melhor do mercado` | 删 |
| `frete grátis` | 删（Shopee 自带） |
| `produto original` | 删 |
| `para todos os tipos de pele` | 按说明书写适用人群 |
| `testado dermatologicamente` | 删（除非有报告） |

### 6.6 侵权类（🟡→🔴 要查授权）

**高风险品牌（举例）**：Nike, Adidas, Puma, Samsung, Apple, Xiaomi, Sony, Dyson, Lululemon, Supreme, Rolex, Gucci, Louis Vuitton, Versace, Ford, Toyota, Volkswagen, Chevrolet, Fiat, Huawei, Amazon, Natura, Boticário, Avon, Lancôme, L'Oréal, Disney, Marvel, Pokemon, Sanrio, Lego, Nintendo

| 情况 | 判定 |
|---|---|
| 品牌名用在标题/详情做商品标识 | 🔴 需授权，否则 [133] 下架 |
| 明写 `réplica` `contrafé` `falso` `falsificado` `cópia não autorizada` `pirata` `look alike` `inspired` | 🔴 直接定性，[602]/[603] |
| 图片上有别人 logo | 🟡 查授权 |
| 写 `compatível com X` / `para X` / `modelo compatível` | ✅ **不是侵权**（Lei 9.279/1996 art. 132 II 指示性使用） |
| 品牌名是产品通用词（vidro, maleta, case, bolsa, cabide…） | 🟡 看上下文，默认按侵权 |

### 6.7 标题质量类（🟢 低 —— 不扣分但会被下架）

| 情况 | 平台码 |
|---|---|
| 关键词堆砌 | [506] |
| 品牌堆砌 | [507] |
| 描述不足（<120 字符） | [605] 中等，**扣分** |
| 图片差/缺图 | [606] |
| 类目错误 | [613] / [612] |
| 品牌字段不准 | [301] |
| 尺寸重量不准 | [120] |
| 变体数据滥用 | [309] |
| 引导站外 | [112] 中等 |
| 误导折扣/划线价 | [105] / [405] |

---

## 7. 第 5 步：收口定处置（把问题变成动作）

**这一步是整个流程的枢纽。** 前面四步收集问题，这里把它们变成动作，然后分流到三个出口。

### 7.0 ★ 收口决策树（照着走）

```
              【商品问题总表】
                     │
        ┌────────────┴────────────┐
        │  有没有 🔴 致命？        │
        └────────────┬────────────┘
              是 │        │ 否
                 │        │
      ┌──────────▼──┐  ┌──▼──────────────────┐
      │ §7.2 致命分支│  │ 有没有"缺资质"？    │
      │ 不上架        │  └──┬──────────────────┘
      │ 出清单给店主  │     │ 是         │ 否
      │ ★ 到此结束   │     │            │
      └──────────────┘  ┌──▼──────┐  ┌──▼──────────────┐
                      │ §10     │  │ §7.3 普通分支    │
                      │ 出工单   │  │ 逐行定动作       │
                      │ ★ 到此   │  └──┬──────────────┘
                      │ 结束     │     │
                      └─────────┘  ┌──┴──────────────────┐
                                    │ §7.4 动作怎么落地   │
                                    │ 改写 → §8          │
                                    │ 查授权 → 挂起等结果 │
                                    └─────────────────────┘
                                             │
                                             ↓
                                    ┌─────────────────────┐
                                    │ §7.6 复检（必做）    │
                                    │ 改完重新判一遍        │
                                    └──────────┬──────────┘
                                               ↓
                                    ┌─────────────────────┐
                                    │ §11 交报告           │
                                    └─────────────────────┘
```

### 7.1 严重度 → 动作对照

| 严重度 | 平台说法 | 扣处罚点 | 你该做什么 |
|---|---|---|---|
| 🔴 **致命** Extrema | 枪支、毒品、赌博、假证、成人、野生动物 | ✅ 扣 | **不上架**。有疑问先问 |
| 🔴 **高** Alta | ANVISA/ANATEL/Inmetro 禁限、烟酒药、汽配无认证、图片侵权 | ✅ 扣 | **先查资质**，无资质不上架 |
| 🟡 **中** Média | 描述不足、受限品违规、站外导流、超重 | ✅ 扣 | **必须改**；改不了就下架 |
| 🟢 **低** Baixa | 标题堆词、类目错、品牌错、图片差、重复 | ❌ 不扣 | **能改就改**；不改也能留 |

> **扣处罚点 ≠ 立刻封号。** 但致命和高危类反复出现，会累积到账号处罚带，限制持续 14–28 天。**致命类一次都不能漏。**

### 7.2 ★ 致命分支（命中就到此为止）

**命中条件**（任一）：

| # | 条件 | 来自 |
|---|---|---|
| 1 | 标题或详情出现 §6.1 禁售类的词 | §6.1 |
| 2 | 变体带不准确的尺寸重量 | [517] |
| 3 | 明写 `réplica` `contrafé` `pirata` `look alike` | §6.6 |
| 4 | 外形抄袭注册外观设计 | [603] |
| 5 | 之前被平台删除的商品重新上架 | §5.2 |

**这一分支的做法**：

```
1. 停 —— 不再看其他字段（结论已经定了）
2. 记到「建议下架清单」：行号 | 命中词 | 依据码 | 严重度
3. ★ 不要自己删 —— 等店主确认（见 §7.5）
4. 继续审下一个商品
```

**注意**：致命分支的商品**也要看完全部四步**再定 —— 因为一个商品可能既有致命问题又有能改的问题。改的部分还是要改。

### 7.3 普通分支：逐行定动作

总表里每一行，落到下面四种动作之一：

| 动作 | 什么情况 | 做什么 | 之后去哪 |
|---|---|---|---|
| **改写** | 文案能解决（功效宣称、空洞描述、模板化、拼写、话术残留） | 按 §8 改 | §7.6 复检 |
| **查授权** | 品牌名/logo 命中 | 找店主确认有没有授权书 | 挂起，等结果 |
| **出工单** | 缺注册号/认证 | 按 §10 填工单 | 不进改写 |
| **无需处理** | 误报豁免（§9）或 🟢 低且改不动 | 记一行"无需处理" | 继续 |

**一个商品可以同时有多个动作** —— 比如「改写」+「查授权」。

### 7.4 动作怎么落地（三个出口）

| 出口 | 什么时候走 | 产出物 |
|---|---|---|
| **出口 A：改写** | 总表里有"改写"行 | 新标题 + 新详情 → 进 §7.6 复检 |
| **出口 B：工单** | 总表里有"出工单"行 | 工单清单 → 交店主，不进改写 |
| **出口 C：挂起** | 总表里有"查授权"行 | 待确认清单 → 等店主回复 |

> **★ 出口 A 和 B 可以同时存在**：文案该改的改，缺资质的出工单 —— **但缺资质的商品即使文案改干净了，也不能上架**。

### 7.5 下架红线（★）

> **没有店主对具体商品的明确同意，不要下架任何商品。**

| 你可以做 | 你不可以做 |
|---|---|
| 列出建议下架清单（行号 + 触线词 + 严重度） | 直接把商品删掉 |
| 在报告里标"建议下架" | 因为"规则说要禁"就自己下架 |
| 说"这 3 个建议不上架" | 顺手把"看起来差不多"的也删了 |

**清单模板**：

```
建议下架（待店主确认）：
  行 20  | à prova d'água      | 标题禁售宣称  | 致命
  行 74  | Retinol              | 标题药品词    | 高
  行 101 | Resultado em 30 dias | 时间承诺      | 中
```

### 7.6 ★★ 复检（改写之后，必做）

**这是最容易漏的一步，也是最值钱的一步。**

**为什么**：改写会引入新问题。**你自己改的地方，可能是下一个错误。**

> **真实事故**：一条没有边界的替换规则把 `Separador` 改成了 `Separadesconforto`；一句自己手写的安全提示（`não substitui acompanhamento profissional`）触发了违规词典。

### 7.6.1 复检清单（对每个改过的商品）

| # | 检查什么 | 怎么查 | 不合格怎么办 |
|---|---|---|---|
| 1 | **原来删掉的词，还有没有漏网的** | 把 §6.3/§6.4/§6.5 的词在改后文案里再搜一遍 | 补删 |
| 2 | **有没有引入新触线词** | 把 §6.3/§6.4/§6.5 在改后文案里再搜一遍 | 补改 |
| 3 | **有没有引入中文/法语** | 找中文字符；找 `nécessaire` `obligatoire` `déjà` | 删 |
| 4 | **有没有粘连词** | 对照 §8.5 的 27 形态 | 拆开 |
| 5 | **残句修好了吗** | 对照 §8.5 的 11 条残句 | 修 |
| 6 | **首句合格吗** | 含商品实词？和其他商品重复？ | 重写首句 |
| 7 | **六段结构齐吗** | 按 §3.2 六段逐段对 | 补 |
| 8 | **长度够吗** | 详情 ≥500 字符；标题 60–95 字符 | 补 |
| 9 | **标题没被切坏** | 末尾不是悬空断词 | 重写结尾 |
| 10 | **有没有和别的商品一字不差** | 和同批其他商品的首句+主体比 | 逐句改写 |
| 11 | **逗号空洞** | 看有没有 `,,` `, ,` 这种 | 整段重写 |
| 12 | **改写前后语义一致** | 新文案说的还是同一个东西吗 | 修正 |

### 7.6.2 复检结论

```
→ 产出：【最终问题清单】（改写后还剩什么）
→ 全部通过 → 进 §11 交报告
→ 还有问题 → 再改一轮，改完再复检（最多 3 轮）
→ 3 轮还不过 → 挂"待复核"，交店主，不要硬改
```

### 7.7 ★ 交给下一步

```
→ 产出：
   【商品问题总表】已填满动作
   【最终问题清单】复检后的残留
   【建议下架清单】致命分支的（有则）
   【工单清单】缺资质的（有则）
   【待确认清单】查授权的（有则）

→ 下一步：
   有改写 → §8 改写标准 → §7.6 复检
   有工单 → §10 工单格式
   全部完成 → §11 交报告
```

### 7.8 工单模板（缺资质类）

```
商品：行号 47 | SKU xxxx
缺什么：ANVISA 注册号
依据：SBR-LV-009（[503] sem informação de registro）
建议：补证后上架；无证则下架
```

---

## 8. 改写标准（要改成什么样）

### 8.1 改写优先级

```
1. 删掉违规承诺（最容易见效）
2. 换掉医疗/药品词
3. 把绝对化改成具体描述
4. 把空洞宣称换成实参数
5. 补齐六段结构
6. 修正葡语拼写和重音
```

### 8.2 触线 → 中性 替换表（可直接抄）

| 触线 | 改成 |
|---|---|
| garante / garantido / garantia | pode auxiliar / auxilia em / pode oferecer |
| Anti-Idade / Antirrugas | Cuidados com a pele |
| clareador / clareamento | esfoliante |
| Lifting Facial | Tratamento |
| Cicatrizante | Cuidados com a pele |
| Anti-inflamatório | Calmante para a pele |
| Analgésico | Relaxante |
| Antidepressivo / Ansiolítico | 删除 |
| Antisséptico / Antibacteriano | Higienico |
| Terapêutico | tratamento（慎用） |
| bactéria / vírus / germes | microorganismos |
| pós-cirúrgica | fase de cuidado / uso doméstico |
| veterinária | especialista em pets |
| Curativo | Adesivo |
| Joanete / Martelo | Dedos |
| Medicamento / uso tópico | 删除 / uso externo |
| reembolso / troca grátis | 全删 |
| 100% garantido / 100% seguro | 全删 |
| Antifraude | Decorativo |
| Antiembaçante | Antivisão Embaçada |
| proporcionar（各种变位） | facilitar |
| emagrece / modela | 删除 / design |
| Redutor de medidas | 删除 |

### 8.3 品类专属改写标准

**化妆品**

| ❌ | ✅ |
|---|---|
| `Anti-idade` `Rugas` `Firming` `Lifting` `Rejuvenescimento` | `Cuidados com a pele` |
| `Cura acne` `Elimina manchas` | `Auxilia na rotina de skincare` |
| `100% seguro` `Garantido` | `Pode auxiliar` |
| `Todos os tipos de pele` | `Pele normal a seca`（按实物） |
| `Testado dermatologicamente` | 删 |
| `Tipo: Cosmético` | `Cosmético`（按真实类别） |

**不能靠改文案解决的**：化妆品必须有 **ANVISA 注册号**。把 "Anti-idade" 改成 "Cuidados" 解决不了这个问题。**没注册号就不上架**，不管文案改得多干净。

**汽配**

| ❌ | ✅ |
|---|---|
| `Homologado`（无认证号） | 删，或写实际认证机构 |
| `Original` `Novo`（描述来源不明） | 删 |

> **注意**：汽配/工业品类里，`Cura` `Tratamento` `Profissional` `Substitui` `Firma` `Inspeção` `Certificação` 这些词在**化工和免责声明语境里是正常的** —— 别误伤。详见 §9。

**药品保健品**

| ❌ | ✅ |
|---|---|
| `Cura` `Emagrece` `Garantido` `Eficaz` | `Pode auxiliar` |
| `tarja` `prescrição` `controlado` | 删除 |
| 具体病名 | 删除 |
| `100% natural` | 删 |

**太阳镜**

- ❌ `UV400` `Proteção UV` `lente escura`
- ✅ 去掉数字宣称，写 `com lentes escuras`
- ⚠️ **但实质合规要 INMETRO 的 UV 实测报告** —— 文字改过只是文字层过关。

**儿童安全用品**

- ❌ 直接承诺安全
- ✅ 加 `Uso com supervisão de um adulto`
- ✅ 加 `Não use por menores de [X] anos`
- ⚠️ **实质要 INMETRO 认证**

### 8.4 反模板化：改写后必须自己看一遍

**下面的现象任一出现，说明这批改写是套模板的，必须重做：**

| 现象 | 为什么是问题 |
|---|---|
| 同一句话在一批商品里出现 5 次以上 | 批量味 |
| 两个商品的详情**一字不差** | 最严重的问题 |
| `✅` 出现 4 次以上 | 套模板 |
| 同一句 `Quer X mais forte` 反复出现 | 套模板 |
| 首句不含商品实词 | 空泛 |
| 标题里同时有 3 个以上形态词 | 矛盾 |

> **首句唯一率必须 100%。** 不是"首句种类数"达标就行 —— 111 种 vs 245 条商品，人工看过去还是模板。

**首句要写成这样：**

```
✅ Saco de malha transparente para organizar livros e materiais.
✅ Suporte de pia fixado na parede para esponjas e utensílios.
✅ Kit de 4 potes de vidro com tampa para guardar temperos.
❌ Item para organizar a rotina, com capacidade ampla e alça confortável.
❌ Produto versátil que atende às suas necessidades.
```

### 8.5 翻译机器味（改写后逐条检查）

改写工具常见错误 —— **单词粘在一起**：

| 错误 | 改成 |
|---|---|
| `uniformementeizar` | `uniformizar` |
| `uniformementeemente` | `uniformemente` |
| `aplicaruniformemente` | `espalhar uniformemente` |
| `espalharuniformemente` | `espalhar uniformemente` |
| `distribuiruniformemente` | `distribuir uniformemente` |
| `parauniformizar` | `para uniformizar` |
| `euniformemente` | `e uniformemente` |
| `pressãouniformemente` | `pressão uniformemente` |
| `v[íi]trees` | `vidros` |
| `produtouniformementemente` | `produto uniformemente` |
| `eelasticidade` | `elasticidade` |

> ⚠️ **`proporcional` 不算错** —— 它是形容词，正常词，别去动它。

**残句**（改写工具留下的病句）：

| 错误 | 改成 |
|---|---|
| `para auxilia` | `para auxiliar` |
| `A design` / `a design` | `O design` / `o design` |
| `rotina de rotina` | `rotina` |
| `Conforto e Conforto` | `Conforto` |
| `Cintura Alta Cintura` | `Cintura Alta` |
| `cuidado com a pele com cuidado` | `cuidado com a pele` |
| `uso geral e uso doméstico` | `uso doméstico` |
| `garantir maior` | `buscar maior` |
| `garantir que` | `para que` |
| `beaconchegante` | `e aconchegante` |
| `permitevariados` | `permite variados` |
| `leitidas` | `lidas` |

**还有一类：批量替换把并列结构打出了空洞**

```
❌ Adequado para, e todos os tipos de.
❌ Adequado para,, palmas manchadas, ...,,,,,, auxilia nos cuidados...,, 
```

> 这种病句规则救不了 —— **整段手工重写。**

### 8.6 葡语重音速查（常见错）

| 错 | 对 |
|---|---|
| pratico | prático |
| confortavel | confortável |
| diario | diário |
| especificacoes | especificações |
| aplicacao | aplicação |
| tendencia | tendência |
| hidratacao | hidratação |
| oleo | óleo |
| serum | sérum |
| mascara | máscara |
| E original | É original |
| frequencia | frequência |
| experiencia | experiência |

**格式**

| 项 | 标准 |
|---|---|
| 容量 | `30ml` `50g`（小写） |
| 防晒 | `FPS 15`（葡语用 FPS 不是 SPF） |
| 时长 | `12 horas`（葡语用复数） |
| 货币 | `R$ 99,90` |
| 小数 | 逗号：`19x2,5cm` |

### 8.7 改完必须做的 3 件事

| # | 动作 | 为什么 |
|---|---|---|
| 1 | **从头再读一遍改后的详情全文** | 扫描器数字归零 ≠ 内容正确 |
| 2 | **再搜一遍刚才删掉的词** | 改写会引入新违规词 |
| 3 | **检查自己刚改的地方** | 你的修改本身可能是下一个错误 |

> **真实事故**：一条没有边界的替换规则把 `Separador` 改成了 `Separadesconforto`；一句自己手写的安全提示（`não substitui acompanhamento profissional`）触发了违规词典。**改完必须再看一遍。**

### 8.8 ★ 交给下一步

```
→ 产出：【新标题】+【新详情】（每个改过的商品一份）
→ ★ 下一步：§7.6 复检 —— 12 项复检清单，逐条过
→ ★ 不要直接跳到交报告 —— 复检没做 = 这次审核不算完成
```

---

## 9. 豁免清单（不要误伤）

**看到这些词不要直接判违规。** 误伤比漏判更常见，也更伤商品。

| # | 情况 | 正确处理 |
|---|---|---|
| **EX-TOOLS** | **工具类**：faca, facas, tesoura, tesouras, chave de fenda, chave phillips, alicate, estilicho, multiplasca, canivete | ✅ **豁免**，不算武器 |
| **EX-CE** | **CE 标志事实陈述**：`produto impresso com selo CE` | ✅ 记录但不拦截 |
| **EX-HERMES** | **Hermes 出现在物流语境**：entrega / transportadora / expresso / frete / logística + Hermes | 🟡 默认按侵权，**看上下文** |
| **EX-REDUZIR** | **`reduzir`**：`reduzir a entrada de água` `reduzir escorregões` | ✅ 功能描述，保留 |
| **EX-DESCONFORTO** | **`desconforto`**：`em caso de desconforto, suspenda o uso` | ✅ 安全提示，保留 |
| **EX-SEGURO** | **`seguro` 作功能**：`fechamento seguro` `encaixe seguro` `trava segura` `suporte seguro` `fixação segura` | ✅ 功能描述，保留 |
| **EX-BRAND-GENERIC** | **品牌名是通用词**：vidro, maleta, case, bolsa, cabide, suporte, organizador, abertura, fechadura | 🟡 看上下文，**默认仍按侵权** |
| **EX-COMPAT** | **兼容说明**：`compatível com X` `para X` `modelo compatível` | ✅ **不是侵权**（Lei 9.279/1996 art. 132 II） |
| **EX-CHEMICAL** | **汽配/工业语境**：`Cura` `Tratamento` `Profissional` `Substitui` `Firma` `Inspeção` `Certificação` | ✅ 化工术语和免责声明，**不是**医疗宣称 |

> **★ 最后一条（EX-CHEMICAL）特别重要。** 这六个词在化妆品里是违规宣称，在汽配和化工里是正常术语。**先定类别再判词**（§1）。

> **误报控制的价值高于"扫描器数字归零"。** 把 `desconforto`、`seguro` 这些安全提示和功能描述全改掉，会让详情读起来像机器人，还降低了合规性。

### 9.1 ★ 什么时候用这张表

**这张表在两个地方用**：

| 什么时候 | 怎么用 |
|---|---|
| **判命中词时**（§5A 合并总表前） | 命中了先查这里 —— 是豁免就不进总表 |
| **复检时**（§7.6） | 确认改写没有把豁免的词误删了 |

> **★ 第二种情况最容易被忽略。** 改写时把 `reduzir` `desconforto` `seguro` 这些合规的功能描述和安全提示一起删掉 —— 详情读起来像机器人，还白白损失了原本正确的合规表达。**复检时要确认它们还在。**

### 9.2 ★ 交给下一步

```
→ 产出：【豁免记录】—— 每条豁免都要记一行，说明为什么豁免
  行号 | 命中词 | 豁免依据 | 为什么
  -----+-------+---------+------
  12   | faca  | EX-TOOLS | 菜刀是工具，不是武器

→ ★ 交给 §11 报告：豁免记录也要附上
→ ★ 店主可能会问"为什么这个没改" —— 有记录才答得上来
```

---

## 10. 无法靠改文案解决的（出工单，不要批量改）

**这些商品的合规性由商品本体决定，改文案无效。**

| 品类 | 监管方 | 关键词 | 需要什么 |
|---|---|---|---|
| **化妆品** | ANVISA | cosmético, batom, base, sérum, hidratante, desodorante, pó facial, protetor solar, sabonete facial | ANVISA 注册号 + 责任主体 |
| **器械/矫形** | ANVISA | joelheira, cotoveleira, compressa, cinta abdominal, tala, aparelho de pressão, massageador, furo auricular | 器械注册与资质 |
| **宠物口腔** | MAPA | escova dental pet, spray bucal pet, espuma dental pet, tártaro pet, halitose pet | 兽药资质，或改成纯清洁宣称 |
| **化学制剂** | ANVISA | cola, epoxy, resina, primer, selante, cera automotiva, solução de limpeza, vedante, espuma expansiva, desengraxante | 包装含成分/警示/批号/有效期 |
| **太阳镜** | INMETRO | óculos de sol, lente escura | UV 实测报告 + 认证 |
| **儿童安全** | INMETRO | trava de segurança infantil, protetor de canto, bloqueador de roda, cesto de bebê, cadeira de bebê | INMETRO 认证 |

**处理流程**

```
命中 → 是上表品类吗？
  是 → 出工单（行号 + 缺什么资质 + 建议）→ 不进批量改写
  否 → 进改写流程 → 改完重读 → 抽样人工读
```

### 10.1 ★ 交给下一步

```
→ 产出：【工单清单】（模板见 §7.8）
→ ★ 这批商品：文案改不改都先放着
→ ★ 关键：文案改干净 ≠ 可以上架 —— 缺资质就是缺资质
→ 下一步：工单交店主 → 等资质结果 → 有资质才走 §7.3 定上架
```

---

## 11. 报告怎么写

**每次审核完，交一份报告。** 六节，顺序固定：

```
## 1. 摘要              —— 审了多少商品、结论分布、需人工处理几个
## 2. 数据缺口          —— 没查到的部分（没有就写"无"）
## 3. 需决策的发现      —— 要店主拍板的
## 4. 待复核的发现      —— 需要人看一眼的
## 5. 逐商品结果        —— 每个商品一条
## 6. 已查阅规则        —— 用到的规则和依据
```

> **第 2 节不能省。** 它把"没查"和"查过没问题"分开。省了它，店主会以为所有商品都过了审。

**摘要写法（给店主的数字对）**

```
本次审核 158 个商品。
致命 3 个（建议不上架）、高 12 个（需资质或改文案）、中 41 个（需修改）、
低 23 个（建议优化）、通过 79 个。
改写后已复检 62 个，全部通过。
```

**不要写**"整体状况良好""基本合规"这种话 —— **给数字对**。

### 11.1 ★ 报告要带上前面五张清单

**审完不是只交一份报告就完了。** 前面五张清单是报告的证据，必须一起交：

| 清单 | 交到报告哪一节 | 格式 |
|---|---|---|
| 类目卡 | §5 逐商品结果 | 字段 |
| 标题问题清单 | §5 逐商品结果 | 表格 |
| 详情问题清单 | §5 逐商品结果 | 表格 |
| 图片问题清单 | §5 逐商品结果 | 表格 |
| 属性问题清单 | §5 逐商品结果 | 表格 |
| **商品问题总表**（已填动作） | §3 需决策 / §4 待复核 | 表格 |
| 建议下架清单 | §3 需决策的发现 | 表格 |
| 工单清单 | §3 需决策的发现 | 表格 |
| 待确认清单（查授权） | §4 待复核的发现 | 表格 |
| 最终问题清单（复检后） | §5 逐商品结果 | 表格 |

### 11.2 ★ 交给下一步（流程终点）

```
→ 产出：【审核报告】6 节 + 全部清单
→ 下一步：交店主
→ ★ 店主可能回复三类：
   · 确认下架清单 → 才执行下架
   · 补资质 → 重新走 §7.3 定上架
   · 指出判错的 → 重新走 §1 审这一批
```

---

## 12. 审核员自查（交工前问自己）

### 12.1 流程完整性

| # | 问题 | 过 |
|---|---|---|
| 1 | 每个商品都**先定了类目**？ | □ |
| 2 | 每个商品都过了标题、详情、图片、属性四关？ | □ |
| 3 | 每一步的问题清单都写了？**空的也写了"无"**？ | □ |
| 4 | 五张清单合并成总表了？重复的合并了？ | □ |
| 5 | 总表里**每行都有动作**？ | □ |

### 12.2 判定准确性

| # | 问题 | 过 |
|---|---|---|
| 6 | 每个禁售品类都查过了？ | □ |
| 7 | 每个命中的词都过了一遍 §9 豁免清单？ | □ |
| 8 | 高风险品牌都查了授权？ | □ |
| 9 | 汽配/化工类目额外对照了 §9 的 EX-CHEMICAL？ | □ |

### 12.3 处置正确性

| # | 问题 | 过 |
|---|---|---|
| 10 | 缺资质的都出工单了，没混进改写清单？ | □ |
| 11 | 建议下架的都列出来了，**没有自己删**？ | □ |
| 12 | 拿不准的挂"待复核"了而不是自己拍板？ | □ |

### 12.4 改写质量

| # | 问题 | 过 |
|---|---|---|
| 13 | 改完做了 §7.6 复检（12 项逐条过）？ | □ |
| 14 | 改写的文案**从头读了一遍**？ | □ |
| 15 | 改写有没有引入中文/法语/粘连词？ | □ |
| 16 | 有没有商品详情和其他商品一字不差？ | □ |
| 17 | 首句唯一率 100%？ | □ |

### 12.5 交付完整性

| # | 问题 | 过 |
|---|---|---|
| 18 | 报告第 2 节（数据缺口）写了？ | □ |
| 19 | 摘要写的是**具体数字**，不是"基本合规"？ | □ |
| 20 | 五张清单都附在报告后面了？ | □ |

> **第 13 项是最容易漏的。** 没做复检 = 这次审核不算完成。

---

## 13. 平台处罚与解封（店主须知）

| 处罚 | 触发 | 能恢复吗 |
|---|---|---|
| 账号冻结（IP 类） | 品牌方投诉 + 平台审核 | **只有品牌方撤销投诉才能恢复** |
| 账号冻结（监管机构类） | Anvisa / Inmetro / 农业部 | **必须原投诉机构书面同意** |
| 下架（IPR） | 商标/版权/专利/外观 | 申诉路径：Contestar → 品牌方决定 |
| 删除（`excluído`） | listing 违规 | **不可恢复**，且计入处罚点 |
| 封禁（`banimento`） | 严重违规 | 问题解决后**可恢复** |
| 限制触达（`alcance limitado`） | 轻度违规 | 整改后**自动恢复** |

> **审批通过 ≠ 解封成功。** 案件要记录**平台侧的实际状态**。

**处罚点机制**：每周一归属 → 一周后生效 → 限制持续 14–28 天 → 每条已认定违规可申诉一次。

**五大 NCL 高风险类目**

| NCL | 类目 | 高风险品牌 |
|---|---|---|
| 03 | 化妆品/个人卫生 | Natura / Boticário / Avon / Lancôme / L'Oréal |
| 09 | 电子/科技 | Apple / Samsung / Sony / Xiaomi / Huawei / Beats / JBL |
| 18 | 皮革/仿皮 | LV / Gucci / Hermès / Chanel / Prada / Coach / MK / Burberry |
| 25 | 服装/鞋帽 | Nike / Adidas / Puma / Supreme / TNF / Champion / Levi's |
| 28 | 玩具/游戏 | Disney / Marvel / Pokemon / Sanrio / Lego / Nintendo |

---

## 14. 改录依据（这份手册的来源）

所有判定标准都来自本仓库的机器可读资产，**不是拍脑袋写的**：

| 来源 | 内容 |
|---|---|
| `rules/01_prohibited_restricted_items.json` | 17 条禁售/受限规则（PI + RI） |
| `rules/02_ip_trademark_copyright.json` | 8 条知识产权规则（IP） |
| `rules/03_listing_violations_duplicates.json` | 17 条刊登与重复规则（LV + DUP） |
| `rules/04_cases_relist_authorization.json` | 5 条案件/重发/授权规则（RL + AU + AC） |
| `rules/05_medicines_health.json` | 3 条药品健康规则（MED） |
| `research/violation_codes.json` | 106 个平台处罚码（严重度 + 是否扣分） |
| `lexicon/exemptions.json` | 7 条误报豁免规则 |
| `lexicon/non_avoidable.json` | 6 类无法靠文字规避的品类 |
| `lexicon/rewrite_map.json` | 触线 → 中性替换表 |
| `lexicon/quality_patterns.json` | 15 条套模板/批量味特征 |

**发现手册和规则库不一致时**：以 `rules/*.json` 为准，并提出来更正本手册。

---

## 15. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-10-28 | 初版：由 50 条规则 + 106 个处罚码 + 7 条豁免 + 6 类无法规避 + 15 条质量特征生成的纯手工审核手册 |
| 1.1.0 | 2026-10-28 | **强化流程衔接**：原版 §2-§6 是并列清单，步骤之间无状态传递。改为带交接的九步流程 —— ① 每步加「★ 交给下一步」段（产出 + 带上什么 + 关键提醒 + 与下一步的衔接逻辑）；② 新增 §1.3 两条硬分支（禁售/缺资质 → 提前退出）；③ 新增 §5A 五张清单合并成商品问题总表（去重 + 每行必须有动作）；④ §7 重写为收口枢纽，新增 §7.0 收口决策树、§7.2 致命分支、§7.3 逐行定动作、§7.4 三个出口、§7.6 复检 12 项清单、§7.7 交接；⑤ 新增 §8.8 / §9.1 / §9.2 / §10.1 / §11.1 / §11.2 交接段；⑥ 豁免表补「什么时候用」（判命中 + 复检防误删）；⑦ §12 自查从 12 项平铺改为 5 组 20 项 |
