#!/usr/bin/env python3
"""Affiliate Viewer: xem dữ liệu Google Sheet Affiliate Research / Advertiser Audit (Windows, macOS, Linux).

Chạy một máy chủ cục bộ (127.0.0.1) rồi mở cửa sổ ứng dụng (Edge/Chrome --app). Chỉ ĐỌC Sheet.
Đăng nhập Google và chọn file ngay trong cửa sổ Google Drive do app mở (hồ sơ trình duyệt riêng của app);
app dùng phiên đăng nhập đó để tải Sheet. Không có mật khẩu hay khóa nào trong mã nguồn. Cấu hình lưu ở config.json
trong thư mục dữ liệu của app (Windows: %APPDATA%\\AffiliateViewer, macOS: ~/Library/Application Support/AffiliateViewer).
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import socket
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cdp
import platform_util as pu
import sheets
import updater
import vip

try:  # macOS (Python cài từ python.org) hay thiếu chứng chỉ gốc: dùng bộ của certifi nếu có
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass

APP_DIR = pu.app_dir()
CONFIG = os.path.join(APP_DIR, "config.json")
CACHE = os.path.join(APP_DIR, "data.json")
VIP_FILE = os.path.join(APP_DIR, "vip.json")
os.makedirs(APP_DIR, exist_ok=True)


def resource(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


STATE = {"last_ping": time.time(), "seen_ping": False, "quit": False}


def parse_sheet_id(text):
    """Nhận link Google Sheet đầy đủ hoặc chính ID; trả '' nếu không nhận ra."""
    m = re.search(r"/d/([A-Za-z0-9_-]{20,})", text or "")
    if m:
        return m.group(1)
    t = (text or "").strip()
    return t if re.fullmatch(r"[A-Za-z0-9_-]{20,}", t) else ""

# ---- Check VIP: chạy nền, kết quả lưu lại để lần sau không phải check lại ----
VIPDB = load_json(VIP_FILE, {})
JOB = {"running": False, "done": 0, "total": 0, "current": "", "stop": False}
JOB_LOCK = threading.Lock()


def vip_worker(items, which):
    try:
        for it in items:
            if JOB["stop"]:
                break
            JOB["current"] = it.get("product", "")
            try:
                VIPDB[it["key"]] = vip.check(it.get("product", ""), it.get("domain", ""), which)
            except Exception as e:  # noqa: BLE001
                VIPDB[it["key"]] = {"at": time.strftime("%Y-%m-%d %H:%M"), "error": str(e)[:120]}
            JOB["done"] += 1
            save_json(VIP_FILE, VIPDB)
    finally:
        JOB["running"] = False
        JOB["current"] = ""


def vip_status():
    return {"job": {k: JOB[k] for k in ("running", "done", "total", "current")}, "results": VIPDB}


BROWSER = {"path": "", "port": 0}
DRIVE_HOME = "https://drive.google.com/drive/home"
SHEET_URL = re.compile(r"https://docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]{20,})")


def cookies():
    if not BROWSER["port"]:
        raise RuntimeError("Không điều khiển được cửa sổ trình duyệt của app (cần Chrome hoặc Edge).")
    return cdp.google_cookies(BROWSER["port"])


def signed_in():
    try:
        return cdp.is_signed_in(cookies())
    except Exception:  # noqa: BLE001
        return False


def current_sheet():
    cfg = load_json(CONFIG, {})
    return {"id": parse_sheet_id(os.environ.get("AV_SHEET_ID") or cfg.get("sheet_id", "")), "name": cfg.get("sheet_name", "")}


def auth_info():
    """need: 'login' (chưa đăng nhập Google), 'sheet' (chưa chọn file), '' (đủ)."""
    ok = signed_in()
    sh = current_sheet()
    return {"signed_in": ok, "sheet": sh, "need": "login" if not ok else ("" if sh["id"] else "sheet")}


def open_drive():
    """Mở Google Drive trong cửa sổ trình duyệt thường của chính hồ sơ app (cùng phiên với cổng điều khiển)."""
    if BROWSER["path"]:
        subprocess.Popen([BROWSER["path"], f"--user-data-dir={os.path.join(APP_DIR, 'profile')}", "--new-window", DRIVE_HOME],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        webbrowser.open(DRIVE_HOME)


def watch():
    """Các tab Google Sheet đang mở trong cửa sổ trình duyệt của app + trạng thái đăng nhập."""
    files, seen, logging_in = [], set(), False
    if BROWSER["port"]:
        try:
            for t in cdp.targets(BROWSER["port"]):
                if t.get("type") != "page":
                    continue
                u = t.get("url", "")
                logging_in = logging_in or u.startswith("https://accounts.google.com")
                m = SHEET_URL.match(u)
                if m and m.group(1) not in seen:
                    seen.add(m.group(1))
                    name = re.sub(r"\s*-\s*Google (Trang tính|Sheets)\s*$", "", t.get("title", "")).strip()
                    files.append({"id": m.group(1), "name": name or "(chưa có tên)"})
        except Exception:  # noqa: BLE001
            pass
    return {"files": files, "logging_in": logging_in, **auth_info()}


def refresh():
    sid = current_sheet()["id"]
    if not sid:
        raise RuntimeError("Chưa chọn file Google Sheet.")
    ck = cookies()
    if not cdp.is_signed_in(ck):
        raise RuntimeError("Chưa đăng nhập Google.")
    data = {"fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"), "tabs": sheets.fetch_all(sid, ck)}
    save_json(CACHE, data)
    return data


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        raw = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/watch":
            return self._send(200, json.dumps(watch(), ensure_ascii=False))
        if self.path in ("/", "/index.html"):
            with open(resource("index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if self.path == "/api/vip":
            return self._send(200, json.dumps(vip_status(), ensure_ascii=False))
        if self.path == "/api/update-check":
            return self._send(200, json.dumps(updater.check(resource), ensure_ascii=False))
        if self.path == "/api/ping":
            STATE["last_ping"], STATE["seen_ping"] = time.time(), True
            return self._send(200, "{}")
        if self.path == "/api/data":
            data = load_json(CACHE, None) if auth_info()["need"] == "" else None
            if data is None:
                try:
                    data = refresh()
                except Exception as e:  # noqa: BLE001
                    return self._send(200, json.dumps({"error": str(e), **auth_info()}, ensure_ascii=False))
            data.update(auth_info())
            return self._send(200, json.dumps(data, ensure_ascii=False))
        self._send(404, "{}")

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}") if n else {}
        if self.path == "/api/refresh":
            try:
                data = refresh()
                data.update(auth_info())
                return self._send(200, json.dumps(data, ensure_ascii=False))
            except Exception as e:  # noqa: BLE001
                return self._send(200, json.dumps({"error": str(e), **auth_info()}, ensure_ascii=False))
        if self.path == "/api/vip/start":
            with JOB_LOCK:
                if JOB["running"]:
                    return self._send(200, json.dumps({"error": "Đang có lượt check chạy."}))
                items = [i for i in body.get("items", []) if i.get("key")][:300]
                which = [w for w in body.get("checks", []) if w in vip.CHECKS] or list(vip.CHECKS)
                JOB.update(running=True, done=0, total=len(items), current="", stop=False)
                threading.Thread(target=vip_worker, args=(items, which), daemon=True).start()
            return self._send(200, json.dumps(vip_status(), ensure_ascii=False))
        if self.path == "/api/vip/stop":
            JOB["stop"] = True
            return self._send(200, "{}")
        if self.path == "/api/set-sheet":
            sid = parse_sheet_id(body.get("value", ""))
            if not sid:
                return self._send(200, json.dumps({"error": "Không nhận ra link hoặc ID Google Sheet."}))
            cfg = load_json(CONFIG, {})
            cfg["sheet_id"] = sid
            cfg["sheet_name"] = str(body.get("name", ""))[:200]
            save_json(CONFIG, cfg)
            try:
                os.remove(CACHE)  # đổi file thì bỏ dữ liệu cũ
            except OSError:
                pass
            return self._send(200, json.dumps({"ok": True}))
        if self.path == "/api/update-install":
            try:
                script = updater.install()
            except Exception as e:  # noqa: BLE001
                return self._send(200, json.dumps({"error": str(e)[:300]}, ensure_ascii=False))
            self._send(200, json.dumps({"ok": True}))
            updater.run_swap(script)
            STATE["quit"] = True
            return
        if self.path == "/api/open-drive":
            open_drive()
            return self._send(200, "{}")
        self._send(404, "{}")


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("AV_PORT", "0"))), Handler)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    browser = "" if os.environ.get("AV_NOBROWSER") else pu.find_browser()
    proc = None
    if browser:
        with socket.socket() as s:  # cổng gỡ lỗi chỉ ở 127.0.0.1, để app đọc tab/cookie của chính cửa sổ này
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        BROWSER.update(path=browser, port=port)
        proc = subprocess.Popen([browser, f"--app={url}", f"--user-data-dir={os.path.join(APP_DIR, 'profile')}",
                                 f"--remote-debugging-port={port}", "--remote-debugging-address=127.0.0.1",
                                 "--window-size=1400,900", "--no-first-run", "--no-default-browser-check"])
    elif not os.environ.get("AV_NOBROWSER"):
        webbrowser.open(url)
    try:
        while True:
            time.sleep(1)
            if proc is not None and proc.poll() is not None:
                break
            if STATE["seen_ping"] and time.time() - STATE["last_ping"] > 20:
                break
            if STATE["quit"]:
                if proc is not None and proc.poll() is None:
                    proc.terminate()
                break
    except KeyboardInterrupt:
        pass
    srv.shutdown()


if __name__ == "__main__":
    main()
