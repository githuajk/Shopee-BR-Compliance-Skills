"""503 等抓取失败的来源正式处置（disposition）管理。

SBRCA 已登记 `br_anvisa_medicamentos_prescricao`（RDC 44/2009）抓取失败
HTTP 503，该来源不得支撑任何规则（H4 引文不可核验 + `tools/check_sources.py`
已识别放行）。本模块把这一处置形式化：每条抓取失败的来源都应有结构化的
`disposition` 字段，写明状态、原因、依赖规则再锚定方式与重抓方案；
`engine.py` 在输出 `AuditResult[]` 与 `module_handoff.known_gaps` 时会
把它作为已知缺口正式披露。
"""

from __future__ import annotations

#: 处置必填字段（`disposition.*` 必须完整）
REQUIRED_FIELDS = ("disposition_id", "status", "reason", "remediation")

#: 允许的处置状态
VALID_STATUSES = {"quarantined", "cleared"}


def dispositions_for(sources: list[dict]) -> dict[str, dict]:
    """返回 {slug: disposition} —— 仅含抓取失败且带处置条目的来源。"""
    out: dict[str, dict] = {}
    for s in sources:
        d = s.get("disposition")
        if not d or not isinstance(d, dict):
            continue
        if not str(s.get("capture_status", "")).startswith("failed"):
            continue
        out[s["slug"]] = d
    return out


def validate_dispositions(sources: list[dict]) -> list[str]:
    """校验所有抓取失败的来源是否都有结构合理的 disposition，返回问题列表。"""
    issues: list[str] = []
    for s in sources:
        slug = s.get("slug", "?")
        if not str(s.get("capture_status", "")).startswith("failed"):
            continue
        d = s.get("disposition")
        if not d or not isinstance(d, dict):
            issues.append(
                f"{slug}: 抓取失败但未登记 disposition —— 该缺口不得留空")
            continue
        missing = [f for f in REQUIRED_FIELDS if f not in d]
        if missing:
            issues.append(
                f"{slug}.disposition: 缺少必填字段 {missing}")
            continue
        if d.get("status") not in VALID_STATUSES:
            issues.append(
                f"{slug}.disposition.status={d.get('status')!r} 不合法")
        if d.get("status") == "cleared" and not d.get("blocked_for_rules", True):
            # cleared 来源若 still blocked 为 True → 语义矛盾
            issues.append(
                f"{slug}.disposition.cleared 与 blocked_for_rules=True 语义冲突")
    return issues


def quarantined_slugs(sources: list[dict]) -> set[str]:
    """当前处于 quarantined 状态的失败来源集合（即 503 缺口）。"""
    disps = dispositions_for(sources)
    return {slug for slug, d in disps.items() if d.get("status") == "quarantined"}


def gap_notes(sources: list[dict]) -> list[str]:
    """生成 `module_handoff.known_gaps` 可用的文字条目。"""
    notes: list[str] = []
    disps = dispositions_for(sources)
    for slug, d in sorted(disps.items()):
        detail = d.get("detail", "")
        detail = f" —— {detail}" if detail else ""
        blocked = d.get("blocked_for_rules", True)
        block_note = ""
        if blocked:
            block_note = (
                f" 该来源不得支撑任何规则（已登记 `{d['disposition_id']}`）；"
                f"若发现相关规则引用此来源，请改到 `rebased_to` 字段所列来源。")
        notes.append(
            f"- **{slug}** ({d.get('reason','')}): 抓取件不可用{detail}。"
            f"处置状态 `quarantined`（{blocked}）{block_note}"
        )
    if not notes:
        notes.append("无已知抓取缺口（所有来源均已成功抓取）。")
    return notes
