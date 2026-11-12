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
from concurrent.futures import ThreadPoolExecutor
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
gemini.SKILL_OVERRIDE = os.path.join(APP_DIR, "skill.md")  # có file này thì dùng thay skill có sẵn
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


CFG_LOCK = threading.Lock()


def gemini_eval(eid, row, search, force, name="", domain="", fast=False):
    key = gemini.load_key(GKEY)
    if not key:
        raise RuntimeError("Chưa có khóa Gemini.")
    evals = load_json(EVALS, {})
    if eid in evals and not force:
        return evals[eid]
    cfg = load_json(CONFIG, {})
    # Dùng lại model đã chạy tốt (trong 24 giờ); quá hạn thì thử lại từ model mới nhất
    mk_, ts_ = ("gemini_model_fast", "gemini_model_fast_ts") if fast else ("gemini_model", "gemini_model_ts")  # mỗi chế độ nhớ model riêng
    preferred = cfg.get(mk_) if time.time() - cfg.get(ts_, 0) < 86400 else None
    mk = market.collect(name or eid, domain)  # Google Trends 90 ngày + link Trustpilot (không đo được thì ghi rõ là thiếu dữ liệu)
    res = gemini.evaluate_auto(key, preferred, row, search, mk, fast=fast)  # model treo/quá tải/không còn thì tự thử model khác
    with CFG_LOCK:
        cfg = load_json(CONFIG, {})
        cfg[mk_], cfg[ts_] = res["model"], time.time()
        save_json(CONFIG, cfg)
    res.update(at=gemini.now(), search=bool(search))
    with EVAL_LOCK:
        evals = load_json(EVALS, {})
        evals[eid] = res
        save_json(EVALS, evals)
    return res


# ---- Đánh giá Gemini hàng loạt: chạy nền, kết quả lưu vào evals.json như đánh giá từng sản phẩm ----
BATCH = {"running": False, "done": 0, "total": 0, "current": "", "stop": False, "ok": 0, "fail": 0, "skipped": 0, "error": "", "last_error": ""}
BATCH_LOCK = threading.Lock()


def _wait(seconds):
    for _ in range(seconds):
        if BATCH["stop"]:
            return
        time.sleep(1)


BATCH_WORKERS = 3  # số sản phẩm đánh giá cùng lúc


def batch_worker(items, search, fast=False):
    lock = threading.Lock()
    state = {"fails_in_row": 0}

    def one(it):
        if BATCH["stop"]:
            return
        BATCH["current"] = it["name"]
        if it["id"] in load_json(EVALS, {}):  # đã có kết quả thì bỏ qua, không tốn lượt
            with lock:
                BATCH["skipped"] += 1
                BATCH["done"] += 1
            return
        for attempt in (1, 2):
            try:
                gemini_eval(it["id"], it["row"], search, False, it["name"], it["domain"], fast)
                with lock:
                    BATCH["ok"] += 1
                    state["fails_in_row"] = 0
                break
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                with lock:
                    BATCH["last_error"] = msg[:200]
                if "không hợp lệ" in msg or "Chưa có khóa" in msg:  # sai khóa thì dừng cả lượt
                    BATCH["error"], BATCH["stop"] = msg, True
                    break
                if "Hết hạn mức" in msg and attempt == 1:  # chạm giới hạn lượt/phút: chờ 60 giây thử lại một lần
                    BATCH["current"] = it["name"] + " (chờ hạn mức…)"
                    _wait(60)
                    continue
                with lock:
                    BATCH["fail"] += 1
                    state["fails_in_row"] += 1
                break
        with lock:
            BATCH["done"] += 1
            if state["fails_in_row"] >= 3 and not BATCH["error"]:  # liên tục lỗi: dừng để không đốt hạn mức vô ích
                BATCH["error"] = "Dừng vì 3 sản phẩm liên tiếp bị lỗi. Lỗi gần nhất: " + BATCH["last_error"]
                BATCH["stop"] = True
        _wait(1)  # giãn cách nhẹ để Google Trends và Gemini không chặn

    try:
        with ThreadPoolExecutor(max_workers=BATCH_WORKERS) as ex:
            list(ex.map(one, items))
    finally:
        BATCH["running"] = False
        BATCH["current"] = ""


