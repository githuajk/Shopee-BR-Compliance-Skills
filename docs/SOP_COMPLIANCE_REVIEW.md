# Shopee BR 商品合规审核 — 统一操作规程（SOP）

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-SOP-001` |
| 版本 | 1.0.0 |
| 状态 | **Draft — 合并自历史审核方法，待用户审批** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | Shopee 巴西站商品合规审核的全部人工与自动方法 |
| 归属模块 | `shopee-br-compliance`（主 Skill） |
| 相关文档 | `PROJECT_RULES.md`、`contracts/risk_action_matrix.json`、`lexicon/`、`tests/test_plan.md` |
| 合并来源 | 见 §1 |

---

## 1. 本文档的合并来源

| 来源 | 内容 | 状态 |
|---|---|---|
| 工作区外部：`_learning/SOP_BIBLE.md` | 9 大业务系统铁律速查 | 已合并 |
| 工作区外部：`_learning/SHOPEE_MASTER_SOP.md` | 31 个踩坑（V1→V39 实战） | 已合并 |
| 工作区外部：`_learning/02_risk_dictionary.md` | 触线→中性映射精简版 | 已合并 |
| 工作区外部：`_learning/compliance_audit/...risk_words.md` | 7 类 1320 词完整词库 | 已合并 → `lexicon/` |
| 工作区外部：`_learning/compliance_audit/...xiuyu_review_learning.md` | 店主 491 商品审阅反馈 | 已合并 |
| 工作区外部：`_learning/compliance_audit/...inpi_...md` | INPI 商标查询 | 已合并 → `ip-review` |
| 工作区外部：`_learning/compliance_audit/...shopee_侵权政策_官方.md` | 平台政策原文 | 已合并 → `research/raw/` |
| `.archive/phase0_prototype/src/` | 原型引擎实现 | 已合并 → 判定语义 |
| `.archive/phase0_prototype/docs/adr/` | 6 份 ADR | 已合并 → 硬约束 |

> ⚠️ **原始文件保留在 `/config/dianshang/_learning/`，本文件是它们的合并视图。** 两者冲突时，以本文件为准（并应回写修正原始文件）。

---

## 2. 审核方法的四条总原则

这四条来自 31 个实战坑的收敛，是所有后续条款的上位原则。

| # | 原则 | 依据 |
|---|---|---|
| **P1** | **词库命中是信号，不是结论** | 词库只做筛查；结论必须由规则层依据来源判定 |
| **P2** | **缺数据 ≠ 通过** | 输入缺失 → 明确报「未评估」，不得静默放过 |
| **P3** | **不猜测** | 无法判定 → 标记需人工复核，不编造 |
| **P4** | **逐字可核验** | 引文、词条、判定依据都必须能回溯到原始抓取件 |

---

## 3. 审核流程（七步）

```
① 定位源文件 → ② 读入并标准化 → ③ 字段完整性检查 → ④ 词库/规则扫描
        → ⑤ 上下文判定 → ⑥ 人工分流 → ⑦ 交付与留痕
```

### ① 定位源文件

> **坑 31 铁律**：多店文件不一定在本机。**先定位再动手。**

```bash
ls /config/dianshang/_ad_analysis/raw/_store_<store>/
find /config -iname "*mass_update*"
# 用报告里的 PID 反查
for pid in <PIDs>; do
  find /config -name "*.xlsx" | while read f; do
    unzip -p "$f" xl/sharedStrings.xml 2>/dev/null | grep -q "$pid" && echo "$f"
  done
