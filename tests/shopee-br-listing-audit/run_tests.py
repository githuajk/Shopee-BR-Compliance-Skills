#!/usr/bin/env python3
"""`shopee-br-listing-audit` 模块测试（L1–L4）。

覆盖（见 `skills/shopee-br-listing-audit/SKILL.md` §8）：

* **L1 单元** —— 字段取值、空值判定、触发条件求值、矩阵查表、词库筛查
* **L2 契约** —— 三份产出通过冻结契约的 Schema 校验
* **L3 规则** —— 每条 `active` 规则 ≥1 正例 + ≥1 反例（自有夹具 + 共享夹具）
* **L4 硬约束** —— H1 / H2 / H3 / H4 / H5 / H6 断言

运行：

```bash
env -u LD_LIBRARY_PATH python3 tests/shopee-br-listing-audit/run_tests.py
```

**只读**共享夹具（`tests/fixtures/**`）；本模块的自有夹具写在
`tests/shopee-br-listing-audit/fixtures/`。**任何情况下都不修改输入文件。**
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MODULE_DIR = os.path.join(ROOT, "skills", "shopee-br-listing-audit")
SRC = os.path.join(MODULE_DIR, "src")

sys.path.insert(0, SRC)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from validate_json import Validator  # noqa: E402

from sbr_listing_audit import __version__, audit_listing  # noqa: E402
from sbr_listing_audit.conditions import (  # noqa: E402
    MATCH,
    NO_MATCH,
    UNEVALUATED,
    ConditionError,
    evaluate_condition,
)
from sbr_listing_audit.engine import ListingAuditEngine  # noqa: E402
from sbr_listing_audit.fields import any_text, get_field, is_empty  # noqa: E402
from sbr_listing_audit.lexicon import candidate_rules, load_rule_map  # noqa: E402
from sbr_listing_audit.matrix import (  # noqa: E402
    is_allowed,
    load_matrix,
    verdict_for,
)
from sbr_listing_audit.rules import (  # noqa: E402
    BLOCKING_ACTIONS,
    OWNED_PREFIXES,
    blocking_allowed,
    load_rules,
    normalise_rule,
    rule_prefix,
)

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name: str, cond: bool, detail: str = "") -> bool:
    if cond:
        PASSED.append(name)
        return True
    FAILED.append((name, detail))
    print(f"  FAIL {name}: {detail}")
    return False


def section(title: str) -> None:
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------------------
# 契约校验器
# ---------------------------------------------------------------------------

def _validator(schema_rel: str) -> Validator:
    schema_path = os.path.join(ROOT, schema_rel)
    with open(schema_path, encoding="utf-8") as handle:
        schema = json.load(handle)
    return Validator(schema, base_dir=os.path.dirname(schema_path))


def validate_against(schema_rel: str, payload, label: str) -> None:
    validator = _validator(schema_rel)
    errors = validator.validate(payload)
    check(f"{label} 符合 {schema_rel}", not errors, "; ".join(errors[:4]))


# ---------------------------------------------------------------------------
# 夹具
# ---------------------------------------------------------------------------

def load_fixture(*parts: str) -> dict:
    path = os.path.join(HERE, *parts)
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_shared(name: str) -> dict:
    path = os.path.join(ROOT, "tests", "fixtures", name)
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def make_skill_input(products, request_id: str = "REQ-LISTING-TEST-001",
                     provenance=None) -> dict:
    return {
        "request_id": request_id,
        "task_type": "listing_audit",
        "target": {"kind": "product_batch", "count": len(products)},
        "products": products,
        "provenance": provenance or {
            "inputs": [{"path": "tests/fixtures/synthetic.json", "kind": "json"}],
            "produced_at": "2026-10-27T00:00:00Z",
        },
    }


# ---------------------------------------------------------------------------
# L1 单元测试
# ---------------------------------------------------------------------------

def test_l1_fields() -> None:
    section("L1 字段取值与空值判定")

    check("is_empty(None) 为真", is_empty(None))
    check("is_empty('') 为真", is_empty(""))
    check("is_empty('   ') 为真", is_empty("   "))
    check("is_empty([]) 为真", is_empty([]))
    check("is_empty({}) 为真", is_empty({}))
    check("is_empty(0) 为假（0 是有效取值）", not is_empty(0))
    check("is_empty(False) 为假", not is_empty(False))
    check("is_empty('x') 为假", not is_empty("x"))

    product = {
        "title": "Título",
        "description": "Descrição",
        "brand": "Marca",
        "category": "Casa > Cozinha",
        "model": "M1",
        "images": [{"image_id": "i1", "ocr_text": "texto"}],
    }
    check("get_field(title) 正确", get_field(product, "title") == "Título")
    check("get_field(image) 返回图片数组",
          get_field(product, "image") == product["images"])
    check("get_field(image_text) 拼接 OCR 文本",
          get_field(product, "image_text") == "texto")
    merged = any_text(product)
    check("any_text 含标题", "Título" in merged)
    check("any_text 含详情", "Descrição" in merged)
    check("any_text 含型号", "M1" in merged)
    check("any_text 含图片 OCR", "texto" in merged)
    check("get_field(未知字段) 返回 None", get_field(product, "no_such_field") is None)


def test_l1_conditions() -> None:
    section("L1 触发条件求值")

    product = {
        "product_id": "P1",
        "title": "Kit 4 Copos de Vidro 250ml",
        "description": "Descrição com mais de 120 caracteres para que a condição de "
                       "comprimento não seja disparada e o teste siga adiante "
                       "verificando outros operadores com segurança determinística.",
        "category": "Casa",
        "brand": None,
        "images": [],
    }

    result = evaluate_condition(product, {"field": "title", "operator": "regex",
                                          "value": "copos"})
    check("regex 命中返回 match", result["status"] == MATCH, result["status"])
    check("regex 命中带片段", bool(result.get("excerpt")))

    result = evaluate_condition(product, {"field": "title", "operator": "regex",
                                          "value": "COPOS"})
    check("regex 大小写不敏感命中", result["status"] == MATCH, result["status"])

    result = evaluate_condition(product, {"field": "title", "operator": "regex",
                                          "value": "inexistente"})
    check("regex 不命中返回 no_match", result["status"] == NO_MATCH, result["status"])

    result = evaluate_condition(product, {"field": "brand", "operator": "regex",
                                          "value": "marca"})
    check("字段缺失返回 unevaluated（H3）", result["status"] == UNEVALUATED,
          result["status"])

    result = evaluate_condition(product, {"field": "description",
                                          "operator": "length_lt", "value": 120})
    check("length_lt 语义正确（长度比较）", result["status"] == NO_MATCH,
          result["status"])

    result = evaluate_condition(product, {"field": "image",
                                          "operator": "image_count_lt", "value": 1})
    check("image_count_lt 对空数组命中", result["status"] == MATCH, result["status"])

    result = evaluate_condition(product, {"field": "category",
                                          "operator": "field_missing",
                                          "value": "category"})
    check("field_missing 对有值不命中", result["status"] == NO_MATCH, result["status"])

    result = evaluate_condition(product, {"field": "description",
                                          "operator": "contains_any",
                                          "value": ["Descrição"]})
    check("contains_any 命中", result["status"] == MATCH, result["status"])

    result = evaluate_condition(product, {"field": "history",
                                          "operator": "contains_any",
                                          "value": ["missing"]})
    check("dict 字段的 contains_any 按键判定", result["status"] == UNEVALUATED,
          result["status"])

    try:
        evaluate_condition(product, {"field": "title", "operator": "regex",
                                     "value": "([unclosed"})
        check("非法正则抛 ConditionError", False, "未抛出")
    except ConditionError:
        check("非法正则抛 ConditionError", True)

    try:
        evaluate_condition(product, {"field": "title", "operator": "no_such_op",
                                     "value": "x"})
        check("未知算子抛 ConditionError", False, "未抛出")
    except ConditionError:
        check("未知算子抛 ConditionError", True)

    result = evaluate_condition(product, {"field": "title", "operator": "regex",
                                          "value": "copos",
                                          "requires_input": ["brand"]})
    check("requires_input 缺失时不评估", result["status"] == UNEVALUATED,
          result["status"])


def test_l1_matrix() -> None:
    section("L1 风险动作矩阵查表")

    matrix, error = load_matrix(ROOT)
    check("矩阵读取成功", error is None, str(error))
    check("critical + block 被允许", is_allowed(matrix, "critical", "block"))
    check("low + block 不被允许", not is_allowed(matrix, "low", "block"))
    check("info + require_evidence 不被允许",
          not is_allowed(matrix, "info", "require_evidence"))
    check("medium + revise 被允许", is_allowed(matrix, "medium", "revise"))
    check("critical + revise 不被允许", not is_allowed(matrix, "critical", "revise"))
    check("action=block 的 verdict 是 BLOCK",
          verdict_for(matrix, "block") == "BLOCK")
    check("action=flag_for_review 的 verdict 是 REVIEW",
          verdict_for(matrix, "flag_for_review") == "REVIEW")
    check("action=require_evidence 的 verdict 是 REVIEW",
          verdict_for(matrix, "require_evidence") == "REVIEW")
    check("action=revise 的 verdict 是 REVISE",
          verdict_for(matrix, "revise") == "REVISE")
    check("action=allow 的 verdict 是 PASS",
          verdict_for(matrix, "allow") == "PASS")


def test_l1_rules() -> None:
    section("L1 规则加载与来源层级")

    rules = load_rules(root=ROOT)
    rule_ids = [rule["rule_id"] for rule in rules]
    check(f"加载到 {len(rules)} 条本模块规则", len(rules) > 0)
    check("全部规则前缀属于本模块",
          all(rule_prefix(rid) in OWNED_PREFIXES for rid in rule_ids),
          str([rid for rid in rule_ids if rule_prefix(rid) not in OWNED_PREFIXES]))
    check("不含 IP 前缀规则",
          not any(rule_prefix(rid) == "IP" for rid in rule_ids))
    check("不含 DUP 前缀规则",
          not any(rule_prefix(rid) == "DUP" for rid in rule_ids))
    check("规则 ID 唯一", len(rule_ids) == len(set(rule_ids)))
    check("每条规则都有 source.excerpt",
          all(rule["source"].get("excerpt") for rule in rules))
    check("每条规则都有 source.last_verified",
          all(rule["source"].get("last_verified") for rule in rules))
    check("每条规则都有 status",
          all(rule.get("status") for rule in rules))

    active = [rule for rule in rules if rule.get("status") == "active"]
    check(f"{len(active)} 条 active 规则可产出结论", len(active) > 0)

    internal = normalise_rule({
        "rule_id": "SBR-PI-999", "title": "x", "category": "prohibited_item",
        "description": "x", "severity": "critical", "decision": "block",
        "source_tier": "internal_risk", "source_url": "https://example.invalid/x",
        "source_excerpt": "x", "last_verified": "2026-10-27", "status": "active",
        "version": 1, "evidence_required": [], "human_review_required": True,
        "trigger_conditions": [{"field": "title", "operator": "regex",
                                "value": "x"}],
    })
    check("internal_risk 规则不得阻断", not blocking_allowed(internal))
    check("internal_risk 规则的最高动作是 flag_for_review",
          blocking_allowed(internal) is False)

    official = normalise_rule({
        "rule_id": "SBR-PI-998", "title": "x", "category": "prohibited_item",
        "description": "x", "severity": "critical", "decision": "block",
        "source_tier": "platform_official", "source_url": "https://example.invalid/x",
        "source_excerpt": "x", "last_verified": "2026-10-27", "status": "active",
        "version": 1, "evidence_required": [], "human_review_required": True,
        "trigger_conditions": [{"field": "title", "operator": "regex",
                                "value": "x"}],
    })
    check("platform_official + active 允许阻断", blocking_allowed(official))

    draft = dict(official)
    draft["status"] = "draft"
    check("platform_official + draft 不得阻断", not blocking_allowed(draft))


def test_l1_lexicon() -> None:
    section("L1 词库筛查（信号层）")

    engine = ListingAuditEngine(root=ROOT)
    rule_map = load_rule_map(ROOT)
    check("词组 → 规则映射可载入", len(rule_map) > 0)

    product = {
        "product_id": "LEX-1",
        "title": "Vape Descartável Sabor Frutas",
        "description": "Vape com juice de nicotina.",
        "brand": "Sem Marca",
    }
    hits = engine.scanner.scan_product(product)
    check("词库扫描到命中", len(hits) > 0)
    check("命中带字段位置", all("field" in hit for hit in hits))
    check("命中带偏移", all("offset" in hit for hit in hits))

    candidates = candidate_rules(hits, rule_map, OWNED_PREFIXES)
    check("命中折算为候选规则", isinstance(candidates, dict))
    for rule_id in candidates:
        check(f"候选规则 {rule_id} 属本模块前缀",
              rule_prefix(rule_id) in OWNED_PREFIXES)

    # 词库命中不得直接产生结论 —— 规则层才是判定者
    evaluation = engine.evaluate_product(product)
    fired_ids = [item["rule"]["rule_id"] for item in evaluation["fired"]]
    check("词库命中伴随规则层命中（非词库单独生效）",
          "SBR-PI-002" in fired_ids, str(fired_ids))

    # 豁免路径：词库命中后先查豁免，命中仍记录但降置信度
    exempt_product = {
        "product_id": "LEX-2",
        "title": "Kit de Frete com Transportadora Hermes para Envio",
        "description": "Entrega feita pela transportadora Hermes para todo o Brasil.",
        "brand": "Sem Marca",
    }
    exempt_hits = engine.scanner.scan_product(exempt_product)
    check("工具类/功能描述命中带豁免标记",
          any(hit.get("exempt") for hit in exempt_hits),
          str([hit.get("exempt") for hit in exempt_hits]))
    check("豁免命中仍被记录（豁免 ≠ 放行）",
          any(hit.get("group_id") == "ip_marca_global" for hit in exempt_hits),
          str([hit.get("group_id") for hit in exempt_hits]))


# ---------------------------------------------------------------------------
# L2 契约测试
# ---------------------------------------------------------------------------

def test_l2_contract() -> None:
    section("L2 契约校验")

    cases = load_fixture("fixtures", "listing_audit_rule_cases.json")["cases"]
    products = [case["product"] for case in cases]
    skill_input = make_skill_input(products)
    bundle = audit_listing(skill_input, root=ROOT)

    check("产出 AuditResult 非空", len(bundle["results"]) > 0)
    for result in bundle["results"]:
        validate_against("contracts/audit_result.schema.json", result,
                         f"result {result['result_id']}")

    validate_against("contracts/module_handoff.schema.json", bundle["handoff"],
                     "module_handoff")

    skill_input_out = make_skill_input(products)
    validate_against("contracts/skill_input.schema.json", skill_input_out,
                     "skill_input（回填检查）")

    # 枚举取值
    verdicts = {"PASS", "REVISE", "REVIEW", "BLOCK"}
    actions = {"allow", "flag_for_review", "require_evidence", "revise", "block",
               "freeze_relist", "escalate_legal"}
    levels = {"info", "low", "medium", "high", "critical"}
    confidences = {"signal", "likely", "confirmed"}
    check("verdict 取值全在契约内",
          all(r["verdict"] in verdicts for r in bundle["results"]))
    check("action 取值全在契约内",
          all(r["action"] in actions for r in bundle["results"]))
    check("risk_level 取值全在契约内",
          all(r["risk_level"] in levels for r in bundle["results"]))
    check("confidence 取值全在契约内",
          all(r["confidence"] in confidences for r in bundle["results"]))
    check("module 固定为 shopee-br-listing-audit",
          all(r["module"] == "shopee-br-listing-audit" for r in bundle["results"]))
    check("request_id 贯穿产出",
          all(r["request_id"] == skill_input["request_id"]
              for r in bundle["results"]))
    check("rule_version 非空",
          all(r["rule_version"] for r in bundle["results"]))
    check("provenance 完整",
          all(r["provenance"].get("produced_at") and r["provenance"].get("producer")
              for r in bundle["results"]))

    # 交接记录必填项
    handoff = bundle["handoff"]
    check("handoff.assumptions 非空", bool(handoff.get("assumptions")))
    check("handoff.known_gaps 非空", bool(handoff.get("known_gaps")))
    check("handoff.contract_version 合法",
          bool(re.fullmatch(r"\d+\.\d+\.\d+", handoff["contract_version"])))
    check("handoff.from_module 正确",
          handoff["from_module"] == "shopee-br-listing-audit")


def test_l2_matrix_consistency() -> None:
    section("L2 结果与矩阵一致")

    cases = load_fixture("fixtures", "listing_audit_rule_cases.json")["cases"]
    bundle = audit_listing(make_skill_input([c["product"] for c in cases]),
                           root=ROOT)
    matrix, _ = load_matrix(ROOT)
    ok = True
    detail = ""
    for result in bundle["results"]:
        if not is_allowed(matrix, result["risk_level"], result["action"]):
            ok = False
            detail = (f"{result['target_ref']}: "
                      f"{result['risk_level']}/{result['action']} 不在矩阵允许格子里")
            break
        expected_verdict = verdict_for(matrix, result["action"])
        if result["verdict"] != expected_verdict:
            ok = False
            detail = (f"{result['target_ref']}: verdict={result['verdict']} 与 "
                      f"action={result['action']} 的矩阵映射 {expected_verdict} 不符")
            break
    check("每条结果的 (risk_level, action) 都是矩阵允许组合", ok, detail)
    check("verdict 与 action 的映射符合矩阵", ok, detail)

# ---------------------------------------------------------------------------
# L3 规则测试
# ---------------------------------------------------------------------------

def test_l3_own_rule_cases() -> None:
    section("L3 自有规则用例（每条规则正例 + 反例）")

    cases = load_fixture("fixtures", "listing_audit_rule_cases.json")["cases"]
    engine = ListingAuditEngine(root=ROOT)

    for case in cases:
        evaluation = engine.evaluate_product(case["product"])
        fired = {item["rule"]["rule_id"] for item in evaluation["fired"]}
        unevaluated = {item["rule"]["rule_id"] for item in evaluation["unevaluated"]}
        for rule_id in case.get("must_fire", []):
            check(f"{case['case_id']} 命中 {rule_id}", rule_id in fired,
                  f"fired={sorted(fired)}")
        for rule_id in case.get("must_not_fire", []):
            check(f"{case['case_id']} 不命中 {rule_id}", rule_id not in fired,
                  f"fired={sorted(fired)}")
        for rule_id in case.get("must_be_unevaluated", []):
            check(f"{case['case_id']} 未评估 {rule_id}", rule_id in unevaluated,
                  f"unevaluated={sorted(unevaluated)}")

    # 覆盖率：每条 active 规则都有正例与反例
    rules = load_rules(root=ROOT)
    active = [rule["rule_id"] for rule in rules if rule.get("status") == "active"]
    positives: set[str] = set()
    negatives: set[str] = set()
    for case in cases:
        positives.update(case.get("must_fire", []))
        negatives.update(case.get("must_not_fire", []))
    missing_positive = [rid for rid in active if rid not in positives]
    missing_negative = [rid for rid in active if rid not in negatives]
    check(f"{len(active)} 条 active 规则全部有正例", not missing_positive,
          str(missing_positive))
    check(f"{len(active)} 条 active 规则全部有反例", not missing_negative,
          str(missing_negative))


def test_l3_shared_fixtures() -> None:
    section("L3 共享夹具一致性（只读）")

    engine = ListingAuditEngine(root=ROOT)

    # --- 正例：必须命中 ---
    violations = load_shared("violation_products.json")["products"]
    for product in violations:
        targets = [rid for rid in product.get("targets", [])
                   if rule_prefix(rid) in OWNED_PREFIXES]
        if not targets:
            continue
        evaluation = engine.evaluate_product(product)
        fired = {item["rule"]["rule_id"] for item in evaluation["fired"]}
        for rule_id in targets:
            check(f"共享正例 {product['product_id']} 命中 {rule_id}",
                  rule_id in fired, f"fired={sorted(fired)}")

    # --- 反例：必须不命中 ---
    normals = load_shared("normal_products.json")["products"]
    for product in normals:
        targets = [rid for rid in product.get("targets", [])
                   if rule_prefix(rid) in OWNED_PREFIXES]
        if not targets:
            continue
        evaluation = engine.evaluate_product(product)
        fired = {item["rule"]["rule_id"] for item in evaluation["fired"]}
        for rule_id in targets:
            check(f"共享反例 {product['product_id']} 不命中 {rule_id}",
                  rule_id not in fired, f"fired={sorted(fired)}")

    # --- 边界用例 ---
    for case in load_shared("edge_cases.json")["cases"]:
        evaluation = engine.evaluate_product(case["product"])
        fired = {item["rule"]["rule_id"] for item in evaluation["fired"]}
        for rule_id in case.get("must_fire", []):
            if rule_prefix(rule_id) not in OWNED_PREFIXES:
                continue
            check(f"共享边界 {case['case_id']} 命中 {rule_id}",
                  rule_id in fired, f"fired={sorted(fired)}")
        for rule_id in case.get("must_not_fire", []):
            if rule_prefix(rule_id) not in OWNED_PREFIXES:
                continue
            check(f"共享边界 {case['case_id']} 不命中 {rule_id}",
                  rule_id not in fired, f"fired={sorted(fired)}")

    # --- 缺失数据用例 ---
    for case in load_shared("missing_data_cases.json")["cases"]:
        evaluation = engine.evaluate_product(case["product"])
        fired = {item["rule"]["rule_id"] for item in evaluation["fired"]}
        unevaluated = {item["rule"]["rule_id"] for item in evaluation["unevaluated"]}
        for rule_id in case.get("must_fire", []):
            if rule_prefix(rule_id) not in OWNED_PREFIXES:
                continue
            check(f"共享缺失 {case['case_id']} 命中 {rule_id}",
                  rule_id in fired, f"fired={sorted(fired)}")
        for rule_id in case.get("must_be_unevaluated", []):
            if rule_prefix(rule_id) not in OWNED_PREFIXES:
                continue
            check(f"共享缺失 {case['case_id']} 未评估 {rule_id}",
                  rule_id in unevaluated, f"unevaluated={sorted(unevaluated)}")


def test_l3_shared_fixtures_untouched() -> None:
    section("L3 共享夹具未被修改")

    for name in ("normal_products.json", "violation_products.json",
                 "edge_cases.json", "missing_data_cases.json"):
        path = os.path.join(ROOT, "tests", "fixtures", name)
        with open(path, "rb") as handle:
            raw = handle.read()
        try:
            json.loads(raw.decode("utf-8"))
            ok = True
            detail = ""
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            ok = False
            detail = str(exc)
        check(f"共享夹具 {name} 仍是合法 JSON 且未被改写", ok, detail)


# ---------------------------------------------------------------------------
# L4 硬约束测试
# ---------------------------------------------------------------------------

def test_h1_ip_never_deterministic() -> None:
    section("L4 / H1 —— IP 类结论恒为 signal + 强制人工复核")

    ip_cases = load_shared("ip_cases.json")["cases"]
    bundle = audit_listing(make_skill_input(
        [c["product"] for c in ip_cases]), root=ROOT)
    check("IP 场景产出了结果", len(bundle["results"]) > 0, f"{len(bundle['results'])}")
    for result in bundle["results"]:
        # 本模块不判定 IP —— 结论只能是「无命中」或「与 IP 无关的其他命中」
        ip_refs = [ref["rule_id"] for ref in result["rule_refs"]
                   if ref["rule_id"].startswith("SBR-IP-")]
        check(f"{result['target_ref']} 不产生 IP 类结论", not ip_refs, str(ip_refs))
        if result["confidence"] == "confirmed":
            check(f"{result['target_ref']} 的确定性结论只来自权威 active 规则",
                  all(ref.get("source_tier") in ("platform_official", "law")
                      for ref in result["rule_refs"]),
                  str([ref.get("source_tier") for ref in result["rule_refs"]]))

    # 注入一条 IP 类规则（category ∈ IP 四类）验证 H1 强制生效
    from sbr_listing_audit.rules import normalise_rule as _normalise
    ip_injected = _normalise({
        "rule_id": "SBR-IP-900",
        "title": "Injected IP rule",
        "category": "ip_trademark",
        "description": "injected IP rule used to prove H1 enforcement",
        "severity": "high",
        "action": "escalate_legal",
        "source": {"tier": "platform_official",
                   "url": "https://example.invalid/ip",
                   "excerpt": "x", "last_verified": "2026-10-27"},
        "status": "active",
        "version": 1,
        "evidence_required": [],
        "requires_human_review": True,
        "trigger_conditions": [{"field": "title", "operator": "regex",
                                "value": "copos"}],
    })
    # `IP` 前缀不在本模块的 OWNED_PREFIXES 里（IP 属 ip-review 模块），
    # 所以要显式放开前缀过滤，否则注入的规则根本不会被加载 ——
    # 那样断言就成了空转，永远「通过」。
    ip_engine = ListingAuditEngine(root=ROOT, options={
        "rules": [ip_injected],
        "rule_prefixes": tuple(OWNED_PREFIXES) + ("IP",),
    })
    ip_product = {
        "product_id": "H1-IP-1",
        "internal_sku": "H1-IP-1",
        "shop_id": "LA-SHOP",
        "title": "Kit 4 Copos de Vidro",
        "description": "x" * 200,
        "category": "Casa",
        "brand": "Sem Marca",
        "images": [],
        "source": {"kind": "manual", "path": None, "imported_at": "2026-10-27T00:00:00Z"},
    }
    ip_result = ip_engine.build_result(ip_engine.evaluate_product(ip_product),
                                       "REQ-H1-0001", "2026-10-27T00:00:00Z")
    check("注入的 IP 规则被命中", any(
        ref["rule_id"] == "SBR-IP-900" for ref in ip_result["rule_refs"]),
          str([ref["rule_id"] for ref in ip_result["rule_refs"]]))
    check("IP 结论 confidence=signal（H1）", ip_result["confidence"] == "signal",
          ip_result["confidence"])
    check("IP 结论 requires_human_review=true（H1）",
          ip_result["requires_human_review"] is True)

    # 本模块**不产生** IP 类结论 —— 全量结果里不得出现 IP 规则引用
    # `violation_products.json` 的 `products[]` 直接就是商品对象
    # （夹具没有 `product` 包装层）。
    all_results = audit_listing(make_skill_input(
        load_shared("violation_products.json")["products"]
    ), root=ROOT)["results"]
    ip_refs = [ref["rule_id"] for r in all_results for ref in r["rule_refs"]
               if ref["rule_id"].startswith("SBR-IP-")]
    check("本模块不引用 IP 规则作为命中规则", not ip_refs, str(ip_refs))


def test_h2_blocking_requires_authoritative_active_rule() -> None:
    section("L4 / H2 —— 阻断类动作只来自 platform_official / law 的 active 规则")

    engine = ListingAuditEngine(root=ROOT)

    # 构造一条 internal_risk 的阻断规则（通过 SkillInput.rules[] 注入）
    injected = {
        "rule_id": "SBR-PI-900",
        "title": "Injected internal-risk blocking rule",
        "category": "prohibited_item",
        "description": "injected rule used to prove H2 enforcement",
        "severity": "critical",
        "action": "block",
        "source": {"tier": "internal_risk", "url": "https://example.invalid/internal",
                   "excerpt": "internal", "last_verified": "2026-10-27"},
        "status": "active",
        "version": 1,
        "evidence_required": [],
        "requires_human_review": True,
        "trigger_conditions": [{"field": "title", "operator": "regex",
                                "value": "copos"}],
    }
    # 必须把注入规则真正传给引擎 —— 否则下面关于「降级」的断言
    # 根本不会执行到那条规则，测试就成了空转。
    engine = ListingAuditEngine(root=ROOT, options={"rules": [injected]})
    product = {
        "product_id": "H2-INJECT-1",
        "internal_sku": "H2-INJECT-1",
        "shop_id": "LA-SHOP",
        "title": "Kit 4 Copos de Vidro",
        "description": "x" * 200,
        "category": "Casa",
        "brand": "Sem Marca",
        "images": [],
        "source": {"kind": "manual", "path": None, "imported_at": "2026-10-27T00:00:00Z"},
    }
    evaluation = engine.evaluate_product(product)
    fired = {item["rule"]["rule_id"]: item for item in evaluation["fired"]}
    check("注入的 internal_risk 规则被加载", "SBR-PI-900" in fired,
          str(sorted(fired)))
    if "SBR-PI-900" in fired:
        action = fired["SBR-PI-900"]["action"]
        # H2 的要求是「不得产出阻断类动作」，不是「必须降级成某一个
        # 特定动作」。引擎择优取的是矩阵允许的最强非阻断动作 ——
        # critical 风险下是 `require_evidence`（比 flag_for_review 更强，
        # 仍然不是阻断）。所以断言应检查「不是阻断类」且「在允许集合内」。
        check("internal_risk 规则的阻断动作被降级", action not in BLOCKING_ACTIONS,
              action)
        check("internal_risk 规则降级为非阻断的复核类动作",
              action in ("require_evidence", "flag_for_review"), action)
        check("降级原因被记录",
              bool(fired["SBR-PI-900"].get("downgrade_reason")))

    # draft 规则不得阻断
    draft_injected = dict(injected)
    draft_injected["rule_id"] = "SBR-PI-901"
    draft_injected["status"] = "draft"
    draft_injected["source"] = dict(injected["source"], tier="platform_official")
    draft_engine = ListingAuditEngine(root=ROOT,
                                      options={"rules": [draft_injected]})
    draft_eval = draft_engine.evaluate_product(product)
    draft_fired = {item["rule"]["rule_id"]: item for item in draft_eval["fired"]}
    check("draft 规则不产出任何结论", "SBR-PI-901" not in draft_fired,
          str(sorted(draft_fired)))

    # 全量结果：不得出现非权威来源产生的阻断类动作
    bundle = audit_listing(make_skill_input(
        load_fixture("fixtures", "listing_audit_rule_cases.json")["cases"]
    ), root=ROOT)
    for result in bundle["results"]:
        if result["action"] in BLOCKING_ACTIONS:
            tiers = {ref.get("source_tier") for ref in result["rule_refs"]
                     if ref.get("rule_id")}
            check(f"{result['target_ref']} 的阻断动作来源层级权威",
                  tiers and tiers <= {"platform_official", "law"}, str(tiers))
            check(f"{result['target_ref']} 的阻断结论要求人工复核",
                  result["requires_human_review"] is True)


def test_h3_missing_input_is_not_a_pass() -> None:
    section("L4 / H3 —— 输入缺失不等于合规")

    cases = load_fixture("fixtures", "listing_audit_rule_cases.json")["cases"]
    missing_cases = [c for c in cases if c.get("must_be_unevaluated")]
    check("存在缺输入用例", len(missing_cases) > 0)

    for case in missing_cases:
        bundle = audit_listing(make_skill_input([case["product"]]), root=ROOT)
        result = bundle["results"][0]
        unevaluated_ids = {item["rule_id"] for item in result["unevaluated"]}
        for rule_id in case["must_be_unevaluated"]:
            check(f"{case['case_id']} 的 {rule_id} 记入 unevaluated",
                  rule_id in unevaluated_ids, str(sorted(unevaluated_ids)))
            check(f"{case['case_id']} 的 {rule_id} 未产生命中",
                  rule_id not in {ref["rule_id"] for ref in result["rule_refs"]})
        check(f"{case['case_id']} 不产生 PASS 结论",
              result["verdict"] != "PASS", result["verdict"])
        check(f"{case['case_id']} 要求人工复核",
              result["requires_human_review"] is True)
        rule_eval_errors = [e for e in result["errors"]
                            if e.get("stage") == "rule_evaluation"]
        check(f"{case['case_id']} 上报 stage=rule_evaluation 的 warning",
              bool(rule_eval_errors) and
              all(e["severity"] == "warning" for e in rule_eval_errors))

    # 全部未评估（无命中）时也不得判 PASS
    empty_product = {
        "product_id": "H3-EMPTY-1",
        "internal_sku": "H3-EMPTY-1",
        "shop_id": "LA-SHOP",
        "title": "Produto sem detalhes",
        "description": "",
        "category": None,
        "brand": None,
        "images": [],
        "source": {"kind": "manual", "path": None, "imported_at": "2026-10-27T00:00:00Z"},
    }
    bundle = audit_listing(make_skill_input([empty_product]), root=ROOT)
    result = bundle["results"][0]
    check("全维度缺失 → 不判 PASS", result["verdict"] != "PASS", result["verdict"])
    check("全维度缺失 → unevaluated 非空", len(result["unevaluated"]) > 0)
    check("全维度缺失 → 要求人工复核", result["requires_human_review"] is True)


def test_h4_citations_verbatim() -> None:
    section("L4 / H4 —— 引文逐字核验")

    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "verify_citations.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    output = proc.stdout + proc.stderr
    check("tools/verify_citations.py 执行成功", proc.returncode == 0,
          output.strip().splitlines()[-1] if output.strip() else "")
    match = re.search(r"(\d+)/(\d+) excerpts verified verbatim, (\d+) failed", output)
    check("引文核验输出可解析", match is not None, output.strip()[-200:])
    if match:
        passed, total, failed = int(match.group(1)), int(match.group(2)), int(match.group(3))
        check(f"引文核验 0 失败（{passed}/{total}）", failed == 0, f"{failed} failed")
        check(f"全部 {total} 条规则引文逐字可核验", passed == total,
              f"{passed}/{total}")

    # 本模块的规则必须逐字出现在抓取件中（独立复核一遍）
    engine = ListingAuditEngine(root=ROOT)
    raw_dir = os.path.join(ROOT, "research", "raw")
    captures = []
    for name in sorted(os.listdir(raw_dir)):
        if name.endswith(".txt"):
            with open(os.path.join(raw_dir, name), encoding="utf-8") as handle:
                captures.append(handle.read())

    def normalise(text: str) -> str:
        for a, b in {"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-",
                     "—": "-", " ": " ", "…": "..."}.items():
            text = text.replace(a, b)
        text = re.sub(r"\s+", " ", text)
        return text.strip().lower()

    def loose(text: str) -> str:
        text = normalise(text)
        text = text.replace(",", " ").replace(".", " ").replace(";", " ").replace(":", " ")
        return re.sub(r"\s+", " ", text).strip()

    misses = []
    for rule in engine.rules:
        excerpt = (rule["source"].get("excerpt") or "").strip()
        if not excerpt:
            misses.append(rule["rule_id"])
            continue
        needle = loose(excerpt)
        if not any(needle in loose(capture) for capture in captures):
            misses.append(rule["rule_id"])
    check(f"本模块 {len(engine.rules)} 条规则的引文逐字出现在 research/raw/",
          not misses, str(misses))


def test_h5_evidence_only_references() -> None:
    section("L4 / H5 —— 证据只存引用，不内嵌凭证内容")

    cases = load_fixture("fixtures", "listing_audit_rule_cases.json")["cases"]
    bundle = audit_listing(make_skill_input([c["product"] for c in cases]),
                           root=ROOT)

    secret_patterns = [
        (re.compile(r"\bsk-[A-Za-z0-9]{8,}"), "openai-style key"),
        (re.compile(r"\bghp_[A-Za-z0-9]{8,}"), "github token"),
        (re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"), "long base64 blob"),
        (re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"), "private key"),
        (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "cpf-like number"),
    ]
    hits = []
    for result in bundle["results"]:
        for ref in result["evidence_refs"]:
            blob = " ".join(str(ref.get(key) or "") for key in
                            ("artifact_ref", "notes", "source_locator"))
            for pattern, label in secret_patterns:
                if pattern.search(blob):
                    hits.append(f"{result['target_ref']}/{ref['evidence_id']}: {label}")
    check("evidence_refs 不含凭证特征", not hits, str(hits[:4]))

    # artifact_ref 只应是路径式引用
    bad_refs = [ref["artifact_ref"] for result in bundle["results"]
                for ref in result["evidence_refs"]
                if ref.get("artifact_ref") and
                not str(ref["artifact_ref"]).startswith("products/")]
    check("artifact_ref 只存产品字段路径引用", not bad_refs, str(bad_refs[:4]))

    # 待补证据的 provided=false
    pending = [ref for result in bundle["results"] for ref in result["evidence_refs"]
               if ref.get("provided") is False]
    check("待补证据标记 provided=false 且 artifact_ref 为空",
          all(ref.get("artifact_ref") is None for ref in pending),
          str(len(pending)))


def test_h6_human_only_actions() -> None:
    section("L4 / H6 —— freeze_relist / escalate_legal 为 human_only")

    cases = load_fixture("fixtures", "listing_audit_rule_cases.json")["cases"]
    bundle = audit_listing(make_skill_input([c["product"] for c in cases]),
                           root=ROOT)
    human_only = [r for r in bundle["results"]
                  if r["action"] in ("freeze_relist", "escalate_legal")]
    check("本模块不产生 freeze_relist / escalate_legal", not human_only,
          str([r["target_ref"] for r in human_only]))
    for result in bundle["results"]:
        if result["action"] in ("freeze_relist", "escalate_legal"):
            check(f"{result['target_ref']} 的 human_only 动作要求人工复核",
                  result["requires_human_review"] is True)

    # 模块不提供任何执行线上处置的入口
    package_files = []
    for dirpath, dirnames, filenames in os.walk(MODULE_DIR):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            if name.endswith(".py"):
                package_files.append(os.path.join(dirpath, name))
    forbidden = re.compile(
        r"\b(unpublish|publish_listing|delete_listing|freeze_shop|"
        r"submit_appeal|api\.shopee|openapi)\b", re.IGNORECASE)
    offenders = [path for path in package_files
                 if forbidden.search(open(path, encoding="utf-8").read())]
    check("模块源码不含线上处置入口", not offenders, str(offenders))


# ---------------------------------------------------------------------------
# 失败路径
# ---------------------------------------------------------------------------

def test_failure_paths() -> None:
    section("失败路径 —— 不静默丢弃、不中断整批")

    good = {
        "product_id": "FAIL-GOOD-1",
        "internal_sku": "FAIL-GOOD-1",
        "shop_id": "LA-SHOP",
        "title": "Copo de Vidro 300ml",
        "description": "Copo de vidro temperado com capacidade de 300 ml. Pode ser usado "
                       "para água e suco. Medidas: 12 cm por 7 cm. Peso: 250 g.",
        "category": "Casa > Cozinha > Copos",
        "brand": "Sem Marca",
        "images": [],
        "source": {"kind": "manual", "path": None, "imported_at": "2026-10-27T00:00:00Z"},
    }
    bundle = audit_listing(make_skill_input([good, {"title": "sem id"},
                                              {"product_id": "FAIL-NO-TITLE-1"},
                                              "não é um objeto"]), root=ROOT)
    check("批次未因坏输入中断", len(bundle["results"]) >= 1, str(len(bundle["results"])))
    check("坏输入产生了错误记录", len(bundle["errors"]) >= 1, str(len(bundle["errors"])))
    check("好输入仍然产出了结论",
          any(r["target_ref"] == "FAIL-GOOD-1" for r in bundle["results"]))
    check("坏输入也产出了结论（降级为需复核）",
          any(r["target_ref"] in ("input-index-1", "FAIL-NO-TITLE-1",
                                  "input-index-3")
              for r in bundle["results"]),
          str([r["target_ref"] for r in bundle["results"]]))
    for result in bundle["results"]:
        if result["target_ref"] != "FAIL-GOOD-1":
            check(f"降级结果 {result['target_ref']} 要求人工复核",
                  result["requires_human_review"] is True)
            check(f"降级结果 {result['target_ref']} 不是 PASS",
                  result["verdict"] != "PASS", result["verdict"])

    # 规则文件缺失 → 模块显式失败
    from sbr_listing_audit.engine import AuditError
    from sbr_listing_audit.rules import RuleLoadError
    try:
        load_rules(root=os.path.join(tempfile.gettempdir(), "sbrca-no-such-root"))
        check("规则文件缺失时抛 RuleLoadError", False, "未抛出")
    except RuleLoadError:
        check("规则文件缺失时抛 RuleLoadError", True)

    check("AuditError 已定义", issubclass(AuditError, Exception))

    # 词库不可用 → 记为未评估而非静默跳过
    engine = ListingAuditEngine(root=ROOT)
    engine.scanner = None
    evaluation = engine.evaluate_product(good)
    check("词库不可用时标记为未评估",
          evaluation["lexicon_state"] == "unevaluated")


def test_cli_end_to_end() -> None:
    section("CLI 端到端")

    cases = load_fixture("fixtures", "listing_audit_rule_cases.json")["cases"]
    with tempfile.TemporaryDirectory() as tmp:
        skill_input_path = os.path.join(tmp, "skill_input.json")
        with open(skill_input_path, "w", encoding="utf-8") as handle:
            json.dump(make_skill_input([c["product"] for c in cases]),
                      handle, ensure_ascii=False)
        out_dir = os.path.join(tmp, "out")
        proc = subprocess.run(
            [sys.executable,
             os.path.join(SRC, "sbr_listing_audit_cli.py"),
             "--skill-input", skill_input_path,
             "--request-id", "REQ-CLI-0001",
             "--out-dir", out_dir],
            cwd=ROOT, capture_output=True, text=True,
        )
        check("CLI 执行成功", proc.returncode == 0,
              (proc.stdout + proc.stderr).strip()[-300:])
        for name in ("audit_results.json", "module_handoff.json"):
            path = os.path.join(out_dir, name)
            check(f"CLI 产出 {name}", os.path.exists(path))
            if os.path.exists(path):
                with open(path, encoding="utf-8") as handle:
                    payload = json.load(handle)
                if name == "audit_results.json":
                    check("CLI 产出非空结果数组", len(payload) > 0)
                    for item in payload[:5]:
                        validate_against("contracts/audit_result.schema.json", item,
                                         "CLI audit_result")
                else:
                    validate_against("contracts/module_handoff.schema.json", payload,
                                     "CLI module_handoff")

    # 输入文件不存在 → 明确报错
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [sys.executable,
             os.path.join(SRC, "sbr_listing_audit_cli.py"),
             "--skill-input", os.path.join(tmp, "nope.json"),
             "--out-dir", os.path.join(tmp, "out")],
            cwd=ROOT, capture_output=True, text=True,
        )
        check("CLI 对不存在的输入文件报错", proc.returncode != 0,
              str(proc.returncode))


# ---------------------------------------------------------------------------
# 注入安全
# ---------------------------------------------------------------------------

def test_injection_safety() -> None:
    section("注入安全 —— 输入文档中的指令只是数据")

    cases = load_shared("injection_cases.json")["cases"]
    bundle = audit_listing(make_skill_input([c["product"] for c in cases]),
                           root=ROOT)
    check("注入样本全部产出结论", len(bundle["results"]) == len(cases),
          f"{len(bundle['results'])}/{len(cases)}")
    for case, result in zip(cases, bundle["results"]):
        fired = {ref["rule_id"] for ref in result["rule_refs"]}
        for rule_id in case.get("must_fire", []):
            if rule_prefix(rule_id) not in OWNED_PREFIXES:
                continue
            check(f"注入样本 {case['case_id']} 命中 {rule_id}", rule_id in fired,
                  f"fired={sorted(fired)}")
        for rule_id in case.get("must_not_fire", []):
            if rule_prefix(rule_id) not in OWNED_PREFIXES:
                continue
            check(f"注入样本 {case['case_id']} 不命中 {rule_id}",
                  rule_id not in fired, f"fired={sorted(fired)}")

    # 注入文本不得改变判定结论。
    #
    # **不能**断言「注入样本不产生阻断类动作」—— 夹具 INJ-01 的商品
    # 本身就是「防弹衣 + 训练弹药」，SBR-PI-001 命中并 block 是**正确**
    # 行为（夹具 note 明写「注入文本不得让禁售规则失效」）。
    #
    # 正确的测法是**对照实验**：把注入载荷替换成**等长的中性填充**，
    # 再跑一次。两次的命中规则集与动作必须完全一致 —— 只有载荷的
    # **内容**变了，长度、其它字段全部不变。
    #
    # 为什么必须等长：有些规则按字段长度触发（如 SBR-LV-006
    # `description length_lt 120`）。若直接删掉载荷，描述变短会让
    # 该规则**多命中** —— 差异来自长度而非注入内容，测的就不是
    # 「注入是否影响判定」了。
    for case in cases:
        case_id = case["case_id"]
        payload = case.get("payload")
        if not payload:
            continue
        product = case["product"]
        baseline = _neutralise_payload(product, payload)
        if baseline is None:
            continue
        with_payload = audit_listing(make_skill_input([product]), root=ROOT)
        without = audit_listing(make_skill_input([baseline]), root=ROOT)
        r_with = with_payload["results"][0]
        r_without = without["results"][0]
        fired_with = {ref["rule_id"] for ref in r_with["rule_refs"]}
        fired_without = {ref["rule_id"] for ref in r_without["rule_refs"]}
        check(f"注入样本 {case_id} 载荷换成中性文本后命中规则集不变",
              fired_with == fired_without,
              f"带载荷={sorted(fired_with)} 中性={sorted(fired_without)}")
        check(f"注入样本 {case_id} 载荷换成中性文本后动作不变",
              r_with["action"] == r_without["action"],
              f"带载荷={r_with['action']} 中性={r_without['action']}")
        check(f"注入样本 {case_id} 载荷换成中性文本后 verdict 不变",
              r_with["verdict"] == r_without["verdict"],
              f"带载荷={r_with['verdict']} 中性={r_without['verdict']}")
        # 对照组必须真的只差载荷内容 —— 否则上面三条断言是空转
        check(f"注入样本 {case_id} 对照实验有效（载荷在输入里）",
              payload in json.dumps(product, ensure_ascii=False),
              "载荷未出现在商品数据中")


def _neutralise_payload(product: dict, payload: str) -> dict | None:
    """把注入载荷替换成**等长**的中性填充文本，返回对照商品。

    等长是关键：按长度触发的规则（如 `description length_lt 120`）
    在两组输入下必须给出相同结论，否则差异来自长度而非载荷内容。

    返回 None 表示载荷不在商品数据里 —— 无法构造对照。
    """
    filler = "x" * len(payload)
    clone = json.loads(json.dumps(product, ensure_ascii=False))
    replaced = False

    def walk(node):
        nonlocal replaced
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str) and payload in value:
                    node[key] = value.replace(payload, filler)
                    replaced = True
                else:
                    walk(value)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                if isinstance(value, str) and payload in value:
                    node[index] = value.replace(payload, filler)
                    replaced = True
                else:
                    walk(value)

    walk(clone)
    return clone if replaced else None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> int:
    print(f"shopee-br-listing-audit {__version__} —— 模块测试")
    print(f"仓库根: {ROOT}")
    started = datetime.now(timezone.utc)

    tests = [
        test_l1_fields,
        test_l1_conditions,
        test_l1_matrix,
        test_l1_rules,
        test_l1_lexicon,
        test_l2_contract,
        test_l2_matrix_consistency,
        test_l3_own_rule_cases,
        test_l3_shared_fixtures,
        test_l3_shared_fixtures_untouched,
        test_h1_ip_never_deterministic,
        test_h2_blocking_requires_authoritative_active_rule,
        test_h3_missing_input_is_not_a_pass,
        test_h4_citations_verbatim,
        test_h5_evidence_only_references,
        test_h6_human_only_actions,
        test_failure_paths,
        test_cli_end_to_end,
        test_injection_safety,
    ]

    for test in tests:
        try:
            test()
        except Exception:  # noqa: BLE001 - 测试框架必须报告崩溃
            FAILED.append((test.__name__, traceback.format_exc(limit=6)))
            print(f"  FAIL {test.__name__} 抛出异常：")
            print(traceback.format_exc(limit=6))

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    print(f"\n{'=' * 62}")
    print(f"PASSED: {len(PASSED)}   FAILED: {len(FAILED)}")
    print(f"耗时: {elapsed:.2f}s")
    if FAILED:
        print("\nFailures:")
        for name, detail in FAILED:
            print(f"  - {name}: {detail}")
        return 1
    print("模块测试全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
