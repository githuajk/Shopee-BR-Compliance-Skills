"""分流：决定本次请求**执行哪些模块**。

> **最小充分原则**：只执行本次输入真正需要的模块。

理由：每个模块都会产生结论，多跑一个模块就多一份误判风险与复核工时。

**分流只决定「跑哪些模块」，不决定任何合规结论。** 命中与否由各专业模块
自己的规则层判定。

分流结果必须**如实记录**（执行的模块 + 未执行的模块 + 原因），写入
`provenance.notes` 与 `ModuleHandoff.known_gaps` —— 绝不让「没跑」看起来
像「跑过且没问题」。

纯标准库实现。
"""

from __future__ import annotations

from .registry import MODULE_SPECS, ModuleSpec, spec_for

#: 分流阶段
STAGE_INGESTION = "ingestion"
STAGE_CONTENT = "content_audit"
STAGE_IP = "ip"
STAGE_DUPLICATE = "duplicate"
STAGE_REPORTING = "reporting"

#: 全部阶段（固定顺序）
ALL_STAGES = (STAGE_INGESTION, STAGE_CONTENT, STAGE_IP, STAGE_DUPLICATE,
              STAGE_REPORTING)

#: 阶段 → 模块名
STAGE_MODULE = {
    STAGE_INGESTION: "shopee-br-data-ingestion",
    STAGE_CONTENT: "shopee-br-listing-audit",
    STAGE_IP: "shopee-br-ip-review",
    STAGE_DUPLICATE: "shopee-br-duplicate-detection",
    STAGE_REPORTING: "shopee-br-reporting",
}


class RoutingDecision:
    """一次分流决定。"""

    def __init__(self, stages: list[str], reasons: dict[str, str],
                 skipped: dict[str, str], explicit: bool = False) -> None:
        #: 执行的阶段（`ALL_STAGES` 的子集，顺序固定）
        self.stages = list(stages)
        #: 每个执行阶段的理由
        self.reasons = dict(reasons)
        #: 未执行阶段 → 原因
        self.skipped = dict(skipped)
        #: 是否由调用方显式指定（`options.modules`）
        self.explicit = explicit

    @property
    def module_names(self) -> list[str]:
        """执行的模块名（按链路顺序）。"""
        return [STAGE_MODULE[s] for s in self.stages]

    def to_dict(self) -> dict:
        return {
            "stages": list(self.stages),
            "modules": self.module_names,
            "reasons": dict(self.reasons),
            "skipped": dict(self.skipped),
            "explicit": self.explicit,
        }

    def note(self) -> str:
        """人类可读的一行说明 —— 写入 `provenance.notes`。"""
        executed = " → ".join(self.module_names) or "(无)"
        parts = [f"本次执行模块：{executed}"]
        if self.skipped:
            parts.append("未执行：" + "；".join(
                f"{STAGE_MODULE.get(stage, stage)}（{reason}）"
                for stage, reason in self.skipped.items()))
        if self.explicit:
            parts.append("模块集合由调用方显式指定（options.modules）")
        return "；".join(parts)


def _has_images(products: list) -> bool:
    for product in products:
        if isinstance(product, dict) and (product.get("images") or []):
            return True
    return False


def _has_brand_signal(products: list) -> bool:
    for product in products:
        if not isinstance(product, dict):
            continue
        if product.get("brand"):
            return True
        text = " ".join(str(product.get(key) or "")
                         for key in ("title", "description"))
        if any(marker in text.lower() for marker in
               ("nike", "adidas", "samsung", "apple", "sony", "puma", "xiaomi",
                "huawei", "ford", "toyota", "amazon", "réplica", "replica",
                "original", "importado")):
            return True
    return False


def _shops(products: list) -> set:
    shops = set()
    for product in products:
        if isinstance(product, dict) and product.get("shop_id"):
            shops.add(str(product["shop_id"]))
    return shops


def _requires_ingestion(options: dict, input_paths: list) -> bool:
    """是否需要 ingestion。

    * 调用方给了输入文件 → 需要；
    * `options.skip_ingestion` 为真 → 不需要；
    * 已经有 `products[]` → 不需要。
    """
    if options.get("skip_ingestion"):
        return False
    if input_paths:
        return True
    return False