done
```

**PID 一个都查不到 = 文件不在本机** → 直接请用户上传，**不要基于审核报告"重建"文件**。

审核报告只给**问题清单**，不给**商品原文** —— 报告里的"用词不自然"无法还原成实际内容。

### ② 读入并标准化

- Excel 仅作输入，导入后转 JSON（`data/schema/product.schema.json`）
- 原始输入**不得被覆盖或修改**
- 解析失败/字段缺失 → 记 error，**不中断整批**

### ③ 字段完整性检查

在扫描**之前**先做这一步，避免把"数据缺失"误判成"listing 违规"。

| 缺失字段 | 处理 |
|---|---|
| `title` | 该记录不参与审核，记 error |
| `description` | 相关规则标记未评估 |
| `images` | 图片类规则标记未评估 |
| `brand` | 品牌类规则标记未评估 |
| `category` | 类目规则标记未评估 |

> **这就是硬约束 H3 的落地。** 原型曾因缺 `images`/`category`/`brand` 列，把 15 个商品全判违规 —— 100% 误报。

### ④ 词库/规则扫描

见 §4 与 §5。

### ⑤ 上下文判定

词库命中后**必须**看上下文。详见 §6。

### ⑥ 人工分流

按 `contracts/risk_action_matrix.json` 决定动作。**高风险动作一律人工专属**（硬约束 H6）。

### ⑦ 交付与留痕

- 结果 JSON + 报告 Markdown
- 写明：范围、商品数、结论分布、**未评估项**、已查阅规则
- 原始文件留在原处，产物另存

---

## 4. 词库扫描方法

### 4.1 匹配铁律（按重要度排序）

| # | 铁律 | 反例 → 正例 |
|---|---|---|
| 1 | **单词边界 `\bword\b`**，不要子串匹配 | `antidade` ≠ `quantidade` |
| 2 | **葡语动词必含全部变位** | `\bproporciona\w*\b` 而非 `\bproporciona\b` |
| 3 | **形容词 ≠ 同根动词** | ❌ `\bproporcional\b` ✅ `\bproporciona(m|r|do|da|das|mos)\b` |
| 4 | **大小写同时匹配** | `[Pp]ara garantir\b` |
| 5 | **大小写不敏感 + 变体归一** | `N1ke→nike`、`@pple→apple` |
| 6 | **描述性用法 ≠ 承诺用法** | `garantir conforto` 不等于 `garantido` |
| 7 | **重音折叠仅用于匹配**，输出保留原形 | |

### 4.2 葡语 `\b` 不可靠（已知坑）

> 葡语的 `\b` 会吞掉相邻单词的首字母。

```python
# ❌ 错误 —— 会吞掉 "Óculos" 的首字母
re.sub(r'\s*at[óo]xico\b\s*', ' ', s)

# ✅ 正确 —— 显式排除字母边界
re.sub(r'(?<![a-zA-Zà-ÿÀ-ß])at[óo]xico(?![a-zA-Zà-ÿÀ-ß])', ' ', s)
```

**所有葡语关键词匹配一律用显式 lookaround。**

### 4.3 变体归一

```
原文 → 小写 → Unicode NFD → 去除组合附加符 → 匹配
输出保留原文形态
```

### 4.4 全字段扫描

> **漏检教训**：标题仅 6% 命中，详情 94% 命中 → **标题+详情+属性+品牌全扫**，不能只扫标题。

---

## 5. 改写方法（命中后处置）

### 5.1 处置分档

| 风险等级 | 含义 | 动作 |
|---|---|---|
| 🔴 **high** | 出现即可能下架/被追责 | 立即改写或下架；查授权 |
| 🟡 **medium** | 需授权或资质才能用 | 要求授权证明，否则移除 |
| 🟢 **low** | 注意但不直接违规 | 记录但保留 |

### 5.2 单遍替换铁律（坑 20，★★★）

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
3. 实测效果：655 → 10 触线命中，零级联

### 5.3 替换值铁律（坑 18 / 21）

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

_assert_no_charclass_in_values(RULES)
```

### 5.4 列表并列项铁律（坑 25）

> **不要批量替换列表里的并列项** —— 换掉其中一项就会留下空洞。

```
'Adequado para, e todos os tipos de.'                                    ← 空洞
'Adequado para,, palmas manchadas, ...,,,,,, auxilia nos cuidados...,, ' ← 空洞成片
```

**修复**：病句无法靠规则救 → **整段手工重写**。

**配套铁律**：替换后必须**抽样读详情全文**，不能只看扫描器数字。

### 5.5 长度护栏

| 检查 | 阈值 | 失败处理 |
|---|---|---|
| 详情长度 | ≥ 500 字符 | 补「Como usar」+「Conteúdo da embalagem」两段 |
| 剥模板/剥 URL 后长度 | ≥ 250 字符 | 过短 → 按标题生成基础描述（坑 23） |
| 标题长度 | 60–95 字符（上限 100） | 见 §5.6 |

### 5.6 标题截断铁律（坑 27）

> **截断必须在词边界，不能裸切。**

```python
cut = new[:95]
sp = cut.rfind(' ')
new = cut[:sp].rstrip(' ,;:-') if sp > 60 else cut.rstrip(' ,;:-')
```

