# 词库扫描规范

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-LA-005` |
| 所属模块 | `shopee-br-listing-audit` |
| 版本 | 1.1.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27；2026-10-28 索引重写（1.1.0） |
| 适用范围 | 合并词库的使用方式、匹配算法与误报控制 |
| 相关文档 | `lexicon/term_groups.json`、`contracts/lexicon_rule_map.json`、`docs/SOP_COMPLIANCE_REVIEW.md` §4 |
| 未决事项 | 大规模索引（前缀分桶 + C 级 `str.find`）**已实现**（2026-10-28，§3.5 / §7.1；词库 104 组 / 211,019 词，其中 C 类监管目录 209,652 词）；EX-BRAND-GENERIC 的同行误降级残留需改 `lexicon/exemptions.json` 的 pattern（data-ingestion 所有，走契约变更） |

---

## 1. 合并词库的构成

| 文件 | 内容 | 规模 |
|---|---|---|
| `lexicon/term_groups.json` | 词组（扫描用） | **104 组 / 211,019 词**（2026-10-28 集成扩充后；原 37 组 / 856 词） |
| `lexicon/rewrite_map.json` | 触线 → 中性替代（改写用） | 8 类映射 |
| `lexicon/exemptions.json` | 误报豁免规则 | **51 条**（2026-10-28 集成时 61 条；E2E 验收轮删 10 条高特异性活性成分/疫苗/农药组 blanket EX-CATALOG，保留 27 条对低判别力通用目录降噪）|
| `lexicon/quality_patterns.json` | 套模板/批量味检测 | 15 条特征 |
| `lexicon/non_avoidable.json` | 无法文字规避的品类 | 6 类 |
| `lexicon/verb_conjugations.json` | 葡语动词变位匹配表 | 7 个动词 |
| `contracts/lexicon_rule_map.json` | 词组 → 规则映射 | 100 条 |

**合并来源**：2026-09-15 合规审计线的 7 类 1320 词词库 + `02_risk_dictionary.md` 触线词 + 原 25 组 179 词。覆盖率经逐词比对达 **96.3%**（剩余为文档说明文字，非词条）。

---

## 2. 词组分类与来源层级

| `risk_hint` | 组数 | 含义 |
|---|---|---|
| `prohibited` | 15 | 禁售类目 |
| `restricted` | 12 | 受限类目 |
| `ip_signal` | 8 | 知识产权信号 |
| `listing_violation` | 4 | 刊登质量 |

| `source_tier` | 允许的最高动作 |
|---|---|
| `platform_official` | `block` |
| `law` | `block` |
| `internal_risk` | `flag` |

> **词库命中恒为信号，不是结论。** 最终动作由规则层依据规则的 `source_tier` 决定 —— 映射表只声明「命中后去判定哪条规则」。

---

## 3. 匹配算法

### 3.1 归一化管线

```
原文
 → 小写
 → Unicode NFD
 → 去除组合附加符（重音折叠）
 → 显式边界匹配
