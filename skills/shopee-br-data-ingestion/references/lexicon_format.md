| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-DI-004` |
| 所属模块 | ``shopee-br-data-ingestion`` |
| 版本 | 0.1.0 |
| 状态 | **Draft — 骨架，内容待 TASK-INGEST-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 词库文件的格式与消费方式 |
| 相关文档 | `data/schema/lexicon.schema.json`、`lexicon/term_groups.json` |
| 未决事项 | 词库格式的最终形态待确认 |

---

## 1. 词库不是规则

| | 词库 | 规则 |
|---|---|---|
| 内容 | 词与词组 | 条件 + 动作 + 来源 + 证据要求 |
| 用途 | **产生信号** | **产生结论** |
| 单独命中 | 只能 `flag_for_review` | 可 `block` |

> 词库命中**本身永远不是违规判定**。它只说明"这里有值得看的东西"。

## 2. 格式

```json
{
  "schema_version": "1.0",
  "name": "shopee-br-risk-lexicon",
  "description": "...",
  "last_verified": "2026-10-27",
  "usage": "screening_only",
  "groups": [
    {
      "group_id": "G-PI-01",
      "label": "禁售类目关键词",
      "risk_hint": "prohibited",
      "terms": ["termo proibido", "outro termo"]
    }
  ]
}
```

| 字段 | 含义 |
|---|---|
| `group_id` | 稳定组标识 |
| `label` | 组名（中文或葡语） |
| `risk_hint` | 风险提示方向，**不是结论** |
| `terms` | 词与词组 |

## 3. 匹配

- 匹配在**规范化后**的文本上进行（见 `false_positive_control.md` §5）
- 词组按**最长优先**匹配
- 一个词可属于多个组 → 产生多条信号
- 命中必须记录**具体位置**（字段 + 偏移），不能只记"命中了"

## 4. 规模

> ⚠️ 词库的历史数据文件已丢失（原 1,320 词 / 36,372 词规模），现存仅 Markdown 文档。
> 规模假设（十万条）**尚未有数据支撑**，需先基准测试再定。

大规模检索可用 Aho–Corasick 等多模式匹配算法建立索引，但**规则原始数据仍以 JSON 保存**。

## 5. 待 TASK-INGEST-01 确定

- [ ] 词库格式的最终确认
- [ ] 重建词库的来源与流程
