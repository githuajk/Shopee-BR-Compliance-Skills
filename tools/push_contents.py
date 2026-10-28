#!/usr/bin/env python3
"""把本地目录推送到 Gitea 仓库（本机 Gitea 28.1.0 兼容版）。

## 为什么不用标准做法

本机 Gitea 28.1.0 的 Contents API 有两个限制：

1. `POST /contents/{path}` 对**已存在**的文件一律返回 422
   "repository file already exists" —— 即使 payload 带正确的 `sha`
   （`PUT` 同样被拒）。
2. Git Data API 的 `POST /git/blobs` 端点返回 404（该版本未启用）。

因此更新采用 **删除 → 重建**：

    GET  /contents/{path}        → 取当前 sha
    DELETE /contents/{path}      → 带 sha 删除
    POST /contents/{path}        → 重新创建

`create` 路径是正常的（201），所以这个组合可以可靠地更新任意文件。

**代价**：每个被修改的文件产生 2 个 commit（一条 delete、一条 create），
提交历史会变长。若目标 Gitea 恢复正常 Contents API 更新能力，
应改回单次 PUT。

用法：
    GITEA_TOKEN=... python3 push_contents.py <local_dir> [headline]
    GITEA_HOST / GITEA_OWNER / GITEA_REPO / GITEA_BRANCH 可覆盖。
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = os.environ.get("GITEA_HOST", "http://10.10.10.10:3000")
OWNER = os.environ.get("GITEA_OWNER", "yan")
REPO = os.environ.get("GITEA_REPO", "Shopee-BR-Compliance-Skills")
BRANCH = os.environ.get("GITEA_BRANCH", "main")
TOKEN = os.environ.get("GITEA_TOKEN", "")

SKIP_DIRS = {".git", "__pycache__", "__MACOSX", ".venv", "venv"}
SKIP_FILES = {".DS_Store"}
BLOCKED_SUFFIX = (".token", ".env")


def _headers():
    if not TOKEN:
        sys.exit("GITEA_TOKEN is not set")
    return {"Authorization": f"token {TOKEN}", "Accept": "application/json"}


def api(method: str, path: str, payload=None, retries=3, allow_404=False):
    url = f"{HOST}/api/v1{path}"
    data = None
    headers = _headers()
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    last = None
    for i in range(retries):
        req = urllib.request.Request(url, data=data, method=method)
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404 and allow_404:
                try:
                    return 404, json.loads(e.read().decode())
                except Exception:  # noqa: BLE001
                    return 404, {}
            raise
        except Exception as e:  # transient
            last = e
            time.sleep(2 ** i)
    raise RuntimeError(f"{method} {path} failed after {retries}: {last}")


def quote_path(path: str) -> str:
    """按段百分号编码 —— 整串编码会破坏含 CJK 的路径。"""
    return "/".join(urllib.parse.quote(s, safe="") for s in path.split("/"))


def collect_files(root: str):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn in SKIP_FILES or fn.endswith(BLOCKED_SUFFIX):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out.append((full, rel))
    return sorted(out, key=lambda x: x[1])


def remote_sha(rel: str):
    st, data = api("GET",
                   f"/repos/{OWNER}/{REPO}/contents/{quote_path(rel)}?ref={BRANCH}",
                   allow_404=True)
    return data.get("sha") if st == 200 else None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    local_dir = os.path.abspath(sys.argv[1])
    headline = sys.argv[2] if len(sys.argv) > 2 else "chore: sync"
    if not os.path.isdir(local_dir):
        sys.exit(f"not a directory: {local_dir}")

    print(f"host   : {HOST}")
    print(f"repo   : {OWNER}/{REPO} (branch={BRANCH})")
    print(f"source : {local_dir}")

    files = collect_files(local_dir)
    total = len(files)
    print(f"files  : {total}\n")

    created = updated = skipped = 0
    failed = []

    for i, (full, rel) in enumerate(files, 1):
        with open(full, "rb") as f:
            body = f.read()
        q = quote_path(rel)
        content = base64.b64encode(body).decode()

        try:
            sha = remote_sha(rel)
            if sha is None:
                st, res = api("POST", f"/repos/{OWNER}/{REPO}/contents/{q}",
                              {"content": content, "branch": BRANCH,
                               "message": f"{headline} ({i}/{total}): {rel}"})
                if st not in (200, 201):
                    raise RuntimeError(f"HTTP {st} {res}")
                created += 1
                action = "create"
            else:
                # 本机 Gitea 拒绝带 sha 的更新 → 删除后重建
                st, res = api("DELETE", f"/repos/{OWNER}/{REPO}/contents/{q}",
                              {"sha": sha, "branch": BRANCH,
                               "message": f"{headline} ({i}/{total}): {rel} [replace]"})
                if st not in (200, 204):
                    raise RuntimeError(f"delete HTTP {st} {res}")
                st, res = api("POST", f"/repos/{OWNER}/{REPO}/contents/{q}",
                              {"content": content, "branch": BRANCH,
                               "message": f"{headline} ({i}/{total}): {rel}"})
                if st not in (200, 201):
                    raise RuntimeError(f"recreate HTTP {st} {res}")
                updated += 1
                action = "replace"
            print(f"  [{i:3d}/{total}] {action:8} {rel} ({len(body)} bytes)")
        except Exception as e:  # noqa: BLE001
            failed.append((rel, str(e)[:160]))
            print(f"  [{i:3d}/{total}] FAIL     {rel}: {str(e)[:120]}")

    print(f"\ncreated : {created}")
    print(f"replaced: {updated}")
    print(f"total   : {created + updated}/{total}")
    if failed:
        print(f"failed  : {len(failed)}")
        for rel, err in failed:
            print(f"  - {rel}: {err}")
        sys.exit(1)
    print("now verify by reading files back off the server")


if __name__ == "__main__":
    main()
