# 词库扫描规范

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-LA-005` |
| 所属模块 | `shopee-br-listing-audit` |
| 版本 | 1.0.0 |
| 状态 | **Draft — 骨架，内容待 TASK-LISTING-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 合并词库的使用方式、匹配算法与误报控制 |
| 相关文档 | `lexicon/term_groups.json`、`contracts/lexicon_rule_map.json`、`docs/SOP_COMPLIANCE_REVIEW.md` §4 |
| 未决事项 | 大规模索引（Aho–Corasick）的具体实现待定 |

---

## 1. 合并词库的构成

| 文件 | 内容 | 规模 |
|---|---|---|
| `lexicon/term_groups.json` | 词组（扫描用） | **37 组 / 856 词** |
| `lexicon/rewrite_map.json` | 触线 → 中性替代（改写用） | 8 类映射 |
| `lexicon/exemptions.json` | 误报豁免规则 | 7 条 |
| `lexicon/quality_patterns.json` | 套模板/批量味检测 | 15 条特征 |
| `lexicon/non_avoidable.json` | 无法文字规避的品类 | 6 类 |
| `lexicon/verb_conjugations.json` | 葡语动词变位匹配表 | 7 个动词 |
| `contracts/lexicon_rule_map.json` | 词组 → 规则映射 | 37 条 |

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

葡语的 `\b` **不可靠** —— 会吞掉相邻单词的首字母：

```python
# ❌ 会把 "Óculos" 变成 "culos"
re.search(r'\bat[óo]xico\b', 'Óculos para visão')

# ✅ 显式 lookaround
re.search(r'(?<![a-zA-Zà-ÿÀ-ß])at[óo]xico(?![a-zA-Zà-ÿÀ-ß])', 'Óculos para visão')
```

**所有葡语词条匹配一律使用显式边界。** 词库中的 `verb_conjugations.json` 已内建此模式。

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

当前 856 词用普通编译正则足够。规模扩大后用 Aho–Corasick 建立多模式索引：

```python
# 逻辑示意
from collections import defaultdict
def build_index(groups):
    goto, fail, out = {}, {}, defaultdict(list)
    for gid, terms in groups.items():
        for t in terms:
            pat = compile_pattern(t)
            insert(goto, fail, out, pat, gid)
    return goto, fail, out
```

> **Aho–Corasick 只是索引加速手段。规则原始数据仍以 JSON 保存**（`PROJECT_RULES.md` 硬性要求）。

---

## 4. 误报控制

### 4.1 豁免规则

`lexicon/exemptions.json` 定义 7 条豁免：

| ID | 场景 | 动作 |
|---|---|---|
| `EX-TOOLS` | 菜刀/剪刀/螺丝刀/美工刀 | `exempt` |
| `EX-CE-FACT` | "产品印有 CE 标志" | `flag_low` |
| `EX-HERMES-CARRIER` | Hermes 作为快递/物流商名 | `require_review` |
| `EX-REDUZIR` | "reduzir a entrada de água" | `exempt` |
| `EX-DESCONFORTO` | "em caso de desconforto, suspenda o uso" | `exempt` |
| `EX-SEGURO-FUNCIONAL` | "fechamento seguro" | `exempt` |
| `EX-BRAND-GENERIC` | 品牌名可能是产品通用词 | `require_review` |

> ⚠️ **豁免 ≠ 放行。** 命中仍要记录，只是降低置信度或转为需复核。

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

`contracts/lexicon_rule_map.json` 定义 37 条映射。

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

## 7. 待 TASK-LISTING-01 确定

- [ ] Aho–Corasick 索引的具体实现
- [ ] 扫描器 CLI 接口
- [ ] 批量扫描的性能基线
- [ ] 词库与规则的联动测试用例
