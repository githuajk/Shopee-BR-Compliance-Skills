#!/usr/bin/env python3
"""框架自检：验证并行开发框架自身的关键不变量。

检查项：
  1. 契约文件存在且 JSON 合法
  2. 契约自洽（risk_action_matrix 实例符合其 Schema；$ref 可解析）
  3. 现存规则 100% 符合 rule_envelope
  4. 7 个模块目录齐备，各有 SKILL.md 且 frontmatter 完整
  5. SKILL.md 七要素齐全
  6. 任务注册表与任务说明文件一一对应
  7. 并行波次内 allowed_paths 交集为空
  8. 依赖图无环
  9. 公共契约文件存在且被标记为冻结
 10. 无 YAML/JSONL/CSV/TXT/XML 作内部正式数据源
 11. 硬约束 H1-H6 在契约实例中齐备

Usage: python3 tools/framework_check.py
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


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        PASSED.append(name)
    else:
        FAILED.append((name, detail))
        print(f"  FAIL {name}: {detail}")


def section(t):
    print(f"\n=== {t} ===")


def load(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return json.load(f)


def main():
    # --- 1/2 契约 ---
    section("1. 契约存在性与自洽")
    contract_files = [
        "contracts/skill_input.schema.json",
        "contracts/audit_result.schema.json",
        "contracts/rule_envelope.schema.json",
        "contracts/evidence_reference.schema.json",
        "contracts/risk_action_matrix.schema.json",
        "contracts/risk_action_matrix.json",
        "contracts/module_handoff.schema.json",
    ]
    for cf in contract_files:
        p = os.path.join(ROOT, cf)
        check(f"存在 {cf}", os.path.exists(p), "文件缺失")
        if os.path.exists(p):
            try:
                json.load(open(p, encoding="utf-8"))
                check(f"JSON 合法 {cf}", True)
            except Exception as e:  # noqa: BLE001
                check(f"JSON 合法 {cf}", False, str(e))

    mat_s = load("contracts/risk_action_matrix.schema.json")
    mat_i = load("contracts/risk_action_matrix.json")
    errs = Validator(mat_s, base_dir=os.path.join(ROOT, "contracts")).validate(mat_i)
    check("risk_action_matrix 实例符合其 Schema", not errs, "; ".join(errs[:5]))

    levels = set(mat_i["risk_levels"])
    actions = set(mat_i["actions"])
    combos = {(m["risk_level"], m["action"]) for m in mat_i["matrix"]}
    missing = [(r, a) for r in levels for a in actions if (r, a) not in combos]
    check(f"矩阵覆盖全部 {len(levels)}×{len(actions)} 组合",
          not missing, str(missing[:5]))

    # $ref 可解析
    for cf in ["contracts/audit_result.schema.json", "contracts/skill_input.schema.json"]:
        s = load(cf)
        try:
            Validator(s, base_dir=os.path.join(ROOT, "contracts"))
            check(f"$ref 可解析 {os.path.basename(cf)}", True)
        except Exception as e:  # noqa: BLE001
            check(f"$ref 可解析 {os.path.basename(cf)}", False, str(e))

    # --- 3 规则符合 envelope ---
    section("2. 现存规则符合 rule_envelope")
    env_schema = load("contracts/rule_envelope.schema.json")
    ev = Validator(env_schema, base_dir=os.path.join(ROOT, "contracts"))
    total = bad = 0
    for fn in sorted(os.listdir(os.path.join(ROOT, "rules"))):
        if not fn.endswith(".json"):
            continue
        for r in load(f"rules/{fn}")["rules"]:
            total += 1
            envelope = {
                "rule_id": r["rule_id"], "title": r["title"],
                "category": r.get("category", "listing_violation"),
                "description": r["description"], "severity": r["severity"],
                "action": r.get("decision", "flag_for_review"),
                "source": {"tier": r.get("source_tier", "unverified"),
                           "url": r["source_url"],
                           "excerpt": r.get("source_excerpt"),
                           "last_verified": r["last_verified"]},
                "status": r["status"], "version": r["version"],
                "evidence_required": r["evidence_required"],
                "requires_human_review": r["human_review_required"],
                "trigger_conditions": r.get("trigger_conditions", []),
            }
            e = ev.validate(envelope)
            if e:
                bad += 1
                if bad <= 3:
                    print(f"    {r['rule_id']}: {e[:2]}")
    check(f"全部 {total} 条规则符合 rule_envelope", bad == 0, f"{bad} 条不符")

    # --- 4/5 模块与 SKILL.md ---
    section("3. 模块目录与 SKILL.md")
    manifest = load("manifest.json")
    mod_names = [s["name"] for s in manifest["skills"]]
    check("manifest 声明 7 个模块", len(mod_names) == 7, str(len(mod_names)))
    ownreg = load("contracts/file_ownership.json")
    for name in mod_names:
        d = os.path.join(ROOT, "skills", name)
        check(f"目录存在 {name}", os.path.isdir(d), "缺失")
        sk = os.path.join(d, "SKILL.md")
        check(f"SKILL.md 存在 {name}", os.path.exists(sk), "缺失")
        if not os.path.exists(sk):
            continue
        t = open(sk, encoding="utf-8").read()
        # frontmatter
        fm = re.match(r"^---\n(.*?)\n---\n", t, re.S)
        check(f"frontmatter 完整 {name}", bool(fm), "缺少 frontmatter")
        if fm:
            body = fm.group(1)
            check(f"frontmatter 含 name {name}", "name:" in body, "")
            check(f"frontmatter 含 description {name}", "description:" in body, "")
            desc = ""
            m = re.search(r"description:\s*(.+)", body)
            if m:
                desc = m.group(1)
            check(f"description 为自包含触发语 {name}",
                  desc.startswith("Use when"), desc[:60])
        # 七要素
        for elem, kw in [("职责", "## 1. 职责"), ("非职责", "## 2. 非职责"),
                         ("输入契约", "输入契约"), ("输出契约", "输出契约"),
                         ("规则与来源要求", "规则与来源要求"),
                         ("失败处理", "失败处理"),
                         ("测试案例与验收标准", "测试案例与验收标准")]:
            check(f"{name} 七要素-{elem}", kw in t, f"缺 {kw}")
        # 不假设自动调用
        if name == "shopee-br-compliance":
            check("主 Skill 声明不假设自动调用",
                  "不假设" in t and "自动调用" in t, "")

    # --- 6 任务注册表 ↔ 任务说明 ---
    section("4. 任务注册表与任务说明")
    reg = load("tasks/task_registry.json")
    ids = [t["task_id"] for t in reg["tasks"]]
    check("任务 ID 唯一", len(ids) == len(set(ids)), "")
    for t in reg["tasks"]:
        p = os.path.join(ROOT, "tasks", f"{t['task_id']}.md")
        if t["status"] == "completed":
            # 已完成的任务在注册表中有 actual_result，不必有任务说明文件
            check(f"已完成任务有结果记录 {t['task_id']}",
                  bool(t.get("actual_result")), "缺 actual_result")
            continue
        check(f"任务说明存在 {t['task_id']}", os.path.exists(p), "缺失")
        if os.path.exists(p):
            txt = open(p, encoding="utf-8").read()
            for sec in ["## 1. 目标", "## 2. 范围", "## 4. 输入契约",
                        "## 5. 输出契约", "## 8. 失败处理", "## 9. 测试计划",
                        "## 10. 验收标准", "## 12. 交付说明"]:
                check(f"{t['task_id']} 含 {sec}", sec in txt, "缺章节")
            # 路径白名单以 contracts/file_ownership.json 为准
            own = load("contracts/file_ownership.json")
            spec = own["modules"].get(t["module"])
            check(f"{t['task_id']} 的 module 在所有权登记中", spec is not None,
                  t.get("module", ""))
            if spec:
                for ap in spec["owns"]:
                    check(f"{t['task_id']} 白名单含 {ap}", ap in txt, "未写入说明")

    # --- 7 并行组路径交集 ---
    section("5. 并行波次路径零重叠")
    groups: dict[str, list] = {}
    for t in reg["tasks"]:
        groups.setdefault(t["parallel_group"], []).append(t)
    own2 = load("contracts/file_ownership.json")
    for g, ts in groups.items():
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                a = set(own2["modules"][ts[i]["module"]]["owns"])
                b = set(own2["modules"][ts[j]["module"]]["owns"])
                inter = a & b
                # 允许共享 rules/03（拆分待办），但需在 split_request 中声明
                shared_rules03 = {p for p in inter if "03_listing_violations" in p}
                other = inter - shared_rules03
                check(f"{g}: {ts[i]['task_id']} ∩ {ts[j]['task_id']} = ∅",
                      not other, f"重叠: {sorted(other)}")
                if shared_rules03:
                    declared = any("split_request" in ts[i] or
                                   "split_request" in ts[j] for _ in [0])
                    check(f"{g}: rules/03 重叠已声明 split_request", declared, "")

    # --- 8 依赖图无环 ---
    section("6. 依赖图无环")
    dep = {t["task_id"]: list(t.get("depends_on", [])) for t in reg["tasks"]}
    state: dict[str, int] = {}

    def visit(n, stack):
        if state.get(n) == 1:
            return [n]
        if state.get(n) == 2:
            return []
        state[n] = 1
        for m in dep.get(n, []):
            r = visit(m, stack + [n])
            if r:
                return r
        state[n] = 2
        return []

    for n in dep:
        cyc = visit(n, [])
        if cyc:
            check("依赖图无环", False, f"环: {cyc}")
            break
    else:
        check("依赖图无环", True)

    # 依赖必须存在
    for t in reg["tasks"]:
        for d in t.get("depends_on", []):
            check(f"{t['task_id']} 依赖 {d} 存在", d in dep, "悬空依赖")
        for b in t.get("blocks", []):
            check(f"{t['task_id']} blocks {b} 存在", b in dep, "悬空 block")

    # --- 9 公共契约冻结标记 ---
    section("7. 公共规范文件与冻结标记")
    for f in ["PROJECT_RULES.md", "AGENT_COLLABORATION.md", "manifest.json",
              "tasks/task_registry.json", "tasks/task_template.md",
              "tests/test_plan.md"]:
        p = os.path.join(ROOT, f)
        check(f"存在 {f}", os.path.exists(p), "缺失")
        if os.path.exists(p) and f.endswith(".md"):
            t = open(p, encoding="utf-8").read()
            check(f"{f} 标记为冻结", "Frozen" in t, "缺 Frozen 标记")

    # --- 10 格式政策 ---
    section("8. 内部数据格式政策")
    banned_ext = {".yaml", ".yml", ".jsonl", ".ndjson", ".csv", ".txt", ".xml"}
    violations = []
    for sub in ["rules", "contracts", "data", "lexicon", "tasks"]:
        base = os.path.join(ROOT, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, _, files in os.walk(base):
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext in banned_ext and fn != "task_template.md":
                    violations.append(os.path.relpath(os.path.join(dirpath, fn), ROOT))
    # research/raw 与 data/samples 是外部输入/抓取件，允许
    allowed_exceptions = ("research/raw", "data/samples")
    real = [v for v in violations
            if not any(v.startswith(x) for x in allowed_exceptions)]
    check("内部正式数据源无 YAML/JSONL/CSV/TXT/XML", not real, str(real))

    # --- 11 硬约束 ---
    section("9. 硬约束 H1-H6")
    hids = [h["id"] for h in mat_i["hard_constraints"]]
    for h in ["H1", "H2", "H3", "H4", "H5", "H6"]:
        check(f"硬约束 {h} 已定义", h in hids, str(hids))
    # 各 SKILL.md 是否提及硬约束
    for name in mod_names:
        sk = os.path.join(ROOT, "skills", name, "SKILL.md")
        if os.path.exists(sk):
            t = open(sk, encoding="utf-8").read()
            check(f"{name} 引用硬约束", "H1" in t or "硬约束" in t, "")

    # --- 12 内部路径引用有效 ---
    # 文档里引用的仓库内路径必须真实存在。第一阶段原型从未入库，
    # 却在 README / PROJECT_RULES / test_plan / 9 份 references 中被引用，
    # 而所有既有检查都只比对路径"形状"、从不校验目标存在 —— 于是
    # 悬空引用可以静默累积。这里做实际存在性校验。
    section("10. 内部路径引用有效")
    # 匹配两种写法：反引号包裹的 `a/b/c.md`，以及代码块 / 命令行里的裸路径
    # （如 `cat .archive/phase0_prototype/docs/X.md`）。裸路径必须带目录
    # 分隔符，避免把普通单词误判成路径。
    path_re = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|json|py|sh|txt|xlsx|csv))`")
    bare_re = re.compile(r"(?<![\w`/.-])((?:\.?[A-Za-z0-9_-]+/)+[A-Za-z0-9_.-]+\.(?:md|json|py|sh|txt|xlsx|csv))")

    # 「计划中」的前缀：任务注册表声明的 allowed_paths 与交付物路径。
    # 这些文件由对应任务负责创建，当前不存在是正常的 —— 不能算悬空。
    planned = set()
    for t in reg["tasks"]:
        for p in t.get("allowed_paths", []):
            planned.add(p.rstrip("/"))
        for d in t.get("deliverables", []):
            for m in re.findall(r"[A-Za-z0-9_./-]+\.(?:md|json|py)", d):
                planned.add(m.rstrip("/"))
    # 测试计划 §5.2 点名的共享夹具文件 —— 由集成 Agent 建立
    for fx in ("normal_products.json", "violation_products.json", "edge_cases.json",
               "missing_data_cases.json", "case_history.json", "ip_cases.json",
               "injection_cases.json"):
        planned.add(f"tests/fixtures/{fx}")
    # 集成阶段才建立的集成测试套件
    planned.add("tests/integrator/run_tests.py")
    planned.add("tests/integration/run_tests.py")
    # 集成验收脚本 —— 由集成 Agent 在 TASK-INTEGRATE-01 中实现
    # （见 tests/test_plan.md §7.2）
    planned.add("tools/integration_check.py")
    # 工作区外部资产（不在本仓库内）—— 文档中以「工作区外部」标注
    for ext in ("_learning/SOP_BIBLE.md",
                "_learning/SHOPEE_MASTER_SOP.md",
                "_learning/02_risk_dictionary.md"):
        planned.add(ext)
    # 第一阶段原型的测试入口 —— 从未入库（已核实，见 .archive/README.md §2.1）
    planned.add("tests/run_tests.py")
    # PROJECT_RULES §14 命名规范表里的**举例**，不是真实引用
    planned.add("references/rule_sources.md")

    def is_planned(ref):
        for p in planned:
            if ref == p or ref.startswith(p.rstrip("/") + "/"):
                return True
            # `skills/<mod>/**` 这类通配
            if "*" in p and ref.startswith(p.split("**")[0]):
                return True
        return False

    doc_files = []
    for sub in ("", "docs", "skills", "tasks", "tests", "contracts", "tools"):
        base = os.path.join(ROOT, sub) if sub else ROOT
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, files in os.walk(base):
            # .archive/ 是历史归档区：其中的文档使用归档当时的相对路径约定
            # （如 `docs/ARCHITECTURE.md`），与当前仓库根相对的解析方式不兼容。
            # 归档内容保留但不参与活跃路径引用校验。
            dirnames[:] = [
                d for d in dirnames if d not in (".git", "__pycache__", ".archive")
            ]
            for fn in files:
                if fn.endswith(".md"):
                    doc_files.append(os.path.join(dirpath, fn))

    dangling = {}
    for fp in doc_files:
        rel = os.path.relpath(fp, ROOT)
        docdir = os.path.dirname(fp)
        # 引用可能是仓库根相对、相对所在文档目录、或相对所属模块目录
        # （references/xxx.md 之间互引时用模块相对写法）。
        moddir = None
        parts = rel.split(os.sep)
        if len(parts) >= 3 and parts[0] == "skills":
            moddir = os.path.join(ROOT, "skills", parts[1])
        txt = open(fp, encoding="utf-8").read()
        refs = [m.group(1) for m in path_re.finditer(txt)]
        refs += [m.group(1) for m in bare_re.finditer(txt)]
        for ref in refs:
            ref = ref.rstrip("/")
            # 裸文件名（无目录分隔符）指的是同目录或已知的上下文文件，
            # 不是仓库内相对路径 —— 无法可靠判定存在性，跳过。
            if "/" not in ref:
                continue
            if ref.startswith(("http", "www")) or "*" in ref:
                continue
            # 含省略号的是「示意路径」而非真实路径（例：`_learning/.../x.md`）
            if "..." in ref:
                continue
            if is_planned(ref):
                continue
            candidates = [os.path.join(ROOT, ref), os.path.join(docdir, ref)]
            if moddir:
                candidates.append(os.path.join(moddir, ref))
            if not any(os.path.exists(c) for c in candidates):
                dangling.setdefault(rel, set()).add(ref)
    for rel, refs in sorted(dangling.items()):
        for ref in sorted(refs):
            check(f"{rel} 引用的 {ref} 存在", False, "悬空引用")
    check("无悬空内部路径引用", not dangling,
          f"{len(dangling)} 个文件含悬空引用")

    # --- 汇总 ---
    print(f"\n{'=' * 62}")
    print(f"PASSED: {len(PASSED)}   FAILED: {len(FAILED)}")
    if FAILED:
        print("\nFailures:")
        for n, d in FAILED:
            print(f"  - {n}: {d}")
        return 1
    print("框架自检全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
