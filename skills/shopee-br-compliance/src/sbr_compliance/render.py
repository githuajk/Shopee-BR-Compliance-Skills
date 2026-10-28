"""人读报告渲染 —— 六节固定结构 + 硬约束自检。

第 2 节（数据缺口与未评估项）必须**存在且独立** —— 「未评估」绝不能混进
「通过」（硬约束 H3）。

本模块**不产生新的结论**，只把 `AuditSummary` 渲染成 Markdown。
"""

from __future__ import annotations

#: 动作 → 中文标签（与 `contracts/risk_action_matrix.json` 的 7 个动作一一对应）
ACTION_LABELS = {
    "allow": "通过",
    "flag_for_review": "提示人工复核",
    "require_evidence": "需补齐证据",
    "revise": "需修改后复审",
    "block": "不得上架",
    "freeze_relist": "冻结重发",
    "escalate_legal": "转交法务/PI",
}

#: 需人工执行的动作（硬约束 H6）
HUMAN_ONLY_ACTIONS = ("freeze_relist", "escalate_legal")

#: verdict → 中文标签
VERDICT_LABELS = {
    "PASS": "通过",
    "REVISE": "需修改",
    "REVIEW": "待复核",
    "BLOCK": "阻断",
}

#: 来源层级 → 中文标签
TIER_LABELS = {
    "platform_official": "平台规则",
    "law": "法律规定",
    "internal_risk": "内部风控建议",
    "unverified": "待核实",
    "ai_inference": "AI 推断",
    "technical": "技术调研结论",
}


def _action_label(action) -> str:
    label = ACTION_LABELS.get(str(action), str(action))
    if str(action) in HUMAN_ONLY_ACTIONS:
        label += "（需人工执行）"
    return label


def _tier_label(tier) -> str:
    return TIER_LABELS.get(str(tier), "未知来源")


def _cell(value) -> str:
    """把可能为空的值渲染成「无」。"""
    if value is None:
        return "无"
    if isinstance(value, str):
        text = value.strip()
        return text if text else "无"
    if isinstance(value, (list, tuple, dict)):
        return str(len(value)) if value else "无"
    return str(value)


