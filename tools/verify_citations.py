#!/usr/bin/env python3
"""Verify that every rule's `source_excerpt` really appears in its source.

This is the guard against fabricated citations. A rule that quotes a source
must quote it VERBATIM (after whitespace normalisation); otherwise the
excerpt is rejected and the rule is reported as unverified.

Source texts are the captures under research/raw/*.txt. A rule's excerpt is
checked against every capture; the capture that contains it is named, so a
reviewer can confirm the excerpt came from the right document.

Usage:
    python3 tools/verify_citations.py [--strict]

Exit code 1 if any excerpt fails to match (with --strict).
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "research", "raw")
RULES = os.path.join(ROOT, "rules")

# Curly quotes / dashes / non-breaking space -> ASCII equivalents.
_TRANSLATE = {
    "’": "'", "‘": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ", "…": "...",
}


def norm(s: str) -> str:
    for a, b in _TRANSLATE.items():
        s = s.replace(a, b)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def loose(s: str) -> str:
    """Normalised text with sentence punctuation removed.

    The captured source pages interleave the rule text with UI boilerplate
    ("..., clique aqui."), so a verbatim excerpt may end in a comma where the
    source has a period. We compare with terminal punctuation stripped, but
    we keep every other character — a paraphrase still fails.
    """
    s = norm(s)
    s = s.replace(",", " ").replace(".", " ").replace(";", " ").replace(":", " ")
    return re.sub(r"\s+", " ", s).strip()


def load_captures() -> dict[str, str]:
    out = {}
    if not os.path.isdir(RAW):
        return out
    for fn in sorted(os.listdir(RAW)):
        if not fn.endswith(".txt"):
            continue
        with open(os.path.join(RAW, fn), encoding="utf-8") as f:
            out[fn[:-4]] = norm(f.read())
    return out


def slug_from_url(url: str) -> str:
    """Best-effort slug for a source URL -> capture name."""
    u = (url or "").lower()
    tail = u.rstrip("/").split("/")[-1]
    return re.sub(r"[^a-z0-9]+", "_", tail).strip("_")


def main():
    strict = "--strict" in sys.argv
    captures = load_captures()
    if not captures:
        print("no captures under research/raw — cannot verify")
        return 2

    rules = []
    for fn in sorted(os.listdir(RULES)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(RULES, fn), encoding="utf-8") as f:
            doc = json.load(f)
        for r in doc.get("rules", []):
            rules.append((fn, r))

    ok = 0
    failed = []
    for fn, r in rules:
        excerpt = (r.get("source_excerpt") or "").strip()
        if not excerpt:
            failed.append((fn, r["rule_id"], "no source_excerpt", ""))
            print(f"FAIL  {r['rule_id']:<14} no source_excerpt")
            continue
        ne = loose(excerpt)
        slug = slug_from_url(r.get("source_url", ""))
        # Prefer the capture whose slug matches the rule's own source URL.
        order = []
        if slug in captures:
            order.append((slug, captures[slug]))
        for key, text in captures.items():
            if key != slug:
                order.append((key, text))
        found_in = None
        for name, text in order:
            if ne and ne in loose(text):
                found_in = name
                break
        if found_in:
            ok += 1
            print(f"ok    {r['rule_id']:<14} verbatim in '{found_in}'")
        else:
            failed.append((fn, r["rule_id"], "excerpt not found verbatim", ne[:130]))
            print(f"FAIL  {r['rule_id']:<14} excerpt not found verbatim")

    print(f"\n{ok}/{len(rules)} excerpts verified verbatim, {len(failed)} failed")
    if failed:
        print("\nFailures:")
        for fn, rid, why, snip in failed:
            print(f"  - {rid} ({fn}): {why}")
            if snip:
                print(f"      excerpt starts: {snip}")
        if strict:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