**配套铁律**：

1. 截断后跑「末尾悬空词」检测：`\b(de|da|do|para|com|em|a|o|e|pa|vi)$`
2. **标题被截断 = 语义也丢了** → 回源标题补，不是简单砍短
3. 标题与详情品类不一致 → **以详情为准**统一，并同步修详情里的指代（坑 28）

---

## 6. 误报控制（4 个已知模式）

| 场景 | 正确处理 | 错误处理 |
|---|---|---|
| 工具类（菜刀/剪刀/螺丝刀/美工刀） | **豁免**，不标 weapon | 标为武器 |
| `Hermes` 出现在快递/邮箱类描述 | 默认按侵权命中，**需人工复核** | 直接放行 |
| `CE` 在"产品印有 CE 标志" | 事实陈述，**记录但不拦截** | 判违规 |
| 品牌名作为产品通用词 | **默认仍按侵权命中** | 自动放行 |
| `reduzir` 46 处（"reduzir a entrada de água"） | 功能描述，**保留** | 全部改写 |
| `desconforto` 4 处（"em caso de desconforto, suspenda o uso"） | 安全提示，**保留** | 全部改写 |
| `seguro`（"fechamento seguro"） | 功能描述，**保留** | 全部改写 |

> **改这些反而会降低合规性。** 误报控制的价值高于"扫描器数字归零"。

### 6.1 品类歧义消解（坑 24）

> `escova` 既是梳子也是刷子 —— 具体关键词必须排在前面，并单独建 override 表。

```python
CATEGORY_OVERRIDES = [
    (r'\bescova\s+(?:de\s+)?(?:limpeza|frestas|dentes|carro)\w*\b', 'limpeza'),
    (r'\bescova\s+de\s+dentes\b', 'banheiro'),
]
# 先查 override，再退回通用 infer_use
```

### 6.2 葡语大小写启发式禁令（坑 29）

> **不要用"小写字母后跟大写字母"判定缺空格** —— 葡语里这完全合法。

```python
# ❌ 会把 "não" 拆成 "n ão"，详情膨胀 39%
re.sub(r'(?i)([a-zà-ÿ])(?=[A-ZÀ-Þ][a-zà-ÿ])', r'\1 ', text)
```

缺空格要**按已知词**修，不能用通用启发式。

---

## 7. 反模板化（店主 491 商品审阅反馈）

> 店主 2026-09-17 亲自审阅 491 个商品：**110 优先核实 / 331 修改补证 / 50 基本可读**。

### 7.1 最严重问题

**491 个商品的详情完全相同** —— 全用统一模板。这是店主判定"最严重"的问题。

### 7.2 触发的"套模板/批量味"特征

任一即打回：

- `✅` × 4+
- 同一句 "Quer X mais forte" 出现 5+ 次
- `new_desc` 一字不差的 2+ 商品
- 含医疗词 / 含中文
- 标题里同时出现 `pomada`/`creme`/`gel`/`cream`/`loção`/`spray`/`sérum`/`máscara`/`pó`/`óleo` 中的 3 个以上
- 重复用 `moderno`/`tendência`/`atual`/`inovador`

### 7.3 首句唯一率（坑 26，★★★）

> **"首句种类数"这个指标本身具有欺骗性** —— 111 种 vs 245 条商品，平均复用 2.2 次，但只要重复的句子都出现在同一类目，人工看过去就是"模板"。

**验收指标必须是首句唯一率 100%**（不是"种类数"）。

**首句 = 商品名 + 具体用途，必须含商品实词**：

```
✅ 'Saco de malha transparente para organizar livros e materiais.'
✅ 'Suporte de pia fixado na parede para esponjas e utensílios.'
❌ 'Item para organizar a rotina, com capacidade ampla e alça confortável.'
```

**规则拼句会出病句** —— 葡语句法（介词搭配/冠词/性数一致）规则搞不定：

```
'Kit com o dia a dia para o uso do dia a dia.'
'Escova de para Escova de.'
```

→ **用 LLM 写首句**，但必须跑后置清洗（LLM 会把源标题里的**中文 hashtag** 带进首句：`'...durante等活动.'`）。

### 7.4 店主的 10 条原则

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

### 7.5 具体反例

