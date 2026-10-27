| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-LA-002` |
| 所属模块 | ``shopee-br-listing-audit`` |
| 版本 | 0.1.0 |
| 状态 | **Draft — 骨架，内容待 TASK-LISTING-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 各类判定的证据要求与证据链构造 |
| 相关文档 | `contracts/evidence_reference.schema.json`、`contracts/risk_action_matrix.json` |
| 未决事项 | 各规则的 `evidence_required` 具体清单待确定 |

---

## 1. 证据引用的规则

**只存引用，不存内容。** 证据本体（图片、授权书扫描件）留在原处，JSON 里只记路径与元信息。

```json
{
  "evidence_id": "EV-LV-001-01",
  "evidence_type": "listing_field",
  "provided": true,
  "artifact_ref": "products/SKU-001/title",
  "source_locator": "title",
  "collected_at": "2026-10-27T00:00:00Z",
  "notes": "标题命中禁售词"
}
```

硬约束 **H5**：不得把凭证内容内嵌进 `artifact_ref` 或 `notes`。

## 2. 证据类型

| `evidence_type` | 用于 | `artifact_ref` 指向 |
|---|---|---|
| `listing_field` | 文本类命中 | 字段路径，如 `title` / `description` |
| `image` | 图片类命中 | 图片路径或 CDN 引用 |
| `authorization` | 授权材料 | 授权书文件路径 |
| `platform_notice` | 平台通知 | 通知原文路径 |
| `external_registry` | 商标/专利注册查询 | 查询结果记录路径 |
| `case_history` | 历史案件 | 案件 ID 引用 |
| `missing` | **缺失的必需输入** | 空 —— 配合 `not_evaluated` |

## 3. 证据链要求

一条 `block` 结论**必须**同时具备：

1. 命中的 `rule_id`
2. 规则要求的所有证据（`evidence_required`）
3. 逐字可核验的 `source.excerpt`
4. 规则 `status = active` 且 `source.tier ∈ {platform_official, law}`

缺任何一项 → 降级为 `flag` + `requires_human_review = true`。

## 4. `provided` 字段的三态

| 值 | 含义 |
|---|---|
| `true` | 证据存在且已取用 |
| `false` | 证据明确不存在 |
| 字段缺失 | **未知** —— 用 `evidence_type: missing` 表达，不要猜 |

## 5. 待 TASK-LISTING-01 确定

- [ ] 每条规则的 `evidence_required` 具体清单
- [ ] 图片类证据的取用方式（OCR 结果如何关联）