def render_report(summary: dict, matrix=None, products=None) -> str:
    """渲染 Markdown 报告。"""
    lines: list[str] = []
    request_id = summary.get("request_id")
    counts = summary.get("verdict_counts") or {}

    lines.append("# Shopee BR 合规审核报告（主 Skill 编排）")
    lines.append("")
    lines.append(f"- 请求 ID：`{request_id}`")
    lines.append(f"- 产出时间：{summary.get('produced_at')}")
    lines.append(f"- 契约版本：{summary.get('contract_version')}")
    lines.append(f"- 整合模块：{summary.get('producer')}")
    lines.append("")

    # --- 1. 摘要 ---
    lines.append("## 1. 摘要")
    lines.append("")
    lines.append(f"- 商品数：{summary.get('target_count', 0)}")
    lines.append(f"- 上游结果条数：{summary.get('input_result_count', 0)}"
                 f"（来自 {len(summary.get('source_modules') or [])} 个模块）")
    lines.append(f"- 整批结论：**{summary.get('batch_verdict')}**"
                 f"（动作 `{summary.get('batch_action')}`，"
                 f"风险等级 `{summary.get('batch_risk_level')}`）")
    distribution = "，".join(
        f"{v}={counts.get(v, 0)}" for v in ("PASS", "REVISE", "REVIEW", "BLOCK")
    )
    lines.append(f"- 结论分布：{distribution}")
    lines.append(f"- 需人工复核：{summary.get('needs_human_review_count', 0)}")
    lines.append(f"- 确定性结论：{summary.get('deterministic_count', 0)}"
                 f"（其中 human_only {summary.get('human_only_count', 0)}）")
    lines.append(f"- 未评估项：{summary.get('unevaluated_count', 0)}"
                 f"（涉及 {summary.get('unevaluated_target_count', 0)} 个目标）")
    lines.append(f"- 待补齐证据：{summary.get('missing_evidence_count', 0)}")
    lines.append(f"- 错误记录：{summary.get('error_count', 0)}")
    lines.append("")

    executed = summary.get("executed_modules") or []
    not_executed = summary.get("not_executed_modules") or []
    lines.append("### 1.1 本次执行的维度")
    lines.append("")
    if executed:
        for name in executed:
            lines.append(f"- ✅ `{name}`")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("### 1.2 本次**未执行**的维度（不得读作「已检查且通过」）")
    lines.append("")
    if not_executed:
        for item in not_executed:
            lines.append(f"- ❌ `{item.get('module')}` —— {item.get('reason')}")
    else:
        routing = summary.get("routing") or {}
        skipped = routing.get("skipped") or {}
        if skipped:
            for stage, reason in skipped.items():
                lines.append(f"- ➖ {stage} —— {reason}")
        else:
            lines.append("- 无")
    lines.append("")

    # --- 2. 数据缺口与未评估项 ---
    lines.append("## 2. 数据缺口与未评估项")
    lines.append("")
    unevaluated = summary.get("unevaluated") or []
    if unevaluated:
        lines.append("以下规则**未评估**（缺输入）—— **不等于通过**：")
        lines.append("")
        lines.append("| 目标 | 规则 | 原因 | 缺失字段 | 负责模块 |")
        lines.append("|---|---|---|---|---|")
        for item in unevaluated[:80]:
            missing = ", ".join(item.get("missing_fields") or []) or "—"
            lines.append(
                f"| {_cell(item.get('target_ref'))} "
                f"| `{_cell(item.get('rule_id'))}` "
                f"| {_cell(item.get('reason'))} "
                f"| {missing} "
                f"| {_cell(item.get('module'))} |")
        if len(unevaluated) > 80:
            lines.append(f"| … | | 另有 {len(unevaluated) - 80} 条见 "
                         f"`audit_summary.json` | | |")
    else:
        lines.append("- 无未评估项。")
    lines.append("")

    missing_evidence = summary.get("missing_evidence") or []
    if missing_evidence:
        lines.append("### 2.1 待补齐的证据")
        lines.append("")
        lines.append("| 目标 | 证据类型 | 引用 | 负责模块 |")
        lines.append("|---|---|---|---|")
        for item in missing_evidence[:60]:
            lines.append(
                f"| {_cell(item.get('target_ref'))} "
                f"| `{_cell(item.get('evidence_type'))}` "
                f"| `{_cell(item.get('artifact_ref'))}` "
                f"| {_cell(item.get('module'))} |")
        lines.append("")

    conflicts = summary.get("conflicts") or []
    if conflicts:
        lines.append("### 2.2 跨模块来源冲突（原文记录，未擅自取舍）")
        lines.append("")
        for item in conflicts:
            lines.append(f"- {item}")
        lines.append("")

    # --- 3. 需决策的发现 ---
    lines.append("## 3. 需决策的发现")
    lines.append("")
    decisions = [r for r in (summary.get("per_target") or [])
                 if r.get("action") in ("block", "freeze_relist",
                                        "escalate_legal", "revise")]
    if decisions:
        for item in decisions:
            lines.append(f"### {_cell(item.get('target_ref'))} —— "
                         f"{_action_label(item.get('action'))}")
            lines.append("")
            lines.append(f"- 结论：`{item.get('verdict')}`"
                         f"　风险等级：`{item.get('risk_level')}`"
                         f"　置信度：`{item.get('confidence')}`")
            lines.append(f"- 理由：{_cell(item.get('reason'))}")
            rules = item.get("rule_refs") or []
            if rules:
                lines.append("- 命中规则：")
                for ref in rules:
                    tier = _tier_label(ref.get("source_tier"))
                    url = ref.get("source_url")
                    excerpt = ref.get("matched_excerpt")
                    line = (f"  - `{_cell(ref.get('rule_id'))}` "
                            f"{_cell(ref.get('title'))} —— 来源：{tier}")
                    if url:
                        line += f"，链接：{url}"
                    lines.append(line)
                    if excerpt:
                        lines.append(f"    - 命中片段：{excerpt}")
            rationale = item.get("review_rationale")
            if rationale:
                lines.append(f"- 需人工判断：{rationale}")
            lines.append("")
    else:
        lines.append("- 无。")
        lines.append("")

    # --- 4. 待复核的发现 ---
    lines.append("## 4. 待复核的发现")
    lines.append("")
    reviews = [r for r in (summary.get("per_target") or [])
               if r.get("action") in ("flag_for_review", "require_evidence")]
    if reviews:
        lines.append("| 目标 | 结论 | 风险等级 | 动作 | 置信度 | 命中规则 |")
        lines.append("|---|---|---|---|---|---|")
        for item in reviews:
            rule_ids = ", ".join(f"`{r.get('rule_id')}`"
                                 for r in (item.get("rule_refs") or [])
                                 if r.get("rule_id")) or "无"
            lines.append(
                f"| {_cell(item.get('target_ref'))} "
                f"| `{_cell(item.get('verdict'))}` "
                f"| `{_cell(item.get('risk_level'))}` "
                f"| {_action_label(item.get('action'))} "
                f"| `{_cell(item.get('confidence'))}` "
                f"| {rule_ids} |")
    else:
        lines.append("- 无。")
    lines.append("")

    # --- 5. 逐商品结果 ---
    lines.append("## 5. 逐商品结果")
    lines.append("")
    products = products or []
    index = {}
    for product in products:
        pid = product.get("product_id")
        if pid:
            index[str(pid)] = product
    per_target = summary.get("per_target") or []
    if per_target:
        lines.append("| 商品 | SKU | 店铺 | 结论 | 动作 | 命中规则 | 未评估 |")
        lines.append("|---|---|---|---|---|---|---|")
        for item in per_target:
            target = str(item.get("target_ref") or "")
            product = index.get(target, {})
            rule_ids = ", ".join(f"`{r.get('rule_id')}`"
                                 for r in (item.get("rule_refs") or [])
                                 if r.get("rule_id")) or "无"
            lines.append(
                f"| {_cell(target)} "
                f"| {_cell(product.get('internal_sku'))} "
                f"| {_cell(product.get('shop_id'))} "
                f"| `{_cell(item.get('verdict'))}` "
                f"| {_action_label(item.get('action'))} "
                f"| {rule_ids} "
                f"| {len(item.get('unevaluated') or [])} |")
    else:
        lines.append("- 无。")
    lines.append("")

    # --- 6. 已查阅规则 ---
    lines.append("## 6. 已查阅规则")
    lines.append("")
    by_rule = summary.get("by_rule") or []
    if by_rule:
        lines.append("| 规则 | 标题 | 来源层级 | 命中模块 | 命中目标数 |")
        lines.append("|---|---|---|---|---|")
        for item in by_rule:
            lines.append(
                f"| `{_cell(item.get('rule_id'))}` "
                f"| {_cell(item.get('title'))} "
                f"| {_tier_label(item.get('source_tier'))} "
                f"| {', '.join(item.get('modules') or []) or '—'} "
                f"| {len(item.get('targets') or [])} |")
    else:
        lines.append("- 无。")
    lines.append("")

    # --- 硬约束 ---
    lines.append("## 硬约束自检")
    lines.append("")
    lines.append("| ID | 内容 | 本次执行 |")
    lines.append("|---|---|---|")
    lines.append(
        "| H1 | IP 类结论恒为 `confidence=signal` + 强制人工复核 | "
        "整合时置信度取**最弱**；IP 模块的结论不会被合并成 `confirmed` |")
    lines.append(
        "| H2 | 阻断类动作只来自 `platform_official`/`law` 的 `active` 规则 | "
        "清洗阶段按 `contracts/risk_action_matrix.json` 校验来源层级，"
        "不合规者降为 `flag_for_review` 并记 `error` |")
    lines.append(
        "| H3 | 输入缺失 → 记 `unevaluated[]`，不得判通过 | "
        "未评估项取并集并独立成节；含未评估项的目标 verdict 不得为 `PASS` |")
    lines.append(
        "| H4 | 引文逐字来自 `research/raw/` | "
        "本模块不新增引文；规则来源与核查日期原样透传 |")
    lines.append(
        "| H5 | 证据只存引用，不内嵌凭证内容 | "
        "`evidence_refs[].artifact_ref` 原样透传，本模块从不读取被引用文件 |")
    lines.append(
        "| H6 | `freeze_relist`/`escalate_legal` 为 `human_only` | "
        "本模块不提供任何执行入口；报告中标注「需人工执行」 |")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 `shopee-br-compliance` 主 Skill 编排生成。"
                 "所有结论均来自各专业模块；主 Skill 不产生新的合规判定，"
                 "也未执行任何平台动作。*")
    lines.append("")
    return "\n".join(lines)
