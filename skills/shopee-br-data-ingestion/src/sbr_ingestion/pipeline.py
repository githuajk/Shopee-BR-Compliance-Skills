"""读取管线：外部文件 → `SkillInput` + `AuditResult[]` + `ModuleHandoff`。

三份产出全部符合冻结契约：

* `contracts/skill_input.schema.json`
* `contracts/audit_result.schema.json`
* `contracts/module_handoff.schema.json`

**本模块不做合规判定。** 产出的 `AuditResult` 只描述「读取与标准化」
这一件事本身：

* `verdict` 恒为 `PASS`（读取成功且无失败记录）或 `REVIEW`（有失败记录）
* `action` 恒为 `allow` 或 `flag_for_review` —— **绝不** `block` /
  `freeze_relist` / `escalate_legal`（硬约束 H2）
* `rule_refs` 恒为空 —— 本模块不定义规则前缀
* `confidence` 恒为 `confirmed`（读取成功的事实是确定的）或 `likely`
"""

from __future__ import annotations

import os

from .builder import build_products
from .errors import (
    SEVERITY_ERROR,
    SEVERITY_FATAL,
    SEVERITY_WARNING,
    STAGE_FIELD_MAPPING,
    STAGE_NORMALIZE,
    STAGE_PARSE,
    STAGE_PROVENANCE,
    ErrorLog,
)
from .parsers import ParseError, UnsupportedFormat, detect_kind, parse_file
from .parsers.base import sha256_file, utc_now_iso

MODULE_NAME = "shopee-br-data-ingestion"
CONTRACT_VERSION = "1.0.0"
RULE_VERSION = "sbr-ingestion-rules/1.0.0"


