#!/usr/bin/env python3
"""Fetch Seller Education Hub article JSON via the browser session.

Why this exists
---------------
`seller.shopee.com.br/edu/article/<id>` is a SPA. Its content comes from
`/help/api/v3/article/detail/?article_id=<id>`, and that request carries an
`SPC_CDS` session token that a plain HTTP client does not obtain (a direct
request answers `{"msg":"not allowed language","code":1008}`).

So we let headless Chromium load the page (it acquires the token), then issue
the API request *from inside the page context* and hand back the JSON.

Usage:
    python3 tools/fetch_edu_article.py <article_id> <out_json> [--wait SEC]
    python3 tools/fetch_edu_article.py --batch batch.json
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
PORT = 9335
PAGE_BASE = "https://seller.shopee.com.br/edu/article/"

HOOK = """
window.__CAP__ = [];
(function(){
  const of = window.fetch;
  window.fetch = function(...a){
    const u = (typeof a[0]==='string')?a[0]:(a[0]&&a[0].url);
    return of.apply(this,a).then(r=>{
      try{ r.clone().text().then(t=>{ window.__CAP__.push({url:u, body:t}); }); }catch(e){}
      return r;
    });
  };
  const oo = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(m,u,...rest){ this.__u=u; return oo.call(this,m,u,...rest); };
  const os = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function(...a){
    this.addEventListener('load', ()=>{ try{ window.__CAP__.push({url:this.__u, body:this.responseText}); }catch(e){} });
    return os.apply(this,a);
  };
})();
"""


def _cdp_session(url, wait):
    """Load `url` in headless Chromium, install the hook, return a CDP client."""
    with tempfile.TemporaryDirectory(prefix="cr_", dir="/tmp") as profile:
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--disable-dev-shm-usage", "--no-first-run",
               f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
               "--window-size=1440,2400", "about:blank"]
        env = dict(os.environ); env["TMPDIR"] = "/tmp"; env.pop("LD_LIBRARY_PATH", None)
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        ws_url = None
        for _ in range(80):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=3) as r:
                    for t in json.loads(r.read().decode()):
                        if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                            ws_url = t["webSocketDebuggerUrl"]; break
                if ws_url:
                    break
            except Exception:
                pass
        if not ws_url:
            proc.kill()
            raise RuntimeError("could not reach chromium devtools")
        sock, buf = ws_connect(ws_url)
        cdp = CDP(sock); cdp.buf = buf
        cdp.call("Page.enable"); cdp.call("Runtime.enable")
        cdp.call("Page.addScriptToEvaluateOnNewDocument", {"source": HOOK})
        cdp.call("Page.navigate", {"url": url})
        time.sleep(wait)
        return proc, cdp


def fetch_article(article_id, wait=10.0):
    url = PAGE_BASE + str(article_id)
    proc, cdp = _cdp_session(url, wait)
    try:
        # 1) the SPA's own request (captured by the hook)
        r = cdp.call("Runtime.evaluate", {
            "expression": "JSON.stringify(window.__CAP__||[])", "returnByValue": True})
        cap = json.loads(r.get("result", {}).get("value") or "[]")
        for c in cap:
            if "article/detail" in (c.get("url") or ""):
                return json.loads(c["body"]), "spa-fetch"

        # 2) fall back: issue the request from page context (token present)
        expr = (
            "fetch('/help/api/v3/article/detail/?article_id=%s',{credentials:'include'})"
            ".then(r=>r.text()).then(t=>t)" % article_id
        )
        r = cdp.call("Runtime.evaluate", {
            "expression": expr, "returnByValue": True, "awaitPromise": True})
        body = r.get("result", {}).get("value")
        if body:
            try:
                return json.loads(body), "page-fetch"
            except json.JSONDecodeError:
                return {"raw": body}, "page-fetch-raw"
        return None, "empty"
    finally:
        cdp.close()
        proc.terminate()
        try: proc.wait(timeout=8)
        except Exception: proc.kill()


def main():
    args = sys.argv[1:]
    if args and args[0] == "--batch":
        with open(args[1], encoding="utf-8") as f:
            batch = json.load(f)
        wait = float(batch.get("wait", 10.0))
        for item in batch["items"]:
            out = item["out"]
            if os.path.exists(out) and os.path.getsize(out) > 500:
                print(f"skip   {item.get('slug', out)} (cached)")
                continue
            try:
                data, how = fetch_article(item["article_id"], wait=wait)
                if data is None:
                    print(f"EMPTY  {item.get('slug', out)}")
                    continue
                os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
                with open(out, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"ok     {item.get('slug', out)}  via={how}  bytes={os.path.getsize(out)}")
            except Exception as e:
                print(f"ERR    {item.get('slug', out)}  {type(e).__name__}: {e}")
        return
    aid, out = args[0], args[1]
    wait = float(args[args.index("--wait") + 1]) if "--wait" in args else 10.0
    data, how = fetch_article(aid, wait=wait)
    if data is None:
        print("empty response")
        return
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"ok {out} via={how} bytes={os.path.getsize(out)}")


if __name__ == "__main__":
    main()
