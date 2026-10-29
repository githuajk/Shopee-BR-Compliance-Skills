#!/usr/bin/env python3
"""组装 docs/CHATGPT_PROMPT.md —— ChatGPT 入口与能力分流。

文档结构（固定顺序）：

    §A 能力探测与分流      ← 入口：先探测能力，再选路径
    §B 判定规则            ← 从 parts/rules_body.md 注入
    §C 判定词表            ← 从 lexicon 自动生成（标记区）
    §D 补充文件指针
    §E 判定依据来源
    §F 输出格式
    §G 五句话总结

词表由 tools/gen_prompt_lexicon.py 生成，注入 §C 的标记区。
判定规则正文（§B）单独放在 parts/rules_body.md —— 那里是人工维护的。

用法：
    python tools/build_prompt_doc.py          # 生成
    python tools/build_prompt_doc.py --check  # 校验是否同步（CI 用）
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, "tools", "gen_prompt_lexicon.py")
BODY = os.path.join(ROOT, "docs", "parts", "rules_body.md")
OUT = os.path.join(ROOT, "docs", "CHATGPT_PROMPT.md")

BEGIN = "<!-- LEXICON_TABLES_BEGIN -->"
END = "<!-- LEXICON_TABLES_END -->"


def head() -> str:
    return """# Shopee BR 合规审核 —— 入口与能力分流

> **这份文档是入口。** 读完它，你就知道该用什么方式审、按什么规则审、输出成什么样。
>
> **用法**：在 ChatGPT 里说「读取 https://raw.githubusercontent.com/githuajk/Shopee-BR-Compliance-Skills/main/docs/CHATGPT_PROMPT.md 然后按它审核下面这些商品」，然后把商品标题和详情贴进去。
>
> 文档 ID：`SBRCA-DOC-PROMPT-001`　版本：2.0.0　更新：2026-10-29

---

## §A. 能力探测与分流（先做这一步）

**先探测你能做什么，再决定怎么做。** 不要一上来就假设环境能力。

### A.1 探测方法

按顺序试，**能做几步就做几步**，不要跳过：

| # | 探测动作 | 成功说明 |
|---|---|---|
| 1 | 读一个 `raw.githubusercontent.com` 的 URL | 你能读远端文本 |
| 2 | 读**第二个** URL | 你能读多文件 |
| 3 | 执行 Python 代码 | 你能跑脚本 |
| 4 | 执行 `git clone` 或下载 zip | 你能取到完整仓库 |
| 5 | 执行 shell 命令（`ls`/`unzip`） | 你有完整 shell |

### A.2 分流表（按你探测到的最高能力选）

| 你的能力 | 走哪一级 | 做什么 | 准确度 |
|---|---|---|---|
| **T4 完整 shell + 能联网** | **§A.3 T4** | 跑真实规则引擎（21 万词 + 57 条规则 + 契约校验） | **最高** |
| **T3 能跑 Python，取不到仓库** | **§A.3 T3** | 用 §C 词表自己写扫描器 | 高 |
| **T2 能读多个文件** | **§A.3 T2** | 读本文档 + 按需读 §D 的补充文件 | 高 |
| **T1 只能读这一个文件** | **§A.3 T1** | 只用本文档，纯自然语言判定 | 中高 |

> **选最高可用的一级。** 不要够得着 T4 却用 T1。

### A.3 各级的执行方式

#### T4 —— 能跑完整引擎

```bash
git clone --depth 1 https://github.com/githuajk/Shopee-BR-Compliance-Skills.git
cd Shopee-BR-Compliance-Skills
python sbrca_run.py --input <商品文件> --out-dir ./out
```

读引擎输出的 `audit_report.md` 与 `audit_summary.json`（在输出目录下），按 §F 汇报。
**不要自己重新判定** —— 引擎结论就是结论，你只负责解读。

#### T3 —— 能跑 Python，取不到仓库

用 §C 的词表在代码解释器里写一个扫描器。**注意葡语词边界不可靠**，用显式 lookaround：

```python
import re

TERMS = {
    # 把 §C 各组的词填进来（文档里已是可直接复制的纯文本）
    "proibido_armas":    ["arma de fogo", "pistola", "munição", ...],
    "proibido_garantia": ["garantia", "garantido", "100%", "original", ...],
    "claim_beleza":      ["anti-idade", "antirrugas", "lifting", ...],
}

def scan(text):
    hits = []
    for group, terms in TERMS.items():
        for t in terms:
            pat = r'(?<![a-zA-Zà-ÿÀ-ß])' + re.escape(t) + r'(?![a-zA-Zà-ÿÀ-ß])'
            if re.search(pat, text, re.IGNORECASE):
                hits.append((group, t))
    return hits
```

**命中后仍然要人工判断** —— 按 §B.3 查豁免。**脚本只缩小范围，判定仍然由你做。**

#### T2 —— 能读多个文件

1. 读本文档（规则 + 词表）
2. **按需**追加读 §D 列出的文件：

| 需要什么 | 读这个 |
|---|---|
| 完整改写标准 + 品类专属改写 | `docs/合规审核SOP.md` |
| 更细的判定表 + 误报控制 | `docs/MANUAL_REVIEW.md` |
| 平台政策原文 + 处罚码对照 | `docs/SOP_COMPLIANCE_REVIEW.md` |
| 工具命令 + xlsx 铁律 | `docs/USER_SOP.md` |

**不要一次全读** —— 按需读，省上下文。

#### T1 —— 只能读这一个文件

