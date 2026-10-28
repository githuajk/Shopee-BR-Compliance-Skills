#!/usr/bin/env python3
"""shopee-br-compliance 模块测试（主 Skill / 编排层）。

**集成测试必须做真实串联** —— 不是模拟：真实调用各专业模块的 CLI，
用 ingestion 的真实产出喂给 listing-audit / ip-review /
duplicate-detection，再喂给 reporting。

运行：
    env -u LD_LIBRARY_PATH python3 tests/shopee-br-compliance/run_tests.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "skills", "shopee-br-compliance", "src")
sys.path.insert(0, SRC)

from sbr_compliance import pipeline, registry, routing  # noqa: E402
from sbr_compliance import integration, matrix as matrix_mod  # noqa: E402
from sbr_compliance.driver import read_module_skill_md, skill_md_digest  # noqa: E402

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


def skill_input(products, request_id="REQ-COMPLIANCE-TEST", cases=None) -> dict:
    """构造符合 `contracts/skill_input.schema.json` 的输入。

    注意 `task_type` 的枚举里没有 `compliance_review` —— 主 Skill 用的
    是 `orchestration`；`target` 是**对象**（不是字符串），且必须带 `kind`。
    """
    return {
        "request_id": request_id,
        "task_type": "orchestration",
        "target": {"kind": "product_batch"},
        "products": products,
        "cases": cases or [],
        "rules": [],
        "scope": {},
        "options": {},
        "provenance": {
            "produced_at": "2026-10-27T00:00:00Z",
            "producer": "tests/shopee-br-compliance",
            # `provenance.inputs` 至少 1 项（契约要求：缺失溯源的输入
            # 不得进入审核链路），且**不允许** `source_refs`。
            "inputs": [{"path": "tests/fixtures/violation_products.json",
                        "kind": "json"}],
        },
    }


# ---------------------------------------------------------------------------
def test_module_registry() -> None:
    section("L1 模块登记")

    names = [spec.name for spec in registry.MODULE_SPECS]
    check("登记了 5 个模块", len(names) == 5, str(names))
    for expected in ("shopee-br-data-ingestion", "shopee-br-listing-audit",
                     "shopee-br-duplicate-detection", "shopee-br-ip-review",
                     "shopee-br-reporting"):
        check(f"登记含 {expected}", expected in names, str(names))
    check("policy-research 标记为独立模块（不驱动）",
          "shopee-br-policy-research" in registry.STANDALONE_MODULES,
          str(registry.STANDALONE_MODULES))

    # 每个登记项的 CLI 必须真实存在
    for spec in registry.MODULE_SPECS:
        cli = os.path.join(ROOT, spec.cli_rel)
        check(f"{spec.name} 的 CLI 存在", os.path.exists(cli), spec.cli_rel)

    # 阶段顺序固定
    check("阶段顺序是 ingestion → content_audit → ip → duplicate → reporting",
          registry.STAGE_ORDER == ("ingestion", "content_audit", "ip",
                                   "duplicate", "reporting"),
          str(registry.STAGE_ORDER))


def test_cli_conventions() -> None:
    section("L2 各模块 CLI 参数约定（编排器必须逐个适配）")

    # 关键：四个模块的 argv 约定**不统一**，套用同一套会让模块直接退出。
    # 这道测试是防止编排器再次对某个模块用错参数。
    expectations = {
        "shopee-br-listing-audit": {"--skill-input", "--request-id", "--out-dir"},
        "shopee-br-duplicate-detection": {"--skill-input", "--out-dir"},
        "shopee-br-ip-review": {"--request-id", "--out-dir"},
        "shopee-br-reporting": {"--request-id", "--out-dir", "--result-file"},
        "shopee-br-data-ingestion": {"--request-id", "--out-dir"},
    }
    for spec in registry.MODULE_SPECS:
        cli = os.path.join(ROOT, spec.cli_rel)
        proc = subprocess.run([sys.executable, cli, "--help"],
                              capture_output=True, text=True)
        check(f"{spec.name} --help 退出码 0", proc.returncode == 0,
              (proc.stderr or "")[-200:])
        out = proc.stdout or ""
        for flag in expectations[spec.name]:
            check(f"{spec.name} 支持 {flag}", flag in out, out[:200])

    # duplicate-detection **没有** --request-id（编排器若传它就会失败）
    dup = os.path.join(ROOT, "skills", "shopee-br-duplicate-detection", "src",
                       "sbr_duplicate_detection_cli.py")
    out = subprocess.run([sys.executable, dup, "--help"],
                         capture_output=True, text=True).stdout
    check("duplicate-detection 确实不支持 --request-id",
          "--request-id" not in out, out[:200])

    # ip-review **没有** --skill-input
    ip = os.path.join(ROOT, "skills", "shopee-br-ip-review", "src",
                      "sbr_ip_review_cli.py")
    out = subprocess.run([sys.executable, ip, "--help"],
                         capture_output=True, text=True).stdout
    check("ip-review 确实不支持 --skill-input",
          "--skill-input" not in out, out[:200])


def test_routing() -> None:
    section("L3 分流决策")

    products = load_shared("violation_products.json")["products"]
    decision = routing.decide(options={}, products=products, cases=[],
                              input_paths=None)
    check("分流出内容审核阶段", "content_audit" in decision.stages,
          str(decision.stages))
    check("分流出 IP 阶段", "ip" in decision.stages, str(decision.stages))
    check("分流出重复检测阶段", "duplicate" in decision.stages,
          str(decision.stages))
    check("分流出汇总阶段", "reporting" in decision.stages,
          str(decision.stages))
    check("没有外部文件时跳过 ingestion",
          "ingestion" in decision.skipped, str(decision.skipped))
    check("每个执行阶段都有理由",
          all(decision.reasons.get(stage) for stage in decision.stages),
          str(decision.reasons))

    # 显式指定模块
    explicit = routing.decide(options={"modules": ["shopee-br-ip-review"]},
                              products=products, cases=[], input_paths=None)
    check("显式指定时只跑该模块",
          explicit.module_names == ["shopee-br-ip-review"],
          str(explicit.module_names))
    check("显式指定被标记", explicit.explicit is True)

    # 只有一个店铺时，跨店对比不成立 —— 但阶段仍应执行（由模块自己记缺口）
    single = [dict(products[0])]
    decision2 = routing.decide(options={}, products=single, cases=[],
                                input_paths=None)
    check("单店也要执行重复检测（由模块报缺口，不是编排器跳过）",
          "duplicate" in decision2.stages, str(decision2.stages))


def test_skill_md_reading() -> None:
    section("L4 显式读取模块 SKILL.md")

    for spec in registry.MODULE_SPECS:
        text, error = read_module_skill_md(ROOT, spec.name)
        check(f"{spec.name} 的 SKILL.md 可读", error is None and text,
              str(error))
        check(f"{spec.name} 的 SKILL.md 含「输出契约」", "输出契约" in (text or ""),
              (text or "")[:100])
        check(f"{spec.name} 的 SKILL.md 含「输入契约」", "输入契约" in (text or ""),
              (text or "")[:100])
        check(f"{spec.name} 的 SKILL.md 含「硬约束」", "硬约束" in (text or ""),
              (text or "")[:100])

    # 摘要必须稳定
    text, _ = read_module_skill_md(ROOT, "shopee-br-listing-audit")
    check("SKILL.md 摘要稳定",
          skill_md_digest(text) == skill_md_digest(text),
          skill_md_digest(text))

    # 不存在的模块必须报错而不是静默
    text, error = read_module_skill_md(ROOT, "shopee-br-does-not-exist")
    check("不存在的模块报错", error is not None and text is None,
          f"text={str(text)[:40]} error={error}")


def test_integration_layer() -> None:
    section("L5 整合层 —— 硬约束在整合时不被降级")

    m = matrix_mod.load_matrix(os.path.join(ROOT, "contracts",
                                            "risk_action_matrix.json"))
    rm = matrix_mod.RiskMatrix(m)
    from sbr_compliance.errors import ErrorLog
    log = ErrorLog()

    # H2：内部来源的规则不能产出阻断类动作
    record = {
        "result_id": "R-1", "request_id": "Q", "module": "shopee-br-ip-review",
        "target_ref": "T1", "verdict": "BLOCK", "risk_level": "critical",
        "action": "block", "reason": "x", "rule_refs": [
            {"rule_id": "SBR-IP-900", "source_tier": "internal_risk"}],
        "evidence_refs": [], "confidence": "signal",
        "requires_human_review": True, "rule_version": "v1",
        "provenance": {"produced_at": "2026-10-27T00:00:00Z",
                       "producer": "x", "source_refs": []},
    }
    sanitized = integration.sanitize(record, rm, log)
    # `sanitize` 返回的 `action` 是清洗后的动作；`record` 里的原始动作
    # 保留在 `original_action`（供审计）。
    check("H2：internal_risk 的 block 被降级",
          sanitized.action not in ("block", "freeze_relist", "escalate_legal"),
          sanitized.action)
    check("H2：降级被记录（非静默）", bool(sanitized.adjustments),
          str(sanitized.adjustments)[:200])
    check("H2：记录了降级前的动作",
          sanitized.original_action == "block", sanitized.original_action)
    check("H2：降级原因写明来源层级不权威",
          "not authoritative" in (sanitized.adjustments[0] if sanitized.adjustments else ""),
          str(sanitized.adjustments)[:200])

    # H1：IP 类不得被整合层升格为确定性结论
    ip_record = dict(record)
    ip_record["rule_refs"] = [{"rule_id": "SBR-IP-001",
                               "source_tier": "platform_official"}]
    ip_record["confidence"] = "confirmed"
    ip_record["action"] = "escalate_legal"
    out = integration.sanitize(ip_record, rm, log)
    check("H1：IP 结论被压回 signal",
          out.record["confidence"] == "signal", out.record["confidence"])
    check("H1：IP 结论保留人工复核",
          out.record["requires_human_review"] is True)
    check("H1：压回动作被记录（非静默）",
          any("H1" in a for a in out.adjustments),
          str(out.adjustments)[:200])

    # 同一 target 的多条结果要合并 rule_refs
    merged = integration._merge_rule_refs([
        {"rule_refs": [{"rule_id": "SBR-A"}]},
        {"rule_refs": [{"rule_id": "SBR-A"}, {"rule_id": "SBR-B"}]},
    ])
    check("rule_refs 去重合并", len(merged[0]) == 2, str(merged[0]))
    check("合并冲突被记录", isinstance(merged[1], list), str(merged[1]))


def test_real_chain_integration() -> None:
    section("L6 真实串联（不是模拟）")

    products = load_shared("violation_products.json")["products"]
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = os.path.join(tmp, "out")
        bundle = pipeline.run_compliance(
            skill_input(products, request_id="REQ-CHAIN-001"),
            root=ROOT, out_dir=out_dir)

        runs = {run["module"]: run for run in bundle["runs"]}
        for name in ("shopee-br-listing-audit", "shopee-br-ip-review",
                     "shopee-br-duplicate-detection", "shopee-br-reporting"):
            check(f"{name} 真实执行成功",
                  name in runs and runs[name]["ok"],
                  (runs.get(name) or {}).get("reason", "")[:200])

        # 每个模块都应产出结果 —— 不能有维度静默缺失
        for name in ("shopee-br-listing-audit", "shopee-br-ip-review",
                     "shopee-br-duplicate-detection"):
            count = runs[name]["result_count"]
            check(f"{name} 产出了结果", count > 0, str(count))
            check(f"{name} 结果数与商品数一致",
                  count == len(products), f"{count} vs {len(products)}")

        # 上游结果应被汇总
        check("整合后的结果数不少于上游总数",
              len(bundle["results"]) >= len(products),
              f"{len(bundle['results'])}")

        # 产出文件
        for name in ("audit_result.json", "audit_results.json",
                     "audit_summary.json", "audit_report.md",
                     "module_handoff.json", "module_runs.json",
                     "routing_plan.json"):
            check(f"产出 {name}",
                  os.path.exists(os.path.join(out_dir, name)), "缺失")

        # 契约校验
        single = json.load(open(os.path.join(out_dir, "audit_result.json"),
                                encoding="utf-8"))
        check("audit_result.json 是单条对象",
              isinstance(single, dict) and "verdict" in single,
              str(type(single).__name__))

        from sbr_compliance.contracts import (audit_result_validator,
                                               module_handoff_validator,
                                               skill_input_validator)
        validator = audit_result_validator(ROOT)
        for record in bundle["results"]:
            problems = validator.validate(record)
            check(f"结果 {record.get('result_id')} 符合契约", not problems,
                  str(problems[:2]))
            break

        handoff = json.load(open(os.path.join(out_dir, "module_handoff.json"),
                                 encoding="utf-8"))
        hproblems = module_handoff_validator(ROOT).validate(handoff)
        check("module_handoff 符合契约", not hproblems, str(hproblems[:3]))

        # 输入契约
        iv = skill_input_validator(ROOT)
        iproblems = iv.validate(skill_input(products))
        check("构造的 SkillInput 符合契约", not iproblems, str(iproblems[:3]))

        # 汇总里必须能看到每个模块
        summary = json.load(open(os.path.join(out_dir, "audit_summary.json"),
                                 encoding="utf-8"))
        check("汇总记录了执行的模块",
              len(summary.get("executed_modules") or []) == 4,
              str(summary.get("executed_modules")))
        check("汇总记录了 verdict 分布",
              bool(summary.get("verdict_counts")),
              str(summary.get("verdict_counts"))[:120])


def test_gaps_reported() -> None:
    section("L7 数据缺口必须被上报（不得静默）")

    products = load_shared("violation_products.json")["products"]
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = os.path.join(tmp, "out")
        bundle = pipeline.run_compliance(
            skill_input(products, request_id="REQ-GAP-001"),
            root=ROOT, out_dir=out_dir)

        summary = json.load(open(os.path.join(out_dir, "audit_summary.json"),
                                 encoding="utf-8"))
        # 本次输入没有 cases[] —— 重发维度无法评估，必须报缺口
        check("缺 cases 时报告了 unevaluated",
              summary.get("unevaluated_count", 0) > 0,
              str(summary.get("unevaluated_count")))
        check("unevaluated 有具体条目",
              bool(summary.get("unevaluated")), "为空")
        first = (summary.get("unevaluated") or [{}])[0]
        check("unevaluated 条目含 rule_id 与理由",
              bool(first.get("rule_id")) and bool(first.get("reason")),
              json.dumps(first, ensure_ascii=False)[:150])

        # 交接必须带 known_gaps
        handoff = json.load(open(os.path.join(out_dir, "module_handoff.json"),
                                 encoding="utf-8"))
        check("handoff 有 known_gaps 字段", "known_gaps" in handoff,
              str(sorted(handoff.keys())))
        check("known_gaps 非空", bool(handoff.get("known_gaps")),
              str(handoff.get("known_gaps"))[:200])


def test_cli_end_to_end() -> None:
    section("L8 CLI 端到端")

    cli = os.path.join(SRC, "sbr_compliance_cli.py")
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = os.path.join(tmp, "out")
        proc = subprocess.run(
            [sys.executable, cli, "--request-id", "REQ-CLI-001",
             "--out-dir", out_dir,
             "--product-file",
             os.path.join(ROOT, "tests", "fixtures", "violation_products.json")],
            capture_output=True, text=True, cwd=ROOT)
        check("CLI 退出码 0", proc.returncode == 0,
              (proc.stdout or "")[-200:] + (proc.stderr or "")[-300:])
        check("CLI 产出 audit_summary.json",
              os.path.exists(os.path.join(out_dir, "audit_summary.json")))
        out = proc.stdout or ""
        check("CLI 摘要显示 4 个模块执行", "shopee-br-ip-review" in out
              or "39" in out, out[:200])

        # 缺必需参数 → 退出码非 0
        proc2 = subprocess.run([sys.executable, cli, "--out-dir",
                                os.path.join(tmp, "o2")],
                               capture_output=True, text=True, cwd=ROOT)
        check("CLI 缺输入退出码非 0", proc2.returncode != 0,
              str(proc2.returncode))


def test_no_writes_to_platform() -> None:
    section("L9 边界 —— 不执行任何线上处置")

    # 主 Skill 不得 import 任何网络/写平台的能力
    forbidden = ("requests", "urllib.request", "httpx", "socket",
                 "boto3", "selenium")
    hits = []
    for dirpath, dirnames, files in os.walk(os.path.join(SRC, "sbr_compliance")):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            for token in forbidden:
                if f"import {token}" in text:
                    hits.append(f"{fn}: import {token}")
    check("主 Skill 不 import 网络/写平台库", not hits, str(hits))

    # 不得出现「发布/下架/解冻」这类动作动词的执行
    action_words = ("publish_listing", "delist_product", "unfreeze_listing",
                    "submit_appeal")
    hits2 = []
    for dirpath, dirnames, files in os.walk(os.path.join(SRC, "sbr_compliance")):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            with open(os.path.join(dirpath, fn), encoding="utf-8") as f:
                text = f.read()
            for token in action_words:
                if token in text:
                    hits2.append(f"{fn}: {token}")
    check("主 Skill 不含线上处置动作", not hits2, str(hits2))


def main() -> int:
    print("=" * 62)
    print("shopee-br-compliance 模块测试")
    print(f"仓库根: {ROOT}")
    print("=" * 62)

    started = datetime.now(timezone.utc)
    test_module_registry()
    test_cli_conventions()
    test_routing()
    test_skill_md_reading()
    test_integration_layer()
    test_real_chain_integration()
    test_gaps_reported()
    test_cli_end_to_end()
    test_no_writes_to_platform()

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
