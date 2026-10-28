"""冻结契约的**只读**校验器（最小 JSON Schema 子集）。

主 Skill 在整合前必须判断「上游模块交来的 `AuditResult` 是否符合契约」：

* 不符合 → 记 `error` 并**排除该条**（`tasks/TASK-MAIN-01.md` §8）
* 符合 → 进入整合

实现只覆盖 `contracts/audit_result.schema.json` / `module_handoff.schema.json`
实际用到的关键字：`type` / `required` / `properties` / `additionalProperties` /
`items` / `enum` / `pattern` / `minLength` / `minItems` / `minimum` /
`$ref`（同目录文件 + 本地指针）。

**不引入第三方依赖**（本项目没有 `jsonschema`）。仓库自带的
`tools/validate_json.py` 是更完整的实现 —— 两者读同一份冻结契约，结论一致。
本文件是**运行时自检**用的最小副本（主 Skill 在整合链路上必须能自己判合规）。
"""

from __future__ import annotations

import json
import os
import re

_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _is_type(value, tname: str) -> bool:
    if tname == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if tname == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if tname == "boolean":
        return isinstance(value, bool)
    cls = _TYPE_MAP.get(tname)
    if cls is None:
        return True
    if cls is not bool and isinstance(value, bool) and cls in (int, float, str):
        return False
    return isinstance(value, cls)


class SchemaError(Exception):
    """Schema 文件本身不可用。"""


class ContractValidator:
    """按 `contracts/` 下的 Schema 校验一份 JSON 文档。"""

    def __init__(self, schema_path: str) -> None:
        self.schema_path = os.path.abspath(schema_path)
        self.base_dir = os.path.dirname(self.schema_path)
        try:
            with open(self.schema_path, encoding="utf-8") as handle:
                self.schema = json.load(handle)
        except (OSError, ValueError) as exc:
            raise SchemaError(f"cannot load schema {self.schema_path}: {exc}") from exc

    # -- $ref ------------------------------------------------------------
    def _resolve(self, ref: str):
        if ref.startswith("#"):
            node = self.schema
            for part in ref.lstrip("#/").split("/"):
                if not part:
                    continue
                part = part.replace("~1", "/").replace("~0", "~")
                node = node[part]
            return node
        path = os.path.normpath(os.path.join(self.base_dir, ref))
        if not os.path.exists(path):
            raise SchemaError(f"cannot resolve $ref {ref!r}")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    # -- 校验 ------------------------------------------------------------
    def validate(self, data, path: str = "$") -> list[str]:
        errors: list[str] = []
        self._check(data, self.schema, path, errors)
        return errors

    def _check(self, data, schema, path: str, errors: list[str]) -> None:
        if schema is True or schema == {}:
            return
        if schema is False:
            errors.append(f"{path}: schema forbids any value")
            return
        if "$ref" in schema:
            self._check(data, self._resolve(schema["$ref"]), path, errors)
            return

        if "type" in schema:
            tnames = schema["type"]
            tnames = tnames if isinstance(tnames, list) else [tnames]
            if not any(_is_type(data, n) for n in tnames):
                errors.append(f"{path}: expected type {tnames}, got {type(data).__name__}")
                return

        if "enum" in schema and data not in schema["enum"]:
            errors.append(f"{path}: value {data!r} not in enum {schema['enum']}")

        if isinstance(data, str):
            if "minLength" in schema and len(data) < schema["minLength"]:
                errors.append(f"{path}: length {len(data)} < minLength {schema['minLength']}")
            if "pattern" in schema and not re.search(schema["pattern"], data):
                errors.append(f"{path}: {data!r} does not match pattern {schema['pattern']!r}")

        if isinstance(data, list):
            if "minItems" in schema and len(data) < schema["minItems"]:
                errors.append(f"{path}: {len(data)} items < minItems {schema['minItems']}")
            if "items" in schema:
                for index, item in enumerate(data):
                    self._check(item, schema["items"], f"{path}[{index}]", errors)

        if isinstance(data, dict):
            for req in schema.get("required", []):
                if req not in data:
                    errors.append(f"{path}: missing required property {req!r}")
            props = schema.get("properties", {})
            additional = schema.get("additionalProperties", True)
            for key, value in data.items():
                if key in props:
                    self._check(value, props[key], f"{path}.{key}", errors)
                    continue
                if additional is False:
                    errors.append(f"{path}: additional property {key!r} is not allowed")
                elif isinstance(additional, dict):
                    self._check(value, additional, f"{path}.{key}", errors)


def audit_result_validator(root: str) -> ContractValidator:
    return ContractValidator(os.path.join(root, "contracts", "audit_result.schema.json"))


def module_handoff_validator(root: str) -> ContractValidator:
    return ContractValidator(os.path.join(root, "contracts", "module_handoff.schema.json"))


def skill_input_validator(root: str) -> ContractValidator:
    return ContractValidator(os.path.join(root, "contracts", "skill_input.schema.json"))
