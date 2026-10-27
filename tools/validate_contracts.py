#!/usr/bin/env python3
"""校验公共契约自身的一致性。

检查项：
  1. contracts/ 下所有 JSON 语法合法
  2. risk_action_matrix 实例符合其 Schema
  3. 矩阵覆盖 risk_levels × actions 全部组合
  4. 全部 schema 的 $ref 可解析
  5. 全部 schema 的 $id 唯一且命名规范
  6. 硬约束 H1–H6 齐备
  7. 每个 schema 都有 title / description
  8. contracts/README.md 索引的每个文件都存在，且每个文件都被索引

Usage: python3 tools/validate_contracts.py
Exit 0 = 全部通过
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACTS = os.path.join(ROOT, "contracts")
sys.path.insert(0, os.path.join(ROOT, "tools"))

from validate_json import Validator  # noqa: E402

ERRORS: list[str] = []
OK: list[str] = []


def ok(msg):
    OK.append(msg)


def err(msg):
    ERRORS.append(msg)
    print(f"  FAIL {msg}")


def load(name):
    with open(os.path.join(CONTRACTS, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    files = sorted(f for f in os.listdir(CONTRACTS) if f.endswith(".json"))
    if not files:
        err("contracts/ 下没有 JSON 文件")
        return report()

    schemas = {}
    instances = {}

    # 1. 语法
    for f in files:
        try:
            data = load(f)
            ok(f"JSON 合法 {f}")
        except Exception as e:  # noqa: BLE001
            err(f"JSON 非法 {f}: {e}")
            continue
        if f.endswith(".schema.json"):
            schemas[f] = data
        else:
            instances[f] = data

    # 2/3. 矩阵实例 vs 其 Schema
    mschema = schemas.get("risk_action_matrix.schema.json")
    minst = instances.get("risk_action_matrix.json")
    if mschema and minst:
        verrs = Validator(mschema, base_dir=CONTRACTS).validate(minst)
        if verrs:
            err(f"risk_action_matrix 实例不符: {'; '.join(verrs[:3])}")
        else:
            ok("risk_action_matrix 实例符合其 Schema")

        levels = set(minst.get("risk_levels", {}))
        actions = set(minst.get("actions", {}))
        combos = {(m["risk_level"], m["action"]) for m in minst.get("matrix", [])}
        missing = sorted((r, a) for r in levels for a in actions if (r, a) not in combos)
        if missing:
            err(f"矩阵缺 {len(missing)} 组合: {missing[:4]}")
        else:
            ok(f"矩阵覆盖全部 {len(levels)}×{len(actions)}={len(levels) * len(actions)} 组合")

        # 6. 硬约束
        hids = {h["id"] for h in minst.get("hard_constraints", [])}
        for h in ["H1", "H2", "H3", "H4", "H5", "H6"]:
            if h not in hids:
                err(f"硬约束 {h} 缺失")
        if all(h in hids for h in ["H1", "H2", "H3", "H4", "H5", "H6"]):
            ok("硬约束 H1–H6 齐备")

        # 聚合规则与硬约束引用完整性
        for c in minst.get("verdict_aggregation", []):
            if "action" in c and c["action"] not in actions:
                err(f"聚合规则引用未知 action: {c['action']}")
    else:
        err("缺少 risk_action_matrix 及其 Schema")

    # 4/5/7. schema 自身
    seen_ids = {}
    for f, s in schemas.items():
        # title / description
        if not s.get("title"):
            err(f"{f} 缺 title")
        if not s.get("description"):
            err(f"{f} 缺 description")
        # $id
        sid = s.get("$id")
        if not sid:
            err(f"{f} 缺 $id")
        else:
            if sid in seen_ids:
                err(f"$id 重复 {sid} ({f} 与 {seen_ids[sid]})")
            seen_ids[sid] = f
            if not sid.startswith("https://shopee-br-compliance-agent.local/contracts/"):
                err(f"{f} $id 不符合命名规范: {sid}")
        # $ref 可解析
        try:
            Validator(s, base_dir=CONTRACTS)
            ok(f"$ref 可解析 {f}")
        except Exception as e:  # noqa: BLE001
            err(f"{f} $ref 无法解析: {e}")

    # 8. README 索引双向一致
    rpath = os.path.join(CONTRACTS, "README.md")
    if os.path.exists(rpath):
        rtxt = open(rpath, encoding="utf-8").read()
        indexed = set(re.findall(r"`([a-z_0-9]+\.(?:schema\.)?json)`", rtxt))
        actual = set(files)
        for f in sorted(actual - indexed):
            err(f"contracts/README.md 未索引 {f}")
        for f in sorted(indexed - actual):
            err(f"contracts/README.md 索引了不存在的 {f}")
        if actual == indexed:
            ok(f"README 索引与实际文件一致（{len(actual)} 个）")
    else:
        err("缺 contracts/README.md")

    return report()


def report():
    print(f"\n{'=' * 58}")
    print(f"契约校验 — 通过 {len(OK)}，失败 {len(ERRORS)}")
    if ERRORS:
        print("\nFailures:")
        for e in ERRORS:
            print(f"  - {e}")
        return 1
    print("公共契约全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
