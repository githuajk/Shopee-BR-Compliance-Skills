#!/usr/bin/env python3
"""Batch-render Seller Education Hub articles (SPA) to text files.

Each article lives at https://seller.shopee.com.br/edu/article/<id>.
The site is a client-side SPA, so a plain HTTP fetch returns an empty shell;
we render each page in headless Chromium and dump the visible text.

Usage: python3 tools/fetch_edu_articles.py batch.json
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_page import render  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        batch = json.load(f)
    wait = float(batch.get("wait", 22.0))
    port = int(batch.get("port", 9350))
    results = []
    for item in batch["items"]:
        slug = item.get("slug", str(item["article_id"]))
        out = os.path.join(ROOT, item["out"]) if not os.path.isabs(item["out"]) else item["out"]
        if os.path.exists(out) and os.path.getsize(out) > 800:
            print(f"skip   {slug} (cached)")
            results.append({"slug": slug, "status": "cached", "chars": os.path.getsize(out)})
            continue
        url = f"https://seller.shopee.com.br/edu/article/{item['article_id']}"
        try:
            text, title = render(url, wait=wait, port=port)
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
            with open(out, "w", encoding="utf-8") as f:
                f.write(f"# title: {title}\n# url: {url}\n\n{text}")
            print(f"ok     {slug}  chars={len(text)}  title={title[:70]!r}")
            results.append({"slug": slug, "status": "ok", "chars": len(text), "title": title})
        except Exception as e:
            print(f"ERR    {slug}  {type(e).__name__}: {e}")
            results.append({"slug": slug, "status": f"error_{type(e).__name__}", "detail": str(e)})
        time.sleep(2)
    rp = os.path.join(ROOT, "research", "raw", "_edu_fetch_report.json")
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
