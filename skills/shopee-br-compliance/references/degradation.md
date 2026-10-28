| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-CO-004` |
| 所属模块 | ``shopee-br-compliance`` |
| 版本 | 0.1.0 |
| 状态 | **Draft — 骨架，内容待 TASK-MAIN-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 模块不可用时的降级行为 |
| 相关文档 | `contracts/module_handoff.schema.json` |
| 未决事项 | 降级的具体输出形态待确定 |

---

## 1. 核心原则

> **宁可如实报告"未执行"，不可假装"通过"。**

模块不可用时，**绝不能**把它的职责当成"没问题"。

## 2. 降级情形

| 情形 | 行为 |
|---|---|
| 模块 SKILL.md 不可读 | 标记该模块未执行，产出 error |
| 模块产出未通过 Schema 校验 | 该模块结果作废，标记未执行 + error |
| 模块依赖的工具缺失 | 标记未执行，列出缺失工具 |
| 模块产出为空但无 error | 视为异常，标记未执行 |
| 规则引文核验失败 | 规则改 `unverified`，只产出 `flag_for_review` |
| 输入数据缺失 | 不产生 result + 记入 `unevaluated[]`，**不是**降级为通过 |

## 3. 输出形态

```json
{
  "errors": [
    {
      "code": "MODULE_UNAVAILABLE",
      "module": "shopee-br-ip-review",
      "message": "模块产出未通过 audit_result Schema 校验",
      "detail": "..."
    }
  ],
  "unevaluated": [
    {
      "product_id": "SKU-001",
      "rule_id": "SBR-IP-001",
      "missing_fields": ["brand"],
      "reason": "模块 shopee-br-ip-review 未执行"
    }
  ]
}
```

## 4. 报告中的呈现

降级**必须**在报告第 2 节（数据缺口）体现：

```markdown
## 2. 数据缺口与未评估项
- SKU-001：SBR-IP-001 未评估 —— 模块 shopee-br-ip-review 未执行（产出校验失败）
- SKU-002：缺少 brand 字段，未评估 SBR-IP-001
```

**不得**在摘要里把这些商品算作"通过"。

## 5. 摘要中的计数

```
总计 15 个商品
  通过 9    待复核 4    需决策 2
  未评估 3  ← 单独列出，不计入通过
```

## 6. 待 TASK-MAIN-01 确定

- [ ] 错误码的完整清单
- [ ] 降级是否允许部分执行
