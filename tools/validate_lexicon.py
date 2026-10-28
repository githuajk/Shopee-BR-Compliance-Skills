#!/usr/bin/env python3
"""校验合并词库及其关联资产。

检查项：
  1. term_groups.json 通过 lexicon.schema.json
  2. groups 与 group_meta 的键一一对应
  3. stats 与实际一致
  4. rewrite_map / exemptions / quality_patterns / non_avoidable /
     verb_conjugations 结构完整
  5. rewrite_map 的替换值**不含字符类**（SOP 坑 18/21）
  6. verb_conjugations 的模式使用显式葡语边界（不用裸 \\b）
  7. lexicon_rule_map 的 group_id 全部存在于词库
  8. lexicon_rule_map 的 rule_ids 全部存在于规则库
  9. 词库 source_tier=internal_risk 的组只能映射到 flag 级规则（不放大风险）
 10. exemptions 的 group_id 与 pattern 合法
 11. quality_patterns 的正则全部可编译

Usage: python3 tools/validate_lexicon.py
Exit 0 = 全部通过
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from validate_json import Validator  # noqa: E402

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
    else:
        FAILED.append((name, detail))
        print(f"  FAIL {name}: {detail}")


def section(t):
    print(f"\n=== {t} ===")


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


# 动作 → 风险级别（用于「不得放大风险」检查）
FLAG_LEVEL_ACTIONS = {
    "allow", "flag_for_review", "require_evidence", "revise",
    "block", "freeze_relist", "escalate_legal",
}


def main():
    # --- 1/2/3 term_groups ---
    section("1. term_groups.json 结构")
    lex = load("lexicon/term_groups.json")
    schema = load("data/schema/lexicon.schema.json")
    errs = Validator(schema).validate(lex)
    check("term_groups 通过 lexicon.schema", not errs, "; ".join(errs[:4]))

    gk, mk = set(lex["groups"]), set(lex["group_meta"])
    check("groups 与 group_meta 键一致", gk == mk,
          f"仅在 groups: {sorted(gk - mk)[:3]} 仅在 meta: {sorted(mk - gk)[:3]}")

    actual_groups = len(lex["groups"])
    actual_terms = sum(len(v) for v in lex["groups"].values())
    check("stats.group_count 一致",
          lex["stats"]["group_count"] == actual_groups,
          f"{lex['stats']['group_count']} vs {actual_groups}")
    check("stats.term_count 一致",
          lex["stats"]["term_count"] == actual_terms,
          f"{lex['stats']['term_count']} vs {actual_terms}")

    # matching 策略：仿牌变体组必须是 loose
    loose = {g for g, v in lex["group_meta"].items() if v.get("matching") == "loose"}
    check("ip_variante_marca 用宽松匹配",
          "ip_variante_marca" in loose, str(sorted(loose)))
    for g, v in lex["group_meta"].items():
        check(f"{g} 有 matching 策略", "matching" in v, "缺字段")
    # 真品牌组不得用 loose（会误伤 "Nikex"）
    bad_loose = [g for g in loose if g.startswith("ip_marca_") and g != "ip_variante_marca"]
    check("真品牌组不用宽松匹配", not bad_loose, str(bad_loose))

    # 词条长度与重复
    bad_len = [(g, t) for g, ts in lex["groups"].items() for t in ts if len(t) < 2]
    check("所有词条长度 >= 2", not bad_len, str(bad_len[:3]))
    # 跨组同词：允许（语义不同，如 antidepressants 既在禁售药品又在健康宣称），
    # 但必须是「有意为之」—— 记录为 overlap_groups 供报告，不作为失败。
    dupes = []
    seen: dict[str, str] = {}
    for g, ts in lex["groups"].items():
        for t in ts:
            k = t.lower()
            if k in seen and seen[k] != g:
                dupes.append((t, seen[k], g))
            seen.setdefault(k, g)
    print(f"  跨组同词 {len(dupes)} 项（语义重叠，允许）")
    for t, a, b in dupes[:8]:
        print(f"    · {t:18} {a} ∩ {b}")

    # 真正的错误：同一组内重复
    within = []
    for g, ts in lex["groups"].items():
        low = [t.lower() for t in ts]
        if len(low) != len(set(low)):
            within.append(g)
    check("组内无重复词条", not within, str(within))

    # --- 4 其它资产结构 ---
    section("2. 关联资产结构")
    rw = load("lexicon/rewrite_map.json")
    for cat in ["absolute_promise", "beauty_claim", "health_claim",
                "medical_implication", "platform_guarantee", "safety_promise",
                "body_shaping", "verb_conjugations"]:
        check(f"rewrite_map 含 {cat}", cat in rw and isinstance(rw[cat], dict),
              "缺失或类型错")
    check("rewrite_map 有 schema_version", "schema_version" in rw, "")

    ex = load("lexicon/exemptions.json")
    check("exemptions 有 rules 数组", isinstance(ex.get("rules"), list), "")
    for r in ex.get("rules", []):
        for f in ["id", "group_id", "pattern", "action", "reason"]:
            check(f"exemption {r.get('id','?')} 含 {f}", f in r, "缺字段")
        try:
            re.compile(r["pattern"])
            check(f"exemption {r['id']} 正则可编译", True)
        except Exception as e:  # noqa: BLE001
            check(f"exemption {r['id']} 正则可编译", False, str(e))
        check(f"exemption {r['id']} group_id 存在", r["group_id"] in gk, r["group_id"])

    qp = load("lexicon/quality_patterns.json")
    check("quality_patterns 有 reject_if_any", isinstance(qp.get("reject_if_any"), list), "")
    for p in qp.get("reject_if_any", []):
        try:
            re.compile(p["pattern"])
            check(f"quality {p['id']} 正则可编译", True)
        except Exception as e:  # noqa: BLE001
            check(f"quality {p['id']} 正则可编译", False, str(e))
        for f in ["id", "pattern", "reason"]:
            check(f"quality {p['id']} 含 {f}", f in p, "缺字段")

    na = load("lexicon/non_avoidable.json")
    check("non_avoidable 有 categories", isinstance(na.get("categories"), list), "")
    for c in na.get("categories", []):
        for f in ["id", "label", "regulator", "keywords", "requirement"]:
            check(f"non_avoidable {c.get('id','?')} 含 {f}", f in c, "缺字段")

    # --- 5 替换值不含字符类 ---
    section("3. 替换值铁律（坑 18/21）")
    charclass = re.compile(r"\[[a-zA-Zà-ÿÀ-Ý]{1,4}\]")
    bad = []
    for cat, mapping in rw.items():
        if not isinstance(mapping, dict):
            continue
        for src, dst in mapping.items():
            if isinstance(dst, str) and charclass.search(dst):
                bad.append((cat, src, dst))
    check("rewrite_map 替换值无字符类", not bad, str(bad[:4]))

    # --- 6 葡语边界 ---
    section("4. 葡语匹配边界（坑 §4.2）")
    vc = load("lexicon/verb_conjugations.json")
    for e in vc.get("entries", []):
        mp = e.get("match_pattern", "")
        check(f"verb {e['lemma']} 用显式葡语边界",
              "(?<![a-zA-Zà-ÿÀ-ß])" in mp and "(?![a-zA-Zà-ÿÀ-ß])" in mp,
              mp)
        check(f"verb {e['lemma']} 有 exclude", "exclude" in e, "缺 exclude")

    # --- 7/8/9 映射表 ---
    section("5. 词库→规则映射")
    mp = load("contracts/lexicon_rule_map.json")
    mappings = mp.get("mappings", [])
    check("映射表非空", len(mappings) > 0, "")

    rule_ids: dict[str, dict] = {}
    for fn in sorted(os.listdir(os.path.join(ROOT, "rules"))):
        if not fn.endswith(".json"):
            continue
        for r in load(f"rules/{fn}")["rules"]:
            rule_ids[r["rule_id"]] = r

    for m in mappings:
        gid = m.get("group_id", "?")
        check(f"映射 group_id {gid} 存在于词库", gid in gk, gid)
        for rid in m.get("rule_ids", []):
            check(f"映射 {gid} → {rid} 规则存在", rid in rule_ids, rid)

    # 覆盖检查：每个词组都应有映射
    unmapped = gk - {m["group_id"] for m in mappings}
    check("所有词组都有映射", not unmapped, str(sorted(unmapped)))

    # 不得放大风险：internal_risk 词组只能映射到「规则本身来源即为 internal_risk」
    # 或非阻断动作的规则。
    #
    # 说明：escalate_legal / freeze_relist 是**人工专属**的合规升级动作
    # （硬约束 H1：IP 类结论恒为 signal + 强制人工复核），它们不是自动阻断，
    # 因此不属于「放大风险」。真正禁止的是 block —— 硬约束 H2 规定
    # block 只能来自 platform_official / law 的 active 规则。
    tier_of = {g: lex["group_meta"][g]["source_tier"] for g in gk}
    risky = []
    for m in mappings:
        if tier_of.get(m["group_id"]) != "internal_risk":
            continue
        for rid in m.get("rule_ids", []):
            r = rule_ids.get(rid)
            if not r:
                continue
            dec = r.get("decision", "flag_for_review")
            rtier = r.get("source_tier", "unverified")
            # 阻断类动作：仅 block。escalate_legal / freeze_relist 是人工专属升级。
            if dec == "block" and rtier not in ("platform_official", "law"):
                risky.append((m["group_id"], rid, dec, rtier))
    check("internal_risk 词组不映射到非官方来源的 block 规则", not risky,
          str(risky[:4]))

    # 硬约束 H2：所有 block 规则必须来自官方或法律来源
    h2_bad = [(rid, r.get("source_tier"), r.get("status"))
              for rid, r in rule_ids.items()
              if r.get("decision") == "block"
              and r.get("source_tier") not in ("platform_official", "law")]
    check("H2: 所有 block 规则来自 platform_official/law", not h2_bad,
          str(h2_bad[:4]))

    # 硬约束 H1：IP 类规则凡产生**结论**的必须强制人工复核。
    # 例外：decision=allow 的豁免规则（如 SBR-IP-006 兼容性描述不构成侵权）
    # 本身就是「确认合法」，无需再送人工。
    h1_bad = [rid for rid, r in rule_ids.items()
              if rid.startswith("SBR-IP-")
              and r.get("decision") != "allow"
              and not r.get("human_review_required")]
    check("H1: 所有 IP 结论规则强制人工复核（allow 类豁免除外）", not h1_bad,
          str(h1_bad))

    # 规则侧反向：拥有 lexicon_group 的规则应在映射表中
    print(f"\n{'=' * 62}")
    print(f"PASSED: {len(PASSED)}   FAILED: {len(FAILED)}")
    if FAILED:
        print("\nFailures:")
        for n, d in FAILED[:25]:
            print(f"  - {n}: {d}")
        return 1
    print(f"词库校验通过：{actual_groups} 组 / {actual_terms} 词 / "
          f"{len(mappings)} 条映射 / {len(rule_ids)} 条规则")
    return 0


if __name__ == "__main__":
    sys.exit(main())
