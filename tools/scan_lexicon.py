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
3. **葡语边界用显式 lookaround** —— 葡语的 `\\b` 会吞掉相邻单词首字母
   （如 "Óculos" → "culos"）。
4. **全字段扫描** —— 标题 + 详情 + 属性 + 品牌。标题仅约 6% 命中，
   详情约 94%，只扫标题会漏掉绝大部分。
5. **豁免先于结论** —— 命中后先查 `lexicon/exemptions.json`。
   豁免 ≠ 放行：仍然记录，只是降置信度或转人工复核。
6. **命中必须带位置** —— 记录字段名与偏移，不能只记「命中了」。

已登记缺陷修复（data-ingestion 2026-10-28 交付 §3.1，本模块所有）：

- **D1 豁免作用域**：豁免只作用于「豁免区间与命中区间重叠」的命中，
  不再因全文任一位置匹配就把整组命中全量降级。`EX-CATALOG-*` 的
  全文 `pattern`（`[\\s\\S]*`）区间覆盖全文，目录组全组降级的既定
  行为保持。
- **D2/D6 同词多次只报一次**：改为逐词条报告**全部**出现（等价
  `re.finditer` 语义，按词去重叠），offset 各次互不相同。
- **D3 offset 错位**：归一化去重音改变长度，原实现直接拿归一化偏移
  回切原文导致 excerpt 整体偏移。现按「归一化字符 → 原文下标」映射
  表把偏移/`matched`/`excerpt` 全部换算回原文坐标。
- **D4 豁免正则不做重音折叠 + 裸 `\\b`**：豁免正则现在作用于
  **归一化文本**（小写 + 去重音）。归一化文本是纯 ASCII 形态，其中
  的 `\\b` 等价于显式词边界，不再吞相邻重音字母 —— 葡语原文上的
  显式 lookaround 铁律（SOP §4.2）在归一化层仍然成立。
- **D5 豁免正则含换行即失效**：豁免匹配前把归一化文本的 `\\n`/`\\r`
  压平成空格（等长替换，偏移不变），`^...$` 类锚定模式不再被多行
  文本绕开。EX-BRAND-GENERIC 的「同一无关通用词同行即全组降级」
  残留需改 `lexicon/exemptions.json` 的 pattern（data-ingestion 所有），
  已按契约流程登记为待改数据变更，本实现只保证「区间重叠」边界。
- **性能**：不再为 21 万词条逐条 `re.compile`（旧实现构造 37–70s）。
  构造期只做一次归一化 + 前缀索引（纯标准库）；匹配期用 C 级
  `str.find` 逐词条定位。索引按（目录, mtime）缓存于模块级，同一进程
  内重复构造 `Scanner` 是 O(1)。

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
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEXICON = os.path.join(ROOT, "lexicon")

# 严格边界的语义参照（SOP §4.2）：
STRICT = r"(?<![a-zA-Zà-ÿÀ-ß]){body}(?![a-zA-Zà-ÿÀ-ß])"

# 与 STRICT 环视字符集等价、作用于**归一化文本**的边界字符集。
# 归一化后文本里没有大写与组合附加符，集合退化为 ASCII 小写字母 +
# 少量不被 NFD 折叠的非 ASCII 字母（ß/ð/þ 等）。数字不构成边界阻挡
# （与旧正则的字符类一致：`[a-zA-Zà-ÿÀ-ß]` 不含 0-9）。
_BOUNDARY_CHARS = frozenset(
    [chr(i) for i in range(0x41, 0x5B)]
    + [chr(i) for i in range(0x61, 0x7B)]
    + [chr(i) for i in range(0xC0, 0x100)]
)


def norm(text: str) -> str:
    """匹配用归一化：小写 + NFD + 去组合附加符。"""
    nfd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfd if not unicodedata.combining(c))


def norm_with_map(text: str) -> tuple[str, list[int]]:
    """归一化 + 每个归一化字符对应的**原文下标**。

    逐字符等价于整体 `norm()`（小写与 NFD 都是逐字符可组合的），
    但额外返回映射表 `omap`：`norm_with_map(t)[0] == norm(t)`，且
    `omap[i]` 是归一化第 i 个字符所在的原文下标。用它可以把归一化
    偏移换回原文坐标（D3 修复），输出保留原文形态。
    """
    out: list[str] = []
    omap: list[int] = []
    for i, ch in enumerate(text):
        nfd = unicodedata.normalize("NFD", ch.lower())
        for c in nfd:
            if not unicodedata.combining(c):
                out.append(c)
                omap.append(i)
    return "".join(out), omap


