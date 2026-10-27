#!/usr/bin/env python3
"""Render a page in headless Chromium and dump its visible text (via CDP).

Robustness notes (learned the hard way):
  * Chromium aborts with "Socket path too long" unless TMPDIR and the
    user-data-dir are short -> we pin both under /tmp.
  * `/json/list` can report a stale URL for a page target. We therefore
    ALWAYS verify `location.href` after navigating, and we navigate
    explicitly with Page.navigate on a known target instead of relying on
    the command-line URL.
  * The Seller Education Hub renders its article body into the DOM only
    after its `/help/api/v3/article/detail/` XHR resolves, so we wait and
    poll until the body text stops growing.

Usage:
    python3 tools/render_page.py <url> <out_txt> [--wait SEC] [--no-scroll]
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_client import CDP, ws_connect  # noqa: E402

CHROME = "/usr/bin/chromium"


def _find_target(port, timeout=40.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=3) as r:
                for t in json.loads(r.read().decode()):
                    if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                        return t["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(0.4)
    raise RuntimeError("no chromium page target")


def render(url, wait=12.0, scroll=True, port=9340, user_agent=None):
    profile = tempfile.mkdtemp(prefix="cr_", dir="/tmp")
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--disable-dev-shm-usage", "--no-first-run", "--no-default-browser-check",
           "--disable-features=DBus,Crashpad",
           f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
           "--window-size=1440,3200", "about:blank"]
    env = dict(os.environ)
    env["TMPDIR"] = "/tmp"
    env.pop("LD_LIBRARY_PATH", None)
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    try:
        ws = _find_target(port)
        sock, buf = ws_connect(ws)
        cdp = CDP(sock)
        cdp.buf = buf
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        if user_agent:
            cdp.call("Emulation.setUserAgentOverride", {"userAgent": user_agent})
        cdp.call("Page.navigate", {"url": url})
        time.sleep(2.0)

        # Verify we really landed on the requested URL.
        href = cdp.call("Runtime.evaluate",
                        {"expression": "location.href", "returnByValue": True}
                        ).get("result", {}).get("value", "")
        if not href.startswith(url.split("#")[0][:40]):
            raise RuntimeError(f"navigation failed: href={href!r}")

        # Poll until the body text stabilises (SPA content still loading).
        best, last, stable = "", -1, 0
        deadline = time.time() + wait
        while time.time() < deadline:
            t = cdp.call("Runtime.evaluate", {
                "expression": "document.body ? document.body.innerText : ''",
                "returnByValue": True}).get("result", {}).get("value") or ""
            if len(t) != last:
                best, last, stable = t, len(t), 0
            else:
                stable += 1
                if stable >= 2 and last > 200:
                    break
            time.sleep(1.2)

        if scroll:
            cdp.call("Runtime.evaluate", {
                "expression": """(async()=>{
                    const H=document.body.scrollHeight;
                    for(let y=0;y<H;y+=500){ window.scrollTo(0,y); await new Promise(r=>setTimeout(r,90)); }
                    window.scrollTo(0,0);
                })()""",
                "returnByValue": True, "awaitPromise": True})
            time.sleep(1.5)
            t = cdp.call("Runtime.evaluate", {
                "expression": "document.body ? document.body.innerText : ''",
                "returnByValue": True}).get("result", {}).get("value") or ""
            if len(t) > len(best):
                best = t

        title = cdp.call("Runtime.evaluate",
                         {"expression": "document.title", "returnByValue": True}
                         ).get("result", {}).get("value", "")
        cdp.close()
        return best, title
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


def main():
    args = sys.argv[1:]
    url, out = args[0], args[1]
    wait = float(args[args.index("--wait") + 1]) if "--wait" in args else 12.0
    scroll = "--no-scroll" not in args
    port = int(args[args.index("--port") + 1]) if "--port" in args else 9340
    text, title = render(url, wait=wait, scroll=scroll, port=port)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# title: {title}\n# url: {url}\n\n{text}")
    print(f"ok {out} chars={len(text)} title={title!r}")


if __name__ == "__main__":
    main()
