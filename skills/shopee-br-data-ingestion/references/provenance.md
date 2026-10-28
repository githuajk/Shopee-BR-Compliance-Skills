| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-DI-003` |
| 所属模块 | ``shopee-br-data-ingestion`` |
| 版本 | 0.1.0 |
| 状态 | **Draft — 骨架，内容待 TASK-INGEST-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 数据溯源：每条记录从哪来 |
| 相关文档 | `contracts/skill_input.schema.json` 的 `provenance` 字段 |
| 未决事项 | 溯源字段的最终形态待确认 |

---

## 1. 为什么必须溯源

审核结论要能被复核，就必须能回答：**这条商品数据是从哪个文件的哪一行来的？**

## 2. 溯源内容

| 字段 | 含义 |
|---|---|
| 源文件路径 | 绝对路径 |
| 源格式 | xlsx / csv / json / pdf / image / ... |
| 工作表或分片 | xlsx 的 sheet 名；JSONL 的分片 |
| 原始位置 | 行号 / 单元格范围 / 字符区间 |
| 解析时间 | ISO 8601 |
| 解析器版本 | 解析代码的版本标识 |
| 店铺 | `shop_id` |
| 解析统计 | 该文件解析出的记录数、跳过数、错误数 |

## 3. 溯源的传递

`provenance` 沿流水线**逐层传递**：

```
ingestion 的 provenance
  → SkillInput.provenance
  → AuditResult.provenance
  → 报告中的来源说明
```

> 主 Skill 在整合时**原样保留**各模块的 `provenance`，不得覆盖。

## 4. 报告中的呈现

每条发现要能点回原始来源：

```
发现：标题命中禁售词
  → 规则：SBR-PI-001
  → 商品：SKU-001
  → 来源：data/samples/demo_mass_update.xlsx
        sheet=mass_update  行=8  列=商品名称
```

## 5. 待 TASK-INGEST-01 确定

- [ ] 溯源字段的最终结构
- [ ] 报告中的呈现细节
