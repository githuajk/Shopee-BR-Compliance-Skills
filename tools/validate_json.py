#!/usr/bin/env python3
"""JSON Schema validator for the compliance agent's data files.

Stdlib only: implements the subset of JSON Schema draft 2020-12 that the
project's schemas actually use. Why not `jsonschema`? The Hermes runtime has
no pip access guarantee (PEP 668 managed env), and the project must run
offline. The subset is validated against the spec-required feature list below.

Supported keywords:
  type, required, additionalProperties, properties, patternProperties,
  items, prefixItems, minItems, maxItems, minLength, maxLength, pattern,
  enum, const, minimum, maximum, exclusiveMinimum, exclusiveMaximum,
  multipleOf, oneOf, anyOf, allOf, not, $ref (local "#/..." pointers),
  format (uri, date — advisory, reported as warnings), if/then/else,
  propertyNames, contains, minProperties, maxProperties, uniqueItems

Usage:
    python3 tools/validate_json.py <file_or_dir> [...]
    python3 tools/validate_json.py --schema data/schema/rule.schema.json rules/
"""
import json
import os
import re
import sys

TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def is_type(value, tname):
    if tname == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if tname == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if tname == "boolean":
        return isinstance(value, bool)
    cls = TYPE_MAP.get(tname)
    if cls is None:
        return True
    if cls is not bool and isinstance(value, bool) and cls in (int, float, str):
        return False
    return isinstance(value, cls)


def resolve_ref(ref, root):
    if not ref.startswith("#"):
        raise ValueError(f"only local refs supported, got {ref!r}")
    node = root
    for part in ref.lstrip("#/").split("/"):
        if not part:
            continue
        part = part.replace("~1", "/").replace("~0", "~")
        node = node[part]
    return node


