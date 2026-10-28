"""规则加载与归一化。

本模块拥有规则前缀 `IP`，规则文件是 `rules/02_ip_trademark_copyright.json`。

**两种规则来源都要支持**（两者结构不同）：

1. **规则库文件**（默认）：顶层是 `{"rules": [...]}`，规则用扁平字段 ——
   `decision`（而非 `action`）、`source_tier` / `source_url` / `source_excerpt`
   （而非嵌套的 `source` 对象）。
2. **调用方传入的 `rules[]`**：`contracts/rule_envelope.schema.json` 结构 ——
   `action`、嵌套的 `source{tier,url,excerpt,last_verified}`。

归一化后统一成 `RuleView`，下游判定逻辑只认这一种形状。
"""

from __future__ import annotations

import json
import os

#: 本模块拥有的规则前缀
RULE_PREFIX = "SBR-IP-"

#: IP 四类（硬约束 H1 的适用范围）
IP_CATEGORIES = frozenset({"ip_trademark", "ip_copyright", "ip_design", "ip_patent"})

#: 默认规则文件（仓库根相对）
DEFAULT_RULE_FILE = os.path.join("rules", "02_ip_trademark_copyright.json")

#: 只读引用的规则文件 —— 归属 `shopee-br-duplicate-detection`，
#: 但**授权完整性**是 IP 判定的必要维度（品牌商品是否有品牌方授权）。
#: `contracts/file_ownership.json` 已声明本模块对该文件**只读**。
#: 本模块只从中取 `SBR-AU-001`（授权缺口），不修改该文件。
READONLY_RULE_FILE = os.path.join("rules", "04_cases_relist_authorization.json")

#: 从只读文件里取用的规则 ID
READONLY_RULE_IDS = ("SBR-AU-001",)


class RuleView:
    """归一化后的规则视图。"""

    __slots__ = (
        "rule_id", "title", "category", "description", "severity", "action",
        "source_tier", "source_url", "source_excerpt", "last_verified",
        "status", "version", "evidence_required", "requires_human_review",
        "trigger_conditions", "tags", "notes", "owner_module",
    )

    def __init__(self, **kwargs):
        for name in self.__slots__:
            setattr(self, name, kwargs.get(name))

    @property
    def is_ip(self) -> bool:
        return self.category in IP_CATEGORIES

    def source(self) -> dict:
        """`contracts/rule_envelope.schema.json` 的 `source` 形状。"""
        return {
            "tier": self.source_tier,
            "url": self.source_url,
            "excerpt": self.source_excerpt,
            "last_verified": self.last_verified,
        }

    def as_envelope(self) -> dict:
        """回写为规则信封形状（供交接与人工复核使用）。"""
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "severity": self.severity,
            "action": self.action,
            "source": self.source(),
            "status": self.status,
            "version": self.version,
            "evidence_required": list(self.evidence_required or []),
            "requires_human_review": bool(self.requires_human_review),
            "trigger_conditions": list(self.trigger_conditions or []),
            "tags": list(self.tags or []),
            "notes": self.notes,
            "owner_module": self.owner_module,
        }


def repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", "..", ".."))


def _view_from_flat(rule: dict) -> RuleView:
    return RuleView(
        rule_id=rule.get("rule_id"),
        title=rule.get("title"),
        category=rule.get("category"),
        description=rule.get("description"),
        severity=rule.get("severity"),
        action=rule.get("action") or rule.get("decision"),
        source_tier=rule.get("source_tier"),
        source_url=rule.get("source_url"),
        source_excerpt=rule.get("source_excerpt"),
        last_verified=rule.get("last_verified"),
        status=rule.get("status"),
        version=rule.get("version"),
        evidence_required=rule.get("evidence_required") or [],
        requires_human_review=rule.get("human_review_required",
                                       rule.get("requires_human_review", True)),
        trigger_conditions=rule.get("trigger_conditions") or [],
        tags=rule.get("tags") or [],
        notes=rule.get("notes"),
        owner_module=rule.get("owner_module") or "shopee-br-ip-review",
    )


def _view_from_envelope(rule: dict) -> RuleView:
    source = rule.get("source") or {}
    return RuleView(
        rule_id=rule.get("rule_id"),
        title=rule.get("title"),
        category=rule.get("category"),
        description=rule.get("description"),
        severity=rule.get("severity"),
        action=rule.get("action"),
        source_tier=source.get("tier"),
        source_url=source.get("url"),
        source_excerpt=source.get("excerpt"),
        last_verified=source.get("last_verified"),
        status=rule.get("status"),
        version=rule.get("version"),
        evidence_required=rule.get("evidence_required") or [],
        requires_human_review=rule.get("requires_human_review", True),
        trigger_conditions=rule.get("trigger_conditions") or [],
        tags=rule.get("tags") or [],
        notes=rule.get("notes"),
        owner_module=rule.get("owner_module"),
    )