```

> **重音折叠只用于匹配，输出必须保留原文形态。**

### 3.2 葡语边界（必读）

葡语词条匹配一律使用**显式 lookaround**，不用 `\b`：

```python
# ✅ 项目约定：显式边界
re.search(r'(?<![a-zA-Zà-ÿÀ-ß])at[óo]xico(?![a-zA-Zà-ÿÀ-ß])', 'produto atóxico')
```

**为什么不用 `\b`（实测结论，不是传闻）**

| 事实 | 说明 |
|---|---|
| `\b` 是**零宽**断言 | 它不会「吞掉」任何字符 —— 文档旧版曾这样写，是错的。`re.search(r'\bÓculos', 'Óculos')` 正常命中 |
| Python 3 的 `\w` **包含**重音字母 | `re.match(r'\w', 'ó')` → True，`re.match(r'\w', 'Ó')` → True。所以 `\b` 落在 `ó` / `Ó` 之前，与显式边界**结论一致** |
| `\b` 的真实弱点 | `\w` 也包含**数字与下划线**。`re.search(r'\bat[óo]xico\b', 'x_atóxico')` → **不命中**（`_` 算词字符），而显式 lookaround → **命中** |
| 显式边界更严格 | lookaround 的字符类只含字母，所以 `9at[óo]xico`、`_at[óo]xico` 都不算词首 —— 边界语义完全由我们定义，不依赖 Python 的 `\w` 定义 |

**结论**：两者在「字母 vs 非字母」的常见情形下结论一致；差异出现在
**数字/下划线相邻**时。项目选显式 lookaround，是因为边界语义完全可控、
不随 Python 版本或 `re.ASCII` 标志变化。

> ⚠️ 上一版文档写「`\b` 会吞掉相邻单词的首字母」，并给出
> `re.search(r'\bat[óo]xico\b', 'Óculos para visão')` 的示例 ——
> **该示例两种写法都不命中**（`at[óo]xico` 与 `Óculos` 本就不同词），
> 论据不成立，已更正。

**当前规则库的实际做法**：28 条规则用显式 lookaround
（`SBR-PI-*` / `SBR-RI-*` / `SBR-IP-001/002/006/007` / `SBR-LV-001/002` /
`SBR-MED-*`）。词库 `lexicon/term_groups.json` 的边界由
`tools/scan_lexicon.py` 的归一化与组级边界策略统一处理。

### 3.3 匹配顺序

1. **词组按最长优先** —— 先匹配 "todos os direitos reservados"，再匹配 "direitos"。
2. **全字段扫描** —— 标题 + 详情 + 属性 + 品牌。

> **漏检教训**：标题仅 6% 命中，详情 94% 命中。只扫标题会漏掉绝大部分。

### 3.4 命中必须记录位置

```json
{
  "group_id": "ip_marca_global",
  "term": "Nike",
  "field": "description",
  "offset": 142,
  "excerpt": "...produto inspirado no estilo Nike...",
  "confidence": "medium"
}
```

**不能只记「命中了」** —— 复核者需要知道在哪看到的。

### 3.5 规模与索引

856 词规模下用普通编译正则足够；2026-10-28 词库扩充至 211,019 词后，改用**前缀分桶 + C 级 `str.find`** 实现：

```python
# tools/scan_lexicon.py · _build_index / scan_text
by_pre: dict[str, list] = {}          # 前 3 字符分桶（L=2 时前缀即全词）
for gid, terms in groups.items():
    for t in terms:
        key = norm(t)                 # 小写+NFD去重音
        by_pre.setdefault(key[:3], []).append((key, len(key), gid, t))
# 匹配期：计算文本 3-gram 集合，跳过未出现的整桶，再用 C 级 find
t3 = frozenset(n[i:i+3] for i in range(Ln-2))
for pre, entries in by_pre.items():
    if pre not in t3: continue
    i = n.find(key); while i != -1: ...
```

> **纯标准库实现**，无第三方依赖。索引按（词库目录, mtime）缓存在模块级，同一进程内重复 `Scanner(...)` 是 O(1)。

---

## 4. 误报控制

### 4.1 豁免规则

`lexicon/exemptions.json` 定义 51 条豁免（2026-10-28 集成后：原 7 条 + 37 条 `EX-CATALOG-*` 目录降级 + 17 条 `EX-D6-*` 批次；交付时点的 44 条为 D6 批次并入前；**E2E 验收轮（batch001）进一步删 10 条高特异性活性成分/疫苗/农药组的 blanket EX-CATALOG**，保留 27 条对低判别力通用目录组降噪）：

| ID | 场景 | 动作 |
|---|---|---|
| `EX-TOOLS` | 菜刀/剪刀/螺丝刀/美工刀 | `exempt` |
| `EX-CE-FACT` | "产品印有 CE 标志" | `flag_low` |
| `EX-HERMES-CARRIER` | Hermes 作为快递/物流商名 | `require_review` |
| `EX-REDUZIR` | "reduzir a entrada de água" | `exempt` |
| `EX-DESCONFORTO` | "em caso de desconforto, suspenda o uso" | `exempt` |
| `EX-SEGURO-FUNCIONAL` | "fechamento seguro" | `exempt` |
| `EX-BRAND-GENERIC` | 品牌名可能是产品通用词 | `require_review` |
| `EX-CATALOG-*` ×**27** | ANVISA/CTI/MAPA 监管目录中低判别力通用组降级 | `exempt` |
| `EX-D6-*` ×17 | 2026-10-28 批次登记的误报场景 | `flag_low` / `require_review` |

> ⚠️ **豁免 ≠ 放行。** 命中仍要记录，只是降低置信度或转为需复核。

**豁免匹配语义（2026-10-28 D1–D5 修复后）**：

1. **区间重叠才豁免（D1）** —— 豁免正则的某个匹配区间必须与该命中的区间
   `[offset, offset+len]` 重叠，命中才标记豁免。同一字段里与工具词无关的
   武器命中不会被 `EX-TOOLS` 连带降级。保留的 `EX-CATALOG-*`（×27）全文
   pattern（`[\s\S]*`）区间覆盖全文，对应目录组全组降级是既定降噪行为。
   E2E 验收轮已对 10 个高特异性组（活性成分/疫苗/农药，目录组中判别力核心）
   **取消** blanket 豁免，使特异性药名仍驱动 `SBR-MED-004` 的
   `require_evidence` 取证（安全网）。
   **引擎配套（batch001）**：当某规则仅由「全被豁免候选」触发时（`detail`
   里 `lexicon_candidates_all_exempt=true`），其动作封顶 `flag_for_review`、
   置信度降为 `signal` —— 目录通用词（棉等）不再对干净商品要求全套注册
   证据；只要有一项非豁免候选（如活性成分组命中）即维持原动作。
2. **重音折叠后匹配（D4）** —— 豁免正则作用于归一化文本（小写 + NFD 去重音）。
   归一化文本是纯 ASCII 形态，其中 pattern 里的 `\b` 等价于显式词边界，
   不会再吞相邻重音字母（SOP §4.2 的葡语 `\b` 铁律在原文层仍然成立）。
3. **换行压平（D5）** —— 豁免匹配前把 `\n` / `\r` 替换为空格（等长替换，
   偏移不变），`^...$` 锚定模式不再被多行文本绕开。已知残留：
   `EX-BRAND-GENERIC` 的 `^(.*)...` 区间覆盖整行，同一无关通用词会使整行
   命中降级 —— 需改 pattern 本身（data-ingestion 所有，走契约变更流程）。

### 4.2 豁免的判定顺序

```
词库命中
 → 查 exemptions.json（按 group_id + pattern）
 → 命中豁免 → 标记豁免原因，仍然记录
 → 未命中豁免 → 进入上下文判定
