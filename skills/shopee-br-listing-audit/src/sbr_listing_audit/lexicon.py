"""词库筛查 —— 复用 `tools/scan_lexicon.py` 的确定性扫描能力。

**词库命中恒为信号，不是结论。** 本模块只做两件事：

1. 扫描商品全部可见文案（标题 + 详情 + 属性 + 品牌 + 类目），记录
   命中位置（字段 + 偏移 + 片段）。
2. 通过 `contracts/lexicon_rule_map.json` 把命中词组映射到**候选规则**，
   供规则层复核。映射本身不产生结论 —— 规则层仍按 `source.tier` 与
   `requires_input` 判定。

词库与豁免的权威定义在 `lexicon/term_groups.json` /
`lexicon/exemptions.json`（由 `shopee-br-data-ingestion` 拥有）。
扫描器实现复用 `tools/scan_lexicon.py`（本模块拥有），**不重复实现**
归一化与边界策略 —— 边界写错一处就会全库误报。
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any


def _repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", "..", ".."))


class LexiconUnavailable(Exception):
    """词库或扫描器不可用 —— 该维度标记未评估，不静默跳过。"""


def _load_scanner(root: str):
    """加载 `tools/scan_lexicon.py` 的 `Scanner`。"""
    tools_dir = os.path.join(root, "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    try:
        from scan_lexicon import Scanner  # type: ignore
    except ImportError as exc:  # pragma: no cover - 环境异常
        raise LexiconUnavailable(f"cannot import tools/scan_lexicon.py: {exc}") from exc
    try:
        return Scanner(os.path.join(root, "lexicon"))
    except (OSError, ValueError) as exc:
        raise LexiconUnavailable(f"lexicon is unusable: {exc}") from exc


def load_rule_map(root: str | None = None) -> dict[str, list[str]]:
    """载入 `contracts/lexicon_rule_map.json` 的「词组 → 规则」映射。"""
    root = root or _repo_root()
    path = os.path.join(root, "contracts", "lexicon_rule_map.json")
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except FileNotFoundError as exc:
        raise LexiconUnavailable(f"lexicon rule map is missing: {path}") from exc
    except (OSError, ValueError) as exc:
        raise LexiconUnavailable(f"lexicon rule map is unreadable: {exc}") from exc
    mapping: dict[str, list[str]] = {}
    for entry in document.get("mappings", []):
        group_id = entry.get("group_id")
        rule_ids = entry.get("rule_ids") or []
        if group_id:
            mapping[group_id] = [str(rule_id) for rule_id in rule_ids]
    return mapping


def field_scope(root: str | None = None) -> dict[str, tuple[str, ...]]:
    """S1（2026-10-29）：读取映射条目可选的 `scan_fields` 声明。

    `contracts/lexicon_rule_map.json` 的每个 mapping 条目可声明
    `"scan_fields": ["title", "description"]` —— 该词组只在声明字段内
    扫描（未声明者默认全字段）。返回 `{group_id: 字段元组}`；
    当前无任何词组声明 → 空 dict → 行为与旧版完全一致（非破坏性机制）。
    """
    root = root or _repo_root()
    path = os.path.join(root, "contracts", "lexicon_rule_map.json")
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError):
        return {}
    scope: dict[str, tuple[str, ...]] = {}
    for entry in document.get("mappings", []):
        fields = entry.get("scan_fields")
        if fields:
            scope[str(entry.get("group_id"))] = tuple(str(f) for f in fields)
    return scope


def apply_field_scope(hits: list[dict], scope: dict[str, tuple[str, ...]]) -> list[dict]:
    """S1：按 `scan_fields` 声明过滤命中（未声明者不过滤）。

    纯函数（不触碰契约），便于单测与未来契约变更复用。
    """
    if not scope:
        return hits
    return [
        h for h in hits
        if h.get("group_id") not in scope
        or h.get("field") in scope[h["group_id"]]
    ]


def scan_product(product: dict, root: str | None = None,
                 scanner=None, scope=None) -> list[dict]:
    """扫描商品，返回命中列表。

    每条命中含：`group_id` / `term` / `field` / `offset` / `matched` /
    `excerpt` / `confidence` / `exempt` / `risk_hint` / `source_tier`。

    S1（2026-10-29）：按契约 `scan_fields` 声明过滤字段（`scope=None`
    时自动载入；无声明者全字段扫描，行为与旧版一致）。
    """
    root = root or _repo_root()
    scanner = scanner or _load_scanner(root)
    hits = scanner.scan_product(product)
    return apply_field_scope(hits, field_scope(root) if scope is None else scope)


def candidate_rules(hits: list[dict], rule_map: dict[str, list[str]],
                     owned_prefixes: tuple[str, ...]) -> dict[str, list[dict]]:
    """把词库命中折算成「候选规则 → 命中明细」。

    只保留本模块拥有的前缀（`PI` / `RI` / `MED` / `LV`）—— IP 类词组
    归 `shopee-br-ip-review`，重复类归 `shopee-br-duplicate-detection`。
    """
    candidates: dict[str, list[dict]] = {}
    for hit in hits:
        group_id = hit.get("group_id")
        for rule_id in rule_map.get(group_id, []):
            prefix = str(rule_id).split("-")[1] if "-" in str(rule_id) else ""
            if prefix not in owned_prefixes:
                continue
            candidates.setdefault(rule_id, []).append(hit)
    return candidates


def summarise(hits: list[dict]) -> dict[str, Any]:
    """命中汇总（写进 `provenance.notes` 与交接记录）。"""
    groups: dict[str, int] = {}
    for hit in hits:
        groups[hit.get("group_id", "?")] = groups.get(hit.get("group_id", "?"), 0) + 1
    exempted = [hit for hit in hits if hit.get("exempt")]
    exemption_ids = sorted({
        hit["exempt"]["id"]
        for hit in exempted
        if isinstance(hit.get("exempt"), dict) and hit["exempt"].get("id")
    })
    return {
        "total_hits": len(hits),
        "groups": groups,
        "exempted_hits": len(exempted),
        "exemption_ids": exemption_ids,
    }
