"""`shopee-br-policy-research` 引擎：一次 `SkillInput(task_type=policy_research)`
→ 全量来源核查 → `AuditResult[]` + `ModuleHandoff` + 结构化 findings。

职责边界（见 `skills/shopee-br-policy-research/SKILL.md`）：

* 只核查**来源与引文**：来源清单 ↔ 抓取件 ↔ 抓取报告 ↔ 规则引用 ↔
  逐字引文（H4）五向一致性；
* 产出契约产物（`contracts/audit_result.schema.json`、
  `contracts/module_handoff.schema.json`），`module_handoff` 的
  `assumptions` / `known_gaps` **必填且非空**；
* **不产生逐商品审核判定**（那是 listing-audit / ip-review 的职责）；
* **只读所有输入资产** —— 本引擎从不写回 `research/` / `rules/`。

纯标准库实现（Python 3.11+）。无第三方依赖。
"""

from __future__ import annotations

import json
import os
import re

from . import assets, citations, contracts, dispositions
from .errors import ContractError

_RULE_ID_RE = re.compile(r"^SBR-[A-Z]{2,4}-[0-9]{3,4}$")

ASSUMPTIONS = [
    ("Source material is read-only: every check in this run was performed "
     "against the in-repo research assets (research/sources.json, "
     "research/raw/, rules/); no online page was re-fetched."),
    ("Citation matching is by platform article id, not by full URL — the "
     "same article is served on both seller.br.shopee.cn and "
     "seller.shopee.com.br."),
    ("'Verbatim' (H4) means character-exact after whitespace and terminal-"
     "punctuation normalisation (tools/verify_citations.py semantics); a "
     "paraphrase still fails."),
    ("Quarantined sources (capture failed, e.g. HTTP 503) may not support "
     "any rule: they are reported as REVIEW and their disposition records "
     "the rebase / re-fetch plan."),
    ("Only sources with tier platform_official or law may back a "
     "block-class action (hard constraint H2)."),
    ("No platform action was taken; freeze_relist / escalate_legal remain "
     "human_only (hard constraint H6)."),
]


def _repo_root() -> str:
    here = os.path.abspath(os.path.dirname(__file__))
    # here = <root>/skills/shopee-br-policy-research/src/sbr_policy_research
    return os.path.abspath(os.path.join(here, "..", "..", "..", ".."))