# ---------------------------------------------------------------- 索引
class _Index:
    """词库索引（构造一次、进程内共享）。纯标准库。

    按「归一化词条前 2 字符」分桶：匹配期先算文本 bigram 集合，
    跳过前缀不出现的整桶词条，再用 C 级 `str.find` 定位全部出现。
    """

    __slots__ = ("by_pre", "by_pre_count", "total_terms", "total_norm_chars")

    def __init__(self, by_pre: dict[str, list], total_terms: int,
                 total_norm_chars: int):
        self.by_pre = by_pre
        self.by_pre_count = len(by_pre)
        self.total_terms = total_terms
        self.total_norm_chars = total_norm_chars


def _build_index(groups: dict, meta: dict) -> _Index:
    by_pre: dict[str, list] = {}
    seen: set = set()
    total_terms = 0
    total_norm_chars = 0
    for gid, terms in groups.items():
        mode = meta.get(gid, {}).get("matching", "strict")
        for t in terms:
            key = norm(t)
            if not key:
                continue
            ident = (gid, key, t)
            if ident in seen:
                continue
            seen.add(ident)
            total_terms += 1
            total_norm_chars += len(key)
            # 前 3 字符分桶（L=2 时前缀即全词）：长文本中任意 3-gram
            # 集合只覆盖极少数桶，绝大多数词条在匹配期被整桶跳过。
            by_pre.setdefault(key[:3], []).append(
                (key, len(key), gid, t, mode))
    for entries in by_pre.values():
        entries.sort(key=lambda e: e[1])
    return _Index(by_pre, total_terms, total_norm_chars)


# ---------------------------------------------------------------- 缓存
_SCANNER_CACHE: dict[tuple, "Scanner"] = {}
_CORE_CACHE: dict[tuple, _Index] = {}


def _cache_key(lexicon_dir: str) -> tuple:
    base = os.path.abspath(lexicon_dir)
    mts: list[int] = []
    for name in ("term_groups.json", "exemptions.json"):
        try:
            mts.append(os.stat(os.path.join(base, name)).st_mtime_ns)
        except OSError:
            mts.append(-1)
    return (base, tuple(mts))


def _load_docs(lexicon_dir: str) -> tuple[dict, dict]:
    with open(os.path.join(lexicon_dir, "term_groups.json"),
              encoding="utf-8") as f:
        lex = json.load(f)
    with open(os.path.join(lexicon_dir, "exemptions.json"),
              encoding="utf-8") as f:
        exdoc = json.load(f)
    return lex, exdoc


def _get_index(lexicon_dir: str) -> _Index:
    ck = _cache_key(lexicon_dir)
    idx = _CORE_CACHE.get(ck)
    if idx is None:
        lex, _ = _load_docs(lexicon_dir)
        idx = _build_index(lex["groups"], lex.get("group_meta", {}))
        _CORE_CACHE[ck] = idx
    return idx


