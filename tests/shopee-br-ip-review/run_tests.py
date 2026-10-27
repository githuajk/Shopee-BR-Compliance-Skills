#!/usr/bin/env python3
"""shopee-br-ip-review 模块测试。

运行：
    env -u LD_LIBRARY_PATH python3 tests/shopee-br-ip-review/run_tests.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "skills", "shopee-br-ip-review", "src")
sys.path.insert(0, SRC)

from sbr_ip_review import engine  # noqa: E402
from sbr_ip_review import rules as rules_mod  # noqa: E402

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name: str, cond: bool, detail: str = "") -> bool:
    if cond:
        PASSED.append(name)
    else:
        FAILED.append((name, detail))
    return bool(cond)


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def load(path: str):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def load_shared(name: str):
    return load(os.path.join("tests", "fixtures", name))


def review(products, request_id="REQ-IP-TEST", options=None):
    opts = {"root": ROOT}
    opts.update(options or {})
    return engine.review_products(
        {"request_id": request_id, "products": products}, options=opts)


# ---------------------------------------------------------------------------
def test_fixture_cases() -> None:
    section("L1 共享夹具 —— IP 场景逐条判定")

    cases = load_shared("ip_cases.json")["cases"]
    check("ip_cases.json 有用例", len(cases) >= 7, str(len(cases)))

    for case in cases:
        cid = case["case_id"]
        result = review([case["product"]], request_id=f"REQ-{cid}")["results"][0]
        fired = {ref["rule_id"] for ref in result["rule_refs"]}
        for rule_id in case.get("must_fire", []):
            check(f"{cid} 命中 {rule_id}", rule_id in fired, f"fired={sorted(fired)}")
        for rule_id in case.get("must_not_fire", []):
            check(f"{cid} 不命中 {rule_id}", rule_id not in fired,
                  f"fired={sorted(fired)}")


def test_h1_never_deterministic() -> None:
    section("L2 硬约束 H1 —— IP 结论恒为 signal + 强制人工复核")

    cases = load_shared("ip_cases.json")["cases"]
    bundle = review([c["product"] for c in cases])
    for result in bundle["results"]:
        check(f"{result['target_ref']} 的 confidence 是 signal",
              result["confidence"] == "signal", result["confidence"])
        check(f"{result['target_ref']} 需要人工复核",
              result["requires_human_review"] is True,
              str(result["requires_human_review"]))
        check(f"{result['target_ref']} 的 review_rationale 非空",
              bool(result.get("review_rationale")), "")

    # 命中 IP 规则的商品，绝不能得出 confirmed / likely
    ip_hits = [r for r in bundle["results"] if r["rule_refs"]]
    check("有 IP 命中的结果不为 confirmed",
          all(r["confidence"] != "confirmed" for r in ip_hits),
          str([r["confidence"] for r in ip_hits]))
    check("有 IP 命中的结果不为 likely",
          all(r["confidence"] != "likely" for r in ip_hits),
          str([r["confidence"] for r in ip_hits]))

    # 故障注入式验证：直接调 _confidence 也不该给出确定性结论
    views, _errors = rules_mod.load_rules(root=ROOT)
    for view in views:
        if view.category not in rules_mod.IP_CATEGORIES:
            continue
        details = [{"field": "title", "operator": "regex", "excerpt": "x"}]
        fake_engine = engine.engine.__new__(engine.engine) \
            if hasattr(engine, "engine") else None
        # 用真实引擎路径验证：构造一个只含该规则的引擎
        from sbr_ip_review.engine import _review_one
        from sbr_ip_review.matrix import ActionMatrix
        matrix = ActionMatrix.load(ROOT)
        product = {
            "product_id": "H1-PROBE", "internal_sku": "H1-PROBE",
            "shop_id": "IP-SHOP", "title": "Nike", "description": "nike",
            "category": "Teste", "brand": "Nike", "images": [],
            "source": {"kind": "manual", "path": None,
                       "imported_at": "2026-10-27T00:00:00Z"},
        }
        result, _detail = _review_one(product, "H1-PROBE", "REQ-H1",
                                      "2026-10-27T00:00:00Z", [view], matrix)
        check(f"{view.rule_id} 的结论 confidence=signal（H1 直接验证）",
              result["confidence"] == "signal", result["confidence"])
        break


def test_nominative_use_exemption() -> None:
    section("L3 指示性使用豁免（Lei 9.279/1996 Art. 132, II）")

    cases = {c["case_id"]: c for c in load_shared("ip_cases.json")["cases"]}
    case = cases["IP-03"]
    result = review([case["product"]], request_id="REQ-IP-03")["results"][0]
    fired = {ref["rule_id"] for ref in result["rule_refs"]}

    check("指示性使用命中 SBR-IP-006", "SBR-IP-006" in fired, f"fired={sorted(fired)}")
    check("指示性使用不判品牌宣称 SBR-IP-001",
          "SBR-IP-001" not in fired, f"fired={sorted(fired)}")
    check("指示性使用 verdict 不是 BLOCK", result["verdict"] != "BLOCK",
          result["verdict"])
    # 该夹具没有图片与授权清单 —— 图片维度与授权维度**无法评估**。
    # 按硬约束 H3，未评估的维度不得被当作「通过」：动作升级到人工复核，
    # 但**不得**是 BLOCK（品牌宣称已被指示性使用豁免）。
    check("指示性使用不产生阻断类动作",
          result["action"] not in ("block", "freeze_relist", "escalate_legal"),
          result["action"])
    check("指示性使用因未评估维度而升级为人工复核",
          result["action"] == "flag_for_review", result["action"])
    check("指示性使用记录了未评估的维度",
          len(result["unevaluated"]) >= 1,
          str([u["rule_id"] for u in result["unevaluated"]]))
    check("未评估条目列出具体缺失字段",
          all(u.get("missing_fields") for u in result["unevaluated"]),
          str(result["unevaluated"][:1]))
    check("豁免理由被记录（可审计）",
          "Art. 132" in (result["reason"] or ""), result["reason"][:150])
    check("豁免仍然要求人工复核（H1 不因豁免而放松）",
          result["requires_human_review"] is True)

    # 假货宣称不受 Art. 132 保护
    case2 = cases["IP-02"]
    result2 = review([case2["product"]], request_id="REQ-IP-02")["results"][0]
    fired2 = {ref["rule_id"] for ref in result2["rule_refs"]}
    check("假货宣称仍命中 SBR-IP-002", "SBR-IP-002" in fired2,
          f"fired={sorted(fired2)}")


def test_h2_blocking_requires_authoritative_rule() -> None:
    section("L4 硬约束 H2 —— 阻断类动作只来自权威 active 规则")

    # 注入一条 internal_risk 的 escalate_legal 规则
    injected = {
        "rule_id": "SBR-IP-900",
        "title": "Injected internal-risk IP rule",
        "category": "ip_trademark",
        "description": "injected rule used to prove H2 enforcement",
        "severity": "critical",
        "action": "escalate_legal",
        "source": {"tier": "internal_risk", "url": "https://example.invalid/ip",
                   "excerpt": "x", "last_verified": "2026-10-27"},
        "status": "active",
        "version": 1,
        "evidence_required": [],
        "requires_human_review": True,
        "trigger_conditions": [{"field": "title", "operator": "regex",
                                "value": "copos"}],
    }
    product = {
        "product_id": "H2-IP-1", "internal_sku": "H2-IP-1",
        "shop_id": "IP-SHOP", "title": "Kit 4 Copos de Vidro",
        "description": "x" * 200, "category": "Casa", "brand": "Sem Marca",
        "images": [],
        "source": {"kind": "manual", "path": None,
                   "imported_at": "2026-10-27T00:00:00Z"},
    }
    bundle = engine.review_products(
        {"request_id": "REQ-H2-IP", "products": [product]},
        options={"root": ROOT}, rules=[injected])
    result = bundle["results"][0]
    check("注入的 internal_risk 规则被加载",
          any(r["rule_id"] == "SBR-IP-900" for r in result["rule_refs"]),
          str([r["rule_id"] for r in result["rule_refs"]]))
    check("internal_risk 的 escalate_legal 被降级为非阻断",
          result["action"] not in ("block", "freeze_relist", "escalate_legal"),
          result["action"])
    check("降级原因被记录",
          "H2" in (result["review_rationale"] or "")
          or "H2" in (result["reason"] or ""),
          (result["review_rationale"] or "")[:150])
    check("降级后仍要求人工复核", result["requires_human_review"] is True)


def test_h3_missing_input() -> None:
    section("L5 硬约束 H3 —— 缺失输入记 unevaluated，不判通过")

    # 一个没有任何文本字段的商品
    product = {
        "product_id": "H3-IP-1", "internal_sku": "H3-IP-1",
        "shop_id": "IP-SHOP",
        "source": {"kind": "manual", "path": None,
                   "imported_at": "2026-10-27T00:00:00Z"},
    }
    bundle = review([product], request_id="REQ-H3-IP")
    result = bundle["results"][0]
    check("缺输入时产出 unevaluated 条目",
          len(result["unevaluated"]) >= 1,
          str([u["rule_id"] for u in result["unevaluated"]]))
    check("缺输入时 verdict 不是 PASS", result["verdict"] != "PASS",
          result["verdict"])
    check("unevaluated 条目列出缺失字段",
          all("missing_fields" in u for u in result["unevaluated"]),
          str(result["unevaluated"][:1]))
    check("缺输入时仍要求人工复核", result["requires_human_review"] is True)

    # 空输入列表
    empty = review([], request_id="REQ-H3-EMPTY")
    check("空输入产出 0 条结果", len(empty["results"]) == 0,
          str(len(empty["results"])))


def test_authorization_dimension() -> None:
    section("L6 授权完整性维度")

    cases = {c["case_id"]: c for c in load_shared("ip_cases.json")["cases"]}

    # IP-06：品牌商品但无授权文件 → 必须命中授权缺口规则
    r6 = review([cases["IP-06"]["product"]], request_id="REQ-IP-06")["results"][0]
    fired6 = {ref["rule_id"] for ref in r6["rule_refs"]}
    check("授权缺失命中 SBR-AU-001", "SBR-AU-001" in fired6,
          f"fired={sorted(fired6)}")

    # IP-07：授权完整 → 不应命中授权缺口规则
    r7 = review([cases["IP-07"]["product"]], request_id="REQ-IP-07")["results"][0]
    fired7 = {ref["rule_id"] for ref in r7["rule_refs"]}
    check("授权完整不命中 SBR-AU-001", "SBR-AU-001" not in fired7,
          f"fired={sorted(fired7)}")

    # 授权清单完全缺失 → 既不能判「已授权」也不能判「未授权」
    no_auth = {
        "product_id": "AUTH-UNKNOWN", "internal_sku": "AUTH-UNKNOWN",
        "shop_id": "IP-SHOP", "title": "Tênis Nike", "description": "nike",
        "category": "Calcados", "brand": "Nike", "images": [],
        "source": {"kind": "manual", "path": None,
                   "imported_at": "2026-10-27T00:00:00Z"},
    }
    bundle = review([no_auth], request_id="REQ-AUTH-UNKNOWN")
    detail = bundle["signals"][0]
    check("无授权清单时 known=False", detail["authorization"]["known"] is False,
          str(detail["authorization"]))
    check("无授权清单时不判「未授权」",
          detail["authorization"]["missing"] == [],
          str(detail["authorization"]))
    check("无授权清单时说明授权状态未知",
          "unknown" in (bundle["results"][0]["provenance"]["notes"] or ""),
          bundle["results"][0]["provenance"]["notes"])


def test_contract_conformance() -> None:
    section("L7 产出符合冻结契约")

    cases = load_shared("ip_cases.json")["cases"]
    bundle = review([c["product"] for c in cases])

    schema = load("contracts/audit_result.schema.json")
    required = schema["required"]
    enum_verdict = set(schema["properties"]["verdict"]["enum"])
    enum_conf = set(schema["properties"]["confidence"]["enum"])
    enum_action = set(schema["properties"]["action"]["enum"])
    enum_risk = set(schema["properties"]["risk_level"]["enum"])

    for result in bundle["results"]:
        target = result["result_id"]
        for field in required:
            check(f"{target} 含必需字段 {field}", field in result,
                  str(sorted(result.keys())))
        check(f"{target} 的 verdict 合法", result["verdict"] in enum_verdict,
              result["verdict"])
        check(f"{target} 的 confidence 合法", result["confidence"] in enum_conf,
              result["confidence"])
        check(f"{target} 的 action 合法", result["action"] in enum_action,
              result["action"])
        check(f"{target} 的 risk_level 合法", result["risk_level"] in enum_risk,
              result["risk_level"])
        check(f"{target} 的 module 正确",
              result["module"] == "shopee-br-ip-review", result["module"])
        check(f"{target} 的 rule_refs 非空时 rule_id 格式正确",
              all(_rule_id_ok(ref["rule_id"]) for ref in result["rule_refs"]),
              str([ref["rule_id"] for ref in result["rule_refs"]]))

    # H5：evidence_refs 只存路径
    bad_evidence = []
    for result in bundle["results"]:
        for evidence in result["evidence_refs"]:
            ref = evidence.get("artifact_ref") or ""
            if any(token in ref for token in ("sk-", "ghp_", "BEGIN ")):
                bad_evidence.append(ref)
    check("H5：evidence_refs 不含凭证内容", not bad_evidence, str(bad_evidence))


def _rule_id_ok(rule_id: str) -> bool:
    import re
    return bool(re.match(r"^SBR-[A-Z]{2,4}-[0-9]{3,4}$", rule_id or ""))


def test_handoff() -> None:
    section("L8 模块交接")

    cases = load_shared("ip_cases.json")["cases"]
    bundle = review([c["product"] for c in cases])
    handoff = bundle["handoff"]

    schema = load("contracts/module_handoff.schema.json")
    for field in schema["required"]:
        check(f"handoff 含必需字段 {field}", field in handoff,
              str(sorted(handoff.keys())))
    check("handoff 的 from_module 正确", handoff["from_module"] == "shopee-br-ip-review",
          handoff["from_module"])
    check("handoff 的 to_module 是主 Skill",
          handoff["to_module"] == "shopee-br-compliance", handoff["to_module"])
    check("handoff 的 payload_ref 记录数正确",
          handoff["payload_ref"]["record_count"] == len(cases),
          str(handoff["payload_ref"]["record_count"]))
    check("handoff 声明全部需人工复核",
          handoff["requires_human_review"] is True)
    check("handoff 记录了前提假设", len(handoff["assumptions"]) >= 3,
          str(len(handoff["assumptions"])))
    check("handoff 的假设说明 IP 结论只是筛查信号",
          any("screening signal" in a for a in handoff["assumptions"]),
          str(handoff["assumptions"][:1]))
    check("handoff 的假设声明不执行线上处置",
          any("no online action" in a.lower() for a in handoff["assumptions"]),
          str(handoff["assumptions"][:1]))
    check("handoff 声明契约版本", handoff["contract_version"] == "1.0.0",
          handoff["contract_version"])


def test_cli() -> None:
    section("L9 CLI 端到端")

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "in.json")
        cases = load_shared("ip_cases.json")["cases"]
        with open(inp, "w", encoding="utf-8") as handle:
            json.dump({"request_id": "REQ-IP-CLI-001",
                       "products": [c["product"] for c in cases]},
                      handle, ensure_ascii=False)

        out = os.path.join(tmp, "out")
        cli = os.path.join(SRC, "sbr_ip_review_cli.py")
        proc = subprocess.run(
            [sys.executable, cli, "--request-id", "REQ-IP-CLI-001",
             "--out-dir", out, inp],
            capture_output=True, text=True)
        check("CLI 退出码 0", proc.returncode == 0,
              (proc.stdout or "")[-200:] + (proc.stderr or "")[-200:])

        for name in ("audit_result.json", "audit_results.json",
                     "module_handoff.json", "signals.json"):
            check(f"CLI 产出 {name}",
                  os.path.exists(os.path.join(out, name)), "缺失")

        with open(os.path.join(out, "audit_result.json"), encoding="utf-8") as h:
            single = json.load(h)
        check("audit_result.json 是单条对象",
              isinstance(single, dict) and "verdict" in single,
              str(type(single).__name__))
        with open(os.path.join(out, "audit_results.json"), encoding="utf-8") as h:
            many = json.load(h)
        check("audit_results.json 是数组", isinstance(many, list),
              str(type(many).__name__))
        check("CLI 结果数与夹具一致", len(many) == len(cases),
              f"{len(many)} vs {len(cases)}")

        # 缺输入文件 → 退出码 1
        proc2 = subprocess.run(
            [sys.executable, cli, "--out-dir", os.path.join(tmp, "out2"),
             os.path.join(tmp, "missing.json")],
            capture_output=True, text=True)
        check("CLI 缺输入文件退出码 1", proc2.returncode == 1, str(proc2.returncode))


def test_rule_loading_failure() -> None:
    section("L10 规则库读不到必须显式失败")

    # 传入非 IP 前缀的规则 → 没有可用规则 → 必须抛错而不是报「无风险」
    bad = [{
        "rule_id": "SBR-LV-001", "title": "x", "category": "listing_violation",
        "severity": "low", "action": "flag_for_review",
        "source": {"tier": "platform_official", "url": "https://example.invalid",
                   "excerpt": "x", "last_verified": "2026-10-27"},
        "status": "active", "version": 1, "evidence_required": [],
        "requires_human_review": False,
        "trigger_conditions": [{"field": "title", "operator": "regex",
                                "value": "x"}],
    }]
    raised = False
    try:
        engine.review_products(
            {"request_id": "REQ-NO-RULES", "products": [
                {"product_id": "X", "title": "x", "description": "x"}]},
            options={"root": ROOT}, rules=bad)
    except engine.RuleLoadError:
        raised = True
    except Exception as exc:                     # noqa: BLE001
        raised = False
        check("无规则时抛的是 RuleLoadError", False, f"{type(exc).__name__}: {exc}")
    if raised:
        check("无规则时抛 RuleLoadError（不报「无风险」）", True)


def main() -> int:
    print("=" * 62)
    print("shopee-br-ip-review 模块测试")
    print(f"仓库根: {ROOT}")
    print("=" * 62)

    started = datetime.now(timezone.utc)
    test_fixture_cases()
    test_h1_never_deterministic()
    test_nominative_use_exemption()
    test_h2_blocking_requires_authoritative_rule()
    test_h3_missing_input()
    test_authorization_dimension()
    test_contract_conformance()
    test_handoff()
    test_cli()
    test_rule_loading_failure()

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    print("\n" + "=" * 62)
    print(f"PASSED: {len(PASSED)}   FAILED: {len(FAILED)}")
    print(f"耗时: {elapsed:.2f}s")
    if FAILED:
        print("\nFailures:")
        for name, detail in FAILED[:25]:
            print(f"  - {name}: {detail}")
        return 1
    print("模块测试全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
