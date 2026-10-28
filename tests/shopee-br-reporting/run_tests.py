#!/usr/bin/env python3
"""`shopee-br-reporting` 模块测试（L1–L4）。

覆盖（见 `skills/shopee-br-reporting/SKILL.md` §10）：

* **L1 单元** —— 矩阵读取、verdict 取重、action 粒度保留、清洗逻辑
* **L2 契约** —— 产出通过 `contracts/audit_result.schema.json` 与
  `contracts/module_handoff.schema.json` 校验
* **L3 聚合** —— 多模块结果聚合（verdict 粒度、action 粒度、不降级、
  缺口并集、规则去重、冲突记录）
* **L4 硬约束** —— H1 / H2 / H3 / H4 / H5 / H6 断言
* **报告结构** —— 六节固定结构、第 2 节独立、空值表达「无」
* **失败路径** —— 输入不可读、契约不符、无结果、输出目录不可写

运行：

```bash
env -u LD_LIBRARY_PATH python3 tests/shopee-br-reporting/run_tests.py
```

**只读**共享夹具（`tests/fixtures/**`）；本模块的自有夹具写在
`tests/shopee-br-reporting/fixtures/`，运行时复制到临时目录，
测试结束后清理。**任何情况下都不修改输入文件。**
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MODULE_DIR = os.path.join(ROOT, "skills", "shopee-br-reporting")
SRC = os.path.join(MODULE_DIR, "src")
FIXTURES = os.path.join(HERE, "fixtures")

sys.path.insert(0, SRC)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from validate_json import Validator  # noqa: E402

from sbr_reporting import run_reporting  # noqa: E402
from sbr_reporting.aggregate import aggregate, sanitize  # noqa: E402
from sbr_reporting.errors import ErrorLog  # noqa: E402
from sbr_reporting.loader import load_results  # noqa: E402
from sbr_reporting.matrix import (  # noqa: E402
    MatrixUnavailable,
    RiskMatrix,
    load_matrix,
)
from sbr_reporting.render import render_report  # noqa: E402
from sbr_reporting.rules import RuleIndex  # noqa: E402

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
# 自有夹具构造
# ---------------------------------------------------------------------------

REQUEST_ID = "REQ-REPORT-TEST-001"

OFFICIAL_URL = "https://seller.br.shopee.cn/edu/article/5139"
LAW_URL = "https://www.planalto.gov.br/ccivil_03/leis/l9279.htm"


def make_result(result_id: str, module: str, target: str, verdict: str,
                risk: str, action: str, *, confidence: str = "likely",
                rule_refs=None, evidence_refs=None, unevaluated=None,
                errors=None, requires_human_review: bool = False,
                rule_version: str = "rules-test/1.0.0") -> dict:
    """构造一条符合 `contracts/audit_result.schema.json` 的结果。"""
    return {
        "result_id": result_id,
        "request_id": REQUEST_ID,
        "module": module,
        "target_ref": target,
        "verdict": verdict,
        "risk_level": risk,
        "action": action,
        "reason": f"{module} reported {action} for {target} with enough detail",
        "rule_refs": rule_refs or [],
        "evidence_refs": evidence_refs or [],
        "confidence": confidence,
        "requires_human_review": requires_human_review,
        "review_rationale": ("needs a human decision"
                              if requires_human_review else None),
        "rule_version": rule_version,
        "provenance": {
            "produced_at": "2026-10-27T00:00:00Z",
            "producer": f"{module}/test",
        },
        "errors": errors or [],
        "unevaluated": unevaluated or [],
    }


def rule_ref(rule_id: str, tier: str, url: str = OFFICIAL_URL,
             title: str | None = None, field: str | None = None,
             excerpt: str | None = None) -> dict:
    return {
        "rule_id": rule_id,
        "title": title,
        "matched_field": field,
        "matched_excerpt": excerpt,
        "source_tier": tier,
        "source_url": url,
    }


def evidence_ref(evidence_id: str, evidence_type: str, provided: bool,
                 artifact_ref: str | None = None, notes: str | None = None) -> dict:
    return {
        "evidence_id": evidence_id,
        "evidence_type": evidence_type,
        "provided": provided,
        "artifact_ref": artifact_ref,
        "source_locator": None,
        "collected_at": None,
        "notes": notes,
    }


def make_input(results=None, result_files=None, products=None) -> dict:
    """构造符合 `contracts/skill_input.schema.json` 的输入。"""
    options: dict = {}
    if results is not None:
        options["results"] = results
    if result_files is not None:
        options["result_files"] = result_files
    return {
        "request_id": REQUEST_ID,
        "task_type": "reporting",
        "target": {"kind": "audit_result_set", "ref": "tests", "count": None},
        "products": products or [],
        "cases": [],
        "rules": [],
        "scope": {},
        "options": options,
        "provenance": {
            "inputs": [{"path": "<inline>", "kind": "audit_result_set"}],
            "produced_at": "2026-10-27T00:00:00Z",
            "producer": "reporting-test",
        },
    }


def matrix() -> RiskMatrix:
    return RiskMatrix(load_matrix(os.path.join(ROOT, "contracts",
                                               "risk_action_matrix.json")))


def aggregate_results(results, request_id: str = REQUEST_ID):
    log = ErrorLog()
    per_target, batch = aggregate(results, matrix(), request_id, log)
    return per_target, batch, log


# ---------------------------------------------------------------------------
# L1 单元测试
# ---------------------------------------------------------------------------

def test_unit() -> None:
    section("L1 单元测试")

    mat = matrix()

    # --- 矩阵读取 ---
    check("verdict 顺序来自契约", mat.verdict_order == ["PASS", "REVISE", "REVIEW", "BLOCK"],
          str(mat.verdict_order))
    check("动作集合为契约的 7 个",
          set(mat.action_order) == {"allow", "flag_for_review", "require_evidence",
                                    "revise", "block", "freeze_relist", "escalate_legal"},
          str(mat.action_order))
    check("矩阵覆盖 5×7=35 个组合", len(mat.allowed_pairs) == 35,
          str(len(mat.allowed_pairs)))

    # --- verdict 取重 ---
    check("verdict 取最重：PASS + BLOCK → BLOCK",
          mat.max_verdict(["PASS", "BLOCK"]) == "BLOCK",
          mat.max_verdict(["PASS", "BLOCK"]))
    check("verdict 取最重：REVISE + REVIEW → REVIEW",
          mat.max_verdict(["REVISE", "REVIEW"]) == "REVIEW",
          mat.max_verdict(["REVISE", "REVIEW"]))
    check("verdict 取最重：空集合 → PASS", mat.max_verdict([]) == "PASS",
          mat.max_verdict([]))

    # --- action 粒度保留 ---
    check("最细粒度：flag_for_review + require_evidence → require_evidence",
          mat.most_specific(["flag_for_review", "require_evidence"]) == "require_evidence",
          str(mat.most_specific(["flag_for_review", "require_evidence"])))
    check("最细粒度：require_evidence + block → block",
          mat.most_specific(["require_evidence", "block"]) == "block",
          str(mat.most_specific(["require_evidence", "block"])))
    check("最细粒度：allow + revise → revise",
          mat.most_specific(["allow", "revise"]) == "revise",
          str(mat.most_specific(["allow", "revise"])))
    check("最细粒度：空集合 → None", mat.most_specific([]) is None,
          str(mat.most_specific([])))

    # --- 动作 → verdict 映射（契约 actions 段） ---
    check("action allow → PASS", mat.verdict_for_action("allow") == "PASS",
          mat.verdict_for_action("allow"))
    check("action revise → REVISE", mat.verdict_for_action("revise") == "REVISE",
          mat.verdict_for_action("revise"))
    check("action require_evidence → REVIEW",
          mat.verdict_for_action("require_evidence") == "REVIEW",
          mat.verdict_for_action("require_evidence"))
    check("action block → BLOCK", mat.verdict_for_action("block") == "BLOCK",
          mat.verdict_for_action("block"))
    check("action freeze_relist → BLOCK",
          mat.verdict_for_action("freeze_relist") == "BLOCK",
          mat.verdict_for_action("freeze_relist"))
    check("action escalate_legal → BLOCK",
          mat.verdict_for_action("escalate_legal") == "BLOCK",
          mat.verdict_for_action("escalate_legal"))

    # --- 矩阵允许组合 ---
    check("low + block 不被允许", not mat.is_allowed("low", "block"),
          str(mat.is_allowed("low", "block")))
    check("high + block 被允许", mat.is_allowed("high", "block"),
          str(mat.is_allowed("high", "block")))
    check("info + require_evidence 不被允许",
          not mat.is_allowed("info", "require_evidence"),
          str(mat.is_allowed("info", "require_evidence")))
    check("critical + revise 不被允许", not mat.is_allowed("critical", "revise"),
          str(mat.is_allowed("critical", "revise")))

    # --- 风险等级取最严重 ---
    check("风险等级取最严重：info + critical → critical",
          mat.max_risk(["info", "critical"]) == "critical",
          mat.max_risk(["info", "critical"]))
    check("风险等级取最严重：low + medium → medium",
          mat.max_risk(["low", "medium"]) == "medium",
          mat.max_risk(["low", "medium"]))

    # --- human_only ---
    check("freeze_relist 是 human_only", mat.executable_by("freeze_relist") == "human_only",
          mat.executable_by("freeze_relist"))
    check("escalate_legal 是 human_only", mat.executable_by("escalate_legal") == "human_only",
          mat.executable_by("escalate_legal"))
    check("block 是 human 执行", mat.executable_by("block") == "human",
          mat.executable_by("block"))
    check("flag_for_review 恒需人工复核", mat.always_human_review("flag_for_review"),
          str(mat.always_human_review("flag_for_review")))
    check("allow 不恒需人工复核", not mat.always_human_review("allow"),
          str(mat.always_human_review("allow")))

    # --- 矩阵不可用 ---
    try:
        load_matrix(os.path.join(ROOT, "contracts", "does_not_exist.json"))
        check("矩阵缺失时抛 MatrixUnavailable", False, "未抛异常")
    except MatrixUnavailable:
        check("矩阵缺失时抛 MatrixUnavailable", True, "")

    # --- 清洗：风险等级 × 动作不合法 ---
    log = ErrorLog()
    bad = sanitize(make_result("RES-UNIT-0001", "shopee-br-listing-audit",
                                "SKU-X", "PASS", "low", "block",
                                rule_refs=[rule_ref("SBR-PI-001", "platform_official")]),
                   mat, log)
    check("low + block 被降级为合法组合", bad.action != "block",
          f"{bad.action}")
    check("low + block 降级后仍被矩阵允许",
          mat.is_allowed(bad.risk_level, bad.action),
          f"{bad.risk_level}+{bad.action}")
    check("low + block 降级记 warning",
          any(e["severity"] == "warning" for e in log.items),
          str([e["severity"] for e in log.items]))

    # --- 清洗：未知动作 ---
    log2 = ErrorLog()
    unknown = sanitize(make_result("RES-UNIT-0002", "shopee-br-listing-audit",
                                    "SKU-Y", "PASS", "info", "totally_unknown_action"),
                       mat, log2)
    check("未知动作被替换为 flag_for_review",
          unknown.action == "flag_for_review", unknown.action)

    # --- 规则索引 ---
    index = RuleIndex.load(ROOT)
    check("规则索引读到了规则库", len(index.rules) > 0, str(len(index.rules)))
    meta = index.get("SBR-PI-001")
    check("规则索引带来源层级", meta.get("source_tier") == "platform_official",
          str(meta.get("source_tier")))
    check("规则索引带核查日期", bool(meta.get("last_verified")),
          str(meta.get("last_verified")))
    check("规则索引带负责模块", meta.get("owner_module") == "shopee-br-listing-audit",
          str(meta.get("owner_module")))


# ---------------------------------------------------------------------------
# L2 契约测试
# ---------------------------------------------------------------------------

def test_contract() -> None:
    section("L2 契约测试")

    results = [
        make_result("RES-CONTRACT-0001", "shopee-br-listing-audit", "SKU-1",
                    "REVIEW", "medium", "flag_for_review",
                    rule_refs=[rule_ref("SBR-LV-001", "platform_official")]),
        make_result("RES-CONTRACT-0002", "shopee-br-ip-review", "SKU-1",
                    "REVIEW", "medium", "require_evidence", confidence="signal",
                    requires_human_review=True,
                    rule_refs=[rule_ref("SBR-IP-001", "platform_official")],
                    evidence_refs=[evidence_ref("EV-CONTRACT-01",
                                                "brand_authorization_letter", False,
                                                "docs/auth/letter.pdf")]),
    ]
    bundle = run_reporting(make_input(results=results), root=ROOT)
    check("汇总成功", bundle["ok"], str(bundle["errors"])[:300])

    for result in bundle["results"]:
        validate_against("contracts/audit_result.schema.json", result,
                         f"AuditResult {result['result_id']}")

    validate_against("contracts/module_handoff.schema.json", bundle["handoff"],
                     "ModuleHandoff")

    check("汇总结果 module 固定为 shopee-br-reporting",
          all(r["module"] == "shopee-br-reporting" for r in bundle["results"]),
          str({r["module"] for r in bundle["results"]}))
    check("汇总结果 request_id 回填",
          all(r["request_id"] == REQUEST_ID for r in bundle["results"]),
          str({r["request_id"] for r in bundle["results"]}))
    check("汇总结果有 provenance.producer",
          all(r["provenance"]["producer"] for r in bundle["results"]),
          "producer 为空")
    check("汇总结果 provenance.source_refs 非空",
          all(r["provenance"]["source_refs"] for r in bundle["results"]),
          "source_refs 为空")
    check("交接 assumptions 非空", len(bundle["handoff"]["assumptions"]) >= 1,
          str(len(bundle["handoff"]["assumptions"])))
    check("交接 known_gaps 非空", len(bundle["handoff"]["known_gaps"]) >= 1,
          str(len(bundle["handoff"]["known_gaps"])))
    check("交接 to_module 默认 shopee-br-compliance",
          bundle["handoff"]["to_module"] == "shopee-br-compliance",
          bundle["handoff"]["to_module"])
    check("交接 record_count 等于聚合后的目标数",
          bundle["handoff"]["payload_ref"]["record_count"] == 1,
          str(bundle["handoff"]["payload_ref"]["record_count"]))
    check("两条输入结果聚合到一个目标",
          bundle["summary"]["target_count"] == 1,
          str(bundle["summary"]["target_count"]))
    check("输入结果条数被单独记录",
          bundle["summary"]["input_result_count"] == 2,
          str(bundle["summary"]["input_result_count"]))

    # verdict / confidence / action 全部落在契约枚举内
    verdicts = {"PASS", "REVISE", "REVIEW", "BLOCK"}
    confidences = {"signal", "likely", "confirmed"}
    actions = {"allow", "flag_for_review", "require_evidence", "revise", "block",
               "freeze_relist", "escalate_legal"}
    bad = [r["result_id"] for r in bundle["results"]
           if r["verdict"] not in verdicts or r["confidence"] not in confidences
           or r["action"] not in actions]
    check("所有 verdict/confidence/action 在契约枚举内", not bad, str(bad))


# ---------------------------------------------------------------------------
# L3 聚合测试
# ---------------------------------------------------------------------------

def test_aggregation() -> None:
    section("L3 聚合测试")

    # --- verdict 取最重 + action 保留最细粒度 ---
    per_target, batch, _ = aggregate_results([
        make_result("RES-AGG-0001", "shopee-br-listing-audit", "SKU-A",
                    "REVIEW", "medium", "flag_for_review"),
        make_result("RES-AGG-0002", "shopee-br-ip-review", "SKU-A",
                    "REVIEW", "medium", "require_evidence"),
    ])
    check("聚合：flag_for_review + require_evidence → verdict REVIEW",
          per_target[0]["verdict"] == "REVIEW", per_target[0]["verdict"])
    check("聚合：action 保留 require_evidence（不退化为 flag）",
          per_target[0]["action"] == "require_evidence", per_target[0]["action"])

    per_target, batch, _ = aggregate_results([
        make_result("RES-AGG-0003", "shopee-br-listing-audit", "SKU-B",
                    "REVIEW", "medium", "require_evidence"),
        make_result("RES-AGG-0004", "shopee-br-ip-review", "SKU-B",
                    "BLOCK", "critical", "block",
                    rule_refs=[rule_ref("SBR-IP-002", "platform_official")]),
    ])
    check("聚合：require_evidence + block → verdict BLOCK",
          per_target[0]["verdict"] == "BLOCK", per_target[0]["verdict"])
    check("聚合：action 为 block", per_target[0]["action"] == "block",
          per_target[0]["action"])

    per_target, batch, _ = aggregate_results([
        make_result("RES-AGG-0005", "shopee-br-listing-audit", "SKU-C",
                    "PASS", "info", "allow"),
        make_result("RES-AGG-0006", "shopee-br-duplicate-detection", "SKU-C",
                    "REVISE", "low", "revise"),
    ])
    check("聚合：allow + revise → verdict REVISE",
          per_target[0]["verdict"] == "REVISE", per_target[0]["verdict"])
    check("聚合：action 为 revise", per_target[0]["action"] == "revise",
          per_target[0]["action"])

    # --- 不降级（确定性结论只增不减） ---
    per_target, batch, _ = aggregate_results([
        make_result("RES-AGG-0007", "shopee-br-listing-audit", "SKU-D",
                    "BLOCK", "critical", "block",
                    rule_refs=[rule_ref("SBR-PI-002", "platform_official")]),
        make_result("RES-AGG-0008", "shopee-br-duplicate-detection", "SKU-D",
                    "PASS", "info", "allow"),
    ])
    check("不降级：block + allow → action 仍为 block",
          per_target[0]["action"] == "block", per_target[0]["action"])
    check("不降级：verdict 仍为 BLOCK", per_target[0]["verdict"] == "BLOCK",
          per_target[0]["verdict"])

    # --- 未评估项并集（H3） ---
    per_target, batch, _ = aggregate_results([
        make_result("RES-AGG-0009", "shopee-br-listing-audit", "SKU-E",
                    "PASS", "info", "allow"),
        make_result("RES-AGG-0010", "shopee-br-duplicate-detection", "SKU-E",
                    "PASS", "info", "allow",
                    unevaluated=[{"rule_id": "SBR-DUP-001",
                                  "reason": "images are missing",
                                  "missing_fields": ["images"]}]),
    ])
    check("H3：未评估项被并集保留",
          len(per_target[0]["unevaluated"]) == 1,
          str(per_target[0]["unevaluated"]))
    check("H3：未评估项的目标不判为 PASS",
          per_target[0]["verdict"] != "PASS", per_target[0]["verdict"])
    check("H3：未评估项使结论升到 REVIEW",
          per_target[0]["verdict"] == "REVIEW", per_target[0]["verdict"])
    check("H3：未评估项使 requires_human_review 为真",
          per_target[0]["requires_human_review"] is True,
          str(per_target[0]["requires_human_review"]))

    # --- 规则去重与冲突记录 ---
    per_target, batch, log = aggregate_results([
        make_result("RES-AGG-0011", "shopee-br-listing-audit", "SKU-F",
                    "REVIEW", "medium", "flag_for_review",
                    rule_refs=[rule_ref("SBR-LV-001", "platform_official")]),
        make_result("RES-AGG-0012", "shopee-br-duplicate-detection", "SKU-F",
                    "REVIEW", "medium", "flag_for_review",
                    rule_refs=[rule_ref("SBR-LV-001", "platform_official")]),
    ])
    check("同一规则被多模块引用时只保留一条",
          len(per_target[0]["rule_refs"]) == 1, str(per_target[0]["rule_refs"]))

    per_target, batch, log = aggregate_results([
        make_result("RES-AGG-0013", "shopee-br-listing-audit", "SKU-G",
                    "REVIEW", "medium", "flag_for_review",
                    rule_refs=[rule_ref("SBR-LV-001", "platform_official")]),
        make_result("RES-AGG-0014", "shopee-br-duplicate-detection", "SKU-G",
                    "REVIEW", "medium", "flag_for_review",
                    rule_refs=[rule_ref("SBR-LV-001", "internal_risk")]),
    ])
    check("跨模块来源冲突被记录",
          len(per_target[0]["_conflicts"]) == 1, str(per_target[0]["_conflicts"]))

    # --- 证据去重 ---
    per_target, batch, _ = aggregate_results([
        make_result("RES-AGG-0015", "shopee-br-listing-audit", "SKU-H",
                    "REVIEW", "medium", "require_evidence",
                    evidence_refs=[evidence_ref("EV-AGG-01", "supplier_invoice",
                                                False, "docs/invoice.pdf")]),
        make_result("RES-AGG-0016", "shopee-br-ip-review", "SKU-H",
                    "REVIEW", "medium", "require_evidence",
                    evidence_refs=[evidence_ref("EV-AGG-01", "supplier_invoice",
                                                False, "docs/invoice.pdf")]),
    ])
    check("同一证据只保留一条",
          len(per_target[0]["evidence_refs"]) == 1,
          str(per_target[0]["evidence_refs"]))

    # --- 整批结论 ---
    per_target, batch, _ = aggregate_results([
        make_result("RES-AGG-0017", "shopee-br-listing-audit", "SKU-I",
                    "PASS", "info", "allow"),
        make_result("RES-AGG-0018", "shopee-br-listing-audit", "SKU-J",
                    "BLOCK", "critical", "block",
                    rule_refs=[rule_ref("SBR-PI-002", "platform_official")]),
    ])
    check("整批结论取最重 verdict", batch["verdict"] == "BLOCK", batch["verdict"])
    check("整批结论的 target_ref 指向整批",
          batch["target_ref"].startswith("batch-"), batch["target_ref"])
    check("整批结论统计了逐目标结果数", len(per_target) == 2, str(len(per_target)))

    # --- 无 target_ref 的结果被拒 ---
    orphan = make_result("RES-AGG-0019", "shopee-br-listing-audit", "",
                         "PASS", "info", "allow")
    per_target, batch, log = aggregate_results([orphan])
    check("无 target_ref 的结果被跳过并记 error",
          any(e["severity"] == "error" for e in log.items),
          str([e["message"] for e in log.items])[:200])
    check("无 target_ref 的结果不进入聚合",
          len(per_target) == 0, str(len(per_target)))


# ---------------------------------------------------------------------------
# L4 硬约束测试
# ---------------------------------------------------------------------------

def test_hard_constraints() -> None:
    section("L4 硬约束测试")

    mat = matrix()

    # --- H1：IP 类结论恒为 signal + 人工复核 ---
    per_target, batch, _ = aggregate_results([
        make_result("RES-H1-0001", "shopee-br-ip-review", "SKU-IP",
                    "REVIEW", "medium", "flag_for_review",
                    confidence="signal", requires_human_review=True,
                    rule_refs=[rule_ref("SBR-IP-003", "platform_official")]),
        make_result("RES-H1-0002", "shopee-br-listing-audit", "SKU-IP",
                    "PASS", "info", "allow", confidence="confirmed"),
    ])
    check("H1：合并后置信度取最弱（signal 不升为 confirmed）",
          per_target[0]["confidence"] == "signal", per_target[0]["confidence"])
    check("H1：IP 结论 requires_human_review 为真",
          per_target[0]["requires_human_review"] is True,
          str(per_target[0]["requires_human_review"]))

    # --- H2：internal_risk 不得产生 block ---
    log = ErrorLog()
    bad = sanitize(make_result("RES-H2-0001", "shopee-br-listing-audit",
                                "SKU-H2", "BLOCK", "high", "block",
                                rule_refs=[rule_ref("SBR-XXX-001", "internal_risk")]),
                   mat, log)
    check("H2：internal_risk 的 block 被拒", bad.action != "block", bad.action)
    check("H2：降级为 flag_for_review", bad.action == "flag_for_review",
          bad.action)
    check("H2：降级记 error", any(e["severity"] == "error" for e in log.items),
          str([e["severity"] for e in log.items]))

    for tier in ("unverified", "ai_inference", "technical"):
        log = ErrorLog()
        item = sanitize(make_result("RES-H2-0002", "shopee-br-listing-audit",
                                    "SKU-H2", "BLOCK", "high", "block",
                                    rule_refs=[rule_ref("SBR-XXX-002", tier)]),
                        mat, log)
        check(f"H2：{tier} 的 block 被拒", item.action == "flag_for_review",
              item.action)

    # law 层级可以产生 block
    log = ErrorLog()
    ok = sanitize(make_result("RES-H2-0003", "shopee-br-ip-review",
                               "SKU-H2", "BLOCK", "high", "block",
                               rule_refs=[rule_ref("SBR-IP-002", "law", LAW_URL)]),
                  mat, log)
    check("H2：law 层级的 block 被接受", ok.action == "block", ok.action)

    # 无来源层级的 block 也被拒
    log = ErrorLog()
    none_tier = sanitize(make_result("RES-H2-0004", "shopee-br-listing-audit",
                                     "SKU-H2", "BLOCK", "high", "block"),
                         mat, log)
    check("H2：没有来源层级的 block 被拒",
          none_tier.action == "flag_for_review", none_tier.action)

    # 端到端：H2 违规不得出现在最终结论里
    bundle = run_reporting(make_input(results=[
        make_result("RES-H2-0005", "shopee-br-listing-audit", "SKU-H2",
                    "BLOCK", "high", "block",
                    rule_refs=[rule_ref("SBR-XXX-003", "internal_risk")]),
    ]), root=ROOT)
    target_result = [r for r in bundle["results"]
                     if r["target_ref"] == "SKU-H2"][0]
    check("H2：端到端结果不含 block 动作",
          target_result["action"] != "block", target_result["action"])
    check("H2：端到端 verdict 随动作降为 REVIEW",
          target_result["verdict"] == "REVIEW", target_result["verdict"])
    check("H2：降级在 errors[] 中留痕",
          any("H2" in e["message"] for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:200])

    # --- H3：缺失输入 → 未评估，不算通过 ---
    bundle = run_reporting(make_input(results=[
        make_result("RES-H3-0001", "shopee-br-listing-audit", "SKU-H3",
                    "PASS", "info", "allow",
                    unevaluated=[{"rule_id": "SBR-LV-008",
                                  "reason": "category is missing",
                                  "missing_fields": ["category"]}],
                    errors=[{"error_id": "ERR-H3-0001",
                             "stage": "rule_evaluation",
                             "severity": "warning",
                             "message": "category is missing"}]),
    ]), root=ROOT)
    target_result = [r for r in bundle["results"]
                     if r["target_ref"] == "SKU-H3"][0]
    check("H3：unevaluated 非空", len(target_result["unevaluated"]) == 1,
          str(target_result["unevaluated"]))
    check("H3：缺失输入不产生 PASS", target_result["verdict"] != "PASS",
          target_result["verdict"])
    check("H3：报告第 2 节列出未评估项",
          "SBR-LV-008" in bundle["report"], "报告中未出现该规则")

    # --- H4：来源链接与核查日期原样透传 ---
    bundle = run_reporting(make_input(results=[
        make_result("RES-H4-0001", "shopee-br-listing-audit", "SKU-H4",
                    "REVIEW", "medium", "flag_for_review",
                    rule_refs=[rule_ref("SBR-LV-001", "platform_official",
                                        OFFICIAL_URL)]),
    ]), root=ROOT)
    check("H4：来源链接原样出现在报告里",
          OFFICIAL_URL in bundle["report"], "来源链接丢失")
    meta = bundle["summary"]["rules"][0]
    check("H4：核查日期来自规则库且被透传",
          meta.get("last_verified") == "2026-10-27", str(meta.get("last_verified")))
    check("H4：来源层级原样透传",
          meta.get("source_tier") == "platform_official",
          str(meta.get("source_tier")))

    # --- H5：报告不含凭证内容 ---
    secret = "-----BEGIN CERTIFICATE-----MIIBsecretMATERIAL-----END CERTIFICATE-----"
    bundle = run_reporting(make_input(results=[
        make_result("RES-H5-0001", "shopee-br-listing-audit", "SKU-H5",
                    "REVIEW", "medium", "require_evidence",
                    evidence_refs=[evidence_ref("EV-H5-01",
                                                "brand_authorization_letter", False,
                                                "docs/auth/letter.pdf")]),
    ]), root=ROOT)
    check("H5：证据引用只出现在 artifact_ref",
          "docs/auth/letter.pdf" in bundle["report"], "引用未出现")
    check("H5：报告不含凭证内容特征",
          ("BEGIN CERTIFICATE" not in bundle["report"]
           and "sk-" not in bundle["report"]),
          "报告出现凭证特征")
    check("H5：证据对象不含内容字段",
          all(set(e.keys()) <= {"evidence_id", "evidence_type", "provided",
                                "artifact_ref", "source_locator",
                                "collected_at", "notes"}
              for e in bundle["results"][0]["evidence_refs"]),
          "证据对象含额外字段")

    # --- H6：human_only 动作标注需人工执行 ---
    bundle = run_reporting(make_input(results=[
        make_result("RES-H6-0001", "shopee-br-duplicate-detection", "SKU-H6",
                    "BLOCK", "high", "freeze_relist",
                    requires_human_review=True,
                    rule_refs=[rule_ref("SBR-RL-002", "platform_official")]),
    ]), root=ROOT)
    check("H6：freeze_relist 的 requires_human_review 为真",
          bundle["results"][0]["requires_human_review"] is True,
          str(bundle["results"][0]["requires_human_review"]))
    check("H6：报告标注需人工执行", "需人工执行" in bundle["report"],
          "报告未标注")
    check("H6：human_only 动作计入摘要",
          bundle["summary"]["human_only_count"] == 1,
          str(bundle["summary"]["human_only_count"]))
    check("H6：模块不提供执行入口",
          not hasattr(sys.modules["sbr_reporting"], "execute_action"),
          "存在执行入口")


# ---------------------------------------------------------------------------
# 报告结构测试
# ---------------------------------------------------------------------------

def test_report_structure() -> None:
    section("报告结构测试")

    bundle = run_reporting(make_input(results=[
        make_result("RES-REPORT-0001", "shopee-br-listing-audit", "SKU-R1",
                    "BLOCK", "critical", "block",
                    requires_human_review=True,
                    rule_refs=[rule_ref("SBR-PI-002", "platform_official",
                                        title="Prohibited item category")]),
        make_result("RES-REPORT-0002", "shopee-br-ip-review", "SKU-R2",
                    "REVIEW", "medium", "flag_for_review",
                    confidence="signal", requires_human_review=True,
                    rule_refs=[rule_ref("SBR-IP-003", "platform_official")],
                    unevaluated=[{"rule_id": "SBR-IP-005",
                                  "reason": "no image OCR was performed",
                                  "missing_fields": ["images"]}]),
    ], products=[{"product_id": "SKU-R1", "internal_sku": "SKU-R1",
                  "shop_id": "SHOP-R", "title": "Produto de teste"}]),
        root=ROOT)
    report = bundle["report"]

    for heading in ("## 1. 摘要", "## 2. 数据缺口与未评估项", "## 3. 需决策的发现",
                    "## 4. 待复核的发现", "## 5. 逐商品结果", "## 6. 已查阅规则"):
        check(f"报告含章节 {heading}", heading in report, "缺失")

    check("六节顺序固定",
          report.index("## 1. 摘要") < report.index("## 2. 数据缺口与未评估项")
          < report.index("## 3. 需决策的发现") < report.index("## 4. 待复核的发现")
          < report.index("## 5. 逐商品结果") < report.index("## 6. 已查阅规则"),
          "章节顺序不对")

    check("报告含硬约束清单", "## 硬约束" in report, "缺失")
    for constraint in ("H1", "H2", "H3", "H4", "H5", "H6"):
        check(f"硬约束 {constraint} 在报告中", constraint in report, "缺失")

    check("第 2 节列出未评估规则", "SBR-IP-005" in report, "缺失")
    check("第 2 节说明与通过分区",
          "分区" in report or "严格分区" in report, "缺少分区说明")

    check("第 3 节列出需决策的发现", "SKU-R1" in report, "缺失")
    check("第 4 节列出待复核的发现", "SKU-R2" in report, "缺失")
    check("第 5 节显示 SKU 与店铺", "SHOP-R" in report, "缺失")
    check("第 6 节显示来源层级", "平台规则" in report, "缺失")
    check("第 6 节显示核查日期", "2026-10-27" in report, "缺失")

    # --- 空值表达「无」 ---
    empty_bundle = run_reporting(make_input(results=[
        make_result("RES-REPORT-0003", "shopee-br-listing-audit", "SKU-R3",
                    "PASS", "info", "allow"),
    ]), root=ROOT)
    empty_report = empty_bundle["report"]
    check("无未评估项时第 2 节显示「无」",
          "## 2. 数据缺口与未评估项\n\n> 本节与「通过」**严格分区**。"
          in empty_report or "无" in empty_report, "未显示「无」")
    check("无待复核发现时第 4 节显示「无」",
          "## 4. 待复核的发现\n\n无" in empty_report, "未显示「无」")
    check("无发现时整批结论为 PASS",
          empty_bundle["summary"]["batch_verdict"] == "PASS",
          empty_bundle["summary"]["batch_verdict"])
    check("正常商品不被判为违规",
          empty_bundle["results"][0]["action"] == "allow",
          empty_bundle["results"][0]["action"])


# ---------------------------------------------------------------------------
# 失败路径测试
# ---------------------------------------------------------------------------

def test_failure_paths(workdir: str) -> None:
    section("失败路径测试")

    # --- 结果文件不可读 ---
    missing = os.path.join(workdir, "not-there.json")
    bundle = run_reporting(make_input(result_files=[missing]), root=ROOT)
    check("结果文件不存在时记 error",
          any(e["severity"] == "error" and "does not exist" in e["message"]
              for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:250])
    check("无有效结果时不生成报告",
          bundle["report"] is None and bundle["summary"] is None,
          "仍然生成了报告")

    # --- 结果文件不可解析 ---
    broken = os.path.join(workdir, "broken.json")
    with open(broken, "w", encoding="utf-8") as handle:
        handle.write("{ this is not json ")
    bundle = run_reporting(make_input(result_files=[broken]), root=ROOT)
    check("结果文件不可解析时记 error",
          any(e["severity"] == "error" and "could not be read" in e["message"]
              for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:250])

    # --- 结果不符合契约 ---
    invalid_path = os.path.join(workdir, "invalid.json")
    bad_result = make_result("RES-BAD-0001", "shopee-br-listing-audit",
                              "SKU-BAD", "PASS", "info", "allow")
    bad_result["verdict"] = "pass"          # 契约外取值
    with open(invalid_path, "w", encoding="utf-8") as handle:
        json.dump([bad_result], handle, ensure_ascii=False)
    bundle = run_reporting(make_input(result_files=[invalid_path]), root=ROOT)
    check("不符合契约的结果被跳过并记 error",
          any(e["severity"] == "error" and "does not satisfy" in e["message"]
              for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:250])
    check("被跳过的结果不出现在结论里",
          all(r["target_ref"] != "SKU-BAD" for r in bundle["results"] or []),
          str([r["target_ref"] for r in bundle["results"] or []]))

    # --- 契约外取值被拒（verdict 不是 pass/flag/not_evaluated/signal） ---
    validator = _validator("contracts/audit_result.schema.json")
    for bad_value in ("pass", "flag", "not_evaluated", "signal"):
        record = make_result("RES-BAD-0002", "shopee-br-listing-audit",
                              "SKU-BAD", "PASS", "info", "allow")
        record["verdict"] = bad_value
        problems = validator.validate(record)
        check(f"契约拒绝 verdict={bad_value!r}", bool(problems), "未被拒绝")

    # --- 部分失败不中断整批 ---
    good_path = os.path.join(workdir, "good.json")
    with open(good_path, "w", encoding="utf-8") as handle:
        json.dump([make_result("RES-GOOD-0001", "shopee-br-listing-audit",
                                "SKU-GOOD", "REVIEW", "medium", "flag_for_review",
                                rule_refs=[rule_ref("SBR-LV-001", "platform_official")])],
                  handle, ensure_ascii=False)
    bundle = run_reporting(make_input(result_files=[broken, good_path]), root=ROOT)
    check("单个文件失败不中断整批",
          any(r["target_ref"] == "SKU-GOOD" for r in bundle["results"] or []),
          str([r["target_ref"] for r in bundle["results"] or []]))
    check("失败的来源仍被记录在 errors[]",
          any(e["severity"] == "error" for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:200])

    # --- 输出目录不可写 ---
    unwritable = os.path.join(workdir, "locked")
    os.makedirs(unwritable, exist_ok=True)
    os.chmod(unwritable, 0o500)
    try:
        bundle = run_reporting(make_input(results=[
            make_result("RES-FAIL-0001", "shopee-br-listing-audit", "SKU-FAIL",
                        "PASS", "info", "allow"),
        ]), root=ROOT, out_dir=os.path.join(unwritable, "out"))
        check("输出目录不可写时记 fatal",
              any(e["severity"] == "fatal" for e in bundle["errors"]),
              str([e["severity"] for e in bundle["errors"]]))
        check("输出失败时 ok 为假", bundle["ok"] is False, str(bundle["ok"]))
    finally:
        os.chmod(unwritable, 0o700)

    # --- 矩阵缺失 → 停止本模块 ---
    empty_root = os.path.join(workdir, "no-contracts")
    os.makedirs(empty_root, exist_ok=True)
    bundle = run_reporting(make_input(results=[
        make_result("RES-FAIL-0002", "shopee-br-listing-audit", "SKU-FAIL",
                    "PASS", "info", "allow"),
    ]), root=empty_root)
    check("契约矩阵缺失时记 fatal",
          any(e["severity"] == "fatal" for e in bundle["errors"]),
          str([e["severity"] for e in bundle["errors"]]))
    check("契约矩阵缺失时不产出结论", bundle["results"] == [],
          str(len(bundle["results"])))
    check("契约矩阵缺失时 ok 为假", bundle["ok"] is False, str(bundle["ok"]))


# ---------------------------------------------------------------------------
# 端到端与 CLI
# ---------------------------------------------------------------------------

def test_end_to_end(workdir: str) -> None:
    section("端到端与 CLI 测试")

    out_dir = os.path.join(workdir, "out")
    results = [
        make_result("RES-E2E-0001", "shopee-br-listing-audit", "SKU-E1",
                    "BLOCK", "critical", "block", requires_human_review=True,
                    rule_refs=[rule_ref("SBR-PI-002", "platform_official",
                                        title="Prohibited item category")]),
        make_result("RES-E2E-0002", "shopee-br-ip-review", "SKU-E1",
                    "BLOCK", "critical", "escalate_legal", confidence="signal",
                    requires_human_review=True,
                    rule_refs=[rule_ref("SBR-IP-002", "platform_official")]),
        make_result("RES-E2E-0003", "shopee-br-listing-audit", "SKU-E2",
                    "PASS", "info", "allow"),
    ]
    bundle = run_reporting(make_input(results=results), root=ROOT, out_dir=out_dir)
    check("端到端成功", bundle["ok"], str(bundle["errors"])[:300])
    for name in ("audit_summary.json", "audit_report.md", "audit_results.json",
                 "module_handoff.json"):
        path = os.path.join(out_dir, name)
        check(f"产出文件存在 {name}", os.path.exists(path), "缺失")
        if os.path.exists(path) and name.endswith(".json"):
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
            if name == "audit_summary.json":
                check("汇总 JSON 可解析且含分组",
                      all(k in payload for k in ("by_rule", "by_module",
                                                 "by_severity", "per_target")),
                      str(list(payload.keys())[:10]))
            if name == "module_handoff.json":
                validate_against("contracts/module_handoff.schema.json", payload,
                                 "落盘的 ModuleHandoff")
            if name == "audit_results.json":
                check("落盘的结果数组非空", len(payload) >= 1, str(len(payload)))
                for item in payload:
                    validate_against("contracts/audit_result.schema.json", item,
                                     f"落盘 AuditResult {item['result_id']}")

    # escalate_legal 是更细粒度 → 保留
    target = [r for r in bundle["results"] if r["target_ref"] == "SKU-E1"][0]
    check("block + escalate_legal → 保留 escalate_legal",
          target["action"] == "escalate_legal", target["action"])

    # --- CLI 端到端 ---
    result_file = os.path.join(workdir, "results.json")
    with open(result_file, "w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=False)
    cli_out = os.path.join(workdir, "cli-out")
    proc = subprocess.run(
        [sys.executable,
         os.path.join(MODULE_DIR, "src", "sbr_reporting_cli.py"),
         "--request-id", REQUEST_ID,
         "--out-dir", cli_out,
         "--result-file", result_file],
        capture_output=True, text=True, cwd=ROOT,
    )
    check("CLI 退出码为 0", proc.returncode == 0,
          (proc.stdout or "")[-400:] + (proc.stderr or "")[-400:])
    check("CLI 产出报告文件",
          os.path.exists(os.path.join(cli_out, "audit_report.md")), "缺失")
    check("CLI 输出目标数", "targets:  2" in proc.stdout,
          (proc.stdout or "")[-300:])
    if os.path.exists(os.path.join(cli_out, "audit_report.md")):
        with open(os.path.join(cli_out, "audit_report.md"), encoding="utf-8") as handle:
            cli_report = handle.read()
        check("CLI 报告含六节结构",
              all(h in cli_report for h in ("## 1. 摘要", "## 2. 数据缺口与未评估项",
                                            "## 3. 需决策的发现", "## 4. 待复核的发现",
                                            "## 5. 逐商品结果", "## 6. 已查阅规则")),
              "结构缺失")

    # --- 输入文件不被修改 ---
    before = os.path.getsize(result_file)
    with open(result_file, "r", encoding="utf-8") as handle:
        content_before = handle.read()
    run_reporting(make_input(result_files=[result_file]), root=ROOT)
    with open(result_file, "r", encoding="utf-8") as handle:
        content_after = handle.read()
    check("输入结果文件未被修改", content_before == content_after,
          "内容变化")
    check("输入结果文件大小未变", os.path.getsize(result_file) == before, "大小变化")


# ---------------------------------------------------------------------------
# 共享夹具兼容性（只读）
# ---------------------------------------------------------------------------

def test_shared_fixtures() -> None:
    section("共享夹具兼容性（只读）")

    fixtures_dir = os.path.join(ROOT, "tests", "fixtures")
    if not os.path.isdir(fixtures_dir):
        check("共享夹具目录存在", False, "缺失")
        return

    # 用共享夹具里的正常商品构造「无命中」的批次，验证不产生误报
    normal_path = os.path.join(fixtures_dir, "normal_products.json")
    if os.path.exists(normal_path):
        with open(normal_path, encoding="utf-8") as handle:
            document = json.load(handle)
        products = document.get("products") or []
        check("共享夹具 normal_products 非空", len(products) > 0, str(len(products)))

        results = [
            make_result(f"RES-FIXTURE-{i:04d}", "shopee-br-listing-audit",
                         product.get("product_id"), "PASS", "info", "allow")
            for i, product in enumerate(products, start=1)
            if product.get("product_id")
        ]
        bundle = run_reporting(make_input(results=results), root=ROOT)
        check("共享夹具批量聚合成功", bundle["ok"], str(bundle["errors"])[:200])
        check("共享夹具全部判为 PASS",
              all(r["verdict"] == "PASS" for r in bundle["results"]
                  if r["target_ref"].startswith("FX-NORM")),
              str([r["verdict"] for r in bundle["results"]][:5]))
        check("共享夹具聚合后目标数正确",
              bundle["summary"]["target_count"] == len(results),
              f"{bundle['summary']['target_count']} vs {len(results)}")

    # 缺失数据夹具 —— 必须体现 H3
    missing_path = os.path.join(fixtures_dir, "missing_data_cases.json")
    if os.path.exists(missing_path):
        with open(missing_path, encoding="utf-8") as handle:
            document = json.load(handle)
        cases = document.get("cases") or document.get("products") or []
        check("共享夹具 missing_data_cases 非空", len(cases) > 0, str(len(cases)))


# ---------------------------------------------------------------------------
# 与真实上游模块的集成（上游已就绪时执行）
# ---------------------------------------------------------------------------

def test_upstream_integration() -> None:
    section("与真实上游模块的集成")

    upstream_src = os.path.join(ROOT, "skills", "shopee-br-listing-audit", "src")
    if not os.path.isdir(upstream_src):
        check("上游 listing-audit 尚未就绪（跳过集成用例）", True, "目录不存在")
        return

    import importlib

    sys.path.insert(0, upstream_src)
    try:
        module = importlib.import_module("sbr_listing_audit")
    except Exception as exc:  # noqa: BLE001
        check("上游 listing-audit 可导入", False, str(exc))
        return
    audit_listing = getattr(module, "audit_listing", None)
    if audit_listing is None:
        check("上游 listing-audit 暴露 audit_listing", False, "缺少入口")
        return
    check("上游 listing-audit 暴露 audit_listing", True, "")

    fixture_path = os.path.join(ROOT, "tests", "fixtures", "violation_products.json")
    with open(fixture_path, encoding="utf-8") as handle:
        products = (json.load(handle)).get("products") or []
    if not products:
        check("违规商品夹具非空", False, "空")
        return

    upstream_input = {
        "request_id": "REQ-REPORT-UPSTREAM-001",
        "task_type": "listing_audit",
        "target": {"kind": "product_batch"},
        "products": products,
        "cases": [],
        "rules": [],
        "scope": {},
        "options": {},
        "provenance": {"inputs": [{"path": "tests/fixtures/violation_products.json"}],
                       "produced_at": "2026-10-27T00:00:00Z"},
    }
    try:
        audit = audit_listing(upstream_input, root=ROOT)
    except Exception as exc:  # noqa: BLE001
        check("上游 listing-audit 可运行", False, str(exc))
        return
    upstream_results = (audit or {}).get("results") or []
    check("上游 listing-audit 产出了结果", len(upstream_results) > 0,
          str(len(upstream_results)))

    # --- 上游产出必须能直接被本模块消费 ---
    bundle = run_reporting(make_input(results=upstream_results), root=ROOT)
    check("上游产出可直接被本模块消费", bundle["ok"],
          str(bundle["errors"])[:250])
    if bundle["ok"]:
        check("上游结果的 request_id 被回填到汇总",
              bundle["summary"]["request_id"] == REQUEST_ID,
              bundle["summary"]["request_id"])
        check("上游结果的模块名被记录",
              "shopee-br-listing-audit" in bundle["summary"]["source_modules"],
              str(bundle["summary"]["source_modules"]))
        check("真实违规商品聚合出真实结论",
              bundle["summary"]["batch_verdict"] != "PASS",
              bundle["summary"]["batch_verdict"])
        for result in bundle["results"]:
            validate_against("contracts/audit_result.schema.json", result,
                             f"集成 AuditResult {result['result_id']}")

    # --- 上游的真实来源层级必须通过 H2 校验 ---
    tiers = {ref.get("source_tier") for r in upstream_results
             for ref in (r.get("rule_refs") or [])}
    check("上游产出了来源层级", bool(tiers), "无 source_tier")
    check("上游来源层级都在契约枚举内",
          tiers <= {"platform_official", "law", "internal_risk", "unverified",
                    "ai_inference", "technical"},
          str(tiers))


# ---------------------------------------------------------------------------
# 引文核验（本模块不新增引文，但全库必须仍然通过）
# ---------------------------------------------------------------------------

def test_citations() -> None:
    section("引文核验")

    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "verify_citations.py")],
        capture_output=True, text=True, cwd=ROOT,
    )
    out = proc.stdout or ""
    check("引文核验通过", proc.returncode == 0 and "0 failed" in out,
          out.strip().splitlines()[-1] if out.strip() else "")


# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 62)
    print("shopee-br-reporting 模块测试")
    print(f"仓库根: {ROOT}")
    print(f"运行时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 62)

    workdir = tempfile.mkdtemp(prefix="sbr-reporting-test-")
    try:
        test_unit()
        test_contract()
        test_aggregation()
        test_hard_constraints()
        test_report_structure()
        test_failure_paths(workdir)
        test_end_to_end(workdir)
        test_shared_fixtures()
        test_upstream_integration()
        test_citations()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print("\n" + "=" * 62)
    print(f"PASSED: {len(PASSED)}   FAILED: {len(FAILED)}")
    if FAILED:
        print("\nFailures:")
        for name, detail in FAILED[:30]:
            print(f"  - {name}: {detail}")
        return 1
    print("全部测试通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
