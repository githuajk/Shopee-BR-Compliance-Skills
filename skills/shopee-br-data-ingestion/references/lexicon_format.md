| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-DI-004` |
| 所属模块 | `shopee-br-data-ingestion` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 词库结构、匹配约定与维护节奏 |
| 相关文档 | `docs/SOP_COMPLIANCE_REVIEW.md`、`contracts/lexicon_rule_map.json`、`tools/validate_lexicon.py`、`tools/build_lexicon.py` |
| 未决事项 | 无 |

---

## 1. 词库的定位

> **词库命中是**筛查信号，**不是**违规判定。
> 任何一组词单独都不构成违规 —— 判定要结合语境、类目、来源层级与规则定义。

`lexicon/term_groups.json` 的 `description` 明确写着这一点：

> *Grupos de palavras-chave para triagem rápida. Nenhum grupo é, por si só,
> uma violação: a palavra é um SINAL que precisa de contexto.*

**所有权**：`lexicon/**` 归 `shopee-br-data-ingestion`
（`contracts/file_ownership.json` 是唯一权威来源）。
**消费方**是 `shopee-br-listing-audit` —— 词库提供筛查面，规则提供判定。

## 2. 六个文件

| 文件 | 内容 | 规模 |
|---|---|---|
| `term_groups.json` | 触线词分组（扫描面） | **105 组 / 210,439 词**（2026-10-28 集成扩充后；原 37 组 / 856 词） |
| `exemptions.json` | 误报豁免规则 | 按规则分组 |
| `non_avoidable.json` | 无法规避的品类（只能改写，不能删词） | 按品类分组 |
| `quality_patterns.json` | 详情质量特征（重复句、模板化） | 判据 + 首句唯一性规则 |
| `rewrite_map.json` | 触线词 → 中性表述映射 | 按宣称类型分组 |
| `verb_conjugations.json` | 葡语动词变位表 | 变位规则 + 条目 |

配套：`contracts/lexicon_rule_map.json` —— 词库组 → 规则的映射（105 条映射 / 57 条规则，2026-10-28 集成扩充 + 肉毒/蜂毒补齐后；原 37 条 / 50 条）。

## 3. 分组结构

```json
{
  "schema_version": "1.0",
  "name": "...",
  "description": "...",
  "last_updated": "2026-10-27",
  "usage": "...",
  "matching_notes": [ ... ],
  "groups": {
    "proibido_armas": ["arma de fogo", "revólver", ...],
    "...": []
  },
  "group_meta": { ... },
  "stats": {"group_count": 37, "term_count": 856}
}
```

组名前缀约定：

| 前缀 | 类别 | 典型组 |
|---|---|---|
| `proibido_*` | 禁售 | `proibido_armas` `proibido_tabaco` `proibido_drogas` `proibido_quimicos` `proibido_financas` `proibido_aval` `proibido_government` `proibido_wildlife` |
| `restrito_*` | 受限 | 酒类、保健品、锂电池、汽车配件、生鲜、兽药、仿真枪械、生乳制品 |
| `excesso_*` | 夸大宣称 | 疗效、绝对化用语 |
| `falso_*` | 仿冒特征 | 复刻、假冒、盗版 |
| `qualidade_*` | 详情质量 | 模板化、重复 |
| `externo_*` | 站外引流 | 电话、WhatsApp、站外链接 |
| `outros_*` | 其它 | 杂项 |

`group_meta` 记录每组的类别、严重度基线与说明 —— 严重度**基线**不等于最终判定，
最终动作由规则 + 矩阵决定。

## 4. 匹配约定（`matching_notes`）

| 约定 | 说明 |
|---|---|
| 葡语 `\b` 不可靠 | 用 `(?<![a-zA-Zà-ÿÀ-ß])...(?!...)` 显式边界（`à`/`ç`/`ã` 下 `\b` 会失灵） |
| 词组按最长优先匹配 | 避免「arma de fogo」被「arma」抢先命中 |
| 必须记录具体位置 | 字段 + 偏移，不能只记「命中了」 |
| 重音折叠仅用于匹配 | 输出保留原形 |
| 全字段扫描 | 标题 + 详情 + 属性 + 品牌 —— **标题仅 6% 命中，详情 94%** |

> 最后一条是本项目最重要的一条经验：只看标题会漏掉 94% 的风险。
> 早期实现只扫标题，导致详情里的触线词全部漏过。

## 5. 误报豁免（`exemptions.json`）

豁免规则的作用是**把已知的误报模式固化成规则**，而不是靠人记。

典型来源（`tests/test_plan.md` §5.5 高误报来源）：

| 来源 | 现象 | 处置 |
|---|---|---|
| chongyang1 | 57 处命中中 46 处 `reduzir`、4 处 `desconforto`、1 处 `seguro` 为误报 | 上下文判定 → 豁免表 |
| zjz-02 | 兼容性描述被判侵权 | `SBR-IP-006` 指示性使用豁免 |
| 店主 491 商品审阅 | 详情完全相同（模板化） | `quality_patterns` 独立规则 |

**豁免必须写成可判定的条件**（「在 `desconforto` 附近 40 字符内无医疗宣称词」），
不能写成「看起来像误报就放过」。

## 6. 无法规避的品类（`non_avoidable.json`）

有些品类**必然**包含触线词（如医用敷料必然含「medicamento」）。
这类不能靠删词解决，只能改写表述 —— 表里记录了每个品类的
「不能动的词」与「改写方向」。

处理流程见该文件的 `workflow` 字段。

## 7. 改写映射（`rewrite_map.json`）

触线词 → 中性表述。按宣称类型分组：

`absolute_promise` `beauty_claim` `health_claim` `medical_implication`
`platform_guarantee` `safety_promise` `body_shaping`

每条映射给出**触线词**与**可用的中性替代**。

> 映射只提供**候选**表述 —— 最终文案必须由人工/规则按语境确定，
> 不能机械套用（否则又制造新的模板化问题）。

## 8. 变位表（`verb_conjugations.json`）

葡语动词的变位形式。用于「词库里存了原形，文本里是变位」的匹配。

- `entries` —— 变位条目
- `case_insensitive_prefix_rule` —— 大小写不敏感的前缀匹配规则
- `accent_folding` —— 变音符号折叠规则

## 9. 维护节奏

| 时机 | 动作 |
|---|---|
| 规则库变更 | 检查 `contracts/lexicon_rule_map.json` 是否需同步 |
| 误报被上报 | 先写进 `exemptions.json`，**再**改代码 |
| 新增品类 | 加词进 `term_groups.json` + 补 `group_meta` + 更新 `stats` |
| 季度复核 | 核对 `stats` 与实际词数、检查失效豁免 |

**每次改完必须跑**：

```bash
env -u LD_LIBRARY_PATH python3 tools/validate_lexicon.py
```

当前基线：**`tools/validate_lexicon.py` 897 项断言全部通过**（105 组 / 210,439 词 / 105 条映射 / 57 条规则，2026-10-28 实测；原基线 266 项 / 37 组 / 856 词已随词库扩充过期）。

## 10. 与规则库的关系

```
lexicon/term_groups.json  ──┐
                            ├──> contracts/lexicon_rule_map.json ──> rules/*.json
rules/*.json ───────────────┘
```

词库提供**筛查面**（哪些词值得看），规则提供**判定**（命中后是什么结论）。
两者的连接由 `lexicon_rule_map.json` 定义 —— 词库新增组时，
必须同时更新映射，否则该组不会进入任何规则的判定。
