#!/usr/bin/env python3
"""SBRCA 单文件入口 —— 给 ChatGPT / 任何 LLM 沙箱用。

只依赖 Python 标准库。克隆仓库后跑这一个文件就能跑完整审核，
不需要 pip install，不需要设 PYTHONPATH。

用法（ChatGPT 代码解释器）：

    # 1) 用户上传商品文件（.xlsx 或 .json）到 /mnt/data
    # 2) 模型执行：
    python sbrca_run.py --input /mnt/data/mass_update.xlsx --out-dir /mnt/data/out

    # 或直接读 GitHub 仓库：
    python sbrca_run.py --repo https://github.com/githuajk/Shopee-BR-Compliance-Skills \
        --input /mnt/data/products.json --out-dir /mnt/data/out

两种输入形态：

| 形态 | 参数 | 说明 |
|---|---|---|
| 文件 | `--input FILE...` | 先经 ingestion 规范化，再驱动其余模块 |
| 已规范化 | `--skill-input FILE` | 跳过 ingestion，直接驱动专业模块 |

产出（写入 --out-dir）：

| 文件 | 内容 |
|---|---|
| `audit_report.md` | 人读 Markdown 报告（六节固定结构）★ 给 LLM 读这个 |
| `audit_summary.json` | 结构化汇总 |
| `audit_results.json` | AuditResult[]（逐商品 + 整批） |
| `module_handoff.json` | 模块交接记录 |
| `routing_plan.json` | 分流决定 |

**只读输入** —— 本脚本从不写回被读取的文件，也不执行任何线上处置。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import zipfile

REPO_URL = "https://github.com/githuajk/Shopee-BR-Compliance-Skills.git"

# 主 CLI 的相对路径（契约冻结，不要随意改）
COMPLIANCE_CLI = "skills/shopee-br-compliance/src/sbr_compliance_cli.py"


def die(msg: str, code: int = 1) -> None:
    print("ERROR: %s" % msg, file=sys.stderr)
    raise SystemExit(code)


def find_repo(start: str = ".") -> str | None:
    """从当前目录向上找包含主 CLI 的仓库根。"""
    cur = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(cur, COMPLIANCE_CLI)):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def _zip_url_for(repo_url: str) -> str:
    """由仓库地址推出 zip 下载地址。

    git 仓库地址不能直接拼 archive 路径：
        https://host/o/r.git  ->  https://host/o/r/archive/refs/heads/main.zip
    """
    url = repo_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return "%s/archive/refs/heads/main.zip" % url


def clone_repo(url: str, dest: str) -> str:
    """克隆仓库。git 不可用时回退到 zip 下载。"""
    if os.path.isdir(os.path.join(dest, COMPLIANCE_CLI)):
        return os.path.abspath(dest)
    if shutil_which("git"):
        print("[sbrca] git clone %s -> %s" % (url, dest), flush=True)
        r = subprocess.run(
            ["git", "clone", "--depth", "1", url, dest],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            return os.path.abspath(dest)
        print("[sbrca] git clone 失败：%s" % (r.stderr.strip()[:200]), flush=True)
    # 回退：zip
    zip_url = _zip_url_for(url)
    print("[sbrca] 回退到 zip 下载：%s" % zip_url, flush=True)
    import urllib.request
    try:
        with urllib.request.urlopen(zip_url, timeout=180) as resp:
            data = resp.read()
    except Exception as exc:  # noqa: BLE001
        die("zip 下载失败：%s（URL: %s）" % (exc, zip_url))
        raise  # die() 会抛 SystemExit；此处仅为类型检查器
    parent = os.path.dirname(os.path.abspath(dest))
    tmp_zip = os.path.join(parent, "sbrca.zip")
    with open(tmp_zip, "wb") as fh:
        fh.write(data)
    with zipfile.ZipFile(tmp_zip) as zf:
        zf.extractall(parent)
    for entry in os.listdir(parent):
        cand = os.path.join(parent, entry)
        if os.path.isfile(os.path.join(cand, COMPLIANCE_CLI)):
            return cand
    die("下载后未找到 %s" % COMPLIANCE_CLI)


def shutil_which(cmd: str) -> str | None:
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = os.path.join(d, cmd)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Shopee BR 合规审核 —— 单文件入口（纯标准库）",
    )
    ap.add_argument("--input", action="append", dest="inputs", metavar="FILE",
                    help="外部文件（.xlsx/.json），走完整 ingestion 链路；可重复")
    ap.add_argument("--skill-input", metavar="FILE",
                    help="已规范化的 SkillInput JSON（跳过 ingestion）")
    ap.add_argument("--product-file", metavar="FILE",
                    help="含 products[] 的 JSON 批次")
    ap.add_argument("--case-file", metavar="FILE",
                    help="含 cases[] 的 JSON 历史案件")
    ap.add_argument("--result-file", action="append", dest="result_files",
                    metavar="FILE", help="既有 AuditResult[]（只整合不重跑）；可重复")
    ap.add_argument("--repo", metavar="URL",
                    help="仓库地址或本地路径（默认自动探测当前目录）")
    ap.add_argument("--request-id", default="REQ-SBRCA-001",
                    help="请求标识（>= 4 字符）")
    ap.add_argument("--out-dir", default="./sbrca-out",
                    help="产出目录（默认 ./sbrca-out）")
    ap.add_argument("--modules", metavar="LIST",
                    help="逗号分隔的模块名；缺省按路由表自动决定")
    ap.add_argument("--quiet", action="store_true", help="不打印摘要")
    args = ap.parse_args()

    if not (args.inputs or args.skill_input or args.product_file or args.result_files):
        die("至少要指定 --input / --skill-input / --product-file / --result-file 之一")

    # 先校验输入文件存在（避免为无效输入白白克隆仓库）
    for group in (args.inputs or [], [args.skill_input, args.product_file,
                                      args.case_file] + (args.result_files or [])):
        for f in group:
            if f and not os.path.isfile(f):
                die("输入文件不存在：%s" % f)

    # 定位仓库
    if args.repo and os.path.isdir(args.repo):
        root = os.path.abspath(args.repo)
    elif args.repo and ("http://" in args.repo or "https://" in args.repo or "git@" in args.repo):
        root = clone_repo(args.repo, os.path.join(
            os.path.dirname(os.path.abspath(args.out_dir)), "sbrca-repo"))
    else:
        root = find_repo() or clone_repo(
            REPO_URL,
            os.path.join(os.path.dirname(os.path.abspath(args.out_dir)), "sbrca-repo"),
        )

    cli = os.path.join(root, COMPLIANCE_CLI)
    if not os.path.isfile(cli):
        die("仓库结构异常：找不到 %s" % COMPLIANCE_CLI)
    print("[sbrca] 仓库根：%s" % root, flush=True)

    # 组装主 CLI 参数
    cmd = [sys.executable, cli,
           "--request-id", args.request_id,
           "--out-dir", os.path.abspath(args.out_dir),
           "--root", root]
    for f in (args.inputs or []):
        cmd += ["--input", f]
    if args.skill_input:
        cmd += ["--skill-input", args.skill_input]
    if args.product_file:
        cmd += ["--product-file", args.product_file]
    if args.case_file:
        cmd += ["--case-file", args.case_file]
    for f in (args.result_files or []):
        cmd += ["--result-file", f]
    if args.modules:
        cmd += ["--modules", args.modules]
    if args.quiet:
        cmd.append("--quiet")

    # Hermes 运行时会污染 LD_LIBRARY_PATH，导致 ssl 导入失败 —— 先清掉
    env = dict(os.environ)
    env.pop("LD_LIBRARY_PATH", None)

    print("[sbrca] 执行：%s" % " ".join(cmd[1:]), flush=True)
    r = subprocess.run(cmd, env=env)
    if r.returncode != 0:
        die("审核失败，退出码 %d" % r.returncode, r.returncode)

    # 打印给 LLM 读的报告摘要
    report = os.path.join(os.path.abspath(args.out_dir), "audit_report.md")
    if os.path.isfile(report):
        print("\n[sbrca] ===== audit_report.md（前 80 行）===== ")
        with open(report, encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i >= 80:
                    print("... (截断)")
                    break
                print(line.rstrip())
        print("[sbrca] ===== 完整报告：%s =====" % report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
