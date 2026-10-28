"""规则索引：只读 `rules/**`，为报告 §6「已查阅规则」提供元信息。

本模块**不定义规则**，也**不修改**规则文件。它只把 `rules/*.json` 里已有的
元信息（类别、严重度、来源层级、核查日期、来源链接）读成一张索引，供报告
呈现。**来源层级与核查日期原样透传**（硬约束 H4），不重新判定。

规则文件里的字段名与 `contracts/rule_envelope.schema.json` 不同
（`decision` vs `action`、`source_tier` vs `source.tier`），
本模块**同时**支持两种写法。
"""

from __future__ import annotations

import json
import os

#: 规则 ID 前缀 → 负责模块（`PROJECT_RULES.md` §8.1）
PREFIX_OWNERS = {
    "PI": "shopee-br-listing-audit",
    "RI": "shopee-br-listing-audit",
    "MED": "shopee-br-listing-audit",
    "LV": "shopee-br-listing-audit",
    "IP": "shopee-br-ip-review",
    "DUP": "shopee-br-duplicate-detection",
    "RL": "shopee-br-duplicate-detection",
    "AU": "shopee-br-duplicate-detection",
    "AC": "shopee-br-duplicate-detection",
}


def rule_prefix(rule_id: str) -> str:
    """从 `SBR-XX-001` 取出前缀 `XX`。"""
    parts = str(rule_id or "").split("-")
    if len(parts) >= 3 and parts[0] == "SBR":
        return parts[1]
    return ""


def owner_of(rule_id: str) -> str:
    """规则前缀对应的负责模块。未知前缀 → 空串。"""
    return PREFIX_OWNERS.get(rule_prefix(rule_id), "")


class RuleIndex:
    """规则元信息索引。

    读不到规则目录时索引为空 —— **不猜、不补**。报告 §6 会显示「无」。
    """

    def __init__(self, rules: dict | None = None) -> None:
        self.rules: dict[str, dict] = dict(rules or {})

    @classmethod
    def load(cls, root: str) -> "RuleIndex":
        base = os.path.join(root, "rules")
        index: dict[str, dict] = {}
        if not os.path.isdir(base):
            return cls(index)
        for name in sorted(os.listdir(base)):
            if not name.endswith(".json"):
                continue
            path = os.path.join(base, name)
            try:
                with open(path, encoding="utf-8") as handle:
                    document = json.load(handle)
            except (OSError, ValueError):
                continue
            for rule in document.get("rules") or []:
                rule_id = rule.get("rule_id")
                if not rule_id:
                    continue
                index[rule_id] = _normalize(rule)
        return cls(index)

    def get(self, rule_id: str) -> dict:
        return self.rules.get(rule_id, {})

    def lookup(self, rule_refs: list[dict]) -> list[dict]:
        """按 `rule_refs[]` 解析出规则元信息。

        规则库里没有的规则（如上游模块自带的临时规则）仍会被列出 ——
        用 `rule_refs` 里已有的字段，缺失处填 `—`。
        """
        resolved: list[dict] = []
        seen: set[str] = set()
        for ref in rule_refs:
            rule_id = ref.get("rule_id")
            if not rule_id or rule_id in seen:
                continue
            seen.add(rule_id)
            meta = self.get(rule_id)
            resolved.append({
                "rule_id": rule_id,
                "title": ref.get("title") or meta.get("title"),
                "category": meta.get("category"),
                "severity": meta.get("severity"),
                "action": meta.get("action"),
                "source_tier": ref.get("source_tier") or meta.get("source_tier"),
                "source_url": ref.get("source_url") or meta.get("source_url"),
                "last_verified": meta.get("last_verified"),
                "status": meta.get("status"),
                "owner_module": meta.get("owner_module"),
                "in_rule_library": rule_id in self.rules,
            })
        return resolved


def _normalize(rule: dict) -> dict:
    """把规则文件的字段形态统一成本模块使用的形态。"""
    raw_source = rule.get("source")
    source = raw_source if isinstance(raw_source, dict) else {}
    return {
        "rule_id": rule.get("rule_id"),
        "title": rule.get("title"),
        "category": rule.get("category"),
        "severity": rule.get("severity"),
        "action": rule.get("action") or rule.get("decision"),
        "source_tier": rule.get("source_tier") or source.get("tier"),
        "source_url": rule.get("source_url") or source.get("url"),
        "last_verified": rule.get("last_verified") or source.get("last_verified"),
        "status": rule.get("status"),
        "owner_module": rule.get("owner_module") or owner_of(str(rule.get("rule_id"))),
        "evidence_required": list(rule.get("evidence_required") or []),
    }
