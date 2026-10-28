#!/usr/bin/env python3
"""校验来源清单与抓取件的一致性。

`sources.json` 声明了每个来源的 slug / tier / url；
`research/raw/<slug>.txt` 是该来源的抓取件。本工具核对：

1. 每条来源都有对应的抓取件（或明确标记为抓取失败）
2. 抓取件非空、不是占位内容
3. `source_tier` 取值合法（只有 platform_official / law 能产生 block 类动作）
4. 抓取件里的 `source_url` 出现在清单中
5. **抓取报告与实际文件一致** —— 报告写"20 字符"但文件有 36KB 的情况，
   说明报告已过期（重抓后没更新报告），必须报出来。

用法：
    python3 tools/check_sources.py [--verbose]
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESEARCH = os.path.join(ROOT, "research")
RAW = os.path.join(RESEARCH, "raw")

VALID_TIERS = {
    "platform_official", "law", "internal_risk", "unverified",
    "ai_inference", "technical",
}

#: 抓取件小于此字节数视为占位/空
MIN_CAPTURE_BYTES = 500

#: 报告字符数与实际字节数允许的偏差（字节 vs 字符，UTF-8 葡语文本约差 15%）
SIZE_TOLERANCE_RATIO = 0.35


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    verbose = "--verbose" in sys.argv
    errors = []
    warnings = []

    sources = load_json(os.path.join(RESEARCH, "sources.json"))
    by_slug = {s["slug"]: s for s in sources}

    # --- 1. 每条来源都要有抓取件 ---
    # 例外：显式记录了 `capture_status: failed` 的来源 —— 抓取确实失败过，
    # 已如实登记。这类来源**不得**用于支撑任何规则（由 check_rule_regex
    # 与 verify_citations 共同保证），但它本身不是清单错误。
    failed_captures = []
    for slug, s in by_slug.items():
        path = os.path.join(RAW, f"{slug}.txt")
        if not os.path.exists(path):
            if s.get("capture_status", "").startswith("failed"):
                failed_captures.append(slug)
                if verbose:
                    print(f"  ok  {slug:42s} 抓取失败（已登记）")
            else:
                errors.append(f"{slug}: 缺少抓取件 research/raw/{slug}.txt")
            continue
        size = os.path.getsize(path)
        if size < MIN_CAPTURE_BYTES:
            errors.append(
                f"{slug}: 抓取件只有 {size} 字节 —— 疑似占位或抓取失败")
        if verbose:
            print(f"  ok  {slug:42s} {size:>7d} 字节  tier={s['tier']}")

    # --- 2. 抓取件不得有来源清单之外的孤儿 ---
    # 孤儿抓取件无法被规则引用（规则引用要经 sources.json 登记），
    # 却留在 raw/ 里 —— 读者会以为它是可用来源。必须报出来。
    for fn in sorted(os.listdir(RAW)):
        if not fn.endswith(".txt"):
            continue
        slug = fn[:-4]
        if slug not in by_slug:
            errors.append(
                f"孤儿抓取件 research/raw/{fn} —— sources.json 未登记，"
                f"该抓取件无法被任何规则引用")

    # --- 3. tier 合法 ---
    for slug, s in by_slug.items():
        tier = s.get("tier")
        if tier not in VALID_TIERS:
            errors.append(f"{slug}: source.tier={tier!r} 不合法")
        if not s.get("url", "").startswith("http"):
            errors.append(f"{slug}: url 缺失或不是 http(s)")

    # --- 4. 抓取报告与实际一致 ---
    # 两份报告：_fetch_report.json（首轮）与 _edu_fetch_report.json（教育中心文章）。
    # 首轮报告对部分来源记录了 "20 字符"（占位），后来重抓但报告没更新 ——
    # 这种不一致会让读者误以为那些来源是空的。
    for report_name in ("_fetch_report.json", "_edu_fetch_report.json"):
        rp = os.path.join(RAW, report_name)
        if not os.path.exists(rp):
            continue
        for entry in load_json(rp):
            slug = entry.get("slug")
            status = entry.get("status")
            if status != "ok":
                # 抓取失败：清单里应该有该来源，且 raw/ 下确实没有文件
                in_list = slug in by_slug
                has_file = os.path.exists(os.path.join(RAW, f"{slug}.txt"))
                if in_list and has_file:
                    warnings.append(
                        f"{report_name}: {slug} 记为 {status}，但 raw/ 下已有抓取件 "
                        f"—— 报告已过期")
                continue
            path = os.path.join(RAW, f"{slug}.txt")
            if not os.path.exists(path):
                errors.append(f"{report_name}: {slug} 记为 ok 但抓取件不存在")
                continue
            actual = os.path.getsize(path)
            claimed = entry.get("text_chars", entry.get("chars"))
            if not claimed:
                continue
            # 报告记字符数，实际是字节数 —— 葡语 UTF-8 约 1.15~1.25 字节/字符
            drift = abs(actual - claimed) / max(claimed, 1)
            if drift > SIZE_TOLERANCE_RATIO:
                warnings.append(
                    f"{report_name}: {slug} 报告称 {claimed} 字符，"
                    f"实际 {actual} 字节 —— 报告已过期（重抓后未更新）")

    # --- 5. 抓取失败的来源不得支撑任何规则 ---
    # 规则必须有逐字可核验的引文。引文必须来自**实际存在的抓取件**——
    # 指向未抓取到的来源的规则，其引文无法核验，等于没有来源。
    rules_dir = os.path.join(ROOT, "rules")
    failed_urls = {s["url"] for s in sources
                   if s.get("capture_status", "").startswith("failed")}
    if failed_urls and os.path.isdir(rules_dir):
        for fn in sorted(os.listdir(rules_dir)):
            if not fn.endswith(".json"):
                continue
            with open(os.path.join(rules_dir, fn), encoding="utf-8") as f:
                rules = json.load(f).get("rules", [])
            for r in rules:
                url = r.get("source_url", "")
                if url in failed_urls:
                    errors.append(
                        f"{r['rule_id']}: 引用了抓取失败的来源 {url} —— "
                        f"引文无法核验，该规则必须改用其它已核验来源")

    # --- 6. 规则的 source_url 必须已登记 ---
    # 匹配按 **article id** 进行，而非整条 URL —— 同一篇文章在平台上有
    # `seller.br.shopee.cn` 与 `seller.shopee.com.br` 两个域名变体，
    # 规则引用的变体可能与清单登记的变体不同。按 id 匹配才不会误报。
    def article_id(url: str) -> str:
        m = re.search(r"/article/(\d+)", url or "")
        return m.group(1) if m else ""

    known_ids = {article_id(s["url"]) for s in sources}
    known_ids.discard("")
    known_urls = {s["url"] for s in sources}
    if os.path.isdir(rules_dir):
        for fn in sorted(os.listdir(rules_dir)):
            if not fn.endswith(".json"):
                continue
            with open(os.path.join(rules_dir, fn), encoding="utf-8") as f:
                rules = json.load(f).get("rules", [])
            for r in rules:
                url = r.get("source_url", "")
                if not url:
                    continue
                aid = article_id(url)
                if aid and aid in known_ids:
                    continue
                if url in known_urls:
                    continue
                errors.append(
                    f"{r['rule_id']}: source_url 未登记在 sources.json —— {url}")

    print(f"核对 {len(sources)} 条来源，{len(os.listdir(RAW))} 个抓取件")
    if failed_captures:
        print(f"  抓取失败（已登记，不得用于支撑规则）：{len(failed_captures)} 条")
        for slug in failed_captures:
            print(f"    - {slug}")
    if warnings:
        print(f"\n{len(warnings)} 个警告：")
        for w in warnings:
            print("  -", w)
    if errors:
        print(f"\n{len(errors)} 个错误：")
        for e in errors:
            print("  -", e)
        return 1
    print("来源清单与抓取件一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
