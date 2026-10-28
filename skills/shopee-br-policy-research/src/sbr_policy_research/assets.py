"""研究资产（来源清单 / 抓取件 / 抓取报告 / 规则引用）的加载与结构核对。

本模块只读这些资产 —— 与 `tools/check_sources.py` 同一套语义，但返回
结构化结果，供 `engine.py` 组装 `AuditResult[]`。所有检查都是纯函数，
不修改任何文件。
"""

from __future__ import annotations

import json
import os
import re

from .errors import AssetMissing

#: 合法的来源层级（与 `skills/shopee-br-policy-research/SKILL.md` §5.1 一致）
VALID_TIERS = {
    "platform_official", "law", "internal_risk", "unverified",
    "ai_inference", "technical",
}

#: 抓取件小于此字节数视为占位/空
MIN_CAPTURE_BYTES = 500

#: 抓取报告字符数与实际文件字节数的允许偏差（葡语 UTF-8 约 1.15~1.25 字节/字符）
SIZE_TOLERANCE_RATIO = 0.35

#: 两份抓取报告
FETCH_REPORTS = ("_fetch_report.json", "_edu_fetch_report.json")


def load_json(path: str):
    """读入 JSON；文件缺失时抛 `AssetMissing`。"""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise AssetMissing(f"missing required asset: {path}") from exc


def load_sources(root: str) -> list[dict]:
    """`research/sources.json` —— 来源的唯一登记处。"""
    sources = load_json(os.path.join(root, "research", "sources.json"))
    if not isinstance(sources, list) or not sources:
        raise AssetMissing("research/sources.json must be a non-empty list")
    return sources


def load_rules(root: str) -> list[tuple[str, dict]]:
    """`rules/*.json` 全量规则（只读）。返回 (文件名, 规则) 对。"""
    rules_dir = os.path.join(root, "rules")
    out: list[tuple[str, dict]] = []
    if not os.path.isdir(rules_dir):
        return out
    for fn in sorted(os.listdir(rules_dir)):
        if not fn.endswith(".json"):
            continue
        for r in load_json(os.path.join(rules_dir, fn)).get("rules", []):
            out.append((fn, r))
    return out


def article_id(url: str) -> str:
    """从 URL 提取平台 article id（域名变体下按 id 匹配，不按整条 URL）。"""
    m = re.search(r"/article/(\d+)", url or "")
    return m.group(1) if m else ""


def is_failed_capture(source: dict) -> bool:
    return str(source.get("capture_status", "")).startswith("failed")


def quarantined_sources(sources: list[dict]) -> list[dict]:
    """抓取失败、显式登记的来源（不得支撑任何规则）。"""
    return [s for s in sources if is_failed_capture(s)]


def capture_findings(sources: list[dict], raw_dir: str) -> list[dict]:
    """逐来源核对抓取件：缺失（未登记失败）/ 占位（< 500 字节）。"""
    findings: list[dict] = []
    for s in sources:
        slug = s.get("slug", "?")
        path = os.path.join(raw_dir, f"{slug}.txt")
        if not os.path.exists(path):
            if is_failed_capture(s):
                findings.append({"slug": slug, "state": "failed_registered"})
            else:
                findings.append({
                    "slug": slug, "state": "capture_missing",
                    "detail": f"research/raw/{slug}.txt 不存在且未登记 capture_status: failed",
                })
            continue
        size = os.path.getsize(path)
        if size < MIN_CAPTURE_BYTES:
            findings.append({
                "slug": slug, "state": "placeholder",
                "detail": f"抓取件只有 {size} 字节（< {MIN_CAPTURE_BYTES}），疑似占位或抓取失败",
            })
        else:
            findings.append({"slug": slug, "state": "ok", "bytes": size})
    return findings


def orphan_findings(sources: list[dict], raw_dir: str) -> list[str]:
    """raw/ 下未登记在 sources.json 的孤儿抓取件。"""
    registered = {s.get("slug") for s in sources}
    orphans: list[str] = []
    if not os.path.isdir(raw_dir):
        return orphans
    for fn in sorted(os.listdir(raw_dir)):
        if fn.endswith(".txt") and fn[:-4] not in registered:
            orphans.append(fn)
    return orphans


def tier_findings(sources: list[dict]) -> list[str]:
    """tier 合法 + url 是 http(s)。"""
    issues: list[str] = []
    for s in sources:
        slug = s.get("slug", "?")
        if s.get("tier") not in VALID_TIERS:
            issues.append(f"{slug}: source.tier={s.get('tier')!r} 不合法")
        if not str(s.get("url", "")).startswith("http"):
            issues.append(f"{slug}: url 缺失或不是 http(s)")
    return issues


def fetch_report_findings(raw_dir: str) -> list[str]:
    """抓取报告与实际文件的一致性（过期报告 → 警告）。"""
    warnings: list[str] = []
    for report_name in FETCH_REPORTS:
        rp = os.path.join(raw_dir, report_name)
        if not os.path.exists(rp):
            continue
        for entry in load_json(rp):
            slug = entry.get("slug")
            status = entry.get("status")
            path = os.path.join(raw_dir, f"{slug}.txt")
            if status != "ok":
                if os.path.exists(path):
                    warnings.append(
                        f"{report_name}: {slug} 记为 {status}，但 raw/ 下已有抓取件 —— 报告已过期")
                continue
            if not os.path.exists(path):
                warnings.append(f"{report_name}: {slug} 记为 ok 但抓取件不存在")
                continue
            actual = os.path.getsize(path)
            claimed = entry.get("text_chars", entry.get("chars"))
            if not claimed:
                continue
            if abs(actual - claimed) / max(claimed, 1) > SIZE_TOLERANCE_RATIO:
                warnings.append(
                    f"{report_name}: {slug} 报告称 {claimed} 字符，实际 {actual} 字节 —— 报告已过期")
    return warnings


def rule_reference_findings(rules: list[tuple[str, dict]],
                            sources: list[dict]) -> dict:
    """规则引用的来源核对。

    返回 {"failed_refs": [...], "unregistered": [...]}：

    * `failed_refs` —— 规则引用了抓取失败的来源（**错误**，引文无法核验）；
    * `unregistered` —— 规则的 source_url 未在 sources.json 登记（按
      article id 匹配，容忍 `seller.br.shopee.cn` / `seller.shopee.com.br`
      域名变体）。
    """
    known_ids = {article_id(s["url"]) for s in sources}
    known_ids.discard("")
    known_urls = {s["url"] for s in sources}
    failed_urls = {s["url"] for s in sources if is_failed_capture(s)}

    failed_refs: list[dict] = []
    unregistered: list[dict] = []
    for fn, r in rules:
        url = r.get("source_url", "")
        if not url:
            continue
        if url in failed_urls:
            failed_refs.append({
                "file": fn, "rule_id": r.get("rule_id", "?"), "url": url,
            })
        elif url not in known_urls and article_id(url) not in known_ids:
            unregistered.append({
                "file": fn, "rule_id": r.get("rule_id", "?"), "url": url,
            })
    return {"failed_refs": failed_refs, "unregistered": unregistered}


def rules_by_source_url(rules: list[tuple[str, dict]],
                        source: dict) -> list[dict]:
    """引用某来源（按 article id 或整 URL）的规则列表。"""
    aid = article_id(source.get("url", ""))
    url = source.get("url", "")
    out: list[dict] = []
    for _fn, r in rules:
        rurl = r.get("source_url", "")
        if rurl == url or (aid and article_id(rurl) == aid):
            out.append(r)
    return out