| ❌ 不可用 | 原因 |
|---|---|
| "Material premium" | 缺材质依据 |
| "Acabamento cuidadoso" | 太空泛 |
| "Confortavel" | 对眼镜/工具不适用 |
| "Tipo: Cosmético" | 对首饰/工具不适用 |
| "Origem: China" | 缺逐品依据，与 Coreano/Korea 冲突 |
| "Todos os tipos de pele" | 普适承诺，未经证明 |
| "Testado dermatologicamente" | 暗示已测试 |
| "Produto original" | 缺真伪证据 |

**替代写法**：`Importado` / `Linha profissional` / `Padrão Internacional`

---

## 8. 葡语写作规范

### 8.1 重音必对

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

### 8.2 数字与容量

- `30ml`（小写 ml）/ `50g`（小写 g）
- `FPS 15`（葡语用 FPS 不是 SPF）
- `12 horas`（葡语用复数）
- `R$ 99,90`（葡语货币格式）

### 8.3 营销词本地化

| ❌ | ✅ |
|---|---|
| `mais vendido` / `best seller` | `um dos mais procurados` |
| `alta qualidade` | `qualidade confiável` 或具体描述 |
| `frete grátis`（Shopee 自带） | 删除 |

### 8.4 触线→中性替换表

完整表见 `lexicon/rewrite_map.json`（机器可读版本）。

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
| Antiembaçcan | Antivisão Embaçada |
| proporcionar（变位） | facilitar |
| emagrece / modela | 删除 / design |
| Redutor de medidas | 删除 |

### 8.5 残句修复规则

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

---

## 9. 平台处罚与解封

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

### 9.1 五大 NCL 高风险类目

| NCL | 类目 | 高风险品牌 |
|---|---|---|
| 03 | 化妆品/个人卫生 | Natura / Boticário / Avon / Lancôme / L'Oréal |
| 09 | 电子/科技 | Apple / Samsung / Sony / Xiaomi / Huawei / Beats / JBL |
| 18 | 皮革/仿皮 | LV / Gucci / Hermès / Chanel / Prada / Coach / MK / Burberry |
| 25 | 服装/鞋帽 | Nike / Adidas / Puma / Supreme / TNF / Champion / Levi's |
| 28 | 玩具/游戏 | Disney / Marvel / Pokemon / Sanrio / Lego / Nintendo |

---

## 10. 无法靠文字规避的品类

> 有些商品的合规性由**商品本体**决定，改文案无效。

| 类别 | 监管依据 | 为什么改写无效 |
|---|---|---|
| 化妆品 | ANVISA 强制注册 | 无注册号不能卖，改成"辅助"也不行 |
| 器械/矫形 | ANVISA | 监管属性由品类决定 |
| 宠物口腔 | 兽药监管 | 宣称去牙结石/除口臭即触及兽药 |
| 化学制剂 | ANVISA | 包装缺成分/警示/批号/有效期即违规 |
| 太阳镜 | INMETRO | 需 UV 实测报告，文字补不了 |
| 儿童安全 | INMETRO | 需认证 |

**这类商品的处理**：标记为「需资质/无法文字规避」，进入人工工单，**不进入批量改写**。

---

## 11. LLM 使用的三条铁律

LLM 在改写流程中是高危环节 —— 实测踩过多个坑。

| # | 铁律 | 事故 |
|---|---|---|
| 1 | **LLM JSON 非法转义会整批丢数据** | 69 条描述因 `Invalid \escape` 退回规则版；改宽松逐对象解析后全部救回 |
| 2 | **LLM 会往葡语里注入中文/法语碎片** | 46 处（`"para uso殺，朝"`、`"nécessaire"`），需字符集直接删 |
| 3 | **LLM 硬切会在 95 字符处切碎单词** | `'...e acessórios de vi'`、`'...amplificador pa'` |

**配套要求**：

- LLM 输出必须**逐条容错解析**（不能用整体 `json.loads` 一刀切）
- LLM 输出必须**后置清洗**：删中文/法语碎片、删控制字符
- 硬切必须**回退到词边界**
- LLM 结果必须**抽样人工读**，不能只看扫描器数字

---

## 12. xlsx 处理铁律（8 条）

