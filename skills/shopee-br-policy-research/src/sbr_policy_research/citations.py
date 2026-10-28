"""逐字引文核验（移植自 `tools/verify_citations.py` 的语义）。

硬约束 H4：规则的 `source_excerpt` 必须**逐字**出现在抓取件中
（空白规范化 + 标点归一化后可比，但不得改写原文）。

本模块只读抓取件与规则，不修改任何文件。
"""

from __future__ import annotations

import json
import os
import re


#: 弯引号 / 破折号 / 不换行空格 → ASCII 等价
_TRANSLATE = {
    "’": "'", "‘": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ", "…": "...",
}


def norm(s: str) -> str:
    for a, b in _TRANSLATE.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip().lower()


def loose(s: str) -> str:
    """归一化文本，去掉句末标点。

    被抓取页面与规则条文混排时，引文末尾可能是逗号/句号。归一去
    除，保留其余一切字符 —— 改写仍算失败。
    """
    s = norm(s)
    s = s.replace(",", " ").replace(".", " ").replace(";", " ").replace(":", " ")
    return re.sub(r"\s+", " ", s).strip()


def load_captures(raw_dir: str) -> dict[str, str]:
    """加载 `research/raw/*.txt`，返回 slug → norm 文本的映射。"""
    out: dict[str, str] = {}
    if not os.path.isdir(raw_dir):
        return out
    for fn in sorted(os.listdir(raw_dir)):
        if not fn.endswith(".txt"):
            continue
        with open(os.path.join(raw_dir, fn), encoding="utf-8") as handle:
            out[fn[:-4]] = norm(handle.read())
    return out


def slug_from_url(url: str) -> str:
    """按 URL 尾部生成一个候选 slug（用于从抓取件反查来源）。"""
    u = (url or "").lower()
    tail = u.rstrip("/").split("/")[-1]
    return re.sub(r"[^a-z0-9]+", "_", tail).strip("_")


def verify_rules(rules: list[tuple[str, dict]], raw_dir: str) -> dict:
    """逐条规则核验 source_excerpt 是否逐字出现在抓取件里。

    参数
    ----
    rules
        `(文件名, rule_dict)` 对列表（`assets.load_rules` 的产物）。
    raw_dir
        `research/raw/` 目录路径。

    返回
    ----
    {
        "total": int,
        "ok": int,
        "failed": [{file, rule_id, reason, excerpt_head, found_in}],
    }
    """
    captures = load_captures(raw_dir)
    if not captures:
        return {"total": 0, "ok": 0, "failed": [
            {"file": "?", "rule_id": "?", "reason": "no captures loaded",
             "excerpt_head": "", "found_in": ""}
        ]}

    ok: int = 0
    failed: list[dict] = []
    for fn, r in rules:
        excerpt = (r.get("source_excerpt") or "").strip()
        if not excerpt:
            failed.append({
                "file": fn, "rule_id": r.get("rule_id", "?"),
                "reason": "no source_excerpt", "excerpt_head": "", "found_in": "",
            })
            continue
        ne = loose(excerpt)
        slug = slug_from_url(r.get("source_url", ""))
        order: list[tuple[str, str]] = []
        if slug in captures:
            order.append((slug, captures[slug]))
        for key, text in captures.items():
            if key != slug:
                order.append((key, text))
        found_in = None
        for name, text in order:
            if ne and ne in loose(text):
                found_in = name
                break
        if found_in:
            ok += 1
        else:
            failed.append({
                "file": fn, "rule_id": r.get("rule_id", "?"),
                "reason": "excerpt not found verbatim",
                "excerpt_head": ne[:130], "found_in": "",
            })

    return {"total": len(rules), "ok": ok, "failed": failed}
