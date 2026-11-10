#!/usr/bin/env python3
"""Affiliate Viewer: xem dữ liệu Google Sheet Affiliate Research / Advertiser Audit (Windows, macOS, Linux).

Chạy một máy chủ cục bộ (127.0.0.1) rồi mở cửa sổ ứng dụng (Edge/Chrome --app). Chỉ ĐỌC Sheet.
Khóa service account và link Google Sheet không nằm trong mã nguồn: người dùng chọn file khóa và dán link Sheet
lần đầu, lưu ở config.json trong thư mục dữ liệu của app (Windows: %APPDATA%\\AffiliateViewer,
macOS: ~/Library/Application Support/AffiliateViewer).
"""
import glob
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import gauth
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
GTOKEN = os.path.join(APP_DIR, "google_token.json")
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


def find_key():
    cfg = load_json(CONFIG, {})
    p = cfg.get("key_path", "")
    if p and os.path.isfile(p):
        return p
    for pat in (os.path.expanduser("~/Downloads/*sa-key*.json"), os.path.expanduser("~/Downloads/affiliate-research*.json"),
                os.path.expanduser("~/.config/affiliate-viewer/*.json"), os.path.expanduser("~/.secrets/*sa-key*.json")):
        hits = glob.glob(pat)
        if hits:
            return hits[0]
    return ""


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


def find_client():
    p = load_json(CONFIG, {}).get("client_path", "")
    if p and os.path.isfile(p):
        return p
    for pat in (os.path.expanduser("~/Downloads/client_secret*.json"), os.path.expanduser("~/.config/affiliate-viewer/client_secret*.json")):
        for hit in sorted(glob.glob(pat), key=os.path.getmtime, reverse=True):
            try:
                gauth.load_client(hit)
            except Exception:  # noqa: BLE001
                continue
            cfg = load_json(CONFIG, {})
            cfg["client_path"] = hit
            save_json(CONFIG, cfg)
            return hit
    return ""


def current_sheet():
    cfg = load_json(CONFIG, {})
    return {"id": parse_sheet_id(os.environ.get("AV_SHEET_ID") or cfg.get("sheet_id", "")), "name": cfg.get("sheet_name", "")}


def need_state():
    """Màn hình cần hiện: 'login' (chưa đăng nhập), 'sheet' (chưa chọn file), '' (đủ)."""
    if not gauth.status(GTOKEN) and not find_key():
        return "login"
    return "" if current_sheet()["id"] else "sheet"


def drive_list(query):
    """Danh sách Google Sheet mà tài khoản đang đăng nhập xem được (của mình + được chia sẻ), mới sửa trước."""
    client = find_client()
    if not client or not gauth.status(GTOKEN):
        raise RuntimeError("Chưa đăng nhập Google.")
    tok = gauth.access_token(client, GTOKEN)
    q = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
    if query.strip():
        q += " and name contains '" + query.strip().replace("\\", "\\\\").replace("'", "\\'") + "'"
    params = {"q": q, "orderBy": "modifiedTime desc", "pageSize": "50", "supportsAllDrives": "true",
              "includeItemsFromAllDrives": "true", "fields": "files(id,name,modifiedTime,owners(displayName))"}
    req = urllib.request.Request("https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode(params),
                                 headers={"Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8")).get("files", [])
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise RuntimeError("Google từ chối liệt kê file (lỗi %d). Kiểm tra đã bật Google Drive API cho dự án, "
                               "và đăng xuất rồi đăng nhập lại để cấp quyền xem danh sách file." % e.code) from None
        raise


def auth_info():
    """Trạng thái hai cách xác thực: đăng nhập Google (ưu tiên) và file khóa service account."""
    return {"key": find_key(), "client": find_client(), "google": gauth.status(GTOKEN), "need": need_state(),
            "sheet": current_sheet()}


def refresh():
    sid = current_sheet()["id"]
    if not sid:
        raise RuntimeError("Chưa chọn file Google Sheet.")
    sheets.SHEET_ID = sid
    client = find_client()
    if client and gauth.status(GTOKEN):
        tabs = sheets.fetch_all(tok=gauth.access_token(client, GTOKEN))
    else:
        key = find_key()
        if not key:
            raise RuntimeError("Chưa đăng nhập Google.")
        tabs = sheets.fetch_all(key)
    data = {"fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"), "tabs": tabs}
    save_json(CACHE, data)
    return data


def pick_key_file(prompt="Chọn file khóa Google (.json)"):
    if sys.platform == "darwin":  # Python của Homebrew thường không có tkinter: dùng hộp thoại của macOS
        r = subprocess.run(["osascript", "-e", f'POSIX path of (choose file with prompt "{prompt}")'],
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(title=prompt, filetypes=[("JSON", "*.json")])
    root.destroy()
    return path


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
        if self.path.startswith("/api/drive-list"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("q", [""])[0]
            try:
                return self._send(200, json.dumps({"files": drive_list(q)}, ensure_ascii=False))
            except Exception as e:  # noqa: BLE001
                return self._send(200, json.dumps({"error": str(e)[:300]}, ensure_ascii=False))
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
            data = load_json(CACHE, None) if need_state() == "" else None
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
        if self.path == "/api/pick-client":
            path = pick_key_file("Chọn file OAuth của Google (client_secret_….json)")
            if path:
                try:
                    gauth.load_client(path)
                except Exception as e:  # noqa: BLE001
                    return self._send(200, json.dumps({"error": str(e)}, ensure_ascii=False))
                cfg = load_json(CONFIG, {})
                cfg["client_path"] = path
                save_json(CONFIG, cfg)
            return self._send(200, json.dumps(auth_info(), ensure_ascii=False))
        if self.path == "/api/google-login":
            client = find_client()
            if not client:  # lần đầu: hỏi file OAuth một lần rồi đăng nhập luôn
                path = pick_key_file("Chọn file OAuth của Google (client_secret_….json)")
                if not path:
                    return self._send(200, json.dumps({"error": "Cần file OAuth (client_secret_….json) để đăng nhập. Xem hướng dẫn trong README."}, ensure_ascii=False))
                try:
                    gauth.load_client(path)
                except Exception as e:  # noqa: BLE001
                    return self._send(200, json.dumps({"error": str(e)}, ensure_ascii=False))
                cfg = load_json(CONFIG, {})
                cfg["client_path"] = client = path
                save_json(CONFIG, cfg)
            try:
                gauth.login(client, GTOKEN)
            except Exception as e:  # noqa: BLE001
                return self._send(200, json.dumps({"error": str(e)}, ensure_ascii=False))
            return self._send(200, json.dumps(auth_info(), ensure_ascii=False))
        if self.path == "/api/google-logout":
            gauth.logout(GTOKEN)
            for p in (CACHE,):
                try:
                    os.remove(p)
                except OSError:
                    pass
            return self._send(200, json.dumps(auth_info(), ensure_ascii=False))
        if self.path == "/api/pick-key":
            path = pick_key_file()
            if path:
                cfg = load_json(CONFIG, {})
                cfg["key_path"] = path
                save_json(CONFIG, cfg)
            return self._send(200, json.dumps(auth_info(), ensure_ascii=False))
        self._send(404, "{}")


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("AV_PORT", "0"))), Handler)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    browser = "" if os.environ.get("AV_NOBROWSER") else pu.find_browser()
    proc = None
    if browser:
        proc = subprocess.Popen([browser, f"--app={url}", f"--user-data-dir={os.path.join(APP_DIR, 'profile')}",
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
