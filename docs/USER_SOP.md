# 使用者操作规程（SBRCA User SOP）

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-SOP-USER-001` |
| 版本 | 2.0.0 |
| 状态 | **Draft — 待用户审批** |
| 创建/更新 | 2026-10-28 |
| 面向对象 | **使用者**（店主 / 运营 / 审核执行人）—— 不是开发 Agent |
| 适用范围 | Shopee 巴西站商品合规审核与文案改写的**完整日常作业流程** |
| 与其他文档的关系 | 本文是**流程框架与操作入口**；纯手工执行见 `docs/MANUAL_REVIEW.md`；判定语义与铁律细节见 `docs/SOP_COMPLIANCE_REVIEW.md`；工程契约见 `PROJECT_RULES.md` |
| 相关文档 | `docs/MANUAL_REVIEW.md`、`docs/SOP_COMPLIANCE_REVIEW.md`、`README.md`、`docs/integration_report.md`、`contracts/risk_action_matrix.json`、`lexicon/` |

---

## 0. 本文档怎么用

### 0.1 按角色选入口

| 你是谁 | 读哪几节 |
|---|---|
| **店主 / 老板** | §1 → §2 → §9 → §10（看懂流程、知道边界、看结果、拍板） |
| **运营 / 执行人** | §1 → §3 → §4 → §5 → §8 → §9 → §11 → §12（全流程，按步骤做） |
| **审核执行人** | **转 `docs/MANUAL_REVIEW.md`** —— 那份是纯手工手册，本文是它的流程上游 |
| **开发 Agent** | `PROJECT_RULES.md` + `AGENT_COLLABORATION.md` + `tasks/*.md`（工程流程，不是本文） |

> ⚠️ **本文不新增任何判定规则。** 所有"什么算违规"的结论一律以 `docs/SOP_COMPLIANCE_REVIEW.md` 与 `rules/*.json` 为准。本文只回答：**做什么、按什么顺序做、做完交什么、遇到问题怎么办**。

### 0.2 ★ 本文与《人工审核操作手册》的分工

两份文档**共用同一套步骤编号**（步骤 0-15）。分工是"谁做这一步"：

| 步骤 | 环节 | 本文（USER_SOP） | 手册（MANUAL_REVIEW） |
|---|---|---|---|
| 0 | 定位源文件 | §3 怎么找文件 | — （纯手工不需要） |
| 1 | 读入并标准化 | §4.1 怎么转模型 | — |
| 2 | 字段完整性检查 | §4.2 缺字段怎么办 | — |
| 3 | 定类目 | — | §1 定类目卡 |
| 4 | 看标题 | — | §2 标题 12 项 |
| 5 | 看详情 | — | §3 详情 20 项 |
| 6 | 看图片 | — | §4 图片 7 项 |
| 7 | 看属性 | — | §5 属性 9 项 + 跨店 7 项 |
| 8 | 合并问题总表 | — | 手册 §5A 五张清单合一 |
| 9 | 扫描 + 上下文判定 | §5 词库扫描 + 判定 | §6 关键词判定表 + §9 豁免 |
| 10 | 人工分流 / 收口 | §6 分流与硬约束 | §7 收口决策树 |
| 11 | 改写 | §7 改写铁律 | §8 改写标准 |
| 12 | 复检 | §7.10 改写后必做 | §7.6 复检 12 项 |
| 13 | 豁免（防误伤） | §6.5 误报控制 | §9 豁免清单 |
| 14 | 无法文字规避 | §6.4 无法规避品类 | §10 出工单 |
| 15 | 交付与留痕 | §8 交付三件套 | §11 报告六节 |

> **一句话**：**本文管"流程怎么走"（含工具、命令、铁律），手册管"每一步怎么判"（清单、词表、动作）。**

---

## 1. 全流程总览（步骤 0-15）

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

**八步是 `docs/SOP_COMPLIANCE_REVIEW.md` §3 的落地版**，本文把每一步展开成"可执行动作"。

### 1.1 每一步都要"交出去"

**这是整套流程的核心。** 审核不是走完八个环节就完事 —— 每一步都要产生一样东西，交给下一步：

```
步骤 0  → 【文件路径】         步骤 8  → 【商品问题总表】
步骤 1  → 【统一商品模型】     步骤 9  → 【命中清单 + 判定结论】
步骤 2  → 【未评估项清单】     步骤 10 → 【动作清单】
步骤 3  → 【类目卡】           步骤 11 → 【新标题 + 新详情】
步骤 4  → 【标题问题清单】     步骤 12 → 【最终问题清单】
步骤 5  → 【详情问题清单】     步骤 13 → 【豁免记录】
步骤 6  → 【图片问题清单】     步骤 14 → 【工单清单】
步骤 7  → 【属性问题清单】     步骤 15 → 【报告 + 全部清单】
```

**每一步结束时你手上必须有一张清单。** 空清单也要写"无"—— **空清单和"还没看"是两回事**。

### 1.2 两条提前退出

流程里有两处命中就**立刻停**，别往下走：

| 触发 | 停在哪 |
|---|---|
| 步骤 0 找不到源文件 | **问店主**，不要基于审核报告"重建"文件 |
| 步骤 10 发现致命违规或缺资质 | **不进改写**，走 §6.3 / §6.4 |

---

## 2. 核心概念（先看这四条，其余都好懂）

### 2.1 四态语义：缺数据不等于通过

| 状态 | 含义 | 你会看到什么 |
|---|---|---|
| `missing` | 字段在，但这次没数据 | 报告里该规则显示「未评估」 |
| `unknown` | 有值但无法确定 | 报告里显示「待复核」 |
| `not_applicable` | 这个商品本来就没这个字段 | 不出现在结果里 |
| `pending_verification` | 有风险，但要等外部确认 | 出现在「待复核」清单 |

> **这是整套流程的地基。** 早期版本因为把「缺 `images` 列」当成「图片违规」，15 个商品 100% 误报。
> **看报告时，永远先看第 2 节「数据缺口与未评估项」，不要看结论分布就下判断。**

### 2.2 词库命中是信号，不是结论

扫到关键词 ≠ 违规。词库只负责**筛出可疑项**，最终判定要看上下文。

| 命中类型 | 处理 |
|---|---|
| 真违规 | 进改写 / 处置流程 |
| 描述性用法（如 "reduzir a entrada de água" = 描述功能） | **保留**，记为误报豁免 |
| 描述性用法但表述暧昧 | 改写成无歧义的写法 |

> **误报控制的价值高于"扫描器数字归零"。** 把 `desconforto`（安全提示）、`seguro`（功能描述）这类词全部改掉，反而会降低合规性。

### 2.3 风险等级 × 处理动作（两张表，不是一张）

**风险等级**说"有多严重"，**处理动作**说"该怎么办"。两者分开定义，靠矩阵查表。

| 风险等级 | 含义 | 你该怎么反应 |
|---|---|---|
| `info` | 提示性，不构成风险 | 不用管 |
| `low` | 低风险，可能被平台提示 | 记录，可不改 |
| `medium` | 中风险，可能被下架但通常不扣分 | **要改** |
| `high` | 高风险，扣分或下架 | **立即改 / 立即查授权** |
| `critical` | 极严重，扣分 + 可能冻结账号 | **停下来，升级处理** |

**处理动作**只有 7 种：`allow`（通过）/ `flag_for_review`（提示复核）/ `require_evidence`（补证后复审）/ `revise`（改内容后复审）/ `block`（不得上架）/ `freeze_relist`（冻结重发）/ `escalate_legal`（转法务）。

> 完整 35 个组合的允许性与聚合规则在 `contracts/risk_action_matrix.json`，**不要自己猜**。

### 2.4 结论只有四个

| `verdict` | 含义 |
|---|---|
| `PASS` | 通过 |
| `REVISE` | 需修改 |
| `REVIEW` | 需人工复核 |
| `BLOCK` | 阻断 |

**`verdict` 是对外汇报的标签，`action` 是执行动作。** 两者不是一一对应。

---

## 3. 步骤 0：定位源文件 —— 先定位，再动手

**这是 31 个实战坑里的头号坑：多店文件不一定在本机。**

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

**动作清单**

| # | 做什么 | 判据 |
|---|---|---|
| 1 | 用上述三种方式定位源文件 | 找到**实际文件路径** |
| 2 | 确认这个文件确实是你要审的那一批 | 抽查 3 个 PID 的标题能对上 |
| 3 | 找到就复制一份到工作区，**不动原件** | 原始输入不得被覆盖或修改 |

**停下来的情况**：PID 一个都查不到 = 文件不在本机。
→ **直接请用户上传。不要基于审核报告"重建"文件。**

> 审核报告只给**问题清单**，不给**商品原文**。报告里一句"用词不自然"是没法还原成实际内容的。

### 3.1 ★ 交给下一步

```
→ 产出：【文件路径】+ 【副本路径】+ 【源文件哈希】
→ 下一步：步骤 1-2（§4 读入并标准化）
→ 带上的东西：文件路径 + 确认过的 3 个 PID 抽样
→ ★ 找不到文件就停在这里 —— 不要往下走
```

---

## 4. 步骤 1-2：读入并标准化 + 字段完整性检查

### 4.1 读入并标准化

- Excel 仅作**输入**，导入后统一转成 `data/schema/product.schema.json` 定义的商品模型
- 解析失败 / 字段缺失 → **记 error，不中断整批**
- 保留溯源信息（文件路径 + 内容哈希 + 解析时间 + 解析器版本）—— **没有溯源的输入不得进入审核链路**

### 4.2 字段完整性检查（扫描之前先做）

| 缺失字段 | 处理 | 你在报告里看到 |
|---|---|---|
| `title` | 该记录**不参与审核**，记 error | 该商品缺 title 记录 |
| `description` | 相关规则标记未评估 | 「未评估：description」 |
| `images` | 图片类规则标记未评估 | 「未评估：images」 |
| `brand` | 品牌类规则标记未评估 | 「未评估：brand」 |
| `category` | 类目规则标记未评估 | 「未评估：category」 |

**为什么要先做这一步**：避免把"数据缺失"误判成"listing 违规"。

### 4.3 xlsx 处理铁律（8 条，做之前必须知道）

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

### 4.4 运行环境铁律（不设这行就跑不动）

> Hermes 运行时会把 `LD_LIBRARY_PATH` 指向自带目录，其中的 `libcrypto.so.3` 与系统 OpenSSL 冲突 → `ssl` 模块直接 ImportError。

```bash
env -u LD_LIBRARY_PATH python3 script.py
```

**必须在进程启动前清掉**（脚本内 `os.environ.pop` 已经太晚，ssl 已被运行时导入）。

```python
def _preflight():
    try:
        import ssl  # noqa
        return True
    except Exception as e:
        print(f'❌ ssl 导入失败: {e}')
        print('   请用: env -u LD_LIBRARY_PATH python 本脚本')
        return False
```

**任何调用 HTTPS 的脚本都要用 `env -u LD_LIBRARY_PATH` 启动。**

### 4.5 ★ 交给下一步

```
→ 产出：【统一商品模型】（每商品一条，符合 data/schema/product.schema.json）
       +【未评估项清单】（步骤 2 缺字段导致的）
→ 下一步：步骤 3-7（定类目 + 四张清单）
→ 带上的东西：商品模型 + 未评估项清单
→ ★ 未评估项必须一路带到底 —— 报告里不能消失
→ ★ 纯手工执行的话，转 docs/MANUAL_REVIEW.md §1（定类目）
```

---

## 5. 步骤 9：词库/规则扫描 + 上下文判定

### 5.1 匹配铁律（按重要度排序）

| # | 铁律 | 反例 → 正例 |
|---|---|---|
| 1 | **单词边界 `\bword\b`**，不要子串匹配 | `antidade` ≠ `quantidade` |
| 2 | **葡语动词必含全部变位** | `\bproporciona\w*\b` 而非 `\bproporciona\b` |
| 3 | **形容词 ≠ 同根动词** | ❌ `\bproporcional\b` ✅ `\bproporciona(m|r|do|da|das|mos)\b` |
| 4 | **大小写同时匹配** | `[Pp]ara garantir\b` |
| 5 | **大小写不敏感 + 变体归一** | `N1ke→nike`、`@pple→apple` |
| 6 | **描述性用法 ≠ 承诺用法** | `garantir conforto` ≠ `garantido` |
| 7 | **重音折叠仅用于匹配**，输出保留原形 | |

### 5.2 葡语 `\b` 不可靠（已知坑，必须避）

> 葡语的 `\b` 会吞掉相邻单词的首字母。

```python
# ❌ 错误 —— 会吞掉 "Óculos" 的首字母
re.sub(r'\s*at[óo]xico\b\s*', ' ', s)

# ✅ 正确 —— 显式排除字母边界
re.sub(r'(?<![a-zA-Zà-ÿÀ-ß])at[óo]xico(?![a-zA-Zà-ÿÀ-ß])', ' ', s)
```

**所有葡语关键词匹配一律用显式 lookaround。**

### 5.3 全字段扫描

> **漏检教训**：标题仅 6% 命中，详情 94% 命中 → **标题 + 详情 + 属性 + 品牌全扫**，不能只扫标题。

### 5.4 上下文判定：4 个已知误报模式

| 场景 | 正确处理 | 错误处理 |
|---|---|---|
| 工具类（菜刀/剪刀/螺丝刀/美工刀） | **豁免**，不标 weapon | 标为武器 |
| `Hermes` 出现在快递/邮箱类描述 | 默认按侵权命中，**需人工复核** | 直接放行 |
| `CE` 在"产品印有 CE 标志" | 事实陈述，**记录但不拦截** | 判违规 |
| 品牌名作为产品通用词 | **默认仍按侵权命中** | 自动放行 |
| `reduzir`（"reduzir a entrada de água"） | 功能描述，**保留** | 全部改写 |
| `desconforto`（"em caso de desconforto, suspenda o uso"） | 安全提示，**保留** | 全部改写 |
| `seguro`（"fechamento seguro"） | 功能描述，**保留** | 全部改写 |

### 5.5 品类歧义消解

> `escova` 既是梳子也是刷子 —— 具体关键词必须排在前面，并单独建 override 表。

```python
CATEGORY_OVERRIDES = [
    (r'\bescova\s+(?:de\s+)?(?:limpeza|frestas|dentes|carro)\w*\b', 'limpeza'),
    (r'\bescova\s+de\s+dentes\b', 'banheiro'),
]
# 先查 override，再退回通用 infer_use
```

### 5.6 葡语大小写启发式禁令

> **不要用"小写字母后跟大写字母"判定缺空格** —— 葡语里这完全合法。

```python
# ❌ 会把 "não" 拆成 "n ão"，详情膨胀 39%
re.sub(r'(?i)([a-zà-ÿ])(?=[A-ZÀ-Þ][a-zà-ÿ])', r'\1 ', text)
```

缺空格要**按已知词**修，不能用通用启发式。

### 5.7 扫描工具怎么用

```bash
# 单条扫
env -u LD_LIBRARY_PATH python3 tools/scan_lexicon.py \
  --title "标题" --description "详情" --brand "品牌"

# 批量扫（商品 JSON）
env -u LD_LIBRARY_PATH python3 tools/scan_lexicon.py --input products.json

# 扫描器自检（回归用例）
env -u LD_LIBRARY_PATH python3 tools/scan_lexicon.py --self-test
```

**词库资产**（`lexicon/`，扫描与改写的机器可读版本）

| 文件 | 用途 | 规模 |
|---|---|---|
| `lexicon/term_groups.json` | 词组（扫描用） | 105 组 / 210,439 词 |
| `lexicon/rewrite_map.json` | 触线 → 中性替代（改写用） | 8 类映射 |
| `lexicon/exemptions.json` | 误报豁免规则 | 51 条 |
| `lexicon/quality_patterns.json` | 套模板/批量味检测 | 15 条特征 |
| `lexicon/non_avoidable.json` | 无法文字规避的品类 | 6 类 |
| `lexicon/verb_conjugations.json` | 葡语动词变位匹配表 | 7 个动词 |

### 5.8 ★ 交给下一步

```
→ 产出：【命中清单】（词 + 位置 + 命中组）
→ 下一步：步骤 10（§6 人工分流）
→ 带上的东西：命中清单 + 类目卡（决定怎么判）
→ ★ 命中 ≠ 违规 —— 必须先过上下文判定（§5.4）和豁免（§6.5）
→ ★ 纯手工执行的话，转 docs/MANUAL_REVIEW.md §6 关键词判定表 + §9 豁免清单
```

---

## 6. 步骤 10：人工分流 —— 决定怎么处置

### 6.1 处置分档

| 风险等级 | 含义 | 动作 |
|---|---|---|
| 🔴 **high** | 出现即可能下架/被追责 | **立即改写或下架；查授权** |
| 🟡 **medium** | 需授权或资质才能用 | **要求授权证明，否则移除** |
| 🟢 **low** | 注意但不直接违规 | **记录但保留** |

### 6.2 六条硬约束（**任何处置都不能违反**）

| ID | 约束 | 落地含义 |
|---|---|---|
| **H1** | IP 类结论恒为 `signal` + 强制人工复核 | 关键词/logo 命中只是筛查信号；只有权利人投诉、书面授权或平台投诉通知才能确立侵权 |
| **H2** | `block`/`freeze_relist`/`escalate_legal` 只来自 `platform_official`/`law` 的 `active` 规则 | 内部风险建议、AI 推断最高只能到 `flag_for_review` |
| **H3** | 输入缺失 → 该规则不评估 + 必须上报 `unevaluated` | **不得当作通过** |
| **H4** | `source.excerpt` 必须逐字出现在抓取件中 | 不编造引文 |
| **H5** | `artifact_ref` 只存引用，不内嵌凭证内容 | 授权书不要内嵌进报告 |
| **H6** | `freeze_relist`/`escalate_legal` 为 `human_only` | 自动化不得代做 |

### 6.3 下架前的硬规则（★ 红线）

> **未经用户对具体商品明确同意，不得批量删除任何商品行。**

| 你可以做（无需再问） | 你不可以做（必须先问） |
|---|---|
| 把疑似违规商品列成清单（PID + 触线词 + 严重度） | 直接从 xlsx 删行 |
| 在结果里标 `takedown_candidates` | 因为"规则说它违规"就跳过输出它 |
| 报告里给出建议下架数量 | 直接套用规则默认下架 |

**报告模板**

```
以下商品建议下架，请确认后我再执行：
  Row 20  | à prova d'água        | 标题硬触线   | high
  Row 74  | Retinol                | 标题硬触线   | high
  Row 101 | Resultado em 30 dias   | 时间承诺     | high
```

> 例外：用户已经明确说"下架 Row 20、74、101"，或引用了上一轮已确认的下架清单 → 可直接执行，不必再问。**不清楚就问。**

### 6.4 无法靠文字规避的品类

> 有些商品的合规性由**商品本体**决定，改文案无效。

| 类别 | 监管依据 | 为什么改写无效 |
|---|---|---|
| 化妆品 | ANVISA 强制注册 | 无注册号不能卖，改成"辅助"也不行 |
| 器械/矫形 | ANVISA | 监管属性由品类决定 |
| 宠物口腔 | 兽药监管 | 宣称去牙结石/除口臭即触及兽药 |
| 化学制剂 | ANVISA | 包装缺成分/警示/批号/有效期即违规 |
| 太阳镜 | INMETRO | 需 UV 实测报告，文字补不了 |
| 儿童安全 | INMETRO | 需认证 |

**处理流程**

```
扫描命中 → 判断是否属于「无法文字规避」品类
  → 是 → 生成工单（PID + 缺什么资质 + 建议）→ 不进批量改写
  → 否 → 进入改写流水线 → 改写后复扫 → 抽样人工读
```

### 6.5 ★ 交给下一步

```
→ 产出：【动作清单】—— 每条命中落到一个动作
  动作只有四种：改写 / 查授权 / 出工单 / 不上架
→ 下一步：
   有改写 → 步骤 11-12（§7 改写与复检）
   有工单 → 步骤 14（§6.4 出工单），不进改写
→ ★ 致命和缺资质两条路要提前退出，别混进改写批次
→ ★ 纯手工执行的话，转 docs/MANUAL_REVIEW.md §7 收口决策树
```

---

## 7. 步骤 11-12：改写与复检

### 7.1 单遍替换铁律（坑 20，★★★）

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

**配套铁律**

1. 替换值要选**不会被任何其他 pattern 匹配**的词（如用 `contribui para` 而不是 `auxiliar a`）
2. 若必须顺序执行，每条规则的替换值后要加**反向清理规则**
3. 实测效果：655 → 10 触线命中，零级联

### 7.2 替换值铁律（坑 18 / 21）

> **替换值里绝不写字符类。**

```python
# ❌ 输出会变成 "Anti-inc[ôo]modo"
RULES.append((r'anti-...', 'Anti-inc[ôo]modo'))

# ✅ 在规则加载阶段解析成真实字符
def resolve_classes(value):
    """'dom[ée]stico' -> 'doméstico'"""
    return re.sub(r'\[([^\[\]\n]{1,4})\]',
                  lambda m: m.group(1)[0] if m.group(1) else '', value)

# ✅ 构建期断言（忘一次就崩一次）
def _assert_no_charclass_in_values(rules):
    bad = [(p, r) for p, r in rules
           if re.search(r'\[[a-zA-Zà-ÿÀ-Ý]{1,4}\]', r)]
    if bad:
        raise SystemExit(f'替换值含字符类: {bad}')
```

### 7.3 列表并列项铁律（坑 25）

> **不要批量替换列表里的并列项** —— 换掉其中一项就会留下空洞。

```
'Adequado para, e todos os tipos de.'                    ← 空洞
'Adequado para,, palmas manchadas, ...,,,,,, auxilia nos cuidados...,, '  ← 空洞成片
```

**修复**：病句无法靠规则救 → **整段手工重写**。

> **配套铁律**：替换后必须**抽样读详情全文**，不能只看扫描器数字。

### 7.4 长度护栏

| 检查 | 阈值 | 失败处理 |
|---|---|---|
| 详情长度 | ≥ 500 字符 | 补「Como usar」+「Conteúdo da embalagem」两段 |
| 剥模板/剥 URL 后长度 | ≥ 250 字符 | 过短 → 按标题生成基础描述 |
| 标题长度 | 60–95 字符（上限 100） | 见 §7.5 |

### 7.5 标题截断铁律（坑 27）

> **截断必须在词边界，不能裸切。**

```python
cut = new[:95]
sp = cut.rfind(' ')
new = cut[:sp].rstrip(' ,;:-') if sp > 60 else cut.rstrip(' ,;:-')
```

**配套铁律**

1. 截断后跑「末尾悬空词」检测：`\b(de|da|do|para|com|em|a|o|e|pa|vi)$`
2. **标题被截断 = 语义也丢了** → 回源标题补，不是简单砍短
3. 标题与详情品类不一致 → **以详情为准**统一，并同步修详情里的指代（坑 28）

### 7.6 详情页六段结构（标准模板）

> 改写后的详情按这六段写，顺序固定。

```
1. Descrição            —— 首句 = 商品名 + 具体用途，必须含商品实词
2. Características      —— 用 • 分条
3. Especificações        —— 尺寸/容量/材质/适用
4. Modo de uso           —— 怎么用
5. Conteúdo da embalagem —— 包装里有什么
6. Cuidados importantes  —— 注意事项 + 适用年龄 + 「不替代专业建议」
```

**首句必须含商品实词**

```
✅ 'Saco de malha transparente para organizar livros e materiais.'
✅ 'Suporte de pia fixado na parede para esponjas e utensílios.'
❌ 'Item para organizar a rotina, com capacidade ampla e alça confortável.'
```

> **规则拼句会出病句** —— 葡语句法（介词搭配/冠词/性数一致）规则搞不定：
> `'Kit com o dia a dia para o uso do dia a dia.'` / `'Escova de para Escova de.'`
> → **首句用 LLM 写**，但必须跑后置清洗（LLM 会把源标题里的**中文 hashtag** 带进首句）。

### 7.7 反模板化：首句唯一率必须 100%

> 店主 2026-09-17 亲自审阅 491 个商品：**110 优先核实 / 331 修改补证 / 50 基本可读**。
> **491 个商品的详情完全相同** —— 全用统一模板。这是店主判定"最严重"的问题。

**"首句种类数"这个指标本身具有欺骗性** —— 111 种 vs 245 条商品，平均复用 2.2 次，但只要重复的句子都出现在同一类目，人工看过去就是"模板"。
→ **验收指标是首句唯一率 100%，不是"种类数"。**

**"套模板/批量味"特征（任一即打回）**

- `✅` × 4+
- 同一句 "Quer X mais forte" 出现 5+ 次
- `new_desc` 一字不差的 2+ 商品
- 含医疗词 / 含中文
- 标题里同时出现 `pomada`/`creme`/`gel`/`cream`/`loção`/`spray`/`sérum`/`máscara`/`pó`/`óleo` 中的 3 个以上
- 重复用 `moderno`/`tendência`/`atual`/`inovador`

### 7.8 店主的 10 条原则

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

### 7.9 LLM 使用的三条铁律

| # | 铁律 | 事故 |
|---|---|---|
| 1 | **LLM JSON 非法转义会整批丢数据** | 69 条描述因 `Invalid \escape` 退回规则版；改宽松逐对象解析后全部救回 |
| 2 | **LLM 会往葡语里注入中文/法语碎片** | 46 处（`"para uso殺，朝"`、`"nécessaire"`），需字符集直接删 |
| 3 | **LLM 硬切会在 95 字符处切碎单词** | `'...e acessórios de vi'`、`'...amplificador pa'` |

**配套要求**

- LLM 输出必须**逐条容错解析**（不能用整体 `json.loads` 一刀切）
- LLM 输出必须**后置清洗**：删中文/法语碎片、删控制字符
- 硬切必须**回退到词边界**
- LLM 结果必须**抽样人工读**，不能只看扫描器数字

### 7.10 改写后必须做的 3 件事（不可省）

| # | 动作 | 为什么 |
|---|---|---|
| 1 | **重新跑一遍 STRICT 全字典扫描** | 改写会引入新触线词 |
| 2 | **抽样人工读详情全文**（至少 10%） | 扫描器数字归零 ≠ 内容正确 |
| 3 | **复扫你上一步改过的文本** | 你的修复本身可能是下一个缺陷 |

> **第 3 条的真实事故**：一次无边界替换规则把 `Separador` 改成了 `Separadesconforto`；一句手写的安全提示（`não substitui acompanhamento profissional`）触发了 STRICT 字典。**改完必须再扫一遍。**

### 7.11 葡语写作规范

**重音必对**

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

**数字与容量**

- `30ml`（小写 ml）/ `50g`（小写 g）
- `FPS 15`（葡语用 FPS 不是 SPF）
- `12 horas`（葡语用复数）
- `R$ 99,90`（葡语货币格式）

**营销词本地化**

| ❌ | ✅ |
|---|---|
| `mais vendido` / `best seller` | `um dos mais procurados` |
| `alta qualidade` | `qualidade confiável` 或具体描述 |
| `frete grátis`（Shopee 自带） | 删除 |

**触线 → 中性替换表**（完整机器可读版见 `lexicon/rewrite_map.json`）

| 触线 | 中性 |
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
| proporcionar（变位） | facilitar |
| emagrece / modela | 删除 / design |
| Redutor de medidas | 删除 |

**残句修复**

```
\bpara auxilia\b           → para auxiliar
\bpode auxiliar uma boa\b   → pode oferecer boa
\bA design\b               → O design
\ba design\b               → o design
\brotina de rotina\b       → rotina
\bCintura Alta Cintura\b   → Cintura Alta
\bConforto e Conforto\b     → Conforto
\bcuidado com a pele com cuidado\b → cuidado com a pele
\buso geral e uso doméstico\b     → uso doméstico
\bgarantir\s+maior\b       → buscar maior
\bgarantir\s+que\b         → para que
\bgarantir\s+(?=...)       → buscar 
\beaconchegante\b          → e aconchegante
\bpermitevariados\b        → permite variados
\bv[íi]trees\b             → vidros
\bleitidas\b               → lidas
\bprodutouniformementemente\b → produto uniformemente
\beelasticidade\b          → elasticidade
```

### 7.12 PT-BR 机器翻译残留（27 个形态族）

> LLM/机器翻译改写会留下拼写粘连。这类问题**扫描器查不出，必须专门 patch**。

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

> ⚠️ **`proporcional` 不许动** —— 它是形容词，不是拼写错误。
> 完整 27 形态清单见 Hermes skill `marketplace-listing-preserve-all` 下的
> 「葡语机器翻译残留」参考文档（该文件在 Hermes skill 目录内，不在本仓库）。

### 7.13 ★ 交给下一步

```
→ 产出：【新标题】+【新详情】（每个改过的商品一份）
→ 下一步：步骤 12 复检（§7.10 三件事 + 重新扫描 + 抽样人工读）
→ ★ 不要直接跳到交付 —— 复检没做 = 这次审核不算完成
→ ★ 复检时还要对照豁免清单（§6.5），确认没把合规表达误删
→ ★ 纯手工执行的话，转 docs/MANUAL_REVIEW.md §8 改写标准 + §7.6 复检 12 项
```

---

## 8. 步骤 15：交付与留痕

### 8.1 交付三件套

| 产物 | 说明 |
|---|---|
| **结果 JSON** | 符合 `contracts/audit_result.schema.json` 的 `AuditResult[]` |
| **人读报告 Markdown** | 六节固定结构（见 §8.2） |
| **溯源信息** | 文件路径 + 内容哈希 + 解析时间 + 规则集版本 |

**原始文件留在原处，产物另存。**

### 8.2 报告六节固定结构（顺序不得调整）

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

> ⚠️ **第 2 节是硬性要求。** 它把"未评估"与"通过"明确分区。
> **省略第 2 节会让读者误以为没问题的商品是通过了审核。**

### 8.3 空值表达

| 情况 | 表达 |
|---|---|
| 无数据缺口 | `无` |
| 无需决策的发现 | `无` |
| 无待复核发现 | `无` |

**不得**用空白或 `-` 省略。

### 8.4 报告末尾必须附硬约束清单

```markdown
## 硬约束
- H1 IP 类结论恒为 signal 且需人工复核 — ✅
- H2 阻断类动作仅来自 platform_official/law 的 active 规则 — ✅
- H3 输入缺失标记未评估，不计为通过 — ✅
- H4 引文逐字核验 — ✅ (50/50)
- H5 证据只引用不内嵌 — ✅
- H6 冻结重发/转法务为人工专属 — ✅
```

### 8.5 来源层级必须呈现

报告中每条发现都要显示来源层级：

| 层级 | 显示为 |
|---|---|
| `platform_official` | `regra da plataforma` |
| `law` | `lei brasileira` |
| `internal_risk` | `sugestão de risco interno` |
| `unverified` | `hipótese não verificada` |

### 8.6 交付前自检清单

| # | 检查 | 通过标准 |
|---|---|---|
| 1 | 商品行数 == 源文件行数 | 一行不多一行不少（除非用户明确确认下架） |
| 2 | 所有源 PID 都在输出的 A 列 | 零丢失 |
| 3 | 标题 STRICT 触线 | 0 |
| 4 | 中文残留 | 0 |
| 5 | 店铺名/客服话术/物流话术/CND 链接残留 | 各 0 |
| 6 | 标题长度 ≥ 120 字符 | 0 |
| 7 | `activePane` | `bottomLeft` |
| 8 | 改写后复扫 | 已跑，0 新增触线 |
| 9 | 抽样人工读详情 | 已读，记录在案 |

**一句话汇报格式**（每次交付都要给）

```
商品行: 158, 标题 STRICT 触线: 0, 中文残留: 0, 店铺名 0, CDN 0, 客服 0, 标题 >=120 字符: 0
```

> **引用具体数字对，不要说"看起来干净"。**

### 8.7 ★ 交给下一步（流程终点）

```
→ 产出：【结果 JSON】+【报告 Markdown】+【溯源信息】
       + 全部过程清单（命中清单/动作清单/工单清单/豁免记录/最终问题清单）
→ 下一步：交店主
→ ★ 店主可能回复三类：
   · 确认下架清单 → 才执行下架（§6.3 红线）
   · 补资质 → 重新走 §6.1 定上架
   · 指出判错的 → 重新走 §5 扫描 + §6 分流
→ ★ 纯手工执行的话，转 docs/MANUAL_REVIEW.md §11 报告六节
```

---

## 9. 特殊场景处理（步骤 3-14 的例外分支）

### 9.1 用户发现之前下架了商品（信任修复）

当用户说"没有我同意，你怎么随意下架产品"：

1. **立刻停止**下架流水线，不要跑完删除步骤
2. 找出上一轮被标下架的行（读工作区的 `takedown_pids.json` 等下架清单）
3. **逐个重写**那一行的内容：泛化标题 + 纯商品描述
   - "Cola para Cílios Postícios Jhessy" → "Cola para Cílios Postícios, 30 ml"
   - "Creme Para Remoção De Cicatrizes ..." → "Creme Corporal Hidratante, 100 g"
   - "V Face Band ... Shaping Máscara" → "Máscara Facial Elástica em Tecido"
   - "Perfume Feromônio Para Homens" → "Perfume Fragrância Suave, 50 ml"
4. 跑完整流程，输出**全部**行
5. 验证：行数 == 源行数，且被下架行的原标题不再逐字出现

> **通用原则：泛化标题 + 纯商品描述，永远比悄悄删行安全。**
> **绝不可以在说"没有下架"时，不列出上一轮的下架清单。** 信任修复靠透明，不靠沉默。

### 9.2 标题和详情对不上

有时源文件的标题和详情**描述的是两个不同 SKU**。

**检测**：详情里找这个模式 → `Atenção: o item selecionado corresponde ao <X>` —— `<X>` 才是实际发货的商品。

**处理**：按详情的实际商品重写标题，并同步修详情里的指代。

### 9.3 用户审核报告 = 新的一轮审计

**当用户拿回你交付的文件，自己审一遍并给出问题清单时** —— 那是**权威缺陷清单**，不是挑刺。

1. **不要辩解**。逐条核对用户的每一项：确认 / 不确认
2. 说清**根因**：缺陷来自 LLM 输出 / 你的 regex / 你的手工编辑 / 原始源文件
3. **重新审计整个文件**，不只是用户点名的几个例子
4. 用户按优先级分层（高/中）告诉你往哪使劲
5. **改完自己再扫一遍** —— 你的修复可能是下一个缺陷

**根因分类比"改了 8 个 PID"值钱得多** —— 因为它告诉你剩下的 290 行是不是同一类问题。

### 9.4 产品事实问不出来时

授权状态、真实物理规格、适用年龄、安全使用范围 —— 这些**无法从商品文案推断**。

**做法**：交付保守版改写（去掉角色名、收窄使用场景、提高年龄下限），然后给用户**一行一个 PID** 的确认清单：

```
Row 179 | 授权状态 | 默认：按无授权处理，已从标题与详情移除角色名
Row 88  | 适用年龄 | 默认：14 岁起，已加「Não use por menores de 14 anos」
```

用户一句话能回掉好几项。**不要为了凑齐信息而猜。**

### 9.5 年龄/受众变更必须传播到每个字段

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

### 9.6 平台处罚与解封

| 处罚 | 触发 | 解封条件 |
|---|---|---|
| 账号冻结（IP 类） | 品牌方投诉 + Shopee 审核 | **只有投诉方（品牌方）撤销投诉才能重新激活** |
| 账号冻结（监管机构类） | Anvisa / Inmetro / 农业部 | **必须由原投诉机构书面同意解封** |
| IPR 下架 | 商标/版权/专利/外观 | 申诉路径：Contestar → 品牌方决定 |
| 删除（`excluído`） | listing 违规 | **不可恢复**，且计入处罚点 |
| 封禁（`banimento`） | 严重违规 | 问题解决后**可恢复** |
| 限制触达（`alcance limitado`） | 轻度违规 | 整改后**自动恢复** |

> ⚠️ **审批通过 ≠ 解封成功。** 案件必须记录**平台侧实际状态**。

**处罚点机制**：每周一归属 → 一周后生效 → 限制持续 14–28 天 → 每条已认定违规可申诉一次。

**五大 NCL 高风险类目**

| NCL | 类目 | 高风险品牌 |
|---|---|---|
| 03 | 化妆品/个人卫生 | Natura / Boticário / Avon / Lancôme / L'Oréal |
| 09 | 电子/科技 | Apple / Samsung / Sony / Xiaomi / Huawei / Beats / JBL |
| 18 | 皮革/仿皮 | LV / Gucci / Hermès / Chanel / Prada / Coach / MK / Burberry |
| 25 | 服装/鞋帽 | Nike / Adidas / Puma / Supreme / TNF / Champion / Levi's |
| 28 | 玩具/游戏 | Disney / Marvel / Pokemon / Sanrio / Lego / Nintendo |

### 9.7 词库维护节奏

| 节奏 | 内容 |
|---|---|
| **即时** | 收到品牌方投诉或平台下架通知时立即加入 |
| **月度** | 补 INPI 最新注册商标、新冒头的仿牌词 |
| **季度** | 跟踪 Shopee BR / Mercado Livre 政策更新 |
| **半年** | 审计现有 SKU 是否含已加词库的词 |

**扫描时机**：新 SKU 上架前（标题/详情/属性必跑）→ 批量筛查 → 改写后验证 → 定期复核。

---

## 10. 边界与红线（使用者须知）

### 10.1 本流程**不做**的事

| ❌ 不做 | 原因 |
|---|---|
| 发布 / 改线上 / 下架 / 解冻 / 申诉 | 需单独评估批准；自动化不得代做（H6） |
| 处理重大 IP 投诉 | 人工专属 |
| 修改核心规则 | 人工专属 |
| 直接修改生产数据 | 人工专属 |
| 批量删除商品行（未经确认） | 红线，见 §6.3 |
| 编造平台政策、法律条文、来源引文 | 红线（N3） |
| 把"未评估"写成"通过" | 红线（H3） |
| 声称执行了未实际执行的测试 | 红线（N4） |
| 在 IP 结论中使用「侵权」表述而无投诉/授权/通知支撑 | 红线（N8） |

### 10.2 来源层级与"什么能做阻断"

| `source.tier` | 含义 | 可否产生 `block` 类动作 |
|---|---|---|
| `platform_official` | Shopee 官方页面明确写出 | ✅ |
| `law` | 巴西联邦法律明文 | ✅ |
| `internal_risk` | 内部风控建议 | ❌ |
| `unverified` | 未验证假设 | ❌ |
| `ai_inference` | AI 模型推断 | ❌ |
| `technical` | 技术调研结论 | ❌ |

**`source.excerpt` 必须逐字出现在抓取件中** —— 引文核验不通过 → 任务不通过。

### 10.3 错误处理

| 情形 | 行为 |
|---|---|
| 读入失败 | **不中断整批**，记 error |
| 某模块不可用 | 明确说明该检查**未执行**，**不得当作通过** |
| 某模块无结果 | 记录为空，**不得当作"无风险"** |
| 契约校验失败 | 拒绝整合该模块结果 |
| 无任何模块产出 | 不生成空结论，显式失败 |

---

## 11. 快速命令速查

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

> ⚠️ **所有 Python 命令都要 `env -u LD_LIBRARY_PATH` 前缀** —— 见 §4.4。

---

## 12. 未决事项

| # | 问题 | 默认处置 |
|---|---|---|
| 1 | 词库中 `internal_risk` 层级的词是否全部升级为 `platform_official` | 保持 `internal_risk`，只产生 `flag` |
| 2 | 处罚点分值表（平台未公开） | 只用「是否扣分」标识，**不编造分值** |
| 3 | INPI 查询自动化程度 | 保留人工查询 + 记录引用 |
| 4 | 「无法文字规避」品类的工单落地方式 | 本期只做标记与清单 |

---

## 13. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-10-28 | 初版：以使用者视角把现有流程做成框架 —— 八步流程、四态语义、风险×动作、硬约束、下架红线、改写铁律、交付清单 |
| 2.0.0 | 2026-10-28 | **与 MANUAL_REVIEW 对齐**：① 章节标题统一挂「步骤 N」（步骤 0-15），与 `docs/MANUAL_REVIEW.md` 共用同一套步骤编号 —— 原本本文用 ①-⑧ 圆圈编号、那份用「第 N 步」，两套编号打架，现合并为一套；② §1 全流程总览重写为步骤 0-15 版，补出定类目/四张清单/合并总表/判定/豁免核对/工单六段；③ §1.1 补交接总表（每步产出什么）；④ §1.2 补两条提前退出；⑤ §0.2 新增两份文档分工表（每一步在哪份文档里）；⑥ §3 / §4 / §5 / §6 / §7 / §8 各加「★ 交给下一步」段；⑦ 各段补「↗ 纯手工执行的话，转 MANUAL_REVIEW §X」跳转 |
