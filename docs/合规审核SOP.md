# Shopee巴西合规审核SOP

# 1. 文件说明

本文为Shopee巴西站商品合规审核SOP    文档编号:

包含合规判定标准、审核操作流程、词库豁免规则、异常处理、报告交付

分为操作部分、步骤细则、附录部分

使用Ctrl\+F进行内容搜索，使用左侧章节进行浏览

## 1.1 适用平台

- 适用站点

    - 信息仅针对shopee巴西站编制

## 1.2 配套文档

- 本SOP为**操作层**文档。判定原理与铁律来源见 `docs/SOP_COMPLIANCE_REVIEW.md`，工程契约见 `PROJECT_RULES.md`。

- **纯手工执行**时，每一步的检查清单、关键词判定表、豁免清单见 `docs/MANUAL_REVIEW.md`。

- **批量/脚本执行**时，扫描工具、xlsx 处理铁律、运行环境见 `docs/USER_SOP.md`。

| 文档 | 面向谁 | 回答什么 |
|---|---|---|
| 本文 `docs/合规审核SOP.md` | 全员 | 一份可执行、可填写的作业手册 |
| `docs/MANUAL_REVIEW.md` | 人工审核员 | 每一步怎么判（清单、词表、动作） |
| `docs/USER_SOP.md` | 运营 / 开发 | 流程怎么走（工具、命令、铁律） |
| `docs/SOP_COMPLIANCE_REVIEW.md` | 判定层 | 什么算违规，铁律为什么这么定 |

## 1.3 变更记录

- 生效日期

- 更新记录

# 2. 合规审核流程概况

## 2.1 审核流程总览

```
步骤 0  定位源文件        ← 找不到就停下来问，别猜
   ↓
步骤 1  读入并标准化      ← 转成统一商品模型，原始文件不动
   ↓
步骤 2  字段完整性检查    ← 缺数据 ≠ 违规，先分清"没数据"和"有问题"
   ↓
步骤 3  定类目            ← 同一个词在不同类别意思不同
   ↓
步骤 4  看标题            ─┐
步骤 5  看详情            ├ 每步产出一张问题清单
步骤 6  看图片            │
步骤 7  看属性           ─┘
   ↓
步骤 8  合并问题总表      ← 五张清单合一，每行定一个动作
   ↓
步骤 9  扫描 + 上下文判定  ← 命中是信号，不是结论
   ↓
步骤 10 人工分流 / 收口    ← 致命 / 缺资质 / 可改写，三条路
   ↓
步骤 11 改写              ← 按替换表改
   ↓
步骤 12 复检              ← ★ 改完必须再判一遍
   ↓
步骤 13 豁免核对          ← 确认没把合规表达误删
   ↓
步骤 14 无法规避分流      ← 缺资质出工单，不进改写
   ↓
步骤 15 交付与留痕        ← 报告 + JSON + 可回溯的记录
```

## 2.2 每一步的产出物

审核不是走完八个环节就完事 —— 每一步都要产生一样东西，交给下一步。

| 步骤 | 产出物 | 交给谁 |
|---|---|---|
| 0 | 【文件路径】+【副本路径】+【源文件哈希】 | 步骤 1 |
| 1 | 【统一商品模型】 | 步骤 2 |
| 2 | 【未评估项清单】 | 步骤 3 |
| 3 | 【类目卡】 | 步骤 4-9 |
| 4 | 【标题问题清单】 | 步骤 8 |
| 5 | 【详情问题清单】 | 步骤 8 |
| 6 | 【图片问题清单】 | 步骤 8 |
| 7 | 【属性问题清单】 | 步骤 8 |
| 8 | 【商品问题总表】（每行有动作） | 步骤 9-10 |
| 9 | 【命中清单 + 判定结论】 | 步骤 10 |
| 10 | 【动作清单】 | 步骤 11 / 14 |
| 11 | 【新标题】+【新详情】 | 步骤 12 |
| 12 | 【最终问题清单】 | 步骤 13-15 |
| 13 | 【豁免记录】 | 步骤 15 |
| 14 | 【工单清单】 | 步骤 15 |
| 15 | 【报告】+【全部清单】 | 店主 |

**空清单也要写"无"** —— 空清单和"还没看"是两回事。

# 3. 合规基础逻辑（必了解）

## 3.1 词库命中是信号，不是结论

**这是整套审核的地基。** 词库只负责筛出可疑项，最终判定必须看上下文。

| 命中类型 | 处理 |
|---|---|
| 真违规 | 进改写 / 处置流程 |
| 描述性用法（如 "reduzir a entrada de água" = 描述功能） | **保留**，记为误报豁免 |
| 描述性用法但表述暧昧 | 改写成无歧义的写法 |

> **误报控制的价值高于"扫描器数字归零"。** 把 `desconforto`（安全提示）、`seguro`（功能描述）这类词全部改掉，反而会降低合规性。

## 3.2 缺数据不等于通过

| 状态 | 含义 | 你会看到什么 |
|---|---|---|
| `missing` | 字段在，但这次没数据 | 报告里该规则显示「未评估」 |
| `unknown` | 有值但无法确定 | 报告里显示「待复核」 |
| `not_applicable` | 这个商品本来就没这个字段 | 不出现在结果里 |
| `pending_verification` | 有风险，但要等外部确认 | 出现在「待复核」清单 |

> **早期版本因为把「缺 images 列」当成「图片违规」，15 个商品 100% 误报。** 看报告时永远先看第 2 节「数据缺口与未评估项」。

## 3.3 先定类目，再判词

**同一个词在不同类别意思完全不同。**

| 词 | 化妆品 | 汽配 / 化工 |
|---|---|---|
| `Cura`（治愈） | 🔴 违规医疗宣称 | ✅ 化工术语 / 免责声明 |
| `Firma`（密封） | — | ✅ 正常术语 |
| `Certificação` | — | ✅ 正常术语 |
| `Inspeção` | — | ✅ 正常术语 |

| 类目 | 关键词识别 | 用哪套判定表 |
|---|---|---|
| **化妆品** | batom, base, sérum, hidratante, pó, protetor solar | §5.3.3 + §5.9 |
| **汽配** | componente automotivo, peça de carro, óleo, filtro | §5.3.6 + §5.9 |
| **电池** | pilha, bateria, power bank | §5.3.2 |
| **酒类** | cerveja, vinho, destilado, licor | §5.3.2 |
| **药品保健品** | remédio, suplemento, vitamina | §5.3.2 + §5.3.3 |
| **兽药** | medicamento pet, veterinário, antiparasitário | §5.3.2 |
| **太阳镜** | óculos de sol, lente escura | §5.3.7 |
| **儿童安全** | trava infantil, cesto de bebê, carrinho | §5.3.7 |
| **其他** | — | 通用清单 |

## 3.4 六条硬约束

**任何处置都不能违反。**

| ID | 约束 | 落地含义 |
|---|---|---|
| **H1** | IP 类结论恒为 `signal` + 强制人工复核 | 关键词/logo 命中只是筛查信号；只有权利人投诉、书面授权或平台投诉通知才能确立侵权 |
| **H2** | `block`/`freeze_relist`/`escalate_legal` 只来自 `platform_official`/`law` 的 `active` 规则 | 内部风险建议、AI 推断最高只能到 `flag_for_review` |
| **H3** | 输入缺失 → 该规则不评估 + 必须上报 `unevaluated` | **不得当作通过** |
| **H4** | `source.excerpt` 必须逐字出现在抓取件中 | 不编造引文 |
| **H5** | `artifact_ref` 只存引用，不内嵌凭证内容 | 授权书不要内嵌进报告 |
| **H6** | `freeze_relist`/`escalate_legal` 为 `human_only` | 自动化不得代做 |

## 3.5 平台处罚严重度对照

| 严重度 | 平台说法 | 扣处罚点 | 典型情形 |
|---|---|---|---|
| 🔴 **致命** Extrema | 枪支、毒品、赌博、假证、成人、野生动物 | ✅ 扣 | §5.3.1 |
| 🔴 **高** Alta | ANVISA/ANATEL/Inmetro 禁限、烟酒药、汽配无认证、图片侵权 | ✅ 扣 | §5.3.2 / §5.3.6 |
| 🟡 **中** Média | 描述不足、受限品违规、站外导流、超重 | ✅ 扣 | §5.3.7 |
| 🟢 **低** Baixa | 标题堆词、类目错、品牌错、图片差、重复 | ❌ 不扣 | §5.3.7 |

> **扣处罚点 ≠ 立刻封号。** 但致命和高危类反复出现，会累积到账号处罚带，限制持续 14–28 天。**致命类一次都不能漏。**

