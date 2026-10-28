| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-CO-001` |
| 所属模块 | `shopee-br-compliance` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 任务分流：输入什么，就执行哪些模块 |
| 相关文档 | `skills/shopee-br-compliance/src/sbr_compliance/routing.py`、`docs/parallel_execution_plan.md` |
| 未决事项 | 无 |

---

## 1. 分流原则

> **最小充分原则**：只执行本次输入真正需要的模块。

理由：每个模块都会产生结论，多跑一个模块就多一份误判风险与复核工时。

实现位置：`skills/shopee-br-compliance/src/sbr_compliance/routing.py`
的 `decide()`，返回 `RoutingDecision`。

## 2. 阶段与模块的映射

阶段是**固定顺序**的（`registry.STAGE_ORDER`）：

| 阶段 | 模块 | 角色（`ModuleSpec.role`） |
|---|---|---|
| `ingestion` | `shopee-br-data-ingestion` | `ingestion` |
| `content_audit` | `shopee-br-listing-audit` | `content_audit` |
| `ip` | `shopee-br-ip-review` | `ip` |
| `duplicate` | `shopee-br-duplicate-detection` | `duplicate` |
| `reporting` | `shopee-br-reporting` | `reporting` |

**阶段顺序固定** —— 汇总永远在最后，ingestion 永远在最前。

## 3. 自动分流的实际判据

`decide()` 的判据（**全部经代码核对**）：

| 阶段 | 执行条件 | 理由文本（`reasons`） |
|---|---|---|
| `ingestion` | 有 `input_paths`（外部文件） | 「本次输入是外部文件，先经 shopee-br-data-ingestion 规范化」 |
| `content_audit` | `products[]` 非空 | 「本次有商品内容待审，商品内容维度必须评估」 |
| `ip` | `products[]` 非空 | 见 §3.1 |
| `duplicate` | `products[]` 非空 | 见 §3.2 |
| `reporting` | **总是** | 「任何批次都以汇总与报告收尾」 |

### 3.1 IP 维度

**只要有商品就执行** —— 不因为「没检测到品牌词」而跳过。

```python
if _has_brand_signal(products) or _has_images(products):
    reasons[STAGE_IP] = "商品含品牌词或图片，知识产权与授权维度需要评估"
else:
    reasons[STAGE_IP] = "有商品待审，IP 维度需要评估（缺图片/品牌时相关规则记为未评估）"
```

**为什么不做更激进的跳过**：缺图片/品牌时，相关 IP 规则会记入
`unevaluated[]`（硬约束 H3）—— 那正是「未评估」的信息，**必须出现在
结果里**。编排器跳过它，缺口就消失了。

`_has_brand_signal()` 的品牌信号 = `brand` 字段非空，或
标题/详情含以下任一标记（不区分大小写）：

```
nike, adidas, samsung, apple, sony, puma, xiaomi, huawei, ford,
toyota, amazon, réplica, replica, original, importado
```

### 3.2 重复检测维度

**只要有商品就执行** —— 跨店比对是否成立由**模块自己**判断并记缺口。

```python
if len(shops) >= 2:
    reasons[STAGE_DUPLICATE] = f"本次涉及 {len(shops)} 个店铺（…），跨店同款关联必须在同一次请求内比对"
else:
    reasons[STAGE_DUPLICATE] = f"本次只涉及 1 个店铺（…）：同店重复与授权/处罚点仍需评估，跨店比对该维度会记为未评估"
```

单店时模块产出 H3 警告（实测：`ERR-DUP-0001`
「the batch carries fewer than two shops, so no cross-store comparison
was possible …（hard constraint H3）」）。

> 编排器**不**因为单店就跳过重复检测 —— 同店重复刊登与重发仍然要查。

## 4. 显式指定模块

调用方可在 `options.modules` 里指定要跑哪些模块：

```json
{"options": {"modules": ["shopee-br-ip-review"]}}
```

行为：

- 只跑被指定的模块，**按阶段固定顺序**
- 未被指定的阶段记入 `skipped`，理由「调用方未在 options.modules 中指定该模块」
- **未知模块名**记入 `skipped`，键为 `unknown:<name>`，理由：
  「未知模块名 'x'：不是 contracts/audit_result.schema.json 枚举内的模块，
  也不是本模块登记的可驱动模块」
- `RoutingDecision.explicit = True`，`note()` 会额外写明
  「模块集合由调用方显式指定（options.modules）」

**未知模块不抛异常** —— 它被记为跳过并写入 `provenance.notes`，
这样一次手误不会让整个批次失败。

## 5. `policy-research` 的特殊地位

它**不在可驱动链路里** —— `registry.STANDALONE_MODULES` 声明
`shopee-br-policy-research` 为独立模块。

理由：它是**按需**执行的 —— 规则引文核验失败、规则 `last_verified`
过期、用户要求核查政策原文、新增规则需要来源时，才单独跑它。
每次审核都跑一遍没有意义。

## 6. 分流结果必须记录

分流决定写入 `provenance.notes`（`RoutingDecision.note()`）。实测输出：

```
本次执行模块：shopee-br-listing-audit → shopee-br-ip-review →
shopee-br-duplicate-detection → shopee-br-reporting；
未执行：shopee-br-data-ingestion（本次分流未选中该维度）
```

> 注意 `skipped` 里各阶段的**理由不同**：
> 自动分流时未选中的维度记「本次分流未选中该维度」；
> 显式指定时记「调用方未在 options.modules 中指定该模块」；
> 无商品时记「没有可审的商品内容，内容维度未评估」这类**具体**说明。

机器可读版本写入产出目录的 `routing_plan.json`：

```json
{
  "stages": ["content_audit", "ip", "duplicate", "reporting"],
  "modules": ["shopee-br-listing-audit", "shopee-br-ip-review",
              "shopee-br-duplicate-detection", "shopee-br-reporting"],
  "reasons": {"content_audit": "本次有商品内容待审，…"},
  "skipped": {"ingestion": "输入已是规范模型…"},
  "explicit": false
}
```

## 7. 实测基线

```bash
$ env -u LD_LIBRARY_PATH python3 tests/shopee-br-compliance/run_tests.py
```

| 场景 | 分流结果 |
|---|---|
| 39 个违规商品（`tests/fixtures/violation_products.json`） | `content_audit → ip → duplicate → reporting`（ingestion 跳过） |
| 显式 `modules: [shopee-br-ip-review]` | 仅 `ip` |
| 单店商品 | 仍跑 `duplicate`（跨店维度记缺口） |
| 无商品 | 三个专业维度全跳过，只跑 `reporting` |