def load_rules(rules=None, root: str | None = None):
    """加载本模块的规则。

    返回 `(rule_views, errors)`。`errors` 是 `[{stage, severity, message, context}]`。
    """
    errors: list[dict] = []
    views: list[RuleView] = []

    if rules is not None:
        # 调用方传入 —— 规则信封结构
        for raw in rules:
            if not isinstance(raw, dict):
                errors.append({
                    "stage": "rule_loading",
                    "severity": "error",
                    "message": "rule entry is not an object; it was skipped",
                    "context": {"type": type(raw).__name__},
                })
                continue
            rule_id = raw.get("rule_id") or ""
            if not rule_id.startswith(RULE_PREFIX):
                # 非本模块前缀的规则 —— 不参与判定，但**不静默丢弃**。
                errors.append({
                    "stage": "rule_loading",
                    "severity": "warning",
                    "message": (f"rule {rule_id!r} is not owned by this module "
                                 f"(prefix {RULE_PREFIX}) and was not evaluated"),
                    "context": {"rule_id": rule_id},
                })
                continue
            views.append(_view_from_envelope(raw))
        if not views:
            errors.append({
                "stage": "rule_loading",
                "severity": "error",
                "message": ("no IP rules were supplied in the request; the IP "
                            "dimensions could not be evaluated"),
                "context": {"expected_prefix": RULE_PREFIX},
            })
        return views, errors

    path = os.path.join(root or repo_root(), DEFAULT_RULE_FILE)
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError) as exc:
        errors.append({
            "stage": "rule_loading",
            "severity": "fatal",
            "message": f"rule library could not be read or parsed: {exc}",
            "context": {"path": path},
        })
        return [], errors

    raw_rules = document.get("rules") or []
    for raw in raw_rules:
        if not isinstance(raw, dict) or not raw.get("rule_id"):
            errors.append({
                "stage": "rule_loading",
                "severity": "error",
                "message": "rule entry without rule_id was skipped",
                "context": {"title": raw.get("title") if isinstance(raw, dict) else None},
            })
            continue
        views.append(_view_from_flat(raw))

    # --- 只读引用的授权规则 ---
    # 授权完整性是 IP 判定的必要维度（品牌商品是否有品牌方书面授权），
    # 该规则归属 `shopee-br-duplicate-detection`，本模块**只读**引用。
    views.extend(_load_readonly_authorization(root, errors))

    if not views:
        errors.append({
            "stage": "rule_loading",
            "severity": "fatal",
            "message": f"rule library {DEFAULT_RULE_FILE} contains no usable rules",
            "context": {"path": path},
        })
    return views, errors


def rule_version(views: list[RuleView]) -> str:
    """规则集版本标识（写入 `AuditResult.rule_version`）。"""
    versions = [v.version for v in views if isinstance(v.version, int)]
    highest = max(versions) if versions else 0
    return f"sbr-ip-rules/{DEFAULT_RULE_FILE.split('/')[-1]}@{highest}"


def _load_readonly_authorization(root: str | None, errors: list[dict]) -> list[RuleView]:
    """从只读引用的规则文件里取授权规则。

    该文件归属 `shopee-br-duplicate-detection`；本模块只**读**它，
    不修改（`contracts/file_ownership.json` 已声明此只读权限）。
    读不到时如实记 warning —— 不因为只读文件缺失就判定无风险。
    """
    path = os.path.join(root or repo_root(), READONLY_RULE_FILE)
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError) as exc:
        errors.append({
            "stage": "rule_loading",
            "severity": "warning",
            "message": (f"read-only authorisation rule file could not be read "
                        f"or parsed: {exc}; the authorisation dimension could "
                        f"not be evaluated"),
            "context": {"path": path},
        })
        return []

    wanted = set(READONLY_RULE_IDS)
    views: list[RuleView] = []
    for raw in document.get("rules") or []:
        if not isinstance(raw, dict):
            continue
        if raw.get("rule_id") not in wanted:
            continue
        views.append(_view_from_flat(raw))
    missing = wanted - {view.rule_id for view in views}
    if missing:
        errors.append({
            "stage": "rule_loading",
            "severity": "warning",
            "message": (f"authorisation rule(s) {sorted(missing)} were not found "
                        f"in the read-only file; the authorisation dimension "
                        f"could not be evaluated"),
            "context": {"path": path},
        })
    return views
