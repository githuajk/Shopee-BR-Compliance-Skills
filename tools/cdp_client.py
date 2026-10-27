#!/usr/bin/env python3
"""Minimal Chrome DevTools Protocol client (stdlib only).

Provides:
  * ws_connect(url)  — raw RFC6455 websocket handshake (text frames only)
  * CDP              — request/response wrapper over CDP

No third-party dependencies: the Hermes runtime's Python has no `websockets`
package and pip installs are not always possible offline.

Frame handling supports the lengths CDP actually uses (small JSON messages),
plus ping/pong and close frames.
"""
import base64
import json
import os
import socket
import struct
import time


def ws_connect(url, timeout=20):
    """Open a websocket to `ws://host:port/path`. Returns (socket, leftover)."""
    assert url.startswith("ws://"), "only ws:// is supported"
    rest = url[5:]
    hostport, _, path = rest.partition("/")
    host, _, port = hostport.partition(":")
    port = int(port or 80)
    s = socket.create_connection((host, port), timeout=timeout)
    s.settimeout(timeout)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    s.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            raise RuntimeError("websocket handshake failed: connection closed")
        buf += chunk
    head, _, rest_bytes = buf.partition(b"\r\n\r\n")
    if b" 101 " not in head.split(b"\r\n")[0]:
        raise RuntimeError("websocket upgrade rejected: " + head[:200].decode("latin-1"))
    return s, rest_bytes


def _ws_send(sock, payload, pending=b""):
    data = payload.encode("utf-8")
    mask = os.urandom(4)
    n = len(data)
    hdr = bytearray([0x81])  # FIN + text
    if n < 126:
        hdr.append(0x80 | n)
    elif n < 65536:
        hdr.append(0x80 | 126)
        hdr += struct.pack(">H", n)
    else:
        hdr.append(0x80 | 127)
        hdr += struct.pack(">Q", n)
    hdr += mask
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    sock.sendall(bytes(hdr) + masked)
    return pending


def _ws_recv(sock, buf=b"", timeout=60):
    """Read one frame. Returns (text, leftover_buffer)."""
    sock.settimeout(timeout)
    while True:
        while len(buf) < 2:
            chunk = sock.recv(65536)
            if not chunk:
                raise RuntimeError("socket closed")
            buf += chunk
        b0, b1 = buf[0], buf[1]
        opcode = b0 & 0x0F
        masked = b1 & 0x80
        ln = b1 & 0x7F
        off = 2
        if ln == 126:
            while len(buf) < off + 2:
                buf += sock.recv(65536)
            ln = struct.unpack(">H", buf[off:off + 2])[0]
            off += 2
        elif ln == 127:
            while len(buf) < off + 8:
                buf += sock.recv(65536)
            ln = struct.unpack(">Q", buf[off:off + 8])[0]
            off += 8
        if masked:
            while len(buf) < off + 4:
                buf += sock.recv(65536)
            mask = buf[off:off + 4]
            off += 4
        else:
            mask = None
        while len(buf) < off + ln:
            chunk = sock.recv(65536)
            if not chunk:
                raise RuntimeError("socket closed mid-frame")
            buf += chunk
        payload = buf[off:off + ln]
        buf = buf[off + ln:]
        if mask:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        if opcode == 0x8:
            raise RuntimeError("websocket closed by peer")
        if opcode == 0x9:  # ping -> pong
            continue
        if opcode in (0x1, 0x2):
            return payload.decode("utf-8", "replace"), buf


class CDP:
    """Request/response CDP client."""

    def __init__(self, sock, leftover=b""):
        self.sock = sock
        self.buf = leftover
        self.id = 0

    def call(self, method, params=None, timeout=60):
        self.id += 1
        mid = self.id
        msg = {"id": mid, "method": method, "params": params or {}}
        self.buf = _ws_send(self.sock, json.dumps(msg), self.buf)
        deadline = time.time() + timeout
        while time.time() < deadline:
            text, self.buf = _ws_recv(
                self.sock, self.buf, timeout=max(1, int(deadline - time.time())))
            try:
                obj = json.loads(text)
            except json.JSONDecodeError:
                continue
            if obj.get("id") == mid:
                if "error" in obj:
                    raise RuntimeError(f"CDP {method} error: {obj['error']}")
                return obj.get("result", {})
        raise TimeoutError(f"CDP {method} timed out")

    def eval(self, expression, await_promise=False):
        """Evaluate JS and return the raw value."""
        res = self.call("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise,
        })
        return res.get("result", {}).get("value")

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
