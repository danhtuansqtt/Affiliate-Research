"""Điều khiển nhẹ trình duyệt Chrome/Edge của chính app qua Chrome DevTools Protocol (chỉ dùng thư viện chuẩn).

App mở trình duyệt với hồ sơ riêng (thư mục profile của app) và cổng gỡ lỗi chỉ lắng nghe ở 127.0.0.1.
Người dùng đăng nhập Google và mở file Sheet ngay trong cửa sổ đó; app chỉ làm hai việc:
  1. liệt kê các tab đang mở (để biết người dùng đã chọn file nào),
  2. lấy cookie phiên Google của hồ sơ này để tải bản xuất của Sheet bằng chính quyền của người dùng.
App không đọc, không lưu mật khẩu; cookie chỉ nằm trong bộ nhớ khi gọi.
"""
import base64
import json
import os
import socket
import struct
import urllib.request
from urllib.parse import urlparse


def targets(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=3) as r:
        return json.loads(r.read().decode("utf-8"))


def browser_ws(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=3) as r:
        return json.loads(r.read().decode("utf-8"))["webSocketDebuggerUrl"]


def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Trình duyệt đóng kết nối.")
        buf += chunk
    return buf


def _read_message(sock):
    """Đọc một thông điệp WebSocket (gộp các mảnh, trả lời ping)."""
    data, opcode0 = b"", None
    while True:
        b1, b2 = _recv_exact(sock, 2)
        fin, opcode, ln = b1 & 0x80, b1 & 0x0F, b2 & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", _recv_exact(sock, 2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", _recv_exact(sock, 8))[0]
        payload = _recv_exact(sock, ln)  # máy chủ không che dữ liệu
        if opcode == 0x9:  # ping -> pong
            _send(sock, payload, 0xA)
            continue
        if opcode == 0x8:
            raise ConnectionError("Trình duyệt đóng kết nối.")
        if opcode in (0x1, 0x2):
            opcode0 = opcode
        data += payload
        if fin:
            return data


def _send(sock, payload, opcode=0x1):
    head = bytes([0x80 | opcode])
    ln = len(payload)
    if ln < 126:
        head += bytes([0x80 | ln])
    elif ln < 65536:
        head += bytes([0x80 | 126]) + struct.pack(">H", ln)
    else:
        head += bytes([0x80 | 127]) + struct.pack(">Q", ln)
    mask = os.urandom(4)
    sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))


def call(ws_url, method, params=None, timeout=15):
    """Gọi một lệnh CDP và trả về result."""
    u = urlparse(ws_url)
    sock = socket.create_connection((u.hostname, u.port), timeout=timeout)
    try:
        key = base64.b64encode(os.urandom(16)).decode()
        sock.sendall((f"GET {u.path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\n"
                      f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += _recv_exact(sock, 1)
        if b" 101 " not in resp.split(b"\r\n")[0]:
            raise ConnectionError("Trình duyệt từ chối kết nối điều khiển.")
        _send(sock, json.dumps({"id": 1, "method": method, "params": params or {}}).encode())
        while True:
            msg = json.loads(_read_message(sock).decode("utf-8"))
            if msg.get("id") == 1:
                if "error" in msg:
                    raise RuntimeError(msg["error"].get("message", "lỗi CDP"))
                return msg.get("result", {})
    finally:
        sock.close()


def google_cookies(port):
    """Cookie của hồ sơ trình duyệt thuộc miền google.com / googleusercontent.com (có cả HttpOnly)."""
    res = call(browser_ws(port), "Storage.getCookies", timeout=15)
    ok = ("google.com", "googleusercontent.com")
    return [c for c in res.get("cookies", []) if c.get("domain", "").lstrip(".").endswith(ok)]


def is_signed_in(cookies):
    names = {c["name"] for c in cookies}
    return "SID" in names or "__Secure-1PSID" in names


def cookie_header(cookies, host):
    """Chuỗi Cookie cho các cookie áp dụng cho host (vd docs.google.com)."""
    parts = []
    for c in cookies:
        d = c["domain"].lstrip(".")
        if host == d or host.endswith("." + d):
            parts.append(f"{c['name']}={c['value']}")
    return "; ".join(parts)


def set_window_state(port, page_url_prefix, state, prev=None):
    """Phóng to ('maximized') hoặc trả về cỡ cũ ('normal') cho cửa sổ chứa trang của app (vẫn là cửa sổ có viền).
    Trả về trạng thái cửa sổ trước khi đổi, để lần sau khôi phục đúng."""
    tid = next((t["id"] for t in targets(port) if t.get("type") == "page" and t.get("url", "").startswith(page_url_prefix)), None)
    if not tid:
        raise RuntimeError("Không tìm thấy cửa sổ của app.")
    ws = browser_ws(port)
    info = call(ws, "Browser.getWindowForTarget", {"targetId": tid})
    before = info.get("bounds", {}).get("windowState", "normal")
    call(ws, "Browser.setWindowBounds", {"windowId": info["windowId"], "bounds": {"windowState": state}})
    return before
