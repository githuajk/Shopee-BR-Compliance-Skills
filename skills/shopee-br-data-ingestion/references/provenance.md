| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-DI-003` |
| 所属模块 | `shopee-br-data-ingestion` |
| 版本 | 1.0.0 |
| 状态 | **Active — 已实现** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 溯源字段的含义、哈希约定与版本标识 |
| 相关文档 | `contracts/skill_input.schema.json`（`provenance` 定义）、`skills/shopee-br-data-ingestion/src/sbr_ingestion/pipeline.py` |
| 未决事项 | 无 |

---

## 1. 为什么溯源是强制的

`PROJECT_RULES.md` §5：**没有溯源的输入不得进入审核链路。**

下游模块（listing-audit / ip-review / duplicate-detection）拿到的是商品数组，
看不到原始文件。没有溯源就无法回答「这条结论是基于哪一版文件、什么时候、
用什么解析器读出来的」—— 也就无法复核。

## 2. `provenance.inputs[]` 的 7 个字段

契约（`contracts/skill_input.schema.json`）定义：

| 字段 | 类型 | 含义 |
|---|---|---|
| `path` | string（必填） | 输入路径（原样保留调用方给的形式） |
| `kind` | string | 识别出的格式：`xlsx` `csv` `json` `jsonl` `txt` `md` `docx` `pdf` `image` `unknown` `unsupported` |
| `digest` | string \| null | 内容哈希（SHA-256 十六进制） |
| `parsed_at` | string \| null | 解析完成时间（ISO 8601，UTC） |
| `parser_version` | string \| null | 解析器标识 |
| `records_parsed` | int \| null | 读出的记录数 |
| `records_failed` | int \| null | 失败的记录数 |

**本模块承诺 7 个字段全部存在**（值可为 `null`，但键必须在）。

## 3. digest 的约定

| 项 | 约定 |
|---|---|
| 算法 | **SHA-256** |
| 表示 | 小写十六进制，无前缀 |
| 计算对象 | 文件**原始字节**（不做换行转换、不做编码转换） |
| 时机 | 解析**之前** —— 哈希的是「读到的那个文件」，不是「解析后的结果」 |
| 失败时 | 文件不可读 → `null`（契约允许）；文件不存在 → `null`（没有内容可哈希） |

> **为什么哈希原始字节而不是解析结果？**
> 因为要回答的是「这个文件是不是我审核时看到的那个文件」。
> 哈希解析结果会因为解析器版本变化而变化，无法用来比对来源。

## 4. `records_parsed` / `records_failed` 的含义

| 字段 | 含义 |
|---|---|
| `records_parsed` | 从该文件**读出并成功规范化**的记录数 |
| `records_failed` | 该文件中**未能规范化**的记录数 |

两者相加 = 该文件的记录总数（对于有明确记录边界的格式）。

**注意**：`records_failed > 0` 时，整批的动作会升级为 `flag_for_review`
（`verdict: REVIEW`）—— 丢了一条就是丢了一条，不能因为其余都成功就判通过。

**「读到了 0 条」也是失败**：扫描件 PDF、纯图片这类读不出内容的情形，
`records_parsed == 0` → 同样升级为 `flag_for_review`。

## 5. `parser_version` 的构成

```
sbr-ingestion/<模块版本>
```

写入 `SkillInput.provenance.producer` 与每个 `AuditResult.provenance.producer`。
`AuditResult.rule_version` 用 `sbr-ingestion-rules/<版本>`。

> **为什么要分开 `parser_version` 与 `rule_version`？**
> 本模块**不定义审核规则**，但要标出「用哪个版本的解析器读的」和
> 「按哪个版本的规则集判的」—— 两者独立演进，混在一起会让人无法
> 判断结论变化是解析变了还是规则变了。

## 6. `SkillInput.provenance` 的其余字段

| 字段 | 值 |
|---|---|
| `produced_at` | 产出时间（ISO 8601，UTC） |
| `producer` | `shopee-br-data-ingestion/<版本>` |

## 7. `AuditResult.provenance`

| 字段 | 值 |
|---|---|
| `produced_at` | 产出时间 |
| `producer` | `shopee-br-data-ingestion/<版本>` |
| `source_refs` | 全部输入路径（便于从结论回溯到文件） |
| `notes` | 解析统计摘要（读出多少条、报错多少条） |

## 8. `ModuleHandoff` 里的溯源

交接记录（`contracts/module_handoff.schema.json`）的 `payload_ref` 指向本模块
产出的 `SkillInput` 路径或内联对象，`produced_at` 记产出时间。

`assumptions` 与 `known_gaps` **必须如实填写** —— 下游需要知道
「哪些字段是推导出来的」「哪些输入没读成功」。

## 9. 硬约束 H5

`evidence_refs[].artifact_ref` **只存引用**（路径或外部工单号），
**禁止**内嵌完整凭证或授权文件内容。

测试断言：所有 `artifact_ref` 不含 `sk-` / `ghp_` / `BEGIN ` 等凭证特征。

## 10. 实测基线

```bash
env -u LD_LIBRARY_PATH python3 tests/shopee-br-data-ingestion/run_tests.py
```

溯源相关断言：每个输入都有全部 7 个字段；已读取输入的 digest 非空；
原始输入的字节与 mtime 在解析前后不变。**189 项断言全部通过。**
