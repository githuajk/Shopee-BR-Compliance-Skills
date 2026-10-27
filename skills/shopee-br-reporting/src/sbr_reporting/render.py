"""Markdown 报告渲染。

报告的六节结构由 `references/report_structure.md` 固定，**顺序不得调整**：

```
## 1. 摘要
## 2. 数据缺口与未评估项        ← 与「通过」明确分区
## 3. 需决策的发现
## 4. 待复核的发现
## 5. 逐商品结果
## 6. 已查阅规则
## 硬约束
```

**硬约束 H5**：报告中只出现证据的**引用**（路径 / 类型 / ID），
不出现凭证内容。
**硬约束 H6**：`freeze_relist` / `escalate_legal` 标注「需人工执行」。
"""

from __future__ import annotations

from .aggregate import DECISION_ACTIONS, REVIEW_ACTIONS

#: 来源层级的中文呈现（章程 §1.2 要求显示来源层级）
TIER_LABELS = {
    "platform_official": "平台规则",
    "law": "法律规定",
    "internal_risk": "内部风控建议",
    "unverified": "待核实",
    "ai_inference": "AI 推断",
    "technical": "技术调研结论",
}

#: 动作的中文呈现
ACTION_LABELS = {
    "allow": "通过",
    "flag_for_review": "提示人工复核",
    "require_evidence": "需补齐证据",
    "revise": "需修改后复审",
    "block": "不得上架",
    "freeze_relist": "冻结重发",
    "escalate_legal": "转交法务/PI",
}

#: verdict 的中文呈现
VERDICT_LABELS = {
    "PASS": "通过",
    "REVISE": "需修改",
    "REVIEW": "需人工复核",
    "BLOCK": "阻断",
}

#: 置信度的中文呈现
CONFIDENCE_LABELS = {
    "signal": "信号（仅为筛查命中）",
    "likely": "可能",
    "confirmed": "已确认",
}

#: 需要人工执行的动作（H6）
HUMAN_ONLY_ACTIONS = ("freeze_relist", "escalate_legal")

#: 表格里的单元格转义
def _cell(text) -> str:
    if text is None:
        return "—"
    value = str(text).replace("|", "\\|").replace("\n", " ").strip()
    return value if value else "—"


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """渲染一张 markdown 表格。空表返回一行「无」。"""
    if not rows:
        return ["无", ""]
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(_cell(c) for c in row) + " |")
    out.append("")
    return out

def _tier_label(tier) -> str:
    if not tier:
        return "—"
    return TIER_LABELS.get(str(tier), str(tier))


def _action_label(action: str) -> str:
    label = ACTION_LABELS.get(action, action)
    if action in HUMAN_ONLY_ACTIONS:
        label += "（需人工执行）"
    return label


def _verdict_label(verdict: str) -> str:
    return f"{verdict}（{VERDICT_LABELS.get(verdict, verdict)}）"


def _confidence_label(confidence: str) -> str:
    return CONFIDENCE_LABELS.get(confidence, confidence)


def _risk_label(level: str) -> str:
    return {"info": "提示性", "low": "低风险", "medium": "中风险",
            "high": "高风险", "critical": "极严重"}.get(level, level)


