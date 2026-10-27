#!/usr/bin/env python3
"""Parse the Shopee BR violation-code catalogue into structured JSON.

Source: "Principais Motivos de Banimento e Suspensão de Anúncios"
(https://seller.br.shopee.cn/edu/article/5139), captured to
research/raw/shopee_br_banimento_suspensao_anuncios.txt.

The page lists each enforcement reason as::

    [NNN] <description>
    Severidade: Alta|Média|Baixa|Extrema
    Gera ponto de penalidade. ...      (or)  Não gera ponto de penalidade. ...

Some codes appear more than once with different severities (e.g. [311] for
tobacco accessories vs. vapes). We keep every occurrence as a separate
entry, distinguished by `code` + `description`.

Output: research/violation_codes.json
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "research", "raw",
                   "shopee_br_banimento_suspensao_anuncios.txt")
OUT = os.path.join(ROOT, "research", "violation_codes.json")
SOURCE_URL = "https://seller.br.shopee.cn/edu/article/5139"

SEV_MAP = {
    "baixa": "low",
    "média": "medium",
    "media": "medium",
    "alta": "high",
    "extrema": "critical",
}

# Category assignment per code. Codes are grouped by the platform's own
# topic headings; where the page does not group them explicitly we map by
# the code's own wording. `None` means "not classified".
CODE_CATEGORY = {
    100: "regulator_prohibited", 101: "regulator_policy_change",
    108: "prohibited_restricted_policy", 117: "regulator_policy_change",
    118: "regulator_policy_change", 122: "regulator_prohibited",
    123: "regulator_prohibited", 124: "regulator_prohibited",
    125: "regulator_prohibited", 126: "regulator_prohibited",
    132: "regulator_prohibited", 135: "regulator_prohibited",
    311: "prohibited_restricted_policy", 312: "prohibited_restricted_policy",
    313: "prohibited_restricted_policy", 315: "prohibited_restricted_policy",
    316: "prohibited_restricted_policy", 317: "prohibited_restricted_policy",
    318: "prohibited_restricted_policy", 320: "prohibited_restricted_policy",
    323: "prohibited_restricted_policy", 324: "prohibited_restricted_policy",
    325: "prohibited_restricted_policy", 326: "prohibited_restricted_policy",
    327: "prohibited_restricted_policy", 328: "prohibited_restricted_policy",
    330: "listing_violation", 331: "prohibited_restricted_policy",
    332: "prohibited_restricted_policy", 333: "prohibited_restricted_policy",
    334: "prohibited_restricted_policy", 335: "prohibited_restricted_policy",
    336: "prohibited_restricted_policy", 337: "listing_violation",
    338: "prohibited_restricted_policy", 339: "prohibited_restricted_policy",
    340: "prohibited_restricted_policy", 341: "prohibited_restricted_policy",
    342: "prohibited_restricted_policy", 343: "prohibited_restricted_policy",
    344: "prohibited_restricted_policy", 345: "prohibited_restricted_policy",
    346: "prohibited_restricted_policy", 347: "prohibited_restricted_policy",
    348: "prohibited_restricted_policy", 349: "ip_trademark",
    508: "listing_violation", 509: "listing_violation",
    512: "listing_violation", 516: "prohibited_restricted_policy",
    517: "listing_violation", 611: "listing_violation",
    110: "listing_violation", 130: "listing_violation",
    133: "ip_trademark", 138: "listing_violation",
    205: "ip_trademark", 401: "duplicate_listing",
    501: "listing_violation", 601: "ip_trademark",
    602: "ip_copyright", 603: "ip_design", 604: "ip_trademark",
    103: "fulfillment", 112: "listing_violation",
    115: "listing_violation", 136: "listing_violation",
    300: "listing_violation", 306: "listing_violation",
    309: "listing_violation", 403: "listing_violation",
    404: "listing_violation", 405: "listing_violation",
    506: "listing_violation", 507: "listing_violation",
    511: "listing_violation", 105: "listing_violation",
    106: "listing_violation", 109: "listing_violation",
    113: "listing_violation", 116: "listing_violation",
    120: "listing_violation", 121: "listing_violation",
    301: "listing_violation", 302: "duplicate_listing",
    307: "listing_violation", 500: "listing_violation",
    503: "regulator_prohibited", 504: "regulator_prohibited",
    505: "regulator_prohibited", 510: "listing_violation",
    515: "ip_trademark", 605: "listing_violation",
    606: "listing_violation", 607: "listing_violation",
    608: "ip_trademark", 612: "listing_violation",
    613: "listing_violation",
}


def parse():
    if not os.path.exists(SRC):
        sys.exit(f"source not found: {SRC}")
    text = open(SRC, encoding="utf-8").read()
    idx = text.find("Motivos de Banimento e Códigos")
    if idx < 0:
        sys.exit("section header not found in source")
    seg = text[idx:]
    lines = [l.strip() for l in seg.split("\n") if l.strip()]

    entries = []
    cur = None
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^\[(\d+)\]\s*(.+)$", line)
        if m:
            if cur:
                entries.append(cur)
            cur = {
                "code": int(m.group(1)),
                "description": m.group(2).strip(),
                "severity_pt": None,
                "severity": None,
                "generates_penalty_point": None,
                "penalty_note": None,
            }
            i += 1
            continue
        if cur is not None:
            sm = re.match(r"^Severidade:\s*(.+)$", line)
            if sm:
                cur["severity_pt"] = sm.group(1).strip()
                cur["severity"] = SEV_MAP.get(
                    cur["severity_pt"].strip().lower(), "medium")
                i += 1
                continue
            if line.startswith("Gera ponto de penalidade"):
                cur["generates_penalty_point"] = True
                cur["penalty_note"] = line
                i += 1
                continue
            if line.startswith("Não gera ponto de penalidade"):
                cur["generates_penalty_point"] = False
                cur["penalty_note"] = line
                i += 1
                continue
        i += 1
    if cur:
        entries.append(cur)

    # Dedup identical (code, description) pairs, keep first.
    seen = set()
    out = []
    for e in entries:
        key = (e["code"], e["description"])
        if key in seen:
            continue
        seen.add(key)
        e["category"] = CODE_CATEGORY.get(e["code"], "listing_violation")
        e["platform_code"] = f"[{e['code']}]"
        out.append(e)
    return out


def main():
    entries = parse()
    doc = {
        "source_title": "Principais Motivos de Banimento e Suspensão de Anúncios",
        "source_url": SOURCE_URL,
        "source_tier": "platform_official",
        "source_file": os.path.relpath(SRC, ROOT),
        "note": (
            "Severities and penalty-point behaviour are quoted from the platform "
            "page as fetched. Codes appearing multiple times with different "
            "severities are distinct entries (different underlying reasons)."
        ),
        "code_count": len(entries),
        "codes": entries,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT} with {len(entries)} violation codes")
    cats = {}
    for e in entries:
        cats[e["category"]] = cats.get(e["category"], 0) + 1
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")


if __name__ == "__main__":
    main()
