#!/usr/bin/env python3
"""Fetch primary source pages (server-rendered) into raw HTML + extracted text.

Input : a JSON list of source descriptors (see research/sources.json).
Output: raw HTML under research/raw/<slug>.html
        extracted plain text under research/raw/<slug>.txt
Nothing here mutates project state; it is a research acquisition step.
"""
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "research", "raw")


def fetch(url, timeout=45):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        },
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        raw = resp.read()
        ctype = resp.headers.get("Content-Type", "")
        return resp.status, ctype, raw


def to_text(raw):
    try:
        h = raw.decode("utf-8")
    except UnicodeDecodeError:
        h = raw.decode("latin-1", "replace")
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", h)
    body = re.sub(r"(?i)<br\s*/?>", "\n", body)
    body = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|section)>", "\n", body)
    body = re.sub(r"(?i)<li[^>]*>", "\n- ", body)
    txt = re.sub(r"(?s)<[^>]+>", " ", body)
    txt = txt.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
    txt = txt.replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
    txt = re.sub(r"&[a-zA-Z#0-9]+;", " ", txt)
    lines = []
    for ln in txt.split("\n"):
        ln = re.sub(r"[ \t\u00a0]+", " ", ln).strip()
        if len(ln) > 1:
            lines.append(ln)
    out, prev = [], None
    for ln in lines:
        if ln != prev:
            out.append(ln)
        prev = ln
    return "\n".join(out)


def main():
    os.makedirs(RAW, exist_ok=True)
    src_file = os.path.join(ROOT, "research", "sources.json")
    with open(src_file, encoding="utf-8") as f:
        sources = json.load(f)
    only = sys.argv[1:] or None
    report = []
    for s in sources:
        slug = s["slug"]
        if only and slug not in only:
            continue
        html_path = os.path.join(RAW, slug + ".html")
        txt_path = os.path.join(RAW, slug + ".txt")
        if os.path.exists(txt_path) and os.path.getsize(txt_path) > 200:
            print(f"skip   {slug} (cached)")
            report.append({"slug": slug, "status": "cached", "chars": os.path.getsize(txt_path)})
            continue
        try:
            status, ctype, raw = fetch(s["url"])
            with open(html_path, "wb") as f:
                f.write(raw)
            text = to_text(raw)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"ok     {slug}  http={status}  bytes={len(raw)}  textchars={len(text)}")
            report.append({"slug": slug, "status": "ok", "http": status, "text_chars": len(text)})
        except urllib.error.HTTPError as e:
            print(f"HTTP{e.code} {slug}  {s['url']}")
            report.append({"slug": slug, "status": f"http_{e.code}", "url": s["url"]})
        except Exception as e:
            print(f"ERR    {slug}  {type(e).__name__}: {e}")
            report.append({"slug": slug, "status": f"error_{type(e).__name__}", "detail": str(e)})
        time.sleep(1.0)
    with open(os.path.join(RAW, "_fetch_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
