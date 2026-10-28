#!/usr/bin/env python3
"""Dump the rendered text of a page, with a wait/scroll loop, to a file.

Usage: python3 tools/dump_page_text.py <url> <out_txt> [--wait 15] [--scroll]
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
PORT = int(os.environ.get("DUMP_PORT", "9337"))


def dump(url, wait=15.0, scroll=True):
    profile = tempfile.mkdtemp(prefix="cr_", dir="/tmp")
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--disable-dev-shm-usage", "--no-first-run",
           f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
           "--window-size=1440,3200", url]
    env = dict(os.environ); env["TMPDIR"] = "/tmp"; env.pop("LD_LIBRARY_PATH", None)
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    try:
        ws = None
        for _ in range(80):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=3) as r:
                    targets = json.loads(r.read().decode())
                # prefer the page whose URL matches what we asked for
                cands = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
                for t in cands:
                    if t.get("url", "").startswith(url[:60]):
                        ws = t["webSocketDebuggerUrl"]; break
                if not ws and cands:
                    ws = cands[0]["webSocketDebuggerUrl"]
                if ws: break
            except Exception:
                pass
        if not ws:
            raise RuntimeError("no devtools target")
        sock, buf = ws_connect(ws)
        cdp = CDP(sock); cdp.buf = buf
        cdp.call("Page.enable"); cdp.call("Runtime.enable")
        time.sleep(wait)
        if scroll:
            # force lazy content: scroll to bottom, then back up
            cdp.call("Runtime.evaluate", {
                "expression": """(async()=>{
                    const H=document.body.scrollHeight;
                    for(let y=0;y<H;y+=600){ window.scrollTo(0,y); await new Promise(r=>setTimeout(r,120)); }
                    window.scrollTo(0,0);
                })()""",
                "returnByValue": True, "awaitPromise": True})
            time.sleep(3)
        r = cdp.call("Runtime.evaluate", {
            "expression": "document.body ? document.body.innerText : ''", "returnByValue": True})
        text = r.get("result", {}).get("value") or ""
        t = cdp.call("Runtime.evaluate", {"expression": "document.title", "returnByValue": True})
        title = t.get("result", {}).get("value") or ""
        cdp.close()
        return text, title
    finally:
        proc.terminate()
        try: proc.wait(timeout=8)
        except Exception: proc.kill()
        import shutil
        shutil.rmtree(profile, ignore_errors=True)


def main():
    args = sys.argv[1:]
    url, out = args[0], args[1]
    wait = float(args[args.index("--wait") + 1]) if "--wait" in args else 15.0
    scroll = "--no-scroll" not in args
    text, title = dump(url, wait=wait, scroll=scroll)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# title: {title}\n# url: {url}\n\n{text}")
    print(f"ok {out} chars={len(text)} title={title!r}")


if __name__ == "__main__":
    main()
