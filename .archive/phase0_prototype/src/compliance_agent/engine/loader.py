"""Rule and lexicon loading, plus the Aho-Corasick multi-pattern index.

Rule source data lives in JSON only (see project rules). A large keyword
lexicon is compiled into an Aho-Corasick automaton for single-pass scanning,
but the *authoring* format on disk stays JSON.
"""
from __future__ import annotations

import json
import os
import re
from typing import Iterable

from ..models import Rule, norm_text

ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, os.pardir))
RULES_DIR = os.path.join(ROOT, "rules")
LEXICON_DIR = os.path.join(ROOT, "lexicon")


# --------------------------------------------------------------------------
# Rule loading
# --------------------------------------------------------------------------
def load_rules(paths: Iterable[str] | None = None) -> list[Rule]:
    """Load every rule JSON file under rules/ (or the given paths).

    `paths` may be a single path (str) or an iterable of paths. A directory is
    expanded to its *.json files.
    """
    if isinstance(paths, str):
        paths = [paths]
    files: list[str] = []
    if paths:
        for p in paths:
            if os.path.isdir(p):
                files.extend(sorted(
                    os.path.join(p, f) for f in os.listdir(p) if f.endswith(".json")))
            else:
                files.append(p)
    else:
        if os.path.isdir(RULES_DIR):
            files = sorted(
                os.path.join(RULES_DIR, f) for f in os.listdir(RULES_DIR)
                if f.endswith(".json"))
    rules: list[Rule] = []
    seen: dict[str, str] = {}
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            payload = json.load(f)
        items = payload.get("rules", payload) if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            raise ValueError(f"{fp}: expected a list of rules")
        for raw in items:
            r = Rule.from_dict(raw)
            if r.rule_id in seen:
                raise ValueError(
                    f"duplicate rule_id {r.rule_id} in {fp} (already in {seen[r.rule_id]})")
            seen[r.rule_id] = fp
            rules.append(r)
    return rules


def load_lexicon(name: str) -> dict:
    """Load a lexicon JSON file (keyword groups) by name."""
    path = name if os.path.isabs(name) else os.path.join(LEXICON_DIR, name)
    if not path.endswith(".json"):
        path += ".json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------
# Aho-Corasick automaton
# --------------------------------------------------------------------------
class _Node:
    __slots__ = ("children", "fail", "outputs")

    def __init__(self):
        self.children: dict[str, "_Node"] = {}
        self.fail: _Node | None = None
        self.outputs: list[str] = []


class AhoCorasick:
    """Multi-pattern single-pass scanner.

    Patterns are matched case-insensitively and accent-insensitively (the
    lexicon is stored accent-folded). Overlapping matches are reported with
    their character span so a caller can extract context.
    """

    def __init__(self, patterns: dict[str, list[str]]):
        """patterns: {group_name: [pattern, ...]}"""
        self.groups = {g: list(v) for g, v in patterns.items()}
        self.root = _Node()
        self._pattern_index: dict[str, tuple[str, str]] = {}
        for group, pats in self.groups.items():
            for raw in pats:
                key = norm_text(raw)
                if not key:
                    continue
                self._pattern_index[key] = (group, raw)
                node = self.root
                for ch in key:
                    node = node.children.setdefault(ch, _Node())
                node.outputs.append(key)

    def _build(self):
        from collections import deque
        q = deque()
        for ch, child in self.root.children.items():
            child.fail = self.root
            q.append(child)
        while q:
            cur = q.popleft()
            for ch, child in cur.children.items():
                q.append(child)
                f = cur.fail
                while f is not None and ch not in f.children:
                    f = f.fail
                child.fail = f.children[ch] if (f is not None and ch in f.children) else self.root
                child.outputs.extend(child.fail.outputs)

    def scan(self, text: str) -> list[dict]:
        """Return every match: {group, pattern, start, end, excerpt}."""
        if not self._pattern_index:
            return []
        if not hasattr(self, "_built"):
            self._build()
            self._built = True
        folded = norm_text(text)
        results: list[dict] = []
        node = self.root
        for i, ch in enumerate(folded):
            while node is not None and ch not in node.children:
                node = node.fail
            if node is None:
                node = self.root
                continue
            node = node.children[ch]
            for key in node.outputs:
                start = i - len(key) + 1
                group, raw = self._pattern_index[key]
                results.append({
                    "group": group,
                    "pattern": raw,
                    "start": start,
                    "end": i + 1,
                    "excerpt": text[max(0, start - 40):i + 41],
                })
        return results

    def matches_groups(self, text: str) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for m in self.scan(text):
            out.setdefault(m["group"], []).append(m)
        return out


def compile_ac(lexicon: dict) -> AhoCorasick:
    """Build an automaton from a lexicon document.

    Expected shape::

        {"groups": {"prohibited": ["termo", ...], ...}}
    """
    groups = lexicon.get("groups", lexicon)
    return AhoCorasick({k: list(v) for k, v in groups.items()})


# --------------------------------------------------------------------------
# Regex helpers
# --------------------------------------------------------------------------
_REGEX_CACHE: dict[str, re.Pattern] = {}


def compile_regex(pattern: str, case_sensitive: bool = False) -> re.Pattern:
    key = f"{int(case_sensitive)}:{pattern}"
    if key not in _REGEX_CACHE:
        flags = 0 if case_sensitive else re.IGNORECASE
        _REGEX_CACHE[key] = re.compile(pattern, flags)
    return _REGEX_CACHE[key]