点击下方链接阅读：
[Shopee巴西卖家中心 - 禁售与下架原因](https://seller.br.shopee.cn/edu/article/5139)
[平台处罚码完整清单](https://shopee.cn/edu/article/5139)

# 4. 审核操作部分

## 4.1 概述

本文档操作部分按**步骤 0-15** 展开。审核员按顺序执行，每步结束确认已产出该步的清单。

**纯手工执行**时，配合 `docs/MANUAL_REVIEW.md` 使用 —— 那里有每一步的完整检查清单和关键词判定表。

## 4.2 步骤 0：定位源文件

**多店文件不一定在本机。先定位，再动手。**

```bash
# 按店铺目录找
ls /config/dianshang/_ad_analysis/raw/_store_<store>/

# 按文件名全盘找
find /config -iname "*mass_update*"

# 用报告里的 PID 反查
for pid in <PIDs>; do
  find /config -name "*.xlsx" | while read f; do
    unzip -p "$f" xl/sharedStrings.xml 2>/dev/null | grep -q "$pid" && echo "$f"
  done
done
```

| # | 做什么 | 判据 |
|---|---|---|
| 1 | 用上述三种方式定位源文件 | 找到**实际文件路径** |
| 2 | 确认这个文件确实是你要审的那一批 | 抽查 3 个 PID 的标题能对上 |
| 3 | 找到就复制一份到工作区，**不动原件** | 原始输入不得被覆盖或修改 |

**停下来的情况**：PID 一个都查不到 = 文件不在本机。
→ **直接请用户上传。不要基于审核报告"重建"文件。**

> 审核报告只给**问题清单**，不给**商品原文**。报告里一句"用词不自然"是没法还原成实际内容的。

### 4.2.1 源文件登记表

| 项目 | 内容 |
|---|---|
| 店铺名 | |
| 店铺 ID | |
| 源文件路径 | |
| 副本路径 | |
| 源文件哈希（sha256） | |
| 商品总数 | |
| 定位日期 | |
| 经手人 | |

## 4.3 步骤 1-2：读入并标准化 + 字段完整性检查

### 4.3.1 读入并标准化

- Excel 仅作**输入**，导入后统一转成 `data/schema/product.schema.json` 定义的商品模型

- 解析失败 / 字段缺失 → **记 error，不中断整批**

- 保留溯源信息（文件路径 + 内容哈希 + 解析时间 + 解析器版本）—— **没有溯源的输入不得进入审核链路**

### 4.3.2 字段完整性检查（扫描之前先做）

| 缺失字段 | 处理 | 你在报告里看到 |
|---|---|---|
| `title` | 该记录**不参与审核**，记 error | 该商品缺 title 记录 |
| `description` | 相关规则标记未评估 | 「未评估：description」 |
| `images` | 图片类规则标记未评估 | 「未评估：images」 |
| `brand` | 品牌类规则标记未评估 | 「未评估：brand」 |
| `category` | 类目规则标记未评估 | 「未评估：category」 |

### 4.3.3 xlsx 处理铁律（8 条，做之前必须知道）

| # | 铁律 | 踩坑后果 |
|---|---|---|
| 1 | 用 sharedStrings 引用，不用 inlineStr | 部分软件不识别 inlineStr |
| 2 | **只替换 C/D 列，绝不删 A/B/E**（PID 一字不动） | 商品对不上号 |
| 3 | 列字母在前：`r="C7"` 不是 `r="7C"` | 文件打不开 |
| 4 | 保持 `s="3"` 样式属性 | 格式全乱 |
| 5 | `activePane "bottom_left"` → `"bottomLeft"`（驼峰） | 卖家中心拒收 |
| 6 | 控制字符必删：`\x00-\x08\x0B\x0C\x0E-\x1F\x7F` | 详情页显示乱码 |
| 7 | regex 不能跨界吃单元格（用 `(?:(?!</c>).)*`） | 串行污染 |
| 8 | `openpyxl max_row` 不可信（用 `len(ws.iter_rows())`） | 漏掉尾行商品 |

> **DISPIMG（WPS 私有内嵌图）保图**：`wb.save()` 会丢图 → 必须走 zipfile patch 路径，只替换 `sheet1.xml` + `sharedStrings.xml`，`media/` `cellimages.xml` `drawings/` `_rels/` 原样保留。

### 4.3.4 运行环境铁律（不设这行就跑不动）

> Hermes 运行时会把 `LD_LIBRARY_PATH` 指向自带目录，其中的 `libcrypto.so.3` 与系统 OpenSSL 冲突 → `ssl` 模块直接 ImportError。

```bash
env -u LD_LIBRARY_PATH python3 script.py
```

**必须在进程启动前清掉**（脚本内 `os.environ.pop` 已太晚，ssl 已被运行时导入）。

**任何调用 HTTPS 的脚本都要用 `env -u LD_LIBRARY_PATH` 启动。**

### 4.3.5 未评估项清单

| 商品行号 | 缺失字段 | 受影响规则 | 备注 |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

## 4.4 步骤 3：定类目

**30 秒，决定后面用哪张判定表。**

### 4.4.1 类目卡（每商品一张）

```
商品编号：____
类目：□ 化妆品  □ 汽配  □ 电池  □ 酒类  □ 药品保健品  □ 兽药
      □ 太阳镜  □ 儿童安全  □ 普通商品
判定依据：标题/详情里看到的：____________
```

### 4.4.2 ★ 两条硬分支（命中就立刻停，别往下走）

| 命中 | 立刻停在哪 |
|---|---|
| 标题或详情出现 **§5.3.1 禁售类**的词 | **§5.5 致命分支** —— 不上架，直接出清单给店主 |
| 类目是化妆品/太阳镜/儿童安全，**且没有对应注册号或认证** | **§5.10 缺资质** —— 出工单，不进改写 |

> **这两条是流程里唯一的"提前退出"。** 命中就别再往下审了 —— 后面看了也白看，结论已经定了。

## 4.5 步骤 4：看标题（12 项）

**标题是最容易中招的地方。** 平台先扫标题，而且标题里的禁售词 = 直接不上架。

| # | 检查什么 | 什么算不合格 | 严重度 | 判定表 |
|---|---|---|---|---|
| 1 | **禁售品类词** | 武器/烟草/毒品/化学品/赌博/证件/野生动物/成人 | 🔴 致命 | §5.3.1 |
| 2 | **品牌名** | 标题里出现别的品牌（Nike / Adidas / Apple / Samsung / Gucci…） | 🟡 要查授权 | §5.3.6 |
| 3 | **品牌堆砌** | 标题里塞了 2 个以上品牌 | 🟢 低（[507]） | §5.3.7 |
| 4 | **关键词堆砌** | 标题是一长串不相关词；或标题超过约 120 字符 | 🟢 低（[506]） | §5.3.7 |
| 5 | **形态词矛盾** | 同时出现 3 个以上形态词（pomada / creme / gel / spray / sérum / máscara / pó / óleo…） | 🟡 需核实实物 | §5.7.10 |
| 6 | **年龄不符** | 标题写 `infantil` / `kids` 但实际是成人用品；或反之 | 🟢 低（[510]） | §5.3.7 |
| 7 | **功效承诺** | `cura` / `garantido` / `elimina` / `milagroso` / `emagrece` / `resultado garantido` | 🟡 要改（[337]） | §5.3.3 |
| 8 | **时间承诺** | `resultado em 30 dias` / `em 2 semanas` | 🟡 要改 | §5.3.3 |
| 9 | **英文残留** | 标题或详情里有英文（Anti-Aging / Firming / Wrinkles / Lifting…） | 🟡 要改 | §5.3.3 |
| 10 | **葡语错误** | 重音错、拼写错、逗号写成小数点 | 🟡 要改 | §5.7.9 |
| 11 | **末尾悬空** | 标题最后一个词是 `de` `da` `para` `com` `vi` `pa` 这类断词 | 🟡 要改 | §5.7.5 |
| 12 | **GTIN / 编号** | 缺 GTIN 或货号（平台要用来比重复） | 🟢 低（[307]） | §4.7 |

### 4.5.1 标题的合格标准

| 项 | 标准 |
|---|---|
| 长度 | 60–95 字符（**不超过 120**） |
| 结构 | 空格分隔关键词，**不要用分隔逗号** |
| 数字 | 葡语小数用逗号：`19x2,5cm`（不是 19x2.5cm） |
| 形态词 | 最多 1–2 个，与实物一致 |
| 品牌 | 只有真能用才写，且最多 1 个 |
| 结尾 | 不能是悬空断词 |

### 4.5.2 标题问题清单

| 商品行号 | 命中词/问题 | 严重度 | 判定表 |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

## 4.6 步骤 5：看详情（20 项）

| # | 检查什么 | 什么算不合格 | 严重度 | 判定表 |
|---|---|---|---|---|
| 1 | **长度** | 少于 120 字符 → 平台直接判"描述不足" | 🟡 中（[605] **扣分**） | §5.3.7 |
| 2 | **长度** | 剥掉模板和链接后少于 250 字符 → 内容太薄 | 🟡 要补充 | §5.7.5 |
| 3 | **长度** | 少于 500 字符 → 缺"使用方法"和"包装内容"两段 | 🟡 要补充 | §5.7.5 |
| 4 | **功效承诺** | `cura` `garantido` `garantia` `eficaz` `elimina` `definitivo` `total` `milagroso` `emagrece` `resultados garantidos` | 🟡 要改（[337]） | §5.3.3 |
| 5 | **疾病宣称** | 出现具体病名：`psoríase` `eczema` `dermatite` `acne` `manchas` `queda de cabelo` `cravos` | 🟡 要改 | §5.3.4 |
| 6 | **医疗词** | `medicamento` `antisséptico` `antibacteriano` `anti-inflamatório` `analgésico` `antidepressivo` `ansiolítico` `terapêutico` | 🟡 要改或删 | §5.3.3 |
| 7 | **绝对化用语** | `100%` `original` `melhor` `o mais` `total` `para todos` `todos os tipos` | 🟡 要改 | §5.3.5 |
| 8 | **商标词** | 品牌名出现（除非是兼容说明） | 🟡 要查授权 | §5.3.6 |
| 9 | **外链/导流** | 网址、WhatsApp、Telegram、"请加微信"、站外联系方式 | 🟡 中（[112]） | §5.3.7 |
| 10 | **残留话术** | 店铺名、客服话术、物流话术（`Bem-vindos à loja...` / `Nossa equipe...` / `Os pedidos são preparados...`） | 🟡 要删 | §5.7.1 |
| 11 | **图片链接** | 详情里塞了店铺图片 URL（`cf.shopee.com.br/file/...`） | 🟡 要删 | §5.7.1 |
| 12 | **中文残留** | 任何中文字符 | 🟡 要删 | §5.7.7 |
| 13 | **法语残留** | `nécessaire` `obligatoire` `déjà` `très bien` | 🟡 要删 | §5.7.7 |
| 14 | **翻译机器味** | 单词粘连：`uniformementeizar` `aplicaruniformemente` `parauniformizar` | 🟡 要改 | §5.7.7 |
| 15 | **空洞宣称** | `Material premium` `Acabamento cuidadoso` `Confortavel` `Produto de alta qualidade` | 🟡 要改成具体描述 | §5.7.1 |
| 16 | **产地统一** | 所有商品都写 `Origem: China` | 🟡 要按实物改 | §5.7.1 |
| 17 | **类目模板** | 首饰/工具类却写 `Tipo: Cosmético` | 🟡 要改 | §5.7.10 |
| 18 | **测试宣称** | `Testado dermatologicamente` | 🟡 要删（无证据） | §5.3.5 |
| 19 | **拼写错误** | 葡语拼写错、双空格、缺空格 | 🟡 要改 | §5.7.9 |
| 20 | **残句** | `para auxilia` / `A design` / `rotina de rotina` / `uso geral e uso doméstico` | 🟡 要改 | §5.7.7 |

### 4.6.1 详情问题清单

| 商品行号 | 命中词/问题 | 严重度 | 判定表 |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

## 4.7 步骤 6：看图片（7 项）

| # | 检查什么 | 什么算不合格 | 严重度 | 判定表 |
|---|---|---|---|---|
| 1 | **数量** | 少于 1 张 | 🟢 低（[606]） | §5.3.7 |
| 2 | **质量** | 模糊、纯白底无商品、与商品无关 | 🟢 低（[606]） | §5.3.7 |
| 3 | **第三方 logo** | 图里有别的品牌 logo、字标、压印 | 🟡 要查授权 | §5.3.6 |
| 4 | **Shopee logo** | 用了 Shopee 的 logo 或 banner | 🟡 中（[608]） | §5.3.7 |
| 5 | **外卖平台 logo** | 背包/袋子上有 iFood / Rappi / delivery app 的 logo | 🟡 中（[349]） | §5.3.6 |
| 6 | **版权图** | 用了盗图、带水印、"todos os direitos reservados" | 🟡 要换（[602]） | §5.3.6 |
| 7 | **工业设计** | 外形抄袭了注册外观设计 | 🔴 转法务（[603]） | §5.3.6 |

> **图片里的 logo 是独立触发条件** —— 即使标题和详情都干净，图上有别人的 logo 一样会被下架。

### 4.7.1 图片问题清单

| 商品行号 | 命中词/问题 | 严重度 | 判定表 |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

## 4.8 步骤 7：看属性 / 类目 / 品牌（9 项 + 跨店 7 项）

### 4.8.1 属性检查清单

| # | 检查什么 | 什么算不合格 | 严重度 | 判定表 |
|---|---|---|---|---|
| 1 | **类目正确** | 选错类目（尤其受限品放错类目） | 🟢 低（[613]/[612]） | §5.3.7 |
| 2 | **品牌准确** | 品牌字段空、或与实际不符 | 🟢 低（[301]） | §5.3.7 |
| 3 | **尺寸重量** | 尺寸重量没填、填错 | 🟢 低（[120]） | §5.3.7 |
| 4 | **尺寸超限** | 超出 Shopee 允许的重量/尺寸 | 🟡 中（[508]/[509]） | §5.3.7 |
| 5 | **注册信息** | 化妆品/电器/汽车件/医疗器械缺 ANVISA / ANATEL / INMETRO / MAPA 注册号或认证 | 🟡 要补证（[503]-[505]） | **§5.10** |
| 6 | **年龄等级** | 年龄段和类目/标题对不上 | 🟢 低（[510]） | §5.3.7 |
| 7 | **变体滥用** | 变体里塞价格/规格混乱数据 | 🟢 低（[309]） | §5.3.7 |
| 8 | **变体尺寸** | 变体带不准确的尺寸重量 | 🔴 致命（[517]） | §5.5 |
| 9 | **GTIN** | 缺 GTIN | 🟢 低（[307]） | §5.3.7 |

### 4.8.2 跨店 / 重复检查（如果有多个店铺）

| # | 检查什么 | 说明 | 严重度 |
|---|---|---|---|
| 10 | **同店重复** | 同一店两个商品内容几乎一样 | 🟡 中（[401]） |
| 11 | **跨店重复** | 同款商品在多个店铺都上了（**包括你自己家的店**） | 🟡 中（[302]） |
| 12 | **换皮重发** | 之前被下架的商品，改个标题或换 SKU 重新上 | 🔴 冻结重发（[401]） |
| 13 | **未结案件** | 商品还挂在未关闭的违规案件上 | 🟡 中 |
| 14 | **已被删** | 商品是平台删掉的，删掉不可恢复 | 🔴 冻结重发 |
| 15 | **处罚点** | 账号有处罚点 | 🟡 要查 |
| 16 | **申诉中** | 处罚点申诉还没到期 | 🟡 别重发 |

### 4.8.3 属性问题清单

| 商品行号 | 命中词/问题 | 严重度 | 判定表 |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

## 4.9 步骤 8：合并问题总表

**这一步是衔接的关键。** 四张清单是分开记的，到这里要合并成一张总表。

### 4.9.1 合并去重

同一个词可能在标题和详情都出现 —— **算一条，不是两条**（严重度取高的）。

| 原样 | 合并后 |
|---|---|
| 标题清单：`cura` 🟡 | **详情清单：`cura` 🟡** | → 总表一条：`cura` 🟡 改写 |

### 4.9.2 总表格式（每商品一张）

```
商品编号：____   类目：____

| # | 命中词/问题 | 出现在 | 严重度 | 判定表 | 动作 |
|---|------------|--------|--------|--------|------|
| 1 | cura        | 标题+详情 | 🟡    | §5.3.3   | 改写 |
| 2 | Nike        | 详情     | 🟡    | §5.3.6   | 查授权 |
| 3 | 缺 ANVISA   | 属性     | 🟡    | §5.10    | 出工单 |
```

**动作只有四种：改写 / 查授权 / 出工单 / 不上架**

**每行都要有动作，没有就填"无需处理"。空动作 = 没判完。**

### 4.9.3 商品问题总表

| 商品编号 | 类目 | # | 命中词/问题 | 出现在 | 严重度 | 判定表 | 动作 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |

# 5. 判定与处置

## 5.1 概述

步骤 9-14 把问题变成动作。**这一部分决定"什么算违规"和"怎么办"。**

**纯手工执行**时，配合 `docs/MANUAL_REVIEW.md` 使用 —— 那里手册 §6 是关键词判定表、手册 §9 是豁免清单。

## 5.2 步骤 9：扫描 + 上下文判定

### 5.2.1 匹配铁律（按重要度排序）

| # | 铁律 | 反例 → 正例 |
|---|---|---|
| 1 | **单词边界 `\bword\b`**，不要子串匹配 | `antidade` ≠ `quantidade` |
| 2 | **葡语动词必含全部变位** | `\bproporciona\w*\b` 而非 `\bproporciona\b` |
| 3 | **形容词 ≠ 同根动词** | ❌ `\bproporcional\b` ✅ `\bproporciona(m\|r\|do\|da\|das\|mos)\b` |
| 4 | **大小写同时匹配** | `[Pp]ara garantir\b` |
| 5 | **大小写不敏感 + 变体归一** | `N1ke→nike`、`@pple→apple` |
| 6 | **描述性用法 ≠ 承诺用法** | `garantir conforto` ≠ `garantido` |
| 7 | **重音折叠仅用于匹配**，输出保留原形 | |

### 5.2.2 葡语 `\b` 不可靠（已知坑，必须避）

> 葡语的 `\b` 会吞掉相邻单词的首字母。

```python
# ❌ 错误 —— 会吞掉 "Óculos" 的首字母
re.sub(r'\s*at[óo]xico\b\s*', ' ', s)

# ✅ 正确 —— 显式排除字母边界
re.sub(r'(?<![a-zA-Zà-ÿÀ-ß])at[óo]xico(?![a-zA-Zà-ÿÀ-ß])', ' ', s)
```

**所有葡语关键词匹配一律用显式 lookaround。**

### 5.2.3 全字段扫描

> **漏检教训**：标题仅 6% 命中，详情 94% 命中 → **标题 + 详情 + 属性 + 品牌全扫**，不能只扫标题。

### 5.2.4 扫描工具怎么用

```bash
# 单条扫
env -u LD_LIBRARY_PATH python3 tools/scan_lexicon.py \
  --title "标题" --description "详情" --brand "品牌"

# 批量扫（商品 JSON）
env -u LD_LIBRARY_PATH python3 tools/scan_lexicon.py --input products.json

# 扫描器自检（回归用例）
env -u LD_LIBRARY_PATH python3 tools/scan_lexicon.py --self-test
```

### 5.2.5 词库资产

| 文件 | 用途 | 规模 |
|---|---|---|
| `lexicon/term_groups.json` | 词组（扫描用） | 37 组 / 856 词 |
| `lexicon/rewrite_map.json` | 触线 → 中性替代（改写用） | 8 类映射 |
| `lexicon/exemptions.json` | 误报豁免规则 | 7 条 |
| `lexicon/quality_patterns.json` | 套模板/批量味检测 | 15 条特征 |
| `lexicon/non_avoidable.json` | 无法文字规避的品类 | 6 类 |
| `lexicon/verb_conjugations.json` | 葡语动词变位匹配表 | 7 个动词 |

## 5.3 关键词判定表

**这是审核员最常用的一张表。** 看到一个词 → 查这里 → 定结论。

### 5.3.1 禁售类（🔴 致命 —— 不上架）

| 品类 | 关键词（葡语） | 平台码 | 备注 |
|---|---|---|---|
| **武器** | arma de fogo, revólver, pistola, escopeta, taser, colete à prova de balas, munição | [317] | **菜刀/剪刀/螺丝刀/美工刀不算**（§5.9 EX-TOOLS） |
| **烟草电子烟** | cigarro, charuto, cachimbo, tabaco, vape, juice, nicotina, narguil, pods, atomizador | [311] | 电子烟配件也禁 |
| **毒品管制药** | droga, medicamento controlado, tarja preta, tarja vermelha, aborto, abortivo, injetável, estimulante sexual, antidepressivo, minoxidil | [313] | 分红标/黑标 |
| **化工易燃爆炸** | explosivo, nitrogênio, gasolina, diesel, acetona, produto químico bruto, corrosivo, trinitrotolueno | [332] | |
| **假币证件** | dinheiro, real, nota, cartão, clonador, jammer, documentos falsificados | [341] | |
| **赌博数字商品** | jogo de azar, loteria online, aposta, caixa misteriosa, itens digitais | [338] | |
| **政府徽章制服** | insígnia, brasão, uniforme militar, policial, item oficial governamental | [516] | |
| **野生动物** | animais vivos, partes de animais selvagens, espécies ameaçadas, fauna, flora | [339] | |
| **成人内容** | pornográfico, conteúdo adulto, sexo, explícito | [320] | |
| **未巴氏消毒乳制品** | leite cru, queijo artesanal, iogurte artesanal, manteiga artesanal | [342] | 工业巴氏杀菌密封装**可以** |

### 5.3.2 受限类（🟡 要资质 —— 缺证就不能上）

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

### 5.3.3 功效宣称类（🟡 要改 —— [337] 中等严重度，**扣分**）

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

### 5.3.4 疾病名类（🟡 要改 —— 只要出现具体病名就删）

| 词 |
|---|
| `psoríase` `eczema` `dermatite` `acne` `manchas` `cravos` `queda de cabelo` `cólera` `fungos` `bactérias` `vírus` `germes` |

> `bactérias` `vírus` `germes` → 改成 `microrganismos`。

### 5.3.5 营销/绝对化类（🟡 要改）

| ❌ | ✅ |
|---|---|
| `mais vendido` / `best seller` | `um dos mais procurados` |
| `alta qualidade` / `qualidade premium` | 具体描述（材质、工艺、参数） |
| `melhor do mercado` | 删 |
| `frete grátis` | 删（Shopee 自带） |
| `produto original` | 删 |
| `para todos os tipos de pele` | 按说明书写适用人群 |
| `testado dermatologicamente` | 删（除非有报告） |

### 5.3.6 侵权类（🟡→🔴 要查授权）

**高风险品牌（举例）**：Nike, Adidas, Puma, Samsung, Apple, Xiaomi, Sony, Dyson, Lululemon, Supreme, Rolex, Gucci, Louis Vuitton, Versace, Ford, Toyota, Volkswagen, Chevrolet, Fiat, Huawei, Amazon, Natura, Boticário, Avon, Lancôme, L'Oréal, Disney, Marvel, Pokemon, Sanrio, Lego, Nintendo

| 情况 | 判定 |
|---|---|
| 品牌名用在标题/详情做商品标识 | 🔴 需授权，否则 [133] 下架 |
| 明写 `réplica` `contrafé` `falso` `falsificado` `cópia não autorizada` `pirata` `look alike` `inspired` | 🔴 直接定性，[602]/[603] |
| 图片上有别人 logo | 🟡 查授权 |
| 写 `compatível com X` / `para X` / `modelo compatível` | ✅ **不是侵权**（Lei 9.279/1996 art. 132 II 指示性使用） |
| 品牌名是产品通用词（vidro, maleta, case, bolsa, cabide…） | 🟡 看上下文，默认按侵权 |

### 5.3.7 标题质量类（🟢 低 —— 不扣分但会被下架）

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

## 5.4 步骤 10：人工分流 / 收口

**这一步是整个流程的枢纽。** 前面收集问题，这里把它们变成动作，然后分流到三个出口。

### 5.4.1 收口决策树

```
              【商品问题总表】
                     │
        ┌────────────┴────────────┐
        │  有没有 🔴 致命？        │
        └────────────┬────────────┘
              是 │        │ 否
                 │        │
      ┌──────────▼──┐  ┌──▼──────────────────┐
      │ §5.5 致命分支│  │ 有没有"缺资质"？    │
      │ 不上架        │  └──┬──────────────────┘
      │ 出清单给店主  │     │ 是         │ 否
      │ ★ 到此结束   │     │            │
      └──────────────┘  ┌──▼──────┐  ┌──▼──────────────┐
                      │ §8      │  │ §5.6 普通分支    │
                      │ 出工单   │  │ 逐行定动作       │
                      │ ★ 到此   │  └──┬──────────────┘
                      │ 结束     │     │
                      └─────────┘  ┌──┴──────────────────┐
                                    │ §5.7 动作怎么落地   │
                                    │ 改写 → §5.7        │
                                    │ 查授权 → 挂起等结果 │
                                    └─────────────────────┘
                                             │
                                             ↓
                                    ┌─────────────────────┐
                                    │ §5.9 复检（必做）    │
                                    │ 改完重新判一遍        │
                                    └──────────┬──────────┘
                                               ↓
                                    ┌─────────────────────┐
                                    │ §7 交报告           │
                                    └─────────────────────┘
```

### 5.4.2 逐行定动作

总表里每一行，落到下面四种动作之一：

| 动作 | 什么情况 | 做什么 | 之后去哪 |
|---|---|---|---|
| **改写** | 文案能解决（功效宣称、空洞描述、模板化） | 按 §5.7 改 | §5.8 复检 |
| **查授权** | 品牌名/logo 命中 | 找店主确认有没有授权书 | 挂起，等结果 |
| **出工单** | 缺注册号/认证 | 按 §5.10 填工单 | 不进改写 |
| **无需处理** | 误报豁免（§5.9）或 🟢 低且改不动 | 记一行"无需处理" | 继续 |

**一个商品可以同时有多个动作** —— 比如「改写」+「查授权」。

### 5.4.3 动作怎么落地（三个出口）

| 出口 | 什么时候走 | 产出物 |
|---|---|---|
| **出口 A：改写** | 总表里有"改写"行 | 新标题 + 新详情 → 进 §5.9 复检 |
| **出口 B：工单** | 总表里有"出工单"行 | 工单清单 → 交店主，不进改写 |
| **出口 C：挂起** | 总表里有"查授权"行 | 待确认清单 → 等店主回复 |

> **★ 出口 A 和 B 可以同时存在**：文案该改的改，缺资质的出工单 —— **但缺资质的商品即使文案改干净了，也不能上架**。

## 5.5 致命分支（命中就到此为止）

**命中条件**（任一）：

| # | 条件 | 来自 |
|---|---|---|
| 1 | 标题或详情出现 §5.3.1 禁售类的词 | §5.3.1 |
| 2 | 变体带不准确的尺寸重量 | [517] |
| 3 | 明写 `réplica` `contrafé` `pirata` `look alike` | §5.3.6 |
| 4 | 外形抄袭注册外观设计 | [603] |
| 5 | 之前被平台删除的商品重新上架 | §4.8.2 |

**这一分支的做法**：

```
1. 停 —— 不再看其他字段（结论已经定了）
2. 记到「建议下架清单」：行号 | 命中词 | 依据码 | 严重度
3. ★ 不要自己删 —— 等店主确认（见 §5.8）
4. 继续审下一个商品
```

**注意**：致命分支的商品**也要看完全部四步**再定 —— 因为一个商品可能既有致命问题又有能改的问题。改的部分还是要改。

### 5.5.1 建议下架清单

```
建议下架（待店主确认）：
  行 20  | à prova d'água      | 标题禁售宣称  | 致命
  行 74  | Retinol              | 标题药品词    | 高
  行 101 | Resultado em 30 dias | 时间承诺      | 中
```

## 5.6 下架红线（★）

> **没有店主对具体商品的明确同意，不要下架任何商品。**

| 你可以做 | 你不可以做 |
|---|---|
| 列出建议下架清单（行号 + 触线词 + 严重度） | 直接把商品删掉 |
| 在报告里标"建议下架" | 因为"规则说要禁"就自己下架 |
| 说"这 3 个建议不上架" | 顺手把"看起来差不多"的也删了 |

## 5.7 步骤 11：改写

### 5.7.1 改写优先级

```
1. 删掉违规承诺（最容易见效）
2. 换掉医疗/药品词
3. 把绝对化改成具体描述
4. 把空洞宣称换成实参数
5. 补齐六段结构
6. 修正葡语拼写和重音
```

### 5.7.2 触线 → 中性 替换表（可直接抄）

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

### 5.7.3 详情页六段结构（标准模板）

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

### 5.7.4 长度护栏

| 检查 | 阈值 | 失败处理 |
|---|---|---|
| 详情长度 | ≥ 500 字符 | 补「Como usar」+「Conteúdo da embalagem」两段 |
| 剥模板/剥 URL 后长度 | ≥ 250 字符 | 过短 → 按标题生成基础描述 |
| 标题长度 | 60–95 字符（上限 100） | 见 §5.7.5 |

### 5.7.5 标题截断铁律

> **截断必须在词边界，不能裸切。**

```python
cut = new[:95]
sp = cut.rfind(' ')
new = cut[:sp].rstrip(' ,;:-') if sp > 60 else cut.rstrip(' ,;:-')
```

**配套铁律**：

1. 截断后跑「末尾悬空词」检测：`\b(de|da|do|para|com|em|a|o|e|pa|vi)$`
2. **标题被截断 = 语义也丢了** → 回源标题补，不是简单砍短
3. 标题与详情品类不一致 → **以详情为准**统一，并同步修详情里的指代

### 5.7.6 反模板化：首句唯一率必须 100%

> 店主 2026-09-17 亲自审阅 491 个商品：**110 优先核实 / 331 修改补证 / 50 基本可读**。
> **491 个商品的详情完全相同** —— 全用统一模板。这是店主判定"最严重"的问题。

**"首句种类数"这个指标本身具有欺骗性** —— 111 种 vs 245 条商品，人工看过去还是模板。
→ **验收指标是首句唯一率 100%，不是"种类数"。**

**"套模板/批量味"特征（任一即打回）**：

- `✅` 出现 4 次以上
- 同一句 "Quer X mais forte" 出现 5+ 次
- `new_desc` 一字不差的 2+ 商品
- 含医疗词 / 含中文
- 标题里同时出现 `pomada`/`creme`/`gel`/`cream`/`loção`/`spray`/`sérum`/`máscara`/`pó`/`óleo` 中的 3 个以上
- 重复用 `moderno`/`tendência`/`atual`/`inovador`

### 5.7.7 PT-BR 机器翻译残留（27 个形态族）

| 族 | 示例 → 修正 |
|---|---|
| 副词当动词 | `uniformementeizar` → `uniformizar` |
| 副词多一个 e | `uniformementeemente` → `uniformemente` |
| 动词粘副词 | `aplicaruniformemente` → `espalhar uniformemente` |
| 动词粘副词 | `espalharuniformemente` → `espalhar uniformemente` |
| 动词粘副词 | `distribuiruniformemente` → `distribuir uniformemente` |
| 介词粘动词 | `parauniformizar` → `para uniformizar` |
| 连词粘副词 | `euniformemente` → `e uniformemente` |
| 副词粘名词 | `euniformementeização` → `e uniformização` |
| 名词粘副词 | `pressãouniformemente` → `pressão uniformemente` |

> ⚠️ **`proporcional` 不许动** —— 它是形容词，正常词，别去动它。

### 5.7.8 残句修复（改写工具留下的病句）

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

### 5.7.9 葡语重音速查（常见错）

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

### 5.7.10 品类专属改写标准

**化妆品**

| ❌ | ✅ |
|---|---|
| `Anti-idade` `Rugas` `Firming` `Lifting` `Rejuvenescimento` | `Cuidados com a pele` |
| `Cura acne` `Elimina manchas` | `Auxilia na rotina de skincare` |
| `100% seguro` `Garantido` | `Pode auxiliar` |
| `Todos os tipos de pele` | `Pele normal a seca`（按实物） |
| `Testado dermatologicamente` | 删 |
| `Tipo: Cosmético` | `Cosmético`（按真实类别） |

> **不能靠改文案解决的**：化妆品必须有 **ANVISA 注册号**。把 "Anti-idade" 改成 "Cuidados" 解决不了这个问题。**没注册号就不上架**。

**汽配**

| ❌ | ✅ |
|---|---|
| `Homologado`（无认证号） | 删，或写实际认证机构 |
| `Original` `Novo`（描述来源不明） | 删 |

> **注意**：汽配/工业品类里，`Cura` `Tratamento` `Profissional` `Substitui` `Firma` `Inspeção` `Certificação` 这些词在**化工和免责声明语境里是正常的** —— 别误伤。详见 §5.9 EX-CHEMICAL。

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
- ⚠️ **但实质合规要 INMETRO 的 UV 实测报告**

**儿童安全用品**

- ❌ 直接承诺安全
- ✅ 加 `Uso com supervisão de um adulto`
- ✅ 加 `Não use por menores de [X] anos`
- ⚠️ **实质要 INMETRO 认证**

### 5.7.11 单遍替换铁律

> **顺序逐条 `re.sub` 必然产生级联污染。**

```python
# ❌ 错误：级联
for pat, rep in RULES:
    text = re.sub(pat, rep, text)
# 'auxiliar a auxiliar a auxiliar a reduzir'   ← 3 层嵌套

# ✅ 正确：单遍合并正则 + 分派函数
parts, mapping = [], {}
for i, (pat, rep) in enumerate(RULES):
    name = f'R{i}'
    parts.append(f'(?P<{name}>{pat})')
    mapping[name] = rep
COMBINED = re.compile('(?i)' + '|'.join(parts))

def dispatch(m):
    for name, rep in mapping.items():
        if m.group(name) is not None:
            return rep
    return m.group(0)

text = COMBINED.sub(dispatch, text)   # 每个位置只匹配一次
```

**配套铁律**：

1. 替换值要选**不会被任何其他 pattern 匹配**的词（如用 `contribui para` 而不是 `auxiliar a`）
2. 若必须顺序执行，每条规则的替换值后要加**反向清理规则**
3. 替换值里**绝不写字符类**（`Anti-inc[ôo]modo` 会原样输出）
4. 实测效果：655 → 10 触线命中，零级联

### 5.7.12 改写记录表

| 商品行号 | 原标题 | 新标题 | 改写要点 | 复检通过 |
|---|---|---|---|---|
| | | | | □ |
| | | | | □ |
| | | | | □ |

## 5.8 步骤 12：复检（改写之后，必做）

**这是最容易漏的一步，也是最值钱的一步。**

**为什么**：改写会引入新问题。**你自己改的地方，可能是下一个错误。**

> **真实事故**：一条没有边界的替换规则把 `Separador` 改成了 `Separadesconforto`；一句自己手写的安全提示（`não substitui acompanhamento profissional`）触发了违规词典。

### 5.8.1 复检清单（对每个改过的商品）

| # | 检查什么 | 怎么查 | 不合格怎么办 |
|---|---|---|---|
| 1 | **原来删掉的词，还有没有漏网的** | 把 §5.3.3/§5.3.4/§5.3.5 的词在改后文案里再搜一遍 | 补删 |
| 2 | **有没有引入新触线词** | 把 §5.3.3/§5.3.4/§5.3.5 在改后文案里再搜一遍 | 补改 |
| 3 | **有没有引入中文/法语** | 找中文字符；找 `nécessaire` `obligatoire` `déjà` | 删 |
| 4 | **有没有粘连词** | 对照 §5.7.7 的 27 形态 | 拆开 |
| 5 | **残句修好了吗** | 对照 §5.7.8 的残句表 | 修 |
| 6 | **首句合格吗** | 含商品实词？和其他商品重复？ | 重写首句 |
| 7 | **六段结构齐吗** | 按 §5.7.3 六段逐段对 | 补 |
| 8 | **长度够吗** | 详情 ≥500 字符；标题 60–95 字符 | 补 |
| 9 | **标题没被切坏** | 末尾不是悬空断词 | 重写结尾 |
| 10 | **有没有和别的商品一字不差** | 和同批其他商品的首句+主体比 | 逐句改写 |
| 11 | **逗号空洞** | 看有没有 `,,` `, ,` 这种 | 整段重写 |
| 12 | **改写前后语义一致** | 新文案说的还是同一个东西吗 | 修正 |
| 13 | **豁免的词还在吗** | 对照 §5.9，确认 `reduzir` `desconforto` `seguro` 等没被误删 | 恢复 |

### 5.8.2 复检结论

```
→ 产出：【最终问题清单】（改写后还剩什么）
→ 全部通过 → 进 §7 交报告
→ 还有问题 → 再改一轮，改完再复检（最多 3 轮）
→ 3 轮还不过 → 挂"待复核"，交店主，不要硬改
```

## 5.9 步骤 13：豁免核对

**看到这些词不要直接判违规。** 误伤比漏判更常见，也更伤商品。

| 编号 | 情况 | 正确处理 |
|---|---|---|
| EX-TOOLS | **工具类**：faca, facas, tesoura, tesouras, chave de fenda, chave phillips, alicate, estilicho, multiplasca, canivete | ✅ **豁免**，不算武器 |
| EX-CE | **CE 标志事实陈述**：`produto impresso com selo CE` | ✅ 记录但不拦截 |
| EX-HERMES | **Hermes 出现在物流语境**：entrega / transportadora / expresso / frete / logística + Hermes | 🟡 默认按侵权，**看上下文** |
| EX-REDUZIR | **`reduzir`**：`reduzir a entrada de água` `reduzir escorregões` | ✅ 功能描述，保留 |
| EX-DESCONFORTO | **`desconforto`**：`em caso de desconforto, suspenda o uso` | ✅ 安全提示，保留 |
| EX-SEGURO | **`seguro` 作功能**：`fechamento seguro` `encaixe seguro` `trava segura` `suporte seguro` `fixação segura` | ✅ 功能描述，保留 |
| EX-BRAND-GENERIC | **品牌名是通用词**：vidro, maleta, case, bolsa, cabide, suporte, organizador, abertura, fechadura | 🟡 看上下文，**默认仍按侵权** |
| EX-COMPAT | **兼容说明**：`compatível com X` / `para X` / `modelo compatível` | ✅ **不是侵权**（Lei 9.279/1996 art. 132 II） |
| EX-CHEMICAL | **汽配/工业语境**：`Cura` `Tratamento` `Profissional` `Substitui` `Firma` `Inspeção` `Certificação` | ✅ 化工术语和免责声明，**不是**医疗宣称 |

> **★ EX-CHEMICAL 特别重要。** 这六个词在化妆品里是违规宣称，在汽配和化工里是正常术语。**先定类别再判词**（§3.3）。

### 5.9.1 ★ 什么时候用这张表

| 什么时候 | 怎么用 |
|---|---|
| **判命中词时**（合并总表前） | 命中了先查这里 —— 是豁免就不进总表 |
| **复检时**（§5.8） | 确认改写没有把豁免的词误删了 |

> **★ 第二种情况最容易被忽略。** 改写时把 `reduzir` `desconforto` `seguro` 这些合规的功能描述和安全提示一起删掉 —— 详情读起来像机器人，还白白损失了原本正确的合规表达。

### 5.9.2 豁免记录表

| 商品行号 | 命中词 | 豁免依据 | 为什么 |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

## 5.10 步骤 14：无法靠改文案解决的

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
  是 → 生成工单（行号 + 缺什么资质 + 建议）→ 不进批量改写
  否 → 进入改写流水线 → 改写后复检 → 抽样人工读
```

### 5.10.1 工单清单

```
商品：行号 47 | SKU xxxx
缺什么：ANVISA 注册号
依据：SBR-LV-009（[503] sem informação de registro）
建议：补证后上架；无证则下架
```

| 商品行号 | SKU | 缺什么资质 | 依据规则 | 建议 |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

## 5.11 步骤 15：交付与留痕

### 5.11.1 交付三件套

| 产物 | 说明 |
|---|---|
| **结果 JSON** | 符合 `contracts/audit_result.schema.json` 的 `AuditResult[]` |
| **人读报告 Markdown** | 六节固定结构（见 §7.1） |
| **溯源信息** | 文件路径 + 内容哈希 + 解析时间 + 规则集版本 |

**原始文件留在原处，产物另存。**

### 5.11.2 报告六节固定结构

```
## 1. 摘要
## 2. 数据缺口与未评估项
## 3. 需决策的发现
## 4. 待复核的发现
## 5. 逐商品结果
## 6. 已查阅规则
```

| 节 | 内容 | 空时的表现 |
|---|---|---|
| 1. 摘要 | 范围、商品数、结论分布、需人工处理数 | 必须有 |
| 2. 数据缺口 | 所有 `unevaluated[]` 条目及其缺失字段 | **必须显示"无"，不得省略** |
| 3. 需决策的发现 | `action` 为 `block`/`revise`/`escalate_legal` 的 | 显示"无" |
| 4. 待复核的发现 | `action` 为 `flag_for_review`/`require_evidence` 的 | 显示"无" |
| 5. 逐商品结果 | 每个商品一条，含所有结论 | 必须有 |
| 6. 已查阅规则 | 本次用到的规则及其来源层级与核查日期 | 必须有 |

> ⚠️ **第 2 节是硬性要求。** 它把"未评估"与"通过"明确分区。省略第 2 节会让读者误以为没问题的商品是通过了审核。

### 5.11.3 报告末尾必须附硬约束清单

```markdown
## 硬约束
- H1 IP 类结论恒为 signal 且需人工复核 — ✅
- H2 阻断类动作仅来自 platform_official/law 的 active 规则 — ✅
- H3 输入缺失标记未评估，不计为通过 — ✅
- H4 引文逐字核验 — ✅ (50/50)
- H5 证据只引用不内嵌 — ✅
- H6 冻结重发/转法务为人工专属 — ✅
```

### 5.11.4 来源层级必须呈现

| 层级 | 显示为 |
|---|---|
| `platform_official` | `regra da plataforma` |
| `law` | `lei brasileira` |
| `internal_risk` | `sugestão de risco interno` |
| `unverified` | `hipótese não verificada` |

### 5.11.5 交付前自检清单

| # | 检查 | 通过标准 |
|---|---|---|
| 1 | 商品行数 == 源文件行数 | 一行不多一行不少（除非用户明确确认下架） |
| 2 | 所有源 PID 都在输出的 A 列 | 零丢失 |
| 3 | 标题 STRICT 触线 | 0 |
| 4 | 中文残留 | 0 |
| 5 | 店铺名/客服话术/物流话术/CND 链接残留 | 各 0 |
| 6 | 标题长度 ≥ 120 字符 | 0 |
| 7 | `activePane` | `bottomLeft` |
| 8 | 改写后复检 | 已跑，0 新增触线 |
| 9 | 抽样人工读详情 | 已读，记录在案 |
| 10 | 五张清单都附在报告后面 | 齐全 |

**一句话汇报格式**（每次交付都要给）

```
商品行: 158, 标题 STRICT 触线: 0, 中文残留: 0, 店铺名 0, CDN 0, 客服 0, 标题 >=120 字符: 0
```

> **引用具体数字对，不要说"看起来干净"。**

# 6. 特殊场景处理

## 6.1 概述

以下是流程中的**例外分支**。遇到时从 §5.4 主流程跳到对应小节，处理完回到主流程。

| 场景 | 处理章节 |
|---|---|
| 用户发现之前下架了商品（信任修复） | §6.2 |
| 标题和详情对不上 | §6.3 |
| 用户审核报告 = 新的一轮审计 | §6.4 |
| 产品事实问不出来 | §6.5 |
| 年龄/受众变更 | §6.6 |
| 平台处罚与解封 | §6.7 |
| 词库维护节奏 | §6.8 |

## 6.2 用户发现之前下架了商品（信任修复）

当用户说"没有我同意，你怎么随意下架产品"：

```
1. 立刻停止下架流水线，不要跑完删除步骤
2. 找出上一轮被标下架的行（读工作区的 takedown_pids.json 等下架清单）
3. 逐个重写那一行的内容：泛化标题 + 纯商品描述
4. 跑完整流程，输出全部行
5. 验证：行数 == 源行数，且被下架行的原标题不再逐字出现
```

**泛化标题示例**：

| 原标题 | 泛化后 |
|---|---|
| `Cola para Cílios Postícios Jhessy` | `Cola para Cílios Postícios, 30 ml` |
| `Creme Para Remoção De Cicatrizes ...` | `Creme Corporal Hidratante, 100 g` |
| `V Face Band ... Shaping Máscara` | `Máscara Facial Elástica em Tecido` |
| `Perfume Feromônio Para Homens` | `Perfume Fragrância Suave, 50 ml` |

> **通用原则：泛化标题 + 纯商品描述，永远比悄悄删行安全。**
> **绝不可以在说"没有下架"时，不列出上一轮的下架清单。** 信任修复靠透明，不靠沉默。

## 6.3 标题和详情对不上

有时源文件的标题和详情**描述的是两个不同 SKU**。

**检测**：详情里找这个模式 → `Atenção: o item selecionado corresponde ao <X>` —— `<X>` 才是实际发货的商品。

**处理**：按详情的实际商品重写标题，并同步修详情里的指代。

## 6.4 用户审核报告 = 新的一轮审计

**当用户拿回你交付的文件，自己审一遍并给出问题清单时** —— 那是**权威缺陷清单**，不是挑刺。

1. **不要辩解**。逐条核对用户的每一项：确认 / 不确认
2. 说清**根因**：缺陷来自 LLM 输出 / 你的 regex / 你的手工编辑 / 原始源文件
3. **重新审计整个文件**，不只是用户点名的几个例子
4. 用户按优先级分层（高/中）告诉你往哪使劲
5. **改完自己再扫一遍** —— 你的修复可能是下一个缺陷

**根因分类比"改了 8 个 PID"值钱得多** —— 因为它告诉你剩下的 290 行是不是同一类问题。

## 6.5 产品事实问不出来

授权状态、真实物理规格、适用年龄、安全使用范围 —— 这些**无法从商品文案推断**。

**做法**：交付保守版改写（去掉角色名、收窄使用场景、提高年龄下限），然后给用户**一行一个 PID** 的确认清单：

```
Row 179 | 授权状态 | 默认：按无授权处理，已从标题与详情移除角色名
Row 88  | 适用年龄 | 默认：14 岁起，已加「Não use por menores de 14 anos」
```

用户一句话能回掉好几项。**不要为了凑齐信息而猜。**

## 6.6 年龄/受众变更必须传播到每个字段

一个商品从「Crianças」改成「Adolescentes e Adults」，要改的地方不止标题：

| 字段 | 改什么 |
|---|---|
| 标题 | 年龄段 |
| Descrição | 年龄段 |
| Características | "pele infantil" → 删 |
| Especificações | "Faixa etária" |
| Cuidados | "Mantenha sob acompanhamento de um adulto" |

并加一条明确的 `Não use por menores de 14 anos`。

**品牌角色无授权时同理**：标题 + 详情都要去掉名字，**衍生风格描述也要中性化**（`Estampas em estilo kawaii` → `Estampas coloridas`）。

## 6.7 平台处罚与解封

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

## 6.8 词库维护节奏

| 节奏 | 内容 |
|---|---|
| **即时** | 收到品牌方投诉或平台下架通知时立即加入 |
| **月度** | 补 INPI 最新注册商标、新冒头的仿牌词 |
| **季度** | 跟踪 Shopee BR / Mercado Livre 政策更新 |
| **半年** | 审计现有 SKU 是否含已加词库的词 |

**扫描时机**：新 SKU 上架前（标题/详情/属性必跑）→ 批量筛查 → 改写后验证 → 定期复核。

# 7. 审核报告

## 7.1 报告六节结构

**每次审核完，交一份报告。** 六节，顺序固定。

### 7.1.1 摘要

```
本次审核 ____ 个商品。
致命 __ 个（建议不上架）、高 __ 个（需资质或改文案）、中 __ 个（需修改）、
低 __ 个（建议优化）、通过 __ 个。
改写后已复检 __ 个，全部通过。
```

**不要写**"整体状况良好""基本合规"这种话 —— **给数字对**。

### 7.1.2 数据缺口与未评估项

| 商品行号 | 缺失字段 | 受影响规则 | 说明 |
|---|---|---|---|
| | | | |
| | | | |

### 7.1.3 需决策的发现

| 商品行号 | 发现 | 严重度 | 依据 | 建议 |
|---|---|---|---|---|
| | | | | |
| | | | | |

### 7.1.4 待复核的发现

| 商品行号 | 发现 | 严重度 | 依据 | 待确认什么 |
|---|---|---|---|---|
| | | | | |
| | | | | |

### 7.1.5 逐商品结果

| 商品行号 | 类目 | 结论 | 动作 | 问题摘要 | 复检 |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |

### 7.1.6 已查阅规则

| 规则 ID | 严重度 | 来源层级 | 核查日期 | 本次命中数 |
|---|---|---|---|---|
| | | | | |
| | | | | |

### 7.1.7 报告要带上前面五张清单

**审完不是只交一份报告就完了。** 前面五张清单是报告的证据，必须一起交：

| 清单 | 交到报告哪一节 |
|---|---|
| 类目卡 | §7.1.5 |
| 标题问题清单 | §7.1.5 |
| 详情问题清单 | §7.1.5 |
| 图片问题清单 | §7.1.5 |
| 属性问题清单 | §7.1.5 |
| **商品问题总表**（已填动作） | §7.1.3 / §7.1.4 |
| 建议下架清单 | §7.1.3 |
| 工单清单 | §7.1.3 |
| 待确认清单（查授权） | §7.1.4 |
| 最终问题清单（复检后） | §7.1.5 |
| 豁免记录 | §7.1.6 |

## 7.2 审核员自查

### 7.2.1 流程完整性

| # | 问题 | 过 |
|---|---|---|
| 1 | 每个商品都**先定了类目**？ | □ |
| 2 | 每个商品都过了标题、详情、图片、属性四关？ | □ |
| 3 | 每一步的问题清单都写了？**空的也写了"无"**？ | □ |
| 4 | 五张清单合并成总表了？重复的合并了？ | □ |
| 5 | 总表里**每行都有动作**？ | □ |

### 7.2.2 判定准确性

| # | 问题 | 过 |
|---|---|---|
| 6 | 每个禁售品类都查过了？ | □ |
| 7 | 每个命中的词都过了一遍 §5.9 豁免清单？ | □ |
| 8 | 高风险品牌都查了授权？ | □ |
| 9 | 汽配/化工类目额外对照了 EX-CHEMICAL？ | □ |

### 7.2.3 处置正确性

| # | 问题 | 过 |
|---|---|---|
| 10 | 缺资质的都出工单了，没混进改写清单？ | □ |
| 11 | 建议下架的都列出来了，**没有自己删**？ | □ |
| 12 | 拿不准的挂"待复核"了而不是自己拍板？ | □ |

### 7.2.4 改写质量

| # | 问题 | 过 |
|---|---|---|
| 13 | 改完做了 §5.8 复检（13 项逐条过）？ | □ |
| 14 | 改写的文案**从头读了一遍**？ | □ |
| 15 | 改写有没有引入中文/法语/粘连词？ | □ |
| 16 | 有没有商品详情和其他商品一字不差？ | □ |
| 17 | 首句唯一率 100%？ | □ |

### 7.2.5 交付完整性

| # | 问题 | 过 |
|---|---|---|
| 18 | 报告第 2 节（数据缺口）写了？ | □ |
| 19 | 摘要写的是**具体数字**，不是"基本合规"？ | □ |
| 20 | 五张清单都附在报告后面了？ | □ |

> **第 13 项是最容易漏的。** 没做复检 = 这次审核不算完成。

# 8. 边界与红线

## 8.1 本流程不做的事

| ❌ 不做 | 原因 |
|---|---|
| 发布 / 改线上 / 下架 / 解冻 / 申诉 | 需单独评估批准；自动化不得代做（H6） |
| 处理重大 IP 投诉 | 人工专属 |
| 修改核心规则 | 人工专属 |
| 直接修改生产数据 | 人工专属 |
| 批量删除商品行（未经确认） | 红线，见 §5.6 |
| 编造平台政策、法律条文、来源引文 | 红线 |
| 把"未评估"写成"通过" | 红线（H3） |
| 声称执行了未实际执行的测试 | 红线 |
| 在 IP 结论中使用「侵权」表述而无投诉/授权/通知支撑 | 红线 |

## 8.2 来源层级与"什么能做阻断"

| `source.tier` | 含义 | 可否产生 `block` 类动作 |
|---|---|---|
| `platform_official` | Shopee 官方页面明确写出 | ✅ |
| `law` | 巴西联邦法律明文 | ✅ |
| `internal_risk` | 内部风控建议 | ❌ |
| `unverified` | 未验证假设 | ❌ |
| `ai_inference` | AI 模型推断 | ❌ |
| `technical` | 技术调研结论 | ❌ |

**`source.excerpt` 必须逐字出现在抓取件中** —— 引文核验不通过 → 任务不通过。

## 8.3 错误处理

| 情形 | 行为 |
|---|---|
| 读入失败 | **不中断整批**，记 error |
| 某模块不可用 | 明确说明该检查**未执行**，**不得当作通过** |
| 某模块无结果 | 记录为空，**不得当作"无风险"** |
| 契约校验失败 | 拒绝整合该模块结果 |
| 无任何模块产出 | 不生成空结论，显式失败 |

# 附录A

## A.1 判定依据来源

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

**发现本文和规则库不一致时**：以 `rules/*.json` 为准，并提出来更正本文。

## A.2 快速命令速查

```bash
# 全量校验（10 步）—— 提交前必跑
env -u LD_LIBRARY_PATH bash scripts/check_all.sh

# 词库扫描
env -u LD_LIBRARY_PATH python3 tools/scan_lexicon.py --input products.json
env -u LD_LIBRARY_PATH python3 tools/scan_lexicon.py --self-test

# 各模块自有测试
env -u LD_LIBRARY_PATH python3 tests/<module>/run_tests.py
env -u LD_LIBRARY_PATH python3 tests/integration/run_tests.py

# 引文逐字核验（不编造来源）
env -u LD_LIBRARY_PATH python3 tools/verify_citations.py

# 定位源文件
find /config -iname "*mass_update*"
```

> ⚠️ **所有 Python 命令都要 `env -u LD_LIBRARY_PATH` 前缀** —— 见 §4.3.4。

## A.3 葡语书写规范

### A.3.1 重音必对

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

### A.3.2 数字与容量

- `30ml`（小写 ml）/ `50g`（小写 g）
- `FPS 15`（葡语用 FPS 不是 SPF）
- `12 horas`（葡语用复数）
- `R$ 99,90`（葡语货币格式）

### A.3.3 营销词本地化

| ❌ | ✅ |
|---|---|
| `mais vendido` / `best seller` | `um dos mais procurados` |
| `alta qualidade` | `qualidade confiável` 或具体描述 |
| `frete grátis`（Shopee 自带） | 删除 |

### A.3.4 店主的 10 条原则

| # | 原则 |
|---|---|
| 1 | 每个商品详情必须**独立手工编写**，不套模板 |
| 2 | 材质/配方/容量必须**按实物核实**，不能空泛宣传 |
| 3 | 适用人群/频率必须按说明书写，不能普适承诺 |
| 4 | 产地按原产标签写，不能统一填 China |
| 5 | FAQ 必须针对商品独立设计，不能跨商品套用 |
| 6 | 未核实的功效不能直接承诺 |
| 7 | 标点重音必须正确 |
| 8 | 类别按真实分类填 |
| 9 | 包装按实际形式填 |
| 10 | 品牌要核实真伪后再使用 |

**具体反例**

| ❌ 不可用 | 原因 | ✅ 替代写法 |
|---|---|---|
| "Material premium" | 缺材质依据 | `Importado` / `Linha profissional` / `Padrão Internacional` |
| "Acabamento cuidadoso" | 太空泛 | 具体描述 |
| "Confortavel" | 对眼镜/工具不适用 | 去掉 |
| "Tipo: Cosmético" | 对首饰/工具不适用 | 按真实类别 |
| "Origem: China" | 缺逐品依据，与 Coreano/Korea 冲突 | 按原产标签写 |
| "Todos os tipos de pele" | 普适承诺，未经证明 | 按说明书 |
| "Testado dermatologicamente" | 暗示已测试 | 去掉 |
| "Produto original" | 缺真伪证据 | 去掉 |

## A.4 未决事项

| # | 问题 | 默认处置 |
|---|---|---|
| 1 | 词库中 `internal_risk` 层级的词是否全部升级为 `platform_official` | 保持 `internal_risk`，只产生 `flag` |
| 2 | 处罚点分值表（平台未公开） | 只用「是否扣分」标识，**不编造分值** |
| 3 | INPI 查询自动化程度 | 保留人工查询 + 记录引用 |
| 4 | 「无法文字规避」品类的工单落地方式 | 本期只做标记与清单 |

# 附录B

## B.1 填写模板汇总

**本文所有需要填写的字段集中在这里。** 打印或复制使用。

### B.1.1 源文件登记表（§4.2.1）

| 项目 | 内容 |
|---|---|
| 店铺名 | |
| 店铺 ID | |
| 源文件路径 | |
| 副本路径 | |
| 源文件哈希（sha256） | |
| 商品总数 | |
| 定位日期 | |
| 经手人 | |

### B.1.2 未评估项清单（§4.3.5）

| 商品行号 | 缺失字段 | 受影响规则 | 备注 |
|---|---|---|---|
| | | | |
| | | | |

### B.1.3 类目卡（§4.4.1）

```
商品编号：____
类目：□ 化妆品  □ 汽配  □ 电池  □ 酒类  □ 药品保健品  □ 兽药
      □ 太阳镜  □ 儿童安全  □ 普通商品
判定依据：标题/详情里看到的：____________
```

### B.1.4 四张问题清单（§4.5.2 / §4.6.1 / §4.7.1 / §4.8.3）

**标题问题清单**

| 商品行号 | 命中词/问题 | 严重度 | 判定表 |
|---|---|---|---|
| | | | |
| | | | |

**详情问题清单**

| 商品行号 | 命中词/问题 | 严重度 | 判定表 |
|---|---|---|---|
| | | | |
| | | | |

**图片问题清单**

| 商品行号 | 命中词/问题 | 严重度 | 判定表 |
|---|---|---|---|
| | | | |
| | | | |

**属性问题清单**

| 商品行号 | 命中词/问题 | 严重度 | 判定表 |
|---|---|---|---|
| | | | |
| | | | |

### B.1.5 商品问题总表（§4.9.3）

| 商品编号 | 类目 | # | 命中词/问题 | 出现在 | 严重度 | 判定表 | 动作 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |

### B.1.6 建议下架清单（§5.5.1）

| 商品行号 | 命中词 | 依据码 | 严重度 | 店主确认 |
|---|---|---|---|---|
| | | | | □ |
| | | | | □ |
| | | | | □ |

### B.1.7 改写记录表（§5.7.12）

| 商品行号 | 原标题 | 新标题 | 改写要点 | 复检通过 |
|---|---|---|---|---|
| | | | | □ |
| | | | | □ |
| | | | | □ |

### B.1.8 豁免记录表（§5.9.2）

| 商品行号 | 命中词 | 豁免依据 | 为什么 |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

### B.1.9 工单清单（§5.10.1）

| 商品行号 | SKU | 缺什么资质 | 依据规则 | 建议 |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

### B.1.10 待确认清单（查授权）

| 商品行号 | 品牌/logo | 出现位置 | 店主回复 | 日期 |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

### B.1.11 批次汇总表

| 项目 | 数量 |
|---|---|
| 审核商品总数 | |
| 致命（建议不上架） | |
| 高（需资质或改文案） | |
| 中（需修改） | |
| 低（建议优化） | |
| 通过 | |
| 已改写 | |
| 已复检 | |
| 复检未通过 | |
| 出工单 | |
| 挂起待确认 | |

**一句话汇报格式**

```
商品行: ____, 标题 STRICT 触线: 0, 中文残留: 0, 店铺名 0, CDN 0, 客服 0, 标题 >=120 字符: 0
```

## B.2 与其他文档的对应关系

| 本文章节 | 步骤 | MANUAL_REVIEW | USER_SOP |
|---|---|---|---|
| §4.2 | 步骤 0 | — | 规程 §3 |
| §4.3 | 步骤 1-2 | — | 规程 §4 |
| §4.4 | 步骤 3 | 手册 §1 | — |
| §4.5 | 步骤 4 | 手册 §2 | — |
| §4.6 | 步骤 5 | 手册 §3 | — |
| §4.7 | 步骤 6 | 手册 §4 | — |
| §4.8 | 步骤 7 | 手册 §5 | — |
| §4.9 | 步骤 8 | 手册 §5A | — |
| §5.2 / §5.3 | 步骤 9 | 手册 §6 + 手册 §9 | 规程 §5 |
| §5.4 | 步骤 10 | 手册 §7 | 规程 §6 |
| §5.7 | 步骤 11 | 手册 §8 | 规程 §7 |
| §5.8 | 步骤 12 | 手册 §7.6 | 规程 §7.10 |
| §5.9 | 步骤 13 | 手册 §9 | 规程 §6.5 |
| §5.10 | 步骤 14 | 手册 §10 | 规程 §6.4 |
| §5.11 / §7 | 步骤 15 | 手册 §11 | 规程 §8 |

## B.3 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-10-28 | 初版：按《跨境发货SOP》格式重写，含文件说明/流程概况/基础逻辑/操作部分/判定与处置/特殊场景/审核报告/边界红线/附录A-B，预留全部填写字段 |
