#!/usr/bin/env python3
"""shopee-br-policy-research 模块测试。

本模块的测试不重新抓取（网络不可靠），而是核对**已有资产**的一致性：
来源清单 ↔ 抓取件 ↔ 抓取报告 ↔ 规则引用。

运行：
    env -u LD_LIBRARY_PATH python3 tests/shopee-br-policy-research/run_tests.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESEARCH = os.path.join(ROOT, "research")
RAW = os.path.join(RESEARCH, "raw")
RULES = os.path.join(ROOT, "rules")

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