```

### 4.3 已知误报高发区

| 词 | 实际语境 | 结论 |
|---|---|---|
| `reduzir` | "reduzir a entrada de água"（功能描述） | **保留** |
| `desconforto` | "em caso de desconforto, suspenda o uso"（安全提示） | **保留** |
| `seguro` | "fechamento seguro"（功能描述） | **保留** |
| `melhor` | "melhor custo-benefício"（中性比较） | 需上下文 |
| `tipo` | "tipo de produto"（普通词） | 需上下文 |

> **改这些反而会降低合规性。** 误报控制的价值高于「扫描器数字归零」。

---

## 5. 词组 → 规则映射

`contracts/lexicon_rule_map.json` 定义 100 条映射。

```json
{
  "group_id": "proibido_armas",
  "rule_ids": ["SBR-PI-001"],
  "note": "武器弹药。"
}
```

### 5.1 映射原则

| 原则 | 说明 |
|---|---|
| 一个词组可映射多条规则 | 如 `ip_contrafito` 既触 `SBR-IP-002` 也触 `SBR-LV-007` |
| 词库不得放大风险 | `internal_risk` 词组不得映射到非官方来源的 `block` 规则 |
| 未映射词组不触发规则 | 只作为扫描提示列出 |

### 5.2 硬约束校验

`tools/validate_lexicon.py` 强制检查：

- **H1**：IP 结论规则强制人工复核（`decision=allow` 的豁免规则除外）
- **H2**：所有 `block` 规则必须来自 `platform_official` / `law`
- **H3**：映射表引用的 rule_id 全部存在
- 词组引用完整性、跨组重复报告、替换值无字符类、葡语边界显式化

---

## 6. 改写流程

### 6.1 单遍替换（不可违背）

> **顺序逐条 `re.sub` 必然产生级联污染。**

```python
# ❌ 级联
for pat, rep in RULES:
    text = re.sub(pat, rep, text)

# ✅ 单遍合并正则 + 分派
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

text = COMBINED.sub(dispatch, text)
```

### 6.2 替换值铁律

**替换值里绝不写字符类。**

```python
def resolve_classes(value):
    """'dom[ée]stico' -> 'doméstico'"""
    return re.sub(r'\[([^\[\]\n]{1,4})\]',
                  lambda m: m.group(1)[0] if m.group(1) else '', value)

def _assert_no_charclass_in_values(rules):
    bad = [(p, r) for p, r in rules
           if re.search(r'\[[a-zA-Zà-ÿÀ-Ý]{1,4}\]', r)]
    if bad:
        raise SystemExit(f'替换值含字符类: {bad}')
