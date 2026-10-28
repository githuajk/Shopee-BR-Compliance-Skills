| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-LA-004` |
| 所属模块 | ``shopee-br-listing-audit`` |
| 版本 | 0.1.0 |
| 状态 | **Draft — 骨架，内容待 TASK-LISTING-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 政策时效性管理：规则过期、失效与重新核验 |
| 相关文档 | `references/audit_semantics.md` §3、`contracts/risk_action_matrix.json` |
| 未决事项 | 过期规则的自动降级机制待实现 |

---

## 1. 规则的时效状态

| `status` | 含义 | 是否产出结论 |
|---|---|---|
| `active` | 已核验且在有效期内 | ✅ |
| `stale` | 超过核查有效期 | ⚠️ 只产出 `flag_for_review`，不产出 `block` |
| `unverified` | 引文未核验通过 | ⚠️ 只产出 `flag_for_review` |
| `deprecated` | 已被政策取代 | ❌ 不产出结论 |
| `draft` | 编写中 | ❌ 不产出结论 |

**只有 `active` 才能产生 `block`** —— 硬约束 **H2**。

## 2. 有效期的判定

| 层级 | 有效期 | 依据 |
|---|---|---|
| `platform_official` | 90 天 | `source.last_verified` |
| `law` | 180 天 | `source.last_verified` |
| `internal_risk` | 无 | 内部策略 |

## 3. 政策变更的处理

```
检测到政策变更
  ↓
抓取新版本 → research/raw/<slug>.<date>.txt
  ↓
逐字核验受影响规则的引文
  ↓
更新规则的 source.last_verified / source.excerpt
  ↓
若语义实质变化 → 规则 version +1，status 置 draft
  ↓
重新执行受影响规则的测试
```

> **不覆盖历史抓取件。** 旧引文的可核验性依赖于旧抓取件仍在。

## 4. 已知需要特别留意的政策

| 政策 | 变化 | 影响 |
|---|---|---|
| OTC 药品 | 2026-08-06 起仅限持牌药房/药店销售 | 旧的"药品一律禁售"规则**必须废弃** |
| 封禁 vs 删除 | 删除不可恢复且计处罚点 | 重发结论分级 |

## 5. 待 TASK-LISTING-01 确定

- [ ] `stale` 规则的降级行为的具体实现
- [ ] 政策变更检测的触发方式（人工触发 vs 自动）