class Scanner:
    def __init__(self, lexicon_dir: str = LEXICON, rebuild: bool = False):
        """构造扫描器。

        同一词库目录（且文件 mtime 未变）下重复构造是 O(1)：索引与
        豁免编译结果缓存在模块级。`rebuild=True` 强制重建（测试用）。
        """
        ck = _cache_key(lexicon_dir)
        if not rebuild:
            hit = _SCANNER_CACHE.get(ck)
            if hit is not None:
                self.__dict__.update(hit.__dict__)
                return
        lex, exdoc = _load_docs(lexicon_dir)
        self.lexicon_dir = lexicon_dir
        self.lex = lex
        self.exemptions = exdoc
        self.groups = lex["groups"]
        self.meta = lex.get("group_meta", {})
        self.index = _get_index(lexicon_dir) if not rebuild else (
            _build_index(self.groups, self.meta))
        # 宽松组集合（loose 模式：裸子串，不加边界）
        self.loose: set[str] = {
            gid for gid, terms in self.groups.items()
            if self.meta.get(gid, {}).get("matching", "strict") != "strict"
        }
        # 豁免：组 → [(id, 编译后的正则, action, reason)]
        self._exempt: dict[str, list[tuple[str, re.Pattern, str, str]]] = {}
        for ex in exdoc.get("rules", []):
            gid = ex["group_id"]
            self._exempt.setdefault(gid, []).append(
                (ex["id"], re.compile(ex["pattern"], re.I),
                 ex.get("action", "exempt"), ex.get("reason", "")))
        _SCANNER_CACHE[ck] = self

    # ---------------------------------------------------------------- 扫描
    def scan_text(self, text: str, field: str) -> list[dict]:
        if not text:
            return []
        n, omap = norm_with_map(text)
        Ln = len(n)
        # D5：豁免匹配前把换行压平成空格（等长替换，偏移不变）。
        nf = n.replace("\n", " ").replace("\r", " ")

        # --- 收集全部出现（等价逐词条 re.finditer，按词去重叠）---
        # 前缀预筛：词条按前 3 字符分桶；文本只会出现极少数 3-gram，
        # 不出现的桶整桶跳过（匹配期成本与文本长度近似无关）。
        t3 = frozenset(n[i:i + 3] for i in range(Ln - 2))
        occ: dict[tuple[str, str, int], list[int]] = {}
        for pre, entries in self.index.by_pre.items():
            if pre not in t3:
                continue
            for key, L, gid, term, _mode in entries:
                if L > Ln:
                    break
                i = n.find(key)
                while i != -1:
                    occ.setdefault((gid, term, L), []).append(i)
                    i = n.find(key, i + L)
        if not occ:
            return []

        # --- 边界过滤 + 原文坐标换算（D2/D6/D3）---
        hits: list[dict] = []
        bchars = _BOUNDARY_CHARS
        for (gid, term, L), starts in occ.items():
            strict = gid not in self.loose
            last_end = 0
            for p in starts:  # 升序
                if p < last_end:
                    continue
                if strict:
                    if (p > 0 and n[p - 1] in bchars) or \
                       (p + L < Ln and n[p + L] in bchars):
                        continue
                last_end = p + L
                o_start = omap[p]
                o_end = omap[p + L - 1] + 1
                gm = self.meta.get(gid, {})
                hits.append({
                    "group_id": gid,
                    "term": term,
                    "field": field,
                    "offset": o_start,
                    "matched": text[o_start:o_end],
                    "excerpt": _excerpt(text, o_start, o_end),
                    "risk_hint": gm.get("risk_hint"),
                    "source_tier": gm.get("source_tier"),
                    "confidence": "high",
                    "exempt": None,
                    "_np": p, "_nL": L,
                })

        # --- 豁免（D1/D4/D5）：匹配归一化文本，仅豁免区间重叠的命中 ---
        if self._exempt and hits:
            by_gid: dict[str, list[dict]] = {}
            for h in hits:
                by_gid.setdefault(h["group_id"], []).append(h)
            for gid, ghits in by_gid.items():
                pats = self._exempt.get(gid)
                if not pats:
                    continue
                span_lists: list[tuple[str, str, str, list]] = []
                for eid, epat, action, reason in pats:
                    spans = [m.span() for m in epat.finditer(nf)]
                    span_lists.append((eid, action, reason, spans))
                for h in ghits:
                    lo = h.pop("_np")
                    nl = h.pop("_nL")
                    hi = lo + nl
                    for eid, action, reason, spans in span_lists:
                        if any(ms < hi and me > lo for ms, me in spans):
                            h["exempt"] = {
                                "id": eid, "action": action,
                                "reason": reason}
                            h["confidence"] = ("low" if action == "exempt"
                                               else "medium")
                            break
        for h in hits:
            h.pop("_np", None)
            h.pop("_nL", None)

        gpos = {g: i for i, g in enumerate(self.groups)}
        hits.sort(key=lambda h: (gpos.get(h["group_id"], 0), h["offset"]))
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

# 已登记缺陷 D1–D6 的回归用例（DELIVERY_lexicon_expansion_20261028 §3.1）。
# 仅作缺陷→测试文本的对照说明；实际断言与计数在 `_defect_checks` 中
# （D2/D6 同根因，合并为「同词多次全部报告」一条）。
DEFECT_CHECKS: list[tuple[str, str]] = [
    ("D1 无关武器命中不被 EX-TOOLS 全组豁免",
     "pistola e faca de cozinha"),
    ("D1 工具词重叠的命中才豁免",
     "facas e lâminas cujo área de corte tenha mais que 30 centímetros"),
    ("D2 同词 5 次出现全报",
     "garantido garantido garantido garantido garantido"),
    ("D3 重音文本 offset 回切原文",
     "Tênis NÍKE"),
    ("D4 豁免正则在重音折叠文本上匹配",
     "Logística Hermes"),
    ("D5 多行文本不再使 ^...$ 豁免失效",
     "Nike\ncase para celular"),
]


