#!/usr/bin/env python3
"""向各 SKILL.md 注入「文件所有权」章节。

章节内容由 contracts/file_ownership.json 驱动 —— 单一权威来源。
插入位置：最后一个「## N. 依赖」章节之后，「## N. 待填内容」之前。
若已存在「## N. 文件所有权」则替换之。

Usage: python3 tools/inject_ownership.py
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
OWN = os.path.join(ROOT, "contracts", "file_ownership.json")


def section(name: str, spec: dict) -> str:
    owns = spec["owns"]
    reads = spec["reads"]
    prefixes = spec["rule_prefixes"]
    lines = [
        f"## X. 文件所有权",
        "",
        f"本模块的路径所有权由 `contracts/file_ownership.json` 定义（`ownership_version` "
        f"{json.load(open(OWN, encoding='utf-8'))['ownership_version']}）。",
        "",
        "**可写路径（白名单）—— 越界即任务失败：**",
        "",
        "```",
    ]
    lines += owns
    lines += [
        "```",
        "",
        "**只读路径：**",
        "",
        "```",
    ]
    lines += reads
    lines += [
        "```",
        "",
    ]
    if prefixes:
        lines += [
            f"**本模块拥有的规则前缀：** `{', '.join(prefixes)}`",
            "",
        ]
    else:
        lines += [
            "**本模块拥有的规则前缀：** 无（本模块不定义审核规则）",
            "",
        ]
    if spec.get("notes"):
        lines += [f"> {spec['notes']}", ""]
    lines += [
        "公共契约（`contracts/**`、`PROJECT_RULES.md`、`AGENT_COLLABORATION.md`、"
        "`manifest.json`、`tasks/**`、`tests/test_plan.md`、`tests/fixtures/**`、"
        "`docs/**`、`tools/**`、`scripts/**`、`.archive/**`）对所有模块 Agent **只读**。",
        "需要修改时提交契约变更建议，不要自行改动。",
        "",
    ]
    return "\n".join(lines)


def renumber(text: str) -> str:
    """把 '## X. 文件所有权' 的 X 替换为正确序号，并保持后续章节号连续。"""
    m = re.search(r"^## X\. 文件所有权$", text, re.M)
    if not m:
        return text
    # 找到该章节之后所有 '## N.' 标题，取最小的 N 作为本章节号
    after = text[m.end():]
    nums = [int(x) for x in re.findall(r"^## (\d+)\.", after, re.M)]
    n = min(nums) if nums else 99
    text = text[:m.start()] + f"## {n}. 文件所有权" + text[m.end():]
    # 重新编号后续章节
    out = []
    idx = n
    seen = False
    for line in text.splitlines():
        mm = re.match(r"^## (\d+)\.(.*)$", line)
        if mm and not seen and int(mm.group(1)) >= n:
            seen = True
            out.append(f"## {idx}.{mm.group(2)}")
            idx += 1
        elif mm and seen:
            out.append(f"## {idx}.{mm.group(2)}")
            idx += 1
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def main():
    own = json.load(open(OWN, encoding="utf-8"))
    mods = own["modules"]
    changed = []
    for name, spec in sorted(mods.items()):
        p = os.path.join(SKILLS, name, "SKILL.md")
        if not os.path.exists(p):
            print(f"  SKIP {name}（无 SKILL.md）")
            continue
        text = open(p, encoding="utf-8").read()
        # 去掉已有的所有权章节
        text = re.sub(r"\n## \d+\. 文件所有权\n.*?(?=\n## \d+\.|\Z)", "\n", text,
                      flags=re.S)
        # 找插入点：最后一个 '## N. 依赖' 之后
        deps = list(re.finditer(r"^## (\d+)\. 依赖$", text, re.M))
        if not deps:
            print(f"  SKIP {name}（无「依赖」章节）")
            continue
        at = deps[-1].end()
        # 找到「依赖」章节结束（下一个 ## 标题）
        nxt = re.search(r"^## \d+\.", text[at:], re.M)
        at = at + (nxt.start() if nxt else len(text) - at)
        new = text[:at].rstrip() + "\n\n" + section(name, spec) + "\n" + text[at:]
        new = renumber(new)
        open(p, "w", encoding="utf-8").write(new)
        changed.append(name)
        print(f"  ✓ {name}")
    print(f"\n已注入 {len(changed)} 个模块的文件所有权章节。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