def batch_status():
    evals = load_json(EVALS, {})
    return {"job": {k: BATCH[k] for k in ("running", "done", "total", "current", "ok", "fail", "skipped", "error", "last_error")},
            "brief": {k: {"score": v.get("score"), "tier": v.get("tier"), "at": v.get("at")} for k, v in evals.items()}}


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
        if self.path == "/api/gemini-batch":
            return self._send(200, json.dumps(batch_status(), ensure_ascii=False))
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
        if self.path == "/api/gemini-batch/start":
            if not gemini.load_key(GKEY):
                return self._send(200, json.dumps({"error": "Chưa có khóa Gemini. Dán khóa trong khung Đánh giá Gemini của một sản phẩm."}, ensure_ascii=False))
            items, seen = [], set()
            for it in (body.get("items") or [])[:100]:
                eid = str(it.get("id", ""))[:200]
                if eid and eid not in seen:
                    seen.add(eid)
                    items.append({"id": eid, "name": str(it.get("name", ""))[:200], "domain": str(it.get("domain", ""))[:200],
                                  "row": {str(k)[:80]: str(v)[:600] for k, v in (it.get("row") or {}).items()}})
            with BATCH_LOCK:
                if BATCH["running"]:
                    return self._send(200, json.dumps({"error": "Đang có lượt đánh giá chạy."}, ensure_ascii=False))
                BATCH.update(running=True, done=0, total=len(items), current="", stop=False, ok=0, fail=0, skipped=0, error="", last_error="")
                threading.Thread(target=batch_worker, args=(items, bool(body.get("search")), bool(body.get("fast"))), daemon=True).start()
            return self._send(200, json.dumps(batch_status(), ensure_ascii=False))
        if self.path == "/api/gemini-batch/stop":
            BATCH["stop"] = True
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
                                  str(body.get("name", ""))[:200], str(body.get("domain", ""))[:200], bool(body.get("fast")))
                return self._send(200, json.dumps(res, ensure_ascii=False))
            except Exception as e:  # noqa: BLE001
                return self._send(200, json.dumps({"error": str(e)[:300]}, ensure_ascii=False))
        if self.path == "/api/open-drive":
            open_drive()
            return self._send(200, "{}")
        self._send(404, "{}")


PING_TIMEOUT = float(os.environ.get("AV_PING_TIMEOUT", "20"))


def window_alive(url):
    """True/False: cửa sổ app còn mở hay không (hỏi trình duyệt qua cổng điều khiển); None: không hỏi được."""
    if not BROWSER["port"]:
        return None
    try:
        return any(t.get("type") == "page" and t.get("url", "").startswith(url) for t in cdp.targets(BROWSER["port"]))
    except Exception:  # noqa: BLE001
        return None


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
                                 "--window-size=1400,900", "--no-first-run", "--no-default-browser-check",
                                 # cửa sổ nền/bị che không được làm chậm bộ đếm giờ, nếu không tín hiệu "còn sống" của trang bị trễ
                                 "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                                 "--disable-backgrounding-occluded-windows"])
    elif not os.environ.get("AV_NOBROWSER"):
        webbrowser.open(url)
    try:
        while True:
            time.sleep(1)
            if proc is not None and proc.poll() is not None:
                break
            if STATE["seen_ping"] and time.time() - STATE["last_ping"] > PING_TIMEOUT:
                alive = window_alive(url)
                if alive:  # trang không gọi kịp (cửa sổ nền bị Chrome làm chậm) nhưng cửa sổ vẫn mở: không thoát
                    STATE["last_ping"] = time.time()
                elif alive is False or time.time() - STATE["last_ping"] > 300:
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