def decide(options: dict | None = None, products: list | None = None,
           cases: list | None = None, input_paths: list | None = None,
           stage: str | None = None) -> RoutingDecision:
    """决定本次执行哪些模块。

    参数
    ----
    options:
        `SkillInput.options`。本模块只读 `options.modules`（显式指定）与
        `options.skip_ingestion`；未知键忽略（契约要求）。
    products:
        已规范化的商品数组（`SkillInput.products`）。
    cases:
        历史案件数组（`SkillInput.cases`）。
    input_paths:
        本次要交给 ingestion 的外部文件路径。
    stage:
        只决定某个阶段的去留。`"ingestion"` → 只判断是否需要 ingestion；
        `"specialists"` → 只判断三个专业维度 + 汇总。

    返回
    ----
    `RoutingDecision`。
    """
    options = dict(options or {})
    products = list(products or [])
    cases = list(cases or [])
    input_paths = list(input_paths or [])

    reasons: dict[str, str] = {}
    skipped: dict[str, str] = {}

    # --- 显式指定：调用方已经决定要跑哪些模块 -------------------
    explicit = options.get("modules")
    if explicit:
        wanted = {str(m).strip() for m in explicit if str(m).strip()}
        unknown = sorted(wanted - {spec.name for spec in MODULE_SPECS})
        stages: list[str] = []
        for candidate in ALL_STAGES:
            module = STAGE_MODULE[candidate]
            if module in wanted:
                stages.append(candidate)
                reasons[candidate] = "由调用方显式指定（options.modules）"
            else:
                skipped[candidate] = "调用方未在 options.modules 中指定该模块"
        for name in unknown:
            skipped[f"unknown:{name}"] = (
                f"未知模块名 {name!r}：不是 contracts/audit_result.schema.json "
                f"枚举内的模块，也不是本模块登记的可驱动模块")
        return RoutingDecision(stages, reasons, skipped, explicit=True)

    # --- 自动分流 -----------------------------------------------
    stages = []
    reasons = {}

    if stage == "ingestion":
        if _requires_ingestion(options, input_paths):
            stages.append(STAGE_INGESTION)
            reasons[STAGE_INGESTION] = (
                "本次输入是外部文件，先经 shopee-br-data-ingestion 规范化")
        else:
            skipped[STAGE_INGESTION] = (
                "输入已是规范模型（products[] 已提供）且无外部文件，跳过 ingestion")
        return RoutingDecision(stages, reasons, skipped, explicit=False)

    # --- 三个专业维度 + 汇总 ---
    if products:
        stages.append(STAGE_CONTENT)
        reasons[STAGE_CONTENT] = (
            "本次有商品内容待审，商品内容维度必须评估"
            "（禁售/受限/药品健康/listing 质量）")
    else:
        skipped[STAGE_CONTENT] = "没有可审的商品内容，内容维度未评估"

    if products:
        stages.append(STAGE_IP)
        if _has_brand_signal(products) or _has_images(products):
            reasons[STAGE_IP] = (
                "商品含品牌词或图片，知识产权与授权维度需要评估")
        else:
            reasons[STAGE_IP] = (
                "有商品待审，IP 维度需要评估（缺图片/品牌时相关规则记为未评估）")
    else:
        skipped[STAGE_IP] = "没有可审的商品，IP 维度未评估"

    shops = _shops(products)
    if products:
        stages.append(STAGE_DUPLICATE)
        if len(shops) >= 2:
            reasons[STAGE_DUPLICATE] = (
                f"本次涉及 {len(shops)} 个店铺（{', '.join(sorted(shops))}），"
                f"跨店同款关联必须在同一次请求内比对")
        else:
            reasons[STAGE_DUPLICATE] = (
                f"本次只涉及 1 个店铺（{next(iter(shops))}）：同店重复与授权/处罚点"
                f"仍需评估，跨店比对该维度会记为未评估")
    else:
        skipped[STAGE_DUPLICATE] = "没有可审的商品，重复与重发维度未评估"

    stages.append(STAGE_REPORTING)
    reasons[STAGE_REPORTING] = "任何批次都以汇总与报告收尾（数据缺口需独立成节）"

    ordered = [s for s in ALL_STAGES if s in stages]
    for candidate in ALL_STAGES:
        if candidate not in ordered:
            skipped.setdefault(candidate, "本次分流未选中该维度")
    return RoutingDecision(ordered, reasons, skipped, explicit=False)


def stage_of(module_name: str) -> str | None:
    """模块名 → 阶段。未知模块 → `None`。"""
    for stage, name in STAGE_MODULE.items():
        if name == module_name:
            return stage
    return None


def spec_of(module_name: str) -> ModuleSpec | None:
    """模块名 → 登记项。"""
    return spec_for(module_name)
