#!/usr/bin/env python3
"""Test suite for the Shopee BR compliance agent.

Run:  python3 tests/run_tests.py

Covers:
  * every required scenario from the project brief (TC-01 .. TC-08)
  * rule-library integrity (unique ids, schema validity, authority guard)
  * engine units (Aho-Corasick, Portuguese word boundaries, duplicates, relist)
  * ingest parsers (xlsx round-trip, csv, json, jsonl, error reporting)

No third-party test runner: the Hermes runtime is a managed PEP 668 env, so
the suite is plain asserts with a tiny harness.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from compliance_agent import load_rules  # noqa: E402
from compliance_agent.engine.duplicates import DuplicateIndex  # noqa: E402
from compliance_agent.engine.evaluator import evaluate_product, product_status  # noqa: E402
from compliance_agent.engine.loader import AhoCorasick  # noqa: E402
from compliance_agent.engine.relist import RelistIndex  # noqa: E402
from compliance_agent.engine.reviewer import Reviewer  # noqa: E402
from compliance_agent.ingest.parsers import parse_csv, parse_jsonl, parse_text, parse_xlsx  # noqa: E402
from compliance_agent.models import Case, Product  # noqa: E402
from compliance_agent.report.markdown import render_report  # noqa: E402
from validate_json import Validator  # noqa: E402

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        PASSED.append(name)
    else:
        FAILED.append((name, detail))
        print(f"  FAIL {name}: {detail}")


def section(title: str):
    print(f"\n=== {title} ===")


# --------------------------------------------------------------------------
def product_from_dict(d: dict) -> Product:
    return Product(
        product_id=d["product_id"],
        internal_sku=d.get("internal_sku", d["product_id"]),
        supplier_sku=d.get("supplier_sku"),
        shop_id=d.get("shop_id", "SHOP"),
        shop_name=d.get("shop_name"),
        platform_pid=d.get("platform_pid"),
        title=d.get("title", ""),
        description=d.get("description", ""),
        category=d.get("category"),
        brand=d.get("brand"),
        model=d.get("model"),
        price=d.get("price"),
        images=d.get("images", []),
        variations=d.get("variations", []),
        product_url=d.get("product_url"),
        history=d.get("history", {}),
        source=d.get("source", {"kind": "manual"}),
    )


def case_from_dict(d: dict) -> Case:
    return Case(
        case_id=d["case_id"],
        shop_id=d.get("shop_id", "SHOP"),
        product_ids=d.get("product_ids", []),
        violation_type=d.get("violation_type", ""),
        status=d.get("status", "open"),
        frozen=d.get("frozen", False),
        rule_ids=d.get("rule_ids", []),
        platform_notice=d.get("platform_notice"),
    )


# --------------------------------------------------------------------------
def test_scenarios():
    section("Scenarios (data/samples/test_cases.json)")
    with open(os.path.join(ROOT, "data", "samples", "test_cases.json"),
              encoding="utf-8") as f:
        doc = json.load(f)
    rules = load_rules()

    for tc in doc["cases"]:
        cid = tc["case_id"]
        products = [product_from_dict(p) for p in tc["products"]]
        hist_cases = [case_from_dict(c) for c in tc.get("history_cases", [])]
        hist_products = [product_from_dict(p) for p in tc.get("history_products", [])]

        reviewer = Reviewer(rules, history_products=hist_products, history_cases=hist_cases)
        result = reviewer.review(products, run_id=f"TEST-{cid}")

        exp = tc["expect"]
        rows = result["products"]
        fired = {f["rule_id"] for f in result["findings"]}

        if exp.get("product_status"):
            got = {r["status"] for r in rows}
            check(f"{cid} status == {exp['product_status']}",
                  exp["product_status"] in got,
                  f"got {sorted(got)}")
        if exp.get("min_findings") is not None:
            check(f"{cid} min_findings >= {exp['min_findings']}",
                  len(result["findings"]) >= exp["min_findings"],
                  f"got {len(result['findings'])}")
        for rid in exp.get("must_include_rules", []):
            check(f"{cid} includes {rid}", rid in fired, f"fired={sorted(fired)}")
        for rid in exp.get("must_not_include_rules", []):
            check(f"{cid} excludes {rid}", rid not in fired, f"fired={sorted(fired)}")
        # a report must always render
        md = render_report(result, {r.rule_id: r for r in rules})
        check(f"{cid} report renders", len(md) > 500, f"len={len(md)}")


# --------------------------------------------------------------------------
def test_rule_library():
    section("Rule library integrity")
    rules = load_rules()
    ids = [r.rule_id for r in rules]
    check("rule ids unique", len(ids) == len(set(ids)),
          f"dupes: {[i for i in set(ids) if ids.count(i) > 1]}")
    check("rules non-empty", len(rules) > 0, "no rules loaded")
    for r in rules:
        check(f"{r.rule_id} has source_url", bool(r.source_url), "")
        check(f"{r.rule_id} has last_verified", bool(r.last_verified), "")
        check(f"{r.rule_id} version >= 1", r.version >= 1, "")
        check(f"{r.rule_id} source_tier known",
              r.source_tier in ("platform_official", "law", "internal_risk", "unverified"),
              r.source_tier)

    # authority guard: a non-authoritative rule must not block
    from compliance_agent.models import Rule
    weak = Rule(
        rule_id="SBR-TEST-999", title="internal hypothesis", category="internal_risk",
        description="hypothesis", trigger_conditions=[
            {"field": "title", "operator": "contains_any", "value": ["xyzzy"]}],
        severity="critical", decision="block", evidence_required=[],
        human_review_required=True, source_url="https://example.invalid/x",
        last_verified="2026-01-01", status="active", version=1,
        source_tier="internal_risk")
    check("internal_risk rule is not enforceable", not weak.is_enforceable, "")
    p = Product(product_id="PROD-0001", internal_sku="S1", shop_id="X", title="xyzzy item")
    fs = evaluate_product(p, [weak])
    check("internal_risk rule cannot block", fs and fs[0].decision == "flag_for_review",
          f"decision={fs[0].decision if fs else None}")

    # a draft rule must not block
    draft = Rule(
        rule_id="SBR-TEST-998", title="draft", category="internal_risk",
        description="draft", trigger_conditions=[
            {"field": "title", "operator": "contains_any", "value": ["xyzzy"]}],
        severity="critical", decision="block", evidence_required=[],
        human_review_required=True, source_url="https://example.invalid/x",
        last_verified="2026-01-01", status="draft", version=1,
        source_tier="platform_official")
    fs = evaluate_product(p, [draft])
    check("draft rule cannot block", fs and fs[0].decision == "flag_for_review",
          f"decision={fs[0].decision if fs else None}")

    # IP rules are never 'confirmed' from text matching
    ip_rule = next(r for r in rules if r.rule_id == "SBR-IP-001")
    p2 = Product(product_id="PROD-0002", internal_sku="S2", shop_id="X",
                 title="Tênis Nike Authentic", description="Nike original")
    fs = evaluate_product(p2, [ip_rule])
    check("IP finding confidence is signal, not confirmed",
          fs and fs[0].confidence == "signal", f"conf={fs[0].confidence if fs else None}")
    check("IP finding requires human review",
          bool(fs) and fs[0].human_review_required, "")


def test_schemas():
    section("Schema validation")
    schema_dir = os.path.join(ROOT, "data", "schema")
    with open(os.path.join(schema_dir, "rule.schema.json"), encoding="utf-8") as f:
        rule_schema = json.load(f)
    v = Validator(rule_schema, base_dir=schema_dir)
    rules = load_rules()
    for r in rules:
        d = r.to_dict() if hasattr(r, "to_dict") else None
    # validate raw rule dicts from disk
    for fn in sorted(os.listdir(os.path.join(ROOT, "rules"))):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(ROOT, "rules", fn), encoding="utf-8") as f:
            doc = json.load(f)
        for raw in doc["rules"]:
            errs = v.validate(raw)
            check(f"{raw['rule_id']} matches rule.schema.json", not errs, "; ".join(errs))

    with open(os.path.join(schema_dir, "review_result.schema.json"), encoding="utf-8") as f:
        rr_schema = json.load(f)
    rv = Validator(rr_schema, base_dir=schema_dir)
    reviewer = Reviewer(load_rules())
    p = Product(product_id="PROD-0003", internal_sku="S3", shop_id="X",
                title="Faca de Cozinha em Aço Inox",
                description="Faca de cozinha em aço inox com cabo preto. Comprimento total 25 cm. indications")
    result = reviewer.review([p], run_id="TEST-SCHEMA")
    errs = rv.validate(result)
    check("review result matches review_result.schema.json", not errs, "; ".join(errs))


def test_aho_corasick():
    section("Aho-Corasick scanner")
    ac = AhoCorasick({"prohibited": ["vape", "narguile"], "brand": ["nike", "adidas"]})
    hits = ac.matches_groups("VAPES e pulseiras NIKE no texto")
    check("AC finds 'vape' case-insensitively", "prohibited" in hits, str(hits))
    check("AC finds 'nike' case-insensitively", "brand" in hits, str(hits))
    check("AC match carries an excerpt", bool(hits["brand"][0]["excerpt"]), "")
    ac2 = AhoCorasick({"x": ["abc"]})
    check("AC no false positive", not ac2.matches_groups("abd"), "")


def test_portuguese_boundaries():
    section("Portuguese word-boundary safety")
    from compliance_agent.models import pt_word_boundary
    import re
    pat = re.compile(pt_word_boundary(r"at[óo]xico"))
    check("matches the real word", bool(pat.search("produto atóxico")), "")
    check("does NOT eat the O of Óculos",
          not pat.search("Óculos de Segurança") or
          "culos de Segurança" not in "Óculos de Segurança".replace(
              pat.search("Óculos de Segurança").group(0), ""),
          "Óculos was damaged")
    check("does not match inside a longer word", not pat.search("atoxicamente"),
          "atoxicamente should not match")


def test_duplicates():
    section("Duplicate detection")
    a = Product(product_id="PROD-A", internal_sku="S1", supplier_sku="SUP1", shop_id="S1",
                title="Caixa Organizadora Transparente com Tampa",
                description="Caixa organizadora em plástico transparente com tampa. 30x20x10 cm.")
    b = Product(product_id="PROD-B", internal_sku="S2", supplier_sku="SUP1", shop_id="S2",
                title="Caixa Organizadora Transparente com Tampa",
                description="Caixa organizadora em plástico transparente com tampa. 30x20x10 cm.")
    c = Product(product_id="PROD-C", internal_sku="S3", supplier_sku="SUP9", shop_id="S2",
                title="Jogo de Copos de Vidro 6 Unidades",
                description="Jogo com 6 copos de vidro temperado de 350 ml.")
    idx = DuplicateIndex()
    for p in (a, b, c):
        idx.add(p)
    matches = idx.find_all()
    check("same supplier SKU across shops is a duplicate",
          any(m.product_id == "PROD-A" and m.other_product_id == "PROD-B" for m in matches),
          str([m.to_dict() for m in matches]))
    check("different products are not duplicates",
          not any("PROD-C" in (m.product_id, m.other_product_id) and
                  ("PROD-A" in (m.product_id, m.other_product_id) or
                   "PROD-B" in (m.product_id, m.other_product_id)) for m in matches),
          "C wrongly matched")
    for m in matches:
        check("duplicate match is cross-store flagged",
              not m.same_shop, f"{m.product_id} vs {m.other_product_id}")


def test_relist():
    section("Relist detection")
    hist = Product(product_id="PROD-OLD", internal_sku="OLD-SKU", supplier_sku="SUP-77",
                   shop_id="S1", platform_pid="555",
                   title="Tênis Esportivo Premium",
                   description="Tênis esportivo premium.")
    case = Case(case_id="SBRC-900", shop_id="S1", product_ids=["PROD-OLD"],
                violation_type="SBR-IP-002", status="blocked", frozen=True,
                rule_ids=["SBR-IP-002"])
    new = Product(product_id="PROD-NEW", internal_sku="BRAND-NEW-SKU", supplier_sku="SUP-77",
                  shop_id="S1", platform_pid="555",
                  title="Tênis Esportivo Premium Réplica",
                  description="Tênis esportivo premium. Réplica.")
    idx = RelistIndex()
    idx.add_product(hist)
    idx.add_case(case)
    idx.add_product(new)
    matches = idx.check(new)
    check("relist detected despite a changed SKU and title",
          bool(matches), "no relist match")
    if matches:
        check("relist matched on supplier SKU", "supplier_sku" in matches[0].match_basis,
              str(matches[0].match_basis))
        check("relist linked to the historical case", matches[0].case_id == "SBRC-900",
              matches[0].case_id)


def test_ingest():
    section("Ingest parsers")
    with tempfile.TemporaryDirectory() as d:
        # CSV
        csv_path = os.path.join(d, "in.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("商品ID,主商品货号,商品名称,商品描述,店铺ID\n")
            f.write("111,SKU1,Tênis de Couro,Tênis em couro legítimo.,SHOP1\n")
            f.write("222,SKU2,,Produto sem título.,SHOP1\n")
        res = parse_csv(csv_path, shop_id="SHOP1")
        check("csv parses 1 valid row", len(res.products) == 1, str(len(res.products)))
        check("csv reports the bad row instead of dropping it",
              len(res.errors) == 1, str(res.errors))
        check("csv product has title", res.products[0].title == "Tênis de Couro",
              res.products[0].title)

        # JSONL
        jl_path = os.path.join(d, "in.jsonl")
        with open(jl_path, "w", encoding="utf-8") as f:
            f.write('{"product_id":"333","internal_sku":"S3","title":"Óculos de Sol","shop_id":"S1"}\n')
            f.write('not json\n')
            f.write('{"internal_sku":"S4","title":"Sem PID","shop_id":"S1"}\n')
        res = parse_jsonl(jl_path)
        check("jsonl parses 2 records", len(res.products) == 2, str(len(res.products)))
        check("jsonl reports the invalid line", len(res.errors) == 1, str(res.errors))

        # TXT
        txt_path = os.path.join(d, "in.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("Title: Suporte para TV\nSKU: TV-1\nDescription: Suporte de parede para TVs.\n\n"
                    "Title: Cadeira Gamer\nSKU: CG-1\nDescription: Cadeira gamer reclinável.\n")
        res = parse_text(txt_path)
        check("txt parses 2 blocks", len(res.products) == 2, str(len(res.products)))

        # XLSX round trip (built by hand with zipfile, no openpyxl)
        xlsx_path = os.path.join(d, "in.xlsx")
        _write_minimal_xlsx(xlsx_path, [
            ["商品ID", "主商品货号", "商品名称", "商品描述"],
            ["444", "SKU4", "Chaleira Térmica", "Chaleira em inox 1,5 L."],
            ["555", "SKU5", "Panela de Pressão", "Panela de pressão 5 litros."],
        ])
        res = parse_xlsx(xlsx_path, shop_id="SHOP2")
        check("xlsx parses 2 rows", len(res.products) == 2, str(len(res.products)))
        if len(res.products) == 2:
            check("xlsx title read correctly",
                  res.products[0].title == "Chaleira Térmica",
                  res.products[0].title)
            check("xlsx shop id applied", res.products[0].shop_id == "SHOP2",
                  res.products[0].shop_id)

        # unreadable file
        bad = os.path.join(d, "bad.xlsx")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("not a zip")
        res = parse_xlsx(bad)
        check("bad xlsx reported as an error", len(res.errors) == 1 and not res.products,
              str(res.errors))


def _write_minimal_xlsx(path, rows):
    """Build a minimal valid .xlsx with the given rows (no openpyxl)."""
    strings = []
    index = {}
    for r in rows:
        for cell in r:
            if cell not in index:
                index[cell] = len(strings)
                strings.append(cell)
    si = "".join(f"<si><t>{s}</t></si>" for s in strings)
    sheet_rows = []
    for i, r in enumerate(rows, start=1):
        cells = []
        for j, cell in enumerate(r):
            col = chr(ord("A") + j)
            cells.append(f'<c r="{col}{i}" t="s"><v>{index[cell]}</v></c>')
        sheet_rows.append(f'<row r="{i}">{"".join(cells)}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
    )
    ss = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          f'count="{len(strings)}" uniqueCount="{len(strings)}">{si}</sst>')
    wb = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
    wb_rels = ('<?xml version="1.0" encoding="UTF-8"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
               'officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
               '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/'
               'officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
               '</Relationships>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
          '</Types>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/sharedStrings.xml", ss)


def test_citations():
    section("Citation verification")
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import verify_citations as vc
    captures = vc.load_captures()
    check("research captures exist", bool(captures), "no captures under research/raw")
    if not captures:
        return
    rules_dir = os.path.join(ROOT, "rules")
    total = 0
    failed = []
    for fn in sorted(os.listdir(rules_dir)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(rules_dir, fn), encoding="utf-8") as f:
            doc = json.load(f)
        for raw in doc.get("rules", []):
            total += 1
            excerpt = (raw.get("source_excerpt") or "").strip()
            if not excerpt:
                failed.append((raw["rule_id"], "no source_excerpt"))
                continue
            ne = vc.loose(excerpt)
            if not any(ne in vc.loose(text) for text in captures.values()):
                failed.append((raw["rule_id"], "excerpt not found verbatim"))
    check(f"all {total} rule excerpts are verbatim in a captured source",
          not failed, "; ".join(f"{a}: {b}" for a, b in failed))


def test_lexicon():
    section("Lexicon + Aho-Corasick over the real lexicon")
    from compliance_agent.engine.loader import compile_ac, load_lexicon
    try:
        lex = load_lexicon("term_groups.json")
    except FileNotFoundError:
        check("lexicon/term_groups.json exists", False, "file missing")
        return
    check("lexicon loads", bool(lex.get("groups")), "no groups")
    ac = compile_ac(lex)
    total = sum(len(v) for v in lex["groups"].values())
    check(f"lexicon has patterns ({total})", total > 50, str(total))
    hits = ac.matches_groups(
        "Vape descartavel com 3000 puffs. Replica de tenis Nike. "
        "Compre no whatsapp 11 99999-9999.")
    check("AC finds 'vape' without accents", "proibido_tabaco" in hits, str(list(hits)))
    check("AC finds 'Replica' without accents", "ip_contrafito" in hits, str(list(hits)))
    check("AC finds the brand", "ip_marca" in hits, str(list(hits)))
    check("AC finds the off-platform contact", "violacao_offplatform" in hits,
          str(list(hits)))
    check("AC match carries context",
          bool(hits["ip_marca"][0]["excerpt"].strip()), "")


def main():
    print("Shopee BR Compliance Agent — test suite")
    test_scenarios()
    test_rule_library()
    test_schemas()
    test_citations()
    test_aho_corasick()
    test_lexicon()
    test_portuguese_boundaries()
    test_duplicates()
    test_relist()
    test_ingest()
    print(f"\n{'=' * 60}")
    print(f"PASSED: {len(PASSED)}   FAILED: {len(FAILED)}")
    if FAILED:
        print("\nFailures:")
        for name, detail in FAILED:
            print(f"  - {name}: {detail}")
        sys.exit(1)
    print("All tests passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