def _defect_checks(sc: Scanner) -> tuple[int, int]:
    """D1–D5 回归断言。返回 (失败数, 实际断言数)。"""
    fails = 0
    total = 0

    def chk(name: str, cond: bool, detail: str = "") -> None:
        nonlocal fails, total
        total += 1
        print(f"  {'ok  ' if cond else 'FAIL'} {name}"
              + (f"（{detail}）" if detail and not cond else ""))
        if not cond:
            fails += 1

    # D1：豁免只豁免「区间重叠」的命中
    hits = sc.scan_text("pistola e faca de cozinha", "test")
    armas = {h["term"]: h for h in hits if h["group_id"] == "proibido_armas"}
    chk("D1 pistola 不被 EX-TOOLS 连带豁免",
        "pistola" in armas and armas["pistola"]["exempt"] is None
        and armas["pistola"]["confidence"] == "high",
        str(armas.get("pistola")))
    hits = sc.scan_text(
        "facas e lâminas cujo área de corte tenha mais que 30 centímetros",
        "test")
    long_hit = next((h for h in hits
                     if h["group_id"] == "proibido_armas"
                     and h["term"].startswith("facas e")), None)
    chk("D1 工具词覆盖的命中被 EX-TOOLS 豁免",
        long_hit is not None
        and (long_hit["exempt"] or {}).get("id") == "EX-TOOLS",
        str(long_hit))

    # D2/D6：同词多次出现逐一报告，offset 互不相同
    hits = sc.scan_text(
        "garantido garantido garantido garantido garantido", "test")
    g5 = [h for h in hits if h["term"] == "garantido"]
    chk("D2/D6 同词 5 次全部报告", len(g5) == 5, f"got {len(g5)}")
    chk("D2/D6 各次 offset 互不相同",
        len({h["offset"] for h in g5}) == 5,
        str([h["offset"] for h in g5]))

    # D3：重音文本 —— offset/matched 回切原文
    text = "Tênis NÍKE"
    h = next((x for x in sc.scan_text(text, "test")
              if x["term"].lower() == "nike"), None)
    chk("D3 offset 指向原文 NÍKE",
        h is not None and h["offset"] == text.find("NÍKE")
        and h["matched"] == "NÍKE",
        str(h))

    # D4：豁免正则做重音折叠（归一化匹配）
    h = next((x for x in sc.scan_text("Logística Hermes", "test")
              if x["term"].lower() == "hermes"), None)
    chk("D4 logística（带重音）触发 EX-HERMES-CARRIER",
        h is not None and (h["exempt"] or {}).get("id")
        == "EX-HERMES-CARRIER", str(h))

    # D5：换行压平后 ^...$ 豁免不再失效（区间重叠语义）
    h = next((x for x in sc.scan_text("Nike\ncase para celular", "test")
              if x["term"].lower() == "nike"), None)
    chk("D5 多行文本 EX-BRAND-GENERIC 生效",
        h is not None and (h["exempt"] or {}).get("id")
        == "EX-BRAND-GENERIC", str(h))

    # 目录组全组降级（EX-CATALOG-*) 的既定行为保持
    h = next((x for x in sc.scan_text("Amoxicilina 500mg", "test")
              if x["group_id"].startswith("catalog_")), None)
    chk("catalog 命中仍带 EX-CATALOG 降级",
        h is not None and h["exempt"] is not None
        and h["exempt"]["id"].startswith("EX-CATALOG"), str(h))
    return fails, total


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

    # 位置记录（D3：原文坐标）
    h = sc.scan_text("Tênis Nike Air Max", "title")
    if h and h[0]["offset"] >= 0 and h[0]["excerpt"]:
        print(f"\n  ok   位置记录: offset={h[0]['offset']} "
              f"excerpt={h[0]['excerpt'][:40]!r}")
    else:
        print("\n  FAIL 位置记录缺失")
        fails += 1

    # 已登记缺陷 D1–D5 回归
    print("\n已登记缺陷回归（DELIVERY_lexicon_expansion_20261028 §3.1）：")
    d_fails, d_total = _defect_checks(sc)
    fails += d_fails

    total = len(SELF_TEST) + 1 + d_total
    print(f"\n自测: {total - fails}/{total} 通过")
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
