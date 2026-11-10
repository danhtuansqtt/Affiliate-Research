"""Đăng nhập Google bằng tài khoản người dùng (OAuth cho ứng dụng máy tính, PKCE, chỉ dùng thư viện chuẩn).

Dùng khi Google Sheet đang ở chế độ "hạn chế": chỉ tài khoản được cấp quyền xem mới đọc được.
Client OAuth (file client_secret_*.json, loại "Desktop app") KHÔNG nằm trong mã nguồn công khai:
người dùng chọn file đó một lần. Token đăng nhập lưu ở google_token.json trong thư mục dữ liệu của app.
"""
import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

SCOPES = "openid email https://www.googleapis.com/auth/spreadsheets.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
LOGIN_TIMEOUT = 180  # giây chờ người dùng bấm đồng ý trên trình duyệt

_lock = threading.Lock()


def load_client(path):
    """Đọc file client_secret_*.json tải từ Google Cloud Console; trả (client_id, client_secret)."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    c = raw.get("installed") or raw.get("web")
    if not c or "client_id" not in c:
        raise RuntimeError("File này không phải client OAuth của Google (cần loại 'Desktop app').")
    return c["client_id"], c.get("client_secret", "")


def _post(url, fields):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode("utf-8"))
            msg = err.get("error_description") or err.get("error") or str(e)
        except ValueError:
            msg = str(e)
        raise RuntimeError(f"Google từ chối: {msg}") from None


def _email_from_id_token(id_token):
    try:
        part = id_token.split(".")[1]
        part += "=" * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part)).get("email", "")
    except (IndexError, ValueError):
        return ""


def _save(token_path, data):
    fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)


def status(token_path):
    """{'email': ...} nếu đã đăng nhập, ngược lại {}."""
    try:
        with open(token_path, encoding="utf-8") as f:
            t = json.load(f)
        return {"email": t.get("email", "")} if t.get("refresh_token") else {}
    except (OSError, ValueError):
        return {}


def logout(token_path):
    try:
        os.remove(token_path)
    except OSError:
        pass


def login(client_path, token_path):
    """Mở trình duyệt để đăng nhập, chờ mã trả về cổng 127.0.0.1 rồi đổi lấy token. Chặn tối đa LOGIN_TIMEOUT giây."""
    client_id, client_secret = load_client(client_path)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    result = {}

    class CB(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" not in q and "error" not in q:
                self.send_response(404)
                self.end_headers()
                return
            if q.get("state", [""])[0] == state:
                result.update({k: v[0] for k, v in q.items()})
                body = "<h3>Đăng nhập xong. Anh đóng tab này và quay lại Affiliate Viewer.</h3>"
            else:
                body = "<h3>Phiên đăng nhập không khớp. Hãy thử lại từ app.</h3>"
            raw = f"<meta charset=utf-8>{body}".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    with _lock:  # một lượt đăng nhập tại một thời điểm
        srv = HTTPServer(("127.0.0.1", 0), CB)
        srv.timeout = 1
        redirect = f"http://127.0.0.1:{srv.server_address[1]}/"
        params = {"client_id": client_id, "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
                  "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
                  "access_type": "offline", "prompt": "consent select_account"}
        webbrowser.open(f"{AUTH_URL}?{urllib.parse.urlencode(params)}")
        deadline = time.time() + LOGIN_TIMEOUT
        try:
            while not result and time.time() < deadline:
                srv.handle_request()
        finally:
            srv.server_close()
    if not result:
        raise RuntimeError("Hết thời gian chờ đăng nhập Google. Bấm 'Đăng nhập Google' để thử lại.")
    if "error" in result:
        raise RuntimeError(f"Đăng nhập Google bị hủy hoặc lỗi: {result['error']}")
    tok = _post(TOKEN_URL, {"code": result["code"], "client_id": client_id, "client_secret": client_secret,
                            "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": verifier})
    if not tok.get("refresh_token"):
        raise RuntimeError("Google không trả refresh token. Vào myaccount.google.com/permissions gỡ quyền app rồi đăng nhập lại.")
    email = _email_from_id_token(tok.get("id_token", ""))
    _save(token_path, {"refresh_token": tok["refresh_token"], "email": email})
    return {"email": email}


def access_token(client_path, token_path):
    """Access token còn hạn (đổi từ refresh token đã lưu)."""
    try:
        with open(token_path, encoding="utf-8") as f:
            saved = json.load(f)
    except (OSError, ValueError):
        raise RuntimeError("Chưa đăng nhập Google. Bấm 'Đăng nhập Google'.") from None
    client_id, client_secret = load_client(client_path)
    try:
        tok = _post(TOKEN_URL, {"client_id": client_id, "client_secret": client_secret,
                                "refresh_token": saved["refresh_token"], "grant_type": "refresh_token"})
    except RuntimeError as e:
        raise RuntimeError(f"{e}. Phiên đăng nhập có thể đã hết hạn: bấm 'Đăng nhập Google' lại.") from None
    return tok["access_token"]
