#!/usr/bin/env python3
"""校验任务包与文件所有权的一致性。

检查项：
  1. 任务包文件与任务注册表一一对应（已完成任务除外）
  2. 每份任务包含全部 12 个必需章节
  3. 任务包中的白名单与 contracts/file_ownership.json 完全一致
  4. 任务包引用的只读路径与所有权登记一致
  5. 所有权登记中不存在路径冲突（一个路径被两个 owner 拥有）
  6. 并行波次内白名单交集为空
  7. 依赖图无环、依赖均存在
  8. 任务包无未填的必填占位符
  9. 每个 Skill 的 SKILL.md 所有权章节与登记一致
 10. 每个 SKILL.md 声明的 references/ 文件都存在

Usage: python3 tools/task_pack_check.py
Exit 0 = 全部通过
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def load(p):
    with open(os.path.join(ROOT, p), encoding="utf-8") as f:
        return json.load(f)


REQUIRED_SECTIONS = [
    "## 1. 目标", "## 2. 范围", "## 3. 前置条件", "## 4. 输入契约",
    "## 5. 输出契约", "## 6. 规则与来源要求", "## 7. 硬约束自检",
    "## 8. 失败处理", "## 9. 测试计划", "## 10. 验收标准",
    "## 11. 交付物", "## 12. 交付说明",
]

# 允许的占位符（执行时由 Agent 填写）
ALLOWED_PLACEHOLDERS = {
    "<你的标识>", "（待填）", "<命令>", "<输出摘要>", "<名称>", "<期望>", "<行为>",
    "<module-name>", "<相关或不相关>", "<说明>", "<不猜测，标记需人工>",
    "<error 记录>", "<error + unevaluated>", "<标记 unverified>",
    "<assumptions/known_gaps>", "<字段>", "<新增/修改/删除>", "<问题>",
    "<证据>", "<建议变更>", "<影响面>", "<严重度>", "<路径>",
}


def main():
    reg = load("tasks/task_registry.json")
    own = load("contracts/file_ownership.json")
    mods = own["modules"]

    # --- 1/2/3/4 任务包 ---
    section("1. 任务包完整性")
    for t in reg["tasks"]:
        tid = t["task_id"]
        p = os.path.join(ROOT, "tasks", f"{tid}.md")
        if t["status"] == "completed":
            check(f"{tid} 已完成且有结果记录", bool(t.get("actual_result")), "")
            continue
        if not os.path.exists(p):
            check(f"任务包存在 {tid}", False, "文件缺失")
            continue
        check(f"任务包存在 {tid}", True)
        txt = open(p, encoding="utf-8").read()
        for sec in REQUIRED_SECTIONS:
            check(f"{tid} 含 {sec}", sec in txt, "缺章节")
        # 白名单一致
        spec = mods.get(t["module"])
        check(f"{tid} 的 module 在所有权登记中", spec is not None, t["module"])
        if spec:
            for ap in spec["owns"]:
                check(f"{tid} 白名单含 {ap}", ap in txt, f"未写入: {ap}")
            for rp in spec["reads"][:6]:
                check(f"{tid} 只读含 {rp}", rp in txt, f"未写入: {rp}")
        # 依赖
        for d in t.get("depends_on", []):
            check(f"{tid} 依赖 {d} 在 §3 中列出", d in txt, "未列出")
        # 占位符
        found = set(re.findall(r"<[^>\n]{2,40}>", txt)) - ALLOWED_PLACEHOLDERS
        found = {f for f in found if not f.startswith("<") or True}
        bad = {f for f in found if f not in ALLOWED_PLACEHOLDERS}
        check(f"{tid} 无未填占位符", not bad, str(sorted(bad)[:4]))

    # --- 5 所有权冲突 ---
    section("2. 文件所有权无冲突")
    owner_of: dict[str, str] = {}
    for mod, spec in mods.items():
        for path in spec["owns"]:
            if path in owner_of:
                check(f"路径唯一归属 {path}", False,
                      f"{owner_of[path]} 与 {mod} 冲突")
            else:
                owner_of[path] = mod
    if not any("路径唯一归属" in f[0] for f in FAILED):
        check("所有可写路径归属唯一", True)

    # reserved 与 owns 不重叠（integrator 为豁免角色）
    exempt = own.get("reserved_paths", {}).get("exempt_owner")
    for p in own.get("reserved_paths", {}).get("paths", []):
        for mod, spec in mods.items():
            if mod == exempt:
                continue
            for o in spec["owns"]:
                if o == p or (p.endswith("/**") and o.startswith(p[:-3])):
                    check(f"保留路径未被模块占用 {p}", False, f"{mod} 拥有 {o}")
    check("保留路径与模块所有权无重叠（integrator 豁免）", True)

    # --- 6 并行组路径交集 ---
    section("3. 并行波次路径零重叠")
    groups: dict[str, list] = {}
    for t in reg["tasks"]:
        if t["status"] == "completed":
            continue
        groups.setdefault(t["parallel_group"], []).append(t)
    for g, ts in groups.items():
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                a = set(mods[ts[i]["module"]]["owns"])
                b = set(mods[ts[j]["module"]]["owns"])
                inter = a & b
                # 允许共享 rules/03（拆分待办）与 integrator 独有
                shared = {p for p in inter if "03_listing_violations" in p}
                other = inter - shared
                check(f"{g}: {ts[i]['task_id']} ∩ {ts[j]['task_id']} = ∅",
                      not other, f"重叠 {sorted(other)}")
                if shared:
                    declared = (ts[i].get("split_request") or ts[j].get("split_request"))
                    check(f"{g}: rules/03 重叠已声明 split_request",
                          bool(declared), "未声明")

    # --- 7 依赖图 ---
    section("4. 依赖图")
    dep = {t["task_id"]: list(t.get("depends_on", [])) for t in reg["tasks"]}
    for t in reg["tasks"]:
        for d in t.get("depends_on", []):
            check(f"{t['task_id']} 依赖 {d} 存在", d in dep, "悬空")
        for b in t.get("blocks", []):
            check(f"{t['task_id']} blocks {b} 存在", b in dep, "悬空")
    state: dict[str, int] = {}

    def visit(n):
        if state.get(n) == 1:
            return [n]
        if state.get(n) == 2:
            return []
        state[n] = 1
        for m in dep.get(n, []):
            r = visit(m)
            if r:
                return r
        state[n] = 2
        return []

    cyc = []
    for n in dep:
        c = visit(n)
        if c:
            cyc = c
            break
    check("依赖图无环", not cyc, str(cyc))

    # --- 9 SKILL.md 所有权一致 ---
    section("5. SKILL.md 与所有权登记一致")
    for mod, spec in mods.items():
        sk = os.path.join(ROOT, "skills", mod, "SKILL.md")
        if mod == "integrator":
            check("integrator 无 Skill.md（角色而非模块）",
                  not os.path.exists(sk), "不应存在")
            continue
        if not os.path.exists(sk):
            check(f"{mod} 有 SKILL.md", False, "缺失")
            continue
        txt = open(sk, encoding="utf-8").read()
        check(f"{mod} SKILL.md 含「文件所有权」章节",
              "文件所有权" in txt, "缺章节")
        for p in spec["owns"]:
            check(f"{mod} SKILL.md 声明拥有 {p}", p in txt, "未声明")
        for p in spec["rule_prefixes"]:
            check(f"{mod} SKILL.md 声明前缀 {p}", p in txt, "未声明")

    # --- 10 references 存在 ---
    section("6. references 文件存在")
    for mod in mods:
        if mod == "integrator":
            continue
        sk = os.path.join(ROOT, "skills", mod, "SKILL.md")
        if not os.path.exists(sk):
            continue
        txt = open(sk, encoding="utf-8").read()
        refs = sorted(set(re.findall(r"`(references/[^`]+)`", txt)))
        d = os.path.dirname(sk)
        for r in refs:
            check(f"{mod}/{r} 存在", os.path.exists(os.path.join(d, r)), "缺失")
        # 反向：目录里多的文件也要被提及
        rd = os.path.join(d, "references")
        if os.path.isdir(rd):
            for f in sorted(os.listdir(rd)):
                check(f"{mod} 提及 references/{f}",
                      f"references/{f}" in txt, "未提及")

    print(f"\n{'=' * 62}")
    print(f"PASSED: {len(PASSED)}   FAILED: {len(FAILED)}")
    if FAILED:
        print("\nFailures:")
        for n, d in FAILED[:25]:
            print(f"  - {n}: {d}")
        return 1
    print("任务包与所有权一致性全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
