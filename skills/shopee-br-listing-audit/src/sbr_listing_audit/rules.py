"""规则加载与来源层级约束。

本模块拥有 `PI` / `RI` / `MED` / `LV` 四个前缀。规则来源：

| 文件 | 前缀 | 本模块权限 |
|---|---|---|
| `rules/01_prohibited_restricted_items.json` | `PI` `RI` | **可写** |
| `rules/05_medicines_health.json` | `MED` | **可写** |
| `rules/03_listing_violations.json` | `LV` | **拥有** |

`rules/03` 混有两个 owner 的前缀，拆分由集成 Agent 在集成阶段执行；
本模块只**读取**其中的 `LV` 部分，不写该文件（见 `SKILL.md` §5）。

`SkillInput.rules[]` 若显式传入规则，则**优先**于文件加载 —— 上游可以
指定本次要用的规则集合（含自定义规则），但来源层级约束（H2）对它们
同样生效。
"""

from __future__ import annotations

import json
import os
from typing import Any

#: 本模块拥有的规则前缀。
OWNED_PREFIXES = ("PI", "RI", "MED", "LV")

#: 本模块拥有的规则文件（仓库根相对路径）。
OWNED_RULE_FILES = (
    "rules/01_prohibited_restricted_items.json",
    "rules/05_medicines_health.json",
)

#: 本模块拥有的规则文件（`LV` 前缀）。2026-10-28 集成拆分后由
#: `rules/03_listing_violations_duplicates.json` 独立成
#: `rules/03_listing_violations.json`；`DUP` 前缀已拆至
#: `rules/06_duplicate_listings.json`（duplicate-detection 拥有）。
OWNED_RULE_FILES = (
    "rules/01_prohibited_restricted_items.json",
    "rules/05_medicines_health.json",
    "rules/03_listing_violations.json",
)

#: 本模块只读引用、但前缀属于本模块的规则文件。
READONLY_RULE_FILES = ()

#: `source.tier` → 允许的最高动作（`contracts/risk_action_matrix.json`
#: 的 H2 条款）。**不可自造**：这四档最高只能到 `flag_for_review`。
TIER_MAX_ACTION = {
    "platform_official": "block",
    "law": "block",
    "technical": "flag_for_review",
    "internal_risk": "flag_for_review",
    "unverified": "flag_for_review",
    "ai_inference": "flag_for_review",
}

#: 阻断类动作 —— 只能由 `platform_official` / `law` 的 `active` 规则产生。
BLOCKING_ACTIONS = ("block", "freeze_relist", "escalate_legal")

#: IP 四类（硬约束 H1）。
IP_CATEGORIES = ("ip_trademark", "ip_copyright", "ip_design", "ip_patent")


class RuleLoadError(Exception):
    """规则文件缺失或不可解析 —— 该模块必须停止并显式失败。"""


def rule_prefix(rule_id: str) -> str:
    """`SBR-PI-001` → `PI`。"""
    parts = str(rule_id or "").split("-")
    return parts[1] if len(parts) >= 2 else ""


def _repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    # .../skills/shopee-br-listing-audit/src/sbr_listing_audit/rules.py
    return os.path.abspath(os.path.join(here, "..", "..", "..", ".."))


def _load_collection(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise RuleLoadError(f"rule file is missing: {path}") from exc
    except (OSError, ValueError) as exc:
        raise RuleLoadError(f"rule file is unreadable: {path}: {exc}") from exc


def load_rules(root: str | None = None,
               extra_rules: list[dict] | None = None,
               prefixes: tuple[str, ...] | None = None) -> list[dict]:
    """加载本模块可用规则。

    参数
    ----
    root:
        仓库根路径；缺省由本文件位置推导。
    extra_rules:
        `SkillInput.rules[]` —— 优先于文件加载。
    prefixes:
        限定前缀；缺省为 `OWNED_PREFIXES`。

    返回
    ----
    `list[dict]` —— 规则字典，**已归一化**为规则信封字段名
    （`decision` → `action`，`source_tier` → `source.tier` 等），
    同时保留原始键以便溯源。
    """
    root = root or _repo_root()
    wanted = tuple(prefixes) if prefixes else OWNED_PREFIXES

    collected: list[dict] = []
    seen: set[str] = set()

    for relative in OWNED_RULE_FILES + READONLY_RULE_FILES:
        path = os.path.join(root, relative)
        if not os.path.exists(path):
            if relative in OWNED_RULE_FILES:
                raise RuleLoadError(f"owned rule file is missing: {relative}")
            continue
        collection = _load_collection(path)
        for rule in collection.get("rules", []):
            rule_id = rule.get("rule_id")
            if not rule_id:
                continue
            if rule_prefix(rule_id) not in wanted:
                continue
            if rule_id in seen:
                continue
            seen.add(rule_id)
            collected.append(normalise_rule(rule, source_file=relative))

    # --- 上游显式传入的规则优先 ---
    for rule in extra_rules or []:
        rule_id = rule.get("rule_id")
        if not rule_id:
            continue
        if rule_prefix(rule_id) not in wanted:
            continue
        collected = [item for item in collected if item["rule_id"] != rule_id]
        collected.append(normalise_rule(rule, source_file="skill_input.rules[]"))

    collected.sort(key=lambda item: item["rule_id"])
    return collected


def normalise_rule(rule: dict, source_file: str = "") -> dict:
    """把规则归一化成统一形状（**不修改原字典**）。

    规则文件用 `decision` / `source_tier` / `source_excerpt`，
    规则信封用 `action` / `source.tier` / `source.excerpt`。
    本模块内部一律用信封形状，输出时再投影回 `audit_result` 的
    `rule_refs` 形状。
    """
    raw_source = rule.get("source")
    source: dict[str, Any] = raw_source if isinstance(raw_source, dict) else {}
    tier = rule.get("source_tier") or source.get("tier") or "unverified"
    excerpt = rule.get("source_excerpt") or source.get("excerpt")
    url = rule.get("source_url") or source.get("url")
    last_verified = rule.get("last_verified") or source.get("last_verified")

    normalised = dict(rule)
    normalised["action"] = rule.get("action") or rule.get("decision") or "flag_for_review"
    normalised["source"] = {
        "tier": tier,
        "url": url,
        "excerpt": excerpt,
        "last_verified": last_verified,
    }
    normalised["requires_human_review"] = bool(
        rule.get("requires_human_review", rule.get("human_review_required", False))
    )
    normalised["evidence_required"] = list(rule.get("evidence_required") or [])
    normalised["trigger_conditions"] = list(rule.get("trigger_conditions") or [])
    normalised["status"] = rule.get("status", "draft")
    normalised["version"] = rule.get("version", 1)
    normalised["category"] = rule.get("category", "listing_violation")
    normalised["severity"] = rule.get("severity", "info")
    normalised["_source_file"] = source_file
    return normalised


def tier_max_action(tier: str) -> str:
    """该来源层级允许的最高动作。未知层级按最保守处理。"""
    return TIER_MAX_ACTION.get(tier, "flag_for_review")


def blocking_allowed(rule: dict) -> bool:
    """该规则**是否允许**产出阻断类动作（硬约束 H2）。

    条件：来源层级 ∈ {platform_official, law} **且** `status == active`。
    """
    tier = (rule.get("source") or {}).get("tier")
    if tier not in ("platform_official", "law"):
        return False
    return rule.get("status") == "active"


def is_ip_rule(rule: dict) -> bool:
    """该规则是否属 IP 四类（硬约束 H1）。"""
    return rule.get("category") in IP_CATEGORIES