只用本文档：§B 规则 + §C 词表。纯自然语言判定，**严格按 §F 输出**。

### A.4 无论哪一级都必须守的三条

1. **命中 ≠ 违规** —— 每次命中都要过 §B.3 豁免清单。
2. **缺信息 ≠ 通过** —— 看不到图片/属性就标「未评估」，**绝不能标「通过」**。
3. **不下架** —— 你只给建议，处置权在店主。

### A.5 向用户声明你在哪一级

报告开头必须写清：

```
本次审核方式：<T4 规则引擎 / T3 脚本扫描+人工判定 / T2 多文件读取 / T1 单文件判定>
判定依据：<规则引擎 57 条规则 + 210,490 词库 | 词表 1,439 触线词 + 豁免清单>
未覆盖：<看不到的部分，如图片、属性字段、历史案件>
```

**不要让用户以为你用了引擎但其实没有。**

---

## §B. 判定规则

"""


def tail() -> str:
    return """
---

## §D. 补充文件指针

**按需读，不要全读。**

| 需要 | 文件（相对仓库根 `githuajk/Shopee-BR-Compliance-Skills`） |
|---|---|
| 完整改写标准 + 品类专属改写 + 可填写字段模板 | `docs/合规审核SOP.md` |
| 判定表更细版本 + 误报控制 | `docs/MANUAL_REVIEW.md` |
| 平台政策原文 + 处罚码对照 | `docs/SOP_COMPLIANCE_REVIEW.md` |
| 工具命令 + xlsx 铁律 + 运行环境 | `docs/USER_SOP.md` |
| 报告六节结构 + 硬约束清单 | `skills/shopee-br-reporting/references/report_structure.md` |
| 证据引用规范 | `skills/shopee-br-reporting/references/evidence_citation.md` |
| 误报控制（葡语词边界坑） | `skills/shopee-br-listing-audit/references/false_positive_control.md` |
| IP 指示性使用（Art. 132 II） | `skills/shopee-br-ip-review/references/nominative_use.md` |
| 授权核验清单 | `skills/shopee-br-ip-review/references/authorization_checklist.md` |
| 重复刊登与重发冻结 | `skills/shopee-br-duplicate-detection/references/relist_axes.md` |
| 处罚点机制 | `skills/shopee-br-duplicate-detection/references/penalty_mechanics.md` |
| 输入格式矩阵 | `skills/shopee-br-data-ingestion/references/format_matrix.md` |

---

## §E. 判定依据来源

所有标准来自仓库的机器可读资产：

| 来源 | 内容 |
|---|---|
| `rules/*.json` | 57 条规则（禁售 / 受限 / IP / 刊登 / 重复 / 案件 / 药品） |
| `lexicon/term_groups.json` | 210,490 词，其中 **1,439 个是判定词**（其余 209,051 是 ANVISA 注册名录，非违规信号） |
| `lexicon/exemptions.json` | 51 条误报豁免 |
| `lexicon/non_avoidable.json` | 6 类无法靠文字规避的品类 |
| `lexicon/rewrite_map.json` | 触线 → 中性替换 |
| `research/violation_codes.json` | 106 个平台处罚码 |

---

## §F. 输出格式

**严格按这个格式。**

每个商品一段：

```
商品 N
  标题：<原标题>
  类目：<化妆品/汽配/...>
  结论：<致命/高危/中低/通过>
  动作：<不下架/改写/查授权/出工单/建议优化>

  命中与判定：
    - 「<命中词>」→ <触线组> → <为什么不算/算>
    - ...

  未评估（未检查到的部分）：
    - <如：图片未提供，无法判断是否有第三方 logo>

  改写建议（如动作是改写）：
    新标题：<葡语新标题，60-95 字符，不带分隔逗号>
    新详情：<按六段结构>
    改动理由：<每处改动的理由>
```

**批量完成后给汇总表：**

```
| 商品 | 结论 | 动作 | 命中词 | 严重度 |
|---|---|---|---|---|
```

---

## §G. 记住这五句话

1. **命中 ≠ 违规**，先查豁免。
2. **缺信息 ≠ 通过**，标「未评估」。
3. **先定类目，再判词。**
4. **不下架**，只给建议 —— 处置权在店主。
5. **改完必须重读**：检查有没有漏删、有没有引入新触线词、有没有误删豁免词。
"""


def generate_tables() -> str:
    r = subprocess.run([sys.executable, GEN], capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        raise SystemExit("生成词表失败")
    return r.stdout.strip("\n")


def build() -> str:
    if not os.path.isfile(BODY):
        raise SystemExit("缺少 %s" % BODY)
    with open(BODY, encoding="utf-8") as fh:
        body = fh.read().strip("\n")
    tables = generate_tables()
    return "%s\n%s\n\n## §C. 判定词表\n\n**这是触线词表。** 命中后回到 §B.3 查豁免，再按 §B.2 定严重度。\n\n%s\n%s\n%s\n%s" % (
        head(), body, BEGIN, tables, END, tail(),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验是否同步")
    args = ap.parse_args()

    new_doc = build()
    if args.check:
        cur = ""
        if os.path.isfile(OUT):
            with open(OUT, encoding="utf-8") as fh:
                cur = fh.read()
        if cur != new_doc:
            print("FAIL: %s 与生成结果不同步 —— 跑 python tools/build_prompt_doc.py" % OUT)
            return 1
        print("OK: %s 与 parts/rules_body.md + 词库同步" % OUT)
        return 0

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(new_doc)
    print("已生成 %s（%d 字节）" % (OUT, len(new_doc)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
