#!/usr/bin/env python3
"""把本地目录推送到 Gitea 仓库（支持更新已存在文件）。

为什么不用 Contents API 更新：
    本机 Gitea 28.1.0 的 `POST /contents/{path}` 对**已存在**的文件一律返回
    422 "repository file already exists"，即使 payload 带正确的 `sha`
    （PUT 同样被拒）。create 路径正常（201）。

    因此更新走 **Git Data API**：
        blobs → trees(base_tree) → commits(parents) → refs(PATCH)
    这是 Gitea/GitHub 都支持的底层接口，语义等价于一次普通提交。

用法：
    GITEA_TOKEN=... python3 push_gitdata.py <local_dir> [headline]
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
    """发起 API 调用。返回 (status, body)。

    allow_404=True 时把 404 作为正常结果返回（而不是抛异常），
    供「分支可能不存在」这类可选查询使用。
    """
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


def head_commit() -> str:
    """当前分支 HEAD 的 commit sha。

    注意：Gitea 28.x 的 `GET /git/refs/heads/{branch}` 返回**数组**
    （即使只匹配一个），旧版返回对象 —— 两种都要兼容。
    """
    st, refs = api("GET", f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}",
                   allow_404=True)
    if st == 404:
        # 分支不存在：用 commits 列表取最新一个
        st, cms = api("GET", f"/repos/{OWNER}/{REPO}/git/commits?sha={BRANCH}&limit=1")
        if st != 200 or not cms:
            raise RuntimeError(f"cannot resolve HEAD for branch {BRANCH}")
        return cms[0]["sha"]
    ref = refs[0] if isinstance(refs, list) else refs
    return ref["object"]["sha"]


def head_tree() -> str:
    st, tr = api("GET", f"/repos/{OWNER}/{REPO}/git/trees/{BRANCH}")
    if st != 200:
        raise RuntimeError(f"cannot resolve tree for branch {BRANCH}: {st} {tr}")
    return tr["sha"]


def make_blob(body: bytes) -> str:
    st, blob = api("POST", f"/repos/{OWNER}/{REPO}/git/blobs",
                   {"content": base64.b64encode(body).decode(), "encoding": "base64"})
    if st not in (201, 200):
        raise RuntimeError(f"blob failed: {st} {blob}")
    return blob["sha"]


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

    parent = head_commit()
    base_tree = head_tree()
    print(f"parent : {parent[:12]}")
    print(f"tree   : {base_tree[:12]}\n")

    # 1) 批量创建 blob
    entries = []
    for i, (full, rel) in enumerate(files, 1):
        with open(full, "rb") as f:
            body = f.read()
        sha = make_blob(body)
        entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": sha})
        if i % 20 == 0 or i == total:
            print(f"  blob {i:3d}/{total}")

    # 2) 创建新 tree（基于当前 tree）
    st, tree = api("POST", f"/repos/{OWNER}/{REPO}/git/trees",
                   {"base_tree": base_tree, "tree": entries})
    if st not in (201, 200):
        sys.exit(f"tree failed: {st} {tree}")
    new_tree = tree["sha"]
    print(f"\nnew tree: {new_tree[:12]}")

    # 3) 创建 commit
    st, nc = api("POST", f"/repos/{OWNER}/{REPO}/git/commits",
                 {"message": f"{headline} — {total} files", "tree": new_tree,
                  "parents": [parent]})
    if st not in (201, 200):
        sys.exit(f"commit failed: {st} {nc}")
    new_commit = nc["sha"]
    print(f"commit  : {new_commit[:12]}")

    # 4) 推进 ref
    st, res = api("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}",
                  {"sha": new_commit, "force": False})
    if st not in (200, 201):
        sys.exit(f"ref update failed: {st} {res}")
    print(f"ref     : {res.get('object', {}).get('sha', '')[:12]}")

    print(f"\ndone   : {total}/{total} files committed in one commit")
    print("now verify by reading files back off the server")


if __name__ == "__main__":
    main()
