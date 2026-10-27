| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-IP-003` |
| 所属模块 | ``shopee-br-ip-review`` |
| 版本 | 0.1.0 |
| 状态 | **Draft — 骨架，内容待 TASK-IP-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 品牌授权材料的核查项与有效性判定 |
| 相关文档 | `data/schema/case.schema.json` 的 `evidence` 字段 |
| 未决事项 | 授权链（上游→下游）的验证要求待补充 |

---

## 1. 核查项

| # | 核查项 | 不满足的后果 |
|---|---|---|
| 1 | 授权书存在 | `require_evidence` |
| 2 | 授权方是**商标权利人**或有权授权方 | `escalate_legal` |
| 3 | 授权覆盖**本商品品牌** | `require_evidence` |
| 4 | 授权覆盖**本商品类目** | `require_evidence` |
| 5 | 授权在**销售期内** | `require_evidence` |
| 6 | 授权覆盖**销售地区**（含巴西） | `require_evidence` |
| 7 | 授权覆盖**销售主体**（店铺） | `require_evidence` |
| 8 | 授权链完整（多级分销时逐级可查） | `escalate_legal` |
| 9 | 授权书真实性可验证 | `escalate_legal` |

## 2. 授权不完整的表达

**不等于侵权。** 它意味着**无法证明有权销售**。

```
授权材料缺失/不完整
  → verdict = signal
  → action = require_evidence
  → requires_human_review = true
  → 不得直接判定侵权
```

## 3. 授权与商标检测的关系

| 情形 | 商标检测 | 授权核查 | 结论 |
|---|---|---|---|
| 品牌词 + 有授权 | 可能命中 | 通过 | `pass` |
| 品牌词 + 无授权 | 可能命中 | 不通过 | `signal` + 复核 |
| 品牌词 + 指示性使用 | 命中 | 不需要 | `pass` |
| 品牌词 + 混淆性使用 | 命中 | — | `signal` + 复核 |

## 4. 证据记录

授权材料按 `contracts/evidence_reference.schema.json`：

```json
{
  "evidence_id": "EV-AU-001",
  "evidence_type": "authorization",
  "provided": true,
  "artifact_ref": "authorizations/SKU-001/authorization.pdf",
  "source_locator": "case.evidence",
  "collected_at": "2026-10-27T00:00:00Z",
  "notes": "授权方与权利人不一致，待核"
}
```

硬约束 **H5**：只存路径，**不内嵌**授权书内容或凭证。

## 5. 待 TASK-IP-01 确定

- [ ] 授权链验证的具体要求
- [ ] 授权书 OCR/人工录入的分工
