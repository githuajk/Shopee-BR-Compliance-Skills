#!/usr/bin/env python3
"""`shopee-br-duplicate-detection` 模块测试（L1–L4）。

覆盖（见 `skills/shopee-br-duplicate-detection/SKILL.md` §10）：

* **L1 单元** —— 归一化、相似度、案件三态、风险矩阵查表
* **L2 契约** —— 三份产出通过冻结契约的 Schema 校验
* **L3 规则** —— 每条规则一个正例 + 一个反例（自有夹具 + 共享夹具）
* **L4 硬约束** —— H1 / H2 / H3 / H4 / H5 / H6 断言

运行：

```bash
env -u LD_LIBRARY_PATH python3 tests/shopee-br-duplicate-detection/run_tests.py
```

**只读**共享夹具（`tests/fixtures/**`）；本模块的自有夹具写在
`tests/shopee-br-duplicate-detection/fixtures/`，运行时**只读加载**，
**任何情况下都不修改输入文件**。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MODULE_DIR = os.path.join(ROOT, "skills", "shopee-br-duplicate-detection")
SRC = os.path.join(MODULE_DIR, "src")

sys.path.insert(0, SRC)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from validate_json import Validator  # noqa: E402

from sbr_duplicate_detection import detect_duplicates  # noqa: E402
from sbr_duplicate_detection.duplicates import DuplicateIndex  # noqa: E402
from sbr_duplicate_detection.matrix import RiskMatrix  # noqa: E402
from sbr_duplicate_detection.normalize import (  # noqa: E402
    dice,
    jaccard,
    norm_sku,
    norm_text,
    stem_token,
    title_tokens,
    trigrams,
)
from sbr_duplicate_detection.relist import (  # noqa: E402
    CASE_ACTIONED,
    CASE_IN_REMEDIATION,
    CASE_RESOLVED,
    RELATION_INHERITS,
    RELATION_SUBJECT,
    case_state,
)
from sbr_duplicate_detection.rules import evaluate_rule, load_rules  # noqa: E402

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


def validate_against(schema_rel: str, payload, label: str) -> bool:
    validator = _validator(schema_rel)
    errors = validator.validate(payload)
    return check(f"{label} 符合 {schema_rel}", not errors, "; ".join(errors[:4]))


# ---------------------------------------------------------------------------
# 输入构造
# ---------------------------------------------------------------------------

FIXTURE_DIR = os.path.join(HERE, "fixtures")
SHARED_FIXTURE_DIR = os.path.join(ROOT, "tests", "fixtures")


def load_json(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def make_input(products, cases=None, request_id="REQ-DUP-TEST-001",
               options=None):
    """构造符合 `contracts/skill_input.schema.json` 的输入。"""
    return {
        "request_id": request_id,
        "task_type": "duplicate_detection",
        "target": {
            "kind": "product_batch",
            "ref": "tests/shopee-br-duplicate-detection/fixtures",
            "count": len(products),
        },
        "products": products,
        "cases": cases or [],
        "rules": [],
        "scope": {},
        "options": options or {},
        "provenance": {
            "inputs": [{
                "path": "tests/shopee-br-duplicate-detection/fixtures/"
                        "duplicate_scenarios.json",
                "kind": "json",
                "digest": None,
                "parsed_at": "2026-10-27T00:00:00Z",
                "parser_version": "sbr-duplicate-detection/1.0.0",
                "records_parsed": len(products),
                "records_failed": 0,
            }],
            "produced_at": "2026-10-27T00:00:00Z",
            "producer": "sbr-duplicate-detection/1.0.0",
        },
    }


def scenario_inputs():
    """自有夹具 → (scenario, skill_input) 列表。"""
    doc = load_json(os.path.join(FIXTURE_DIR, "duplicate_scenarios.json"))
    out = []
    for scenario in doc["scenarios"]:
        out.append((scenario, make_input(
            scenario["products"], scenario["cases"],
            request_id=f"REQ-{scenario['case_id']}")))
    return out


def result_for(bundle, product_id):
    for result in bundle["results"]:
        if result["target_ref"] == product_id:
            return result
    return None


def fired_rules(result) -> set[str]:
    return {ref["rule_id"] for ref in result.get("rule_refs") or []}


def unevaluated_rules(result) -> set[str]:
    return {item["rule_id"] for item in result.get("unevaluated") or []}


# ---------------------------------------------------------------------------
# L1 单元测试
# ---------------------------------------------------------------------------

def test_unit() -> None:
    section("L1 单元测试")

    # --- 1. 归一化 ---
    check("norm_text 折叠重音", norm_text("Descrição") == "descricao",
          norm_text("Descrição"))
    check("norm_text 去标点", norm_text("Kit 4, Panelas!") == "kit 4 panelas",
          norm_text("Kit 4, Panelas!"))
    check("stem_token 折叠葡语词尾 a",
          stem_token("organizadora") == "organizador",
          stem_token("organizadora"))
    check("stem_token 保留短词", stem_token("kit") == "kit", stem_token("kit"))
    check("norm_sku 去分隔符", norm_sku("SUP-001") == "SUP001",
          norm_sku("SUP-001"))
    check("norm_sku 忽略大小写与空格", norm_sku(" sup 001 ") == "SUP001",
          norm_sku(" sup 001 "))
    check("norm_sku 空值返回空串", norm_sku(None) == "", repr(norm_sku(None)))

    # --- 标题词元 ---
    tokens = title_tokens("Promoção Kit 4 Panelas Antiaderente 20cm")
    check("title_tokens 去掉营销词 promoção", "promocao" not in tokens,
          str(tokens))
    check("title_tokens 保留实义词", "panela" in tokens, str(tokens))
    check("title_tokens 去停用词 de", "de" not in tokens, str(tokens))
    check("title_tokens 折叠词尾 a",
          "organizador" in title_tokens("Caixa Organizadora"), str(tokens))

    # --- 相似度 ---
    check("jaccard 完全相同 = 1.0",
          jaccard({"a", "b"}, {"a", "b"}) == 1.0, "")
    check("jaccard 无交集 = 0.0",
          jaccard({"a"}, {"b"}) == 0.0, "")
    check("jaccard 空集 = 0.0", jaccard(set(), {"a"}) == 0.0, "")
    check("dice 部分重叠",
          abs(dice({"a", "b", "c"}, {"b", "c", "d"}) - 2 * 2 / 6.0) < 1e-9,
          str(dice({"a", "b", "c"}, {"b", "c", "d"})))
    check("trigrams 长度 3",
          trigrams("abcd") == {"abc", "bcd"}, str(trigrams("abcd")))

    # --- 案件三态 ---
    check("case_state under_review = 整改中",
          case_state({"status": "under_review", "frozen": True})
          == CASE_IN_REMEDIATION, "")
    check("case_state open = 整改中",
          case_state({"status": "open"}) == CASE_IN_REMEDIATION, "")
    check("case_state awaiting_evidence = 整改中",
          case_state({"status": "awaiting_evidence"}) == CASE_IN_REMEDIATION, "")
    check("case_state blocked = 已处置",
          case_state({"status": "blocked"}) == CASE_ACTIONED, "")
    check("case_state relist_frozen = 已处置",
          case_state({"status": "relist_frozen"}) == CASE_ACTIONED, "")
    check("case_state escalated = 已处置",
          case_state({"status": "escalated"}) == CASE_ACTIONED, "")
    check("case_state rejected = 已处置",
          case_state({"status": "rejected"}) == CASE_ACTIONED, "")
    check("case_state closed 且未冻结 = 已结",
          case_state({"status": "closed", "frozen": False}) == CASE_RESOLVED, "")
    check("case_state approved 且未冻结 = 已结",
          case_state({"status": "approved", "frozen": False}) == CASE_RESOLVED, "")
    check("case_state 未知状态 + frozen=true = 已处置",
          case_state({"status": "weird", "frozen": True}) == CASE_ACTIONED, "")

    # --- 风险矩阵 ---
    matrix = RiskMatrix.load(ROOT)
    check("风险矩阵装载成功", matrix.load_error is None, matrix.load_error or "")
    check("矩阵 verdict: allow → PASS",
          matrix.verdict_for("allow") == "PASS", matrix.verdict_for("allow"))
    check("矩阵 verdict: flag_for_review → REVIEW",
          matrix.verdict_for("flag_for_review") == "REVIEW",
          matrix.verdict_for("flag_for_review"))
    check("矩阵 verdict: freeze_relist → BLOCK",
          matrix.verdict_for("freeze_relist") == "BLOCK",
          matrix.verdict_for("freeze_relist"))
    check("矩阵 medium + freeze_relist 不允许",
          not matrix.is_allowed("medium", "freeze_relist"), "")
    check("矩阵 high + freeze_relist 允许",
          matrix.is_allowed("high", "freeze_relist"), "")
    check("矩阵 info + allow 允许", matrix.is_allowed("info", "allow"), "")

    # --- 重复索引 ---
    index = DuplicateIndex()
    index.add({"product_id": "P1", "shop_id": "S1", "internal_sku": "A",
               "title": "Kit 4 Panelas Antiaderente 20cm",
               "description": "Conjunto com 4 panelas de alumínio."})
    index.add({"product_id": "P2", "shop_id": "S1", "internal_sku": "A",
               "title": "Kit 4 Panelas Antiaderente 20cm",
               "description": "Conjunto com 4 panelas de alumínio."})
    matches = index.find_all()
    check("重复索引找到 1 对同店重复", len(matches) == 1, str(len(matches)))
    if matches:
        check("重复索引标记 same_shop",
              matches[0].same_shop is True, str(matches[0].same_shop))
        check("重复索引命中身份轴 internal_sku",
              "internal_sku" in matches[0].axes, str(matches[0].axes))
        check("重复索引给出双方 ID",
              {matches[0].product_id, matches[0].other_product_id}
              == {"P1", "P2"}, str(matches[0].to_dict()))

    # --- 规则装载 ---
    rules = load_rules(root=ROOT)
    rule_ids = {rule["rule_id"] for rule in rules}
    expected = {"SBR-DUP-001", "SBR-DUP-002", "SBR-DUP-003",
                "SBR-RL-001", "SBR-RL-002", "SBR-AU-001",
                "SBR-AC-001", "SBR-AC-002"}
    check("装载到本模块拥有的 8 条规则", rule_ids == expected,
          str(sorted(rule_ids ^ expected)))
    check("未装载其它模块的 LV 前缀规则",
          not any(rid.startswith("SBR-LV-") for rid in rule_ids),
          str(sorted(rule_ids)))
    check("未装载其它模块的 IP 前缀规则",
          not any(rid.startswith("SBR-IP-") for rid in rule_ids),
          str(sorted(rule_ids)))


# ---------------------------------------------------------------------------
# L2 契约测试
# ---------------------------------------------------------------------------

def test_contract() -> None:
    section("L2 契约测试")

    scenarios = scenario_inputs()
    if not check("自有夹具至少 10 个场景", len(scenarios) >= 10,
                 str(len(scenarios))):
        return

    all_results = []
    for scenario, skill_input in scenarios:
        bundle = detect_duplicates(skill_input, root=ROOT)
        all_results.extend(bundle["results"])

        validate_against("contracts/skill_input.schema.json", skill_input,
                         f"{scenario['case_id']} 的 SkillInput")
        validate_against("contracts/module_handoff.schema.json",
                         bundle["handoff"], f"{scenario['case_id']} 的 ModuleHandoff")
        for result in bundle["results"]:
            validate_against("contracts/audit_result.schema.json", result,
                             f"{scenario['case_id']}/{result['target_ref']} "
                             f"的 AuditResult")

        # --- 字段级断言 ---
        for result in bundle["results"]:
            check(f"{scenario['case_id']}/{result['target_ref']}: module 固定",
                  result["module"] == "shopee-br-duplicate-detection",
                  result["module"])
            check(f"{scenario['case_id']}/{result['target_ref']}: request_id 回填",
                  result["request_id"] == skill_input["request_id"],
                  result["request_id"])
            check(f"{scenario['case_id']}/{result['target_ref']}: "
                  f"provenance.produced_at 非空",
                  bool(result["provenance"].get("produced_at")),
                  str(result["provenance"]))
            check(f"{scenario['case_id']}/{result['target_ref']}: "
                  f"provenance.producer 含模块名",
                  "shopee-br-duplicate-detection"
                  in result["provenance"].get("producer", ""),
                  result["provenance"].get("producer", ""))
            check(f"{scenario['case_id']}/{result['target_ref']}: "
                  f"reason 长度 ≥ 5",
                  len(result["reason"]) >= 5, result["reason"])

        handoff = bundle["handoff"]
        check(f"{scenario['case_id']}: handoff.assumptions 非空",
              len(handoff["assumptions"]) >= 1, str(handoff["assumptions"]))
        check(f"{scenario['case_id']}: handoff.known_gaps 非空",
              len(handoff["known_gaps"]) >= 1, str(handoff["known_gaps"]))
        check(f"{scenario['case_id']}: handoff.record_count 正确",
              handoff["payload_ref"]["record_count"] == len(bundle["results"]),
              str(handoff["payload_ref"]["record_count"]))
        check(f"{scenario['case_id']}: handoff.contract_version 语义化",
              bool(re.fullmatch(r"\d+\.\d+\.\d+", handoff["contract_version"])),
              handoff["contract_version"])

    check("全部场景产出的 AuditResult 都通过契约校验",
          all("AuditResult" not in name for name, _ in FAILED),
          str([n for n, _ in FAILED if "AuditResult" in n][:3]))


# ---------------------------------------------------------------------------
# L3 规则测试（每条规则正例 + 反例）
# ---------------------------------------------------------------------------

def test_rules() -> None:
    section("L3 规则测试")

    scenarios = scenario_inputs()
    coverage = {rule_id: {"fire": 0, "no_fire": 0}
                for rule_id in ("SBR-DUP-001", "SBR-DUP-002", "SBR-DUP-003",
                                "SBR-RL-001", "SBR-RL-002", "SBR-AU-001",
                                "SBR-AC-001", "SBR-AC-002")}

    for scenario, skill_input in scenarios:
        bundle = detect_duplicates(skill_input, root=ROOT)
        results = {r["target_ref"]: r for r in bundle["results"]}

        expect = scenario.get("expect") or {}
        focus = expect.get("on")
        if focus and focus in results:
            result = results[focus]
            if "verdict" in expect:
                check(f"{scenario['case_id']}/{focus}: verdict = "
                      f"{expect['verdict']}",
                      result["verdict"] == expect["verdict"],
                      f"{result['verdict']} (期望 {expect['verdict']})")
            if "action" in expect:
                check(f"{scenario['case_id']}/{focus}: action = "
                      f"{expect['action']}",
                      result["action"] == expect["action"],
                      f"{result['action']} (期望 {expect['action']})")
            if "confidence" in expect:
                check(f"{scenario['case_id']}/{focus}: confidence = "
                      f"{expect['confidence']}",
                      result["confidence"] == expect["confidence"],
                      f"{result['confidence']} (期望 {expect['confidence']})")

        for product_id, result in results.items():
            fired = fired_rules(result)
            unevaluated = unevaluated_rules(result)
            for rule_id in fired:
                coverage[rule_id]["fire"] += 1
            # 未命中的规则都算作反例证据（该商品在该规则上不命中）。
            for rule_id in coverage:
                if rule_id not in fired:
                    coverage[rule_id]["no_fire"] += 1
            for rule_id in scenario.get("must_fire") or []:
                # must_fire 只对「焦点商品」断言 —— 场景里的其它商品
                # （如历史商品）本就不该命中。
                if focus and product_id != focus:
                    continue
                check(f"{scenario['case_id']}/{product_id}: 必须命中 "
                      f"{rule_id}",
                      rule_id in fired,
                      f"命中={sorted(fired)} 未评估={sorted(unevaluated)}")
            for rule_id in scenario.get("must_not_fire") or []:
                if focus and product_id != focus:
                    continue
                check(f"{scenario['case_id']}/{product_id}: 不得命中 "
                      f"{rule_id}",
                      rule_id not in fired,
                      f"命中={sorted(fired)}")

    # --- 每条规则都有正例与反例 ---
    for rule_id, counts in sorted(coverage.items()):
        check(f"{rule_id} 有正例", counts["fire"] >= 1,
              f"fire={counts['fire']} no_fire={counts['no_fire']}")
        check(f"{rule_id} 有反例", counts["no_fire"] >= 1,
              f"fire={counts['fire']} no_fire={counts['no_fire']}")

    # --- 共享夹具：正常商品池作为反例来源 ---
    shared_normal = load_json(
        os.path.join(SHARED_FIXTURE_DIR, "normal_products.json"))["products"]
    shared_cases = load_json(
        os.path.join(SHARED_FIXTURE_DIR, "case_history.json"))["cases"]
    bundle = detect_duplicates(
        make_input(shared_normal, shared_cases,
                   request_id="REQ-SHARED-NORMAL"), root=ROOT)
    shared_results = {r["target_ref"]: r for r in bundle["results"]}

    # 共享夹具里 FX-NORM-0005 / FX-NORM-0006 是跨店同款对照组
    for product_id in ("FX-NORM-0005", "FX-NORM-0006"):
        result = shared_results.get(product_id)
        if check(f"共享夹具 {product_id} 有结果", result is not None, ""):
            check(f"共享夹具 {product_id}: 命中 SBR-DUP-002",
                  "SBR-DUP-002" in fired_rules(result),
                  str(sorted(fired_rules(result))))
            check(f"共享夹具 {product_id}: 不得命中 SBR-DUP-001",
                  "SBR-DUP-001" not in fired_rules(result),
                  str(sorted(fired_rules(result))))

    # 共享夹具里其它正常商品不得命中重复规则
    for product_id, result in shared_results.items():
        if product_id in ("FX-NORM-0005", "FX-NORM-0006"):
            continue
        check(f"共享夹具 {product_id}: 正常商品不命中任何重复规则",
              not (fired_rules(result) & {"SBR-DUP-001", "SBR-DUP-002",
                                         "SBR-DUP-003"}),
              str(sorted(fired_rules(result))))

    # 共享案件历史：FX-NORM-0012 挂在 under_review 案件上 → 不冻结
    result = shared_results.get("FX-NORM-0012")
    if check("共享夹具 FX-NORM-0012 有结果", result is not None, ""):
        check("共享夹具 FX-NORM-0012: 命中 SBR-RL-001（整改中）",
              "SBR-RL-001" in fired_rules(result),
              str(sorted(fired_rules(result))))
        check("共享夹具 FX-NORM-0012: 不得命中 SBR-RL-002（不得冻结）",
              "SBR-RL-002" not in fired_rules(result),
              str(sorted(fired_rules(result))))
        check("共享夹具 FX-NORM-0012: action 不是 freeze_relist",
              result["action"] != "freeze_relist", result["action"])


# ---------------------------------------------------------------------------
# L4 硬约束测试
# ---------------------------------------------------------------------------

def test_hard_constraints() -> None:
    section("L4 硬约束测试")

    scenarios = scenario_inputs()
    all_results = []
    for scenario, skill_input in scenarios:
        bundle = detect_duplicates(skill_input, root=ROOT)
        all_results.extend(bundle["results"])

    # --- H1：IP 类结论恒为 signal + 强制人工复核 ---
    ip_results = [r for r in all_results if "OWN-IP-01" in r["result_id"]]
    check("H1: 有 IP 投诉关联的结果可检验", len(ip_results) >= 1,
          str(len(ip_results)))
    for result in ip_results:
        check(f"H1: {result['target_ref']} confidence = signal",
              result["confidence"] == "signal", result["confidence"])
        check(f"H1: {result['target_ref']} requires_human_review = true",
              result["requires_human_review"] is True,
              str(result["requires_human_review"]))
        check(f"H1: {result['target_ref']} action 不是 escalate_legal",
              result["action"] != "escalate_legal", result["action"])
        check(f"H1: {result['target_ref']} action 不是 freeze_relist",
              result["action"] != "freeze_relist", result["action"])

    # 本模块不产生 IP 类 category 的 rule_ref
    ip_categories = {"ip_trademark", "ip_copyright", "ip_design", "ip_patent"}
    for result in all_results:
        for ref in result.get("rule_refs") or []:
            check(f"H1: {result['target_ref']} 未引用 IP 类规则",
                  not str(ref.get("rule_id", "")).startswith("SBR-IP-"),
                  ref.get("rule_id", ""))

    # --- H2：internal_risk / unverified 不能产生阻断类动作 ---
    internal_risk_rule = {
        "rule_id": "SBR-DUP-001",
        "title": "Duplicate listing within the same store",
        "category": "duplicate_listing",
        "description": "internal_risk tier test rule for the H2 assertion.",
        "severity": "high",
        "action": "freeze_relist",
        "status": "active",
        "version": 1,
        "evidence_required": [],
        "requires_human_review": True,
        "trigger_conditions": [
            {"field": "any_text", "operator": "contains_any",
             "value": ["__DUPLICATE_SIGNAL__"]}
        ],
        "source": {
            "tier": "internal_risk",
            "url": "https://seller.shopee.com.br/edu/article/5139",
            "excerpt": "[401] Cópia de outro(s) anúncio(s). Severidade: Baixa. "
                       "Não gera ponto de penalidade.",
            "last_verified": "2026-10-27",
        },
    }
    matrix = RiskMatrix.load(ROOT)
    resolved = matrix.resolve("high", "freeze_relist", "internal_risk", "active")
    check("H2: internal_risk 的 freeze_relist 被降级",
          resolved["action"] == "flag_for_review", resolved["action"])
    check("H2: 降级原因写明 H2",
          "H2" in resolved["reason"], resolved["reason"])

    resolved = matrix.resolve("high", "block", "unverified", "active")
    check("H2: unverified 的 block 被降级",
          resolved["action"] == "flag_for_review", resolved["action"])
    resolved = matrix.resolve("high", "block", "ai_inference", "active")
    check("H2: ai_inference 的 block 被降级",
          resolved["action"] == "flag_for_review", resolved["action"])
    resolved = matrix.resolve("high", "block", "platform_official", "active")
    check("H2: platform_official 的 block 不降级",
          resolved["action"] == "block", resolved["action"])
    resolved = matrix.resolve("high", "freeze_relist", "platform_official",
                              "draft")
    check("H2: 非 active 规则的 freeze_relist 被降级",
          resolved["action"] == "flag_for_review", resolved["action"])

    # 用真实的规则信封跑一遍：把 DUP-001 换成 internal_risk 的版本
    dup01 = json.loads(json.dumps(internal_risk_rule))
    scenario, skill_input = next(
        (s, si) for s, si in scenarios if s["case_id"] == "OWN-DUP-01")
    skill_input = dict(skill_input)
    skill_input["rules"] = [dup01]
    bundle = detect_duplicates(skill_input, root=ROOT)
    for result in bundle["results"]:
        check(f"H2 端到端: {result['target_ref']} action 不是阻断类",
              result["action"] not in ("block", "freeze_relist",
                                       "escalate_legal"),
              result["action"])

    # 全量结果的 H2 断言
    for result in all_results:
        check(f"H2: {result['target_ref']} action 与 source_tier 相容",
              _tier_action_ok(result), json.dumps(
                  [r.get("source_tier") for r in result.get("rule_refs") or []],
                  ensure_ascii=False))

    # --- H3：缺输入 → unevaluated 非空，不产生 PASS ---
    # 构造一个**完全没有案件历史**的批次：重发规则无法评估。
    no_cases_scenario, no_cases_input = next(
        (s, si) for s, si in scenarios if s["case_id"] == "OWN-DUP-01")
    no_cases_input = make_input(
        no_cases_scenario["products"], [],
        request_id="REQ-DUP-NOCASES")
    bundle = detect_duplicates(no_cases_input, root=ROOT)
    for result in bundle["results"]:
        check(f"H3: {result['target_ref']} 无案件时 unevaluated 非空",
              len(result["unevaluated"]) >= 1,
              str([u["rule_id"] for u in result["unevaluated"]]))
        check(f"H3: {result['target_ref']} 无案件时 verdict != PASS",
              result["verdict"] != "PASS", result["verdict"])
        check(f"H3: {result['target_ref']} 无案件时 errors 含 "
              f"stage=rule_evaluation 的 warning",
              any(e.get("stage") == "rule_evaluation"
                  and e.get("severity") == "warning"
                  for e in result.get("errors") or []),
              str([(e.get("stage"), e.get("severity"))
                   for e in result.get("errors") or []]))

    # 缺 cases 的输入 → 重发规则必须进 unevaluated
    check("H3: 无案件时重发规则进 unevaluated",
          {"SBR-RL-001", "SBR-RL-002"}
          <= unevaluated_rules(bundle["results"][0]),
          str(sorted(unevaluated_rules(bundle["results"][0]))))

    # 边界：字段存在但为空 == 缺失
    empty_product = dict(no_cases_input["products"][0])
    empty_product["title"] = ""
    empty_input = make_input([empty_product], [], request_id="REQ-DUP-EMPTY")
    bundle = detect_duplicates(empty_input, root=ROOT)
    result = bundle["results"][0]
    check("H3 边界: 标题为空 → 重复规则未评估",
          {"SBR-DUP-001", "SBR-DUP-002", "SBR-DUP-003"}
          & unevaluated_rules(result) != set(),
          str(sorted(unevaluated_rules(result))))
    check("H3 边界: 标题为空 → 不判 PASS", result["verdict"] != "PASS",
          result["verdict"])

    # 单店铺批次 → 跨店规则未评估
    single_shop_input = make_input(
        [no_cases_scenario["products"][0]], [], request_id="REQ-DUP-ONESHOP")
    bundle = detect_duplicates(single_shop_input, root=ROOT)
    result = bundle["results"][0]
    check("H3: 单店铺批次 → SBR-DUP-002 未评估",
          "SBR-DUP-002" in unevaluated_rules(result),
          str(sorted(unevaluated_rules(result))))
    check("H3: 单店铺批次 → 不判 PASS", result["verdict"] != "PASS",
          result["verdict"])

    # 跨店比对被关闭 → 跨店规则未评估
    disabled_products = [p for s, si in scenarios
                         if s["case_id"] == "OWN-DUP-02" for p in s["products"]]
    disabled_input = make_input(
        disabled_products, [], request_id="REQ-DUP-NOCROSS",
        options={"cross_store": False})
    bundle = detect_duplicates(disabled_input, root=ROOT)
    for result in bundle["results"]:
        check("H3: cross_store=false → SBR-DUP-002 未评估",
              "SBR-DUP-002" in unevaluated_rules(result),
              str(sorted(unevaluated_rules(result))))
        check("H3: cross_store=false → 不命中 SBR-DUP-002",
              "SBR-DUP-002" not in fired_rules(result),
              str(sorted(fired_rules(result))))

    # --- H4：引文逐字核验 ---
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "verify_citations.py")],
        cwd=ROOT, capture_output=True, text=True)
    check("H4: tools/verify_citations.py 退出码 0",
          proc.returncode == 0, proc.stdout[-400:] + proc.stderr[-200:])
    check("H4: 引文核验 0 失败",
          "0 failed" in proc.stdout, proc.stdout[-200:])

    # 本模块规则的引文必须逐字出现在抓取件中
    rules = load_rules(root=ROOT)
    raw_dir = os.path.join(ROOT, "research", "raw")
    raw_text = ""
    for name in sorted(os.listdir(raw_dir)):
        if name.endswith(".txt"):
            with open(os.path.join(raw_dir, name), encoding="utf-8") as handle:
                raw_text += handle.read() + "\n"

    def _loose(text: str) -> str:
        text = text.lower()
        text = re.sub(r"[,.;:]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    loose_raw = _loose(raw_text)
    for rule in rules:
        excerpt = rule.get("source_excerpt") or ""
        check(f"H4: {rule['rule_id']} 的引文逐字出现在抓取件中",
              bool(excerpt) and _loose(excerpt) in loose_raw,
              excerpt[:80])
        check(f"H4: {rule['rule_id']} 的 last_verified 已填",
              bool(rule.get("last_verified")), str(rule.get("last_verified")))

    # --- H5：证据引用只存引用，不内嵌凭证内容 ---
    credential_patterns = [r"sk-[A-Za-z0-9]{16,}", r"ghp_[A-Za-z0-9]{16,}",
                           r"-----BEGIN [A-Z ]*PRIVATE KEY-----"]
    for result in all_results:
        for ref in result.get("evidence_refs") or []:
            artifact = ref.get("artifact_ref") or ""
            check(f"H5: {result['target_ref']} 证据 {ref['evidence_id']} "
                  f"不含凭证特征",
                  not any(re.search(p, artifact) for p in credential_patterns),
                  artifact[:80])
            check(f"H5: {result['target_ref']} 证据 {ref['evidence_id']} "
                  f"是引用而非内容",
                  len(artifact) < 300 and "\n" not in artifact,
                  artifact[:120])

    # --- H6：freeze_relist / escalate_legal 是 human_only ---
    freeze_results = [r for r in all_results
                      if r["action"] in ("freeze_relist", "escalate_legal")]
    check("H6: 至少有一个 freeze_relist 结果可检验",
          len(freeze_results) >= 1, str(len(freeze_results)))
    for result in freeze_results:
        check(f"H6: {result['target_ref']} requires_human_review = true",
              result["requires_human_review"] is True,
              str(result["requires_human_review"]))
        check(f"H6: {result['target_ref']} 有 review_rationale",
              bool(result.get("review_rationale")),
              str(result.get("review_rationale")))
        check(f"H6: {result['target_ref']} review_rationale 提到 human_only",
              "human_only" in (result.get("review_rationale") or ""),
              str(result.get("review_rationale")))

    # 模块不得提供任何执行 freeze_relist / 解冻的入口
    src_files = []
    for dirpath, dirnames, filenames in os.walk(SRC):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            if name.endswith(".py"):
                src_files.append(os.path.join(dirpath, name))
    forbidden = re.compile(
        r"\b(def\s+(unfreeze|release_relist|execute_freeze|apply_freeze)"
        r"|requests\.(post|put|delete)|urlopen|http\.client)", re.IGNORECASE)
    offenders = []
    for path in src_files:
        with open(path, encoding="utf-8") as handle:
            body = handle.read()
        if forbidden.search(body):
            offenders.append(os.path.relpath(path, ROOT))
    check("H6: 模块不提供任何解冻/线上执行入口", not offenders, str(offenders))


def _tier_action_ok(result) -> bool:
    """H2 的结果级断言：阻断类动作必须来自 platform_official/law 的 active 规则。"""
    if result["action"] not in ("block", "freeze_relist", "escalate_legal"):
        return True
    for ref in result.get("rule_refs") or []:
        if ref.get("source_tier") in ("platform_official", "law"):
            return True
    return False


# ---------------------------------------------------------------------------
# 失败路径测试
# ---------------------------------------------------------------------------

def test_failure_paths() -> None:
    section("失败路径测试")

    scenarios = scenario_inputs()

    # --- 输入不可读：products 不是数组 ---
    broken = make_input([], [], request_id="REQ-DUP-BROKEN")
    broken["products"] = "not-a-list"
    bundle = detect_duplicates(broken, root=ROOT)
    check("失败路径: products 类型错误 → 不产生 PASS",
          all(r["verdict"] != "PASS" for r in bundle["results"]),
          str([r["verdict"] for r in bundle["results"]]))
    check("失败路径: products 类型错误 → 记 error",
          any(e.get("severity") == "fatal" for e in bundle["errors"]),
          str([(e.get("stage"), e.get("severity")) for e in bundle["errors"]]))
    check("失败路径: products 类型错误 → 交接 known_gaps 非空",
          len(bundle["handoff"]["known_gaps"]) >= 1,
          str(bundle["handoff"]["known_gaps"]))

    # --- 规则文件不可读 → 模块停摆，但不中断 ---
    scenario, skill_input = next(
        (s, si) for s, si in scenarios if s["case_id"] == "OWN-DUP-01")
    bundle = detect_duplicates(skill_input, root="/nonexistent-root")
    check("失败路径: 规则库不可用 → 记 fatal",
          any(e.get("severity") == "fatal" for e in bundle["errors"]),
          str([(e.get("stage"), e.get("severity")) for e in bundle["errors"]]))
    check("失败路径: 规则库不可用 → 不产生 PASS",
          all(r["verdict"] != "PASS" for r in bundle["results"]),
          str([r["verdict"] for r in bundle["results"]]))
    check("失败路径: 规则库不可用 → 每件商品都有 unevaluated",
          all(len(r["unevaluated"]) >= 1 for r in bundle["results"]),
          str([len(r["unevaluated"]) for r in bundle["results"]]))
    check("失败路径: 规则库不可用 → 交接 known_gaps 提及缺失",
          any("rule library" in g for g in bundle["handoff"]["known_gaps"]),
          str(bundle["handoff"]["known_gaps"]))

    # --- 单个商品缺字段 → 记 error，不中断整批 ---
    scenario, skill_input = next(
        (s, si) for s, si in scenarios if s["case_id"] == "OWN-DUP-01")
    products = [dict(p) for p in scenario["products"]]
    products[0]["shop_id"] = ""
    partial = make_input(products, scenario["cases"],
                          request_id="REQ-DUP-PARTIAL")
    bundle = detect_duplicates(partial, root=ROOT)
    check("失败路径: 单个商品缺字段 → 整批仍产出结果",
          len(bundle["results"]) == len(products),
          str(len(bundle["results"])))
    check("失败路径: 单个商品缺字段 → 缺字段的商品未评估",
          any("SBR-DUP-001" in unevaluated_rules(r)
              for r in bundle["results"]),
          str([sorted(unevaluated_rules(r)) for r in bundle["results"]]))
    check("失败路径: 单个商品缺字段 → 缺字段的商品不判 PASS",
          any(r["verdict"] != "PASS" for r in bundle["results"]),
          str([r["verdict"] for r in bundle["results"]]))

    # --- cases 类型错误 → 记 error，不中断 ---
    scenario, skill_input = next(
        (s, si) for s, si in scenarios if s["case_id"] == "OWN-RL-01")
    broken_cases = make_input(scenario["products"], [],
                              request_id="REQ-DUP-BADCASES")
    broken_cases["cases"] = {"oops": True}
    bundle = detect_duplicates(broken_cases, root=ROOT)
    check("失败路径: cases 类型错误 → 记 error",
          any(e.get("stage") == "input" for e in bundle["errors"]),
          str([(e.get("stage"), e.get("severity")) for e in bundle["errors"]]))
    check("失败路径: cases 类型错误 → 仍产出全部结果",
          len(bundle["results"]) == len(scenario["products"]),
          str(len(bundle["results"])))

    # --- 空批次 → 不崩溃 ---
    empty = make_input([], [], request_id="REQ-DUP-EMPTY-BATCH")
    bundle = detect_duplicates(empty, root=ROOT)
    check("失败路径: 空批次 → 不崩溃且产出空结果",
          bundle["results"] == [], str(len(bundle["results"])))
    check("失败路径: 空批次 → 交接 assumptions 非空",
          len(bundle["handoff"]["assumptions"]) >= 1, "")


# ---------------------------------------------------------------------------
# CLI 测试
# ---------------------------------------------------------------------------

def test_cli() -> None:
    section("CLI 测试")

    import tempfile

    scenario, skill_input = next(
        (s, si) for s, si in scenario_inputs() if s["case_id"] == "OWN-RL-01")
    with tempfile.TemporaryDirectory() as tmp:
        input_path = os.path.join(tmp, "skill_input.json")
        with open(input_path, "w", encoding="utf-8") as handle:
            json.dump(skill_input, handle, ensure_ascii=False)
        before = os.path.getmtime(input_path)

        out_dir = os.path.join(tmp, "out")
        proc = subprocess.run(
            [sys.executable,
             os.path.join(SRC, "sbr_duplicate_detection_cli.py"),
             "--skill-input", input_path, "--out-dir", out_dir, "--quiet"],
            cwd=ROOT, capture_output=True, text=True)
        check("CLI: 退出码 0", proc.returncode == 0,
              proc.stdout[-400:] + proc.stderr[-400:])
        for name in ("skill_input.json", "audit_results.json",
                     "module_handoff.json"):
            check(f"CLI: 产出 {name}",
                  os.path.exists(os.path.join(out_dir, name)), name)

        with open(os.path.join(out_dir, "audit_results.json"),
                  encoding="utf-8") as handle:
            results = json.load(handle)
        check("CLI: audit_results.json 是数组", isinstance(results, list),
              type(results).__name__)
        if results:
            validate_against("contracts/audit_result.schema.json", results[0],
                             "CLI 产出的 AuditResult")

        check("CLI: 不修改输入文件", os.path.getmtime(input_path) == before,
              "mtime 变化")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 62)
    print("shopee-br-duplicate-detection 模块测试")
    print(f"仓库根: {ROOT}")
    print("=" * 62)

    test_unit()
    test_contract()
    test_rules()
    test_hard_constraints()
    test_failure_paths()
    test_cli()

    print("\n" + "=" * 62)
    print(f"PASSED: {len(PASSED)}   FAILED: {len(FAILED)}")
    if FAILED:
        print("\nFailures:")
        for name, detail in FAILED[:40]:
            print(f"  - {name}: {detail}")
        return 1
    print("全部测试通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
