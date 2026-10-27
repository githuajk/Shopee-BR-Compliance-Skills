#!/usr/bin/env python3
"""Capture the JSON body of a specific XHR/fetch response from a rendered page.

This is how the Seller Education Hub articles are read: their content lives in
`/help/api/v3/article/detail/?article_id=<id>` responses, and the SPA requests
carry an SPC_CDS session token that a plain HTTP client does not get.

Usage: python3 tools/capture_api.py <page_url> <url_substring> [out_json] [wait]
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_page import CDP, ws_connect  # noqa: E402

CHROME = "/usr/bin/chromium"
PORT = 9334


def main():
    page_url = sys.argv[1]
    needle = sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else "/tmp/captured.json"
    wait = float(sys.argv[4]) if len(sys.argv) > 4 else 12.0

    with tempfile.TemporaryDirectory(prefix="cr_", dir="/tmp") as profile:
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--disable-dev-shm-usage", "--no-first-run",
               f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
               "--window-size=1440,2400", page_url]
        env = dict(os.environ); env["TMPDIR"] = "/tmp"; env.pop("LD_LIBRARY_PATH", None)
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        try:
            ws_url = None
            for _ in range(80):
                time.sleep(0.5)
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=3) as r:
                        for t in json.loads(r.read().decode()):
                            if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                                ws_url = t["webSocketDebuggerUrl"]; break
                    if ws_url: break
                except Exception:
                    pass
            sock, buf = ws_connect(ws_url)
            cdp = CDP(sock); cdp.buf = buf
            cdp.call("Page.enable"); cdp.call("Runtime.enable")
            cdp.call("Network.enable")
            # Install the fetch/XHR hook BEFORE the target URL is loaded, so the
            # SPA's very first /help/api/v3/article/detail call is captured.
            cdp.call("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                window.__CAP__ = [];
                const of = window.fetch;
                window.fetch = function(...a){
                  const u = (typeof a[0]==='string')?a[0]:(a[0]&&a[0].url);
                  return of.apply(this,a).then(r=>{
                    try{ r.clone().text().then(t=>{ window.__CAP__.push({url:u, body:t}); }); }catch(e){}
                    return r;
                  });
                };
                const oo = XMLHttpRequest.prototype.open;
                XMLHttpRequest.prototype.open = function(m,u,...rest){
                  this.__u = u; return oo.call(this,m,u,...rest);
                };
                const os = XMLHttpRequest.prototype.send;
                XMLHttpRequest.prototype.send = function(...a){
                  this.addEventListener('load', ()=>{
                    try{ window.__CAP__.push({url:this.__u, body:this.responseText}); }catch(e){}
                  });
                  return os.apply(this,a);
                };
                """})
            cdp.call("Page.reload", {"ignoreCache": True})
            time.sleep(wait)
            # The SPA may fetch the article lazily (route change / scroll), so
            # also force a direct fetch of the API endpoint from page context,
            # where the SPC_CDS token already exists.
            if "article/detail" not in needle:
                r = cdp.call("Runtime.evaluate", {
                    "expression": "location.reload()", "returnByValue": True})
            time.sleep(2)
            r = cdp.call("Runtime.evaluate", {
                "expression": "JSON.stringify(window.__CAP__||[])",
                "returnByValue": True})
            cap = json.loads(r.get("result", {}).get("value") or "[]")
            hits = [c for c in cap if needle in (c.get("url") or "")]
            print(f"captured {len(cap)} responses, {len(hits)} matching {needle!r}")
            if hits:
                os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
                with open(out, "w", encoding="utf-8") as f:
                    json.dump(hits, f, ensure_ascii=False, indent=2)
                print("wrote", out, "size", os.path.getsize(out))
                for h in hits[:3]:
                    print("  url:", (h.get("url") or "")[:160])
                    print("  body head:", (h.get("body") or "")[:300].replace("\n", " "))
            else:
                for c in cap[:25]:
                    print("  seen:", (c.get("url") or "")[:150])
            cdp.close()
        finally:
            proc.terminate()
            try: proc.wait(timeout=8)
            except Exception: proc.kill()


if __name__ == "__main__":
    main()
