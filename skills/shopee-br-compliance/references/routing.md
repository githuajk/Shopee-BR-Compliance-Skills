| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-CO-001` |
| 所属模块 | ``shopee-br-compliance`` |
| 版本 | 0.1.0 |
| 状态 | **Draft — 骨架，内容待 TASK-MAIN-01 填充** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 任务分流：输入什么，就执行哪些模块 |
| 相关文档 | `docs/parallel_execution_plan.md`、`skills/*/SKILL.md` |
| 未决事项 | 分流决策的完整形态待确定 |

---

## 1. 分流原则

> **最小充分原则**：只执行本次输入真正需要的模块。

理由：每个模块都会产生结论，多跑一个模块就多一份误判风险与复核工时。

## 2. 决策表

| 输入特征 | 执行模块 |
|---|---|
| 纯文本输入（标题/详情） | `listing-audit` |
| 含图片 | `listing-audit` + `ip-review` |
| 含品牌名 | `ip-review` |
| 含多店铺商品 | `duplicate-detection` |
| 含历史案件/违规记录 | `duplicate-detection` |
| 含店铺处罚状态 | `duplicate-detection` |
| 含品牌授权材料 | `ip-review` + `duplicate-detection` |
| 输入是文件（Excel/CSV/PDF/图片） | 先 `data-ingestion` |
| 任何情况 | 最后 `reporting` |
| 源政策需重新核验 | `policy-research` |

## 3. 合并规则

| 同时命中 | 执行 |
|---|---|
| 多店铺 + 图片 | `listing-audit` + `ip-review` + `duplicate-detection` |
| 文件 + 多店铺 | `data-ingestion` → 三个专业模块 → `reporting` |
| 仅需出报告 | `reporting`（复用已有结果） |

## 4. `policy-research` 的特殊地位

它**不是**每次都跑。它只在以下情况执行：

- 规则引文核验失败
- 规则的 `last_verified` 过期
- 用户要求核查政策原文
- 新增规则需要来源

## 5. 分流结果必须记录

分流决定写入 `provenance.notes`：

```
本次执行模块：data-ingestion → listing-audit → ip-review → duplicate-detection → reporting
未执行：policy-research（规则引文核验通过且未过期）
```

## 6. 待 TASK-MAIN-01 确定

- [ ] 决策表的完整形态
- [ ] 是否支持用户手动指定模块
