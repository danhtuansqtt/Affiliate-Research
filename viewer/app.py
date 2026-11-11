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
import gemini
import market
import platform_util as pu
import sheets
import updater
import views

try:  # macOS (Python cài từ python.org) hay thiếu chứng chỉ gốc: dùng bộ của certifi nếu có
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass

APP_DIR = pu.app_dir()
CONFIG = os.path.join(APP_DIR, "config.json")
CACHE = os.path.join(APP_DIR, "data.json")
PENDING = os.path.join(APP_DIR, "views_pending.jsonl")
GKEY = os.path.join(APP_DIR, "gemini_key.txt")
EVALS = os.path.join(APP_DIR, "evals.json")
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


STATE = {"last_ping": time.time(), "seen_ping": False, "quit": False, "email": ""}


def parse_sheet_id(text):
    """Nhận link Google Sheet đầy đủ hoặc chính ID; trả '' nếu không nhận ra."""
    m = re.search(r"/d/([A-Za-z0-9_-]{20,})", text or "")
    if m:
        return m.group(1)
    t = (text or "").strip()
    return t if re.fullmatch(r"[A-Za-z0-9_-]{20,}", t) else ""

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
    return {"signed_in": ok, "sheet": sh, "tracking": view_form() is not None, "gemini": bool(gemini.load_key(GKEY)), "viewer": STATE["email"] or load_json(CONFIG, {}).get("email", ""), "need": "login" if not ok else ("" if sh["id"] else "sheet")}


def view_form():
    """Cấu hình Google Form ghi lượt xem (None = tắt): env AV_VIEW_FORM > config.json > form.txt đóng gói cùng app."""
    url = os.environ.get("AV_VIEW_FORM") or load_json(CONFIG, {}).get("view_form", "")
    if not url:
        try:
            with open(resource("form.txt"), encoding="utf-8") as f:
                url = f.read().strip()
        except OSError:
            url = ""
    return views.parse_form(url)


def viewer_email():
    """Email Google của người đang dùng app (tra một lần mỗi lần mở app, nhớ lại để lần sau dùng khi chưa tra được)."""
    if not STATE["email"] and BROWSER["port"]:
        try:
            STATE["email"] = cdp.account_email(BROWSER["port"])
        except Exception:  # noqa: BLE001
            pass
        cfg = load_json(CONFIG, {})
        if STATE["email"]:
            cfg["email"] = STATE["email"]
            save_json(CONFIG, cfg)
    return STATE["email"] or load_json(CONFIG, {}).get("email", "")


def track_view(product, domain):
    form = view_form()
    if not form or not product:
        return
    user = viewer_email() or "(không rõ)"
    views.record(PENDING, form, user, product[:300], domain[:200])


EVAL_LOCK = threading.Lock()


def gemini_eval(eid, row, search, force, name="", domain=""):
    key = gemini.load_key(GKEY)
    if not key:
        raise RuntimeError("Chưa có khóa Gemini.")
    evals = load_json(EVALS, {})
    if eid in evals and not force:
        return evals[eid]
    cfg = load_json(CONFIG, {})
    model = cfg.get("gemini_model") or gemini.pick_model(key)
    mk = market.collect(name or eid, domain)  # Google Trends 90 ngày + link Trustpilot (không đo được thì ghi rõ là thiếu dữ liệu)
    try:
        res = gemini.evaluate(key, model, row, search, mk)
    except RuntimeError as e:
        if getattr(e, "code", 0) != 404:
            raise
        model = gemini.pick_model(key)  # model cũ không còn: chọn lại một lần
        res = gemini.evaluate(key, model, row, search, mk)
    cfg["gemini_model"] = model
    save_json(CONFIG, cfg)
    res.update(at=gemini.now(), search=bool(search))
    with EVAL_LOCK:
        evals = load_json(EVALS, {})
        evals[eid] = res
        save_json(EVALS, evals)
    return res


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
        if self.path == "/api/gemini-evals":
            return self._send(200, json.dumps({"evals": load_json(EVALS, {})}, ensure_ascii=False))
        if self.path == "/api/watch":
            return self._send(200, json.dumps(watch(), ensure_ascii=False))
        if self.path in ("/", "/index.html"):
            with open(resource("index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
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
        if self.path == "/api/view":
            if view_form():  # chỉ ghi khi quản lý đã bật; chạy nền để không làm chậm giao diện
                threading.Thread(target=track_view, args=(str(body.get("product", "")), str(body.get("domain", ""))), daemon=True).start()
            return self._send(200, "{}")
        if self.path == "/api/gemini-key":
            try:
                if body.get("remove"):
                    os.remove(GKEY) if os.path.exists(GKEY) else None
                else:
                    gemini.save_key(GKEY, str(body.get("key", "")))
            except Exception as e:  # noqa: BLE001
                return self._send(200, json.dumps({"error": str(e)}, ensure_ascii=False))
            return self._send(200, json.dumps({"gemini": bool(gemini.load_key(GKEY))}))
        if self.path == "/api/gemini-eval":
            try:
                row = {str(k)[:80]: str(v)[:600] for k, v in (body.get("row") or {}).items()}
                res = gemini_eval(str(body.get("id", ""))[:200], row, bool(body.get("search")), bool(body.get("force")),
                                  str(body.get("name", ""))[:200], str(body.get("domain", ""))[:200])
                return self._send(200, json.dumps(res, ensure_ascii=False))
            except Exception as e:  # noqa: BLE001
                return self._send(200, json.dumps({"error": str(e)[:300]}, ensure_ascii=False))
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
