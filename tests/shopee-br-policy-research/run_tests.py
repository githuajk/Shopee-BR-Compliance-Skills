#!/usr/bin/env python3
"""shopee-br-policy-research 模块测试。

本模块的测试不重新抓取（网络不可靠），而是核对**已有资产**的一致性：
来源清单 ↔ 抓取件 ↔ 抓取报告 ↔ 规则引用。

L9 额外覆盖 `src/` 实现层（`sbr_policy_research` 包 + CLI 入口 + 503
来源处置记录）：包导入 / 处置校验 / 引文核验模块 / 引擎全量运行 /
契约 Schema 校验 / 错误路径 / CLI 冒烟。

运行：
    env -u LD_LIBRARY_PATH python3 tests/shopee-br-policy-research/run_tests.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESEARCH = os.path.join(ROOT, "research")
RAW = os.path.join(RESEARCH, "raw")
RULES = os.path.join(ROOT, "rules")
MODULE_SRC = os.path.join(ROOT, "skills", "shopee-br-policy-research", "src")

sys.path.insert(0, MODULE_SRC)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from validate_json import Validator  # noqa: E402
from sbr_policy_research import (  # noqa: E402
    CONTRACT_VERSION,
    MODULE_NAME,
    RULE_VERSION,
    __version__,
    build_skill_input,
    run_policy_research,
)
from sbr_policy_research import citations as pr_citations  # noqa: E402
from sbr_policy_research import dispositions as pr_dispositions  # noqa: E402
from sbr_policy_research import assets as pr_assets  # noqa: E402
from sbr_policy_research.errors import ContractError  # noqa: E402

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name: str, cond: bool, detail: str = "") -> bool:
    if cond:
        PASSED.append(name)
    else:
        FAILED.append((name, detail))
    return bool(cond)


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def load(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def article_id(url: str) -> str:
    m = re.search(r"/article/(\d+)", url or "")
    return m.group(1) if m else ""


# ---------------------------------------------------------------- L1
def test_source_registry() -> None:
    section("L1 来源清单结构")

    sources = load(os.path.join(RESEARCH, "sources.json"))
    check("sources.json 非空", len(sources) > 0, str(len(sources)))

    VALID_TIERS = {
        "platform_official", "law", "internal_risk", "unverified",
        "ai_inference", "technical",
    }
    slugs = set()
    for s in sources:
        slug = s.get("slug", "")
        check(f"{slug}: slug 唯一", slug not in slugs, "重复")
        slugs.add(slug)
        for field in ("slug", "title", "publisher", "url", "tier", "scope"):
            check(f"{slug}: 有 {field}", field in s and s[field], "缺失")
        check(f"{slug}: tier 合法", s.get("tier") in VALID_TIERS, str(s.get("tier")))
        check(f"{slug}: url 是 http(s)",
              str(s.get("url", "")).startswith("http"), str(s.get("url")))

    tiers = {s["tier"] for s in sources}
    check("至少有一条 platform_official 来源", "platform_official" in tiers, str(tiers))
    check("至少有一条 law 来源", "law" in tiers, str(tiers))

    # 抓取失败的来源必须显式登记
    for s in sources:
        if s.get("capture_status", "").startswith("failed"):
            check(f"{s['slug']}: 抓取失败已登记 capture_note",
                  bool(s.get("capture_note")), "缺 capture_note")


# ---------------------------------------------------------------- L2
def test_captures() -> None:
    section("L2 抓取件")

    sources = load(os.path.join(RESEARCH, "sources.json"))
    for s in sources:
        slug = s["slug"]
        path = os.path.join(RAW, f"{slug}.txt")
        if not os.path.exists(path):
            check(f"{slug}: 抓取件存在或已登记抓取失败",
                  s.get("capture_status", "").startswith("failed"), "缺文件且未登记")
            continue
        size = os.path.getsize(path)
        check(f"{slug}: 抓取件非占位（≥500 字节）", size >= 500, f"{size} 字节")
        with open(path, encoding="utf-8") as f:
            head = f.read(400)
        check(f"{slug}: 抓取件有来源标记",
              ("# title:" in head or "# url:" in head
               or "|" in head or "Presidência" in head
               or "Legislação" in head or "INPI" in head),
              head[:60].replace("\n", " "))

    # 无孤儿
    registered = {s["slug"] for s in sources}
    for fn in sorted(os.listdir(RAW)):
        if not fn.endswith(".txt"):
            continue
        slug = fn[:-4]
        check(f"{fn}: 已登记在 sources.json", slug in registered, "孤儿抓取件")


# ---------------------------------------------------------------- L3
def test_fetch_reports() -> None:
    section("L3 抓取报告与实际一致")

    for report in ("_fetch_report.json", "_edu_fetch_report.json"):
        rp = os.path.join(RAW, report)
        if not os.path.exists(rp):
            check(f"{report} 存在", False, "缺失")
            continue
        entries = load(rp)
        check(f"{report} 非空", len(entries) > 0, str(len(entries)))
        for e in entries:
            slug = e.get("slug", "")
            fp = os.path.join(RAW, f"{slug}.txt")
            if e.get("status") != "ok":
                # 记为失败的，抓取件要么不存在（真实失败），要么存在（报告过期）
                if os.path.exists(fp):
                    check(f"{report}:{slug} 状态与文件一致", False,
                          "报告记为失败但文件存在")
                else:
                    check(f"{report}:{slug} 状态与文件一致", True, "")
                continue
            if not os.path.exists(fp):
                check(f"{report}:{slug} 记为 ok 但文件缺失", False, "缺文件")
                continue
            claimed = e.get("text_chars", e.get("chars"))
            actual = os.path.getsize(fp)
            check(f"{report}:{slug} 字符数与实际一致",
                  claimed is not None and abs(actual - claimed) <= max(500, actual * 0.35),
                  f"报告 {claimed} vs 实际 {actual}")


# ---------------------------------------------------------------- L4
def test_rule_references() -> None:
    section("L4 规则引用的来源")

    sources = load(os.path.join(RESEARCH, "sources.json"))
    known_ids = {article_id(s["url"]) for s in sources}
    known_ids.discard("")
    known_urls = {s["url"] for s in sources}
    failed_urls = {s["url"] for s in sources
                   if s.get("capture_status", "").startswith("failed")}

    total = 0
    for fn in sorted(os.listdir(RULES)):
        if not fn.endswith(".json"):
            continue
        for r in load(os.path.join(RULES, fn)).get("rules", []):
            total += 1
            url = r.get("source_url", "")
            check(f"{r['rule_id']}: 有 source_url", bool(url), "缺失")
            if not url:
                continue
            check(f"{r['rule_id']}: source_url 已登记",
                  (article_id(url) in known_ids) or (url in known_urls), url)
            check(f"{r['rule_id']}: 未引用抓取失败的来源",
                  url not in failed_urls, url)
    check("规则总数 > 0", total > 0, str(total))


# ---------------------------------------------------------------- L5
def test_violation_codes() -> None:
    section("L5 平台违规码目录")

    vc = load(os.path.join(RESEARCH, "violation_codes.json"))
    codes = vc.get("codes", [])
    check("违规码目录非空", len(codes) > 0, str(len(codes)))
    check("code_count 与实际一致", vc.get("code_count") == len(codes),
          f"{vc.get('code_count')} vs {len(codes)}")
    check("source_tier 是 platform_official",
          vc.get("source_tier") == "platform_official", str(vc.get("source_tier")))
    check("source_file 指向实际抓取件",
          os.path.exists(os.path.join(ROOT, vc.get("source_file", ""))),
          vc.get("source_file"))

    SEV = {"Extrema": "critical", "Alta": "high", "Média": "medium", "Baixa": "low"}
    for c in codes:
        cid = c.get("platform_code", "?")
        for field in ("code", "description", "severity_pt", "severity",
                      "generates_penalty_point", "category", "platform_code"):
            check(f"{cid}: 有 {field}", field in c, "缺失")
        check(f"{cid}: severity 与 severity_pt 一致",
              SEV.get(c.get("severity_pt")) == c.get("severity"),
              f"{c.get('severity_pt')} → {c.get('severity')}")
        check(f"{cid}: penalty 是布尔", isinstance(c.get("generates_penalty_point"), bool),
              str(type(c.get("generates_penalty_point"))))
        check(f"{cid}: 无未公开的处罚点分值",
              "penalty_points" not in c, "含分值字段")

    # 平台原文声明：Baixa 严重度不产生处罚点
    low_with_penalty = [c["platform_code"] for c in codes
                        if c.get("severity") == "low" and c.get("generates_penalty_point")]
    check("low 严重度均不产生处罚点", not low_with_penalty, str(low_with_penalty[:5]))


# ---------------------------------------------------------------- L6
def test_no_unpublished_numbers() -> None:
    section("L6 未公开数值与占位文本")

    # 规则库与词库中不得出现具体处罚点分值
    forbidden = re.compile(r"(-?\d+)\s*(pontos? de penalidade|penalty points?)", re.I)
    hits = []
    for sub in ("rules", "lexicon"):
        base = os.path.join(ROOT, sub)
        for dirpath, _, files in os.walk(base):
            for fn in files:
                if not fn.endswith(".json"):
                    continue
                p = os.path.join(dirpath, fn)
                with open(p, encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        m = forbidden.search(line)
                        if m:
                            hits.append(f"{os.path.relpath(p, ROOT)}:{i}")
    check("无平台未公开的处罚点分值", not hits, str(hits[:5]))

    # 抓取件与规则中不得残留占位标记
    placeholders = ("TODO", "FIXME", "TBD", "<your", "PLACEHOLDER")
    ph = []
    for sub in ("rules", "research"):
        base = os.path.join(ROOT, sub)
        for dirpath, _, files in os.walk(base):
            for fn in files:
                if not (fn.endswith(".json") or fn.endswith(".txt")):
                    continue
                p = os.path.join(dirpath, fn)
                with open(p, encoding="utf-8", errors="replace") as f:
                    text = f.read()
                for token in placeholders:
                    if token in text:
                        ph.append(f"{os.path.relpath(p, ROOT)}:{token}")
    check("无占位符残留", not ph, str(ph[:5]))


# ---------------------------------------------------------------- L7
def test_tools() -> None:
    section("L7 校验工具可执行")

    for tool, expect_ok in (("tools/verify_citations.py", True),
                            ("tools/check_sources.py", True)):
        proc = subprocess.run([sys.executable, os.path.join(ROOT, tool)],
                              capture_output=True, text=True, cwd=ROOT)
        if expect_ok:
            check(f"{tool} 退出码为 0", proc.returncode == 0,
                  (proc.stdout or "")[-300:] + (proc.stderr or "")[-300:])

    proc = subprocess.run([sys.executable, os.path.join(ROOT, "tools/verify_citations.py")],
                          capture_output=True, text=True, cwd=ROOT)
    out = proc.stdout
    # 不硬编码规则条数 —— 规则库随批次扩充，数量会变；
    # 只断言「全部引文逐字命中且 0 failed」。
    import re as _re
    m = _re.search(r"(\d+)/(\d+) excerpts verified verbatim", out)
    ok = bool(m) and m.group(1) == m.group(2) and "0 failed" in out
    check(f"引文核验全部通过（{m.group(0) if m else '未解析'}）", ok,
          out.strip().splitlines()[-1] if out.strip() else "")


# ---------------------------------------------------------------- L8
def test_edu_articles() -> None:
    section("L8 教育中心文章登记")

    ea = load(os.path.join(RESEARCH, "edu_articles.json"))
    items = ea.get("items", [])
    check("edu_articles.json 非空", len(items) > 0, str(len(items)))
    for it in items:
        slug = it.get("slug", "?")
        out = it.get("out", "")
        check(f"{slug}: 输出路径指向实际文件",
              bool(out) and os.path.exists(os.path.join(ROOT, out)), out)
        if out and os.path.exists(os.path.join(ROOT, out)):
            with open(os.path.join(ROOT, out), encoding="utf-8") as f:
                head = f.read(300)
            aid = str(it.get("article_id", ""))
            check(f"{slug}: 抓取件头部的 article id 与登记一致",
                  aid in head, f"登记 {aid}，头部 {head[:80]!r}")


def _validator(schema_rel: str) -> "Validator":
    path = os.path.join(ROOT, schema_rel)
    with open(path, encoding="utf-8") as f:
        return Validator(json.load(f), base_dir=os.path.dirname(path))


def validate_against(schema_rel: str, payload, label: str) -> bool:
    errs = _validator(schema_rel).validate(payload)
    return check(f"{label} 通过 {schema_rel} 校验", not errs, str(errs[:2]))


# ---------------------------------------------------------------- L9
def test_src_implementation() -> None:
    section("L9 src 实现层（sbr_policy_research 包 + CLI + 503 处置）")

    # --- L9.1 包常量 -------------------------------------------------
    check("MODULE_NAME 正确", MODULE_NAME == "shopee-br-policy-research",
          MODULE_NAME)
    for name, val in (("CONTRACT_VERSION", CONTRACT_VERSION),
                      ("RULE_VERSION", RULE_VERSION),
                      ("__version__", __version__)):
        check(f"{name} 非空", isinstance(val, str) and val, str(val))

    sources = load(os.path.join(RESEARCH, "sources.json"))
    failed = [s for s in sources if s.get("capture_status", "").startswith("failed")]
    check("抓取失败来源已登记", len(failed) >= 1, str([s["slug"] for s in failed]))
    failed_url = failed[0]["url"] if failed else ""

    # --- L9.2 503 来源正式处置（disposition） -------------------------
    disps = pr_dispositions.dispositions_for(sources)
    check("每条抓取失败来源都有 disposition",
          all(s["slug"] in disps for s in failed),
          str([s["slug"] for s in failed if s["slug"] not in disps]))

    qslug, qdisp = failed[0]["slug"], disps.get(failed[0]["slug"], {})
    check(f"{qslug}: disposition 状态为 quarantined",
          qdisp.get("status") == "quarantined", str(qdisp.get("status")))
    check(f"{qslug}: disposition 原因含 503",
          "503" in str(qdisp.get("reason", "")), str(qdisp.get("reason")))
    check(f"{qslug}: disposition 有重抓方案",
          bool(qdisp.get("remediation")), "缺失")
    check(f"{qslug}: disposition 必填字段齐全",
          all(f in qdisp for f in pr_dispositions.REQUIRED_FIELDS),
          str([f for f in pr_dispositions.REQUIRED_FIELDS if f not in qdisp]))
    check("dispositions.validate_dispositions 无问题",
          pr_dispositions.validate_dispositions(sources) == [],
          str(pr_dispositions.validate_dispositions(sources))[:200])
    check("quarantined_slugs 与登记一致",
          pr_dispositions.quarantined_slugs(sources) == {qslug},
          str(pr_dispositions.quarantined_slugs(sources)))

    slugs_known = {s["slug"] for s in sources}
    rebased_to = qdisp.get("rebased_to", [])
    check(f"{qslug}: rebased_to 来源均已登记",
          all(s in slugs_known for s in rebased_to), str(rebased_to))
    rule_ids = set()
    for fn in sorted(os.listdir(RULES)):
        if fn.endswith(".json"):
            for r in load(os.path.join(RULES, fn)).get("rules", []):
                rule_ids.add(r.get("rule_id"))
    rebased_rules = qdisp.get("dependent_rules_rebased", [])
    check(f"{qslug}: dependent_rules_rebased 在规则库中存在",
          all(rid in rule_ids for rid in rebased_rules), str(rebased_rules))
    citing_failed = [r.get("rule_id")
                     for fn in sorted(os.listdir(RULES))
                     for r in (load(os.path.join(RULES, fn)).get("rules", [])
                               if fn.endswith(".json") else [])
                     if r.get("source_url") == failed_url]
    check(f"{qslug}: 无任何规则引用 503 来源", not citing_failed,
          str(citing_failed))

    # --- L9.3 引文核验模块 -------------------------------------------
    rules_pairs = pr_assets.load_rules(ROOT)
    rep = pr_citations.verify_rules(rules_pairs, RAW)
    check(f"src 引文核验模块：{rep['ok']}/{rep['total']} 逐字命中",
          rep["total"] > 0 and rep["ok"] == rep["total"],
          f"{rep['ok']}/{rep['total']}, failed={rep['failed'][:2]}")

    # --- L9.4 引擎全量运行 -------------------------------------------
    si = build_skill_input("REQ-L9-0001",
                           [{"path": "research/", "kind": "source_document"}])
    bundle = run_policy_research(si, options={}, root=ROOT)
    check("引擎全量运行 ok", bundle["ok"] is True, str(bundle["errors"][:3]))
    check("引擎无 error", bundle["errors"] == [], str(bundle["errors"][:3]))
    results = bundle["results"]
    check(f"引擎产出 {len(results)} 条来源核查结果", len(results) > 0,
          str(len(results)))

    by_target = {r["target_ref"]: r for r in results}
    ok_slug = next((s["slug"] for s in sources
                    if s["slug"] not in {f["slug"] for f in failed}), "")
    check(f"{ok_slug}: 正常来源 verdict=PASS",
          by_target.get(ok_slug, {}).get("verdict") == "PASS",
          str(by_target.get(ok_slug, {}).get("verdict")))
    q = by_target.get(qslug, {})
    check(f"{qslug}: 隔离来源 verdict=REVIEW / flag_for_review",
          q.get("verdict") == "REVIEW" and q.get("action") == "flag_for_review"
          and q.get("requires_human_review") is True,
          f"verdict={q.get('verdict')} action={q.get('action')}")

    handoff = bundle["handoff"]
    check("handoff assumptions 非空（契约 minItems 1）",
          len(handoff["assumptions"]) >= 1, str(len(handoff["assumptions"])))
    check("handoff known_gaps 非空（契约 minItems 1）",
          len(handoff["known_gaps"]) >= 1, str(handoff["known_gaps"]))
    check("handoff known_gaps 含 503 隔离来源",
          any(qslug in g for g in handoff["known_gaps"]),
          str(handoff["known_gaps"])[:120])

    # --- L9.5 契约 Schema 校验 ----------------------------------------
    for i, r in enumerate(results):
        validate_against("contracts/audit_result.schema.json", r,
                         f"results[{i}] ({r['target_ref']})")
    validate_against("contracts/module_handoff.schema.json", handoff,
                     "module_handoff")
    validate_against("contracts/skill_input.schema.json", si, "skill_input")

    # --- L9.6 错误路径（隔离来源被规则引用 → 必须报错） -----------------
    with tempfile.TemporaryDirectory(prefix="sbr-pr-l9-") as tmp:
        tmp_raw = os.path.join(tmp, "research", "raw")
        os.makedirs(tmp_raw, exist_ok=True)
        os.makedirs(os.path.join(tmp, "rules"), exist_ok=True)
        json.dump([
            {"slug": qslug, "title": "t", "publisher": "Anvisa",
             "url": failed_url, "tier": "law", "scope": "s",
             "capture_status": "failed_http_503"},
        ], open(os.path.join(tmp, "research", "sources.json"), "w"),
            ensure_ascii=False)
        json.dump({"rules": [
            {"rule_id": "SBR-MED-001", "title": "t", "description": "d",
             "status": "active", "source_url": failed_url,
             "source_excerpt": "一段无法核验的引文",
             "trigger_conditions": [], "severity": "high",
             "decision": "flag_for_review"},
        ]}, open(os.path.join(tmp, "rules", "05_medicines_health.json"), "w"),
            ensure_ascii=False)
        bad = run_policy_research(
            build_skill_input("REQ-L9-0002",
                              [{"path": "research/", "kind": "source_document"}]),
            options={}, root=tmp)
        joined = " | ".join(bad["errors"])
        check("规则引用 503 来源 → 引擎报错",
              any("抓取失败" in e for e in bad["errors"]), joined[:200])
        check("缺失 disposition → 引擎报错",
              any("disposition" in e for e in bad["errors"]), joined[:200])
        check("引文无法核验 → 引擎报错（strict）",
              any("引文" in e for e in bad["errors"]), joined[:200])
        check("错误路径 ok=False", bad["ok"] is False, str(bad["errors"]))

    # --- L9.7 未知 options 忽略 + 契约错误 --------------------------------
    try:
        bundle2 = run_policy_research(
            si, options={"bogus_key": 1, "unknown_flag": None}, root=ROOT)
        check("未知 options 键被忽略（契约要求）",
              bundle2["ok"] is True, str(bundle2["errors"][:2]))
    except Exception as exc:  # noqa: BLE001
        check("未知 options 键被忽略（契约要求）", False, repr(exc))

    wrong = dict(si)
    wrong["task_type"] = "listing_audit"
    try:
        run_policy_research(wrong, root=ROOT)
        check("task_type 非 policy_research → 抛 ContractError", False, "未抛错")
    except ContractError:
        check("task_type 非 policy_research → 抛 ContractError", True, "")

    # --- L9.8 targets 过滤 ------------------------------------------------
    filtered = run_policy_research(
        si, options={"targets": [qslug]}, root=ROOT)
    check("targets 过滤只产出指定来源",
          [r["target_ref"] for r in filtered["results"]] == [qslug],
          str([r["target_ref"] for r in filtered["results"]]))

    # --- L9.9 CLI 冒烟 ------------------------------------------------------
    cli = os.path.join(ROOT, "skills", "shopee-br-policy-research", "src",
                       "sbr_policy_research_cli.py")
    env = {k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"}
    with tempfile.TemporaryDirectory(prefix="sbr-pr-cli-") as tmp:
        out_dir = os.path.join(tmp, "out")
        proc = subprocess.run(
            [sys.executable, cli, "--request-id", "REQ-L9-CLI",
             "--out-dir", out_dir, "--quiet"],
            capture_output=True, text=True, cwd=ROOT, env=env)
        check("CLI 全量审计退出码 0", proc.returncode == 0,
              (proc.stderr or "")[-200:])
        for name in ("skill_input.json", "audit_results.json",
                     "module_handoff.json"):
            p = os.path.join(out_dir, name)
            exists = os.path.exists(p)
            check(f"CLI 产出 {name}", exists, p)
            if exists:
                json.load(open(p, encoding="utf-8"))
        check("CLI 产出三份契约文件可解析", True, "")

        bad_si = os.path.join(tmp, "bad_si.json")
        with open(bad_si, "w", encoding="utf-8") as f:
            json.dump({"request_id": "REQ-BAD-1", "task_type": "listing_audit",
                       "target": {"kind": "product_batch"},
                       "provenance": {"inputs": [{"path": "x"}],
                                      "produced_at": "2026-10-28T00:00:00Z"}},
                      f)
        proc2 = subprocess.run(
            [sys.executable, cli, "--skill-input", bad_si,
             "--out-dir", out_dir, "--quiet"],
            capture_output=True, text=True, cwd=ROOT, env=env)
        check("CLI 对 task_type 不匹配的 SkillInput 退出码 2",
              proc2.returncode == 2, str(proc2.returncode)
              + (proc2.stderr or "")[-120:])


# ---------------------------------------------------------------- main
def main() -> int:
    print("=" * 62)
    print("shopee-br-policy-research 模块测试")
    print(f"仓库根: {ROOT}")
    print("=" * 62)

    test_source_registry()
    test_captures()
    test_fetch_reports()
    test_rule_references()
    test_violation_codes()
    test_no_unpublished_numbers()
    test_edu_articles()
    test_src_implementation()
    test_tools()

    print("\n" + "=" * 62)
    print(f"PASSED: {len(PASSED)}   FAILED: {len(FAILED)}")
    if FAILED:
        print("\nFailures:")
        for name, detail in FAILED[:25]:
            print(f"  - {name}: {detail}")
        return 1
    print("全部测试通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