| # | 铁律 |
|---|---|
| 1 | **sharedStrings 引用，不要 inlineStr**（某些软件不识别 inlineStr） |
| 2 | **只替换 C/D 列，绝不删 A/B/E**（PID 一字不动） |
| 3 | **列字母在前**：`r="C7"` 不是 `r="7C"` |
| 4 | 保持 `s="3"` 样式属性 |
| 5 | `activePane "bottom_left"` → `"bottomLeft"`（驼峰） |
| 6 | **控制字符必删**：`\x00-\x08\x0B\x0C\x0E-\x1F\x7F` |
| 7 | **regex 不能跨界吃单元格** —— 用 `(?:(?!</c>).)*` 负向先行断言 |
| 8 | **openpyxl `max_row` 不可信** —— 用 `len(ws.iter_rows())` |

**DISPIMG（wps 私有）保图**：`wb.save()` 会丢图 → 走 zipfile patch 路径，只替换 `sheet1.xml` + `sharedStrings.xml`，`media/` `cellimages.xml` `drawings/` `_rels/` 原样保留。

---

## 13. 运行环境铁律

> **Hermes 运行时会把 `LD_LIBRARY_PATH` 指向自带目录**，其中的 `libcrypto.so.3` 与系统 OpenSSL 冲突 → `ssl` 模块直接 ImportError。

```bash
env -u LD_LIBRARY_PATH python3 script.py
```

**必须在进程启动前清掉**（脚本内 `os.environ.pop` 已太晚，ssl 已被运行时导入）。

脚本内加 preflight 自检：

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

---

## 14. 不可由文字规避 / 需人工工单的处理

> 见 §10 品类表。**处理流程**：

```
扫描命中 → 判断是否属于「无法文字规避」品类
  → 是 → 生成工单（PID + 缺什么资质 + 建议）→ 不进批量改写
  → 否 → 进入改写流水线 → 改写后复扫 → 抽样人工读
```

---

## 15. 词库维护节奏

| 节奏 | 内容 |
|---|---|
| **即时** | 收到品牌方投诉或平台下架通知时立即加入 |
| **月度** | 补 INPI 最新注册商标、新冒头的仿牌词 |
| **季度** | 跟踪 Shopee BR / Mercado Livre 政策更新 |
| **半年** | 审计现有 SKU 是否含已加词库的词 |

**扫描时机**：新 SKU 上架前（标题/详情/属性必跑）→ 批量筛查 → 改写后验证 → 定期复核。

---

## 16. 本 SOP 与 Skill 架构的对应

| 本 SOP 章节 | 归属 Skill | 机器可读资产 |
|---|---|---|
| §3 审核流程 | `shopee-br-compliance` | `skills/shopee-br-compliance/references/execution_workflow.md` |
| §4 词库扫描 | `shopee-br-listing-audit` | `lexicon/term_groups.json` |
| §5 改写方法 | `shopee-br-listing-audit` | `lexicon/rewrite_map.json` |
| §6 误报控制 | `shopee-br-listing-audit` | `lexicon/exemptions.json` |
| §7 反模板化 | `shopee-br-listing-audit` | `lexicon/quality_patterns.json` |
| §8 葡语写作 | `shopee-br-listing-audit` | `lexicon/rewrite_map.json` |
| §9 处罚与解封 | `shopee-br-duplicate-detection` | `skills/shopee-br-duplicate-detection/references/penalty_mechanics.md` |
| §10 无法规避品类 | `shopee-br-listing-audit` | `lexicon/non_avoidable.json` |
| §11 LLM 铁律 | `shopee-br-listing-audit` | `references/` 待补 |
| §12 xlsx 铁律 | `shopee-br-data-ingestion` | `skills/shopee-br-data-ingestion/references/format_matrix.md` |
| §13 运行环境 | 全局 | `scripts/check_all.sh` |

---

## 17. 未决事项

| # | 问题 | 默认处置 |
|---|---|---|
| 1 | 词库中 `internal_risk` 层级的词是否全部升级为 `platform_official` | 保持 `internal_risk`，只产生 `flag` |
| 2 | 处罚点分值表（平台未公开） | 只用「是否扣分」标识，不编造分值 |
| 3 | INPI 查询自动化程度 | 保留人工查询 + 记录引用 |
| 4 | 「无法文字规避」品类的工单落地方式 | 本期只做标记与清单 |

---

## 18. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-10-27 | 初版：合并 9 份历史文档、31 个实战坑、店主 491 商品审阅反馈、7 类 1320 词词库 |
