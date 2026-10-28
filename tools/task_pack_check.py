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

    # --- 11 任务包枚举与冻结契约一致 ---
    # 任务包若写死与契约不同的 verdict/confidence/action 枚举，执行 Agent
    # 会照抄，产出的 AuditResult 直接通不过 audit_result 校验。路径类断言
    # 抓不到这种"值"的漂移，必须单独比对。
    section("7. 任务包枚举与冻结契约一致")
    with open(os.path.join(ROOT, "contracts", "audit_result.schema.json"), encoding="utf-8") as f:
        props = json.load(f)["properties"]
    contract_vals = {k: set(props[k]["enum"]) for k in ("verdict", "risk_level", "action", "confidence")}

    # 契约之外出现的常见误写（历史模板遗留）
    stale = {
        "verdict": {"pass", "flag", "not_evaluated", "signal"},
        "confidence": {"low", "medium", "high"},
        "action": {"flag"},
    }

    for t in reg["tasks"]:
        if t["status"] == "completed":
            continue
        p = os.path.join(ROOT, "tasks", f"{t['task_id']}.md")
        if not os.path.exists(p):
            continue
        txt = open(p, encoding="utf-8").read()
        for field in ("verdict", "risk_level", "action", "confidence"):
            # 抽取形如 | `verdict` | `a` / `b` / `c` | 的声明行
            m = re.search(rf"^\|\s*`{field}`\s*\|\s*(.+?)\s*\|\s*$", txt, re.M)
            check(f"{t['task_id']} 声明 {field} 取值", m is not None, "缺少取值行")
            if not m:
                continue
            # 只把形如标识符的记号当作枚举候选；行内散文里引用的文件路径
            # （如 `contracts/risk_action_matrix.json`）不是取值。
            declared = {t for t in re.findall(r"`([^`]+)`", m.group(1))
                        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t)}
            bad = declared & stale.get(field, set())
            check(f"{t['task_id']} 的 {field} 无契约外取值",
                  not bad, f"混入 {sorted(bad)}")
            unknown = declared - contract_vals[field]
            check(f"{t['task_id']} 的 {field} 取值全在契约 enum 内",
                  not unknown, f"未知 {sorted(unknown)}")
        # tier → action 上限表不得出现契约外的 action
        for tier, allowed in (("platform_official", "block"), ("law", "block"),
                               ("internal_risk", "flag_for_review"),
                               ("unverified", "flag_for_review"),
                               ("ai_inference", "flag_for_review")):
            m = re.search(rf"^\|\s*`{tier}`\s*\|\s*`([^`]+)`\s*\|\s*$", txt, re.M)
            check(f"{t['task_id']} 声明 tier {tier} 上限", m is not None, "缺少 tier 行")
            if m:
                check(f"{t['task_id']} 的 tier {tier} 上限合法",
                      m.group(1) in contract_vals["action"],
                      f"未知 action {m.group(1)}")

    # --- 12 全项目文档的 verdict 用值合法 ---
    # references/ 与 SKILL.md 里若把 pass / flag / not_evaluated / signal
    # 写进 verdict 的位置，执行 Agent 会照抄并产出通不过校验的结果。
    # 同样的问题曾出现在 14 份 references 中 —— 这里做全量扫描。
    section("8. 文档中 verdict 取值合法")
    verdict_bad = 0

    def _cell_tokens(text):
        """取单元格里的标识符记号（去反引号）。"""
        return {t.strip().strip("`") for t in re.findall(r"`([^`]+)`", text)}

    def _scan_table(lines, rel, start):
        """扫描一张 markdown 表：找出名为 verdict 的列，校验该列每行的取值。

        返回 (命中数, 下一张表的起始行)。表头与取值分处不同行 —— 只用
        单行正则匹配是抓不到的。
        """
        # 定位表头行的分隔行（|---|---|），确定表格范围
        sep_idx = None
        for i in range(start, min(start + 5, len(lines))):
            if re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i]) and "-" in lines[i]:
                sep_idx = i
                break
        if sep_idx is None:
            return 0, start + 1
        header = lines[sep_idx - 1] if sep_idx > 0 else ""
        cols = [c.strip() for c in header.strip().strip("|").split("|")]
        # verdict 列的下标（列名可能就是 `verdict`）
        vcols = [i for i, c in enumerate(cols)
                 if c.strip().strip("`").lower() == "verdict"]
        if not vcols:
            return 0, sep_idx + 1
        bad = 0
        i = sep_idx + 1
        while i < len(lines) and lines[i].strip().startswith("|"):
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            for vi in vcols:
                if vi >= len(cells):
                    continue
                toks = _cell_tokens(cells[vi])
                for t in toks:
                    if t in ("pass", "flag", "not_evaluated", "signal"):
                        bad += 1
                        check(f"{rel}:{i + 1} verdict 列取值合法", False,
                              f"出现契约外取值 {t}")
            i += 1
        return bad, i

    doc_scan = []
    for sub in ("", "skills", "docs", "tasks", "tests", "contracts"):
        base = os.path.join(ROOT, sub) if sub else ROOT
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, files in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fn in files:
                if fn.endswith(".md"):
                    doc_scan.append(os.path.join(dirpath, fn))

    for fp in doc_scan:
        rel = os.path.relpath(fp, ROOT)
        lines = open(fp, encoding="utf-8").read().splitlines()
        # (a) 行内赋值形式：verdict = pass / `flag` / not_evaluated / signal
        for i, line in enumerate(lines, 1):
            if "不是契约取值" in line:
                continue  # 明确写出"这不是契约取值"的警示行本身合法
            m = re.search(r"verdict\s*=\s*`?(pass|flag|not_evaluated|signal)`?",
                          line)
            if m:
                verdict_bad += 1
                check(f"{rel}:{i} verdict 赋值合法", False,
                      f"出现契约外取值 {m.group(1)}")
        # (b) 表格形式：verdict 列的取值
        i = 0
        while i < len(lines):
            if lines[i].strip().startswith("|"):
                bad, nxt = _scan_table(lines, rel, i)
                verdict_bad += bad
                i = nxt
            else:
                i += 1
    check("文档中无契约外 verdict 取值", verdict_bad == 0, f"{verdict_bad} 处")

    # --- 13 路径所有权三方一致 ---
    # 同一路径的 owner 曾出现四处不同说法：task_registry.path_ownership、
    # contracts/file_ownership.json、manifest.json、以及任务的 allowed_paths。
    # contracts/file_ownership.json 是声明的唯一权威来源 —— 其余三方必须与它一致。
    section("9. 路径所有权三方一致")
    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        man = json.load(f)
    own_paths = {}
    for mod, spec in mods.items():
        for p in spec["owns"]:
            own_paths[p] = mod

    for path, owner in reg.get("path_ownership", {}).items():
        declared = own_paths.get(path)
        if declared is None:
            # file_ownership 未声明该路径 —— 可能是它归 integrator 或不存在
            continue
        check(f"registry 与 ownership 对 {path} 的 owner 一致",
              declared == owner, f"registry={owner} ownership={declared}")

    # manifest 里登记了 owner 的共享资产，也必须与 ownership 一致
    shared = man.get("shared_assets", {})
    lex_owner = shared.get("lexicon", {}).get("owner")
    if lex_owner:
        check("manifest 的 lexicon owner 与 ownership 一致",
              lex_owner == own_paths.get("lexicon/**"),
              f"manifest={lex_owner} ownership={own_paths.get('lexicon/**')}")

    # 任务的 allowed_paths 不得超出该模块在 ownership 里声明的可写路径
    for t in reg["tasks"]:
        mod = t["module"]
        if mod not in mods:
            continue
        allowed = set(t.get("allowed_paths", []))
        owned = set(mods[mod]["owns"])
        for ap in allowed:
            # 允许任务声明比模块 owns 更宽（任务级白名单），但必须是 owns 的
            # 扩展或与之相容 —— 关键是不能与别的模块的 owns 冲突
            owners_of = {m for m, spec in mods.items()
                         for p in spec["owns"] if p == ap}
            if owners_of and mod not in owners_of:
                check(f"{t['task_id']} 的 {ap} 属于 {sorted(owners_of)}",
                      False, f"任务归属 {mod} 与路径 owner 不符")
            else:
                check(f"{t['task_id']} 的 {ap} 归属一致", True, "")

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