```

### 6.3 改写后的强制校验

| 检查 | 阈值 | 失败处理 |
|---|---|---|
| 详情长度 | ≥ 500 字符 | 补「Como usar」+「Conteúdo da embalagem」 |
| 剥模板/剥 URL 后长度 | ≥ 250 字符 | 按标题生成基础描述 |
| 标题长度 | 60–95 字符（上限 100） | 在词边界回退 |
| 末尾悬空词 | 无 | `\b(de|da|do|para|com|em|a|o|e|pa|vi)$` |
| 复扫 | 触线词数下降且无新增 | 出现新触线 → 回退该条 |
| 标点空洞 | 无 `,,` `,,,` | 整段手工重写 |

> **改写后必须抽样读详情全文**，不能只看扫描器数字。

---

## 7. 实现现状与已知限制

本节记录**实测**的现状，不写设想。

| 项 | 状态 | 实测依据 |
|---|---|---|
| 大规模索引 | ✅ **已实现**（前缀分桶 + C 级 `str.find`，纯标准库） | 210,992 词冷启动构建 **0.85 s**；进程内命中缓存后重复构造 **~0.06 ms**；见 §7.1 |
| 扫描器 CLI | ✅ **已实现** | `tools/scan_lexicon.py`，参数：`--title` / `--description` / `--brand` / `--input` / `--self-test` |
| 性能基线 | ✅ **已实测**（100 组 / 210,984 词） | 见 §7.1 |
| 词库与规则的联动测试 | ✅ **已实现** | `tools/verify_fixtures.py` 的 108 条夹具-规则断言（58 应命中 / 50 应不命中）+ `tools/scan_lexicon.py --self-test` 的 19 条回归用例（12 条基础 + D1–D5 缺陷回归） |

### 7.1 性能基线（实测）

测量条件：本机，100 组 / 210,984 词词库，2026-10-28 索引重写后复测。

| 指标 | 实测值 |
|---|---|
| 冷启动构建（新进程，含 21 MB JSON 载入 + 归一化 + 分桶） | **0.85 s** |
| 进程内缓存命中后重复 `Scanner(...)` | **~0.06 ms**（O(1)） |
| 单次扫描 10,200 字符详情 | **~75 ms** |
| 单次扫描 60 字符字段 | **~2 ms** |
| 推算 500 商品 × 3 字段（单进程） | **约 40 s** |
| 推算 5,000 商品 × 3 字段（单进程） | **约 400 s（≈7 分钟）** |

与旧实现（逐词条 `re.compile`，21 万条正则，单次构建 37–70 s，
listing 测试套件全跑 ~39 分钟）相比，listing 套件实测降到 **~28 s**
（`tests/shopee-br-listing-audit/run_tests.py`，406/406 全绿）。

> **不要**在没有实测数据的情况下写「性能足够」或「性能有风险」这类
> 判断 —— 上面每个数字都可复现。

### 7.2 批量扫描的正确用法

`tools/scan_lexicon.py --input` 接受**一个** JSON 文件。
批量场景应当：

- 在**单个进程内**复用同一个 `Scanner` 实例（索引按词库 mtime 缓存，
  重复构造是 O(1)，无需额外「常驻进程」）
- 或直接调用 `shopee-br-listing-audit` 的引擎，它内部已按商品复用扫描器

### 7.3 词库扫描与规则判定是两层

词库扫描**不是**判定 —— 它只提供**信号**：

| 层 | 职责 | 产出 |
|---|---|---|
| 词库层（`tools/scan_lexicon.py`） | 确定性文本筛查 | 命中了哪些组、在哪个字段、什么偏移、什么片段 |
| 规则层（`rules/*.json`） | 按规则条件求值 | `rule_refs`、动作、置信度 |

**两层聚合的字段范围不同** —— 这是误报控制的要点：

| 字段 | 规则层 `any_text` | 词库层扫描器 |
|---|---|---|
| `title` | ✅ | ✅ |
| `description` | ✅ | ✅ |
| `brand` | ✅ | ✅ |
| `category` | ✅ | ✅ |
| `model` | ✅ | ❌ |
| 图片 `ocr_text` | ✅ | ❌ |
| `attributes.*` | ❌ | ✅ |

规则层覆盖 `model` 与图片 OCR，**不**覆盖 `attributes`；词库层相反 ——
覆盖 `attributes`，**不**覆盖 `model` 与图片 OCR。

**这意味着**：词库扫不到的 `model` / 图片文字，规则层能扫到；反过来，
写在 `attributes` 里的敏感词，规则层扫不到，**只有词库层能报**。
排查「为什么某条敏感词没被判违规」时，先确认它落在哪个字段。

> 同一段文字，两层看到的字段不一样是**正常现象**，不是 bug ——
> 两层各有盲区。可运行的验证示例见
> `skills/shopee-br-listing-audit/references/false_positive_control.md` §2。
