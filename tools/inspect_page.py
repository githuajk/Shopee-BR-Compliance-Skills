#!/usr/bin/env python3
"""Inspect a rendered page: dump outerHTML, shadow roots, and any API responses.

Debug helper for the research acquisition step — not part of the audit engine.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_page import CDP, ws_connect  # noqa: E402
import subprocess
import tempfile
import time
import urllib.request

CHROME = "/usr/bin/chromium"


def main():
    url = sys.argv[1]
    wait = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
    with tempfile.TemporaryDirectory(prefix="cr_", dir="/tmp") as profile:
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--disable-dev-shm-usage", "--no-first-run",
               f"--remote-debugging-port=9333", f"--user-data-dir={profile}",
               "--window-size=1440,2400", url]
        env = dict(os.environ); env["TMPDIR"] = "/tmp"; env.pop("LD_LIBRARY_PATH", None)
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        try:
            ws_url = None
            for _ in range(80):
                time.sleep(0.5)
                try:
                    with urllib.request.urlopen("http://127.0.0.1:9333/json/list", timeout=3) as r:
                        for t in json.loads(r.read().decode()):
                            if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                                ws_url = t["webSocketDebuggerUrl"]; break
                    if ws_url: break
                except Exception:
                    pass
            sock, buf = ws_connect(ws_url)
            cdp = CDP(sock); cdp.buf = buf
            cdp.call("Page.enable"); cdp.call("Runtime.enable"); cdp.call("Network.enable")
            time.sleep(wait)

            for expr, label in [
                ("location.href", "URL"),
                ("document.readyState", "readyState"),
                ("document.documentElement.outerHTML.length", "outerHTML len"),
                ("document.body ? document.body.innerHTML.length : -1", "body innerHTML len"),
                ("document.body ? document.body.innerText.length : -1", "body innerText len"),
                ("document.querySelectorAll('*').length", "element count"),
                ("Array.from(document.querySelectorAll('*')).slice(0,40).map(e=>e.tagName+'#'+e.id+'.'+(e.className&&e.className.baseVal===undefined?String(e.className):'')).join('\\n')", "first 40 tags"),
                ("JSON.stringify(Object.keys(window).filter(k=>/shop|Shop|__/.test(k)).slice(0,30))", "window keys"),
            ]:
                r = cdp.call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
                v = r.get("result", {}).get("value")
                print(f"--- {label}: {str(v)[:1500]}")

            # network requests log
            r = cdp.call("Runtime.evaluate", {
                "expression": "performance.getEntriesByType('resource').filter(e=>e.name.includes('/api/')).map(e=>e.name).slice(0,40).join('\\n')",
                "returnByValue": True})
            print("--- api resources:\n" + str(r.get("result", {}).get("value"))[:2500])
            cdp.close()
        finally:
            proc.terminate()
            try: proc.wait(timeout=8)
            except Exception: proc.kill()


if __name__ == "__main__":
    main()