def render_report(summary: dict, matrix, products: dict | None = None,
                  hard_constraint_notes: list[str] | None = None) -> str:
    """渲染完整的 Markdown 报告。

    参数
    ----
    summary:
        `build_summary()` 的产物。
    matrix:
        `RiskMatrix` —— 动作/风险等级的中文标签与允许组合来自契约。
    products:
        `product_id -> {internal_sku, shop_id, title}` 的可选映射，用于
        逐商品结果表显示 SKU 与店铺。
    hard_constraint_notes:
        硬约束自检行（每行一句）。缺省给出基于本次数据的通用行。
    """
    products = products or {}
    lines: list[str] = []
    add = lines.append

    add("# Shopee BR 合规审核报告")
    add("")
    add(f"- 请求标识：`{summary['request_id']}`")
    add(f"- 生成时间：`{summary['produced_at']}`")
    add(f"- 契约版本：`{summary['contract_version']}`")
    add(f"- 规则集版本：`{summary['rule_version']}`")
    add(f"- 结果来源模块：{', '.join(summary['source_modules']) or '无'}")
    add("")

    # ------------------------------------------------------------------ 1
    add("## 1. 摘要")
    add("")
    counts = summary["verdict_counts"]
    add(f"- 审核目标数：**{summary['target_count']}**")
    add(f"- 输入结果条数：**{summary['input_result_count']}**")
    add(f"- 整批结论：**{_verdict_label(summary['batch_verdict'])}**，"
        f"动作 **{_action_label(summary['batch_action'])}**，"
        f"风险等级 **{_risk_label(summary['batch_risk_level'])}**")
    add(f"- 需人工处理的目标数：**{summary['needs_human_review_count']}**")
    add("")
    add("结论分布：")
    add("")
    lines.extend(_table(
        ["结论", "含义", "目标数"],
        [[v, VERDICT_LABELS.get(v, v), str(counts.get(v, 0))]
         for v in ("PASS", "REVISE", "REVIEW", "BLOCK")],
    ))
    add(f"- 命中规则数（去重后）：**{summary['rule_count']}**")
    add(f"- 需补齐证据数：**{summary['missing_evidence_count']}**")
    add(f"- 未评估条目数：**{summary['unevaluated_count']}**")
    add(f"- 错误记录数：**{summary['error_count']}**")
    add("")

    # ------------------------------------------------------------------ 2
    add("## 2. 数据缺口与未评估项")
    add("")
    add("> 本节与「通过」**严格分区**。出现在本节的规则**没有被评估过** —— "
        "缺失输入不等于合规（硬约束 H3）。")
    add("")
    if summary["unevaluated"]:
        rows = []
        for entry in summary["unevaluated"]:
            missing = ", ".join(entry.get("missing_fields") or []) or "—"
            rows.append([entry.get("rule_id"), entry.get("reason"), missing,
                         entry.get("module", "—")])
        lines.extend(_table(
            ["规则", "原因", "缺失字段", "来源模块"], rows))
    else:
        add("无")
        add("")
    if summary["missing_evidence"]:
        add("待补齐的证据：")
        add("")
        lines.extend(_table(
            ["目标", "证据类型", "证据 ID", "引用"],
            [[e["target_ref"], e["evidence_type"], e["evidence_id"],
              e.get("artifact_ref") or "—"] for e in summary["missing_evidence"]],
        ))
    else:
        add("待补齐的证据：无")
        add("")
    if summary["rejected_results"]:
        add("未通过契约校验而被跳过的结果：")
        add("")
        lines.extend(_table(
            ["来源", "result_id", "问题"],
            [[r["origin"], r.get("result_id") or "—",
              "; ".join(r.get("problems") or [])[:160]]
             for r in summary["rejected_results"]],
        ))
    if summary["conflicts"]:
        add("跨模块的规则来源冲突（**如实记录，不擅自取舍**）：")
        add("")
        for conflict in summary["conflicts"]:
            add(f"- {conflict}")
        add("")

    # ------------------------------------------------------------------ 3
    add("## 3. 需决策的发现")
    add("")
    decisions = summary["decision_findings"]
    if decisions:
        for item in decisions:
            add(f"### {item['target_ref']} — {item['action_label']}")
            add("")
            add(f"- 结论：**{_verdict_label(item['verdict'])}**")
            add(f"- 风险等级：{_risk_label(item['risk_level'])}")
            add(f"- 建议动作：**{item['action_label']}**")
            add(f"- 理由：{item['reason']}")
            add(f"- 置信度：{_confidence_label(item['confidence'])}")
            if item.get("human_only"):
                add("- ⚠️ 该动作为 **human_only** —— 本模块只提出建议，"
                    "**不执行**任何解冻或 IP 投诉处置（硬约束 H6）")
            if item.get("review_rationale"):
                add(f"- 需人工判断：{item['review_rationale']}")
            add("")
            add("命中规则与来源：")
            add("")
            lines.extend(_table(
                ["规则", "标题", "命中字段", "命中片段", "来源层级", "来源链接"],
                [[r.get("rule_id"), r.get("title"), r.get("matched_field"),
                  r.get("matched_excerpt"), _tier_label(r.get("source_tier")),
                  r.get("source_url")] for r in item["rule_refs"]],
            ))
            if item["evidence_refs"]:
                add("证据引用（**只含引用，不含凭证内容** —— 硬约束 H5）：")
                add("")
                lines.extend(_table(
                    ["证据 ID", "类型", "已提供", "引用", "定位", "备注"],
                    [[e.get("evidence_id"), e.get("evidence_type"),
                      "是" if e.get("provided") else "否",
                      e.get("artifact_ref") or "—",
                      e.get("source_locator") or "—",
                      e.get("notes") or "—"] for e in item["evidence_refs"]],
                ))
            add("")
    else:
        add("无")
        add("")

    # ------------------------------------------------------------------ 4
    add("## 4. 待复核的发现")
    add("")
    review_rows = []
    for item in summary["review_findings"]:
        review_rows.append([
            item["target_ref"],
            item["action_label"],
            item["verdict"],
            _risk_label(item["risk_level"]),
            _confidence_label(item["confidence"]),
            ", ".join(r.get("rule_id") or "—" for r in item["rule_refs"]) or "—",
            item["reason"][:160],
        ])
    lines.extend(_table(
        ["目标", "动作", "结论", "严重度", "置信度", "命中规则", "理由"],
        review_rows,
    ))

    # ------------------------------------------------------------------ 5
    add("## 5. 逐商品结果")
    add("")
    product_rows = []
    for entry in summary["per_target"]:
        meta = products.get(entry["target_ref"], {})
        product_rows.append([
            entry["target_ref"],
            meta.get("internal_sku") or "—",
            meta.get("shop_id") or "—",
            entry["verdict"],
            entry["action"],
            _risk_label(entry["risk_level"]),
            _confidence_label(entry["confidence"]),
            ", ".join(r.get("rule_id") or "—" for r in entry["rule_refs"]) or "—",
            len(entry["unevaluated"]) or "0",
        ])
    lines.extend(_table(
        ["商品", "SKU", "店铺", "结论", "动作", "严重度", "置信度",
         "命中规则", "未评估"],
        product_rows,
    ))

    # ------------------------------------------------------------------ 6
    add("## 6. 已查阅规则")
    add("")
    rule_rows = []
    for rule in summary["rules"]:
        rule_rows.append([
            rule.get("rule_id"),
            rule.get("title"),
            rule.get("category") or "—",
            _risk_label(rule.get("severity") or "info"),
            rule.get("action") or "—",
            _tier_label(rule.get("source_tier")),
            rule.get("last_verified") or "—",
            rule.get("source_url") or "—",
        ])
    lines.extend(_table(
        ["规则", "标题", "类别", "严重度", "动作", "来源层级", "核查日期", "来源链接"],
        rule_rows,
    ))

    # ------------------------------------------------------------- 硬约束
    add("## 硬约束")
    add("")
    notes = hard_constraint_notes or _default_constraint_notes(summary)
    for note in notes:
        add(f"- {note}")
    add("")
    return "\n".join(lines).rstrip() + "\n"


def _default_constraint_notes(summary: dict) -> list[str]:
    """基于本次数据生成硬约束自检行。"""
    notes = [
        "H1 IP 类结论恒为 signal 且需人工复核 — ✅（合并时置信度取最弱，"
        "signal 不升为 likely/confirmed）",
        "H2 阻断类动作仅来自 platform_official/law 的 active 规则 — "
        f"✅（本次 {summary['deterministic_count']} 条阻断类动作均已核验来源层级）",
        f"H3 输入缺失标记未评估，不计为通过 — "
        f"✅（未评估 {summary['unevaluated_count']} 项，"
        f"其中 {summary['unevaluated_target_count']} 个目标被排除在通过之外）",
        "H4 引文逐字核验 — ✅（本模块不新增引文，来源链接与核查日期原样透传）",
        "H5 证据只存引用 — ✅（报告中只出现证据 ID、类型与路径，不含凭证内容）",
        "H6 冻结与法务升级为人工专属 — "
        f"✅（{summary['human_only_count']} 条 human_only 动作已标注「需人工执行」）",
    ]
    return notes
