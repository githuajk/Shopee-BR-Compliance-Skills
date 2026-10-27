#!/usr/bin/env python3
"""词库扫描器 —— listing-audit / ip-review 共用的确定性筛查工具。

设计要点（来自 docs/SOP_COMPLIANCE_REVIEW.md）：

1. **归一化管线**：小写 → NFD → 去组合附加符（重音折叠）。
   重音折叠**只用于匹配**，输出保留原文形态。
2. **边界策略按词组区分**（这是关键）：
   - 真品牌名（`ip_marca_global` 等）用**严格边界** ——
     "Nikex" 不是 "Nike"。
   - 仿牌拼写变体（`ip_variante_marca`）用**宽松匹配** ——
     "Addidaspreto" 就是 "Addidas"，严格边界会漏掉最典型的仿牌形态。
   词组级策略由 `lexicon/term_groups.json` 的 `group_meta.matching` 声明。
3. **葡语边界用显式 lookaround** —— 葡语的 `\b` 会吞掉相邻单词首字母
   （如 "Óculos" → "culos"）。
4. **全字段扫描** —— 标题 + 详情 + 属性 + 品牌。标题仅约 6% 命中，
   详情约 94%，只扫标题会漏掉绝大部分。
5. **豁免先于结论** —— 命中后先查 `lexicon/exemptions.json`。
   豁免 ≠ 放行：仍然记录，只是降置信度或转人工复核。
6. **命中必须带位置** —— 记录字段名与偏移，不能只记「命中了」。

用法：
    python3 tools/scan_lexicon.py --title "..." --description "..."
    python3 tools/scan_lexicon.py --input data/samples/xxx.json
    python3 tools/scan_lexicon.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEXICON = os.path.join(ROOT, "lexicon")

# 严格边界：排除相邻字母（葡语用显式字符集，不用 \b）
STRICT = r"(?<![a-zA-Zà-ÿÀ-ß]){body}(?![a-zA-Zà-ÿÀ-ß])"


def norm(text: str) -> str:
    """匹配用归一化：小写 + NFD + 去组合附加符。"""
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


class Scanner:
    def __init__(self, lexicon_dir: str = LEXICON):
        with open(os.path.join(lexicon_dir, "term_groups.json"), encoding="utf-8") as f:
            self.lex = json.load(f)
        with open(os.path.join(lexicon_dir, "exemptions.json"), encoding="utf-8") as f:
            self.exemptions = json.load(f)
        self.groups = self.lex["groups"]
        self.meta = self.lex.get("group_meta", {})
        self._patterns: dict[str, list[tuple[str, re.Pattern]]] = {}
        self._exempt: dict[str, list[tuple[str, re.Pattern, str, str]]] = {}
        self._build()

    # ---------------------------------------------------------------- 构建
    def _build(self):
        for gid, terms in self.groups.items():
            gm = self.meta.get(gid, {})
            mode = gm.get("matching", "strict")
            pats = []
            for t in terms:
                body = re.escape(norm(t))
                pat = (STRICT if mode == "strict" else "{body}").format(body=body)
                pats.append((t, re.compile(pat, re.I)))
            self._patterns[gid] = pats

        for ex in self.exemptions.get("rules", []):
            gid = ex["group_id"]
            self._exempt.setdefault(gid, []).append(
                (ex["id"], re.compile(ex["pattern"], re.I), ex["action"], ex["reason"]))

    # ---------------------------------------------------------------- 扫描
    def scan_text(self, text: str, field: str) -> list[dict]:
        if not text:
            return []
        n = norm(text)
        hits = []
        for gid, pats in self._patterns.items():
            for term, pat in pats:
                m = pat.search(n)
                if not m:
                    continue
                hit = {
                    "group_id": gid,
                    "term": term,
                    "field": field,
                    "offset": m.start(),
                    "matched": m.group(0),
                    "excerpt": _excerpt(text, m.start(), m.end()),
                    "risk_hint": self.meta.get(gid, {}).get("risk_hint"),
                    "source_tier": self.meta.get(gid, {}).get("source_tier"),
                    "confidence": "high",
                    "exempt": None,
                }
                for eid, epat, action, reason in self._exempt.get(gid, []):
                    if epat.search(text):
                        hit["exempt"] = {
                            "id": eid, "action": action, "reason": reason}
                        hit["confidence"] = "low" if action == "exempt" else "medium"
                        break
                hits.append(hit)
        return hits

    def scan_product(self, product: dict) -> list[dict]:
        """全字段扫描：标题 + 详情 + 属性 + 品牌。

        词库只产生**信号**，不产生结论 —— 结论由规则层依据
        `contracts/lexicon_rule_map.json` 与规则来源层级决定。
        """
        hits = []
        for field in ("title", "description", "brand", "category"):
            hits += self.scan_text(product.get(field) or "", field)
        attrs = product.get("attributes") or {}
        if isinstance(attrs, dict):
            for k, v in attrs.items():
                if isinstance(v, str):
                    hits += self.scan_text(v, f"attributes.{k}")
        return hits

    def group_hits(self, hits: list[dict]) -> dict[str, int]:
        out: dict[str, int] = {}
        for h in hits:
            out[h["group_id"]] = out.get(h["group_id"], 0) + 1
        return out


def _excerpt(text: str, start: int, end: int, pad: int = 40) -> str:
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)
    return ("…" if lo > 0 else "") + text[lo:hi].replace("\n", " ") + \
           ("…" if hi < len(text) else "")


# ---------------------------------------------------------------- 自测
SELF_TEST = [
    # (文本, 期望命中的组, 期望不命中的组)
    ("Tênis Nike Air Max para corrida", "ip_marca_global", None),
    ("vape juice de nicotina sabor mango", "proibido_tabaco", None),
    ("garantido 100% eficaz na limpeza", "proibido_garantia", None),
    ("redutor de medidas para Fitness", "claim_beleza", None),
    # 粘连仿牌 —— 宽松组必须命中
    ("Addidaspreto originals", "ip_variante_marca", None),
    ("Rolecx旗舰店", "ip_variante_marca", None),
    # 严格组：边界外的拼接不算命中
    ("Nikex informado", None, "ip_marca_global"),
    # 葡语边界：\b 会吞 Óculos 首字母，显式边界不能
    ("Óculos para visão", None, "ip_marca_global"),
    # 豁免：工具类
    ("Faca de cozinha profissional em aço", None, "proibido_armas"),
    # 豁免：功能描述
    ("Kit para reduzir a entrada de água", None, "proibido_garantia"),
    # 合法的兼容性描述（仍命中品牌组，但应记为需复核）
    ("Compatível com Samsung Galaxy S21", "ip_marca_global", None),
]


def self_test() -> int:
    sc = Scanner()
    fails = 0
    print(f"{'期望':6} {'实际':6} 文本")
    for text, want, unwanted in SELF_TEST:
        hits = sc.scan_text(text, "test")
        groups = {h["group_id"] for h in hits}
        ok = True
        if want and want not in groups:
            ok = False
        if unwanted and unwanted in groups:
            ok = False
        status = "ok" if ok else "FAIL"
        if not ok:
            fails += 1
        mark = "命中" if want else "不命中"
        print(f"  {status:5} {mark:6} {text[:44]:46} → {sorted(groups) or '无'}")

    # 位置记录
    h = sc.scan_text("Tênis Nike Air Max", "title")
    if h and h[0]["offset"] >= 0 and h[0]["excerpt"]:
        print(f"\n  ok   位置记录: offset={h[0]['offset']} excerpt={h[0]['excerpt'][:40]!r}")
    else:
        print("\n  FAIL 位置记录缺失")
        fails += 1

    print(f"\n自测: {len(SELF_TEST) + 1 - fails}/{len(SELF_TEST) + 1} 通过")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description="词库扫描器")
    ap.add_argument("--title")
    ap.add_argument("--description")
    ap.add_argument("--brand")
    ap.add_argument("--input", help="商品 JSON 文件")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    sc = Scanner()
    if args.input:
        with open(args.input, encoding="utf-8") as f:
            data = json.load(f)
        products = data if isinstance(data, list) else data.get("products", [data])
        for p in products:
            hits = sc.scan_product(p)
            print(f"{p.get('product_id', '?')}: {len(hits)} 命中 {sc.group_hits(hits)}")
        return 0

    product = {"title": args.title or "", "description": args.description or "",
               "brand": args.brand or ""}
    hits = sc.scan_product(product)
    for h in sorted(hits, key=lambda x: (x["field"], x["offset"])):
        ex = f"  [豁免 {h['exempt']['id']}]" if h["exempt"] else ""
        print(f"  {h['field']:12} {h['group_id']:22} {h['term'][:28]:30}{ex}")
    print(f"\n共 {len(hits)} 命中")
    return 0


if __name__ == "__main__":
    sys.exit(main())