def run_policy_research(skill_input: dict, options: dict | None = None,
                        root: str | None = None) -> dict:
    """执行一次全量来源核查。

    参数
    ----
    skill_input:
        符合 `contracts/skill_input.schema.json` 的输入，`task_type` 必须
        为 `policy_research`。
    options:
        模块私有选项：`targets`（slug / 规则 ID 过滤，缺省全量）、
        `strict`（默认 True，引文失败与孤儿抓取件算执行失败）、
        `to_module`（handoff 目标，默认 `shopee-br-compliance`）。未知键
        忽略（契约要求）。
    root:
        仓库根；缺省自动推导。

    返回
    ----
    bundle：``skill_input`` / ``results`` / ``handoff`` / ``findings`` /
    ``errors`` / ``ok``。``ok`` 为 True 时可安全交接下游。
    """
    if not isinstance(skill_input, dict):
        raise ContractError("skill_input must be a dict (SkillInput)")
    task_type = skill_input.get("task_type")
    if task_type != "policy_research":
        raise ContractError(
            f"task_type must be 'policy_research', got {task_type!r}")
    request_id = str(skill_input.get("request_id", ""))
    if len(request_id) < 4:
        raise ContractError("request_id must be >= 4 chars")
    options = options or {}
    targets = options.get("targets") or []
    to_module = options.get("to_module") or "shopee-br-compliance"
    strict = bool(options.get("strict", True))
    root = root or _repo_root()

    sources = assets.load_sources(root)
    raw_dir = os.path.join(root, "research", "raw")
    rules = assets.load_rules(root)

    cap = assets.capture_findings(sources, raw_dir)
    orphans = assets.orphan_findings(sources, raw_dir)
    tier_issues = assets.tier_findings(sources)
    stale = assets.fetch_report_findings(raw_dir)
    refs = assets.rule_reference_findings(rules, sources)
    cit = citations.verify_rules(rules, raw_dir)
    disp_issues = dispositions.validate_dispositions(sources)
    quarantined = dispositions.quarantined_slugs(sources)
    disp_map = dispositions.dispositions_for(sources)

    # ------------------------------------------------------------- results
    state_by_slug = {f["slug"]: f for f in cap}
    results: list[dict] = []

    def _in_scope(s: dict) -> bool:
        if not targets:
            return True
        if s.get("slug") in targets:
            return True
        return any(r.get("rule_id") in targets
                   for r in assets.rules_by_source_url(rules, s))

    for s in sources:
        if not _in_scope(s):
            continue
        slug = s.get("slug", "?")
        st = state_by_slug.get(slug, {}).get("state", "capture_missing")
        size = state_by_slug.get(slug, {}).get("bytes")

        rule_refs = [
            {"rule_id": r["rule_id"], "title": r.get("title"),
             "source_tier": r.get("source_tier"), "source_url": r.get("source_url")}
            for r in assets.rules_by_source_url(rules, s)
            if _RULE_ID_RE.match(str(r.get("rule_id", "")))
        ]

        if st == "ok":
            results.append(contracts.build_audit_result(
                request_id, slug, "PASS", "info", "allow",
                f"抓取件存在（{size} 字节，tier={s.get('tier')}，"
                f"域名变体按 article id 匹配），来源可支撑规则",
                rule_refs=rule_refs, confidence="confirmed",
                source_refs=[f"research/raw/{slug}.txt"],
                notes=f"source slug={slug}"))
        elif st == "failed_registered":
            d = disp_map.get(slug)
            if d:
                detail = d.get("remediation") or "(未给出重抓方案)"
                results.append(contracts.build_audit_result(
                    request_id, slug, "REVIEW", "medium", "flag_for_review",
                    f"抓取失败（{s.get('capture_status')}），处置 "
                    f"{d.get('disposition_id')} 状态 quarantined —— 该来源"
                    f"不得支撑任何规则。重抓方案：{str(detail)[:240]}",
                    confidence="confirmed", requires_human_review=True,
                    source_refs=[s["url"]] if s.get("url") else [],
                    review_rationale=f"quarantined 来源（{slug}）需人工重抓并更新处置记录",
                    notes=f"disposition {d.get('disposition_id')} status={d.get('status')}"))
            else:
                results.append(contracts.build_audit_result(
                    request_id, slug, "REVISE", "high", "revise",
                    f"抓取失败（{s.get('capture_status')}）但未登记 disposition —— "
                    f"该来源缺口未做正式处置",
                    confidence="confirmed", requires_human_review=True))
        else:  # capture_missing / placeholder
            results.append(contracts.build_audit_result(
                request_id, slug, "REVISE", "high", "revise",
                state_by_slug.get(slug, {}).get("detail",
                                                 f"{slug}: 抓取件缺失或为占位"),
                confidence="confirmed", requires_human_review=True))

    # 引文失败的规则 —— 一条 REVISE/REVIEW 结果（H4：核验不过不得 active）
    if cit["failed"]:
        verdict = "REVISE" if strict else "REVIEW"
        for x in cit["failed"]:
            results.append(contracts.build_audit_result(
                request_id, x["rule_id"], verdict, "high", "revise",
                f"引文核验失败（H4）：{x['reason']} —— 该规则不得标记 "
                f"active，须改 unverified 或重录逐字引文",
                confidence="confirmed", requires_human_review=True,
                notes=f"excerpt head: {x['excerpt_head'][:120]}"
                      if x.get("excerpt_head") else "no excerpt"))

    # ------------------------------------------------------------- errors
    errors: list[str] = []
    for f in refs["failed_refs"]:
        errors.append(
            f"{f['rule_id']}: 引用了抓取失败的来源 {f['url']} —— 引文无法核验，"
            f"该规则必须改用其它已核验来源")
    for u in refs["unregistered"]:
        errors.append(
            f"{u['rule_id']}: source_url 未登记在 sources.json —— {u['url']}")
    errors.extend(f"disposition: {i}" for i in disp_issues)
    errors.extend(tier_issues)
    if strict:
        errors.extend(f"孤儿抓取件 research/raw/{fn}（sources.json 未登记）"
                      for fn in orphans)
        errors.extend(
            f"{x['rule_id']}: 引文非逐字（{x['reason']}）"
            for x in cit["failed"])

    # ------------------------------------------------------------- handoff
    known_gaps = dispositions.gap_notes(sources)
    if stale:
        known_gaps.append(
            f"抓取报告与实际文件不一致（{len(stale)} 条），详见 "
            f"findings.stale_reports")
    if refs["unregistered"]:
        known_gaps.append(
            f"{len(refs['unregistered'])} 条规则的 source_url 未登记在 "
            f"sources.json（findings.unregistered_source_refs）")

    handoff = contracts.build_handoff(
        request_id, results, ASSUMPTIONS, known_gaps, to_module=to_module,
        requires_human_review=any(r["requires_human_review"] for r in results))

    findings = {
        "sources_total": len(sources),
        "captures_ok": sum(1 for f in cap if f.get("state") == "ok"),
        "quarantined": sorted(quarantined),
        "orphans": orphans,
        "stale_reports": stale,
        "rules_total": len(rules),
        "citations_ok": cit["ok"],
        "citation_failures": [x["rule_id"] for x in cit["failed"]],
        "failed_source_refs": [x["rule_id"] for x in refs["failed_refs"]],
        "unregistered_source_refs": [x["rule_id"] for x in refs["unregistered"]],
        "disposition_issues": disp_issues,
    }

    return {
        "skill_input": skill_input,
        "results": results,
        "handoff": handoff,
        "findings": findings,
        "errors": errors,
        "ok": not errors,
    }


def run_from_files(skill_input_path: str, out_dir: str,
                   options: dict | None = None,
                   root: str | None = None) -> dict:
    """读入 `skill_input.json`，写出三份契约产物（与兄弟模块同形）。

    写出（到 ``out_dir``）：

    * ``skill_input.json`` —— 原样回写，便于追溯；
    * ``audit_results.json`` —— `AuditResult[]`（来源核查结果）；
    * ``module_handoff.json`` —— `ModuleHandoff`（assumptions /
      known_gaps 必填非空）。

    **只读输入** —— 本函数从不写回被读取的文件。
    """
    with open(skill_input_path, encoding="utf-8") as handle:
        skill_input = json.load(handle)

    bundle = run_policy_research(skill_input, options=options, root=root)

    os.makedirs(out_dir, exist_ok=True)
    written = {
        "skill_input.json": bundle["skill_input"],
        "audit_results.json": bundle["results"],
        "module_handoff.json": bundle["handoff"],
    }
    for name, payload in written.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    bundle["written"] = sorted(written)
    return bundle