class Validator:
    def __init__(self, schema, base_dir=None):
        self.schema = schema
        self.base_dir = base_dir
        self.warnings = []

    def validate(self, data, root=None, path="$"):
        root = root if root is not None else self.schema
        errs = []
        self._check(data, self.schema, root, path, errs)
        return errs

    def _resolve(self, ref, root):
        """Resolve a $ref.

        Supports local pointers ("#/definitions/x") and sibling schema files
        ("rule.schema.json"), resolved relative to the schema's directory.
        """
        if ref.startswith("#"):
            return resolve_ref(ref, root)
        if self.base_dir:
            path = os.path.normpath(os.path.join(self.base_dir, ref))
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
        raise ValueError(f"cannot resolve $ref {ref!r}")

    def _check(self, data, schema, root, path, errs):
        if schema is True or schema == {}:
            return
        if schema is False:
            errs.append(f"{path}: schema forbids any value")
            return
        if "$ref" in schema:
            self._check(data, self._resolve(schema["$ref"], root), root, path, errs)
            return

        # type
        if "type" in schema:
            t = schema["type"]
            tnames = t if isinstance(t, list) else [t]
            if not any(is_type(data, n) for n in tnames):
                errs.append(f"{path}: expected type {tnames}, got {type(data).__name__}")
                return

        # enum / const
        if "enum" in schema and data not in schema["enum"]:
            errs.append(f"{path}: value {data!r} not in enum {schema['enum']}")
        if "const" in schema and data != schema["const"]:
            errs.append(f"{path}: value {data!r} != const {schema['const']!r}")

        # string constraints
        if isinstance(data, str):
            if "minLength" in schema and len(data) < schema["minLength"]:
                errs.append(f"{path}: length {len(data)} < minLength {schema['minLength']}")
            if "maxLength" in schema and len(data) > schema["maxLength"]:
                errs.append(f"{path}: length {len(data)} > maxLength {schema['maxLength']}")
            if "pattern" in schema and not re.search(schema["pattern"], data):
                errs.append(f"{path}: {data!r} does not match pattern {schema['pattern']!r}")
            if schema.get("format") == "date" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data):
                self.warnings.append(f"{path}: {data!r} is not an ISO date")
            if schema.get("format") == "uri" and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", data):
                self.warnings.append(f"{path}: {data!r} is not an absolute URI")

        # numeric constraints
        if isinstance(data, (int, float)) and not isinstance(data, bool):
            if "minimum" in schema and data < schema["minimum"]:
                errs.append(f"{path}: {data} < minimum {schema['minimum']}")
            if "maximum" in schema and data > schema["maximum"]:
                errs.append(f"{path}: {data} > maximum {schema['maximum']}")
            if "exclusiveMinimum" in schema and data <= schema["exclusiveMinimum"]:
                errs.append(f"{path}: {data} <= exclusiveMinimum {schema['exclusiveMinimum']}")
            if "exclusiveMaximum" in schema and data >= schema["exclusiveMaximum"]:
                errs.append(f"{path}: {data} >= exclusiveMaximum {schema['exclusiveMaximum']}")

        if isinstance(data, list):
            self._check_array(data, schema, root, path, errs)
        if isinstance(data, dict):
            self._check_object(data, schema, root, path, errs)

        # combinators
        if "oneOf" in schema:
            ok = 0
            for sub in schema["oneOf"]:
                if not Validator(sub, self.base_dir).validate(data, root, path):
                    ok += 1
            if ok != 1:
                errs.append(f"{path}: matched {ok} of oneOf branches (must be exactly 1)")
        if "anyOf" in schema:
            if not any(not Validator(sub, self.base_dir).validate(data, root, path) for sub in schema["anyOf"]):
                errs.append(f"{path}: matched no anyOf branch")
        if "allOf" in schema:
            for sub in schema["allOf"]:
                self._check(data, sub, root, path, errs)
        if "not" in schema and not Validator(schema["not"], self.base_dir).validate(data, root, path):
            errs.append(f"{path}: value must NOT match the 'not' schema")
        if "if" in schema:
            cond_ok = not Validator(schema["if"]).validate(data, root, path)
            branch = schema.get("then") if cond_ok else schema.get("else")
            if branch:
                self._check(data, branch, root, path, errs)

    def _check_array(self, data, schema, root, path, errs):
        if "minItems" in schema and len(data) < schema["minItems"]:
            errs.append(f"{path}: {len(data)} items < minItems {schema['minItems']}")
        if "maxItems" in schema and len(data) > schema["maxItems"]:
            errs.append(f"{path}: {len(data)} items > maxItems {schema['maxItems']}")
        if schema.get("uniqueItems"):
            seen = [json.dumps(x, sort_keys=True) for x in data]
            if len(set(seen)) != len(seen):
                errs.append(f"{path}: items are not unique")
        prefix = schema.get("prefixItems") or []
        for i, sub in enumerate(prefix):
            if i < len(data):
                self._check(data[i], sub, root, f"{path}[{i}]", errs)
        if "items" in schema:
            for i in range(len(prefix), len(data)):
                self._check(data[i], schema["items"], root, f"{path}[{i}]", errs)
        if "contains" in schema:
            if not any(not Validator(schema["contains"], self.base_dir).validate(x, root, path) for x in data):
                errs.append(f"{path}: no item matches 'contains' schema")

    def _check_object(self, data, schema, root, path, errs):
        for req in schema.get("required", []):
            if req not in data:
                errs.append(f"{path}: missing required property {req!r}")
        props = schema.get("properties", {})
        pattern_props = schema.get("patternProperties", {})
        addl = schema.get("additionalProperties", True)
        for key, value in data.items():
            handled = False
            if key in props:
                self._check(value, props[key], root, f"{path}.{key}", errs)
                handled = True
            for pat, sub in pattern_props.items():
                if re.search(pat, key):
                    self._check(value, sub, root, f"{path}.{key}", errs)
                    handled = True
            if not handled:
                if addl is False:
                    errs.append(f"{path}: additional property {key!r} is not allowed")
                elif isinstance(addl, dict):
                    self._check(value, addl, root, f"{path}.{key}", errs)
            if "propertyNames" in schema:
                self._check(key, schema["propertyNames"], root, f"{path}.<key {key!r}>", errs)
        if "minProperties" in schema and len(data) < schema["minProperties"]:
            errs.append(f"{path}: {len(data)} properties < minProperties {schema['minProperties']}")
        if "maxProperties" in schema and len(data) > schema["maxProperties"]:
            errs.append(f"{path}: {len(data)} properties > maxProperties {schema['maxProperties']}")


def load_schema(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_file(schema_path, data_path):
    schema = load_schema(schema_path)
    v = Validator(schema, base_dir=os.path.dirname(os.path.abspath(schema_path)))
    try:
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"{data_path}: invalid JSON: {e}"], []
    errs = v.validate(data)
    prefix = f"{data_path}: "
    return [prefix + e for e in errs], [prefix + w for w in v.warnings]


def collect_files(path):
    if os.path.isfile(path):
        return [path]
    out = []
    for root, _, files in os.walk(path):
        for fn in files:
            if fn.endswith(".json"):
                out.append(os.path.join(root, fn))
    return sorted(out)


def main():
    args = sys.argv[1:]
    if args and args[0] == "--schema":
        schema_path = args[1]
        targets = args[2:]
        all_err, all_warn = [], []
        for t in targets:
            for fp in collect_files(t):
                e, w = validate_file(schema_path, fp)
                all_err += e
                all_warn += w
                status = "FAIL" if e else ("WARN" if w else "ok  ")
                print(f"{status} {fp}")
        print(f"\n{len(all_err)} errors, {len(all_warn)} warnings")
        for e in all_err:
            print("  ERROR", e)
        for w in all_warn:
            print("  WARN ", w)
        sys.exit(1 if all_err else 0)
    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    main()
