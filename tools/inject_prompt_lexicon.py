#!/usr/bin/env python3
"""把判定词表注入 docs/CHATGPT_PROMPT.md。

词表由 tools/gen_prompt_lexicon.py 从 lexicon/term_groups.json 生成，
本脚本只负责注入 —— 保证文档里的词表永远与词库一致。

用法：
    python tools/inject_prompt_lexicon.py          # 注入/更新
    python tools/inject_prompt_lexicon.py --check  # 只校验是否同步（CI 用）
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, "tools", "gen_prompt_lexicon.py")
DOC = os.path.join(ROOT, "docs", "CHATGPT_PROMPT.md")

BEGIN = "<!-- LEXICON_TABLES_BEGIN -->"
END = "<!-- LEXICON_TABLES_END -->"


def generate() -> str:
    r = subprocess.run([sys.executable, GEN], capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        raise SystemExit("生成词表失败")
    return r.stdout.strip("\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验是否同步")
    args = ap.parse_args()

    if not os.path.isfile(DOC):
        print("FAIL: %s 不存在" % DOC)
        return 1

    with open(DOC, encoding="utf-8") as fh:
        doc = fh.read()

    if BEGIN not in doc or END not in doc:
        print("FAIL: %s 缺少 %s / %s 标记" % (DOC, BEGIN, END))
        return 1

    tables = generate()
    head, rest = doc.split(BEGIN, 1)
    _old, tail = rest.split(END, 1)
    new_doc = "%s%s\n%s\n%s%s" % (head, BEGIN, tables, END, tail)

    if args.check:
        if new_doc != doc:
            print("FAIL: %s 的词表与词库不同步 —— 跑 python tools/inject_prompt_lexicon.py" % DOC)
            return 1
        print("OK: %s 词表与词库同步" % DOC)
        return 0

    if new_doc != doc:
        with open(DOC, "w", encoding="utf-8") as fh:
            fh.write(new_doc)
        print("已更新 %s（词表 %d 字符）" % (DOC, len(tables)))
    else:
        print("%s 已是最新" % DOC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
