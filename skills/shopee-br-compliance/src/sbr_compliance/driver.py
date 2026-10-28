"""显式工作流的执行层：**读模块说明 → 构造输入 → 驱动 CLI → 校验 → 交接**。

> **目标平台不保证 Skill 之间存在自动调用能力**（`PROJECT_RULES.md` §4.2）。
>
> 因此本模块**不假设**能「调用」另一个 Skill。它做的是：
>
> 1. **读取**目标模块的 `SKILL.md`（文本）—— `read_module_skill_md`
> 2. 依该文件声明的契约**构造**输入（`contracts/skill_input.schema.json`）
> 3. 依该文件声明的输出契约**驱动**该模块的命令行入口，取得 `AuditResult[]`
> 4. 依 `contracts/audit_result.schema.json` **校验**
> 5. 记录 `ModuleHandoff`（含 `assumptions` / `known_gaps`）

平台若将来提供自动调用能力，只需把第 3 步替换为真正的调用 ——
**第 1、2、4、5 步与契约、字段、判定语义一律不变**。

本层**不产生任何合规结论**：所有 verdict / action 都来自上游模块的产出。

纯标准库实现。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from .contracts import audit_result_validator
from .errors import STAGE_INVOKE, STAGE_LOAD, STAGE_VALIDATE, ErrorLog
from .registry import ModuleSpec

#: 子进程的环境：清掉 `LD_LIBRARY_PATH`
#: （本机 Hermes runtime 会遮蔽系统 OpenSSL，导致子进程 SSL 损坏）。
_ENV_STRIP = ("LD_LIBRARY_PATH",)


def _child_env() -> dict:
    env = dict(os.environ)
    for key in _ENV_STRIP:
        env.pop(key, None)
    return env


def read_module_skill_md(root: str, module_name: str) -> tuple[str | None, str | None]:
    """**显式读取**模块的说明文件。

    返回 `(text, error)`：
    * `text` 非 `None` → 读到了
    * `error` 非 `None` → 读不到（模块不可用）
    """
    path = os.path.join(root, "skills", module_name, "SKILL.md")
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read(), None
    except FileNotFoundError:
        return None, (f"module description file not found: {path} "
                      f"(the module is not installed; its review dimension "
                      f"cannot be executed and must not be read as compliant)")
    except OSError as exc:
        return None, (f"module description file is unreadable: {path} ({exc})")


def skill_md_digest(text: str) -> str:
    """模块说明文件的摘要 —— 记进 `provenance.source_refs`，便于追溯「按哪版说明执行」。"""
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def build_skill_input(request_id: str, spec: ModuleSpec, *, products=None,
                       cases=None, scope=None, rules=None,
                       provenance=None, target=None,
                       options=None) -> dict:
    """依 `contracts/skill_input.schema.json` 为某个模块构造输入。"""
    payload = {
        "request_id": request_id,
        "task_type": spec.task_type,
        "target": target or {"kind": "product_batch"},
        "products": list(products or []),
        "cases": list(cases or []),
        "rules": list(rules or []),
        "scope": dict(scope or {}),
        "options": dict(options or {}),
        "provenance": dict(provenance or {
            "inputs": [{"path": "<orchestrated>", "kind": "product_batch"}],
            "produced_at": "",
        }),
    }
    return payload


def _read_json(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _extract_results(payload) -> list[dict]:
    """从 JSON 文档里抽出 `AuditResult` 记录列表。

    支持三种形态：裸数组、单个对象、`{"results": [...]}` 包裹
    （与 `shopee-br-reporting` 的装载约定一致）。
    """
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("results", "audit_results", "audit_result"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
            if isinstance(value, dict):
                return [value]
        return [payload]
    return []


class ModuleRun:
    """一次模块执行的结果。"""

    def __init__(self, module_name: str) -> None:
        self.module_name = module_name
        #: 通过契约校验的结果
        self.results: list[dict] = []
        #: 被契约拒绝的结果（附原因）
        self.rejected: list[dict] = []
        #: 上游模块的 `ModuleHandoff`（如可得）
        self.handoff: dict | None = None
        #: 产出目录
        self.out_dir: str | None = None
        #: 产出文件路径 → 载荷（供后续模块消费）
        self.artifacts: dict[str, str] = {}
        #: 执行是否成功
        self.ok = False
        #: 未执行 / 失败的原因
        self.reason: str = ""
        #: 执行记录（用于 `provenance.notes`）
        self.trail: list[str] = []


def run_module(spec: ModuleSpec, root: str, *, request_id: str, out_dir: str,
               products=None, cases=None, scope=None, rules=None,
               provenance=None, input_paths=None, skill_input_path=None,
               result_files=None, options=None,
               log: ErrorLog | None = None) -> ModuleRun:
    """驱动一个模块，并按契约校验它的产出。

    参数
    ----
    spec:
        模块登记项（`registry.ModuleSpec`）。
    root:
        仓库根路径。
    out_dir:
        该模块的产出目录。
    skill_input_path:
        已写好的 `SkillInput` 文件路径（内容审核 / 重复检测用）。
    result_files:
        已有结果文件路径（汇总用）。
    input_paths:
        外部输入文件（ingestion 用）。

    返回
    ----
    `ModuleRun` —— 含 `results` / `rejected` / `ok` / `reason`。
    """
    log = log if log is not None else ErrorLog()
    run = ModuleRun(spec.name)
    run.out_dir = out_dir

    # --- 步骤 1：显式读取模块说明 --------------------------------
    text, read_error = read_module_skill_md(root, spec.name)
    if read_error:
        run.reason = read_error
        log.error(STAGE_INVOKE, read_error,
                  {"module": spec.name, "stage": "read_skill_md"})
        return run
    run.trail.append(
        f"read {spec.name}/SKILL.md ({skill_md_digest(text or '')})")

    cli_path = os.path.join(root, spec.cli_rel)
    if not os.path.exists(cli_path):
        run.reason = (f"the module entry point does not exist: {cli_path} "
                      f"(the module is not installed)")
        log.error(STAGE_INVOKE, run.reason,
                  {"module": spec.name, "cli": spec.cli_rel})
        return run

    os.makedirs(out_dir, exist_ok=True)

    # --- 步骤 2/3：构造输入并驱动 CLI ---------------------------
    #
    # 各模块的 CLI 参数约定**并不统一** —— 不能套用同一套 argv。
    # 实际接口（逐个核对过 `--help`）：
    #
    # | 模块 | 参数 |
    # |---|---|
    # | ingestion | `--request-id` `--out-dir` + 位置参数（输入文件） |
    # | listing-audit | `--skill-input`（必需）`--request-id` `--out-dir` |
    # | duplicate-detection | `--skill-input`（必需）`--out-dir`（**无** `--request-id`） |
    # | ip-review | `--request-id` `--out-dir` + **位置参数**（输入文件，**无** `--skill-input`） |
    # | reporting | `--request-id` `--out-dir` `--result-file` `--skill-input` |
    #
    # 套错参数会让模块直接退出（argparse 报 unrecognized arguments），
    # 该维度就**静默缺失** —— 汇总出来的结论会少一块，却看不出缺了。
    argv = [sys.executable, cli_path]
    if spec.role == "ingestion":
        argv += ["--request-id", request_id, "--out-dir", out_dir]
        argv += list(input_paths or [])
    elif spec.role == "reporting":
        argv += ["--request-id", request_id, "--out-dir", out_dir]
        for path in (result_files or []):
            argv += ["--result-file", path]
        if skill_input_path:
            argv += ["--skill-input", skill_input_path]
    else:
        # 内容审核 / 重复检测 / IP 筛查：读 SkillInput 文件
        payload_path = skill_input_path
        if not payload_path:
            payload = build_skill_input(
                request_id, spec, products=products, cases=cases,
                scope=scope, rules=rules, provenance=provenance,
                options=options,
            )
            payload_path = os.path.join(out_dir, "skill_input.json")
            with open(payload_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
        if spec.role == "ip":
            # ip-review 吃的是**含 products[] 的 JSON**，位置参数传入
            argv += ["--request-id", request_id, "--out-dir", out_dir]
            argv += [payload_path]
        elif spec.role == "duplicate":
            # duplicate-detection 只认 `--skill-input`，**没有** `--request-id`
            argv += ["--skill-input", payload_path, "--out-dir", out_dir]
        else:
            # listing-audit：两个都支持
            argv += ["--skill-input", payload_path,
                     "--request-id", request_id, "--out-dir", out_dir]

    try:
        proc = subprocess.run(argv, capture_output=True, text=True,
                              cwd=root, env=_child_env(), timeout=600)
    except (OSError, subprocess.SubprocessError) as exc:
        run.reason = f"the module could not be executed: {exc}"
        log.error(STAGE_INVOKE, run.reason,
                  {"module": spec.name, "argv": argv})
        return run

    run.trail.append(f"ran {os.path.basename(cli_path)} (exit {proc.returncode})")

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        tail = detail[-1] if detail else "no output"
        run.reason = (f"the module exited with status {proc.returncode}: {tail}")
        log.error(STAGE_INVOKE, run.reason,
                  {"module": spec.name, "exit_code": proc.returncode,
                   "stderr_tail": tail[:400]})
        return run

    # --- 步骤 4：读取产出并按契约校验 ---------------------------
    results_path = os.path.join(out_dir, "audit_results.json")
    single_path = os.path.join(out_dir, "audit_result.json")
    load_path = results_path if os.path.exists(results_path) else single_path
    if not os.path.exists(load_path):
        run.reason = (f"the module produced no readable AuditResult file in "
                      f"{out_dir}")
        log.error(STAGE_LOAD, run.reason,
                  {"module": spec.name, "out_dir": out_dir})
        return run

    try:
        payload = _read_json(load_path)
    except (OSError, ValueError) as exc:
        run.reason = f"the module output is not readable JSON: {exc}"
        log.error(STAGE_LOAD, run.reason, {"module": spec.name,
                                           "path": load_path})
        return run

    candidates = _extract_results(payload)
    if not candidates:
        run.reason = ("the module output contains no AuditResult object; an "
                      "empty result set is not evidence of compliance")
        log.error(STAGE_LOAD, run.reason,
                  {"module": spec.name, "path": load_path})
        return run

    validator = audit_result_validator(root)
    for index, record in enumerate(candidates):
        problems = validator.validate(record)
        if problems:
            run.rejected.append({
                "module": spec.name,
                "index": index,
                "result_id": record.get("result_id"),
                "target_ref": record.get("target_ref"),
                "problems": problems[:6],
            })
            log.error(STAGE_VALIDATE,
                      (f"a result from {spec.name} (index {index}) does not "
                       f"satisfy contracts/audit_result.schema.json and was "
                       f"excluded: " + "; ".join(problems[:3])),
                      {"module": spec.name, "index": index,
                       "result_id": record.get("result_id"),
                       "problems": problems[:6]})
            continue
        run.results.append(record)

    if not run.results:
        run.reason = (f"every result produced by {spec.name} was rejected by "
                      f"contracts/audit_result.schema.json")
        log.error(STAGE_VALIDATE, run.reason,
                  {"module": spec.name, "rejected": len(run.rejected)})
        return run

    # --- 交接记录 ------------------------------------------------
    handoff_path = os.path.join(out_dir, "module_handoff.json")
    if os.path.exists(handoff_path):
        try:
            run.handoff = _read_json(handoff_path)
        except (OSError, ValueError):
            run.handoff = None

    for name in ("skill_input.json", "products.json", "audit_results.json",
                 "audit_result.json", "module_handoff.json", "signals.json",
                 "audit_summary.json", "audit_report.md"):
        path = os.path.join(out_dir, name)
        if os.path.exists(path):
            run.artifacts[name] = path

    run.ok = True
    return run