def _risk_action_matrix_path() -> str:
    """`contracts/risk_action_matrix.json` 的路径（仓库根相对）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    # .../skills/shopee-br-data-ingestion/src/sbr_ingestion/pipeline.py
    root = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    return os.path.join(root, "contracts", "risk_action_matrix.json")


def _load_matrix() -> dict:
    """载入 `contracts/risk_action_matrix.json`；读不到则回落到内置的
    保守映射（**只允许** `allow` / `flag_for_review`）。"""
    import json

    try:
        with open(_risk_action_matrix_path(), encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {
            "actions": {
                "allow": {"verdict": "PASS", "always_human_review": False},
                "flag_for_review": {"verdict": "REVIEW", "always_human_review": True},
            },
            "matrix": [],
        }


def _action_allowed(matrix: dict, risk_level: str, action: str) -> bool:
    for entry in matrix.get("matrix", []):
        if entry.get("risk_level") == risk_level and entry.get("action") == action:
            return bool(entry.get("allowed"))
    return action == "allow"


def _verdict_for(matrix: dict, action: str) -> str:
    spec = matrix.get("actions", {}).get(action, {})
    return spec.get("verdict", "REVIEW")


def _needs_human_review(matrix: dict, action: str, errors: list[dict]) -> bool:
    spec = matrix.get("actions", {}).get(action, {})
    if spec.get("always_human_review"):
        return True
    return any(e.get("severity") in (SEVERITY_ERROR, SEVERITY_FATAL) for e in errors)


def ingest_paths(paths, request_id: str, options=None, scope=None, target=None) -> dict:
    """读取一组外部文件并产出三份契约产物。

    参数见 `sbr_ingestion.ingest_paths`。
    """
    options = options or {}
    scope = scope or {}
    target = target or {}

    if isinstance(paths, (str, os.PathLike)):
        paths = [paths]
    paths = [os.fspath(p) for p in paths]

    matrix = _load_matrix()
    error_log = ErrorLog()
    started_at = utc_now_iso()

    products: list[dict] = []
    provenance_inputs: list[dict] = []
    per_file_summary: list[dict] = []
    failed_records: list[dict] = []

    for path in paths:
        entry, file_products, file_errors, failed = _ingest_one(
            path, options, error_log, started_at
        )
        provenance_inputs.append(entry)
        products.extend(file_products)
        failed_records.extend(failed)
        per_file_summary.append({
            "path": path,
            "kind": entry.get("kind"),
            "records_parsed": entry.get("records_parsed"),
            "records_failed": entry.get("records_failed"),
        })

    errors = error_log.items

    # 失败判定：**任何**记录级失败都算失败 —— 包括只丢了单行的情况。
    # 只有 error/fatal 或「有记录没读出来」才升级动作；纯提示性 warning
    # （如「标识符是推导出来的」）不升级。
    #
    # 另一条判据：**读到了 0 条记录且有输入** —— 视为失败。
    # 扫描件 PDF（无文本层）、纯图片等情形根本读不出内容，
    # 此时若判 PASS，等于把「什么都没读到」说成「一切正常」，
    # 与硬约束 H3「输入缺失不等于合规」同理。
    has_failures = (
        any(e.get("severity") in (SEVERITY_ERROR, SEVERITY_FATAL) for e in errors)
        or any((i.get("records_failed") or 0) > 0 for i in provenance_inputs)
        or bool(failed_records)
        or (bool(provenance_inputs) and not products
            and any((i.get("records_parsed") or 0) == 0
                    and i.get("kind") not in ("image", "unknown", "unsupported")
                    for i in provenance_inputs))
    )

    # --- 本模块的动作只能是 allow / flag_for_review ---
    risk_level = "low" if has_failures else "info"
    action = "flag_for_review" if has_failures else "allow"
    if not _action_allowed(matrix, risk_level, action):
        action = "flag_for_review"
    verdict = _verdict_for(matrix, action)
    requires_human_review = _needs_human_review(matrix, action, errors)

    produced_at = utc_now_iso()

    # --- SkillInput ---
    skill_input = {
        "request_id": request_id,
        "task_type": "ingestion",
        "target": {
            "kind": target.get("kind", "data_source"),
            "ref": target.get("ref") or (paths[0] if paths else None),
            "count": target.get("count", len(products)),
        },
        "products": products,
        "cases": [],
        "rules": [],
        "scope": scope,
        "options": _public_options(options),
        "provenance": {
            "inputs": provenance_inputs,
            "produced_at": produced_at,
            "producer": f"{MODULE_NAME}/{_version()}",
        },
    }

    # --- AuditResult ---
    result_id = f"RES-INGEST-{request_id}"
    reason = _build_reason(provenance_inputs, products, errors)
    result = {
        "result_id": result_id,
        "request_id": request_id,
        "module": MODULE_NAME,
        "target_ref": skill_input["target"]["ref"] or "ingestion-batch",
        "verdict": verdict,
        "risk_level": risk_level,
        "action": action,
        "reason": reason,
        "rule_refs": [],
        "evidence_refs": [],
        "confidence": "likely" if has_failures else "confirmed",
        "requires_human_review": requires_human_review,
        "review_rationale": _build_review_rationale(errors) if requires_human_review else None,
        "rule_version": RULE_VERSION,
        "provenance": {
            "produced_at": produced_at,
            "producer": f"{MODULE_NAME}/{_version()}",
            "source_refs": [p["path"] for p in provenance_inputs],
            "notes": (f"parsed {len(products)} product(s) from {len(provenance_inputs)} "
                     f"input file(s); {len(errors)} error(s) recorded"),
        },
        "errors": errors,
        "unevaluated": _build_unevaluated(failed_records),
    }

    # --- ModuleHandoff ---
    handoff = {
        "handoff_id": f"HO-INGEST-{request_id}",
        "from_module": MODULE_NAME,
        "to_module": target.get("to_module", "shopee-br-compliance"),
        "request_id": request_id,
        "payload_ref": {
            "artifact_ref": None,
            "inline": {
                "products": products,
                "provenance": skill_input["provenance"],
                "audit_result": result,
            },
            "record_count": len(products),
        },
        "contract_version": CONTRACT_VERSION,
        "produced_at": produced_at,
        "assumptions": _build_assumptions(options, per_file_summary),
        "known_gaps": _build_known_gaps(errors, products, failed_records),
        "unevaluated": _build_unevaluated(failed_records),
        "requires_human_review": requires_human_review,
    }

    return {
        "skill_input": skill_input,
        "results": [result],
        "handoff": handoff,
        "products": products,
        "errors": errors,
    }


def _version() -> str:
    from . import __version__

    return __version__


def _public_options(options: dict) -> dict:
    """只把「模块认识且下游需要知道」的选项写进 `SkillInput.options`。"""
    allowed = ("default_shop_id", "default_currency", "shop_name", "sheet")
    return {k: options[k] for k in allowed if k in options}


def _ingest_one(path: str, options: dict, error_log: ErrorLog, started_at: str):
    """读取单个文件。返回 `(provenance_entry, products, errors, failed)`。"""
    abspath = os.path.abspath(path)
    entry = {
        "path": path,
        "kind": None,
        "digest": None,
        "parsed_at": None,
        "parser_version": None,
        "records_parsed": None,
        "records_failed": None,
    }

    if not os.path.exists(abspath):
        error_log.error(STAGE_PARSE, f"input file does not exist: {path}",
                        {"path": path})
        entry["kind"] = "unknown"
        entry["parsed_at"] = utc_now_iso()
        entry["parser_version"] = f"{MODULE_NAME}/{_version()}"
        # 文件不存在 → 没有内容可哈希，digest 合法为 null（契约允许）。
        # 但解析计数仍要如实填：读了 0 条，失败 1 条。
        entry["records_parsed"] = 0
        entry["records_failed"] = 1
        return entry, [], [], []

    if not os.path.isfile(abspath):
        error_log.error(STAGE_PARSE, f"input path is not a regular file: {path}",
                        {"path": path})
        entry["kind"] = "unknown"
        entry["parsed_at"] = utc_now_iso()
        entry["parser_version"] = f"{MODULE_NAME}/{_version()}"
        entry["records_parsed"] = 0
        entry["records_failed"] = 1
        return entry, [], [], []

    # --- 内容哈希（只读） ---
    try:
        entry["digest"] = sha256_file(abspath)
    except OSError as exc:
        error_log.error(STAGE_PROVENANCE, f"could not hash {path}: {exc}",
                        {"path": path})

    # --- 格式识别 ---
    try:
        kind = detect_kind(abspath)
        entry["kind"] = kind
    except UnsupportedFormat as exc:
        error_log.error(STAGE_PARSE, exc.message, exc.context)
        entry["kind"] = "unsupported"
        entry["parsed_at"] = utc_now_iso()
        entry["parser_version"] = f"{MODULE_NAME}/{_version()}"
        entry["records_parsed"] = 0
        entry["records_failed"] = 1
        return entry, [], [], []

    # --- 解析 ---
    try:
        doc = parse_file(abspath, options)
    except ParseError as exc:
        error_log.error(STAGE_PARSE, exc.message, exc.context)
        entry["parsed_at"] = utc_now_iso()
        entry["parser_version"] = f"{MODULE_NAME}/{_version()}"
        entry["records_parsed"] = 0
        entry["records_failed"] = 1
        return entry, [], [], []

    entry["kind"] = doc.kind
    entry["parsed_at"] = utc_now_iso()
    entry["parser_version"] = f"{MODULE_NAME}/{_version()}"
    entry["records_parsed"] = doc.records_parsed
    entry["records_failed"] = doc.records_failed

    for item in doc.errors:
        severity = item.get("severity", SEVERITY_WARNING)
        error_log.add(STAGE_PARSE, severity, item.get("message", "parse error"),
                      item.get("context"))

    # --- 字段映射与标准化 ---
    contexts = []
    for index, record in enumerate(doc.records):
        contexts.append({
            "kind": doc.kind,
            "path": path,
            "imported_at": started_at,
            "locator": doc.locator(index),
            "default_shop_id": options.get("default_shop_id"),
            "default_currency": options.get("default_currency"),
            "shop_name": options.get("shop_name") or (doc.meta.get("banner") or {}).get("shop_name"),
        })

    products, failed, issues = build_products(doc.records, contexts)

    for item in issues:
        severity = item.get("severity", SEVERITY_WARNING)
        stage = STAGE_FIELD_MAPPING if severity == SEVERITY_ERROR else STAGE_NORMALIZE
        error_log.add(stage, severity, item.get("message", "record issue"),
                      item.get("context"))

    for item in failed:
        error_log.error(
            STAGE_FIELD_MAPPING,
            f"record at {item['locator']} could not be normalised "
            f"(missing: {', '.join(item['missing_fields'])}); it was NOT dropped silently",
            {"locator": item["locator"], "missing_fields": item["missing_fields"]},
        )

    return entry, products, [], failed


def _build_reason(inputs: list[dict], products: list[dict], errors: list[dict]) -> str:
    """一句话说明「读到了什么、依据是什么」。"""
    total = sum(i.get("records_parsed") or 0 for i in inputs)
    failed = sum(i.get("records_failed") or 0 for i in inputs)
    parts = [f"parsed {total} record(s) into {len(products)} normalised product(s) "
             f"from {len(inputs)} input file(s)"]
    if failed:
        parts.append(f"{failed} record(s) failed")
    if errors:
        parts.append(f"{len(errors)} error(s) reported")
    return "; ".join(parts) + "; source digests recorded in provenance.inputs"


def _build_review_rationale(errors: list[dict]) -> str:
    stages = sorted({e.get("stage", "unknown") for e in errors})
    return ("manual review needed: parsing problems were recorded at stage(s) "
            + ", ".join(stages) + "; check errors[] for the affected records")


def _build_unevaluated(failed: list[dict]) -> list[dict]:
    """必填字段缺失的记录 → `unevaluated` 条目（硬约束 H3）。

    本模块不评估规则，但「这条记录因缺字段而无法进入审核链路」这件事
    必须可见 —— 绝不能因为缺字段就当作通过。
    """
    items: list[dict] = []
    for entry in failed:
        items.append({
            "rule_id": "SBR-INGEST-REQ-001",
            "reason": (f"record at {entry['locator']} could not be normalised because "
                       f"required field(s) are missing: {', '.join(entry['missing_fields'])}"),
            "missing_fields": entry["missing_fields"],
        })
    return items


def _build_assumptions(options: dict, summaries: list[dict]) -> list[str]:
    """本模块做出的假设 —— 下游必须知道。"""
    assumptions = [
        "Column-to-field mapping uses the alias table in references/field_mapping.md; "
        "columns that are not in the table are preserved verbatim under attributes.",
        "Normalisation (case folding, accent folding, whitespace collapsing) is applied "
        "for comparison only; stored values keep their original text.",
        "The ingestion layer performs no OCR and no logo detection: image records are "
        "registered with empty ocr_text / detected_logos so downstream image rules are "
        "reported as unevaluated rather than as passed.",
        "This module produces no compliance finding: every AuditResult it emits describes "
        "the reading step only, and its action never exceeds flag_for_review.",
    ]
    if options.get("default_shop_id"):
        assumptions.append(
            f"Records without a shop_id were assigned the default {options['default_shop_id']!r}."
        )
    if options.get("default_currency"):
        assumptions.append(
            f"Records without a currency were assigned the default {options['default_currency']!r}."
        )
    if summaries:
        assumptions.append(
            "Only the first readable worksheet of each workbook was parsed; "
            "additional worksheets were not ingested."
        )
    return assumptions


def _build_known_gaps(errors: list[dict], products: list[dict], failed: list[dict]) -> list[str]:
    """已知缺口 —— 不得让下游误以为结果完整。"""
    gaps: list[str] = []
    if failed:
        gaps.append(
            f"{len(failed)} record(s) could not be normalised (required fields missing) "
            f"and are not present in products[]; see errors[] and unevaluated[]."
        )
    if errors:
        gaps.append(
            f"{len(errors)} error(s) were recorded during reading; the affected rows may "
            f"carry only partial data."
        )
    image_products = [p for p in products if p.get("images")]
    if image_products:
        gaps.append(
            f"{len(image_products)} product(s) carry image references without OCR text "
            f"or detected logos; image-based rules must be treated as unevaluated."
        )
    gaps.append(
        "No OCR, visual analysis, platform scraping or link following is performed by "
        "this module; only local files were read."
    )
    if not gaps:
        gaps.append("No known gaps were recorded for this batch.")
    return gaps
